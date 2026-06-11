# Implementation Checklist

Quick reference for implementing the retrieval improvements.

---

## Phase 1: Core Retrieval Improvements

### Prerequisites
- [ ] Review [`RETRIEVAL_IMPROVEMENT_PLAN.md`](RETRIEVAL_IMPROVEMENT_PLAN.md)
- [ ] Review [`RETRIEVAL_ARCHITECTURE.md`](RETRIEVAL_ARCHITECTURE.md)
- [ ] Backup current system state
- [ ] Create feature branch: `git checkout -b feature/retrieval-improvements`

### 1.1 Reranking Service
- [ ] Create `backend/app/services/reranking_service.py`
- [ ] Add `sentence-transformers>=2.2.0` to `requirements.txt`
- [ ] Install dependencies: `pip install -r backend/requirements.txt`
- [ ] Test reranking service independently
- [ ] Verify model downloads correctly (~80MB)

**Files:**
- ✨ NEW: `backend/app/services/reranking_service.py`
- 📝 EDIT: `backend/requirements.txt`

### 1.2 Adaptive Similarity Filtering
- [ ] Add `filter_by_adaptive_threshold()` to `retrieval_service.py`
- [ ] Add configuration to `backend/app/config.py`:
  - `min_similarity_absolute: float = 0.5`
  - `similarity_relative_threshold: float = 0.8`
  - `enable_adaptive_filtering: bool = True`
- [ ] Test filtering with various score distributions
- [ ] Verify logging shows filtering results

**Files:**
- 📝 EDIT: `backend/app/services/retrieval_service.py`
- 📝 EDIT: `backend/app/config.py`

### 1.3 Diversity Filtering
- [ ] Add `scikit-learn>=1.0.0` and `numpy>=1.21.0` to `requirements.txt`
- [ ] Add `filter_by_diversity()` to `retrieval_service.py`
- [ ] Update SQL query to return embeddings
- [ ] Test diversity filtering with similar chunks
- [ ] Verify redundant chunks are removed

**Files:**
- 📝 EDIT: `backend/app/services/retrieval_service.py`
- 📝 EDIT: `backend/requirements.txt`

### 1.4 Multi-Stage Pipeline
- [ ] Add `search_with_reranking()` method to `retrieval_service.py`
- [ ] Integrate all filtering stages
- [ ] Add metrics collection
- [ ] Test complete pipeline end-to-end
- [ ] Verify each stage logs correctly

**Files:**
- 📝 EDIT: `backend/app/services/retrieval_service.py`

### 1.5 Retrieval Metrics
- [ ] Add `calculate_retrieval_metrics()` to `retrieval_service.py`
- [ ] Add metrics to pipeline return value
- [ ] Test metrics calculation
- [ ] Verify metrics are meaningful

**Files:**
- 📝 EDIT: `backend/app/services/retrieval_service.py`

### 1.6 API Updates
- [ ] Update `QueryResponse` schema in `backend/app/models/schemas.py`
- [ ] Add `retrieval_metrics: Optional[Dict]` field
- [ ] Update `/query` endpoint in `backend/app/api/routes.py`
- [ ] Switch to `search_with_reranking()` method
- [ ] Test API returns metrics correctly

**Files:**
- 📝 EDIT: `backend/app/models/schemas.py`
- 📝 EDIT: `backend/app/api/routes.py`

### 1.7 Testing Phase 1
- [ ] Test with broad query: "What is LinuxONE?"
- [ ] Test with specific query: "How do I configure TLS encryption?"
- [ ] Test with multi-aspect query: "What are the security and performance benefits?"
- [ ] Test with edge case: "Tell me about quantum computing"
- [ ] Verify top_k=5, 10, 15 all produce good results
- [ ] Check retrieval metrics for each query
- [ ] Document any issues found

**Success Criteria:**
- ✅ Consistent quality across different top_k values
- ✅ Low-relevance chunks filtered out
- ✅ No redundant chunks in results
- ✅ Metrics logged for all queries

---

## Phase 2: Chunking Optimization

### 2.1 Update Configuration
- [ ] Update `backend/app/config.py`:
  - `chunk_size: int = 300` (from 500)
  - `top_k_results: int = 10` (from 5)
- [ ] Commit configuration changes

**Files:**
- 📝 EDIT: `backend/app/config.py`

### 2.2 Sentence-Aware Chunking
- [ ] Review `chunk_by_sentences()` in `backend/app/utils/chunking.py`
- [ ] Make it default chunking strategy if not already
- [ ] Test chunking with sample text
- [ ] Verify chunks don't break mid-sentence

**Files:**
- 📝 EDIT: `backend/app/utils/chunking.py`

### 2.3 Database Backup
- [ ] Create `backend/scripts/backup_database.sh`
- [ ] Make executable: `chmod +x backend/scripts/backup_database.sh`
- [ ] Run backup: `./backend/scripts/backup_database.sh`
- [ ] Verify backup file created
- [ ] Test restore process (optional)

**Files:**
- ✨ NEW: `backend/scripts/backup_database.sh`

### 2.4 Re-ingestion
- [ ] Verify `backend/scripts/reingest_with_new_chunks.sh` exists
- [ ] Review script to ensure it uses new config
- [ ] Run re-ingestion: `./backend/scripts/reingest_with_new_chunks.sh`
- [ ] Monitor progress (may take 10-30 minutes)
- [ ] Check for errors in logs

**Files:**
- 📝 VERIFY: `backend/scripts/reingest_with_new_chunks.sh`

### 2.5 Verify Chunk Count
- [ ] Connect to database: `psql -U raguser -h localhost linuxone_rag`
- [ ] Check total chunks: `SELECT COUNT(*) FROM chunks;`
- [ ] Check average tokens: `SELECT AVG(token_count) FROM chunks;`
- [ ] Check per-document: `SELECT document_id, COUNT(*) FROM chunks GROUP BY document_id;`
- [ ] Verify: 3,000-10,000 total chunks
- [ ] Verify: ~300 average tokens

**Expected:**
- Current: ~512 chunks
- Target: 3,000-10,000 chunks
- Avg tokens: ~300

### 2.6 Test with New Chunks
- [ ] Restart backend server
- [ ] Run same test queries from Phase 1
- [ ] Compare answer quality before/after
- [ ] Check if chunks are more focused
- [ ] Verify no degradation in quality
- [ ] Document improvements observed

---

## Phase 3: Evaluation & Monitoring

### 3.1 Test Query Dataset
- [ ] Create `backend/tests/test_queries.json`
- [ ] Add 10-15 diverse test queries
- [ ] Include expected topics for each
- [ ] Include minimum chunk requirements
- [ ] Review with team

**Files:**
- ✨ NEW: `backend/tests/test_queries.json`

### 3.2 Evaluation Script
- [ ] Create `backend/scripts/evaluate_retrieval.py`
- [ ] Make executable: `chmod +x backend/scripts/evaluate_retrieval.py`
- [ ] Test with sample queries
- [ ] Verify metrics calculation
- [ ] Run full evaluation
- [ ] Review results in `backend/tests/evaluation_results.json`

**Files:**
- ✨ NEW: `backend/scripts/evaluate_retrieval.py`

### 3.3 Retrieval Dashboard
- [ ] Add `/retrieval-stats` endpoint to `backend/app/api/routes.py`
- [ ] Query recent QueryLog entries
- [ ] Calculate aggregate statistics
- [ ] Test endpoint
- [ ] Document API response format

**Files:**
- 📝 EDIT: `backend/app/api/routes.py`

### 3.4 Configuration Documentation
- [ ] Create `RETRIEVAL_CONFIGURATION.md`
- [ ] Document optimal parameters
- [ ] Explain trade-offs
- [ ] Add tuning guidelines
- [ ] Include performance considerations

**Files:**
- ✨ NEW: `RETRIEVAL_CONFIGURATION.md`

### 3.5 Troubleshooting Guide
- [ ] Create `RETRIEVAL_TROUBLESHOOTING.md`
- [ ] Document common issues
- [ ] Add diagnostic steps
- [ ] Include solutions
- [ ] Add FAQ section

**Files:**
- ✨ NEW: `RETRIEVAL_TROUBLESHOOTING.md`

---

## Final Validation

### System-Wide Testing
- [ ] Test with 20+ diverse queries
- [ ] Verify consistent quality
- [ ] Check performance metrics
- [ ] Review logs for errors
- [ ] Test edge cases

### Performance Validation
- [ ] Measure average query time
- [ ] Verify < 3 seconds total
- [ ] Check retrieval overhead (~200ms)
- [ ] Monitor memory usage
- [ ] Test under load (optional)

### Documentation Review
- [ ] All markdown files complete
- [ ] Code comments added
- [ ] API documentation updated
- [ ] README updated with new features
- [ ] CHANGELOG updated

### Deployment Preparation
- [ ] All tests passing
- [ ] No errors in logs
- [ ] Configuration documented
- [ ] Rollback plan ready
- [ ] Team trained on new features

---

## Quick Commands

### Development
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run backend
cd backend && uvicorn app.main:app --reload

# Run tests
python backend/scripts/evaluate_retrieval.py
```

### Database
```bash
# Backup
./backend/scripts/backup_database.sh

# Re-ingest
./backend/scripts/reingest_with_new_chunks.sh

# Check stats
psql -U raguser -h localhost linuxone_rag -c "SELECT COUNT(*) FROM chunks;"
```

### Git
```bash
# Create branch
git checkout -b feature/retrieval-improvements

# Commit changes
git add .
git commit -m "Phase 1: Add reranking and filtering"

# Push
git push origin feature/retrieval-improvements
```

---

## File Summary

### New Files (7)
1. `backend/app/services/reranking_service.py` - Cross-encoder reranking
2. `backend/scripts/backup_database.sh` - Database backup script
3. `backend/scripts/evaluate_retrieval.py` - Evaluation framework
4. `backend/tests/test_queries.json` - Test query dataset
5. `RETRIEVAL_CONFIGURATION.md` - Configuration guide
6. `RETRIEVAL_TROUBLESHOOTING.md` - Troubleshooting guide
7. `RETRIEVAL_IMPROVEMENT_PLAN.md` - This plan (already created)

### Modified Files (6)
1. `backend/app/services/retrieval_service.py` - Multi-stage pipeline
2. `backend/app/api/routes.py` - Updated query endpoint
3. `backend/app/models/schemas.py` - Added retrieval_metrics field
4. `backend/app/config.py` - Updated chunking + retrieval config
5. `backend/requirements.txt` - Added dependencies
6. `backend/app/utils/chunking.py` - Enhanced sentence chunking

---

## Estimated Timeline

- **Phase 1:** 2-3 days (core improvements)
- **Phase 2:** 1-2 days (re-chunking)
- **Phase 3:** 1-2 days (evaluation)
- **Total:** 4-7 days

---

## Success Metrics

### Phase 1
- [ ] Retrieval quality consistent across top_k values
- [ ] Low-relevance chunks filtered (min score > 0.5)
- [ ] No redundant chunks in results
- [ ] Metrics logged for all queries

### Phase 2
- [ ] Chunk count: 3,000-10,000 (from ~512)
- [ ] Average chunk size: ~300 tokens
- [ ] Improved answer precision
- [ ] No quality degradation

### Phase 3
- [ ] Evaluation framework functional
- [ ] 90%+ test queries pass
- [ ] Documentation complete
- [ ] Monitoring operational

---

## Support

**Questions?** Review:
1. [`RETRIEVAL_IMPROVEMENT_PLAN.md`](RETRIEVAL_IMPROVEMENT_PLAN.md) - Detailed plan
2. [`RETRIEVAL_ARCHITECTURE.md`](RETRIEVAL_ARCHITECTURE.md) - Architecture diagrams
3. Code comments in implementation files

**Issues?** Check:
1. Logs: `backend/logs/`
2. Retrieval metrics in API responses
3. Database statistics: `/statistics` endpoint

---

*Ready to implement? Switch to Code mode and start with Phase 1.1!*