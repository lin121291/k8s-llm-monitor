#!/bin/bash

set -e

echo "Deploying AI Service Monitor to GCP..."

# Get project config from centralized configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID=${PROJECT_ID:-$(python3 "$SCRIPT_DIR/get_project_config.py" gcp_project_id)}
REGION=${REGION:-us-central1}
NAMESPACE=${NAMESPACE:-$(python3 "$SCRIPT_DIR/get_project_config.py" namespace)}

echo "Project: $PROJECT_ID, Region: $REGION"

# Check dependencies
echo "Checking dependencies..."
for cmd in gcloud terraform kubectl docker; do
    if ! command -v $cmd &> /dev/null; then
        echo "$cmd not found"
        exit 1
    fi
done

# Set GCP project
echo "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable APIs
echo "Enabling APIs..."
gcloud services enable compute.googleapis.com container.googleapis.com servicenetworking.googleapis.com sqladmin.googleapis.com redis.googleapis.com --quiet

# Build and push images (optional)
if [ "$SKIP_BUILD" != "true" ]; then
    echo "Building images..."
    ./scripts/build.sh
    
    echo "Pushing images..."
    REGISTRY=$(python3 "$SCRIPT_DIR/get_project_config.py" docker_registry)
    docker push $REGISTRY/ai-monitor:latest
fi

# Deploy infrastructure
if [ "$SKIP_TERRAFORM" != "true" ]; then
    echo "Generating Terraform variables..."
    python3 "$SCRIPT_DIR/generate_terraform_vars.py"
    
    echo "Deploying infrastructure..."
    cd terraform
    terraform init
    terraform apply -auto-approve
    cd ..
    
    # Get cluster credentials
    echo "Getting cluster credentials..."
    gcloud container clusters get-credentials ai-monitor-dev-gke --region $REGION --project $PROJECT_ID
fi

# Deploy applications
echo "Deploying applications..."
# Deploy in correct order: namespace, RBAC, then applications
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/deployments/ -n $NAMESPACE
kubectl apply -f k8s/services/ -n $NAMESPACE

# Wait for deployments
echo "Waiting for deployments..."
kubectl wait --for=condition=available --timeout=600s deployment --all -n $NAMESPACE
if [ $? -eq 0 ]; then
    echo "All deployments are ready!"
else
    echo "Some deployments may still be starting. Check status with:"
    echo "kubectl get pods -n $NAMESPACE"
fi

echo "Deployment completed!"
echo ""
echo "Access your services:"
echo "kubectl port-forward svc/api-gateway-service 8080:80 -n $NAMESPACE"
echo "Open: http://localhost:8080/docs"