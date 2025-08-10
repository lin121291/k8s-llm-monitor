#!/usr/bin/env python3
"""
Script to apply Kubernetes configurations with project-specific values
"""
import os
import sys
import yaml
from pathlib import Path

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from monitor.config import Config

def main():
    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "monitor.yaml"
    config = Config.load_from_file(str(config_path))
    
    k8s_dir = Path(__file__).parent.parent / "k8s"
    
    # Process all YAML files in k8s directory
    for yaml_file in k8s_dir.rglob("*.yaml"):
        print(f"Processing {yaml_file}")
        
        with open(yaml_file, 'r') as f:
            content = f.read()
        
        # Replace placeholders with actual values
        content = content.replace('gcr.io/ai-powered-468303', config.project.docker_registry)
        content = content.replace('namespace: ai-monitor', f'namespace: {config.project.namespace}')
        
        # Apply the configuration
        temp_file = yaml_file.with_suffix('.tmp.yaml')
        with open(temp_file, 'w') as f:
            f.write(content)
        
        # Apply using kubectl
        os.system(f"kubectl apply -f {temp_file}")
        
        # Clean up temp file
        temp_file.unlink()

if __name__ == "__main__":
    main()