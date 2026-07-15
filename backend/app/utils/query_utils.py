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
        "what are",
        "what does",
        "how does",
        "how do",
        "define",
        "explain",
        "tell me about",
        "describe",
        "overview of",
        "introduction to",
        "list",
    ]
    
    for pattern in vague_patterns:
        if q.startswith(pattern):
            return True
    
    return False


# IBM MQ-specific signals used for query expansion
_MQ_SIGNALS = {'mq', 'queue', 'channel', 'broker', 'message', 'ibm mq',
               'queue manager', 'runmqsc', 'mqsc', 'mq explorer'}

_MQ_EXPANSION = (
    " ibm mq queue manager channel configuration messaging"
    " listener cluster tls security runmqsc"
)


def _is_mq_query(query: str) -> bool:
    """Return True when the query contains at least one IBM MQ signal term."""
    q = query.lower()
    return any(signal in q for signal in _MQ_SIGNALS)


def expand_query(query: str) -> str:
    """
    Expand vague or MQ-specific queries to improve retrieval coverage.

    - Vague queries receive general context keywords.
    - IBM MQ queries receive MQ-specific domain expansion.
    Both expansions can apply simultaneously.

    Args:
        query: Original user query

    Returns:
        Expanded query for better retrieval
    """
    result = query

    if is_vague_query(query):
        result += " overview features architecture components benefits use cases capabilities implementation"

    if _is_mq_query(query):
        result += _MQ_EXPANSION

    return result


def get_answer_mode(query: str) -> str:
    """
    Determine the appropriate answer mode based on query type.
    
    Args:
        query: User query string
        
    Returns:
        'comprehensive' for vague queries, 'focused' for specific queries
    """
    return "comprehensive" if is_vague_query(query) else "focused"


def classify_mq_query(query: str) -> str:
    """
    Classify an IBM MQ query as 'procedure', 'troubleshooting', or 'concept'.
    Mirrors the classify_query logic from IBM_MQ_RAG_Ingestion_Guide.md §6.

    Args:
        query: User query string

    Returns:
        'procedure', 'troubleshooting', or 'concept'
    """
    q = query.lower()

    troubleshooting_signals = {
        'error', 'fail', 'cannot', 'not working', 'issue', 'problem',
        'exception', 'unable', 'warning', 'fix', 'resolve', 'troubleshoot',
    }
    procedure_signals = {
        'install', 'configure', 'create', 'setup', 'set up', 'how to',
        'how do i', 'step', 'enable', 'start', 'stop', 'deploy',
    }

    if any(s in q for s in troubleshooting_signals):
        return 'troubleshooting'
    if any(s in q for s in procedure_signals):
        return 'procedure'
    return 'concept'


# Made with Bob