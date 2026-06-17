from typing import List, Dict


class TextChunker:
    """Split text into chunks with overlap for better context preservation."""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Initialize the text chunker.
        
        Args:
            chunk_size: Maximum number of tokens per chunk
            overlap: Number of tokens to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        # Lazy import tiktoken - optional dependency
        try:
            import tiktoken
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            # Graceful fallback to word-based chunking
            self.encoding = None
        except Exception:
            # Fallback if tiktoken fails for other reasons
            self.encoding = None
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries with content and metadata
        """
        if not text or not text.strip():
            return []
        
        if self.encoding:
            return self._chunk_with_tiktoken(text, metadata)
        else:
            return self._chunk_by_words(text, metadata)
    
    def _chunk_with_tiktoken(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Chunk text using tiktoken tokenizer."""
        # Tokenize the text
        tokens = self.encoding.encode(text)
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(tokens):
            # Get chunk tokens
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            
            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Create chunk object
            chunk = {
                'chunk_index': chunk_index,
                'content': chunk_text.strip(),
                'token_count': len(chunk_tokens),
                'start_token': start,
                'end_token': min(end, len(tokens))
            }
            
            # Add metadata if provided
            if metadata:
                chunk.update(metadata)
            
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start = end - self.overlap
            chunk_index += 1
        
        return chunks
    
    def _chunk_by_words(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Fallback chunking by words (approximate tokens)."""
        words = text.split()
        # Approximate: 1 token ≈ 0.75 words
        words_per_chunk = int(self.chunk_size * 0.75)
        overlap_words = int(self.overlap * 0.75)
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(words):
            end = start + words_per_chunk
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            
            chunk = {
                'chunk_index': chunk_index,
                'content': chunk_text.strip(),
                'token_count': len(chunk_words),  # Approximate
                'start_token': start,
                'end_token': min(end, len(words))
            }
            
            if metadata:
                chunk.update(metadata)
            
            chunks.append(chunk)
            
            start = end - overlap_words
            chunk_index += 1
        
        return chunks
    
    def chunk_by_sentences(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Split text by sentences while respecting token limits.
        Better for maintaining semantic coherence.
        """
        import re
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            if self.encoding:
                sentence_tokens = len(self.encoding.encode(sentence))
            else:
                sentence_tokens = len(sentence.split())
            
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunk = {
                    'chunk_index': chunk_index,
                    'content': chunk_text.strip(),
                    'token_count': current_tokens
                }
                if metadata:
                    chunk.update(metadata)
                chunks.append(chunk)
                
                # Start new chunk with overlap (last 2 sentences)
                overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                current_chunk = overlap_sentences + [sentence]
                if self.encoding:
                    current_tokens = sum(len(self.encoding.encode(s)) for s in current_chunk)
                else:
                    current_tokens = sum(len(s.split()) for s in current_chunk)
                chunk_index += 1
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk = {
                'chunk_index': chunk_index,
                'content': chunk_text.strip(),
                'token_count': current_tokens
            }
            if metadata:
                chunk.update(metadata)
            chunks.append(chunk)
        
        return chunks

# Made with Bob
