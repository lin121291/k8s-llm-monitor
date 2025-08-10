#!/usr/bin/env python3
"""
Helper script to extract project configuration values for shell scripts
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
    if len(sys.argv) < 2:
        print("Usage: python3 get_project_config.py <config_key>", file=sys.stderr)
        sys.exit(1)
    
    config_key = sys.argv[1]
    
    try:
        # Load configuration from file
        config_path = Path(__file__).parent.parent / "config" / "monitor.yaml"
        with open(config_path, 'r') as f:
            content = f.read()
        
        if config_key == "gcp_project_id":
            value = extract_yaml_value(content, 'gcp_project_id') or 'ai-log-468303'
        elif config_key == "docker_registry":
            value = extract_yaml_value(content, 'docker_registry') or 'gcr.io/ai-log-468303'
        elif config_key == "project_name":
            value = extract_yaml_value(content, 'name') or 'AI-log'
        elif config_key == "namespace":
            value = extract_yaml_value(content, 'namespace') or 'ai-monitor'
        else:
            print(f"Unknown config key: {config_key}", file=sys.stderr)
            sys.exit(1)
            
        print(value)
            
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()