#!/usr/bin/env python3
"""
Evaluation script for Hybrid RAG implementation.

Tests the updated prompt system with a representative set of queries
across different categories to assess answer quality improvements.

Usage:
    python backend/scripts/evaluate_hybrid_rag.py
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.db_connection import get_db
from app.services.embedding_service import get_embedding_service
from app.services.llm_service import get_llm_service
from app.services.retrieval_service import RetrievalService
from app.config import get_settings

# Test queries organized by category
TEST_QUERIES = {
    "broad_conceptual": [
        "What is LinuxONE?",
        "What are the key features of LinuxONE?",
        "What are the benefits of LinuxONE?",
    ],
    "technical_specific": [
        "How does LinuxONE ensure high availability?",
        "What AI frameworks are supported on LinuxONE?",
        "What are LinuxONE hardware capabilities?",
        "How does PR/SM work on LinuxONE?",
    ],
    "performance_architecture": [
        "What are the performance benchmarks for LinuxONE?",
        "How does LinuxONE handle scaling?",
        "What is the memory architecture of LinuxONE?",
    ],
    "business_use_case": [
        "What are LinuxONE's enterprise applications in finance?",
        "What workloads are well suited for LinuxONE?",
        "How does LinuxONE support cloud-native applications?",
    ],
}


def evaluate_query(
    query: str,
    embedding_service,
    llm_service,
    retrieval_service,
    settings
) -> Dict:
    """
    Evaluate a single query and return detailed results.
    
    Returns:
        Dictionary with query, answer, metadata, and timing
    """
    start_time = time.time()
    
    try:
        # Generate embedding
        query_embedding = embedding_service.embed_text(query)
        
        # Retrieve chunks
        retrieval_result = retrieval_service.search_with_reranking(
            query=query,
            query_embedding=query_embedding,
            top_k=5,
            enable_reranking=settings.enable_reranking,
            enable_filtering=settings.enable_adaptive_filtering,
            enable_diversity=settings.enable_diversity_filtering,
            min_absolute=settings.min_similarity_absolute,
            relative_threshold=settings.similarity_relative_threshold,
            diversity_threshold=settings.diversity_threshold
        )
        
        chunks = retrieval_result['chunks']
        retrieval_metrics = retrieval_result['metrics']
        
        if not chunks:
            return {
                'query': query,
                'status': 'no_chunks',
                'error': 'No relevant chunks retrieved',
                'elapsed_time': time.time() - start_time
            }
        
        # Generate response
        llm_response = llm_service.generate_response(
            query=query,
            context_chunks=chunks,
            max_context_tokens=settings.max_context_tokens,
            use_evidence_extraction=True  # Test with evidence extraction
        )
        
        elapsed_time = time.time() - start_time
        
        return {
            'query': query,
            'answer': llm_response['answer'],
            'status': llm_response.get('status', 'unknown'),
            'repair_strategy': llm_response.get('repair_strategy', 'none'),
            'chunks_retrieved': len(chunks),
            'retrieval_confidence': retrieval_metrics.get('confidence_level', 'unknown'),
            'top_similarity': retrieval_metrics.get('top_similarity', 0.0),
            'sources': [
                {
                    'title': chunk['document']['title'],
                    'page': chunk.get('page_number'),
                    'similarity': chunk['similarity']
                }
                for chunk in chunks[:3]  # Top 3 sources
            ],
            'elapsed_time': elapsed_time,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            'query': query,
            'status': 'error',
            'error': str(e),
            'elapsed_time': time.time() - start_time
        }


def print_result(result: Dict, verbose: bool = True):
    """Print evaluation result in a readable format."""
    print(f"\n{'='*80}")
    print(f"Query: {result['query']}")
    print(f"{'='*80}")
    
    if result['status'] == 'error':
        print(f"❌ ERROR: {result['error']}")
        return
    
    if result['status'] == 'no_chunks':
        print(f"⚠️  NO CHUNKS: {result['error']}")
        return
    
    # Answer
    print(f"\n📝 Answer ({len(result['answer'])} chars):")
    print(f"{result['answer'][:500]}...")  # First 500 chars
    
    # Metadata
    print(f"\n📊 Metadata:")
    print(f"  Status: {result['status']}")
    print(f"  Repair Strategy: {result['repair_strategy']}")
    print(f"  Chunks Retrieved: {result['chunks_retrieved']}")
    print(f"  Retrieval Confidence: {result['retrieval_confidence']}")
    print(f"  Top Similarity: {result['top_similarity']:.3f}")
    print(f"  Elapsed Time: {result['elapsed_time']:.2f}s")
    
    # Sources
    if verbose and 'sources' in result:
        print(f"\n📚 Top Sources:")
        for i, source in enumerate(result['sources'], 1):
            print(f"  {i}. {source['title']} (Page {source['page']}, Sim: {source['similarity']:.3f})")


def run_evaluation(output_file: str | None = None, verbose: bool = True):
    """
    Run full evaluation across all test queries.
    
    Args:
        output_file: Optional path to save results as JSON
        verbose: Whether to print detailed results
    """
    print("="*80)
    print("HYBRID RAG EVALUATION")
    print("="*80)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    
    # Initialize services
    settings = get_settings()
    db = next(get_db())
    embedding_service = get_embedding_service(settings.embedding_model)
    llm_service = get_llm_service(settings.ollama_base_url, settings.ollama_model)
    retrieval_service = RetrievalService(db)
    
    # Run evaluation
    all_results = {}
    total_queries = sum(len(queries) for queries in TEST_QUERIES.values())
    current_query = 0
    
    for category, queries in TEST_QUERIES.items():
        print(f"\n{'='*80}")
        print(f"Category: {category.upper().replace('_', ' ')}")
        print(f"{'='*80}")
        
        category_results = []
        
        for query in queries:
            current_query += 1
            print(f"\n[{current_query}/{total_queries}] Evaluating: {query}")
            
            result = evaluate_query(
                query,
                embedding_service,
                llm_service,
                retrieval_service,
                settings
            )
            
            category_results.append(result)
            
            if verbose:
                print_result(result, verbose=True)
        
        all_results[category] = category_results
    
    # Summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}")
    
    total_success = 0
    total_errors = 0
    total_no_chunks = 0
    total_repairs = 0
    total_time = 0
    
    for category, results in all_results.items():
        success = sum(1 for r in results if r['status'] not in ['error', 'no_chunks'])
        errors = sum(1 for r in results if r['status'] == 'error')
        no_chunks = sum(1 for r in results if r['status'] == 'no_chunks')
        repairs = sum(1 for r in results if r.get('repair_strategy', 'none') != 'none')
        avg_time = sum(r['elapsed_time'] for r in results) / len(results)
        
        total_success += success
        total_errors += errors
        total_no_chunks += no_chunks
        total_repairs += repairs
        total_time += sum(r['elapsed_time'] for r in results)
        
        print(f"\n{category.upper().replace('_', ' ')}:")
        print(f"  Success: {success}/{len(results)}")
        print(f"  Errors: {errors}")
        print(f"  No Chunks: {no_chunks}")
        print(f"  Repairs: {repairs}")
        print(f"  Avg Time: {avg_time:.2f}s")
    
    print(f"\nOVERALL:")
    print(f"  Total Queries: {total_queries}")
    print(f"  Success Rate: {total_success}/{total_queries} ({100*total_success/total_queries:.1f}%)")
    print(f"  Error Rate: {total_errors}/{total_queries} ({100*total_errors/total_queries:.1f}%)")
    print(f"  Repair Rate: {total_repairs}/{total_success} ({100*total_repairs/total_success:.1f}% of successful)")
    print(f"  Total Time: {total_time:.2f}s")
    print(f"  Avg Time: {total_time/total_queries:.2f}s")
    
    # Save results
    if output_file:
        output_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'settings': {
                'model': settings.ollama_model,
                'max_context_tokens': settings.max_context_tokens,
                'enable_reranking': settings.enable_reranking,
                'evidence_extraction': True
            },
            'results': all_results,
            'summary': {
                'total_queries': total_queries,
                'success_rate': total_success / total_queries,
                'error_rate': total_errors / total_queries,
                'repair_rate': total_repairs / total_success if total_success > 0 else 0,
                'avg_time': total_time / total_queries
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n✅ Results saved to: {output_file}")
    
    print(f"\nCompleted at: {datetime.utcnow().isoformat()}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate Hybrid RAG implementation')
    parser.add_argument(
        '--output',
        '-o',
        default='hybrid_rag_evaluation_results.json',
        help='Output file for results (JSON)'
    )
    parser.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    run_evaluation(
        output_file=args.output,
        verbose=not args.quiet
    )

# Made with Bob
