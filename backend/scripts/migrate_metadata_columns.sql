-- Migration script to rename metadata columns to avoid SQLAlchemy reserved word conflict
-- Run this with: psql -U raguser -d linuxone_rag -f backend/scripts/migrate_metadata_columns.sql

BEGIN;

-- Rename metadata column in documents table
ALTER TABLE documents RENAME COLUMN metadata TO doc_metadata;

-- Rename metadata column in chunks table
ALTER TABLE chunks RENAME COLUMN metadata TO chunk_metadata;

-- Rename metadata column in query_logs table
ALTER TABLE query_logs RENAME COLUMN metadata TO query_metadata;

COMMIT;

-- Verify the changes
\d documents
\d chunks
\d query_logs

-- Made with Bob
