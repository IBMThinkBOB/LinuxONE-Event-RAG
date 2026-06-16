"""
Query processing utilities for improving retrieval and answer quality.
"""

def is_vague_query(query: str) -> bool:
    """
    Detect if a query is vague and needs expansion.
    
    Args:
        query: User query string
        
    Returns:
        True if query is vague, False otherwise
    """
    q = query.lower().strip()
    
    # Check for short queries
    if len(q.split()) <= 4:
        return True
    
    # Check for common vague patterns
    vague_patterns = [
        "what is",
        "define",
        "explain",
        "tell me about",
        "describe",
        "overview of",
        "introduction to"
    ]
    
    for pattern in vague_patterns:
        if q.startswith(pattern):
            return True
    
    return False


def expand_query(query: str) -> str:
    """
    Expand vague queries to improve retrieval coverage.
    
    Args:
        query: Original user query
        
    Returns:
        Expanded query for better retrieval
    """
    if is_vague_query(query):
        # Add context keywords to improve retrieval
        expansion = " overview features architecture components benefits use cases capabilities implementation"
        return query + expansion
    
    return query


def get_answer_mode(query: str) -> str:
    """
    Determine the appropriate answer mode based on query type.
    
    Args:
        query: User query string
        
    Returns:
        'comprehensive' for vague queries, 'focused' for specific queries
    """
    return "comprehensive" if is_vague_query(query) else "focused"


# Made with Bob