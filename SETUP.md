# 🚀 AI-Powered Service Monitor - Setup Guide

## 📋 Prerequisites

1. **Google Cloud Platform Account**
2. **Docker and Docker Compose**
3. **Terraform** (for infrastructure deployment)
4. **kubectl** (for Kubernetes management)
5. **gcloud CLI** (configured with your GCP project)

## ⚙️ Initial Configuration

### 1. Environment Setup

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```bash
# Required: Your GCP Project ID
GCP_PROJECT_ID=your-actual-gcp-project-id
DOCKER_REGISTRY=gcr.io/your-actual-gcp-project-id

# Security
GRAFANA_ADMIN_PASSWORD=your-secure-password-here
```

### 2. Project Configuration

Edit `config/monitor.yaml` and update:

```yaml
project:
  gcp_project_id: "your-actual-gcp-project-id"
  docker_registry: "gcr.io/your-actual-gcp-project-id"
```

### 3. GCP Authentication

```bash
# Login to GCP
gcloud auth login

# Set your project
gcloud config set project your-actual-gcp-project-id

# Configure Docker for GCR
gcloud auth configure-docker
```

## 🚀 Deployment Options

### Option 1: Local Development (Docker Compose)

```bash
# Start all services locally
docker-compose up -d

# Access services
# - API Gateway: http://localhost:8080/docs
# - Grafana: http://localhost:3000 (admin/your-password)
# - Prometheus: http://localhost:9090
```

### Option 2: GCP/GKE Deployment

```bash
# Full deployment (infrastructure + applications)
./scripts/deploy.sh

# Or step by step:
./scripts/build.sh          # Build and push Docker images
cd terraform && terraform init && terraform apply
kubectl apply -f k8s/       # Deploy to Kubernetes
```

## 🔐 Security Notes

- **Never commit** real project IDs, passwords, or credentials
- **Always use** environment variables for sensitive configuration
- **Keep** your `.env` file in `.gitignore`
- **Rotate** passwords and access tokens regularly

## 📁 Important Files

- `config/monitor.yaml` - Main configuration (template)
- `.env.example` - Environment variables template
- `.env` - Your actual environment (never commit this!)
- `terraform/terraform.tfvars` - Terraform variables (create from template)

## 🆘 Troubleshooting

### Common Issues

1. **"Project not found"** - Check your GCP project ID
2. **"Image pull error"** - Ensure Docker images are built and pushed
3. **"API not enabled"** - Run the deployment script to enable required APIs

### Getting Help

- Check logs: `kubectl logs -f deployment/api-gateway -n ai-monitor`
- Check status: `kubectl get pods -n ai-monitor`
- Port forward for testing: `kubectl port-forward svc/api-gateway-service 8080:80 -n ai-monitor`

## 🛠️ Development

For development setup, see the main README.md file.