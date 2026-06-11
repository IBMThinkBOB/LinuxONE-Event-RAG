"""
Reranking service using cross-encoder models for improved relevance scoring.

This service re-scores retrieved chunks using a cross-encoder model that processes
query-chunk pairs together, providing more accurate semantic relevance scores than
bi-encoder embeddings alone.
"""

from sentence_transformers import CrossEncoder
from typing import List, Dict, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


class RerankingService:
    """Rerank retrieved chunks using cross-encoder for better relevance."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize reranking service.
        
        Args:
            model_name: Cross-encoder model for reranking
                       Default: ms-marco-MiniLM-L-6-v2 (~80MB, optimized for passage ranking)
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the cross-encoder model."""
        try:
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            logger.info("Cross-encoder model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading cross-encoder model: {e}")
            raise
    
    def rerank_chunks(
        self,
        query: str,
        chunks: List[Dict],
        top_n: Optional[int] = None,
        return_scores: bool = True
    ) -> List[Dict]:
        """
        Rerank chunks using cross-encoder scores.
        
        The cross-encoder processes query-chunk pairs together, providing more
        accurate semantic relevance scores than cosine similarity of separate embeddings.
        
        Args:
            query: User query text
            chunks: List of retrieved chunks with content and metadata
            top_n: Optional limit on number of chunks to return (None = return all)
            return_scores: Whether to include rerank scores in output
            
        Returns:
            Reranked chunks sorted by relevance score (highest first)
        """
        if not chunks:
            logger.warning("No chunks provided for reranking")
            return []
        
        if not self.model:
            logger.error("Cross-encoder model not loaded")
            return chunks  # Return original chunks if model unavailable
        
        try:
            # Prepare query-chunk pairs for the cross-encoder
            pairs = [(query, chunk['content']) for chunk in chunks]
            
            logger.info(f"Reranking {len(chunks)} chunks with cross-encoder")
            
            # Get cross-encoder scores (higher = more relevant)
            scores = self.model.predict(pairs)
            
            # Add rerank scores to chunks and preserve original similarity
            for chunk, score in zip(chunks, scores):
                chunk['rerank_score'] = float(score)
                # Preserve original similarity score for comparison
                if 'similarity' in chunk:
                    chunk['original_similarity'] = chunk['similarity']
            
            # Sort by rerank score (descending)
            reranked = sorted(chunks, key=lambda x: x['rerank_score'], reverse=True)
            
            # Limit to top_n if specified
            if top_n and top_n > 0:
                reranked = reranked[:top_n]
            
            # Log reranking statistics
            if reranked:
                avg_score = np.mean([c['rerank_score'] for c in reranked])
                min_score = min(c['rerank_score'] for c in reranked)
                max_score = max(c['rerank_score'] for c in reranked)
                
                logger.info(
                    f"Reranking complete: {len(chunks)} → {len(reranked)} chunks | "
                    f"Scores: min={min_score:.3f}, avg={avg_score:.3f}, max={max_score:.3f}"
                )
            
            return reranked
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            # Return original chunks if reranking fails
            return chunks
    
    def get_relevance_scores(
        self,
        query: str,
        texts: List[str]
    ) -> List[float]:
        """
        Get relevance scores for a list of texts without modifying them.
        
        Args:
            query: User query
            texts: List of text strings to score
            
        Returns:
            List of relevance scores (same order as input texts)
        """
        if not texts:
            return []
        
        if not self.model:
            logger.error("Cross-encoder model not loaded")
            return [0.0] * len(texts)
        
        try:
            pairs = [(query, text) for text in texts]
            scores = self.model.predict(pairs)
            return [float(score) for score in scores]
        except Exception as e:
            logger.error(f"Error getting relevance scores: {e}")
            return [0.0] * len(texts)
    
    def compare_chunks(
        self,
        query: str,
        chunk1: str,
        chunk2: str
    ) -> Dict:
        """
        Compare relevance of two chunks for a given query.
        
        Args:
            query: User query
            chunk1: First chunk text
            chunk2: Second chunk text
            
        Returns:
            Dict with scores for both chunks and the difference
        """
        scores = self.get_relevance_scores(query, [chunk1, chunk2])
        
        return {
            'chunk1_score': scores[0],
            'chunk2_score': scores[1],
            'difference': scores[0] - scores[1],
            'more_relevant': 'chunk1' if scores[0] > scores[1] else 'chunk2'
        }


# Global reranking service instance (singleton pattern)
_reranking_service: Optional[RerankingService] = None


def get_reranking_service(
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
) -> RerankingService:
    """
    Get or create the global reranking service instance.
    
    Args:
        model_name: Cross-encoder model name
        
    Returns:
        RerankingService instance
    """
    global _reranking_service
    
    if _reranking_service is None:
        _reranking_service = RerankingService(model_name)
    
    return _reranking_service


# Made with Bob