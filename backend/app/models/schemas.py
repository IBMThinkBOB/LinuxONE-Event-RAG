from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# Query Request/Response Models
class QueryRequest(BaseModel):
    """Request model for querying the RAG system."""
    query: str = Field(..., description="User's question", min_length=1)
    top_k: Optional[int] = Field(None, description="Number of chunks to retrieve (None=auto)", ge=1, le=20)
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filters (topic, document_id, etc.)")
    min_similarity: float = Field(0.0, description="Minimum similarity threshold", ge=0.0, le=1.0)


class SourceInfo(BaseModel):
    """Information about a source document."""
    document_id: int
    filename: str
    title: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    similarity: float


class QueryResponse(BaseModel):
    """Response model for query results."""
    answer: str = Field(..., description="Generated answer")
    sources: List[SourceInfo] = Field(..., description="Source documents used")
    retrieved_chunks: int = Field(..., description="Number of chunks retrieved")
    model: str = Field(..., description="LLM model used")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    retrieval_metrics: Optional[Dict[str, Any]] = Field(None, description="Retrieval quality metrics")


# Document Models
class DocumentBase(BaseModel):
    """Base document model."""
    filename: str
    title: Optional[str] = None
    source_type: str = "redbook"


class DocumentCreate(DocumentBase):
    """Model for creating a document."""
    total_pages: Optional[int] = None
    doc_metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(DocumentBase):
    """Response model for document information."""
    id: int
    upload_date: datetime
    total_pages: Optional[int] = None
    total_chunks: Optional[int] = None
    doc_metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response model for list of documents."""
    documents: List[DocumentResponse]
    total: int


# Chunk Models
class ChunkBase(BaseModel):
    """Base chunk model."""
    content: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    topic: Optional[str] = None


class ChunkResponse(ChunkBase):
    """Response model for chunk information."""
    id: int
    chunk_index: int
    token_count: Optional[int] = None
    document_id: int
    
    class Config:
        from_attributes = True


# Statistics Models
class StatisticsResponse(BaseModel):
    """Response model for database statistics."""
    total_documents: int
    total_chunks: int
    chunks_with_embeddings: int
    avg_chunk_tokens: float


# Health Check Models
class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    database: str
    llm: str
    embedding_service: str
    timestamp: datetime


# Ingestion Models
class IngestionRequest(BaseModel):
    """Request model for document ingestion."""
    file_path: str = Field(..., description="Path to the PDF file")


class IngestionResponse(BaseModel):
    """Response model for ingestion results."""
    document_id: int
    filename: str
    chunks_created: int
    status: str
    message: Optional[str] = None


# Error Models
class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime

# Made with Bob
