from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime

Base = declarative_base()


class Document(Base):
    """Document model representing a PDF file."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, nullable=False)
    title = Column(String(500))
    source_type = Column(String(50), default="redbook")
    upload_date = Column(DateTime, default=datetime.utcnow)
    total_pages = Column(Integer)
    total_chunks = Column(Integer)
    doc_metadata = Column(JSON, default={})
    
    # Relationship to chunks
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """Chunk model representing a text chunk with embedding."""
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384))  # 384 dimensions for all-MiniLM-L6-v2
    token_count = Column(Integer)
    page_number = Column(Integer)
    section = Column(String(255))
    topic = Column(String(255))
    chunk_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to document
    document = relationship("Document", back_populates="chunks")


class QueryLog(Base):
    """Query log model for analytics."""
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    retrieved_chunks = Column(Integer)
    response_time_ms = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    query_metadata = Column(JSON, default={})

# Made with Bob
