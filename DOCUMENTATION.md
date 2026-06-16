# LinuxONE RAG Pipeline - Complete Documentation

**Last Updated**: June 16, 2026

---

## 📚 Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Current Implementation](#current-implementation)
4. [Configuration](#configuration)
5. [Deployment](#deployment)
6. [Troubleshooting](#troubleshooting)
7. [Development](#development)
8. [Documentation Index](#documentation-index)

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- PostgreSQL 15+ with pgvector extension
- Ollama with Qwen model

### Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd LinuxONERAGPipeline

# 2. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 3. Start services
docker-compose up -d

# 4. Initialize database
./setup.sh

# 5. Ingest documents
python backend/scripts/ingest_documents.py

# 6. Start backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 7. Start frontend
cd frontend
npm install
npm run dev
```

### Quick Test
```bash
# Test the API
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is LinuxONE?"}'
```

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

---

## Architecture Overview

### System Architecture

```
┌─────────────┐
│   Frontend  │ (React + Vite)
│   (Port 3000)│
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Backend API (FastAPI)           │
│              (Port 8000)                │
├─────────────────────────────────────────┤
│  ┌──────────────┐  ┌─────────────────┐ │
│  │  Retrieval   │  │   LLM Service   │ │
│  │   Service    │  │   (Ollama)      │ │
│  └──────┬───────┘  └────────┬────────┘ │
│         │                   │          │
│  ┌──────▼───────┐  ┌────────▼────────┐ │
│  │  Evidence    │  │  Multi-Stage    │ │
│  │  Extraction  │  │   Pipeline      │ │
│  └──────────────┘  └─────────────────┘ │
└──────────┬──────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │  PostgreSQL  │
    │  + pgvector  │
    └──────────────┘
```

### Current Implementation: Hybrid RAG

**Philosophy**: Context-first hybrid where LLM uses both retrieved context and general knowledge.

```
User Query
    ↓
Retrieve Chunks (vector similarity + reranking)
    ↓
Evidence Extraction (clean & structure)
    ↓
LLM Generation (knowledge + context)
    ↓
Validation & Repair (continuation/regeneration)
    ↓
Final Answer
```

**Key Features**:
- ✅ Hybrid RAG (context enhances, doesn't constrain)
- ✅ Evidence extraction (cleans noisy chunks)
- ✅ Multi-stage pipeline (validation, continuation, regeneration)
- ✅ Adaptive retrieval (reranking, filtering, diversity)
- ✅ Query expansion for vague queries

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture.

---

## Current Implementation

### Hybrid RAG (June 2026)

**Status**: ✅ Production Ready

**What Changed**:
- Simplified prompts (from 30+ to 15-20 lines)
- Removed strict "MUST use sources" constraints
- Added context-first hybrid philosophy
- Preserved evidence extraction and multi-stage pipeline

**Key Components**:

1. **Evidence Extraction Service** (`backend/app/services/evidence_service.py`)
   - Cleans chunks (removes headers, footers, captions)
   - Extracts key facts
   - Structures evidence for LLM

2. **LLM Service** (`backend/app/services/llm_service.py`)
   - Hybrid RAG prompts
   - Multi-stage pipeline (validation, continuation, regeneration)
   - Enhanced observability

3. **Retrieval Service** (`backend/app/services/retrieval_service.py`)
   - Vector similarity search
   - Reranking with cross-encoder
   - Adaptive filtering and diversity

**Documentation**:
- [HYBRID_RAG_IMPLEMENTATION.md](HYBRID_RAG_IMPLEMENTATION.md) - Complete implementation guide
- [docs/implementation/](docs/implementation/) - Phase-by-phase implementation history

---

## Configuration

### Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://raguser:ragpassword@localhost:5432/linuxone_rag
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpassword
POSTGRES_DB=linuxone_rag

# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen
LLM_MAX_TOKENS=2500
LLM_TEMPERATURE=0.2

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# RAG Configuration
CHUNK_SIZE=600
CHUNK_OVERLAP=100
TOP_K_RESULTS=10
MAX_CONTEXT_TOKENS=1200

# Retrieval Quality
MIN_SIMILARITY_ABSOLUTE=0.4
SIMILARITY_RELATIVE_THRESHOLD=0.6
DIVERSITY_THRESHOLD=0.95
MIN_RELEVANCE_THRESHOLD=0.2
ENABLE_RERANKING=true
ENABLE_ADAPTIVE_FILTERING=true
ENABLE_DIVERSITY_FILTERING=true
```

### Tuning Guidelines

**For Better Retrieval**:
- Increase `TOP_K_RESULTS` (10-15) for broader context
- Lower `MIN_SIMILARITY_ABSOLUTE` (0.3-0.4) for more results
- Enable all filtering options

**For Better Answers**:
- Increase `LLM_MAX_TOKENS` (2500-3000) for detailed responses
- Adjust `LLM_TEMPERATURE` (0.15-0.25) for creativity vs focus
- Increase `MAX_CONTEXT_TOKENS` (1200-1500) for more context

**For Faster Responses**:
- Decrease `TOP_K_RESULTS` (5-8)
- Disable `ENABLE_RERANKING` (faster but lower quality)
- Reduce `MAX_CONTEXT_TOKENS` (800-1000)

---

## Deployment

### Local Development
```bash
# Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev
```

### Docker Deployment
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### LinuxONE Deployment
See [LINUXONE_DEPLOYMENT.md](LINUXONE_DEPLOYMENT.md) for LinuxONE-specific deployment instructions.

---

## Troubleshooting

### Common Issues

#### 1. No Results Retrieved
**Symptoms**: "No relevant information found" error

**Solutions**:
- Lower `MIN_SIMILARITY_ABSOLUTE` in config
- Check if documents are ingested: `SELECT COUNT(*) FROM chunks;`
- Verify embeddings exist: `SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;`
- Try query expansion for vague queries

See [docs/troubleshooting/TROUBLESHOOTING_RETRIEVAL.md](docs/troubleshooting/TROUBLESHOOTING_RETRIEVAL.md)

#### 2. Truncated Answers
**Symptoms**: Answers cut off mid-sentence

**Solutions**:
- Increase `LLM_MAX_TOKENS` (2500-3000)
- Check logs for "Answer appears incomplete"
- Multi-stage pipeline should auto-repair (continuation)
- Verify Ollama is running: `curl http://localhost:11434/api/tags`

#### 3. Generic Answers
**Symptoms**: Answers not LinuxONE-specific

**Solutions**:
- Check retrieval quality (similarity scores)
- Verify chunks contain LinuxONE content
- Enable evidence extraction (`use_evidence_extraction=True`)
- Review prompt templates in `llm_service.py`

#### 4. Slow Responses
**Symptoms**: >10 second response times

**Solutions**:
- Reduce `TOP_K_RESULTS` (5-8)
- Disable reranking temporarily
- Check database query performance
- Monitor Ollama resource usage

### Database Issues

```bash
# Check database connection
psql -U raguser -d linuxone_rag -c "SELECT 1;"

# Verify pgvector extension
psql -U raguser -d linuxone_rag -c "SELECT * FROM pg_extension WHERE extname='vector';"

# Check chunk count
psql -U raguser -d linuxone_rag -c "SELECT COUNT(*) FROM chunks;"

# Backup database
./backend/scripts/backup_database.sh
```

---

## Development

### Project Structure

```
LinuxONERAGPipeline/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── services/     # Core services
│   │   ├── utils/        # Utilities
│   │   └── models/       # Database models
│   ├── scripts/          # Utility scripts
│   └── tests/            # Test suite
├── frontend/
│   └── src/
│       ├── components/   # React components
│       └── services/     # API client
├── data/
│   └── redbooks/         # PDF documents
├── docs/                 # Documentation
│   ├── implementation/   # Implementation history
│   ├── plans/           # Planning documents
│   ├── troubleshooting/ # Troubleshooting guides
│   └── archive/         # Archived docs
└── [config files]
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# LLM service tests
pytest tests/test_llm_service.py -v

# Retrieval tests
python scripts/test_retrieval_pipeline.py

# Hybrid RAG evaluation
python scripts/evaluate_hybrid_rag.py
```

### Adding New Documents

```bash
# 1. Add PDFs to data/redbooks/
cp your_document.pdf data/redbooks/

# 2. Ingest documents
python backend/scripts/ingest_documents.py

# 3. Verify ingestion
psql -U raguser -d linuxone_rag -c "SELECT title, chunk_count FROM documents;"
```

### Code Style

- **Backend**: Black formatter, type hints, docstrings
- **Frontend**: ESLint, Prettier
- **Commits**: Conventional commits format

---

## Documentation Index

### Core Documentation (Root)
- [README.md](README.md) - Project overview
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [HYBRID_RAG_IMPLEMENTATION.md](HYBRID_RAG_IMPLEMENTATION.md) - Current implementation
- [LINUXONE_DEPLOYMENT.md](LINUXONE_DEPLOYMENT.md) - Deployment guide

### Implementation History (docs/implementation/)
- [PHASE1_COMPLETE.md](docs/implementation/PHASE1_COMPLETE.md) - Initial implementation
- [PHASE5_RETRIEVAL_STABILITY.md](docs/implementation/PHASE5_RETRIEVAL_STABILITY.md) - Retrieval improvements
- [PHASE10_LLM_ARCHITECTURE_IMPLEMENTATION.md](docs/implementation/PHASE10_LLM_ARCHITECTURE_IMPLEMENTATION.md) - Multi-stage pipeline
- [CONTEXT_OVERLOAD_FIX.md](docs/implementation/CONTEXT_OVERLOAD_FIX.md) - Context management
- [MULTI_CHUNK_AGGREGATION_ENFORCEMENT.md](docs/implementation/MULTI_CHUNK_AGGREGATION_ENFORCEMENT.md) - Multi-chunk synthesis
- [CONTEXT_FIRST_HYBRID_RAG.md](docs/implementation/CONTEXT_FIRST_HYBRID_RAG.md) - Hybrid RAG transition

### Planning Documents (docs/plans/)
- [hybrid_rag_plan.md](docs/plans/hybrid_rag_plan.md) - Hybrid RAG upgrade plan
- [linuxone_llm_architecture_upgrade_plan.md](docs/plans/linuxone_llm_architecture_upgrade_plan.md) - LLM architecture plan
- [linuxone_ui_upgrade_plan.md](docs/plans/linuxone_ui_upgrade_plan.md) - UI/UX improvements
- [RETRIEVAL_IMPROVEMENT_PLAN.md](docs/plans/RETRIEVAL_IMPROVEMENT_PLAN.md) - Retrieval enhancements
- [RAG_DIAGNOSIS_ANALYSIS.md](docs/plans/RAG_DIAGNOSIS_ANALYSIS.md) - Issue diagnosis
- [rag_issue_diagnosis_and_solutions.md](docs/plans/rag_issue_diagnosis_and_solutions.md) - Detailed solutions

### Troubleshooting (docs/troubleshooting/)
- [TROUBLESHOOTING_RETRIEVAL.md](docs/troubleshooting/TROUBLESHOOTING_RETRIEVAL.md) - Retrieval issues
- [VAGUE_QUERIES.md](docs/troubleshooting/VAGUE_QUERIES.md) - Handling vague queries
- [DOCKER_RATE_LIMIT_FIX.md](docs/troubleshooting/DOCKER_RATE_LIMIT_FIX.md) - Docker issues

### Archived (docs/archive/)
- Historical implementation guides
- Deprecated configuration docs
- Old architecture documents

---

## Support & Contributing

### Getting Help
1. Check [Troubleshooting](#troubleshooting) section
2. Review [docs/troubleshooting/](docs/troubleshooting/)
3. Check GitHub issues
4. Contact maintainers

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit pull request
5. Update documentation

---

## License

[Add license information]

---

## Changelog

### June 2026 - Hybrid RAG Implementation
- ✅ Implemented hybrid RAG architecture
- ✅ Simplified prompt templates
- ✅ Added evidence extraction service
- ✅ Created evaluation framework
- ✅ Consolidated documentation

### May 2026 - Multi-Stage Pipeline
- ✅ Added validation and repair
- ✅ Implemented continuation logic
- ✅ Enhanced observability

### April 2026 - Retrieval Improvements
- ✅ Added reranking
- ✅ Implemented adaptive filtering
- ✅ Added diversity filtering

### March 2026 - Initial Release
- ✅ Basic RAG pipeline
- ✅ Vector similarity search
- ✅ Document ingestion

---

*Made with Bob - LinuxONE RAG Pipeline Team*