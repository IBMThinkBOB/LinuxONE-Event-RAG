"""
Metadata enricher for IBM MQ documentation chunks.
Classifies chunk content by type (procedure / troubleshooting / concept),
detects target platforms and interfaces, and returns a fully-populated
metadata dict matching the schema defined in IBM_MQ_RAG_Ingestion_Guide.md §5.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# ── Keyword tables ────────────────────────────────────────────────────────────

_PROCEDURE_KEYWORDS = {
    'install', 'configure', 'step', 'create', 'enable', 'run',
    'setup', 'set up', 'deploy', 'start', 'stop', 'restart',
    'define', 'add', 'enter', 'execute', 'type the command',
}

_TROUBLESHOOTING_KEYWORDS = {
    'error', 'fail', 'troubleshoot', 'cannot', 'reason', 'resolve',
    'fix', 'issue', 'problem', 'warning', 'exception', 'unable',
    'not working', 'diagnostic', 'diagnose',
}

_PLATFORM_MAP = {
    'Linux':   ['linux'],
    'Windows': ['windows'],
    'z/OS':    ['z/os', 'zos'],
    'AIX':     ['aix'],
}

_INTERFACE_MAP = {
    'CLI': ['cli', 'command line', 'terminal', 'runmqsc', 'mqsc',
            'command prompt', 'shell', 'strmqm', 'endmqm', 'crtmqm'],
    'GUI': ['gui', 'mq explorer', 'explorer', 'click', 'dialog',
            'toolbar', 'wizard', 'checkbox', 'dropdown', 'button'],
    'API': ['api', 'rest', 'http', 'amqp', 'jms', 'mqi', 'pcf',
            'programmatic', 'sdk'],
}


class MetadataEnricher:
    """Produce IBM MQ-specific chunk metadata from content and document context."""

    def classify_content_type(self, text: str) -> str:
        """
        Classify text as 'procedure', 'troubleshooting', or 'concept'.

        Troubleshooting is checked before procedure because error-resolution
        content often contains both install and error keywords.

        Args:
            text: Chunk or section text.

        Returns:
            One of 'procedure', 'troubleshooting', or 'concept'.
        """
        text_lower = text.lower()

        if any(kw in text_lower for kw in _TROUBLESHOOTING_KEYWORDS):
            return 'troubleshooting'
        if any(kw in text_lower for kw in _PROCEDURE_KEYWORDS):
            return 'procedure'
        return 'concept'

    def extract_platform(self, text: str) -> List[str]:
        """
        Return platform names mentioned in the text.

        Args:
            text: Chunk or section text.

        Returns:
            Subset of ['Linux', 'Windows', 'z/OS', 'AIX'].
        """
        text_lower = text.lower()
        return [
            platform
            for platform, signals in _PLATFORM_MAP.items()
            if any(s in text_lower for s in signals)
        ]

    def extract_interface(self, text: str) -> List[str]:
        """
        Return interface types mentioned in the text.

        Args:
            text: Chunk or section text.

        Returns:
            Subset of ['CLI', 'GUI', 'API'].
        """
        text_lower = text.lower()
        return [
            iface
            for iface, signals in _INTERFACE_MAP.items()
            if any(s in text_lower for s in signals)
        ]

    def enrich_chunk(self, content: str, doc_meta: Dict) -> Dict:
        """
        Build the full IBM MQ metadata dict for a chunk.

        Schema (IBM_MQ_RAG_Ingestion_Guide.md §5):
            {
                "title":     str,
                "type":      "procedure" | "troubleshooting" | "concept",
                "platform":  [str, ...],
                "interface": [str, ...],
                "source":    str,
                "keywords":  [str, ...],
                "content":   str,
                "embedding": []   # populated later by EmbeddingService
            }

        Args:
            content:  Chunk text.
            doc_meta: Document-level metadata dict (from HTMLLoader._build_result).

        Returns:
            Populated metadata dict.
        """
        content_type = self.classify_content_type(content)
        platforms = self.extract_platform(content)
        interfaces = self.extract_interface(content)

        # Derive a keyword list from doc-level topics + any extra from content
        doc_topics = doc_meta.get('topics', [])
        keywords = list(dict.fromkeys(doc_topics))  # deduplicate, preserve order

        return {
            'title':     doc_meta.get('title', ''),
            'type':      content_type,
            'platform':  platforms,
            'interface': interfaces,
            'source':    doc_meta.get('filename', ''),
            'keywords':  keywords,
            'content':   content,
            'embedding': [],
        }

# Made with Bob
