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

-- Made with Bob
