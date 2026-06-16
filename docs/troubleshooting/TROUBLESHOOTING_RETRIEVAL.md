# RAG Retrieval Troubleshooting Guide

## Overview

This guide helps diagnose and fix common retrieval quality issues in the LinuxONE RAG system.

---

## Quick Diagnostic Checklist

Before diving into specific issues, run this quick check:

```bash
# 1. Check system is running
curl http://localhost:8000/health

# 2. Run evaluation script
python backend/scripts/evaluate_retrieval.py

# 3. Check recent logs
docker logs linuxone-rag-backend --tail 100

# 4. Verify database
psql -U postgres -d rag_db -c "SELECT COUNT(*) FROM document_chunks;"
# Expected: ~762 chunks
```

---

## Common Issues & Solutions

### Issue 1: Answers Are Too Short

**Symptoms:**
- Answers only 1-2 sentences
- Incomplete information
- Truncated mid-sentence

**Diagnosis:**
```python
# Check current max_tokens setting
grep "llm_max_tokens" backend/app/config.py
```

**Root Causes:**
1. `llm_max_tokens` too low (< 1000)
2. Retrieved chunks lack sufficient context
3. LLM prompt doesn't encourage detail

**Solutions:**

**Solution A: Increase max_tokens**
```python
# backend/app/config.py
llm_max_tokens: int = 1500  # or 2000 for complex queries
```

**Solution B: Check retrieval quality**
```bash
# Run test query and check metrics
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is LinuxONE?", "topic_filter": null}'
  
# Look at retrieval_metrics.chunk_count
# Should be 6-10 chunks
```

**Solution C: Verify prompt**
```python
# backend/app/services/llm_service.py
# Ensure prompt includes:
# "Provide a detailed, comprehensive answer..."
```

**Verification:**
- Answer length: 400-800 tokens for simple queries
- Answer length: 1000-1500 tokens for complex queries
- No truncation mid-sentence

---

### Issue 2: Answers Include Irrelevant Information

**Symptoms:**
- Off-topic content in answers
- Mixing unrelated concepts
- Confusing or contradictory information

**Diagnosis:**
```bash
# Check retrieval metrics
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "YOUR_QUERY", "topic_filter": null}' | jq '.retrieval_metrics'

# Look for:
# - Low avg_similarity (< 0.5)
# - High chunk_count (> 12)
# - Low min_similarity (< 0.4)
```

**Root Causes:**
1. Similarity threshold too low
2. Reranking disabled
3. Too many chunks retrieved
4. Poor query embedding

**Solutions:**

**Solution A: Increase similarity threshold**
```python
# backend/app/config.py
min_similarity_absolute: float = 0.6  # from 0.5
similarity_relative_threshold: float = 0.85  # from 0.8
```

**Solution B: Enable/verify reranking**
```python
# backend/app/config.py
enable_reranking: bool = True
enable_adaptive_filtering: bool = True
```

**Solution C: Check reranking service**
```bash
# Test reranking directly
python -c "
from backend.app.services.reranking_service import RerankingService
service = RerankingService()
scores = service.rerank('test query', ['chunk 1', 'chunk 2'])
print(scores)
"
```

**Solution D: Reduce candidate pool**
```python
# backend/app/api/routes.py
# In query endpoint, reduce initial retrieval:
adaptive_top_k = 10  # from 15
candidates = adaptive_top_k * 2  # 20 instead of 30
```

**Verification:**
- avg_similarity > 0.6
- chunk_count: 6-10
- min_similarity > 0.5
- No off-topic content in answer

---

### Issue 3: Missing Important Information

**Symptoms:**
- Incomplete answers
- Key facts omitted
- "I don't have information about..." when docs contain it

**Diagnosis:**
```bash
# Check if chunks exist
psql -U postgres -d rag_db -c "
SELECT COUNT(*), AVG(LENGTH(content)) 
FROM document_chunks 
WHERE content ILIKE '%YOUR_SEARCH_TERM%';
"

# Check retrieval
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "YOUR_QUERY", "topic_filter": null}' | jq '.retrieval_metrics.chunk_count'
```

**Root Causes:**
1. Similarity threshold too high
2. Not enough chunks retrieved
3. Poor query-document semantic match
4. Relevant chunks filtered out

**Solutions:**

**Solution A: Lower similarity threshold**
```python
# backend/app/config.py
min_similarity_absolute: float = 0.4  # from 0.5
similarity_relative_threshold: float = 0.75  # from 0.8
```

**Solution B: Increase candidate pool**
```python
# backend/app/api/routes.py
adaptive_top_k = 20  # from 15
candidates = adaptive_top_k * 2  # 40 candidates
```

**Solution C: Check embedding quality**
```bash
# Test embedding similarity
python -c "
from backend.app.services.embedding_service import EmbeddingService
service = EmbeddingService()
q_emb = service.get_embedding('your query')
d_emb = service.get_embedding('document text')
from numpy import dot
from numpy.linalg import norm
similarity = dot(q_emb, d_emb) / (norm(q_emb) * norm(d_emb))
print(f'Similarity: {similarity}')
"
```

**Solution D: Disable strict filtering temporarily**
```python
# backend/app/config.py
enable_adaptive_filtering: bool = False  # Test without filtering
```

**Verification:**
- chunk_count: 8-12 (more chunks)
- min_similarity: 0.4-0.5 (lower threshold)
- Answer includes expected information
- Re-enable filtering after diagnosis

---

### Issue 4: Redundant/Repetitive Information

**Symptoms:**
- Same information repeated multiple times
- Chunks with nearly identical content
- Verbose, circular answers

**Diagnosis:**
```bash
# Check diversity filtering
grep "enable_diversity_filtering" backend/app/config.py

# Check diversity threshold
grep "diversity_threshold" backend/app/config.py
```

**Root Causes:**
1. Diversity filtering disabled
2. Diversity threshold too high (> 0.95)
3. Document has repetitive content
4. Chunks overlap too much

**Solutions:**

**Solution A: Enable diversity filtering**
```python
# backend/app/config.py
enable_diversity_filtering: bool = True
diversity_threshold: float = 0.9
```

**Solution B: Lower diversity threshold**
```python
# backend/app/config.py
diversity_threshold: float = 0.85  # from 0.9
# More aggressive deduplication
```

**Solution C: Reduce chunk overlap**
```python
# backend/app/config.py
chunk_overlap: int = 30  # from 50
# Then re-ingest documents
```

**Solution D: Check chunk distribution**
```bash
psql -U postgres -d rag_db -c "
SELECT source_document, COUNT(*) 
FROM document_chunks 
GROUP BY source_document;
"
# Should be relatively balanced
```

**Verification:**
- No repeated information in answer
- Chunks are semantically diverse
- Answer is concise and focused

---

### Issue 5: Slow Query Response

**Symptoms:**
- Query takes > 5 seconds
- Timeout errors
- Poor user experience

**Diagnosis:**
```bash
# Check component timing
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "topic_filter": null}' -w "\nTime: %{time_total}s\n"

# Check logs for timing breakdown
docker logs linuxone-rag-backend --tail 50 | grep "took"
```

**Root Causes:**
1. Too many candidates for reranking
2. LLM generation slow
3. Database query slow
4. Reranking model on CPU

**Solutions:**

**Solution A: Reduce candidate pool**
```python
# backend/app/api/routes.py
adaptive_top_k = 10  # from 15
candidates = adaptive_top_k * 1.5  # 15 instead of 30
```

**Solution B: Optimize reranking**
```python
# backend/app/services/reranking_service.py
# Use batch processing (already implemented)
# Consider GPU if available
```

**Solution C: Add database index**
```sql
-- Check existing indexes
\d document_chunks

-- Add index if missing
CREATE INDEX IF NOT EXISTS idx_embedding_vector 
ON document_chunks USING ivfflat (embedding vector_cosine_ops);
```

**Solution D: Reduce max_tokens**
```python
# backend/app/config.py
llm_max_tokens: int = 1200  # from 1500
# Faster generation, slightly shorter answers
```

**Solution E: Cache embeddings**
```python
# backend/app/services/embedding_service.py
# Add caching for common queries (if needed)
from functools import lru_cache

@lru_cache(maxsize=100)
def get_embedding_cached(self, text: str):
    return self.get_embedding(text)
```

**Verification:**
- Total query time < 3 seconds
- Retrieval time < 300ms
- LLM time < 2.5 seconds

---

### Issue 6: Inconsistent Answer Quality

**Symptoms:**
- Same query gives different quality answers
- Some queries work great, others fail
- Unpredictable behavior

**Diagnosis:**
```bash
# Run evaluation script multiple times
for i in {1..3}; do
  echo "Run $i:"
  python backend/scripts/evaluate_retrieval.py | grep "Pass Rate"
done

# Check for variance in pass rate
```

**Root Causes:**
1. LLM temperature too high
2. Filtering thresholds inconsistent
3. Reranking not deterministic
4. Query embedding variance

**Solutions:**

**Solution A: Lower temperature**
```python
# backend/app/config.py
llm_temperature: float = 0.5  # from 0.7
# More deterministic, less creative
```

**Solution B: Ensure all filtering enabled**
```python
# backend/app/config.py
enable_reranking: bool = True
enable_adaptive_filtering: bool = True
enable_diversity_filtering: bool = True
```

**Solution C: Add query preprocessing**
```python
# backend/app/services/retrieval_service.py
def preprocess_query(self, query: str) -> str:
    """Normalize query for consistent embedding"""
    query = query.strip().lower()
    # Remove extra whitespace
    query = ' '.join(query.split())
    return query
```

**Solution D: Set random seed**
```python
# backend/app/services/llm_service.py
# In generate_answer method
payload = {
    "temperature": self.temperature,
    "seed": 42,  # Add for reproducibility
    # ...
}
```

**Verification:**
- Consistent pass rate across runs (±5%)
- Similar answers for same query
- Predictable behavior

---

### Issue 7: Database Connection Issues

**Symptoms:**
- "Connection refused" errors
- "Too many connections" errors
- Intermittent failures

**Diagnosis:**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check connection
psql -U postgres -d rag_db -c "SELECT 1;"

# Check connection count
psql -U postgres -d rag_db -c "
SELECT count(*) FROM pg_stat_activity;
"
```

**Root Causes:**
1. PostgreSQL not running
2. Connection pool exhausted
3. Network issues
4. Wrong credentials

**Solutions:**

**Solution A: Restart PostgreSQL**
```bash
docker restart linuxone-rag-postgres
# Wait 10 seconds
docker logs linuxone-rag-postgres --tail 20
```

**Solution B: Check connection pool**
```python
# backend/app/models/db_connection.py
# Verify pool settings
pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,  # Increase if needed
    # ...
)
```

**Solution C: Verify credentials**
```bash
# Check .env file
cat .env | grep POSTGRES

# Should match docker-compose.yml
```

**Solution D: Check pgvector extension**
```bash
psql -U postgres -d rag_db -c "SELECT * FROM pg_extension WHERE extname='vector';"
# Should return 1 row
```

**Verification:**
- Connection successful
- Queries execute without errors
- No connection pool warnings

---

### Issue 8: Embedding Service Errors

**Symptoms:**
- "Model not found" errors
- Embedding generation fails
- Dimension mismatch errors

**Diagnosis:**
```bash
# Test embedding service
python -c "
from backend.app.services.embedding_service import EmbeddingService
service = EmbeddingService()
emb = service.get_embedding('test')
print(f'Embedding dimension: {len(emb)}')
print(f'Sample values: {emb[:5]}')
"
```

**Root Causes:**
1. Model not downloaded
2. Wrong model name
3. Dimension mismatch with database
4. Memory issues

**Solutions:**

**Solution A: Download model**
```bash
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print('Model downloaded successfully')
"
```

**Solution B: Verify model name**
```python
# backend/app/config.py
embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
# Must match exactly
```

**Solution C: Check dimension**
```bash
# Database dimension
psql -U postgres -d rag_db -c "
SELECT atttypmod FROM pg_attribute 
WHERE attrelid = 'document_chunks'::regclass 
AND attname = 'embedding';
"
# Should be 384

# Model dimension
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print(f'Model dimension: {model.get_sentence_embedding_dimension()}')
"
# Should be 384
```

**Solution D: Increase memory**
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G  # Increase if needed
```

**Verification:**
- Embeddings generate successfully
- Dimension matches database (384)
- No memory errors

---

## Advanced Diagnostics

### Retrieval Pipeline Deep Dive

```python
# backend/scripts/debug_retrieval.py
import sys
sys.path.append('.')

from backend.app.services.retrieval_service import RetrievalService
from backend.app.services.embedding_service import EmbeddingService

# Initialize services
retrieval = RetrievalService()
embedding = EmbeddingService()

# Test query
query = "What is LinuxONE?"
query_embedding = embedding.get_embedding(query)

# Stage 1: Vector search
print("=== Stage 1: Vector Search ===")
candidates = retrieval.search(query_embedding, top_k=30)
print(f"Retrieved {len(candidates)} candidates")
for i, (chunk, score) in enumerate(candidates[:5]):
    print(f"{i+1}. Score: {score:.3f}, Preview: {chunk['content'][:100]}...")

# Stage 2: Adaptive filtering
print("\n=== Stage 2: Adaptive Filtering ===")
filtered = retrieval.filter_by_adaptive_threshold(candidates)
print(f"After filtering: {len(filtered)} chunks")
print(f"Score range: {filtered[-1][1]:.3f} - {filtered[0][1]:.3f}")

# Stage 3: Reranking
print("\n=== Stage 3: Reranking ===")
reranked = retrieval.rerank_chunks(query, filtered)
print(f"After reranking: {len(reranked)} chunks")
for i, (chunk, score) in enumerate(reranked[:5]):
    print(f"{i+1}. Rerank score: {score:.3f}")

# Stage 4: Diversity filtering
print("\n=== Stage 4: Diversity Filtering ===")
final = retrieval.filter_by_diversity(reranked)
print(f"Final chunks: {len(final)}")
print(f"Score range: {final[-1][1]:.3f} - {final[0][1]:.3f}")
```

### Performance Profiling

```python
# backend/scripts/profile_retrieval.py
import time
import sys
sys.path.append('.')

from backend.app.services.retrieval_service import RetrievalService
from backend.app.services.embedding_service import EmbeddingService

retrieval = RetrievalService()
embedding = EmbeddingService()

query = "What is LinuxONE?"

# Profile each stage
stages = {}

start = time.time()
query_embedding = embedding.get_embedding(query)
stages['embedding'] = time.time() - start

start = time.time()
candidates = retrieval.search(query_embedding, top_k=30)
stages['vector_search'] = time.time() - start

start = time.time()
filtered = retrieval.filter_by_adaptive_threshold(candidates)
stages['filtering'] = time.time() - start

start = time.time()
reranked = retrieval.rerank_chunks(query, filtered)
stages['reranking'] = time.time() - start

start = time.time()
final = retrieval.filter_by_diversity(reranked)
stages['diversity'] = time.time() - start

# Print results
print("=== Performance Profile ===")
total = sum(stages.values())
for stage, duration in stages.items():
    pct = (duration / total) * 100
    print(f"{stage:20s}: {duration*1000:6.1f}ms ({pct:5.1f}%)")
print(f"{'TOTAL':20s}: {total*1000:6.1f}ms")
```

---

## Monitoring & Alerts

### Key Metrics to Monitor

```python
# Add to backend/app/api/routes.py
@app.get("/metrics")
async def get_metrics():
    """Return system metrics"""
    return {
        "retrieval": {
            "avg_similarity": get_avg_similarity_last_hour(),
            "avg_chunks": get_avg_chunks_last_hour(),
            "avg_time_ms": get_avg_time_last_hour(),
        },
        "database": {
            "total_chunks": get_total_chunks(),
            "connection_pool": get_pool_status(),
        },
        "system": {
            "memory_mb": get_memory_usage(),
            "cpu_percent": get_cpu_usage(),
        }
    }
```

### Alert Rules

```yaml
# Example alert configuration
alerts:
  - name: Low Retrieval Quality
    condition: avg_similarity < 0.5
    severity: warning
    action: notify_team
    
  - name: Slow Queries
    condition: avg_time_ms > 5000
    severity: warning
    action: notify_team
    
  - name: High Error Rate
    condition: error_rate > 0.05
    severity: critical
    action: page_oncall
    
  - name: Database Connection Issues
    condition: connection_errors > 10
    severity: critical
    action: page_oncall
```

---

## Getting Help

### Information to Provide

When reporting an issue, include:

1. **Query details**
   - Exact query text
   - Expected vs actual behavior
   - Retrieval metrics from response

2. **System state**
   - Output of evaluation script
   - Recent logs (last 100 lines)
   - Configuration settings

3. **Environment**
   - Docker container status
   - Database connection status
   - Available resources (memory, CPU)

4. **Reproduction steps**
   - Minimal example to reproduce
   - Frequency (always, sometimes, rarely)
   - Recent changes made

### Useful Commands

```bash
# Full system check
./backend/scripts/system_check.sh

# Export logs
docker logs linuxone-rag-backend > backend.log 2>&1
docker logs linuxone-rag-postgres > postgres.log 2>&1

# Database dump
pg_dump -U postgres rag_db > rag_db_dump.sql

# Configuration snapshot
cat backend/app/config.py > config_snapshot.txt
cat .env > env_snapshot.txt
```

---

## Prevention Best Practices

1. **Regular Monitoring**
   - Run evaluation script daily
   - Monitor key metrics
   - Review logs for warnings

2. **Configuration Management**
   - Document all changes
   - Test in dev before production
   - Keep backups of working configs

3. **Database Maintenance**
   - Regular backups
   - Vacuum and analyze periodically
   - Monitor index health

4. **Testing**
   - Test new queries before deployment
   - Regression test after changes
   - A/B test configuration changes

5. **Documentation**
   - Keep troubleshooting guide updated
   - Document known issues
   - Share solutions with team

---

*This guide is a living document. Update it as new issues are discovered and solved.*