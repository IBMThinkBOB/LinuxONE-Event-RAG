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
    
    # LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen"
    llm_api_key: str = ""
    llm_max_tokens: int = 1500
    llm_temperature: float = 0.3  # Lower for more coherent, complete responses
    
    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
    # RAG Configuration
    chunk_size: int = 300  # Reduced from 500 for better semantic precision
    chunk_overlap: int = 50
    top_k_results: int = 5  # Reduced from 10 to prevent context overload
    max_context_length: int = 2000
    
    # Context Management (prevent LLM overload)
    max_chunks_to_llm: int = 5  # Hard limit on chunks sent to LLM
    max_context_tokens: int = 1200  # Token budget for context
    
    # Retrieval Quality Settings
    min_similarity_absolute: float = 0.5
    similarity_relative_threshold: float = 0.8
    diversity_threshold: float = 0.9
    enable_reranking: bool = True
    enable_adaptive_filtering: bool = True
    enable_diversity_filtering: bool = True
    reranking_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Application
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_port: int = 3000
    
    class Config:
        # Look for .env in project root (parent of backend directory)
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Made with Bob
