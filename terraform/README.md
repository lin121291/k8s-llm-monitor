# Terraform Configuration

This directory contains Terraform configuration for deploying the Service Monitor API to Google Cloud Platform (GCP).

## 🏗️ Infrastructure

The Terraform configuration creates:

- **GKE Cluster** - Managed Kubernetes cluster
- **VPC Network** - Custom virtual private cloud
- **Subnet** - Private subnet for the cluster
- **Service Account** - IAM service account for Kubernetes
- **Firewall Rules** - Security rules for load balancer health checks
- **Node Pool** - Managed worker nodes

## 🚀 Quick Deploy

```bash
# 1. Set up variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project ID

# 2. Initialize Terraform
terraform init

# 3. Plan deployment
terraform plan

# 4. Deploy infrastructure
terraform apply

# 5. Configure kubectl
gcloud container clusters get-credentials service-monitor-cluster \
  --zone us-central1-a \
  --project your-project-id

# 6. Deploy application
kubectl apply -f ../k8s/
```

## 📋 Prerequisites

1. **GCP Account** with billing enabled
2. **Terraform** >= 1.0 installed
3. **gcloud CLI** configured with authentication
4. **Enable APIs**:
   ```bash
   gcloud services enable container.googleapis.com
   gcloud services enable compute.googleapis.com
   ```

## 🔧 Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `project_id` | GCP Project ID | `my-project-123` |
| `region` | GCP Region | `us-central1` |
| `zone` | GCP Zone | `us-central1-a` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `cluster_name` | GKE cluster name | `service-monitor-cluster` |
| `node_count` | Number of worker nodes | `2` |
| `machine_type` | Node machine type | `e2-medium` |
| `environment` | Environment tag | `demo` |

## 📊 Outputs

After deployment, Terraform outputs:

- `cluster_name` - The name of the created GKE cluster
- `cluster_endpoint` - Kubernetes API endpoint
- `cluster_location` - Cluster zone/region
- `kubectl_config_command` - Command to configure kubectl

## 🧹 Cleanup

```bash
# Destroy all infrastructure
terraform destroy

# Clean up local state
rm -rf .terraform terraform.tfstate*
```

## 💡 Best Practices

1. **State Management** - Use remote state for production
2. **Security** - Enable Workload Identity for pod authentication
3. **Monitoring** - Stackdriver logging and monitoring enabled
4. **Auto-scaling** - Cluster autoscaling configured
5. **Network Security** - Private cluster with authorized networks

## 🔍 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        GCP Project                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Custom VPC                           │   │
│  │                                                     │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │              GKE Cluster                    │   │   │
│  │  │                                             │   │   │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐    │   │   │
│  │  │  │  Node   │  │  Node   │  │   ...   │    │   │   │
│  │  │  │ Pool    │  │ Pool    │  │         │    │   │   │
│  │  │  └─────────┘  └─────────┘  └─────────┘    │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```