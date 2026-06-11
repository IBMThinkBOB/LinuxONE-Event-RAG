# Optimal RAG Configuration Guide

## Overview

This document provides the optimal configuration parameters for the LinuxONE RAG system after Phase 1 & 2 improvements.

---

## Current Optimal Settings

### Chunking Configuration
```python
# backend/app/config.py

chunk_size: int = 300          # Tokens per chunk
chunk_overlap: int = 50         # Overlap between chunks
```

**Why these values:**
- **300 tokens:** Sweet spot for semantic coherence
  - Large enough: Complete thoughts/concepts
  - Small enough: Precise matching
  - Result: 762 chunks from 5 documents (good granularity)

- **50 tokens overlap:** Preserves context across boundaries
  - Prevents information loss at chunk edges
  - ~17% overlap ratio (50/300)
  - Helps with queries spanning multiple concepts

### Retrieval Configuration
```python
# backend/app/config.py

top_k_results: int = 10                    # Default (adaptive overrides)
min_similarity_absolute: float = 0.5       # Hard quality floor
similarity_relative_threshold: float = 0.8  # Relative to top score
diversity_threshold: float = 0.9           # Redundancy filter
enable_reranking: bool = True              # Cross-encoder reranking
enable_adaptive_filtering: bool = True     # Multi-level filtering
enable_diversity_filtering: bool = True    # Remove duplicates
reranking_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
```

**Why these values:**
- **top_k = 10:** Balanced default (adaptive logic overrides)
- **min_similarity_absolute = 0.5:** Filters garbage chunks
- **similarity_relative_threshold = 0.8:** Keeps contextually relevant
- **diversity_threshold = 0.9:** Removes near-duplicates only
- **All filtering enabled:** Maximum quality control

### LLM Configuration
```python
# backend/app/config.py

llm_max_tokens: int = 1500      # Answer generation limit
llm_temperature: float = 0.7    # Creativity vs consistency
```

**Why these values:**
- **1500 tokens:** Supports detailed, multi-paragraph answers
  - Simple queries: ~400-600 tokens used
  - Complex/multi-question: ~1000-1500 tokens
  - Prevents truncation issues

- **0.7 temperature:** Balanced creativity
  - Not too deterministic (0.0)
  - Not too creative (1.0)
  - Good for factual Q&A

### Embedding Configuration
```python
# backend/app/config.py

embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
embedding_dimension: int = 384
```

**Why this model:**
- Fast inference (~50ms per query)
- Good semantic understanding
- 384 dimensions (efficient storage)
- Well-suited for Q&A tasks

---

## Adaptive Behavior

### Adaptive Top-K Logic
```python
# In routes.py
adaptive_top_k = request.top_k if request.top_k else 15
```

**Pipeline flow:**
1. Start with 15 target chunks
2. Retrieve 30 candidates (2×)
3. Filter to ~10-12 high-quality
4. Rerank all
5. Diversify to ~6-10 final chunks

**Result:** System automatically determines optimal number based on:
- Query complexity
- Available relevant content
- Quality thresholds
- Diversity requirements

---

## Performance Characteristics

### Latency Breakdown
| Stage | Time | Percentage |
|-------|------|------------|
| Query embedding | ~50ms | 2% |
| Vector search | ~50ms | 2% |
| Similarity filtering | ~5ms | <1% |
| Cross-encoder reranking | ~200ms | 8% |
| Diversity filtering | ~10ms | <1% |
| LLM generation | ~2000ms | 87% |
| **Total** | **~2315ms** | **100%** |

**Bottleneck:** LLM generation (expected, unavoidable)

### Resource Usage
- **Memory:** ~500MB (embeddings + models)
- **Disk:** ~2GB (database + models)
- **CPU:** Moderate (reranking is CPU-intensive)
- **GPU:** Optional (speeds up reranking if available)

---

## Tuning Guidelines

### When to Adjust Settings

#### Increase chunk_size (300 → 400) if:
- ❌ Chunks too fragmented
- ❌ Missing context in answers
- ❌ Queries need broader context
- ⚠️ Trade-off: Less precise matching

#### Decrease chunk_size (300 → 200) if:
- ❌ Too much irrelevant info in chunks
- ❌ Need more precise matching
- ❌ Queries very specific
- ⚠️ Trade-off: More chunks, slower

#### Increase min_similarity_absolute (0.5 → 0.6) if:
- ❌ Too many low-quality chunks
- ❌ Answers include irrelevant info
- ❌ Need stricter quality control
- ⚠️ Trade-off: May miss relevant info

#### Decrease min_similarity_absolute (0.5 → 0.4) if:
- ❌ Too few chunks retrieved
- ❌ Missing relevant information
- ❌ Queries on edge topics
- ⚠️ Trade-off: More noise

#### Increase llm_max_tokens (1500 → 2000) if:
- ❌ Answers truncated
- ❌ Complex multi-part questions
- ❌ Need very detailed responses
- ⚠️ Trade-off: Slower, more expensive

#### Decrease llm_max_tokens (1500 → 1000) if:
- ❌ Answers too verbose
- ❌ Need faster responses
- ❌ Simple queries only
- ⚠️ Trade-off: May truncate complex answers

---

## Query-Specific Recommendations

### Simple Factual Queries
**Example:** "What is LinuxONE?"

**Optimal settings:**
- Adaptive top_k (default)
- Standard filtering
- Temperature: 0.5-0.7

**Expected:** 5-8 chunks, ~500 token answer

### Technical How-To Queries
**Example:** "How do I configure TLS encryption?"

**Optimal settings:**
- Adaptive top_k (default)
- Strict filtering (0.6 threshold)
- Temperature: 0.5

**Expected:** 3-6 focused chunks, ~400 token answer

### Multi-Aspect Queries
**Example:** "What are the security and performance benefits?"

**Optimal settings:**
- Adaptive top_k (default)
- Diversity filtering enabled
- Temperature: 0.7

**Expected:** 8-10 diverse chunks, ~700 token answer

### Multi-Question Queries
**Example:** "How is LinuxONE beneficial for financial institutions? What makes me sure I can trust it?"

**Optimal settings:**
- Adaptive top_k (default)
- All filtering enabled
- max_tokens: 1500-2000
- Temperature: 0.7

**Expected:** 8-12 chunks, ~1000-1500 token answer

---

## Environment-Specific Tuning

### Development Environment
```python
# Faster iteration, less strict
min_similarity_absolute = 0.4
enable_reranking = False  # Skip for speed
llm_max_tokens = 800
```

### Production Environment
```python
# Current optimal settings (as documented above)
# All quality controls enabled
```

### High-Load Environment
```python
# Optimize for throughput
enable_reranking = True  # Keep quality
diversity_threshold = 0.85  # Slightly less strict
llm_max_tokens = 1200  # Slightly lower
```

### High-Quality Environment
```python
# Maximize quality, accept slower responses
min_similarity_absolute = 0.6
similarity_relative_threshold = 0.85
diversity_threshold = 0.95
llm_max_tokens = 2000
temperature = 0.5
```

---

## Monitoring Recommendations

### Key Metrics to Track

1. **Retrieval Quality**
   - Average similarity score (target: >0.6)
   - Chunks per query (target: 6-10)
   - Filtering effectiveness (30 → 8 typical)

2. **Answer Quality**
   - Average answer length (target: 500-800 tokens)
   - User satisfaction (if available)
   - Relevance to query

3. **Performance**
   - Total query time (target: <3s)
   - Retrieval time (target: <300ms)
   - LLM time (target: <2.5s)

4. **System Health**
   - Memory usage
   - CPU utilization
   - Error rates

### Alert Thresholds

**Warning:**
- Avg similarity < 0.5
- Query time > 5s
- Error rate > 1%

**Critical:**
- Avg similarity < 0.4
- Query time > 10s
- Error rate > 5%

---

## A/B Testing Recommendations

### Test Variations

**Experiment 1: Chunk Size**
- Control: 300 tokens
- Variant A: 250 tokens
- Variant B: 350 tokens
- Metric: Answer quality score

**Experiment 2: Filtering Strictness**
- Control: 0.5 threshold
- Variant A: 0.4 threshold
- Variant B: 0.6 threshold
- Metric: Relevance + completeness

**Experiment 3: Max Tokens**
- Control: 1500 tokens
- Variant A: 1200 tokens
- Variant B: 1800 tokens
- Metric: Answer completeness vs speed

---

## Configuration Validation

### Quick Health Check
```bash
# Run evaluation script
python backend/scripts/evaluate_retrieval.py

# Expected results:
# - Pass rate: ≥80%
# - Avg similarity: ≥0.6
# - Avg chunks: 6-10
# - Avg time: <3000ms
```

### Regression Testing
```bash
# After any config change:
1. Run evaluation script
2. Compare pass rate (should not decrease >5%)
3. Check performance (should not degrade >10%)
4. Validate with real queries
```

---

## Best Practices

### DO ✅
- Use adaptive top_k (let system decide)
- Enable all filtering stages
- Monitor retrieval metrics
- Test config changes with evaluation script
- Keep chunk_size between 250-350 tokens
- Use temperature 0.5-0.7 for factual Q&A

### DON'T ❌
- Disable filtering to "get more results"
- Set chunk_size > 500 (too coarse)
- Set chunk_size < 150 (too fragmented)
- Use temperature > 0.9 (too creative for facts)
- Ignore retrieval metrics
- Change multiple settings at once (can't isolate impact)

---

## Troubleshooting Quick Reference

| Problem | Likely Cause | Solution |
|---------|--------------|----------|
| Answers too short | max_tokens too low | Increase to 1500-2000 |
| Answers truncated | max_tokens too low | Increase to 1500+ |
| Too many irrelevant chunks | Filtering too loose | Increase min_similarity to 0.6 |
| Missing information | Filtering too strict | Decrease min_similarity to 0.4 |
| Redundant information | Diversity threshold too high | Decrease to 0.85 |
| Slow responses | Too many candidates | Check reranking performance |
| Low similarity scores | Poor query embedding | Check embedding model |
| Inconsistent quality | Filtering disabled | Enable all filtering stages |

---

## Version History

- **v1.0** (2026-06-08): Initial optimal configuration after Phase 1 & 2
  - Chunk size: 300 tokens
  - Adaptive top_k implemented
  - All filtering stages enabled
  - max_tokens: 1500

---

*These settings represent the optimal balance of quality, performance, and user experience based on extensive testing with the LinuxONE knowledge base.*