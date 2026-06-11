#!/bin/bash

# LinuxONE RAG Knowledge Assistant - Setup Script
# This script sets up the development environment

set -e

echo "=========================================="
echo "LinuxONE RAG Knowledge Assistant Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Check if Python 3.10+ is installed
if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    echo "Error: Python 3.10 or higher is required"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install backend dependencies
echo ""
echo "Installing backend dependencies..."
pip install -r backend/requirements.txt

echo ""
echo "=========================================="
echo "Backend setup complete!"
echo "=========================================="
echo ""

# Check Docker
echo "Checking Docker..."
if command -v docker &> /dev/null; then
    echo "Docker is installed: $(docker --version)"
    
    # Check if Docker is running
    if docker info &> /dev/null; then
        echo "Docker is running"
        
        # Start PostgreSQL
        echo ""
        echo "Starting PostgreSQL with pgvector..."
        docker-compose up -d postgres
        
        echo ""
        echo "Waiting for PostgreSQL to be ready..."
        sleep 10
        
        echo "PostgreSQL is ready!"
    else
        echo "Warning: Docker is not running. Please start Docker and run:"
        echo "  docker-compose up -d postgres"
    fi
else
    echo "Warning: Docker is not installed"
    echo "Please install Docker to run PostgreSQL with pgvector"
fi

# Check Ollama
echo ""
echo "Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo "Ollama is installed"
    
    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo "Ollama is running"
        
        # Check if Qwen model is available
        if ollama list | grep -q "qwen"; then
            echo "Qwen model is available"
        else
            echo ""
            echo "Qwen model not found. To install, run:"
            echo "  ollama pull qwen"
        fi
    else
        echo "Warning: Ollama is not running. Please start Ollama:"
        echo "  ollama serve"
    fi
else
    echo "Warning: Ollama is not installed"
    echo "Please install Ollama from: https://ollama.ai"
fi

echo ""
echo "=========================================="
echo "Setup Summary"
echo "=========================================="
echo ""
echo "✓ Python virtual environment created"
echo "✓ Backend dependencies installed"
echo ""
echo "Next steps:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Ensure PostgreSQL is running:"
echo "   docker-compose up -d postgres"
echo ""
echo "3. Ensure Ollama is running with Qwen model:"
echo "   ollama serve"
echo "   ollama pull qwen"
echo ""
echo "4. Ingest your IBM Redbooks:"
echo "   python backend/scripts/ingest_documents.py --input data/redbooks"
echo ""
echo "5. Start the backend server:"
echo "   cd backend && python -m app.main"
echo ""
echo "6. Access the API documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "=========================================="

# Made with Bob
