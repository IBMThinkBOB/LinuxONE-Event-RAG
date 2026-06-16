from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class RetrievalService:
    """Handle vector similarity search and retrieval."""
    
    def __init__(self, db: Session):
        """
        Initialize the retrieval service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def search_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict] = None,
        min_similarity: float = 0.0
    ) -> List[Dict]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query_embedding: Query vector embedding
            top_k: Number of results to return
            filters: Optional filters (topic, document_id, etc.)
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
            
        Returns:
            List of similar chunks with metadata and similarity scores
        """
        try:
            # Build the query
            # Format embedding as PostgreSQL array literal for casting
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            query_str = """
                SELECT
                    c.id,
                    c.content,
                    c.chunk_index,
                    c.page_number,
                    c.section,
                    c.topic,
                    c.chunk_metadata,
                    d.id as document_id,
                    d.filename,
                    d.title,
                    1 - (c.embedding <=> CAST(:embedding AS vector)) as similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.embedding IS NOT NULL
            """
            
            params = {'embedding': embedding_str}
            
            # Add filters
            if filters:
                if 'topic' in filters and filters['topic']:
                    query_str += " AND c.topic = :topic"
                    params['topic'] = filters['topic']
                if 'document_id' in filters and filters['document_id']:
                    query_str += " AND c.document_id = :document_id"
                    params['document_id'] = filters['document_id']
                if 'section' in filters and filters['section']:
                    query_str += " AND c.section ILIKE :section"
                    params['section'] = f"%{filters['section']}%"
            
            # Add similarity threshold
            if min_similarity > 0:
                query_str += " AND (1 - (c.embedding <=> CAST(:embedding AS vector))) >= :min_similarity"
                params['min_similarity'] = str(min_similarity)
            
            # Order by similarity and limit
            query_str += """
                ORDER BY c.embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """
            params['top_k'] = str(top_k)
            
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
                    'chunk_metadata': row.chunk_metadata,
                    'document': {
                        'id': row.document_id,
                        'filename': row.filename,
                        'title': row.title
                    },
                    'similarity': float(row.similarity)
                })
            
            logger.info(f"Retrieved {len(chunks)} chunks with similarity >= {min_similarity}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            raise
    def filter_by_adaptive_threshold(
        self,
        chunks: List[Dict],
        min_absolute: float = 0.5,
        relative_threshold: float = 0.8,
        score_key: str = 'similarity'
    ) -> List[Dict]:
        """
        Filter chunks using adaptive threshold based on score distribution.
        
        Strategy:
        1. Absolute minimum (e.g., 0.5) - hard floor for quality
        2. Relative threshold - keep chunks within X% of top score
        3. Score gap detection - drop chunks after large gap
        
        Args:
            chunks: List of chunks with scores
            min_absolute: Absolute minimum score threshold
            relative_threshold: Relative threshold as fraction of top score (0-1)
            score_key: Key to use for scoring ('similarity' or 'rerank_score')
            
        Returns:
            Filtered chunks
        """
        if not chunks:
            return []
        
        # Sort by score descending
        sorted_chunks = sorted(chunks, key=lambda x: x.get(score_key, 0), reverse=True)
        
        # Apply absolute minimum
        filtered = [c for c in sorted_chunks if c.get(score_key, 0) >= min_absolute]
        
        if not filtered:
            logger.warning(f"No chunks passed absolute threshold {min_absolute}")
            return []
        
        # Calculate relative threshold (e.g., 80% of top score)
        top_score = filtered[0].get(score_key, 0)
        relative_min = top_score * relative_threshold
        
        # Apply relative threshold
        filtered = [c for c in filtered if c.get(score_key, 0) >= relative_min]
        
        # Detect score gaps (drop after 20% drop from previous)
        final_chunks = [filtered[0]]  # Always keep top chunk
        for i in range(1, len(filtered)):
            prev_score = filtered[i-1].get(score_key, 0)
            curr_score = filtered[i].get(score_key, 0)
            
            # If score drops more than 20%, stop
            if curr_score < prev_score * 0.8:
                logger.info(f"Score gap detected at position {i}: {prev_score:.3f} -> {curr_score:.3f}")
                break
            
            final_chunks.append(filtered[i])
        
        logger.info(
            f"Adaptive filter: {len(chunks)} → {len(final_chunks)} chunks "
            f"(absolute>{min_absolute}, relative>{relative_min:.3f})"
        )
        return final_chunks
    
    def filter_by_diversity(
        self,
        chunks: List[Dict],
        similarity_threshold: float = 0.9,
        max_chunks: Optional[int] = None
    ) -> List[Dict]:
        """
        Remove redundant chunks using content similarity.
        
        Strategy: Keep chunks that are sufficiently different from already-selected chunks.
        Uses greedy selection to maximize diversity while preserving relevance order.
        
        Args:
            chunks: List of chunks (should be pre-sorted by relevance)
            similarity_threshold: Max similarity between kept chunks (0-1)
            max_chunks: Optional maximum number of chunks to return
            
        Returns:
            Diverse set of chunks
        """
        if not chunks or len(chunks) <= 1:
            return chunks
        
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            # Need to fetch embeddings for diversity calculation
            # Get chunk IDs
            chunk_ids = [c['id'] for c in chunks]
            
            # Fetch embeddings from database
            query_str = """
                SELECT id, embedding
                FROM chunks
                WHERE id = ANY(:chunk_ids)
            """
            result = self.db.execute(text(query_str), {'chunk_ids': chunk_ids})
            
            # Build embedding lookup
            embedding_lookup = {}
            for row in result:
                if row.embedding:
                    embedding_lookup[row.id] = row.embedding
            
            # Check if we have embeddings for all chunks
            if len(embedding_lookup) != len(chunks):
                logger.warning(
                    f"Missing embeddings for some chunks, skipping diversity filter "
                    f"({len(embedding_lookup)}/{len(chunks)} have embeddings)"
                )
                return chunks[:max_chunks] if max_chunks else chunks
            
            # Build embedding matrix in same order as chunks
            embeddings = np.array([embedding_lookup[c['id']] for c in chunks])
            
            # Calculate pairwise similarities
            similarities = cosine_similarity(embeddings)
            
            # Greedy selection: keep chunks that are different enough
            selected_indices = [0]  # Always keep top chunk
            
            for i in range(1, len(chunks)):
                # Check similarity to all selected chunks
                is_diverse = True
                for j in selected_indices:
                    if similarities[i][j] > similarity_threshold:
                        is_diverse = False
                        logger.debug(
                            f"Chunk {i} too similar to chunk {j} "
                            f"(similarity={similarities[i][j]:.3f})"
                        )
                        break
                
                if is_diverse:
                    selected_indices.append(i)
                    
                    # Stop if we've reached max_chunks
                    if max_chunks and len(selected_indices) >= max_chunks:
                        break
            
            diverse_chunks = [chunks[i] for i in selected_indices]
            logger.info(
                f"Diversity filter: {len(chunks)} → {len(diverse_chunks)} chunks "
                f"(threshold={similarity_threshold})"
            )
            
            return diverse_chunks
            
        except ImportError:
            logger.warning("scikit-learn not available, skipping diversity filter")
            return chunks[:max_chunks] if max_chunks else chunks
        except Exception as e:
            logger.error(f"Error in diversity filtering: {e}")
            return chunks[:max_chunks] if max_chunks else chunks
    
    def calculate_retrieval_metrics(self, chunks: List[Dict], score_key: str = 'similarity') -> Dict:
        """
        Calculate quality metrics for retrieved chunks.
        
        Args:
            chunks: List of chunks with scores
            score_key: Key to use for scoring
            
        Returns:
            Dict with metrics like score distribution, diversity, etc.
        """
        if not chunks:
            return {
                'num_chunks': 0,
                'avg_score': 0.0,
                'min_score': 0.0,
                'max_score': 0.0,
                'score_std': 0.0,
                'score_range': 0.0
            }
        
        import numpy as np
        scores = [c.get(score_key, 0) for c in chunks]
        
        return {
            'num_chunks': len(chunks),
            'avg_score': float(np.mean(scores)),
            'min_score': float(min(scores)),
            'max_score': float(max(scores)),
            'score_std': float(np.std(scores)) if len(scores) > 1 else 0.0,
            'score_range': float(max(scores) - min(scores))
        }
    
    def _check_relevance_threshold(
        self,
        chunks: List[Dict],
        min_relevance: float = 0.2
    ) -> tuple:
        """
        Check if top chunks meet minimum relevance threshold.
        
        Args:
            chunks: Retrieved chunks with similarity scores
            min_relevance: Minimum similarity to consider relevant (lowered for hybrid RAG)
            
        Returns:
            (is_relevant, top_similarity)
        """
        if not chunks:
            return False, 0.0
        
        # Check top chunk similarity
        top_similarity = chunks[0].get('similarity', 0.0)
        is_relevant = top_similarity >= min_relevance
        
        logger.info(
            f"Relevance check: top_similarity={top_similarity:.3f}, "
            f"threshold={min_relevance}, relevant={is_relevant}"
        )
        
        return is_relevant, top_similarity
    
    def search_with_reranking(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
        enable_reranking: bool = True,
        enable_filtering: bool = True,
        enable_diversity: bool = True,
        min_absolute: float = 0.5,
        relative_threshold: float = 0.8,
        diversity_threshold: float = 0.9,
        min_relevance: float = 0.2
    ) -> Dict:
        """
        Multi-stage retrieval pipeline with smart relevance checking.
        
        Pipeline:
        1. Vector search (retrieve top_k * 2 candidates)
        2. Relevance check (fail if top_similarity < min_relevance)
        3. Adaptive similarity filtering
        4. Cross-encoder reranking
        5. Diversity filtering
        6. Return top N high-quality chunks
        
        Args:
            query: User query text
            query_embedding: Query embedding vector
            top_k: Target number of chunks to return
            filters: Optional metadata filters
            enable_reranking: Whether to use cross-encoder reranking
            enable_filtering: Whether to apply adaptive filtering
            enable_diversity: Whether to apply diversity filtering
            min_absolute: Absolute minimum similarity score
            relative_threshold: Relative threshold as fraction of top score
            diversity_threshold: Maximum similarity between kept chunks
            min_relevance: Minimum similarity for query to be considered relevant (lowered for hybrid RAG)
            
        Returns:
            Dict with chunks and retrieval metrics
        """
        from app.services.reranking_service import get_reranking_service
        
        metrics = {
            'initial_candidates': 0,
            'after_similarity_filter': 0,
            'after_reranking': 0,
            'final_chunks': 0,
            'confidence_level': 'none',
            'top_similarity': 0.0,
            'pipeline_stages': []
        }
        
        # Stage 1: Vector search (retrieve more candidates)
        candidate_k = top_k * 2
        logger.info(f"Stage 1: Retrieving {candidate_k} candidates via vector search")
        
        candidates = self.search_similar_chunks(
            query_embedding=query_embedding,
            top_k=candidate_k,
            filters=filters,
            min_similarity=0.0  # No filtering yet
        )
        metrics['initial_candidates'] = len(candidates)
        metrics['pipeline_stages'].append({
            'stage': 'vector_search',
            'chunks': len(candidates)
        })
        
        if not candidates:
            logger.error("CRITICAL: No candidates retrieved from vector search")
            return {'chunks': [], 'metrics': metrics}
        
        # Stage 2: Relevance check (CRITICAL - fail if truly irrelevant)
        is_relevant, top_sim = self._check_relevance_threshold(
            candidates,
            min_relevance=min_relevance
        )
        metrics['top_similarity'] = top_sim
        
        # If top match is below relevance threshold, query is irrelevant
        if not is_relevant:
            logger.warning(
                f"Query not relevant to knowledge base: "
                f"top_similarity={top_sim:.3f} < {min_relevance}"
            )
            return {'chunks': [], 'metrics': metrics}
        
        # Query is relevant, proceed with filtering
        logger.info(f"Query is relevant: top_similarity={top_sim:.3f}")
        
        # Stage 3: Adaptive similarity filtering
        unfiltered_candidates = candidates.copy()  # Keep for fallback
        
        if enable_filtering:
            logger.info("Stage 3: Applying adaptive similarity filter")
            filtered = self.filter_by_adaptive_threshold(
                candidates,
                min_absolute=min_absolute,
                relative_threshold=relative_threshold,
                score_key='similarity'
            )
            
            # If filtering removed everything but query is relevant, use top chunks
            if not filtered:
                logger.warning(
                    f"Filtering removed all chunks but query is relevant "
                    f"(top_sim={top_sim:.3f}), using top {top_k} unfiltered"
                )
                filtered = unfiltered_candidates[:top_k]
            
            candidates = filtered
            metrics['after_similarity_filter'] = len(candidates)
            metrics['pipeline_stages'].append({
                'stage': 'similarity_filter',
                'chunks': len(candidates)
            })
        else:
            metrics['after_similarity_filter'] = len(candidates)
        
        # Stage 4: Cross-encoder reranking
        if enable_reranking and candidates:
            logger.info("Stage 3: Reranking with cross-encoder")
            try:
                reranker = get_reranking_service()
                candidates = reranker.rerank_chunks(query, candidates)
                metrics['after_reranking'] = len(candidates)
                metrics['pipeline_stages'].append({
                    'stage': 'reranking',
                    'chunks': len(candidates)
                })
            except Exception as e:
                logger.error(f"Reranking failed: {e}, continuing without reranking")
                metrics['after_reranking'] = len(candidates)
        else:
            metrics['after_reranking'] = len(candidates)
        
        # Stage 4: Diversity filtering with hard limit
        if enable_diversity and candidates:
            logger.info("Stage 4: Applying diversity filter")
            # Hard limit: never more than 5 chunks to LLM to prevent context overload
            safe_max_chunks = min(top_k, 5)
            candidates = self.filter_by_diversity(
                candidates,
                similarity_threshold=diversity_threshold,
                max_chunks=safe_max_chunks
            )
            logger.info(f"Enforced hard limit: {len(candidates)} chunks (max={safe_max_chunks})")
            metrics['pipeline_stages'].append({
                'stage': 'diversity_filter',
                'chunks': len(candidates)
            })
        else:
            # Just limit to safe maximum (5 chunks)
            candidates = candidates[:5]
            logger.info(f"No diversity filter: limited to {len(candidates)} chunks (hard max=5)")
        
        metrics['final_chunks'] = len(candidates)
        
        # Calculate quality metrics
        score_key = 'rerank_score' if enable_reranking else 'similarity'
        quality_metrics = self.calculate_retrieval_metrics(candidates, score_key)
        metrics.update(quality_metrics)
        
        # Calculate confidence level based on average similarity
        if candidates:
            avg_sim = sum(c.get('similarity', 0) for c in candidates) / len(candidates)
            if avg_sim >= 0.6:
                metrics['confidence_level'] = 'high'
            elif avg_sim >= 0.4:
                metrics['confidence_level'] = 'medium'
            elif avg_sim >= 0.3:
                metrics['confidence_level'] = 'low'
            else:
                metrics['confidence_level'] = 'none'
        
        logger.info(
            f"Retrieval complete: {len(candidates)} chunks, "
            f"confidence={metrics['confidence_level']}, "
            f"top_sim={top_sim:.3f}, "
            f"avg_sim={metrics.get('avg_score', 0):.3f}"
        )
        
        return {
            'chunks': candidates,
            'metrics': metrics
        }
    
    
    def get_chunk_context(
        self,
        chunk_id: int,
        context_size: int = 1
    ) -> List[Dict]:
        """
        Get surrounding chunks for additional context.
        
        Args:
            chunk_id: ID of the central chunk
            context_size: Number of chunks before and after to retrieve
            
        Returns:
            List of chunks including the central chunk and its context
        """
        try:
            query_str = """
                SELECT 
                    c.id,
                    c.content,
                    c.chunk_index,
                    c.page_number,
                    c.section,
                    d.title as document_title
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.document_id = (SELECT document_id FROM chunks WHERE id = :chunk_id)
                AND c.chunk_index >= (SELECT chunk_index - :context_size FROM chunks WHERE id = :chunk_id)
                AND c.chunk_index <= (SELECT chunk_index + :context_size FROM chunks WHERE id = :chunk_id)
                ORDER BY c.chunk_index
            """
            
            result = self.db.execute(
                text(query_str),
                {'chunk_id': chunk_id, 'context_size': context_size}
            )
            
            chunks = []
            for row in result:
                chunks.append({
                    'id': row.id,
                    'content': row.content,
                    'chunk_index': row.chunk_index,
                    'page_number': row.page_number,
                    'section': row.section,
                    'document_title': row.document_title
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error getting chunk context: {e}")
            raise
    
    def get_document_chunks(
        self,
        document_id: int,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get all chunks for a specific document.
        
        Args:
            document_id: ID of the document
            limit: Optional limit on number of chunks
            
        Returns:
            List of chunks from the document
        """
        try:
            query_str = """
                SELECT 
                    c.id,
                    c.content,
                    c.chunk_index,
                    c.page_number,
                    c.section,
                    c.topic
                FROM chunks c
                WHERE c.document_id = :document_id
                ORDER BY c.chunk_index
            """
            
            if limit:
                query_str += " LIMIT :limit"
                result = self.db.execute(
                    text(query_str),
                    {'document_id': document_id, 'limit': limit}
                )
            else:
                result = self.db.execute(
                    text(query_str),
                    {'document_id': document_id}
                )
            
            chunks = []
            for row in result:
                chunks.append({
                    'id': row.id,
                    'content': row.content,
                    'chunk_index': row.chunk_index,
                    'page_number': row.page_number,
                    'section': row.section,
                    'topic': row.topic
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error getting document chunks: {e}")
            raise
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about the vector database.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            stats_query = """
                SELECT 
                    COUNT(DISTINCT d.id) as total_documents,
                    COUNT(c.id) as total_chunks,
                    COUNT(c.embedding) as chunks_with_embeddings,
                    AVG(c.token_count) as avg_chunk_tokens
                FROM documents d
                LEFT JOIN chunks c ON d.id = c.document_id
            """
            
            result = self.db.execute(text(stats_query)).fetchone()
            
            return {
                'total_documents': result.total_documents or 0,
                'total_chunks': result.total_chunks or 0,
                'chunks_with_embeddings': result.chunks_with_embeddings or 0,
                'avg_chunk_tokens': float(result.avg_chunk_tokens) if result.avg_chunk_tokens else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'total_documents': 0,
                'total_chunks': 0,
                'chunks_with_embeddings': 0,
                'avg_chunk_tokens': 0.0
            }

# Made with Bob
