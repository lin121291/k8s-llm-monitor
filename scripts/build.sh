#!/bin/bash

set -e

echo "Building AI Service Monitor..."

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "Docker not running"
    exit 1
fi

# Get project config from centralized configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID=${PROJECT_ID:-$(python3 "$SCRIPT_DIR/get_project_config.py" gcp_project_id)}
REGISTRY=${DOCKER_REGISTRY:-$(python3 "$SCRIPT_DIR/get_project_config.py" docker_registry)}

echo "Building images..."
docker build --platform linux/amd64 -t $REGISTRY/ai-monitor:latest .

# Tag for different services
docker tag $REGISTRY/ai-monitor:latest $REGISTRY/llm-analyzer:latest
docker tag $REGISTRY/ai-monitor:latest $REGISTRY/auto-scaler:latest
docker tag $REGISTRY/ai-monitor:latest $REGISTRY/api-gateway:latest

echo "Build completed!"
echo "Push: docker push $REGISTRY/ai-monitor:latest"