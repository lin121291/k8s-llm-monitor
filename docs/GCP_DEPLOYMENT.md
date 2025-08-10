# AI Service Monitor - GCP Deployment Guide

Complete guide for deploying AI Service Monitor to Google Cloud Platform using Terraform and GKE.

## Prerequisites

### Required Tools
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (gcloud CLI)
- [Docker](https://docs.docker.com/get-docker/)
- [Kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli) (>= 1.0)
- [Helm](https://helm.sh/docs/intro/install/) (>= 3.0)

### GCP Account Setup
1. Create a Google Cloud Project
2. Enable billing for your project
3. Install and initialize gcloud CLI:
```bash
gcloud init
gcloud auth application-default login
```

## Quick Deployment

### One-Command Deployment
```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Deploy everything to GCP
./scripts/deploy.sh
```

This script will:
- Check all dependencies
- Enable required GCP APIs
- Build and push Docker images to GCR
- Deploy infrastructure with Terraform
- Deploy applications to GKE
- Setup monitoring stack (Prometheus, Grafana, Kafka)
- Verify deployment and show access information

## Infrastructure Components

### What Gets Deployed

#### Core Infrastructure
- **GKE Cluster**: Managed Kubernetes with auto-scaling
- **VPC Network**: Private networking with NAT gateway
- **Cloud SQL**: PostgreSQL database for metadata
- **Redis**: In-memory caching and session storage
- **Cloud Storage**: Log storage and backups
- **Pub/Sub**: Message queuing system
- **Secret Manager**: Secure credential storage

#### Monitoring Stack
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization dashboards  
- **Kafka**: Real-time log streaming
- **Fluentd**: Log aggregation and forwarding

#### Security Features
- **Workload Identity**: Secure GCP service authentication
- **Private GKE Nodes**: No external IP addresses
- **Network Policies**: Micro-segmentation
- **IAM Roles**: Least privilege access

## Detailed Deployment Steps

### 1. Prepare Environment
```bash
# Clone repository
git clone https://github.com/yourusername/ai-service-monitor.git
cd ai-service-monitor

# Set environment variables
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export ENVIRONMENT="dev"  # or staging, prod
```

### 2. Configure Terraform (Optional)
```bash
# Edit terraform/terraform.tfvars (optional customization)
cat > terraform/terraform.tfvars << EOF
project_id = "$PROJECT_ID"
region = "$REGION"
environment = "$ENVIRONMENT"

# Custom configurations
gke_node_count = 3
gke_machine_type = "e2-standard-4"
enable_gpu = false
redis_tier = "BASIC"
EOF
```

### 3. Deploy Infrastructure
```bash
# Option A: Use automated script (recommended)
./scripts/deploy.sh

# Option B: Manual step-by-step deployment
./scripts/terraform.sh init -p $PROJECT_ID -e $ENVIRONMENT
./scripts/terraform.sh plan -p $PROJECT_ID -e $ENVIRONMENT
./scripts/terraform.sh apply -p $PROJECT_ID -e $ENVIRONMENT
```

### 4. Verify Deployment
```bash
# Check cluster status
kubectl get nodes
kubectl get pods -n ai-monitor

# Check services
kubectl get services -n ai-monitor

# Test API Gateway
kubectl port-forward svc/api-gateway-service 8080:80 -n ai-monitor &
curl http://localhost:8080/health
```

## Advanced Configuration

### Environment-Specific Deployments

#### Development Environment
```bash
ENVIRONMENT=dev ./scripts/deploy.sh
```
- Single node cluster
- Basic Redis tier
- Preemptible instances
- Local storage

#### Production Environment
```bash
ENVIRONMENT=prod ./scripts/deploy.sh
```
- Multi-zone cluster with high availability
- Standard Redis tier with replication
- Non-preemptible instances
- Persistent storage with backups

### Custom Terraform Variables

Create `terraform/environments/$ENVIRONMENT/terraform.tfvars`:
```hcl
# Infrastructure sizing
gke_node_count = 5
gke_machine_type = "c2-standard-4"
gke_disk_size = 100

# GPU configuration
enable_gpu = true
gpu_type = "nvidia-tesla-t4"
gpu_max_nodes = 2

# Database configuration
db_tier = "db-custom-2-4096"
db_disk_size = 100
redis_memory_size = 4
redis_tier = "STANDARD_HA"

# Security
enable_workload_identity = true
enable_network_policy = true
deletion_protection = true

# Monitoring
monitoring_retention_days = 30
```

### Helm Values Customization

#### Prometheus Configuration
Edit `terraform/helm-values/prometheus.yaml`:
```yaml
prometheus:
  prometheusSpec:
    retention: "30d"
    storageSpec:
      volumeClaimTemplate:
        spec:
          resources:
            requests:
              storage: 50Gi
```

#### Kafka Configuration
Edit `terraform/helm-values/kafka.yaml`:
```yaml
kafka:
  replicaCount: 5
  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "2000m"
```

## Monitoring and Access

### Dashboard Access

#### Port Forwarding (Development)
```bash
# Grafana Dashboard
kubectl port-forward svc/prometheus-grafana 3000:80 -n ai-monitor
# Access: http://localhost:3000 (admin/admin123)

# Prometheus
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n ai-monitor
# Access: http://localhost:9090

# API Gateway
kubectl port-forward svc/api-gateway-service 8080:80 -n ai-monitor
# Access: http://localhost:8080/docs
```

#### External Load Balancer (Production)
```bash
# Get external IPs
kubectl get services -n ai-monitor -o wide

# API Gateway external IP
API_GATEWAY_IP=$(kubectl get service api-gateway-service -n ai-monitor -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "API Gateway: http://$API_GATEWAY_IP"
```

### GCP Console Links
```bash
# After deployment, get direct links
terraform output -raw monitoring_dashboard_urls
```

## Security Configuration

### Workload Identity Setup
```bash
# Workload Identity is automatically configured
# Verify setup
kubectl describe serviceaccount ai-monitor-ksa -n ai-monitor
```

### Secret Management
```bash
# Add API keys to Secret Manager
gcloud secrets versions add ai-monitor-dev-api-keys --data-file=secrets.json

# Update secrets in cluster
kubectl create secret generic api-keys \
  --from-literal=openai_key="your-key" \
  --from-literal=anthropic_key="your-key" \
  -n ai-monitor
```

### Network Security
- All nodes are private (no external IPs)
- Traffic flows through NAT gateway
- Network policies restrict pod-to-pod communication
- Firewall rules limit external access

## Cost Management

### Estimated Monthly Costs (USD)

#### Development Environment
```
GKE Nodes (3x e2-standard-4): ~$220
Cloud SQL (db-f1-micro): ~$7
Redis (1GB Basic): ~$25
Storage & Networking: ~$15
Total: ~$267/month
```

#### Production Environment
```
GKE Nodes (5x c2-standard-4): ~$650
Cloud SQL (db-custom-2-4096): ~$120
Redis (4GB Standard HA): ~$200
Storage & Networking: ~$50
Total: ~$1020/month
```

### Cost Optimization Tips
1. **Use Preemptible Instances**: 60-70% cost reduction
2. **Enable Cluster Autoscaling**: Scale down during low traffic
3. **Right-size Resources**: Monitor usage and adjust
4. **Use Committed Use Discounts**: For stable workloads

```bash
# Enable preemptible instances
export TF_VAR_enable_preemptible=true
./scripts/deploy.sh
```

## Troubleshooting

### Common Issues

#### 1. API Enablement Failures
```bash
# Manually enable APIs
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable sql.googleapis.com
```

#### 2. Terraform State Conflicts
```bash
# Import existing resources
terraform import google_container_cluster.primary projects/$PROJECT_ID/locations/$REGION/clusters/ai-monitor-dev-gke

# Or force unlock
terraform force-unlock <lock_id>
```

#### 3. Image Build Failures
```bash
# Check Docker daemon
docker ps

# Manually build and push
docker build -t gcr.io/$PROJECT_ID/api-gateway:latest .
docker push gcr.io/$PROJECT_ID/api-gateway:latest
```

#### 4. Cluster Access Issues
```bash
# Get cluster credentials
gcloud container clusters get-credentials ai-monitor-dev-gke --region us-central1

# Check RBAC permissions
kubectl auth can-i create pods --namespace ai-monitor
```

### Debug Commands
```bash
# Check all resources
kubectl get all -n ai-monitor

# Examine failed pods
kubectl describe pod <pod-name> -n ai-monitor
kubectl logs <pod-name> -n ai-monitor --previous

# Check cluster events
kubectl get events -n ai-monitor --sort-by='.lastTimestamp'

# Verify Terraform state
terraform show
terraform refresh
```

## Cleanup

### Destroy Infrastructure
```bash
# Complete cleanup
./scripts/terraform.sh destroy -p $PROJECT_ID -e $ENVIRONMENT

# Manual cleanup if needed
terraform destroy -var="project_id=$PROJECT_ID"

# Clean up container images
gcloud container images list --repository=gcr.io/$PROJECT_ID
gcloud container images delete gcr.io/$PROJECT_ID/api-gateway:latest --quiet
```

### Partial Cleanup
```bash
# Only remove Kubernetes resources
kubectl delete namespace ai-monitor

# Only remove specific services
helm uninstall prometheus -n ai-monitor
helm uninstall kafka -n ai-monitor
```

## CI/CD Integration

### GitHub Actions Setup
1. Create service account key:
```bash
gcloud iam service-accounts create github-actions --description="GitHub Actions Service Account"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.developer" \
  --role="roles/storage.admin" \
  --role="roles/container.admin"

gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@$PROJECT_ID.iam.gserviceaccount.com
```

2. Add GitHub Secrets:
   - `GCP_PROJECT_ID`: Your project ID
   - `GCP_SA_KEY`: Contents of key.json file

3. Push to trigger deployment:
```bash
git push origin main  # Deploys to dev
git push origin release/production  # Deploys to prod
```

## Additional Resources

- [Terraform GCP Provider Documentation](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [GKE Best Practices](https://cloud.google.com/kubernetes-engine/docs/best-practices)
- [Monitoring and Logging](https://cloud.google.com/monitoring/kubernetes-engine)
- [Security Hardening](https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster)

## Support

For deployment issues:
1. Check the [troubleshooting section](#-troubleshooting)
2. Review logs: `kubectl logs -n ai-monitor <pod-name>`
3. Open an issue with deployment logs and error messages
4. Join our community Discord for real-time help