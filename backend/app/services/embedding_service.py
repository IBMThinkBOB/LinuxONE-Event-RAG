from typing import List, Union
import numpy as np
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings using SentenceTransformers."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the SentenceTransformer model to use
        """
        self.model_name = model_name
        self.model = None
        self.dimension = None
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model with lazy import."""
        try:
            # Lazy import - only load when actually needed
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.dimension}")
        except ImportError as e:
            logger.error(
                "sentence-transformers not installed. "
                "Install with: pip install -r requirements-ai.txt"
            )
            raise RuntimeError(
                "Local embedding generation requires sentence-transformers. "
                "Install AI dependencies or use external embedding service."
            ) from e
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
        
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.dimension
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def embed_batch(self, texts: List[str], batch_size: int = 32, show_progress: bool = True) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            show_progress: Whether to show progress bar
            
        Returns:
            List of embedding vectors
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
        
        if not texts:
            return []
        
        try:
            logger.info(f"Generating embeddings for {len(texts)} texts")
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=show_progress
            )
            logger.info("Embeddings generated successfully")
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Compute cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        return {
            'model_name': self.model_name,
            'embedding_dimension': self.dimension,
            'max_seq_length': self.model.max_seq_length if self.model else None
        }


# Global embedding service instance
_embedding_service = None


def get_embedding_service(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> EmbeddingService:
    """
    Get or create the global embedding service instance.
    
    Args:
        model_name: Name of the model to use
        
    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name)
    return _embedding_service

# Made with Bob
