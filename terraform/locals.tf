# AI Service Monitor - Local Values
# This file defines commonly used local values

locals {
  # Naming convention
  name = "ai-monitor-${var.environment}"
  
  # Common labels
  common_labels = {
    project     = "ai-monitor"
    environment = var.environment
    managed_by  = "terraform"
  }
  
  # Network configuration
  vpc_cidr               = "10.0.0.0/24"
  pods_cidr              = "10.1.0.0/16"
  services_cidr          = "10.2.0.0/16"
  master_ipv4_cidr_block = "172.16.0.0/28"
}