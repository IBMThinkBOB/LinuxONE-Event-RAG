# LinuxONE RAG Knowledge Assistant

A Retrieval-Augmented Generation (RAG) system for querying LinuxONE-related knowledge from IBM Redbooks, powered by local LLM inference with Ollama/Qwen.

## 🎯 Overview

This system demonstrates an enterprise-grade AI pipeline that:
- Processes IBM Redbooks PDFs into a searchable knowledge base
- Uses semantic search to retrieve relevant information
- Generates accurate, grounded responses using local LLM inference
- Provides citations and source attribution
- Scales from local development to LinuxONE enterprise deployment

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Offline Pipeline                          │
│  PDF → Text Extraction → Chunking → Embeddings → Database   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     Online Pipeline                          │
│  Query → Embedding → Vector Search → Context → LLM → Response│
└─────────────────────────────────────────────────────────────┘
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for detailed system design.

## 📋 Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18+ and npm
- **PostgreSQL**: 15+ with pgvector extension
- **Docker**: For containerized deployment
- **Ollama**: With Qwen model installed and running
- **IBM Redbooks**: PDF files for knowledge base

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd LinuxONERAGPipeline

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Start PostgreSQL with pgvector

```bash
# Start PostgreSQL using Docker Compose
docker-compose up -d postgres

# Wait for database to be ready
docker-compose logs -f postgres
```

### 3. Verify Ollama is Running

```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# If not running, start Ollama with Qwen model
ollama run qwen
```

### 4. Initialize Database

```bash
# The database will be automatically initialized on first run
# Or manually run:
python backend/scripts/setup_database.py
```

### 5. Ingest Documents

```bash
# Place your IBM Redbooks PDFs in data/redbooks/
# Then run the ingestion script
python backend/scripts/ingest_documents.py --input data/redbooks/
```

### 6. Start Backend Server

```bash
# From project root
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Start Frontend

```bash
# In a new terminal
cd frontend
npm run dev
```

### 8. Access the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## 📁 Project Structure

```
LinuxONERAGPipeline/
├── backend/
│   ├── app/
│   │   ├── models/          # Database models
│   │   ├── services/        # Business logic
│   │   ├── api/             # API routes
│   │   ├── utils/           # Utilities
│   │   ├── config.py        # Configuration
│   │   └── main.py          # FastAPI app
│   ├── scripts/
│   │   ├── ingest_documents.py
│   │   └── setup_database.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API client
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── data/
│   └── redbooks/            # Place PDFs here
├── docs/
├── docker-compose.yml
├── .env
├── ARCHITECTURE.md
├── IMPLEMENTATION_GUIDE.md
└── README.md
```

## 🔧 Configuration

Edit `.env` file to customize settings:

```env
# Database
DATABASE_URL=postgresql://raguser:ragpassword@localhost:5432/linuxone_rag

# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# RAG Parameters
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
MAX_CONTEXT_LENGTH=2000
```

## 📊 Usage Examples

### Query via API

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I optimize AI workloads on LinuxONE?",
    "top_k": 5
  }'
```

### Query via Frontend

1. Open http://localhost:3000
2. Enter your question in the search box
3. View the AI-generated response with source citations

### Ingest New Documents

```bash
# Add PDFs to data/redbooks/
python backend/scripts/ingest_documents.py \
  --input data/redbooks/new_document.pdf \
  --batch-size 32
```

## 🧪 Testing

```bash
# Run backend tests
cd backend
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

## 📈 Performance Optimization

### Embedding Generation
- Batch size: 32 (adjust based on GPU memory)
- Model: all-MiniLM-L6-v2 (384 dimensions)
- Upgrade to larger models for better quality

### Vector Search
- HNSW index parameters: m=16, ef_construction=64
- Adjust for speed vs. accuracy tradeoff
- Monitor query latency

### Chunking Strategy
- Default: 500 tokens with 50 token overlap
- Experiment with different sizes for your use case
- Consider semantic chunking for better context

## 🐳 Docker Deployment

### Build and Run All Services

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Deployment

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d
```

## 🔒 Security Considerations

- **API Authentication**: Add JWT tokens for production
- **Database Security**: Use strong passwords, encrypted connections
- **Input Validation**: All user inputs are sanitized
- **Rate Limiting**: Implement for production deployment
- **CORS**: Configure allowed origins appropriately

## 📝 API Endpoints

### Query Endpoint
```
POST /api/query
{
  "query": "string",
  "top_k": 5,
  "filters": {
    "topic": "string"
  }
}
```

### Document Ingestion
```
POST /api/ingest
Content-Type: multipart/form-data
file: <PDF file>
```

### Health Check
```
GET /api/health
```

### List Documents
```
GET /api/documents
```

See full API documentation at http://localhost:8000/docs

## 🎯 Roadmap

### Phase 1: Local Development ✅
- [x] Basic RAG pipeline
- [x] PostgreSQL + pgvector
- [x] Ollama/Qwen integration
- [x] React frontend

### Phase 2: Enhancement (Current)
- [ ] Multi-turn conversations
- [ ] Advanced filtering
- [ ] Analytics dashboard
- [ ] Performance optimization

### Phase 3: LinuxONE Deployment
- [ ] LinuxONE infrastructure setup
- [ ] Enterprise security features
- [ ] High availability configuration
- [ ] Load testing and optimization

## 🐛 Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Ollama Not Responding
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve

# Pull Qwen model if missing
ollama pull qwen
```

### Embedding Generation Slow
- Reduce batch size in config
- Use GPU if available
- Consider smaller embedding model

### Poor Retrieval Quality
- Adjust chunk size and overlap
- Increase top_k results
- Fine-tune embedding model
- Improve metadata tagging

## 📚 Documentation

### Core Documentation
- [`README.md`](README.md) - This file (project overview)
- [`DOCUMENTATION.md`](DOCUMENTATION.md) - **Complete documentation index and guide**
- [`QUICKSTART.md`](QUICKSTART.md) - Quick start guide
- [`ARCHITECTURE.md`](ARCHITECTURE.md) - System architecture and design
- [`HYBRID_RAG_IMPLEMENTATION.md`](HYBRID_RAG_IMPLEMENTATION.md) - Current implementation details
- [`LINUXONE_DEPLOYMENT.md`](LINUXONE_DEPLOYMENT.md) - LinuxONE deployment guide
- [API Documentation](http://localhost:8000/docs) - Interactive API docs

### Additional Documentation
- [`docs/implementation/`](docs/implementation/) - Implementation history and phase documentation
- [`docs/plans/`](docs/plans/) - Planning documents and upgrade plans
- [`docs/troubleshooting/`](docs/troubleshooting/) - Troubleshooting guides
- [`docs/archive/`](docs/archive/) - Archived documentation

**📖 For complete documentation, see [DOCUMENTATION.md](DOCUMENTATION.md)**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- IBM Redbooks for comprehensive LinuxONE documentation
- Ollama for local LLM inference
- pgvector for efficient vector search
- SentenceTransformers for embeddings

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review troubleshooting section

---

**Built for LinuxONE | Powered by RAG | Enterprise-Ready**