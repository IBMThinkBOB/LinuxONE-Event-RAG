#!/bin/bash

# Final pgvector setup script - handles permissions correctly

set -e

echo "=========================================="
echo "Final pgvector Setup for PostgreSQL 15"
echo "=========================================="
echo ""

# Get the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Project directory: $PROJECT_DIR"
echo ""

# Step 1: Grant superuser to raguser (needed for creating extensions)
echo "Step 1: Granting superuser privileges to raguser..."
psql postgres -c "ALTER USER raguser WITH SUPERUSER;" && echo "✓ raguser is now a superuser" || echo "Note: May already be superuser"

echo ""

# Step 2: Create vector extension as postgres superuser
echo "Step 2: Creating vector extension..."
psql postgres -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || echo "Trying in linuxone_rag database..."
psql -U raguser -d linuxone_rag -c "CREATE EXTENSION IF NOT EXISTS vector;" && echo "✓ Vector extension created!" || {
    echo "Creating extension as postgres user..."
    psql postgres -d linuxone_rag -c "CREATE EXTENSION IF NOT EXISTS vector;" && echo "✓ Vector extension created!"
}

echo ""

# Step 3: Verify extension
echo "Step 3: Verifying vector extension..."
psql -U raguser -d linuxone_rag -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

echo ""

# Step 4: Initialize database schema
echo "Step 4: Initializing database schema..."
if [ -f "$PROJECT_DIR/backend/scripts/init_db.sql" ]; then
    psql -U raguser -d linuxone_rag -f "$PROJECT_DIR/backend/scripts/init_db.sql" && echo "✓ Database schema initialized!"
else
    echo "Warning: init_db.sql not found at $PROJECT_DIR/backend/scripts/init_db.sql"
    echo "Creating tables manually..."
    
    psql -U raguser -d linuxone_rag <<EOF
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(500),
    source_type VARCHAR(50) DEFAULT 'redbook',
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_pages INTEGER,
    total_chunks INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Chunks table with embeddings
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),
    token_count INTEGER,
    page_number INTEGER,
    section VARCHAR(255),
    topic VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS chunks_embedding_idx 
ON chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create indexes for filtering
CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks(document_id);
CREATE INDEX IF NOT EXISTS chunks_topic_idx ON chunks(topic);
CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents(filename);

-- Query logs table for analytics
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    retrieved_chunks INTEGER,
    response_time_ms INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);
EOF
    echo "✓ Tables created!"
fi

echo ""

# Step 5: Verify tables
echo "Step 5: Verifying tables..."
psql -U raguser -d linuxone_rag -c "\dt"

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Database is ready! You can now:"
echo ""
echo "1. Activate virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Ingest IBM Redbooks:"
echo "   python backend/scripts/ingest_documents.py --input data/redbooks"
echo ""
echo "3. Start the backend:"
echo "   cd backend && python -m app.main"
echo ""
echo "4. Start the frontend (in another terminal):"
echo "   cd frontend && npm install && npm run dev"
echo ""

# Made with Bob
