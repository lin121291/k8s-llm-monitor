#!/bin/bash

set -e

echo "Running tests..."

# Activate virtual environment if exists
[ -d "venv" ] && source venv/bin/activate

# Format code
echo "Formatting code..."
black src/ tests/ || true

# Run tests
echo "Running tests..."
pytest tests/ -v || echo "Some tests failed"

echo "Tests completed!"