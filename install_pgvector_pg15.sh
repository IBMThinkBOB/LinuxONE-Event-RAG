#!/bin/bash

# Compile and install pgvector for PostgreSQL 15

set -e

echo "=========================================="
echo "Compiling pgvector for PostgreSQL 15"
echo "=========================================="
echo ""

# Install build dependencies
echo "Installing build dependencies..."
brew install git

# Clone pgvector
echo "Cloning pgvector repository..."
cd /tmp
rm -rf pgvector
git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
cd pgvector

# Set PostgreSQL 15 path
export PG_CONFIG=/opt/homebrew/opt/postgresql@15/bin/pg_config

# Verify pg_config
echo "Using PostgreSQL at: $($PG_CONFIG --bindir)"
echo "Extension directory: $($PG_CONFIG --sharedir)/extension"
echo ""

# Compile and install
echo "Compiling pgvector..."
make clean
make OPTFLAGS=""

echo "Installing pgvector..."
sudo make install

echo ""
echo "Restarting PostgreSQL..."
brew services restart postgresql@15
sleep 3

echo ""
echo "Creating vector extension..."
psql -U raguser -d linuxone_rag -c "CREATE EXTENSION IF NOT EXISTS vector;" && echo "✓ Success!" || echo "✗ Failed"

echo ""
echo "Verifying installation..."
psql -U raguser -d linuxone_rag -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

echo ""
echo "Running database initialization..."
psql -U raguser -d linuxone_rag -f backend/scripts/init_db.sql

echo ""
echo "=========================================="
echo "pgvector installation complete!"
echo "=========================================="

# Made with Bob
