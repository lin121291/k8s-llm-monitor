# AI Service Monitor - Terraform Infrastructure

This is the Terraform infrastructure configuration for AI Service Monitor, using a modular structure to manage GCP resources.

## File Structure

```
terraform/
├── main.tf           # Core infrastructure resources (VPC, GKE, Cloud SQL, Redis)
├── variables.tf      # Input variable definitions
├── outputs.tf        # Output value definitions
├── providers.tf      # Provider configuration
├── versions.tf       # Terraform and Provider version constraints
├── locals.tf         # Local values and common configurations
├── terraform.tfvars  # Actual variable values (not version controlled)
├── terraform.tfvars.example # Variable value examples
└── README.md         # This file
```

## Centralized Configuration

All project settings are centrally managed in `../config/monitor.yaml`:
- GCP Project ID
- Docker registry location  
- Kubernetes namespace
- Other project settings

**To change project settings**: Simply edit the `project` block in `config/monitor.yaml`.

## Quick Deployment

### 1. Prerequisites
```bash
# Ensure necessary tools are installed
terraform --version
gcloud --version

# Login to GCP
gcloud auth login
gcloud auth application-default login
```

### 2. Configure Variables
```bash
# Copy example configuration and modify
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars
```

### 3. Deploy
```bash
# Using convenience script (recommended)
../scripts/terraform.sh init
../scripts/terraform.sh plan  
../scripts/terraform.sh apply

# Or manually execute
terraform init
terraform plan
terraform apply
```

### 4. Get Cluster Access
```bash
# Use terraform output to get command
terraform output get_credentials_command

# Or manually execute
gcloud container clusters get-credentials ai-monitor-dev-gke --region us-central1 --project ai-log-468502
```

## Included Resources

### Network Resources
- **VPC Network**: 10.0.0.0/24 primary network
- **Subnet**: Includes pods (10.1.0.0/16) and services (10.2.0.0/16) secondary ranges
- **NAT Gateway**: Provides external network access for nodes
- **Firewall Rules**: SSH access and internal communication

### GKE Cluster
- **Regional GKE Cluster**: Spans multiple availability zones
- **Node Pool**: 2 nodes, can auto-scale to 5 nodes
- **Preemptible instances**: Cost optimization
- **Private nodes**: Private cluster with public endpoint

### Managed Services
- **Cloud SQL PostgreSQL**: f1-micro specification, suitable for development
- **Redis Cache**: 1GB Basic tier
- **Private Service Connection**: Secure internal network connection

### Kubernetes Resources
- **Namespace**: ai-monitor
- **ConfigMap**: Contains database and Redis connection information

## Modular Structure Explanation

### main.tf
Contains all core infrastructure resources:
- Network resources (VPC, subnets, NAT)
- GKE cluster and node pools  
- Cloud SQL and Redis instances
- Kubernetes namespace and configuration

### variables.tf
Defines all input variables:
- `project_id`: GCP Project ID
- `region`: GCP region
- `zone`: GCP availability zone
- `environment`: Environment tag

### outputs.tf  
Defines output values:
- Cluster information (name, endpoint, auth commands)
- Database connection information
- Redis host information

### locals.tf
Defines common local values:
- Naming conventions
- Common tags
- Network CIDR ranges

## Custom Configuration

### Changing Node Specifications
Edit node configuration in `main.tf`:
```hcl
node_config {
  machine_type = "e2-standard-2"  # Larger instance
  disk_size_gb = 100              # Larger disk
}
```

### Changing Database Specifications
Edit database settings in `main.tf`:
```hcl
settings {
  tier = "db-g1-small"  # Larger database instance
}
```

### Production Environment Configuration
Modify `terraform.tfvars`:
```hcl
environment = "prod"
```

Then adjust production settings in `main.tf`:
```hcl
# Disable preemptible nodes
preemptible = false

# Increase node count
node_count = 3
max_node_count = 10

# Enable deletion protection
deletion_protection = true
```

## Cost Estimation

### Development Environment Configuration (Monthly)
- GKE cluster management fee: $74.40
- 2x e2-medium preemptible: ~$24
- Cloud SQL f1-micro: ~$9  
- Redis 1GB Basic: ~$25
- Network and storage: ~$10

**Total: ~$142/month**

### Cost Saving Tips
- Use preemptible nodes (already enabled)
- Use small instance specifications for development
- Enable auto-scaling to avoid over-provisioning
- Regularly clean up unnecessary resources

## Troubleshooting

### Common Errors

**1. APIs Not Enabled**
```bash
# Enable necessary APIs
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com  
gcloud services enable servicenetworking.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

**2. Insufficient Permissions**
```bash
# Check IAM permissions
gcloud projects get-iam-policy ai-log-468502
```

**3. Network Conflicts**
```bash
# Check existing networks
gcloud compute networks list --project=ai-log-468502
```

## Clean Up Resources

```bash
# Destroy all resources
terraform destroy

# Confirm cleanup
gcloud compute networks list --project=ai-log-468502
```

## File Change Tracking

- `main.tf.backup`: Backup file before refactoring
- After modularization, each file has clear responsibilities for easier maintenance and collaboration