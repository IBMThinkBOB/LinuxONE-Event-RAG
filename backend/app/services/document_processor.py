import fitz  # PyMuPDF
from typing import List, Dict, Optional
import re
from pathlib import Path


class DocumentProcessor:
    """Process PDF documents and extract text content."""
    
    def __init__(self):
        self.supported_formats = ['.pdf']
    
    def load_pdf(self, file_path: str) -> Dict:
        """
        Load and extract text from PDF.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing pages and metadata
        """
        doc = fitz.open(file_path)
        
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            pages.append({
                'page_number': page_num + 1,
                'content': text
            })
        
        metadata = {
            'filename': Path(file_path).name,
            'total_pages': len(doc),
            'title': self._extract_title(doc),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'creator': doc.metadata.get('creator', '')
        }
        
        doc.close()
        
        return {
            'pages': pages,
            'metadata': metadata
        }
    
    def _extract_title(self, doc) -> str:
        """
        Extract title from PDF metadata or first page.
        
        Args:
            doc: PyMuPDF document object
            
        Returns:
            Extracted title or default
        """
        # Try metadata first
        if doc.metadata.get('title'):
            return doc.metadata['title']
        
        # Try first page
        if len(doc) > 0:
            first_page_text = doc[0].get_text()
            lines = first_page_text.split('\n')
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if len(line) > 10 and len(line) < 200:
                    return line
        
        return "Untitled Document"
    
    def extract_sections(self, text: str) -> List[Dict]:
        """
        Extract sections from document text based on common patterns.
        
        Args:
            text: Document text
            
        Returns:
            List of sections with titles and content
        """
        # Common section patterns in technical documents
        section_patterns = [
            r'^(Chapter|CHAPTER)\s+\d+[:\.]?\s+(.+)$',
            r'^(Section|SECTION)\s+\d+[:\.]?\s+(.+)$',
            r'^(Part|PART)\s+\d+[:\.]?\s+(.+)$',
            r'^\d+\.\s+(.+)$',  # Numbered sections like "1. Introduction"
            r'^\d+\.\d+\s+(.+)$'  # Subsections like "1.1 Overview"
        ]
        
        sections = []
        current_section = None
        current_content = []
        
        for line in text.split('\n'):
            line_stripped = line.strip()
            
            # Check if line matches any section pattern
            is_section = False
            for pattern in section_patterns:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    # Save previous section
                    if current_section:
                        sections.append({
                            'title': current_section,
                            'content': '\n'.join(current_content)
                        })
                    
                    # Start new section
                    current_section = line_stripped
                    current_content = []
                    is_section = True
                    break
            
            if not is_section and line_stripped:
                current_content.append(line)
        
        # Add final section
        if current_section:
            sections.append({
                'title': current_section,
                'content': '\n'.join(current_content)
            })
        
        # If no sections found, return entire text as one section
        if not sections:
            sections = [{
                'title': 'Main Content',
                'content': text
            }]
        
        return sections
    
    def extract_topics(self, text: str, max_topics: int = 3) -> List[str]:
        """
        Extract main topics from text using simple keyword extraction.
        
        Args:
            text: Text to analyze
            max_topics: Maximum number of topics to extract
            
        Returns:
            List of topic keywords
        """
        # Common technical terms in LinuxONE/IBM context
        technical_keywords = {
            'linuxone', 'linux', 'ibm', 'z/os', 'mainframe', 'security',
            'ai', 'machine learning', 'artificial intelligence', 'workload',
            'performance', 'scalability', 'virtualization', 'container',
            'kubernetes', 'docker', 'cloud', 'hybrid', 'encryption',
            'resilience', 'availability', 'disaster recovery', 'backup',
            'database', 'postgresql', 'db2', 'analytics', 'data',
            'enterprise', 'infrastructure', 'architecture', 'deployment',
            # IBM MQ keywords
            'mq', 'ibm mq', 'queue manager', 'channel', 'message broker',
            'topic', 'subscription', 'clustering', 'high availability', 'tls',
        }
        
        # Convert text to lowercase for matching
        text_lower = text.lower()
        
        # Count keyword occurrences
        keyword_counts = {}
        for keyword in technical_keywords:
            count = text_lower.count(keyword)
            if count > 0:
                keyword_counts[keyword] = count
        
        # Sort by frequency and return top topics
        sorted_topics = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        topics = [topic for topic, _ in sorted_topics[:max_topics]]
        
        return topics if topics else ['general']
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing extra whitespace and special characters.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,;:!?()\-\']', '', text)
        
        # Remove multiple newlines
        text = re.sub(r'\n+', '\n', text)
        
        return text.strip()

# Made with Bob
