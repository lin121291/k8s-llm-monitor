# AI Service Monitor - Provider Configuration
# This file configures all required providers

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Get Google Cloud client configuration
data "google_client_config" "default" {}

# Configure the Kubernetes Provider
provider "kubernetes" {
  host                   = "https://${google_container_cluster.gke.endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(google_container_cluster.gke.master_auth[0].cluster_ca_certificate)
}