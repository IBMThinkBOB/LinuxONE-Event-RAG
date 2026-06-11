#!/bin/bash

# Install PostgreSQL with pgvector locally (macOS)
# This avoids Docker Hub rate limits

set -e

echo "=========================================="
echo "Installing PostgreSQL with pgvector"
echo "=========================================="
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Error: Homebrew is not installed"
    echo "Please install Homebrew first: https://brew.sh"
    exit 1
fi

# Install PostgreSQL
echo "Installing PostgreSQL..."
brew install postgresql@15

# Start PostgreSQL service
echo "Starting PostgreSQL service..."
brew services start postgresql@15

# Wait for PostgreSQL to start
echo "Waiting for PostgreSQL to start..."
sleep 5

# Install pgvector
echo "Installing pgvector extension..."
brew install pgvector

# Create database and user
echo "Creating database and user..."
psql postgres -c "CREATE USER raguser WITH PASSWORD 'ragpassword';" || echo "User may already exist"
psql postgres -c "CREATE DATABASE linuxone_rag OWNER raguser;" || echo "Database may already exist"
psql -U raguser -d linuxone_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run initialization script
echo "Running database initialization..."
psql -U raguser -d linuxone_rag -f backend/scripts/init_db.sql

echo ""
echo "=========================================="
echo "PostgreSQL with pgvector installed!"
echo "=========================================="
echo ""
echo "Database connection details:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: linuxone_rag"
echo "  User: raguser"
echo "  Password: ragpassword"
echo ""
echo "Connection string:"
echo "  postgresql://raguser:ragpassword@localhost:5432/linuxone_rag"
echo ""
echo "To stop PostgreSQL:"
echo "  brew services stop postgresql@15"
echo ""
echo "To start PostgreSQL:"
echo "  brew services start postgresql@15"
echo ""

# Made with Bob
