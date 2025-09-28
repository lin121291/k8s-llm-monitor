# Service Monitor API

A microservices monitoring API built with FastAPI and Kubernetes for demonstration purposes.

## 🚀 Quick Demo

This project showcases:
- **FastAPI** REST API development
- **Docker** containerization
- **Kubernetes** microservices deployment
- **Terraform** infrastructure as code
- **Minikube** local development

## 📋 Prerequisites

### Local Development
- Docker
- Minikube
- kubectl

### Cloud Deployment (Optional)
- Terraform >= 1.0
- GCP Account with billing enabled
- gcloud CLI

## 🏃‍♂️ Quick Start

### Local Development (Minikube)

```bash
# 1. Start minikube
minikube start

# 2. Build and deploy
./scripts/build.sh
kubectl apply -f k8s/

# 3. Check deployment
kubectl get pods -n ai-monitor

# 4. Access API
kubectl port-forward service/api-gateway-service 8080:80 -n ai-monitor &
curl http://localhost:8080/health
```

### Cloud Deployment (GCP)

```bash
# 1. Configure Terraform variables
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your GCP project ID

# 2. Deploy infrastructure
terraform init
terraform plan
terraform apply

# 3. Configure kubectl
gcloud container clusters get-credentials service-monitor-cluster \
  --zone us-central1-a --project your-project-id

# 4. Deploy application
kubectl apply -f ../k8s/

# 5. Get external IP
kubectl get service api-gateway-service -n ai-monitor
```

## 🛠 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │    │  Log Analyzer   │    │   Auto Scaler   │
│   (Port 8080)   │────│   (Port 8000)   │    │   (Port 8001)   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/health` | GET | Health check |
| `/health/detailed` | GET | Detailed system status |
| `/analyze/logs` | POST | Log analysis endpoint |
| `/scale/predict` | POST | Scaling prediction |
| `/services` | GET | List monitored services |
| `/services/{service}/status` | GET | Service status |

## 🧪 Testing

```bash
# Basic health check
curl http://localhost:8080/health

# Detailed health status
curl http://localhost:8080/health/detailed

# Mock log analysis
curl -X POST http://localhost:8080/analyze/logs \
  -H "Content-Type: application/json" \
  -d '{"logs": ["error log example"]}'

# Service list
curl http://localhost:8080/services
```

## 🐳 Docker Commands

```bash
# Build image
docker build -t service-monitor .

# Run locally
docker run -p 8080:8080 service-monitor
```

## ☸️ Kubernetes Commands

```bash
# Deploy all components
kubectl apply -f k8s/

# Check pods
kubectl get pods -n ai-monitor

# Check services
kubectl get services -n ai-monitor

# View logs
kubectl logs -f deployment/api-gateway -n ai-monitor

# Scale deployment
kubectl scale deployment api-gateway --replicas=3 -n ai-monitor

# Clean up
kubectl delete namespace ai-monitor
```

## 📁 Project Structure

```
service-monitor/
├── src/api/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   └── models.py            # Pydantic models
├── k8s/
│   ├── namespace.yaml       # Kubernetes namespace
│   ├── rbac.yaml           # RBAC configuration
│   ├── deployments/        # Application deployments
│   ├── services/           # Service definitions
│   └── configmaps/         # Configuration
├── terraform/
│   ├── main.tf             # Infrastructure resources
│   ├── variables.tf        # Input variables
│   ├── outputs.tf          # Output values
│   ├── providers.tf        # Provider configuration
│   └── terraform.tfvars.example # Example variables
├── scripts/
│   └── build.sh            # Build script for minikube
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🔧 Technologies Used

- **FastAPI** - Modern Python web framework
- **Docker** - Containerization
- **Kubernetes** - Container orchestration
- **Terraform** - Infrastructure as code
- **GCP/GKE** - Cloud platform and managed Kubernetes
- **Minikube** - Local Kubernetes cluster
- **Python 3.11** - Programming language

## 🎯 Demo Points

1. **Microservices Architecture** - Multiple services working together
2. **Infrastructure as Code** - Terraform for reproducible deployments
3. **Container Orchestration** - Kubernetes deployment and scaling
4. **API Design** - RESTful endpoints with proper HTTP methods
5. **Local Development** - Complete development environment setup
6. **Cloud-Native** - GCP/GKE production deployment
7. **Monitoring Concept** - Service health checks and status monitoring

## 🚀 Deployment Options

| Environment | Tool | Use Case |
|-------------|------|----------|
| **Local** | Minikube | Development, Testing, Demo |
| **Cloud** | Terraform + GKE | Production, Staging |

### Quick Cloud Demo
```bash
cd terraform && terraform apply -auto-approve
# Infrastructure ready in ~5 minutes
```

## 📝 Notes

This is a demonstration project showcasing modern containerized application development and deployment practices. The monitoring functionality is simplified for demo purposes.