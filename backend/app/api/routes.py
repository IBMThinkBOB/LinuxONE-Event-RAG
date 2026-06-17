from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import time
import logging
from datetime import datetime

from app.models.db_connection import get_db
from app.models.database import Document, QueryLog
from app.models.schemas import (
    QueryRequest, QueryResponse, SourceInfo,
    DocumentResponse, DocumentListResponse,
    StatisticsResponse, HealthResponse,
    ErrorResponse
)
from app.services.embedding_service import get_embedding_service
from app.services.llm_service import get_llm_service
from app.services.retrieval_service import RetrievalService
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Query the RAG knowledge base.
    
    Args:
        request: Query request with question and parameters
        db: Database session
        
    Returns:
        QueryResponse with answer and sources
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing query: {request.query}")
        
        # Import query utilities
        from app.utils.query_utils import expand_query, get_answer_mode
        
        # Detect if query is vague and expand for better retrieval
        expanded_query = expand_query(request.query)
        answer_mode = get_answer_mode(request.query)
        
        if expanded_query != request.query:
            logger.info(f"Vague query detected - expanding for retrieval")
            logger.info(f"Answer mode: {answer_mode}")
        
        # Get services
        embedding_service = get_embedding_service(settings.embedding_model)
        
        # Get LLM service based on provider configuration
        if settings.llm_provider == "external":
            llm_service = get_llm_service(
                provider="external",
                api_key=settings.bob_api_key,
                base_url=settings.bob_api_base_url,
                model=settings.bob_model
            )
        else:
            llm_service = get_llm_service(
                provider="ollama",
                base_url=settings.ollama_base_url,
                model=settings.ollama_model
            )
        
        retrieval_service = RetrievalService(db)
        
        # Generate query embedding using EXPANDED query for better retrieval
        logger.info("Generating query embedding...")
        query_embedding = embedding_service.embed_text(expanded_query)
        
        # Use adaptive top_k if not specified
        # Limit to 5 chunks max to prevent context overload
        adaptive_top_k = request.top_k if request.top_k else 5
        logger.info(f"Retrieving chunks with enhanced pipeline (adaptive_top_k={adaptive_top_k})...")
        retrieval_result = retrieval_service.search_with_reranking(
            query=request.query,
            query_embedding=query_embedding,
            top_k=adaptive_top_k,
            filters=request.filters,
            enable_reranking=settings.enable_reranking,
            enable_filtering=settings.enable_adaptive_filtering,
            enable_diversity=settings.enable_diversity_filtering,
            min_absolute=settings.min_similarity_absolute,
            relative_threshold=settings.similarity_relative_threshold,
            diversity_threshold=settings.diversity_threshold
        )
        
        chunks = retrieval_result['chunks']
        retrieval_metrics = retrieval_result['metrics']
        
        # Check if query was truly irrelevant (confidence = 'none')
        confidence = retrieval_metrics.get('confidence_level', 'none')
        top_similarity = retrieval_metrics.get('top_similarity', 0.0)
        
        if not chunks or confidence == 'none':
            # Query is truly irrelevant (lowered threshold for hybrid RAG)
            logger.warning(
                f"Query not relevant to knowledge base: "
                f"top_similarity={top_similarity:.3f} < 0.2"
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
        
        # Log context size before LLM generation
        context_size = sum(len(chunk.get('content', '')) for chunk in chunks)
        logger.info(
            f"Sending to LLM: {len(chunks)} chunks, "
            f"~{context_size // 4} tokens, "
            f"~{context_size} characters"
        )
        
        # Generate response using LLM with ORIGINAL query and answer mode
        logger.info(f"Generating LLM response (mode: {answer_mode})...")
        llm_response = llm_service.generate_response(
            query=request.query,  # Use original query, NOT expanded
            context_chunks=chunks,
            max_context_tokens=settings.max_context_tokens,
            answer_mode=answer_mode  # Pass answer mode for structured responses
        )
        
        # Format sources
        sources = [
            SourceInfo(
                document_id=chunk['document']['id'],
                filename=chunk['document']['filename'],
                title=chunk['document']['title'],
                page_number=chunk.get('page_number'),
                section=chunk.get('section'),
                similarity=chunk['similarity']
            )
            for chunk in chunks
        ]
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Log query
        query_log = QueryLog(
            query_text=request.query,
            retrieved_chunks=len(chunks),
            response_time_ms=response_time_ms,
            query_metadata={
                'top_k': request.top_k,
                'filters': request.filters,
                'model': llm_response['model']
            }
        )
        db.add(query_log)
        db.commit()
        
        logger.info(f"Query completed in {response_time_ms}ms")
        
        return QueryResponse(
            answer=llm_response['answer'],
            sources=sources,
            retrieved_chunks=len(chunks),
            model=llm_response['model'],
            response_time_ms=response_time_ms,
            retrieval_metrics=retrieval_metrics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all documents in the knowledge base.
    
    Args:
        skip: Number of documents to skip
        limit: Maximum number of documents to return
        db: Database session
        
    Returns:
        List of documents
    """
    try:
        documents = db.query(Document).offset(skip).limit(limit).all()
        total = db.query(Document).count()
        
        return DocumentListResponse(
            documents=[DocumentResponse.from_orm(doc) for doc in documents],
            total=total
        )
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific document.
    
    Args:
        document_id: ID of the document
        db: Database session
        
    Returns:
        Document details
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID {document_id} not found"
            )
        
        return DocumentResponse.from_orm(document)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting document: {str(e)}"
        )


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get statistics about the knowledge base.
    
    Args:
        db: Database session
        
    Returns:
        Statistics about documents and chunks
    """
    try:
        retrieval_service = RetrievalService(db)
        stats = retrieval_service.get_statistics()
        
        return StatisticsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting statistics: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    
    Args:
        db: Database session
        
    Returns:
        Health status of all services
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "llm": "unknown",
        "embedding_service": "unknown",
        "timestamp": datetime.utcnow()
    }
    
    # Check database
    try:
        db.execute("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
    
    # Check LLM service
    try:
        if settings.llm_provider == "external":
            llm_service = get_llm_service(
                provider="external",
                api_key=settings.bob_api_key,
                base_url=settings.bob_api_base_url,
                model=settings.bob_model
            )
        else:
            llm_service = get_llm_service(
                provider="ollama",
                base_url=settings.ollama_base_url,
                model=settings.ollama_model
            )
        
        if llm_service.check_availability():
            health_status["llm"] = "available"
        else:
            health_status["llm"] = "unavailable"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        health_status["llm"] = "error"
        health_status["status"] = "degraded"
    
    # Check embedding service
    try:
        embedding_service = get_embedding_service(settings.embedding_model)
        if embedding_service.model is not None:
            health_status["embedding_service"] = "loaded"
        else:
            health_status["embedding_service"] = "not loaded"
            health_status["status"] = "unhealthy"
    except Exception as e:
        logger.error(f"Embedding service health check failed: {e}")
        health_status["embedding_service"] = "error"
        health_status["status"] = "unhealthy"
    
    return HealthResponse(**health_status)

# Made with Bob
