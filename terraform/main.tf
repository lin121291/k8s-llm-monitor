# AI Service Monitor - Main Infrastructure Resources
# This file contains all the core GCP resources: VPC, GKE, Cloud SQL, Redis

# =============================================================================
# NETWORKING
# =============================================================================

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "${local.name}-vpc"
  auto_create_subnetworks = false
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "${local.name}-subnet"
  ip_cidr_range = local.vpc_cidr
  region        = var.region
  network       = google_compute_network.vpc.id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = local.pods_cidr
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = local.services_cidr
  }

  private_ip_google_access = true
}

# Cloud Router for NAT
resource "google_compute_router" "router" {
  name    = "${local.name}-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

# NAT Gateway
resource "google_compute_router_nat" "nat" {
  name                               = "${local.name}-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# Firewall Rules
resource "google_compute_firewall" "allow_internal" {
  name    = "${local.name}-allow-internal"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/24", "10.1.0.0/16", "10.2.0.0/16"]
  target_tags   = ["gke-node"]
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "${local.name}-allow-ssh"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"] # Google IAP
  target_tags   = ["gke-node"]
}

# =============================================================================
# GKE CLUSTER
# =============================================================================

# GKE Cluster
resource "google_container_cluster" "gke" {
  name     = "${local.name}-gke"
  location = var.region

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name

  # IP allocation policy
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = local.master_ipv4_cidr_block
  }

  # Remove default node pool
  remove_default_node_pool = true
  initial_node_count       = 1

  # Basic configuration
  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"

  # Disable client certificate
  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }

  # Maintenance policy
  maintenance_policy {
    daily_maintenance_window {
      start_time = "04:00"
    }
  }

  deletion_protection = false
}

# Node Pool
resource "google_container_node_pool" "primary" {
  name       = "${local.name}-nodes"
  location   = var.region
  cluster    = google_container_cluster.gke.name
  node_count = 2

  autoscaling {
    min_node_count = 1
    max_node_count = 5
  }

  node_config {
    preemptible  = true
    machine_type = "e2-medium"
    disk_size_gb = 50

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    labels = {
      env = var.environment
    }

    tags = ["gke-node"]

    metadata = {
      disable-legacy-endpoints = "true"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# =============================================================================
# MANAGED SERVICES
# =============================================================================

# Private Service Connection for managed services
resource "google_compute_global_address" "private_service_range" {
  name          = "${local.name}-private-service-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_service_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_service_range.name]
}

# Cloud SQL (PostgreSQL)
resource "random_password" "db_password" {
  length  = 16
  special = true
}

resource "google_sql_database_instance" "postgres" {
  name             = "${local.name}-postgres"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro"

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }

    backup_configuration {
      enabled    = true
      start_time = "02:00"
    }
  }

  depends_on = [google_service_networking_connection.private_service_connection]
}

resource "google_sql_database" "app_db" {
  name     = "ai_monitor"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app_user" {
  name     = "ai_monitor_user"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

# Redis Cache
resource "google_redis_instance" "cache" {
  name           = "${local.name}-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region

  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  depends_on = [google_service_networking_connection.private_service_connection]
}

# =============================================================================
# KUBERNETES RESOURCES
# =============================================================================

# Namespace
resource "kubernetes_namespace" "ai_monitor" {
  metadata {
    name = "ai-monitor"
    labels = {
      name        = "ai-monitor"
      environment = var.environment
    }
  }

  depends_on = [google_container_node_pool.primary]
}

# ConfigMap
resource "kubernetes_config_map" "config" {
  metadata {
    name      = "ai-monitor-config"
    namespace = kubernetes_namespace.ai_monitor.metadata[0].name
  }

  data = {
    "DATABASE_URL" = "postgresql://${google_sql_user.app_user.name}:${random_password.db_password.result}@${google_sql_database_instance.postgres.private_ip_address}:5432/${google_sql_database.app_db.name}"
    "REDIS_URL"    = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
    "ENVIRONMENT"  = var.environment
  }
}

# End of main infrastructure resources