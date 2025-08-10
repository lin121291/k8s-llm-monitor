#!/usr/bin/env python3
"""
Generate terraform.tfvars from centralized configuration
"""
import os
import sys
import re
from pathlib import Path

def extract_yaml_value(content, key):
    """Simple YAML value extractor for basic key: value pairs"""
    pattern = f'{key}:\\s*"([^"]*)"'
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    return None

def main():
    try:
        # Load configuration from file
        config_path = Path(__file__).parent.parent / "config" / "monitor.yaml"
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Extract project configuration
        project_id = extract_yaml_value(content, 'gcp_project_id') or 'ai-log-468303'
        
        # Generate terraform.tfvars content
        tfvars_content = f"""# AI Service Monitor - Terraform Variables
# Generated automatically from config/monitor.yaml

project_id  = "{project_id}"
region      = "us-central1"
zone        = "us-central1-a"
environment = "dev"
"""
        
        # Write to terraform.tfvars
        terraform_dir = Path(__file__).parent.parent / "terraform"
        tfvars_path = terraform_dir / "terraform.tfvars"
        
        with open(tfvars_path, 'w') as f:
            f.write(tfvars_content)
        
        print(f"Generated {tfvars_path} with project_id: {project_id}")
            
    except Exception as e:
        print(f"Error generating terraform.tfvars: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()