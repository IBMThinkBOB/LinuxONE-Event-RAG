# RAG Retrieval Quality Improvement Plan

## Executive Summary

This plan addresses inconsistent retrieval quality in the LinuxONE RAG system. The core issue is that increasing `top_k` sometimes improves answers but often degrades them due to context dilution and lack of relevance filtering.

**Root Causes Identified:**
1. No post-retrieval quality filtering
2. No reranking (embedding similarity ≠ semantic relevance)
3. Coarse chunking (500 tokens) reduces semantic precision
4. No diversity control (redundant chunks waste context)

**Solution:** Three-phase implementation focusing on retrieval robustness, then chunking optimization, then evaluation.

---

## Current System State

### Retrieval Pipeline
- **Location:** [`backend/app/services/retrieval_service.py`](backend/app/services/retrieval_service.py)
- **Method:** Pure pgvector cosine similarity search
- **Issues:**
  - Returns all top_k chunks regardless of quality
  - No filtering, reranking, or diversity control
  - High top_k → context dilution → poor answers

### Chunking Configuration
- **Location:** [`backend/app/config.py`](backend/app/config.py)
- **Current:** `chunk_size=500`, `chunk_overlap=50`
- **Result:** ~512 chunks (too coarse)
- **Target:** 3,000-10,000 chunks with 300-token chunks

### LLM Configuration
- **Location:** [`backend/app/services/llm_service.py`](backend/app/services/llm_service.py)
- **Current:** `max_tokens=600`, `temperature=0.7`
- **Prompt:** Encourages detailed answers but lacks context quality guidance

---

## Phase 1: Core Retrieval Improvements

**Goal:** Make retrieval robust and consistent across all query types, regardless of top_k setting.

### 1.1 Create Reranking Service

**File:** `backend/app/services/reranking_service.py` (new)

**Purpose:** Use cross-encoder model to re-score chunks based on query-chunk semantic match.

**Implementation:**
```python
from sentence_transformers import CrossEncoder
from typing import List, Dict
import logging

class RerankingService:
    """Rerank retrieved chunks using cross-encoder for better relevance."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize reranking service.
        
        Args:
            model_name: Cross-encoder model for reranking
        """
        self.model = CrossEncoder(model_name)
        self.logger = logging.getLogger(__name__)
    
    def rerank_chunks(
        self,
        query: str,
        chunks: List[Dict],
        top_n: int = None
    ) -> List[Dict]:
        """
        Rerank chunks using cross-encoder scores.
        
        Args:
            query: User query
            chunks: List of retrieved chunks with content
            top_n: Optional limit on returned chunks
            
        Returns:
            Reranked chunks with updated scores
        """
        if not chunks:
            return []
        
        # Prepare query-chunk pairs
        pairs = [(query, chunk['content']) for chunk in chunks]
        
        # Get cross-encoder scores
        scores = self.model.predict(pairs)
        
        # Add rerank scores to chunks
        for chunk, score in zip(chunks, scores):
            chunk['rerank_score'] = float(score)
            chunk['original_similarity'] = chunk.get('similarity', 0.0)
        
        # Sort by rerank score
        reranked = sorted(chunks, key=lambda x: x['rerank_score'], reverse=True)
        
        # Limit if specified
        if top_n:
            reranked = reranked[:top_n]
        
        self.logger.info(f"Reranked {len(chunks)} chunks, returning top {len(reranked)}")
        return reranked
```

**Dependencies:** Add to `requirements.txt`:
```
sentence-transformers>=2.2.0
```

**Why This Works:**
- Cross-encoders process query + chunk together → better semantic understanding
- More accurate than bi-encoder embeddings for relevance scoring
- Catches nuanced relevance that embedding similarity misses

---

### 1.2 Implement Adaptive Similarity Threshold Filtering

**File:** `backend/app/services/retrieval_service.py` (modify)

**Purpose:** Filter out low-quality chunks using dynamic thresholds based on score distribution.

**Implementation:**
```python
def filter_by_adaptive_threshold(
    self,
    chunks: List[Dict],
    min_absolute: float = 0.5,
    score_key: str = 'similarity'
) -> List[Dict]:
    """
    Filter chunks using adaptive threshold based on score distribution.
    
    Strategy:
    1. Absolute minimum (e.g., 0.5) - hard floor
    2. Relative threshold - keep chunks within X% of top score
    3. Score gap detection - drop chunks after large gap
    
    Args:
        chunks: List of chunks with scores
        min_absolute: Absolute minimum score threshold
        score_key: Key to use for scoring ('similarity' or 'rerank_score')
        
    Returns:
        Filtered chunks
    """
    if not chunks:
        return []
    
    # Sort by score descending
    sorted_chunks = sorted(chunks, key=lambda x: x.get(score_key, 0), reverse=True)
    
    # Apply absolute minimum
    filtered = [c for c in sorted_chunks if c.get(score_key, 0) >= min_absolute]
    
    if not filtered:
        logger.warning(f"No chunks passed absolute threshold {min_absolute}")
        return []
    
    # Calculate relative threshold (80% of top score)
    top_score = filtered[0].get(score_key, 0)
    relative_threshold = top_score * 0.8
    
    # Apply relative threshold
    filtered = [c for c in filtered if c.get(score_key, 0) >= relative_threshold]
    
    # Detect score gaps (drop after 20% drop)
    final_chunks = [filtered[0]]  # Always keep top chunk
    for i in range(1, len(filtered)):
        prev_score = filtered[i-1].get(score_key, 0)
        curr_score = filtered[i].get(score_key, 0)
        
        # If score drops more than 20%, stop
        if curr_score < prev_score * 0.8:
            logger.info(f"Score gap detected at position {i}: {prev_score:.3f} -> {curr_score:.3f}")
            break
        
        final_chunks.append(filtered[i])
    
    logger.info(f"Filtered {len(chunks)} -> {len(final_chunks)} chunks")
    return final_chunks
```

**Configuration:** Add to `backend/app/config.py`:
```python
# Retrieval filtering
min_similarity_absolute: float = 0.5
similarity_relative_threshold: float = 0.8
enable_adaptive_filtering: bool = True
```

---

### 1.3 Add Diversity/Redundancy Filtering

**File:** `backend/app/services/retrieval_service.py` (modify)

**Purpose:** Remove near-duplicate chunks to maximize context diversity.

**Implementation:**
```python
def filter_by_diversity(
    self,
    chunks: List[Dict],
    similarity_threshold: float = 0.9,
    max_chunks: int = None
) -> List[Dict]:
    """
    Remove redundant chunks using content similarity.
    
    Strategy: Keep chunks that are sufficiently different from already-selected chunks.
    
    Args:
        chunks: List of chunks (should be pre-sorted by relevance)
        similarity_threshold: Max similarity between kept chunks (0-1)
        max_chunks: Optional maximum number of chunks to return
        
    Returns:
        Diverse set of chunks
    """
    if not chunks or len(chunks) <= 1:
        return chunks
    
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    
    # Get embeddings for all chunks
    embeddings = []
    for chunk in chunks:
        if 'embedding' in chunk and chunk['embedding']:
            embeddings.append(chunk['embedding'])
        else:
            # If no embedding stored, skip diversity filtering
            logger.warning("Chunks missing embeddings, skipping diversity filter")
            return chunks[:max_chunks] if max_chunks else chunks
    
    embeddings = np.array(embeddings)
    
    # Calculate pairwise similarities
    similarities = cosine_similarity(embeddings)
    
    # Greedy selection: keep chunks that are different enough
    selected_indices = [0]  # Always keep top chunk
    
    for i in range(1, len(chunks)):
        # Check similarity to all selected chunks
        is_diverse = True
        for j in selected_indices:
            if similarities[i][j] > similarity_threshold:
                is_diverse = False
                logger.debug(f"Chunk {i} too similar to chunk {j} ({similarities[i][j]:.3f})")
                break
        
        if is_diverse:
            selected_indices.append(i)
            
            # Stop if we've reached max_chunks
            if max_chunks and len(selected_indices) >= max_chunks:
                break
    
    diverse_chunks = [chunks[i] for i in selected_indices]
    logger.info(f"Diversity filter: {len(chunks)} -> {len(diverse_chunks)} chunks")
    
    return diverse_chunks
```

**Note:** This requires chunk embeddings to be returned from the database query. Update the SQL query in `search_similar_chunks()` to include `c.embedding`.

---

### 1.4 Refactor Retrieval Service with Multi-Stage Pipeline

**File:** `backend/app/services/retrieval_service.py` (major refactor)

**New Method:**
```python
def search_with_reranking(
    self,
    query: str,
    query_embedding: List[float],
    top_k: int = 10,
    filters: Optional[Dict] = None,
    enable_reranking: bool = True,
    enable_filtering: bool = True,
    enable_diversity: bool = True
) -> Dict:
    """
    Multi-stage retrieval pipeline with reranking and filtering.
    
    Pipeline:
    1. Vector search (retrieve top_k * 2 candidates)
    2. Adaptive similarity filtering
    3. Cross-encoder reranking
    4. Diversity filtering
    5. Return top N high-quality chunks
    
    Args:
        query: User query text
        query_embedding: Query embedding vector
        top_k: Target number of chunks to return
        filters: Optional metadata filters
        enable_reranking: Whether to use cross-encoder reranking
        enable_filtering: Whether to apply adaptive filtering
        enable_diversity: Whether to apply diversity filtering
        
    Returns:
        Dict with chunks and retrieval metrics
    """
    from app.services.reranking_service import RerankingService
    
    metrics = {
        'initial_candidates': 0,
        'after_similarity_filter': 0,
        'after_reranking': 0,
        'final_chunks': 0
    }
    
    # Stage 1: Vector search (retrieve more candidates)
    candidate_k = top_k * 2
    logger.info(f"Stage 1: Retrieving {candidate_k} candidates")
    
    candidates = self.search_similar_chunks(
        query_embedding=query_embedding,
        top_k=candidate_k,
        filters=filters,
        min_similarity=0.0  # No filtering yet
    )
    metrics['initial_candidates'] = len(candidates)
    
    if not candidates:
        return {'chunks': [], 'metrics': metrics}
    
    # Stage 2: Adaptive similarity filtering
    if enable_filtering:
        logger.info("Stage 2: Applying adaptive similarity filter")
        candidates = self.filter_by_adaptive_threshold(
            candidates,
            min_absolute=0.5,
            score_key='similarity'
        )
        metrics['after_similarity_filter'] = len(candidates)
    
    # Stage 3: Cross-encoder reranking
    if enable_reranking and candidates:
        logger.info("Stage 3: Reranking with cross-encoder")
        reranker = RerankingService()
        candidates = reranker.rerank_chunks(query, candidates)
        metrics['after_reranking'] = len(candidates)
    
    # Stage 4: Diversity filtering
    if enable_diversity and candidates:
        logger.info("Stage 4: Applying diversity filter")
        candidates = self.filter_by_diversity(
            candidates,
            similarity_threshold=0.9,
            max_chunks=top_k
        )
    else:
        # Just limit to top_k
        candidates = candidates[:top_k]
    
    metrics['final_chunks'] = len(candidates)
    
    logger.info(f"Retrieval pipeline complete: {metrics}")
    
    return {
        'chunks': candidates,
        'metrics': metrics
    }
```

---

### 1.5 Add Detailed Retrieval Metrics and Logging

**File:** `backend/app/services/retrieval_service.py` (modify)

**Add Metrics Collection:**
```python
def calculate_retrieval_metrics(self, chunks: List[Dict]) -> Dict:
    """
    Calculate quality metrics for retrieved chunks.
    
    Returns:
        Dict with metrics like score distribution, diversity, etc.
    """
    if not chunks:
        return {}
    
    scores = [c.get('rerank_score', c.get('similarity', 0)) for c in chunks]
    
    return {
        'num_chunks': len(chunks),
        'avg_score': sum(scores) / len(scores),
        'min_score': min(scores),
        'max_score': max(scores),
        'score_std': np.std(scores) if len(scores) > 1 else 0.0,
        'score_range': max(scores) - min(scores)
    }
```

---

### 1.6 Update API Routes

**File:** `backend/app/api/routes.py` (modify)

**Update Query Endpoint:**
```python
@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    # ... existing code ...
    
    # Use new multi-stage retrieval
    retrieval_result = retrieval_service.search_with_reranking(
        query=request.query,
        query_embedding=query_embedding,
        top_k=request.top_k,
        filters=request.filters,
        enable_reranking=True,
        enable_filtering=True,
        enable_diversity=True
    )
    
    chunks = retrieval_result['chunks']
    retrieval_metrics = retrieval_result['metrics']
    
    # ... rest of existing code ...
    
    # Add retrieval metrics to response
    return QueryResponse(
        answer=llm_response['answer'],
        sources=sources,
        retrieved_chunks=len(chunks),
        model=llm_response['model'],
        response_time_ms=response_time_ms,
        retrieval_metrics=retrieval_metrics  # New field
    )
```

**Update Schema:** Add to `backend/app/models/schemas.py`:
```python
class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]
    retrieved_chunks: int
    model: str
    response_time_ms: int
    retrieval_metrics: Optional[Dict] = None  # New field
```

---

### 1.7 Testing Phase 1

**Test Queries:**
1. **Broad query:** "What is LinuxONE?" (should work with high top_k)
2. **Specific query:** "How do I configure TLS encryption?" (needs precise chunks)
3. **Multi-aspect query:** "What are the security and performance benefits?" (needs diverse chunks)
4. **Edge case:** "Tell me about quantum computing" (should filter out low-relevance)

**Success Criteria:**
- Increasing top_k from 5 → 10 → 15 should NOT degrade answer quality
- Low-relevance chunks should be filtered out
- Diverse chunks should be selected (no redundancy)
- Retrieval metrics should show consistent quality

---

## Phase 2: Chunking Optimization

**Goal:** Improve semantic precision with smaller, better-bounded chunks.

### 2.1 Update Chunking Configuration

**File:** `backend/app/config.py` (modify)

```python
# RAG Configuration
chunk_size: int = 300  # Changed from 500
chunk_overlap: int = 50  # Unchanged
top_k_results: int = 10  # Increased from 5 (can handle more with filtering)
```

---

### 2.2 Add Sentence-Aware Chunking

**File:** `backend/app/utils/chunking.py` (modify)

**Enhance `chunk_by_sentences()` method:**
- Make it the default chunking strategy
- Ensure chunks don't break mid-sentence
- Respect 300-token limit while maintaining semantic coherence

---

### 2.3 Database Backup

**Script:** `backend/scripts/backup_database.sh` (new)

```bash
#!/bin/bash
# Backup current database before re-ingestion

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/linuxone_rag_${TIMESTAMP}.sql"

mkdir -p $BACKUP_DIR

echo "Backing up database to ${BACKUP_FILE}..."
pg_dump -U raguser -h localhost linuxone_rag > $BACKUP_FILE

echo "Backup complete!"
echo "To restore: psql -U raguser -h localhost linuxone_rag < ${BACKUP_FILE}"
```

---

### 2.4 Re-ingestion Script

**File:** `backend/scripts/reingest_with_new_chunks.sh` (already exists)

**Verify it:**
1. Clears existing chunks
2. Uses updated chunking config
3. Re-processes all documents
4. Generates new embeddings

---

### 2.5 Verify Chunk Count

**Expected Results:**
- Current: ~512 chunks
- Target: 3,000-10,000 chunks
- Calculation: 5 docs × ~200 pages × 3-10 chunks/page = 3,000-10,000

**Verification Query:**
```sql
SELECT COUNT(*) as total_chunks FROM chunks;
SELECT AVG(token_count) as avg_tokens FROM chunks;
SELECT document_id, COUNT(*) as chunks_per_doc FROM chunks GROUP BY document_id;
```

---

### 2.6 Test with New Chunks

**Compare:**
- Answer quality before/after re-chunking
- Retrieval precision (are chunks more focused?)
- Context utilization (less wasted context?)

---

## Phase 3: Evaluation & Monitoring

**Goal:** Systematic evaluation and ongoing quality monitoring.

### 3.1 Test Query Dataset

**File:** `backend/tests/test_queries.json` (new)

```json
{
  "queries": [
    {
      "id": 1,
      "query": "What is LinuxONE?",
      "type": "broad",
      "expected_topics": ["LinuxONE", "IBM Z", "mainframe"],
      "min_chunks": 3
    },
    {
      "id": 2,
      "query": "How do I configure TLS encryption on LinuxONE?",
      "type": "specific",
      "expected_topics": ["TLS", "encryption", "security"],
      "min_chunks": 2
    },
    {
      "id": 3,
      "query": "What are the AI capabilities of LinuxONE?",
      "type": "focused",
      "expected_topics": ["AI", "machine learning", "inference"],
      "min_chunks": 3
    }
  ]
}
```

---

### 3.2 Evaluation Script

**File:** `backend/scripts/evaluate_retrieval.py` (new)

```python
#!/usr/bin/env python3
"""
Evaluate retrieval quality across test queries.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.retrieval_service import RetrievalService
from app.services.embedding_service import get_embedding_service
from app.models.db_connection import SessionLocal
from app.config import get_settings

def evaluate_query(query_data: Dict, retrieval_service, embedding_service) -> Dict:
    """Evaluate a single query."""
    query = query_data['query']
    
    # Get embedding
    query_embedding = embedding_service.embed_text(query)
    
    # Retrieve with new pipeline
    result = retrieval_service.search_with_reranking(
        query=query,
        query_embedding=query_embedding,
        top_k=10
    )
    
    chunks = result['chunks']
    metrics = result['metrics']
    
    # Calculate evaluation metrics
    evaluation = {
        'query_id': query_data['id'],
        'query': query,
        'num_chunks_retrieved': len(chunks),
        'retrieval_metrics': metrics,
        'avg_score': sum(c.get('rerank_score', 0) for c in chunks) / len(chunks) if chunks else 0,
        'min_score': min(c.get('rerank_score', 0) for c in chunks) if chunks else 0,
        'passed': len(chunks) >= query_data.get('min_chunks', 1)
    }
    
    return evaluation

def main():
    """Run evaluation on test queries."""
    settings = get_settings()
    
    # Load test queries
    with open('backend/tests/test_queries.json') as f:
        test_data = json.load(f)
    
    # Initialize services
    embedding_service = get_embedding_service(settings.embedding_model)
    db = SessionLocal()
    retrieval_service = RetrievalService(db)
    
    # Evaluate each query
    results = []
    for query_data in test_data['queries']:
        print(f"\nEvaluating: {query_data['query']}")
        result = evaluate_query(query_data, retrieval_service, embedding_service)
        results.append(result)
        
        print(f"  Chunks: {result['num_chunks_retrieved']}")
        print(f"  Avg Score: {result['avg_score']:.3f}")
        print(f"  Passed: {result['passed']}")
    
    # Summary
    passed = sum(1 for r in results if r['passed'])
    print(f"\n{'='*50}")
    print(f"Evaluation Summary: {passed}/{len(results)} queries passed")
    
    # Save results
    with open('backend/tests/evaluation_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    db.close()

if __name__ == "__main__":
    main()
```

---

### 3.3 Retrieval Quality Dashboard

**File:** `backend/app/api/routes.py` (add endpoint)

```python
@router.get("/retrieval-stats")
async def get_retrieval_stats(db: Session = Depends(get_db)):
    """Get aggregated retrieval quality statistics."""
    
    # Query recent query logs
    recent_queries = db.query(QueryLog).order_by(
        QueryLog.created_at.desc()
    ).limit(100).all()
    
    # Calculate statistics
    stats = {
        'total_queries': len(recent_queries),
        'avg_chunks_retrieved': sum(q.retrieved_chunks for q in recent_queries) / len(recent_queries),
        'avg_response_time_ms': sum(q.response_time_ms for q in recent_queries) / len(recent_queries),
        # Add more metrics as needed
    }
    
    return stats
```

---

### 3.4 Documentation

**File:** `RETRIEVAL_CONFIGURATION.md` (new)

Document:
- Optimal configuration parameters
- When to adjust top_k, thresholds, etc.
- Trade-offs between precision and recall
- Performance considerations

---

### 3.5 Troubleshooting Guide

**File:** `RETRIEVAL_TROUBLESHOOTING.md` (new)

Common issues:
- "Answers are too short" → Check max_tokens, context quality
- "Irrelevant information" → Lower top_k, increase filtering threshold
- "Missing information" → Increase top_k, check chunking
- "Slow responses" → Optimize reranking batch size

---

## Configuration Summary

### Recommended Settings (Post-Implementation)

```python
# backend/app/config.py

# Chunking
chunk_size: int = 300
chunk_overlap: int = 50

# Retrieval
top_k_results: int = 10  # Can be higher with filtering
min_similarity_absolute: float = 0.5
similarity_relative_threshold: float = 0.8
diversity_threshold: float = 0.9

# Reranking
enable_reranking: bool = True
reranking_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# LLM
max_tokens: int = 600
temperature: float = 0.7
```

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ Retrieval quality consistent across different top_k values (5, 10, 15)
- ✅ Low-relevance chunks filtered out (min score > 0.5)
- ✅ No redundant chunks in final context
- ✅ Retrieval metrics logged for all queries

### Phase 2 Success Criteria
- ✅ Chunk count: 3,000-10,000 (from ~512)
- ✅ Average chunk size: ~300 tokens
- ✅ Improved answer precision (more focused responses)
- ✅ No degradation in answer quality

### Phase 3 Success Criteria
- ✅ Evaluation framework running successfully
- ✅ 90%+ test queries pass quality checks
- ✅ Documentation complete
- ✅ Monitoring dashboard functional

---

## Implementation Timeline

**Phase 1:** 2-3 days
- Day 1: Reranking service + filtering logic
- Day 2: Integration + testing
- Day 3: Refinement + validation

**Phase 2:** 1-2 days
- Day 1: Update config + backup + re-ingest
- Day 2: Validation + comparison

**Phase 3:** 1-2 days
- Day 1: Evaluation framework
- Day 2: Documentation + monitoring

**Total:** 4-7 days

---

## Next Steps

1. Review this plan and confirm approach
2. Switch to Code mode to begin Phase 1 implementation
3. Implement and test each phase sequentially
4. Validate improvements with real queries
5. Document final configuration and best practices

---

## Technical Dependencies

### New Python Packages
```
sentence-transformers>=2.2.0  # For cross-encoder reranking
scikit-learn>=1.0.0           # For cosine similarity in diversity filter
numpy>=1.21.0                 # For numerical operations
```

### Files to Create
- `backend/app/services/reranking_service.py`
- `backend/tests/test_queries.json`
- `backend/scripts/evaluate_retrieval.py`
- `backend/scripts/backup_database.sh`
- `RETRIEVAL_CONFIGURATION.md`
- `RETRIEVAL_TROUBLESHOOTING.md`

### Files to Modify
- `backend/app/services/retrieval_service.py` (major refactor)
- `backend/app/api/routes.py` (update query endpoint)
- `backend/app/models/schemas.py` (add retrieval_metrics field)
- `backend/app/config.py` (update chunking + add retrieval config)
- `backend/requirements.txt` (add dependencies)

---

*This plan addresses the core retrieval quality issues while maintaining system stability through phased implementation and thorough testing.*