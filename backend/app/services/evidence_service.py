"""
Evidence Extraction Service

Transforms raw retrieved chunks into clean, structured evidence summaries.
This addresses the "chunk noisiness/fragmentation" and "multi-chunk synthesis failure" issues.

Architecture:
Raw chunks → Clean text → Extract key facts → Structured evidence → LLM
"""

import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class EvidenceService:
    """
    Service for extracting and structuring evidence from raw chunks.
    
    Solves:
    - Chunk noisiness (removes headers, footers, figure captions)
    - Fragmentation (normalizes formatting, merges broken lines)
    - Multi-chunk synthesis (creates structured evidence format)
    """
    
    def __init__(self, llm_service=None):
        """
        Initialize evidence service.
        
        Args:
            llm_service: Optional LLM service for evidence extraction (if None, uses rule-based)
        """
        self.llm_service = llm_service
    
    def extract_evidence_from_chunks(
        self,
        chunks: List[Dict],
        query: str,
        use_llm: bool = False
    ) -> List[Dict]:
        """
        Extract structured evidence from raw chunks.
        
        Args:
            chunks: Raw retrieved chunks with content and metadata
            query: User query (for relevance filtering)
            use_llm: Whether to use LLM for extraction (vs rule-based)
            
        Returns:
            List of evidence dictionaries with structured facts
        """
        evidence_list = []
        
        for i, chunk in enumerate(chunks, 1):
            # Clean the chunk text
            cleaned_text = self._clean_chunk_text(chunk.get('content', ''))
            
            # Extract key facts
            if use_llm and self.llm_service:
                facts = self._extract_facts_with_llm(cleaned_text, query)
            else:
                facts = self._extract_facts_rule_based(cleaned_text)
            
            # Build evidence structure
            evidence = {
                'source_id': i,
                'document': chunk.get('document', {}).get('title', 'Unknown'),
                'page': chunk.get('page_number', 'N/A'),
                'section': chunk.get('section', 'N/A'),
                'topic': chunk.get('topic', 'General'),
                'facts': facts,
                'original_content': chunk.get('content', ''),  # Keep for fallback
                'similarity': chunk.get('similarity', 0.0)
            }
            
            evidence_list.append(evidence)
            
            logger.info(
                f"Extracted {len(facts)} facts from Source {i} "
                f"({evidence['document']}, Page {evidence['page']})"
            )
        
        return evidence_list
    
    def _clean_chunk_text(self, text: str) -> str:
        """
        Clean raw chunk text by removing noise and normalizing formatting.
        
        Removes:
        - Repeated headers/footers
        - Figure captions (e.g., "Figure 3.2: ...")
        - Page numbers
        - Excessive whitespace
        
        Normalizes:
        - Broken lines
        - Bullet points
        - List formatting
        
        Args:
            text: Raw chunk text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove figure captions
        text = re.sub(r'Figure\s+\d+\.?\d*\s*:.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Table\s+\d+\.?\d*\s*:.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
        
        # Remove page numbers (standalone numbers on lines)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove common headers/footers
        text = re.sub(r'^\s*(Chapter|Section)\s+\d+.*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^\s*©.*IBM.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*LinuxONE\s+RedBook.*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        
        # Merge broken lines (lines ending mid-word)
        # If a line ends with a lowercase letter and next starts with lowercase, merge
        lines = text.split('\n')
        merged_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # Check if line ends mid-word and next line continues
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if (line and line[-1].isalnum() and 
                    next_line and next_line[0].islower() and
                    not line.endswith('.')):
                    # Merge lines
                    line = line + ' ' + next_line
                    i += 2
                else:
                    merged_lines.append(line)
                    i += 1
            else:
                merged_lines.append(line)
                i += 1
        
        text = '\n'.join(merged_lines)
        
        # Normalize bullet points
        text = re.sub(r'^\s*[•●○▪▫■□]\s+', '- ', text, flags=re.MULTILINE)
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def _extract_facts_rule_based(self, text: str) -> List[str]:
        """
        Extract key facts using rule-based approach.
        
        Strategy:
        - Split into sentences
        - Filter for informative sentences (not questions, not too short)
        - Prioritize sentences with technical terms
        - Limit to top facts
        
        Args:
            text: Cleaned chunk text
            
        Returns:
            List of key fact strings
        """
        if not text:
            return []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        facts = []
        for sentence in sentences:
            # Skip if too short
            if len(sentence) < 20:
                continue
            
            # Skip questions
            if sentence.endswith('?'):
                continue
            
            # Skip if starts with common noise patterns
            if re.match(r'^(This|These|It|They|The following)\s', sentence, re.IGNORECASE):
                # These are often meta-sentences, but keep if they have technical content
                if not self._has_technical_content(sentence):
                    continue
            
            # Add to facts
            facts.append(sentence)
            
            # Limit to reasonable number
            if len(facts) >= 5:
                break
        
        return facts
    
    def _has_technical_content(self, text: str) -> bool:
        """
        Check if text contains technical content.
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears technical
        """
        # Technical indicators
        technical_patterns = [
            r'\b(processor|CPU|memory|RAM|storage|disk|network|I/O)\b',
            r'\b(LPAR|PR/SM|VSWITCH|z/VM|KVM|Linux)\b',
            r'\b(encryption|security|firewall|authentication)\b',
            r'\b(performance|throughput|latency|bandwidth)\b',
            r'\b(availability|redundancy|failover|backup)\b',
            r'\b(GB|TB|MHz|GHz|Mbps|Gbps)\b',
            r'\b(configure|install|deploy|manage|monitor)\b',
        ]
        
        for pattern in technical_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_facts_with_llm(self, text: str, query: str) -> List[str]:
        """
        Extract key facts using LLM.
        
        Args:
            text: Cleaned chunk text
            query: User query for relevance
            
        Returns:
            List of key fact strings
        """
        # TODO: Implement LLM-based extraction
        # For now, fall back to rule-based
        logger.warning("LLM-based extraction not yet implemented, using rule-based")
        return self._extract_facts_rule_based(text)
    
    def format_evidence_for_prompt(
        self,
        evidence_list: List[Dict],
        include_original: bool = False
    ) -> str:
        """
        Format extracted evidence into a structured prompt format.
        
        Args:
            evidence_list: List of evidence dictionaries
            include_original: Whether to include original content as fallback
            
        Returns:
            Formatted evidence string for prompt
        """
        formatted_parts = []
        
        for evidence in evidence_list:
            source_id = evidence['source_id']
            document = evidence['document']
            page = evidence['page']
            section = evidence.get('section', 'N/A')
            topic = evidence.get('topic', 'General')
            facts = evidence['facts']
            
            # Build source header
            header = f"Source {source_id} ({document}, Page {page}"
            if section and section != 'N/A':
                header += f", Section: {section}"
            if topic and topic != 'General':
                header += f", Topic: {topic}"
            header += "):"
            
            # Add facts
            if facts:
                fact_lines = [f"  - {fact}" for fact in facts]
                source_text = header + "\n" + "\n".join(fact_lines)
            else:
                # No facts extracted, use original content
                source_text = header + "\n  " + evidence.get('original_content', '')[:500]
            
            formatted_parts.append(source_text)
        
        return "\n\n".join(formatted_parts)
    
    def get_evidence_summary(self, evidence_list: List[Dict]) -> Dict:
        """
        Get summary statistics about extracted evidence.
        
        Args:
            evidence_list: List of evidence dictionaries
            
        Returns:
            Summary dictionary
        """
        total_facts = sum(len(e['facts']) for e in evidence_list)
        sources_with_facts = sum(1 for e in evidence_list if e['facts'])
        
        topics = set()
        for e in evidence_list:
            if e.get('topic') and e['topic'] != 'General':
                topics.add(e['topic'])
        
        return {
            'total_sources': len(evidence_list),
            'sources_with_facts': sources_with_facts,
            'total_facts': total_facts,
            'avg_facts_per_source': total_facts / len(evidence_list) if evidence_list else 0,
            'topics_covered': list(topics),
            'num_topics': len(topics)
        }


# Global evidence service instance
_evidence_service = None


def get_evidence_service(llm_service=None) -> EvidenceService:
    """
    Get or create the global evidence service instance.
    
    Args:
        llm_service: Optional LLM service for extraction
        
    Returns:
        EvidenceService instance
    """
    global _evidence_service
    if _evidence_service is None:
        _evidence_service = EvidenceService(llm_service)
    return _evidence_service

# Made with Bob
