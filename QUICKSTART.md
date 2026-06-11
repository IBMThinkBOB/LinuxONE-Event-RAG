# Quick Start Guide

Get the LinuxONE RAG Knowledge Assistant up and running in minutes!

## Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Ollama with Qwen model
- IBM Redbooks PDFs (already in `data/redbooks/`)

## Step 1: Run Setup Script

```bash
./setup.sh
```

This will:
- Create Python virtual environment
- Install all dependencies
- Start PostgreSQL with pgvector
- Check Ollama availability

## Step 2: Activate Virtual Environment

```bash
source venv/bin/activate
```

## Step 3: Verify Services

### Check PostgreSQL
```bash
docker-compose ps
```

Should show `linuxone_rag_db` running.

### Check Ollama
```bash
curl http://localhost:11434/api/tags
```

Should return list of models including `qwen`.

## Step 4: Ingest IBM Redbooks

```bash
python backend/scripts/ingest_documents.py --input data/redbooks
```

This will:
- Process all PDFs in `data/redbooks/`
- Extract text and chunk it
- Generate embeddings
- Store in PostgreSQL

**Expected output:**
```
Processing document: AIForLinuxOnIBMZ.pdf
Extracting text from PDF...
Extracting topics...
Created document record with ID: 1
Created 245 chunks
Generating embeddings...
Storing chunks in database...
Successfully ingested AIForLinuxOnIBMZ.pdf
  - Pages: 156
  - Chunks: 245
  - Topics: linuxone, ai, machine learning
```

**Time estimate:** ~5-10 minutes for all 5 Redbooks

## Step 5: Start Backend Server

```bash
cd backend
python -m app.main
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 6: Test the API

### Open API Documentation
Visit: http://localhost:8000/docs

### Test Health Check
```bash
curl http://localhost:8000/api/health
```

### Test Query (via curl)
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I optimize AI workloads on LinuxONE?",
    "top_k": 5
  }'
```

### Test Query (via Python)
```python
import requests

response = requests.post(
    "http://localhost:8000/api/query",
    json={
        "query": "What are the security features of LinuxONE?",
        "top_k": 5
    }
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"\nSources:")
for source in result['sources']:
    print(f"  - {source['title']} (Page {source['page_number']})")
```

## Step 7: View Statistics

```bash
curl http://localhost:8000/api/statistics
```

Expected response:
```json
{
  "total_documents": 5,
  "total_chunks": 1247,
  "chunks_with_embeddings": 1247,
  "avg_chunk_tokens": 487.3
}
```

## Common Issues & Solutions

### Issue: PostgreSQL not starting
```bash
# Check logs
docker-compose logs postgres

# Restart
docker-compose restart postgres
```

### Issue: Ollama not responding
```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama
ollama serve

# Pull Qwen model if missing
ollama pull qwen
```

### Issue: Import errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r backend/requirements.txt
```

### Issue: Embedding model download slow
The first time you run ingestion, SentenceTransformers will download the model (~90MB). This is normal and only happens once.

### Issue: Out of memory during ingestion
Reduce batch size in the ingestion script:
```python
embeddings = embedding_service.embed_batch(chunk_texts, batch_size=16)  # Reduced from 32
```

## Example Queries to Try

1. **AI Workloads:**
   - "How do I deploy AI models on LinuxONE?"
   - "What AI frameworks are supported on LinuxONE?"

2. **Security:**
   - "What are the security features of LinuxONE?"
   - "How does LinuxONE handle encryption?"

3. **Performance:**
   - "How can I optimize performance on LinuxONE?"
   - "What are the scalability features?"

4. **Resilience:**
   - "How does LinuxONE ensure high availability?"
   - "What disaster recovery options are available?"

## Next Steps

### Add More Documents
```bash
# Add new PDFs to data/redbooks/
cp /path/to/new.pdf data/redbooks/

# Ingest the new document
python backend/scripts/ingest_documents.py --input data/redbooks/new.pdf
```

### Build Frontend
See `frontend/README.md` for React frontend setup instructions.

### Deploy to Production
See `LINUXONE_DEPLOYMENT.md` for enterprise deployment guide.

## Monitoring

### Check Database Size
```bash
docker exec linuxone_rag_db psql -U raguser -d linuxone_rag -c "
SELECT 
    pg_size_pretty(pg_database_size('linuxone_rag')) as db_size,
    (SELECT COUNT(*) FROM documents) as documents,
    (SELECT COUNT(*) FROM chunks) as chunks;
"
```

### View Recent Queries
```bash
docker exec linuxone_rag_db psql -U raguser -d linuxone_rag -c "
SELECT query_text, response_time_ms, timestamp 
FROM query_logs 
ORDER BY timestamp DESC 
LIMIT 10;
"
```

## Stopping Services

```bash
# Stop backend (Ctrl+C in terminal)

# Stop PostgreSQL
docker-compose down

# Stop Ollama (if running in terminal)
# Ctrl+C in Ollama terminal
```

## Clean Restart

```bash
# Stop all services
docker-compose down -v  # -v removes volumes (deletes data!)

# Remove virtual environment
rm -rf venv

# Start fresh
./setup.sh
```

---

**Need Help?**
- Check logs: `docker-compose logs -f postgres`
- API docs: http://localhost:8000/docs
- Full documentation: See `README.md` and `ARCHITECTURE.md`