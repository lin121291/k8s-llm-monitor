#!/bin/bash

set -e

echo "Terraform Operations Wrapper for AI Service Monitor"

# Get project config from centralized configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to show usage
usage() {
    echo "Usage: $0 [init|plan|apply|destroy]"
    echo "  init     - Initialize Terraform"
    echo "  plan     - Plan Terraform changes"
    echo "  apply    - Apply Terraform changes"
    echo "  destroy  - Destroy Terraform resources"
    exit 1
}

if [ $# -eq 0 ]; then
    usage
fi

ACTION=$1

# Generate terraform.tfvars from centralized config
echo "Generating Terraform variables from centralized config..."
python3 "$SCRIPT_DIR/generate_terraform_vars.py"

cd "$SCRIPT_DIR/../terraform"

case $ACTION in
    init)
        echo "Initializing Terraform..."
        terraform init
        ;;
    plan)
        echo "Planning Terraform changes..."
        terraform plan
        ;;
    apply)
        echo "Applying Terraform changes..."
        terraform apply -auto-approve
        ;;
    destroy)
        echo "Destroying Terraform resources..."
        terraform destroy -auto-approve
        ;;
    *)
        echo "Unknown action: $ACTION"
        usage
        ;;
esac

echo "Terraform $ACTION completed!"