# Phase 5: Retrieval Stability - Smart Failure Handling

## Objective

**CRITICAL**: Distinguish between "no relevant information" (should fail) vs "weak but relevant match" (should succeed).

**Philosophy**:
- ✅ Weak but relevant match → Succeed with low confidence
- ❌ Truly irrelevant query → Fail gracefully
- 🎯 Smart threshold: similarity > 0.3 = relevant enough to try

---

## Problem Analysis

### Current Failure Points

1. **routes.py:75-79** - Hard failure when no chunks returned:
```python
if not chunks:
    raise HTTPException(
        status_code=404,
        detail="No relevant information found in the knowledge base"
    )
```

2. **retrieval_service.py:373-375** - Returns empty when no candidates:
```python
if not candidates:
    logger.warning("No candidates retrieved from vector search")
    return {'chunks': [], 'metrics': metrics}
```

3. **retrieval_service.py:394-396** - Returns empty after filtering:
```python
if not candidates:
    logger.warning("No candidates passed similarity filter")
    return {'chunks': [], 'metrics': metrics}
```

### Why Current Approach Is Problematic

**Current behavior**: Fails if filtered chunks = 0

**Problems**:
1. ❌ Fails on weak but relevant matches (e.g., similarity 0.35)
2. ❌ Doesn't distinguish "no match" from "weak match"
3. ✅ Correctly fails on truly irrelevant queries (but by accident)

**What we need**: Smart threshold that distinguishes relevance

---

## Solution Strategy

### Core Principle

**Use minimum similarity threshold to determine relevance**

### Smart Threshold System

```
Query: "What is LinuxONE?"
  → Top similarity: 0.85 → ✅ SUCCEED (high confidence)

Query: "How do I configure TLS?"
  → Top similarity: 0.42 → ✅ SUCCEED (low confidence, but relevant)

Query: "What is the best Call of Duty game?"
  → Top similarity: 0.15 → ❌ FAIL (truly irrelevant)
```

### Relevance Threshold

**Minimum similarity for relevance: 0.3**

- **> 0.6**: High confidence (strong match)
- **0.4-0.6**: Medium confidence (decent match)
- **0.3-0.4**: Low confidence (weak but relevant)
- **< 0.3**: No relevance (should fail)

**Rationale**:
- Similarity 0.3 = some semantic overlap exists
- Below 0.3 = query is about different domain entirely
- Prevents "Call of Duty" queries from succeeding
- Allows weak LinuxONE matches to succeed

### Confidence Levels

- **high**: avg_similarity > 0.6 (strong match)
- **medium**: avg_similarity 0.4-0.6 (decent match)
- **low**: avg_similarity 0.3-0.4 (weak but relevant)
- **none**: avg_similarity < 0.3 (irrelevant - FAIL)

---

## Implementation Plan

### Step 1: Update Retrieval Service (Critical)

**File**: `backend/app/services/retrieval_service.py`

**Changes**:

1. **Remove early returns** - Never return empty chunks
2. **Add fallback logic** - If filtering removes all chunks, use unfiltered
3. **Track confidence** - Mark when fallback was triggered

**New method to add**:

```python
def _check_relevance_threshold(
    self,
    chunks: List[Dict],
    min_relevance: float = 0.3
) -> tuple[bool, float]:
    """
    Check if top chunks meet minimum relevance threshold.
    
    Args:
        chunks: Retrieved chunks with similarity scores
        min_relevance: Minimum similarity to consider relevant
        
    Returns:
        (is_relevant, top_similarity)
    """
    if not chunks:
        return False, 0.0
    
    # Check top chunk similarity
    top_similarity = chunks[0].get('similarity', 0.0)
    is_relevant = top_similarity >= min_relevance
    
    logger.info(
        f"Relevance check: top_similarity={top_similarity:.3f}, "
        f"threshold={min_relevance}, relevant={is_relevant}"
    )
    
    return is_relevant, top_similarity
```

**Update search_with_reranking**:

```python
def search_with_reranking(
    self,
    query: str,
    query_embedding: List[float],
    top_k: int = 10,
    filters: Optional[Dict] = None,
    enable_reranking: bool = True,
    enable_filtering: bool = True,
    enable_diversity: bool = True,
    min_absolute: float = 0.5,
    relative_threshold: float = 0.8,
    diversity_threshold: float = 0.9,
    min_relevance: float = 0.3  # NEW: Minimum similarity for relevance
) -> Dict:
    """Multi-stage retrieval with smart relevance checking."""
    
    metrics = {
        'initial_candidates': 0,
        'after_similarity_filter': 0,
        'after_reranking': 0,
        'final_chunks': 0,
        'confidence_level': 'none',
        'top_similarity': 0.0,
        'pipeline_stages': []
    }
    
    # Stage 1: Vector search
    candidate_k = max(top_k * 2, 10)
    candidates = self.search_similar_chunks(
        query_embedding=query_embedding,
        top_k=candidate_k,
        filters=filters,
        min_similarity=0.0  # No filtering yet
    )
    
    # Check if we have any candidates at all
    if not candidates:
        logger.error("CRITICAL: No chunks in database or vector search failed")
        return {
            'chunks': [],
            'metrics': {**metrics, 'confidence_level': 'none'}
        }
    
    metrics['initial_candidates'] = len(candidates)
    
    # CRITICAL: Check relevance threshold BEFORE filtering
    is_relevant, top_sim = self._check_relevance_threshold(
        candidates,
        min_relevance=min_relevance
    )
    metrics['top_similarity'] = top_sim
    
    # If top match is below relevance threshold, fail gracefully
    if not is_relevant:
        logger.warning(
            f"Query not relevant: top_similarity={top_sim:.3f} < {min_relevance}"
        )
        return {
            'chunks': [],
            'metrics': {**metrics, 'confidence_level': 'none'}
        }
    
    # Query is relevant, proceed with filtering
    logger.info(f"Query is relevant: top_similarity={top_sim:.3f}")
    
    # Stage 2: Adaptive filtering
    if enable_filtering:
        filtered = self.filter_by_adaptive_threshold(
            candidates,
            min_absolute=min_absolute,
            relative_threshold=relative_threshold,
            score_key='similarity'
        )
        
        # If filtering removed everything but query is relevant, use top chunks
        if not filtered:
            logger.warning(
                f"Filtering removed all chunks but query is relevant "
                f"(top_sim={top_sim:.3f}), using top {top_k} unfiltered"
            )
            filtered = candidates[:top_k]
        
        candidates = filtered
        metrics['after_similarity_filter'] = len(candidates)
    
    # Stage 3: Reranking
    if enable_reranking and candidates:
        try:
            reranker = get_reranking_service()
            candidates = reranker.rerank_chunks(query, candidates)
            metrics['after_reranking'] = len(candidates)
        except Exception as e:
            logger.error(f"Reranking failed: {e}, continuing without")
    
    # Stage 4: Diversity filtering with hard limit
    if enable_diversity and candidates:
        safe_max = min(top_k, 5)
        diverse = self.filter_by_diversity(
            candidates,
            similarity_threshold=diversity_threshold,
            max_chunks=safe_max
        )
        
        # Ensure minimum 3 chunks if available
        if len(diverse) < 3 and len(candidates) >= 3:
            logger.warning("Diversity filter too aggressive, keeping top 3")
            diverse = candidates[:3]
        
        candidates = diverse
    else:
        candidates = candidates[:5]
    
    # Calculate confidence based on average similarity
    if candidates:
        avg_sim = sum(c.get('similarity', 0) for c in candidates) / len(candidates)
        if avg_sim >= 0.6:
            metrics['confidence_level'] = 'high'
        elif avg_sim >= 0.4:
            metrics['confidence_level'] = 'medium'
        elif avg_sim >= 0.3:
            metrics['confidence_level'] = 'low'
        else:
            metrics['confidence_level'] = 'none'
    
    metrics['final_chunks'] = len(candidates)
    
    logger.info(
        f"Retrieval complete: {len(candidates)} chunks, "
        f"confidence={metrics['confidence_level']}, "
        f"top_sim={top_sim:.3f}, avg_sim={avg_sim:.3f}"
    )
    
    return {
        'chunks': candidates,
        'metrics': metrics
    }
```

---

### Step 2: Update API Routes (Critical)

**File**: `backend/app/api/routes.py`

**Smart failure handling**:

```python
# OLD (lines 75-79):
if not chunks:
    raise HTTPException(
        status_code=404,
        detail="No relevant information found in the knowledge base"
    )

# NEW:
# Check if query was truly irrelevant (confidence = 'none')
confidence = retrieval_metrics.get('confidence_level', 'none')
top_similarity = retrieval_metrics.get('top_similarity', 0.0)

if not chunks or confidence == 'none':
    # Query is truly irrelevant (e.g., "What is Call of Duty?")
    logger.warning(
        f"Query not relevant to knowledge base: "
        f"top_similarity={top_similarity:.3f} < 0.3"
    )
    raise HTTPException(
        status_code=404,
        detail="No relevant information found in the knowledge base for this query"
    )

# Query is relevant (even if weak), proceed with generation
logger.info(
    f"Retrieval confidence: {confidence}, "
    f"top_similarity: {top_similarity:.3f}, "
    f"chunks: {len(chunks)}"
)
```

---

### Step 3: Update Response Schema (Optional but Recommended)

**File**: `backend/app/models/schemas.py`

**Add confidence field**:

```python
class QueryResponse(BaseModel):
    """Response from query endpoint."""
    answer: str
    sources: List[SourceInfo]
    response_time: float
    retrieval_metrics: Optional[Dict] = None
    confidence_level: Optional[str] = None  # NEW: 'high', 'medium', 'low'
    fallback_used: Optional[bool] = None    # NEW: True if fallback triggered
```

**Update routes.py to include**:

```python
return QueryResponse(
    answer=llm_response['answer'],
    sources=sources,
    response_time=response_time,
    retrieval_metrics=retrieval_metrics,
    confidence_level=retrieval_metrics.get('confidence_level'),  # NEW
    fallback_used=retrieval_metrics.get('fallback_triggered')    # NEW
)
```

---

### Step 4: Update LLM Prompt for Low Confidence

**File**: `backend/app/services/llm_service.py`

**Modify _build_prompt to handle low confidence**:

```python
def _build_prompt(
    self, 
    query: str, 
    context_chunks: List[Dict],
    confidence_level: str = 'high'
) -> str:
    """Build prompt with confidence-aware instructions."""
    
    # Format context
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        doc_title = chunk.get('document', {}).get('title', 'Unknown')
        page_num = chunk.get('page_number', 'N/A')
        content = chunk.get('content', '')
        context_parts.append(
            f"[Source {i}: {doc_title}, Page {page_num}]\n{content}"
        )
    
    context_text = "\n\n".join(context_parts) if context_parts else "No specific context available."
    
    # Adjust instructions based on confidence
    if confidence_level == 'low':
        confidence_note = """
Note: The retrieved context may have limited relevance to your question. 
If the context doesn't directly answer the question, provide a general answer 
based on the available information and clearly indicate what information is missing.
"""
    else:
        confidence_note = ""
    
    prompt = f"""You are a knowledgeable assistant specializing in LinuxONE and IBM technologies.
Answer the user's question based on the provided context from IBM Redbooks.

Context from IBM Redbooks:
{context_text}

Question: {query}

Instructions:
- Provide a detailed, comprehensive answer with multiple paragraphs when appropriate
- Base your answer strictly on the context provided above
- If the context doesn't contain enough information to fully answer the question, acknowledge this clearly
- Include relevant technical details, examples, and explanations from the context
- Structure your answer logically with clear explanations
- Cite sources by mentioning the document name when referencing specific information
- Aim for completeness and clarity rather than brevity
{confidence_note}

Answer:"""
    
    return prompt
```

---

## Testing Strategy

### Test Cases

1. **High confidence query** (strong match)
   - Query: "What is LinuxONE?"
   - Expected: ✅ SUCCEED, confidence='high', top_sim > 0.6

2. **Medium confidence query** (decent match)
   - Query: "How do I configure TLS encryption?"
   - Expected: ✅ SUCCEED, confidence='medium', top_sim 0.4-0.6

3. **Low confidence query** (weak but relevant)
   - Query: "What are the performance benchmarks?"
   - Expected: ✅ SUCCEED, confidence='low', top_sim 0.3-0.4

4. **Irrelevant query** (should fail)
   - Query: "What is the best Call of Duty game?"
   - Expected: ❌ FAIL (404), confidence='none', top_sim < 0.3

5. **Typo query** (should still work)
   - Query: "What is LnuxONE?" (typo)
   - Expected: ✅ SUCCEED, confidence='medium/high', semantic match

6. **Edge domain query** (borderline)
   - Query: "What is quantum computing?"
   - Expected: ❌ FAIL (404), top_sim < 0.3 (not in LinuxONE docs)

### Success Criteria

✅ Relevant queries (sim > 0.3) always succeed
❌ Irrelevant queries (sim < 0.3) always fail with 404
✅ Confidence level accurately reflects similarity
✅ Weak but relevant matches (0.3-0.4) produce answers
✅ Truly irrelevant queries fail gracefully
✅ Logging shows top_similarity for debugging

---

## Monitoring & Alerts

### Metrics to Track

1. **Fallback rate**: % of queries triggering fallback
   - Target: <10%
   - Alert if: >25%

2. **Confidence distribution**:
   - High: >60%
   - Medium: 20-30%
   - Low: <10%

3. **Average similarity scores**:
   - Target: >0.6
   - Alert if: <0.4

### Logging

```python
logger.info(
    f"Query: {query[:50]}... | "
    f"Chunks: {len(chunks)} | "
    f"Confidence: {confidence} | "
    f"Fallback: {fallback} | "
    f"Avg similarity: {avg_sim:.3f}"
)
```

---

## Rollback Plan

If issues arise:

1. **Revert routes.py**: Add back the hard failure check
2. **Revert retrieval_service.py**: Remove fallback logic
3. **Monitor**: Check if 404 errors return

---

## Benefits

✅ **Reliability**: System never appears "broken"
✅ **User experience**: Always get an answer
✅ **Transparency**: Confidence level shows quality
✅ **Debugging**: Fallback logging helps identify issues
✅ **Graceful degradation**: Weak answer > no answer

---

## Implementation Order

1. ✅ Add `_ensure_minimum_chunks` method
2. ✅ Update `search_with_reranking` with fallback logic
3. ✅ Remove hard failure in `routes.py`
4. ✅ Add confidence logging
5. ⚠️ (Optional) Update response schema
6. ⚠️ (Optional) Update LLM prompt for low confidence
7. ✅ Test with edge cases

---

*This ensures the system is robust and user-friendly, never failing when data exists.*