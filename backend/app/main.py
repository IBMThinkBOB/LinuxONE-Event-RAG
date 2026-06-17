from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.routes import router
from app.config import get_settings
from app.models.db_connection import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title="LinuxONE RAG Knowledge Assistant",
    description="Retrieval-Augmented Generation system for LinuxONE documentation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware configuration
# Dynamically configure based on environment
import os

allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite default port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173"
]

# Add production frontend URL if configured
if settings.frontend_url:
    allowed_origins.append(settings.frontend_url)
    # Also add without trailing slash if present
    if settings.frontend_url.endswith('/'):
        allowed_origins.append(settings.frontend_url.rstrip('/'))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api", tags=["api"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting LinuxONE RAG Knowledge Assistant...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Log configuration
    logger.info(f"Ollama URL: {settings.ollama_base_url}")
    logger.info(f"Ollama Model: {settings.ollama_model}")
    logger.info(f"Embedding Model: {settings.embedding_model}")
    logger.info(f"Chunk Size: {settings.chunk_size}")
    logger.info(f"Top-K Results: {settings.top_k_results}")
    
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down LinuxONE RAG Knowledge Assistant...")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "LinuxONE RAG Knowledge Assistant",
        "version": "1.0.0",
        "description": "Retrieval-Augmented Generation system for LinuxONE documentation",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": {
            "query": "POST /api/query",
            "documents": "GET /api/documents",
            "statistics": "GET /api/statistics",
            "health": "GET /api/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
        log_level="info"
    )

# Made with Bob
