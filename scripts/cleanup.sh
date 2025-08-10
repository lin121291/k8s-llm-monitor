#!/bin/bash

set -e

echo "Cleaning up AI Service Monitor resources..."

# Get project config from centralized configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID=${PROJECT_ID:-$(python3 "$SCRIPT_DIR/get_project_config.py" gcp_project_id)}
NAMESPACE=${NAMESPACE:-$(python3 "$SCRIPT_DIR/get_project_config.py" namespace)}

# Docker cleanup
echo "Cleaning Docker resources..."
[ -f "docker-compose.yml" ] && docker-compose down -v || true
docker images | grep "ai-monitor\|gcr.io.*$PROJECT_ID" | awk '{print $3}' | xargs -r docker rmi -f || true
docker system prune -f

# Kubernetes cleanup
echo "Cleaning Kubernetes resources..."
if command -v kubectl &> /dev/null; then
    kubectl delete namespace $NAMESPACE --ignore-not-found=true
    echo "Deleted $NAMESPACE namespace"
else
    echo "kubectl not found, skipping K8s cleanup"
fi

# Terraform cleanup
echo "Cleaning Terraform resources..."
if [ -d "terraform" ]; then
    cd terraform && terraform destroy -auto-approve || true
    cd ..
fi

echo "Cleanup completed!"