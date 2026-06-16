# Retrieval Pipeline Architecture

## Current vs. Improved Architecture

### Current Architecture (Problematic)

```mermaid
graph LR
    A[User Query] --> B[Generate Embedding]
    B --> C[pgvector Search]
    C --> D[Return top_k chunks]
    D --> E[LLM Generation]
    E --> F[Answer]
    
    style D fill:#ff6b6b
    style E fill:#ff6b6b
```

**Problems:**
- No quality filtering
- All top_k chunks passed to LLM regardless of relevance
- High top_k → context dilution → poor answers

---

### Improved Architecture (Phase 1)

```mermaid
graph TB
    A[User Query] --> B[Generate Embedding]
    B --> C[pgvector Search<br/>top_k × 2 candidates]
    
    C --> D{Adaptive<br/>Similarity Filter}
    D -->|Score > threshold| E[Filtered Candidates]
    D -->|Score < threshold| X1[Discard]
    
    E --> F[Cross-Encoder<br/>Reranking]
    F --> G[Reranked by<br/>Semantic Relevance]
    
    G --> H{Diversity<br/>Filter}
    H -->|Unique content| I[Final top_k chunks]
    H -->|Redundant| X2[Discard]
    
    I --> J[LLM Generation<br/>with Quality Context]
    J --> K[High-Quality Answer]
    
    style D fill:#51cf66
    style F fill:#51cf66
    style H fill:#51cf66
    style I fill:#51cf66
    style J fill:#51cf66
    style K fill:#51cf66
```

**Improvements:**
- Multi-stage quality filtering
- Reranking for better relevance
- Diversity control
- Robust across different top_k values

---

## Detailed Pipeline Stages

### Stage 1: Vector Search (Candidate Retrieval)

```mermaid
graph LR
    A[Query Embedding<br/>384 dimensions] --> B[pgvector<br/>Cosine Similarity]
    B --> C[Top 2×k candidates<br/>Cast wide net]
    
    C --> D[Candidate Pool<br/>e.g., 20 chunks for top_k=10]
```

**Purpose:** Retrieve more candidates than needed to allow filtering

**Configuration:**
- Retrieve: `top_k × 2` chunks
- No minimum threshold yet
- Fast vector search using pgvector index

---

### Stage 2: Adaptive Similarity Filtering

```mermaid
graph TB
    A[Candidate Chunks] --> B{Absolute<br/>Threshold}
    B -->|Score ≥ 0.5| C[Pass]
    B -->|Score < 0.5| X1[Reject]
    
    C --> D{Relative<br/>Threshold}
    D -->|Score ≥ 80% of top| E[Pass]
    D -->|Score < 80% of top| X2[Reject]
    
    E --> F{Score Gap<br/>Detection}
    F -->|Gap < 20%| G[Keep]
    F -->|Gap ≥ 20%| X3[Stop here]
    
    G --> H[Filtered Candidates]
```

**Three-Level Filtering:**

1. **Absolute Minimum** (0.5)
   - Hard floor for quality
   - Prevents garbage chunks

2. **Relative Threshold** (80% of top score)
   - Adapts to query difficulty
   - Keeps contextually relevant chunks

3. **Score Gap Detection** (20% drop)
   - Stops at natural quality boundary
   - Prevents including marginal chunks

**Example:**
```
Chunk 1: 0.92 ✓ (top score)
Chunk 2: 0.89 ✓ (within 80% = 0.736)
Chunk 3: 0.85 ✓ (within threshold)
Chunk 4: 0.67 ✗ (>20% drop from 0.85)
Chunk 5: 0.65 ✗ (rejected)
```

---

### Stage 3: Cross-Encoder Reranking

```mermaid
graph LR
    A[Filtered Chunks] --> B[Cross-Encoder Model]
    C[Query] --> B
    
    B --> D[Semantic<br/>Relevance Scores]
    D --> E[Re-sort by<br/>Rerank Score]
    E --> F[Reranked Chunks]
```

**How It Works:**

**Bi-Encoder (Current):**
```
Query → Embedding A
Chunk → Embedding B
Similarity = cosine(A, B)
```
- Fast but less accurate
- Embeddings computed independently

**Cross-Encoder (New):**
```
[Query + Chunk] → Model → Relevance Score
```
- Slower but much more accurate
- Processes query and chunk together
- Captures nuanced semantic relationships

**Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Trained on MS MARCO passage ranking
- Optimized for relevance scoring
- ~80MB model size

---

### Stage 4: Diversity Filtering

```mermaid
graph TB
    A[Reranked Chunks] --> B[Chunk 1<br/>Always Keep]
    
    B --> C{Chunk 2<br/>Similar to 1?}
    C -->|Similarity < 0.9| D[Keep Chunk 2]
    C -->|Similarity ≥ 0.9| X1[Discard]
    
    D --> E{Chunk 3<br/>Similar to 1 or 2?}
    E -->|All < 0.9| F[Keep Chunk 3]
    E -->|Any ≥ 0.9| X2[Discard]
    
    F --> G[Continue until<br/>top_k reached]
    G --> H[Diverse Chunk Set]
```

**Purpose:** Maximize information density

**Strategy:**
- Greedy selection (keep best first)
- Check similarity to all selected chunks
- Threshold: 0.9 (very similar = redundant)

**Example:**
```
Chunk A: "LinuxONE is a secure mainframe..." ✓
Chunk B: "LinuxONE provides security..." ✗ (too similar to A)
Chunk C: "AI workloads on LinuxONE..." ✓ (different topic)
```

---

## Data Flow Example

### Query: "How do I configure TLS encryption on LinuxONE?"

**Stage 1: Vector Search**
```
Retrieved 20 candidates:
1. TLS configuration guide (0.89)
2. Security best practices (0.87)
3. Encryption overview (0.85)
4. Network setup (0.82)
...
15. General Linux intro (0.52)
20. Hardware specs (0.45)
```

**Stage 2: Similarity Filtering**
```
After filtering (absolute > 0.5, relative > 0.71):
1. TLS configuration guide (0.89) ✓
2. Security best practices (0.87) ✓
3. Encryption overview (0.85) ✓
4. Network setup (0.82) ✓
...
10. Certificate management (0.73) ✓
11. General security (0.68) ✗ (>20% drop)
```
Result: 10 chunks

**Stage 3: Reranking**
```
Cross-encoder scores:
1. TLS configuration guide (0.95) ← moved up
2. Certificate management (0.91) ← moved up
3. Encryption overview (0.88)
4. Security best practices (0.85) ← moved down
...
```
Result: Reordered by true relevance

**Stage 4: Diversity**
```
Check similarity between chunks:
1. TLS configuration (0.95) ✓
2. Certificate management (0.91) ✓ (different aspect)
3. Encryption overview (0.88) ✗ (too similar to #1)
4. Security best practices (0.85) ✓ (broader context)
...
```
Result: 8 diverse, high-quality chunks

**Final Context to LLM:**
- 8 highly relevant chunks
- No redundancy
- Focused on TLS/encryption
- High semantic relevance

---

## Performance Characteristics

### Latency Breakdown

```mermaid
graph LR
    A[Vector Search<br/>~50ms] --> B[Filtering<br/>~5ms]
    B --> C[Reranking<br/>~200ms]
    C --> D[Diversity<br/>~10ms]
    D --> E[LLM Generation<br/>~2000ms]
    
    style C fill:#ffd43b
    style E fill:#ffd43b
```

**Total Retrieval:** ~265ms (vs. 50ms before)
**Total Query:** ~2265ms (vs. 2050ms before)
**Overhead:** +10% latency for much better quality

### Scalability

**Vector Search:**
- O(log n) with pgvector index
- Scales to millions of chunks

**Reranking:**
- O(k) where k = filtered candidates
- Typically 10-20 chunks
- Bottleneck but acceptable

**Diversity:**
- O(k²) pairwise comparisons
- Negligible for k < 50

---

## Configuration Trade-offs

### Top K Selection

```mermaid
graph TB
    A[top_k = 5] --> B[Pros: Fast, focused]
    A --> C[Cons: May miss info]
    
    D[top_k = 10] --> E[Pros: Balanced]
    D --> F[Cons: Slight overhead]
    
    G[top_k = 20] --> H[Pros: Comprehensive]
    G --> I[Cons: Slower reranking]
    
    style D fill:#51cf66
    style E fill:#51cf66
```

**Recommendation:** top_k = 10
- Good balance of coverage and speed
- Filtering ensures quality
- Diversity prevents redundancy

### Filtering Aggressiveness

**Strict Filtering** (threshold = 0.6):
- Pros: Very high precision
- Cons: May miss relevant info

**Moderate Filtering** (threshold = 0.5):
- Pros: Balanced precision/recall
- Cons: Occasional low-quality chunk

**Loose Filtering** (threshold = 0.4):
- Pros: High recall
- Cons: More noise, slower reranking

**Recommendation:** 0.5 (moderate)

---

## Monitoring & Debugging

### Key Metrics to Track

```mermaid
graph TB
    A[Retrieval Metrics] --> B[Candidates Retrieved]
    A --> C[After Filtering]
    A --> D[After Reranking]
    A --> E[Final Chunks]
    
    F[Quality Metrics] --> G[Avg Rerank Score]
    F --> H[Score Distribution]
    F --> I[Diversity Score]
    
    J[Performance] --> K[Retrieval Time]
    J --> L[Reranking Time]
    J --> M[Total Time]
```

### Debug Checklist

**Problem: Answers too short**
- Check: Final chunk count
- Check: LLM max_tokens setting
- Check: Context quality (avg score)

**Problem: Irrelevant information**
- Check: Similarity threshold (increase?)
- Check: Reranking scores (working?)
- Check: Query embedding quality

**Problem: Missing information**
- Check: Initial candidates (enough?)
- Check: Filtering too aggressive?
- Check: Chunking granularity

**Problem: Slow responses**
- Check: Reranking batch size
- Check: Number of candidates
- Check: Database query performance

---

## Future Enhancements

### Potential Improvements

1. **Query Expansion**
   - Expand query with synonyms
   - Better coverage of relevant chunks

2. **Hybrid Search**
   - Combine vector + keyword search
   - Better for specific terms/codes

3. **Contextual Compression**
   - Compress retrieved context
   - Keep only relevant sentences

4. **Adaptive Top-K**
   - Dynamically adjust based on query
   - Simple queries → fewer chunks
   - Complex queries → more chunks

5. **Caching**
   - Cache reranking results
   - Faster for repeated queries

---

*This architecture ensures consistent, high-quality retrieval across all query types while maintaining acceptable performance.*