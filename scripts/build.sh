#!/bin/bash

set -e

echo "Building AI Service Monitor for local minikube..."

# Check if minikube is running
if ! minikube status > /dev/null 2>&1; then
    echo "Minikube not running. Please start with: minikube start"
    exit 1
fi

# Switch to minikube's Docker environment
echo "Switching to minikube Docker environment..."
eval $(minikube docker-env)

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "Docker not available in minikube environment"
    exit 1
fi

echo "Building images in minikube..."
docker build -t local/ai-monitor:latest .

# Tag for different services
echo "Tagging images for different services..."
docker tag local/ai-monitor:latest local/llm-analyzer:latest
docker tag local/ai-monitor:latest local/auto-scaler:latest
docker tag local/ai-monitor:latest local/api-gateway:latest

echo "Build completed!"
echo "Images available in minikube:"
docker images | grep "local/"