#!/usr/bin/env python3
"""
Quick test script for Phase 1 retrieval improvements.
Tests the new multi-stage pipeline with various query types.
"""

import sys
import os
from pathlib import Path
import logging
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.models.db_connection import SessionLocal
from app.services.embedding_service import get_embedding_service
from app.services.retrieval_service import RetrievalService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_query(query: str, top_k: int = 10):
    """Test a single query through the new pipeline."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing Query: {query}")
    logger.info(f"top_k: {top_k}")
    logger.info(f"{'='*80}\n")
    
    settings = get_settings()
    db = SessionLocal()
    
    try:
        # Get services
        embedding_service = get_embedding_service(settings.embedding_model)
        retrieval_service = RetrievalService(db)
        
        # Generate embedding
        logger.info("Generating query embedding...")
        query_embedding = embedding_service.embed_text(query)
        
        # Run new pipeline
        logger.info("Running multi-stage retrieval pipeline...")
        result = retrieval_service.search_with_reranking(
            query=query,
            query_embedding=query_embedding,
            top_k=top_k,
            enable_reranking=settings.enable_reranking,
            enable_filtering=settings.enable_adaptive_filtering,
            enable_diversity=settings.enable_diversity_filtering,
            min_absolute=settings.min_similarity_absolute,
            relative_threshold=settings.similarity_relative_threshold,
            diversity_threshold=settings.diversity_threshold
        )
        
        chunks = result['chunks']
        metrics = result['metrics']
        
        # Display results
        logger.info(f"\n{'='*80}")
        logger.info("RESULTS")
        logger.info(f"{'='*80}")
        logger.info(f"Final chunks: {len(chunks)}")
        logger.info(f"\nPipeline Metrics:")
        logger.info(f"  Initial candidates: {metrics['initial_candidates']}")
        logger.info(f"  After similarity filter: {metrics['after_similarity_filter']}")
        logger.info(f"  After reranking: {metrics['after_reranking']}")
        logger.info(f"  Final chunks: {metrics['final_chunks']}")
        logger.info(f"\nQuality Metrics:")
        logger.info(f"  Average score: {metrics['avg_score']:.3f}")
        logger.info(f"  Min score: {metrics['min_score']:.3f}")
        logger.info(f"  Max score: {metrics['max_score']:.3f}")
        logger.info(f"  Score std: {metrics['score_std']:.3f}")
        logger.info(f"  Score range: {metrics['score_range']:.3f}")
        
        logger.info(f"\nTop 3 Chunks:")
        for i, chunk in enumerate(chunks[:3], 1):
            score = chunk.get('rerank_score', chunk.get('similarity', 0))
            logger.info(f"\n  {i}. Score: {score:.3f}")
            logger.info(f"     Document: {chunk['document']['title']}")
            logger.info(f"     Page: {chunk.get('page_number', 'N/A')}")
            logger.info(f"     Section: {chunk.get('section', 'N/A')}")
            logger.info(f"     Content preview: {chunk['content'][:150]}...")
        
        return {
            'query': query,
            'top_k': top_k,
            'chunks_returned': len(chunks),
            'metrics': metrics,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Error testing query: {e}", exc_info=True)
        return {
            'query': query,
            'top_k': top_k,
            'success': False,
            'error': str(e)
        }
    finally:
        db.close()


def main():
    """Run test suite."""
    logger.info("="*80)
    logger.info("Phase 1 Retrieval Pipeline Test Suite")
    logger.info("="*80)
    
    # Test queries
    test_cases = [
        {
            'name': 'Broad Query',
            'query': 'What is LinuxONE?',
            'top_k': 10,
            'expected': 'Should handle high top_k well, return comprehensive info'
        },
        {
            'name': 'Specific Query',
            'query': 'How do I configure TLS encryption on LinuxONE?',
            'top_k': 10,
            'expected': 'Should filter to TLS-specific content only'
        },
        {
            'name': 'Multi-Aspect Query',
            'query': 'What are the security and performance benefits of LinuxONE?',
            'top_k': 10,
            'expected': 'Should return diverse chunks covering both aspects'
        },
        {
            'name': 'Edge Case',
            'query': 'Tell me about quantum computing',
            'top_k': 10,
            'expected': 'Should filter out most chunks, return few or none'
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n\n{'#'*80}")
        logger.info(f"Test Case {i}/{len(test_cases)}: {test_case['name']}")
        logger.info(f"Expected: {test_case['expected']}")
        logger.info(f"{'#'*80}")
        
        result = test_query(test_case['query'], test_case['top_k'])
        result['test_name'] = test_case['name']
        result['expected'] = test_case['expected']
        results.append(result)
    
    # Summary
    logger.info(f"\n\n{'='*80}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*80}")
    
    successful = sum(1 for r in results if r['success'])
    logger.info(f"Tests run: {len(results)}")
    logger.info(f"Successful: {successful}/{len(results)}")
    
    logger.info(f"\nResults by test:")
    for result in results:
        status = "✓" if result['success'] else "✗"
        logger.info(f"  {status} {result['test_name']}: {result.get('chunks_returned', 0)} chunks")
    
    # Save results
    output_file = Path(__file__).parent / 'test_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nDetailed results saved to: {output_file}")
    
    logger.info(f"\n{'='*80}")
    logger.info("Phase 1 testing complete!")
    logger.info(f"{'='*80}\n")


if __name__ == "__main__":
    main()

# Made with Bob
