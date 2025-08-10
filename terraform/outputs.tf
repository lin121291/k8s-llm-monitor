# AI Service Monitor - Terraform Outputs
# This file defines all output values from the Terraform configuration

# GKE Cluster Information
output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.gke.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.gke.endpoint
  sensitive   = true
}

output "get_credentials_command" {
  description = "Command to get GKE credentials"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.gke.name} --region ${var.region} --project ${var.project_id}"
}

# Project Information
output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region"
  value       = var.region
}

# Database Information
output "database_connection" {
  description = "PostgreSQL database connection information"
  value = {
    host     = google_sql_database_instance.postgres.private_ip_address
    port     = 5432
    database = google_sql_database.app_db.name
    username = google_sql_user.app_user.name
  }
  sensitive = true
}

# Redis Information  
output "redis_host" {
  description = "Redis instance host"
  value       = google_redis_instance.cache.host
}