from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str
    postgres_user: str = "raguser"
    postgres_password: str = "ragpassword"
    postgres_db: str = "linuxone_rag"
    
    # LLM Provider Configuration
    llm_provider: str = "external"  # "external" or "ollama"
    
    # External LLM (BOB API) - Primary for LinuxONE
    bob_api_key: str = ""
    bob_api_base_url: str = "https://api.bob.build/v1"
    bob_model: str = "gpt-4o-mini"  # or gpt-4, claude-3-5-sonnet, etc.
    
    # Ollama (Local) - Fallback/Development
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen"
    
    # LLM Generation Settings (Context-First Hybrid RAG optimized)
    llm_api_key: str = ""  # Deprecated - use bob_api_key
    llm_max_tokens: int = 2500  # Increased for detailed, complete answers
    llm_temperature: float = 0.2  # Balanced for detailed yet focused generation
    
    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
    # RAG Configurationß
    chunk_size: int = 600  # Reduced from 500 for better semantic precision | was 300
    chunk_overlap: int = 100 # was 50
    top_k_results: int = 10  # Reduced from 10 to prevent context overload | was 5
    max_context_length: int = 2000
    
    # Context Management (prevent LLM overload)
    max_chunks_to_llm: int = 8  # Hard limit on chunks sent to LLM | was 5
    max_context_tokens: int = 1200  # Token budget for context
    
    # Retrieval Quality Settings (Hybrid RAG optimized)
    min_similarity_absolute: float = 0.4  # Absolute minimum for filtering (was 0.5)
    similarity_relative_threshold: float = 0.6  # Relative threshold (was 0.8)
    diversity_threshold: float = 0.95  # Diversity filtering (was 0.9)
    min_relevance_threshold: float = 0.2  # Minimum for query relevance (lowered for hybrid RAG)
    enable_reranking: bool = True
    enable_adaptive_filtering: bool = True
    enable_diversity_filtering: bool = True
    reranking_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Application
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_port: int = 3000
    frontend_url: str = ""  # For CORS in production
    
    # Feature Flags (LinuxONE Production)
    enable_local_embeddings: bool = True  # Set to False if using external embedding service
    enable_local_reranking: bool = True  # Set to False to disable reranking
    enable_pdf_processing: bool = True  # Set to False if PDF processing not needed
    
    class Config:
        # Look for .env in project root (parent of backend directory)
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Made with Bob
