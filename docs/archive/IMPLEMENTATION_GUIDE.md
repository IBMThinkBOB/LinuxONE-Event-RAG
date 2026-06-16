# LinuxONE RAG Knowledge Assistant - Implementation Guide

## Overview

This guide provides detailed, step-by-step instructions for implementing the RAG system. Each section corresponds to tasks in the todo list and includes code examples, configuration details, and best practices.

## Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm
- PostgreSQL 15+
- Docker and Docker Compose
- Ollama with Qwen model (already running)
- IBM Redbooks PDFs

## Phase 1: Environment Setup

### 1.1 Project Structure Creation

```bash
# Create main project structure
mkdir -p backend/app/{models,services,api,utils}
mkdir -p backend/scripts
mkdir -p backend/tests
mkdir -p frontend/src/{components,services}
mkdir -p data/redbooks
mkdir -p docs

# Create __init__.py files
touch backend/app/__init__.py
touch backend/app/models/__init__.py
touch backend/app/services/__init__.py
touch backend/app/api/__init__.py
touch backend/app/utils/__init__.py
```

### 1.2 Python Dependencies

Create `backend/requirements.txt`:

```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
pgvector==0.2.4

# ML & Embeddings
sentence-transformers==2.2.2
torch==2.1.1
transformers==4.35.2

# PDF Processing
PyMuPDF==1.23.8
pdfplumber==0.10.3

# Utilities
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
requests==2.31.0
numpy==1.26.2

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
```

### 1.3 Frontend Dependencies

Create `frontend/package.json`:

```json
{
  "name": "linuxone-rag-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.2",
    "@mui/material": "^5.14.20",
    "@emotion/react": "^11.11.1",
    "@emotion/styled": "^11.11.0",
    "react-markdown": "^9.0.1"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8"
  }
}
```

### 1.4 Environment Configuration

Update `.env`:

```env
# LLM Configuration
LLM_API_KEY=bob_prod_bob-user_2viThXYhcKnmDiyxZFhNNguHH7yDrbA3D5P6db8pwrchHSAyAb8rSsGcv1nmD3KcEov6YrXg59XrkErp7gut5jrc_A2juynjwk4rGVXx33DpoLf3PjuFpUxVnwQq1Zj4MTuy1
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen

# Database Configuration
DATABASE_URL=postgresql://raguser:ragpassword@localhost:5432/linuxone_rag
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpassword
POSTGRES_DB=linuxone_rag

# Embedding Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Application Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_PORT=3000

# RAG Configuration
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
MAX_CONTEXT_LENGTH=2000
```

## Phase 2: Database Setup

### 2.1 Docker Compose Configuration

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    container_name: linuxone_rag_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### 2.2 Database Initialization Script

Create `backend/scripts/init_db.sql`:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(500),
    source_type VARCHAR(50) DEFAULT 'redbook',
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_pages INTEGER,
    total_chunks INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Chunks table with embeddings
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),  -- Dimension for all-MiniLM-L6-v2
    token_count INTEGER,
    page_number INTEGER,
    section VARCHAR(255),
    topic VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS chunks_embedding_idx 
ON chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create indexes for filtering
CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks(document_id);
CREATE INDEX IF NOT EXISTS chunks_topic_idx ON chunks(topic);
CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents(filename);

-- Query logs table for analytics
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    retrieved_chunks INTEGER,
    response_time_ms INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);
```

### 2.3 Database Models

Create `backend/app/models/database.py`:

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, nullable=False)
    title = Column(String(500))
    source_type = Column(String(50), default="redbook")
    upload_date = Column(DateTime, default=datetime.utcnow)
    total_pages = Column(Integer)
    total_chunks = Column(Integer)
    metadata = Column(JSON, default={})
    
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384))  # Dimension for all-MiniLM-L6-v2
    token_count = Column(Integer)
    page_number = Column(Integer)
    section = Column(String(255))
    topic = Column(String(255))
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="chunks")

class QueryLog(Base):
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    retrieved_chunks = Column(Integer)
    response_time_ms = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default={})
```

## Phase 3: Core Services Implementation

### 3.1 Configuration Management

Create `backend/app/config.py`:

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen"
    
    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
    # RAG Configuration
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_results: int = 5
    max_context_length: int = 2000
    
    # Application
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings():
    return Settings()
```

### 3.2 Document Processing Service

Create `backend/app/services/document_processor.py`:

```python
import fitz  # PyMuPDF
from typing import List, Dict, Optional
import re
from pathlib import Path

class DocumentProcessor:
    """Process PDF documents and extract text content."""
    
    def __init__(self):
        self.supported_formats = ['.pdf']
    
    def load_pdf(self, file_path: str) -> Dict:
        """Load and extract text from PDF."""
        doc = fitz.open(file_path)
        
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            pages.append({
                'page_number': page_num + 1,
                'content': text
            })
        
        metadata = {
            'filename': Path(file_path).name,
            'total_pages': len(doc),
            'title': self._extract_title(doc),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', '')
        }
        
        doc.close()
        
        return {
            'pages': pages,
            'metadata': metadata
        }
    
    def _extract_title(self, doc) -> str:
        """Extract title from PDF metadata or first page."""
        # Try metadata first
        if doc.metadata.get('title'):
            return doc.metadata['title']
        
        # Try first page
        if len(doc) > 0:
            first_page_text = doc[0].get_text()
            lines = first_page_text.split('\n')
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if len(line) > 10 and len(line) < 200:
                    return line
        
        return "Untitled Document"
    
    def extract_sections(self, text: str) -> List[Dict]:
        """Extract sections from document text."""
        # Simple section detection based on common patterns
        section_pattern = r'^(Chapter|Section|Part)\s+\d+[:\.]?\s+(.+)$'
        
        sections = []
        current_section = None
        current_content = []
        
        for line in text.split('\n'):
            match = re.match(section_pattern, line.strip(), re.IGNORECASE)
            if match:
                if current_section:
                    sections.append({
                        'title': current_section,
                        'content': '\n'.join(current_content)
                    })
                current_section = line.strip()
                current_content = []
            else:
                current_content.append(line)
        
        if current_section:
            sections.append({
                'title': current_section,
                'content': '\n'.join(current_content)
            })
        
        return sections if sections else [{'title': 'Main Content', 'content': text}]
```

### 3.3 Text Chunking Utility

Create `backend/app/utils/chunking.py`:

```python
from typing import List, Dict
import tiktoken

class TextChunker:
    """Split text into chunks with overlap."""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Split text into overlapping chunks."""
        # Tokenize the text
        tokens = self.encoding.encode(text)
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(tokens):
            # Get chunk tokens
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            
            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Create chunk object
            chunk = {
                'chunk_index': chunk_index,
                'content': chunk_text.strip(),
                'token_count': len(chunk_tokens),
                'start_token': start,
                'end_token': end
            }
            
            # Add metadata if provided
            if metadata:
                chunk.update(metadata)
            
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start = end - self.overlap
            chunk_index += 1
        
        return chunks
    
    def chunk_by_sentences(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Split text by sentences while respecting token limits."""
        import re
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_tokens = len(self.encoding.encode(sentence))
            
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunk = {
                    'chunk_index': chunk_index,
                    'content': chunk_text.strip(),
                    'token_count': current_tokens
                }
                if metadata:
                    chunk.update(metadata)
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                current_chunk = overlap_sentences + [sentence]
                current_tokens = sum(len(self.encoding.encode(s)) for s in current_chunk)
                chunk_index += 1
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk = {
                'chunk_index': chunk_index,
                'content': chunk_text.strip(),
                'token_count': current_tokens
            }
            if metadata:
                chunk.update(metadata)
            chunks.append(chunk)
        
        return chunks
```

### 3.4 Embedding Service

Create `backend/app/services/embedding_service.py`:

```python
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
from functools import lru_cache

class EmbeddingService:
    """Generate embeddings using SentenceTransformers."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = self._load_model()
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    @lru_cache(maxsize=1)
    def _load_model(self):
        """Load the embedding model (cached)."""
        return SentenceTransformer(self.model_name)
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=True
        )
        return embeddings.tolist()
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between two embeddings."""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        return float(dot_product / (norm1 * norm2))
```

## Phase 4: Retrieval and LLM Services

### 4.1 Retrieval Service

Create `backend/app/services/retrieval_service.py`:

```python
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Optional
from app.models.database import Chunk, Document

class RetrievalService:
    """Handle vector similarity search and retrieval."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def search_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Search for similar chunks using vector similarity."""
        
        # Build the query
        query_str = """
            SELECT 
                c.id,
                c.content,
                c.chunk_index,
                c.page_number,
                c.section,
                c.topic,
                c.metadata,
                d.filename,
                d.title,
                1 - (c.embedding <=> :query_embedding) as similarity
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE 1=1
        """
        
        params = {'query_embedding': str(query_embedding)}
        
        # Add filters
        if filters:
            if 'topic' in filters:
                query_str += " AND c.topic = :topic"
                params['topic'] = filters['topic']
            if 'document_id' in filters:
                query_str += " AND c.document_id = :document_id"
                params['document_id'] = filters['document_id']
        
        query_str += """
            ORDER BY c.embedding <=> :query_embedding
            LIMIT :top_k
        """
        params['top_k'] = top_k
        
        # Execute query
        result = self.db.execute(text(query_str), params)
        
        # Format results
        chunks = []
        for row in result:
            chunks.append({
                'id': row.id,
                'content': row.content,
                'chunk_index': row.chunk_index,
                'page_number': row.page_number,
                'section': row.section,
                'topic': row.topic,
                'metadata': row.metadata,
                'document': {
                    'filename': row.filename,
                    'title': row.title
                },
                'similarity': float(row.similarity)
            })
        
        return chunks
    
    def get_chunk_context(self, chunk_id: int, context_size: int = 1) -> List[Dict]:
        """Get surrounding chunks for context."""
        chunk = self.db.query(Chunk).filter(Chunk.id == chunk_id).first()
        if not chunk:
            return []
        
        # Get chunks before and after
        context_chunks = self.db.query(Chunk).filter(
            Chunk.document_id == chunk.document_id,
            Chunk.chunk_index >= chunk.chunk_index - context_size,
            Chunk.chunk_index <= chunk.chunk_index + context_size
        ).order_by(Chunk.chunk_index).all()
        
        return [
            {
                'id': c.id,
                'content': c.content,
                'chunk_index': c.chunk_index
            }
            for c in context_chunks
        ]
```

### 4.2 LLM Service

Create `backend/app/services/llm_service.py`:

```python
import requests
from typing import List, Dict, Optional

class LLMService:
    """Interface with Ollama/Qwen for response generation."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen"):
        self.base_url = base_url
        self.model = model
    
    def generate_response(
        self,
        query: str,
        context_chunks: List[Dict],
        max_tokens: int = 500
    ) -> Dict:
        """Generate response using retrieved context."""
        
        # Construct prompt with context
        prompt = self._build_prompt(query, context_chunks)
        
        # Call Ollama API
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"LLM API error: {response.text}")
        
        result = response.json()
        
        return {
            'answer': result['response'],
            'model': self.model,
            'prompt_tokens': result.get('prompt_eval_count', 0),
            'completion_tokens': result.get('eval_count', 0)
        }
    
    def _build_prompt(self, query: str, context_chunks: List[Dict]) -> str:
        """Build prompt with context and query."""
        
        # Format context
        context_text = "\n\n".join([
            f"[Source: {chunk['document']['title']}, Page {chunk.get('page_number', 'N/A')}]\n{chunk['content']}"
            for chunk in context_chunks
        ])
        
        # Build prompt
        prompt = f"""You are a knowledgeable assistant specializing in LinuxONE and IBM technologies. 
Answer the user's question based on the provided context from IBM Redbooks.

Context:
{context_text}

Question: {query}

Instructions:
- Provide a clear, accurate answer based on the context
- If the context doesn't contain enough information, say so
- Include relevant details and examples when available
- Cite sources by mentioning the document name

Answer:"""
        
        return prompt
    
    def extract_topics(self, text: str) -> List[str]:
        """Extract main topics from text using LLM."""
        
        prompt = f"""Extract 2-3 main topics or keywords from the following text. 
Return only the topics as a comma-separated list.

Text: {text[:500]}

Topics:"""
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 50,
                    "temperature": 0.3
                }
            }
        )
        
        if response.status_code == 200:
            topics_text = response.json()['response'].strip()
            topics = [t.strip() for t in topics_text.split(',')]
            return topics[:3]
        
        return []
```

## Phase 5: API Implementation

### 5.1 FastAPI Main Application

Create `backend/app/main.py`:

```python
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import time

from app.config import get_settings
from app.models.database import Base, engine
from app.api.routes import router
from app.api.dependencies import get_db

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="LinuxONE RAG Knowledge Assistant",
    description="Retrieval-Augmented Generation system for LinuxONE documentation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "LinuxONE RAG Knowledge Assistant API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Check database connection
        db.execute("SELECT 1")
        
        # Check Ollama
        settings = get_settings()
        import requests
        ollama_response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=2)
        
        return {
            "status": "healthy",
            "database": "connected",
            "llm": "available" if ollama_response.status_code == 200 else "unavailable"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True
    )
```

This implementation guide provides detailed code for the core components. The next sections would cover API routes, frontend implementation, and deployment configurations.

Would you like me to continue with the remaining sections?