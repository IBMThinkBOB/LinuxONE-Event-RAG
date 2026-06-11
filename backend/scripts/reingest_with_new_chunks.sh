#!/bin/bash
# Script to clear old data and re-ingest documents with optimized chunking

echo "🔄 Re-ingesting documents with optimized chunking parameters"
echo "============================================================"
echo ""
echo "New parameters:"
echo "  - Chunk size: 300 tokens (was 500)"
echo "  - Chunk overlap: 50 tokens"
echo "  - Top-k results: 3 (was 5)"
echo "  - Max tokens: 600 (was 500)"
echo ""

# Clear existing data
echo "📦 Clearing existing documents and chunks..."
psql -U raguser -d linuxone_rag -c "TRUNCATE TABLE chunks CASCADE;"
psql -U raguser -d linuxone_rag -c "TRUNCATE TABLE documents CASCADE;"
psql -U raguser -d linuxone_rag -c "TRUNCATE TABLE query_logs CASCADE;"

echo "✅ Database cleared"
echo ""

# Re-ingest documents
echo "📥 Starting document ingestion with new chunking parameters..."
echo ""

cd "$(dirname "$0")/../.."
source venv/bin/activate
python backend/scripts/ingest_documents.py --input data/redbooks

echo ""
echo "✅ Re-ingestion complete!"
echo ""

# Show statistics
echo "📊 New database statistics:"
psql -U raguser -d linuxone_rag -c "
SELECT 
    (SELECT COUNT(*) FROM documents) as total_documents,
    (SELECT COUNT(*) FROM chunks) as total_chunks,
    (SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL) as chunks_with_embeddings,
    (SELECT ROUND(AVG(token_count)::numeric, 2) FROM chunks) as avg_chunk_tokens;
"

echo ""
echo "🎉 System ready with optimized parameters!"
echo "   Restart the backend server to use new settings."

# Made with Bob
