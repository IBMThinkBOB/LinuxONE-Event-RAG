#!/usr/bin/env python3
"""
Comprehensive evaluation script for RAG retrieval quality.
Tests the system with various query types and measures performance.
"""

import sys
import os
from pathlib import Path
import logging
import json
from typing import List, Dict
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.models.db_connection import SessionLocal
from app.services.embedding_service import get_embedding_service
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import get_llm_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_queries(file_path: str = 'backend/tests/test_queries.json') -> Dict:
    """Load test queries from JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Test queries file not found: {file_path}")
        sys.exit(1)


def evaluate_query(
    query_data: Dict,
    retrieval_service: RetrievalService,
    embedding_service,
    llm_service,
    settings
) -> Dict:
    """
    Evaluate a single query and measure quality metrics.
    
    Returns:
        Dict with evaluation results
    """
    query = query_data['query']
    query_id = query_data['id']
    category = query_data['category']
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Query {query_id}: {category}")
    logger.info(f"Question: {query}")
    logger.info(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        # Generate embedding
        query_embedding = embedding_service.embed_text(query)
        
        # Retrieve with new pipeline
        retrieval_result = retrieval_service.search_with_reranking(
            query=query,
            query_embedding=query_embedding,
            top_k=None,  # Use adaptive
            enable_reranking=settings.enable_reranking,
            enable_filtering=settings.enable_adaptive_filtering,
            enable_diversity=settings.enable_diversity_filtering,
            min_absolute=settings.min_similarity_absolute,
            relative_threshold=settings.similarity_relative_threshold,
            diversity_threshold=settings.diversity_threshold
        )
        
        chunks = retrieval_result['chunks']
        retrieval_metrics = retrieval_result['metrics']
        
        # Generate answer
        llm_response = llm_service.generate_response(
            query=query,
            context_chunks=chunks,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature
        )
        
        answer = llm_response['answer']
        
        # Calculate metrics
        retrieval_time = time.time() - start_time
        
        # Evaluate against success criteria
        success_criteria = query_data.get('success_criteria', {})
        
        # Check chunk count
        min_chunks = query_data.get('min_chunks', 0)
        max_chunks = query_data.get('max_chunks', 20)
        chunks_in_range = min_chunks <= len(chunks) <= max_chunks
        
        # Check similarity scores
        min_similarity_required = success_criteria.get('min_similarity', 0.5)
        avg_similarity = retrieval_metrics.get('avg_score', 0)
        similarity_ok = avg_similarity >= min_similarity_required
        
        # Check answer length
        min_answer_length = success_criteria.get('answer_length_min', 0)
        answer_length = len(answer)
        length_ok = answer_length >= min_answer_length
        
        # Check required terms
        must_contain = success_criteria.get('must_contain', [])
        contains_required = all(
            term.lower() in answer.lower() 
            for term in must_contain
        )
        
        # Overall pass/fail
        passed = (
            chunks_in_range and 
            similarity_ok and 
            length_ok and 
            (not must_contain or contains_required)
        )
        
        # Compile results
        result = {
            'query_id': query_id,
            'category': category,
            'query': query,
            'passed': passed,
            'retrieval_time_ms': int(retrieval_time * 1000),
            'chunks_retrieved': len(chunks),
            'chunks_in_range': chunks_in_range,
            'expected_range': f"{min_chunks}-{max_chunks}",
            'avg_similarity': round(avg_similarity, 3),
            'similarity_ok': similarity_ok,
            'min_similarity_required': min_similarity_required,
            'answer_length': answer_length,
            'length_ok': length_ok,
            'min_length_required': min_answer_length,
            'contains_required_terms': contains_required,
            'required_terms': must_contain,
            'retrieval_metrics': retrieval_metrics,
            'answer_preview': answer[:200] + '...' if len(answer) > 200 else answer,
            'top_3_sources': [
                {
                    'document': c['document']['title'],
                    'page': c.get('page_number'),
                    'score': round(c.get('rerank_score', c.get('similarity', 0)), 3)
                }
                for c in chunks[:3]
            ]
        }
        
        # Log results
        logger.info(f"✓ Chunks: {len(chunks)} (expected: {min_chunks}-{max_chunks})")
        logger.info(f"✓ Avg similarity: {avg_similarity:.3f} (min: {min_similarity_required})")
        logger.info(f"✓ Answer length: {answer_length} chars (min: {min_answer_length})")
        if must_contain:
            logger.info(f"✓ Contains required terms: {contains_required}")
        logger.info(f"{'✅ PASSED' if passed else '❌ FAILED'}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error evaluating query {query_id}: {e}", exc_info=True)
        return {
            'query_id': query_id,
            'category': category,
            'query': query,
            'passed': False,
            'error': str(e)
        }


def generate_report(results: List[Dict], output_file: str):
    """Generate evaluation report."""
    
    # Calculate summary statistics
    total_queries = len(results)
    passed_queries = sum(1 for r in results if r.get('passed', False))
    failed_queries = total_queries - passed_queries
    pass_rate = (passed_queries / total_queries * 100) if total_queries > 0 else 0
    
    # Group by category
    by_category = {}
    for result in results:
        category = result.get('category', 'unknown')
        if category not in by_category:
            by_category[category] = {'total': 0, 'passed': 0}
        by_category[category]['total'] += 1
        if result.get('passed', False):
            by_category[category]['passed'] += 1
    
    # Calculate average metrics
    avg_chunks = sum(r.get('chunks_retrieved', 0) for r in results) / total_queries
    avg_similarity = sum(r.get('avg_similarity', 0) for r in results) / total_queries
    avg_time = sum(r.get('retrieval_time_ms', 0) for r in results) / total_queries
    
    # Generate report
    report = {
        'evaluation_date': datetime.now().isoformat(),
        'summary': {
            'total_queries': total_queries,
            'passed': passed_queries,
            'failed': failed_queries,
            'pass_rate': round(pass_rate, 2),
            'avg_chunks_retrieved': round(avg_chunks, 2),
            'avg_similarity_score': round(avg_similarity, 3),
            'avg_retrieval_time_ms': round(avg_time, 2)
        },
        'by_category': {
            cat: {
                'total': stats['total'],
                'passed': stats['passed'],
                'pass_rate': round(stats['passed'] / stats['total'] * 100, 2)
            }
            for cat, stats in by_category.items()
        },
        'detailed_results': results
    }
    
    # Save report
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report


def print_summary(report: Dict):
    """Print evaluation summary to console."""
    summary = report['summary']
    by_category = report['by_category']
    
    print(f"\n{'='*80}")
    print("EVALUATION SUMMARY")
    print(f"{'='*80}")
    print(f"Date: {report['evaluation_date']}")
    print(f"\nOverall Results:")
    print(f"  Total queries: {summary['total_queries']}")
    print(f"  Passed: {summary['passed']} ✅")
    print(f"  Failed: {summary['failed']} ❌")
    print(f"  Pass rate: {summary['pass_rate']}%")
    print(f"\nPerformance Metrics:")
    print(f"  Avg chunks retrieved: {summary['avg_chunks_retrieved']}")
    print(f"  Avg similarity score: {summary['avg_similarity_score']}")
    print(f"  Avg retrieval time: {summary['avg_retrieval_time_ms']}ms")
    
    print(f"\nResults by Category:")
    for category, stats in by_category.items():
        status = "✅" if stats['pass_rate'] >= 80 else "⚠️" if stats['pass_rate'] >= 60 else "❌"
        print(f"  {status} {category}: {stats['passed']}/{stats['total']} ({stats['pass_rate']}%)")
    
    print(f"\n{'='*80}")


def main():
    """Run comprehensive evaluation."""
    logger.info("="*80)
    logger.info("RAG Retrieval Quality Evaluation")
    logger.info("="*80)
    
    # Load configuration
    settings = get_settings()
    
    # Load test queries
    test_data = load_test_queries()
    test_queries = test_data['test_queries']
    
    logger.info(f"Loaded {len(test_queries)} test queries")
    logger.info(f"Categories: {', '.join(test_data['metadata']['categories'])}")
    
    # Initialize services
    logger.info("\nInitializing services...")
    embedding_service = get_embedding_service(settings.embedding_model)
    llm_service = get_llm_service(settings.ollama_base_url, settings.ollama_model)
    db = SessionLocal()
    retrieval_service = RetrievalService(db)
    
    # Run evaluation
    logger.info("\nStarting evaluation...")
    results = []
    
    for i, query_data in enumerate(test_queries, 1):
        logger.info(f"\nProgress: {i}/{len(test_queries)}")
        result = evaluate_query(
            query_data,
            retrieval_service,
            embedding_service,
            llm_service,
            settings
        )
        results.append(result)
    
    # Generate report
    output_file = 'backend/tests/evaluation_report.json'
    logger.info(f"\nGenerating report: {output_file}")
    report = generate_report(results, output_file)
    
    # Print summary
    print_summary(report)
    
    # Cleanup
    db.close()
    
    logger.info(f"\nEvaluation complete!")
    logger.info(f"Detailed report saved to: {output_file}")
    
    # Exit with appropriate code
    if report['summary']['pass_rate'] >= 80:
        logger.info("✅ System passed evaluation (≥80% pass rate)")
        sys.exit(0)
    elif report['summary']['pass_rate'] >= 60:
        logger.warning("⚠️  System needs improvement (60-80% pass rate)")
        sys.exit(0)
    else:
        logger.error("❌ System failed evaluation (<60% pass rate)")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
