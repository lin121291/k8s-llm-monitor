#!/bin/bash

set -e

echo "Setting up development environment..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv || python -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Start services
echo "Starting services..."
docker-compose up -d

echo "Setup completed!"
echo ""
echo "Next steps:"
echo "  source venv/bin/activate"
echo "  python -m src.api.main"
echo "  Open: http://localhost:8080/docs"