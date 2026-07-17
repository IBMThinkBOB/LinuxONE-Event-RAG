import requests
from typing import List, Dict, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)


class LLMService:
    """
    Production-grade LLM service with completion validation and repair.
    
    Implements multi-stage answer generation:
    1. Initial generation with strict source grounding
    2. Completion integrity validation
    3. Hidden continuation for truncated answers
    4. Conditional hidden regeneration as fallback
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen"):
        """
        Initialize the LLM service.
        
        Args:
            base_url: Base URL for Ollama API
            model: Model name to use (e.g., 'qwen')
        """
        self.base_url = base_url
        self.model = model
        # Use a session so every request carries the ngrok bypass header.
        # This header is a no-op against real Ollama but required when tunnelling
        # through ngrok's free tier, which otherwise returns 403 for non-browser clients.
        self._session = requests.Session()
        self._session.headers.update({"ngrok-skip-browser-warning": "true"})
    
    def generate_response(
        self,
        query: str,
        context_chunks: List[Dict],
        max_tokens: int = 2500,
        temperature: float = 0.2,
        max_context_tokens: int = 1200,
        answer_mode: str = "focused",
        use_evidence_extraction: bool = False
    ) -> Dict:
        """
        Generate response with automatic validation and repair.
        
        Multi-stage pipeline:
        1. (Optional) Extract structured evidence from chunks
        2. Generate initial answer
        3. Validate completion integrity
        4. If incomplete → hidden continuation
        5. If still incomplete/poor → hidden regeneration
        6. Return final answer with metadata
        
        Args:
            query: User's question
            context_chunks: Retrieved chunks with content and metadata
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            max_context_tokens: Maximum tokens for context
            answer_mode: 'comprehensive' for structured answers, 'focused' for specific answers
            use_evidence_extraction: Whether to extract structured evidence from chunks
            
        Returns:
            Dictionary with answer, metadata, and repair strategy
        """
        # Optional: Extract structured evidence
        evidence_list = None
        if use_evidence_extraction:
            try:
                from app.services.evidence_service import get_evidence_service
                evidence_service = get_evidence_service()
                evidence_list = evidence_service.extract_evidence_from_chunks(
                    context_chunks, query, use_llm=False
                )
                evidence_summary = evidence_service.get_evidence_summary(evidence_list)
                logger.info(
                    f"[Evidence] Extracted {evidence_summary['total_facts']} facts "
                    f"from {evidence_summary['sources_with_facts']}/{evidence_summary['total_sources']} sources"
                )
            except Exception as e:
                logger.warning(f"[Evidence] Extraction failed: {e}, falling back to raw chunks")
                evidence_list = None
        
        # Enforce token budget
        context_chunks = self._enforce_token_budget(context_chunks, max_context_tokens)
        context_tokens = self._calculate_context_tokens(context_chunks)
        
        logger.info(
            f"[LLM] Starting generation: {len(context_chunks)} chunks, "
            f"~{context_tokens} context tokens, query='{query[:50]}...', "
            f"evidence_extraction={'enabled' if evidence_list else 'disabled'}"
        )
        
        # Stage 1: Initial generation
        initial_result = self._generate_initial_answer(
            query, context_chunks, max_tokens, temperature, answer_mode, evidence_list
        )
        
        answer = initial_result['answer']
        done_reason = initial_result.get('done_reason')
        
        logger.info(
            f"[LLM] Initial answer: {len(answer)} chars, "
            f"done_reason={done_reason}, "
            f"tokens={initial_result.get('completion_tokens', 0)}"
        )
        
        # Stage 2: Validate completion
        is_incomplete, incomp_reason = self._looks_incomplete(answer, done_reason)
        
        repair_strategy = "none"
        
        if is_incomplete:
            logger.warning(f"[LLM] Answer incomplete: {incomp_reason}")
            
            # Stage 3: Try continuation
            continued_result = self.continue_response(
                query, context_chunks, answer, max_tokens, temperature
            )
            
            if continued_result['success']:
                answer = continued_result['answer']
                repair_strategy = "continued"
                logger.info(f"[LLM] Continuation successful: {len(answer)} chars")
                
                # Revalidate
                is_still_incomplete, _ = self._looks_incomplete(
                    answer, continued_result.get('done_reason')
                )
                
                if is_still_incomplete:
                    logger.warning("[LLM] Still incomplete after continuation")
                    
                    # Stage 4: Conditional regeneration
                    regen_result = self.regenerate_response(
                        query, context_chunks, max_tokens, temperature
                    )
                    
                    if regen_result['success']:
                        answer = regen_result['answer']
                        repair_strategy = "regenerated"
                        logger.info(f"[LLM] Regeneration successful: {len(answer)} chars")
            else:
                logger.error("[LLM] Continuation failed, trying regeneration")
                
                # Stage 4: Fallback to regeneration
                regen_result = self.regenerate_response(
                    query, context_chunks, max_tokens, temperature
                )
                
                if regen_result['success']:
                    answer = regen_result['answer']
                    repair_strategy = "regenerated"
                    logger.info(f"[LLM] Regeneration successful: {len(answer)} chars")
        
        # Final validation
        final_incomplete, final_reason = self._looks_incomplete(answer, done_reason)
        
        if final_incomplete and repair_strategy != "none":
            logger.error(
                f"[LLM] Answer still incomplete after repair: {final_reason}"
            )
        
        return {
            'answer': answer,
            'model': self.model,
            'status': 'complete' if not final_incomplete else 'incomplete',
            'repair_strategy': repair_strategy,
            'done': initial_result.get('done', True),
            'done_reason': done_reason,
            'prompt_tokens': initial_result.get('prompt_tokens', 0),
            'completion_tokens': initial_result.get('completion_tokens', 0),
            'total_tokens': initial_result.get('total_tokens', 0),
            'context_chunk_count': len(context_chunks),
            'context_estimated_tokens': context_tokens,
        }
    
    def _generate_initial_answer(
        self,
        query: str,
        context_chunks: List[Dict],
        max_tokens: int,
        temperature: float,
        answer_mode: str = "focused",
        evidence_list: Optional[List[Dict]] = None
    ) -> Dict:
        """Generate initial answer with structured evidence or raw chunks."""
        prompt = self._build_prompt(query, context_chunks, answer_mode, evidence_list)
        
        try:
            response = self._session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,  # Use parameter, not hardcoded
                        "top_p": 0.9,
                        "repeat_penalty": 1.15
                    }
                },
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                raise Exception(f"LLM API error: {response.text}")
            
            result = response.json()
            
            return {
                'answer': result['response'],
                'done': result.get('done', True),
                'done_reason': result.get('done_reason'),
                'prompt_tokens': result.get('prompt_eval_count', 0),
                'completion_tokens': result.get('eval_count', 0),
                'total_tokens': result.get('prompt_eval_count', 0) + result.get('eval_count', 0)
            }
        except requests.exceptions.Timeout:
            logger.error("LLM request timed out")
            raise Exception("LLM request timed out. Please try again.")
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            raise
    
    def continue_response(
        self,
        query: str,
        context_chunks: List[Dict],
        partial_answer: str,
        max_tokens: int,
        temperature: float
    ) -> Dict:
        """
        Continue a truncated answer using the same context.
        
        Args:
            query: Original question
            context_chunks: Same retrieved context
            partial_answer: Incomplete answer to continue
            max_tokens: Maximum tokens for continuation
            temperature: Sampling temperature
            
        Returns:
            Dictionary with success status and combined answer
        """
        logger.info("[LLM] Attempting continuation")
        
        prompt = self._build_continuation_prompt(query, context_chunks, partial_answer)
        
        try:
            response = self._session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                        "top_p": 0.9,
                        "repeat_penalty": 1.2  # Higher to avoid repeating partial answer
                    }
                },
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"Continuation API error: {response.status_code}")
                return {'success': False, 'answer': partial_answer}
            
            result = response.json()
            continuation = result['response'].strip()
            
            # Merge partial + continuation
            combined_answer = self._merge_continuation(partial_answer, continuation)
            
            return {
                'success': True,
                'answer': combined_answer,
                'done_reason': result.get('done_reason')
            }
        except Exception as e:
            logger.error(f"Continuation failed: {e}")
            return {'success': False, 'answer': partial_answer}
    
    def regenerate_response(
        self,
        query: str,
        context_chunks: List[Dict],
        max_tokens: int,
        temperature: float
    ) -> Dict:
        """
        Regenerate answer with stricter controls (conditional fallback).
        
        Args:
            query: Original question
            context_chunks: Retrieved context
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            
        Returns:
            Dictionary with success status and regenerated answer
        """
        logger.info("[LLM] Attempting full regeneration")
        
        prompt = self._build_regenerate_prompt(query, context_chunks)
        
        try:
            response = self._session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": max(0.1, temperature - 0.05),  # Even lower
                        "top_p": 0.85,
                        "repeat_penalty": 1.2
                    }
                },
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"Regeneration API error: {response.status_code}")
                return {'success': False}
            
            result = response.json()
            
            return {
                'success': True,
                'answer': result['response'],
                'done_reason': result.get('done_reason')
            }
        except Exception as e:
            logger.error(f"Regeneration failed: {e}")
            return {'success': False}
    
    def _looks_incomplete(self, text: str, done_reason: Optional[str]) -> Tuple[bool, str]:
        """
        Validate answer completion integrity.
        
        Checks:
        - Provider finish reason (length cap)
        - Text ending quality
        - Dangling connectors
        - Structural completeness
        
        Args:
            text: Generated answer text
            done_reason: Provider's completion reason
            
        Returns:
            Tuple of (is_incomplete: bool, reason: str)
        """
        if not text or len(text.strip()) < 3:
            return True, "answer too short"
        
        text = text.strip()
        
        # Check 1: Provider signals length stop
        if done_reason == 'length':
            return True, "done_reason=length (token cap)"
        
        # Check 2: Dangling connector words (check before punctuation)
        dangling_connectors = [
            'and', 'or', 'with', 'within', 'of', 'to', 'for',
            'including', 'that', 'which', 'such as', 'as well as',
            'in addition', 'furthermore', 'moreover', 'however'
        ]
        
        last_words = text.lower().split()[-2:] if len(text.split()) >= 2 else text.lower().split()
        last_word = last_words[-1] if last_words else ''
        
        for connector in dangling_connectors:
            # Check if connector is the last word (exact match)
            if last_word == connector:
                return True, f"dangling connector: '{connector}'"
        
        # Check 3: Incomplete list structure
        if re.search(r'\d+\.\s*$', text):  # Ends with "1. " or similar
            return True, "incomplete numbered list"
        
        if re.search(r'[-*]\s*$', text):  # Ends with "- " or "* "
            return True, "incomplete bulleted list"
        
        # Check 4: Open markdown/formatting
        if text.count('```') % 2 != 0:
            return True, "unclosed code block"
        
        if text.count('**') % 2 != 0:
            return True, "unclosed bold formatting"
        
        # Check 5: Ends mid-sentence (no terminal punctuation)
        # Only flag if answer is long enough and doesn't end with punctuation
        if not re.search(r'[.!?]$', text):
            # Allow short answers without punctuation (e.g., "Yes", "No", "LinuxONE")
            if len(text) > 100:
                return True, "no terminal punctuation"
        
        # Answer appears complete
        return False, "complete"
    
    def _merge_continuation(self, partial: str, continuation: str) -> str:
        """
        Safely merge partial answer with continuation.
        
        Args:
            partial: Incomplete answer
            continuation: Continuation text
            
        Returns:
            Combined answer
        """
        partial = partial.strip()
        continuation = continuation.strip()
        
        # Remove duplicate content if continuation repeats the end of partial
        partial_end = partial[-100:] if len(partial) > 100 else partial
        
        if continuation.startswith(partial_end):
            continuation = continuation[len(partial_end):].strip()
        
        # Merge with appropriate spacing
        if partial and continuation:
            # Only merge without space if partial ends mid-word
            # (last char is alphanumeric AND continuation completes that word)
            if partial[-1].isalnum() and continuation[0].isalnum():
                # Get last partial word
                partial_words = partial.split()
                if partial_words:
                    last_word = partial_words[-1]
                    # Check if this looks like mid-word truncation:
                    # 1. Last word doesn't end with common word endings
                    # 2. Continuation starts with lowercase (likely completing the word)
                    common_endings = ['s', 'ed', 'ing', 'ly', 'er', 'est', 'ion', 'tion', 'ment', 'ness', 'ity', 'ty']
                    ends_with_common = any(last_word.endswith(ending) for ending in common_endings)
                    
                    if not ends_with_common and continuation[0].islower():
                        # Likely mid-word, merge without space
                        return partial + continuation
            
            # Default: add space between (most common case)
            return f"{partial.rstrip()} {continuation.lstrip()}"
        
        return partial + continuation
    
    def _build_prompt(
        self,
        query: str,
        context_chunks: List[Dict],
        answer_mode: str = "focused",
        evidence_list: Optional[List[Dict]] = None
    ) -> str:
        """
        Build initial answer prompt with Hybrid RAG approach.
        Uses structured evidence if available, otherwise raw chunks.
        
        Philosophy: Context-first hybrid where retrieved context enhances answers
        but doesn't strictly constrain them. LLM can use general knowledge when
        context is limited.
        
        Args:
            query: User's question
            context_chunks: Retrieved chunks with metadata
            answer_mode: "comprehensive" for structured answers, "focused" for direct answers
            evidence_list: Optional structured evidence extracted from chunks
            
        Returns:
            Formatted prompt string
        """
        # Use structured evidence if available, otherwise format raw chunks
        if evidence_list:
            from app.services.evidence_service import get_evidence_service
            evidence_service = get_evidence_service()
            context_text = evidence_service.format_evidence_for_prompt(evidence_list)
        else:
            # Format context from raw chunks
            context_parts = []
            for i, chunk in enumerate(context_chunks, 1):
                doc_title = chunk.get('document', {}).get('title', 'Unknown')
                page_num = chunk.get('page_number', 'N/A')
                content = chunk.get('content', '')
                
                context_parts.append(
                    f"[Source {i}: {doc_title}, Page {page_num}]\n{content}"
                )
            
            context_text = "\n\n".join(context_parts)
        
        if answer_mode == "comprehensive":
            # Hybrid RAG: Comprehensive mode with structured guidance
            prompt = f"""You are an expert assistant for IBM LinuxONE with deep knowledge of enterprise computing.

Answer the user's question about IBM's LinuxONE Mainframe in depth. If the query seems vague, assume it refers specifically to IBM's LinuxONE Mainframe platform.

Use the provided context to enhance your answer, but do not rely on it exclusively.

Context from LinuxONE RedBooks:
{context_text}

Question:
{query}

Instructions:
- Write a thorough, multi-paragraph response — do not stop after one or two sentences
- Organize with clear sections: Overview, Key Features, Technical Details, Use Cases, Benefits
- Each section should contain multiple sentences with concrete details
- Use context when relevant and cite sources naturally
- Supplement with general LinuxONE knowledge where context is limited
- Focus on LinuxONE-specific information
- Avoid repetition; combine similar points into one

Answer:"""
        else:
            # Hybrid RAG: Focused mode for direct answers
            prompt = f"""You are an expert assistant for IBM LinuxONE with deep knowledge of enterprise computing.

Answer the user's question clearly and in depth — do not give a one-sentence summary.

Use the provided context to enhance your answer, but do not rely on it exclusively.

Context from LinuxONE RedBooks:
{context_text}

Question:
{query}

Instructions:
- Write at least 3–5 sentences with specific, concrete details
- Use context when relevant
- Supplement with general LinuxONE knowledge if context is limited
- Avoid repetition
- Prefer depth and clarity over brevity

Answer:"""
        
        return prompt
    
    def _build_continuation_prompt(
        self,
        query: str,
        context_chunks: List[Dict],
        partial_answer: str
    ) -> str:
        """
        Build continuation prompt with hybrid approach.
        More grounded than initial prompt but still allows general knowledge.
        
        Args:
            query: Original question
            context_chunks: Same retrieved context
            partial_answer: Incomplete answer
            
        Returns:
            Continuation prompt
        """
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            doc_title = chunk.get('document', {}).get('title', 'Unknown')
            page_num = chunk.get('page_number', 'N/A')
            content = chunk.get('content', '')
            
            context_parts.append(
                f"[Source {i}: {doc_title}, Page {page_num}]\n{content}"
            )
        
        context_text = "\n\n".join(context_parts)
        
        prompt = f"""Your previous response was cut off. Continue from where you left off.

Context from LinuxONE RedBooks:
{context_text}

Question:
{query}

Partial answer:
{partial_answer}

Instructions:
- Continue from exactly where you stopped
- Use the context to enhance your continuation
- Do NOT restart or repeat prior content
- Complete your explanation fully
- End with a complete sentence

Continuation:"""
        
        return prompt
    
    def _build_regenerate_prompt(self, query: str, context_chunks: List[Dict]) -> str:
        """
        Build regeneration prompt with hybrid approach (fallback only).
        Slightly more conservative than initial prompt to ensure stability.
        
        Args:
            query: User's question
            context_chunks: Retrieved chunks
            
        Returns:
            Regeneration prompt
        """
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            doc_title = chunk.get('document', {}).get('title', 'Unknown')
            page_num = chunk.get('page_number', 'N/A')
            content = chunk.get('content', '')
            
            context_parts.append(
                f"[Source {i}: {doc_title}, Page {page_num}]\n{content}"
            )
        
        context_text = "\n\n".join(context_parts)
        
        prompt = f"""You are an expert assistant for IBM LinuxONE with deep knowledge of enterprise computing.

Answer the user's question clearly and in detail.

Use the provided context to enhance your answer, but do not rely on it exclusively.

Context from LinuxONE RedBooks:
{context_text}

Question:
{query}

Instructions:
- Provide a complete and detailed answer
- Use context when relevant and cite sources naturally
- If context is limited, supplement with general LinuxONE knowledge
- Focus on LinuxONE-specific information
- Avoid repetition
- End with a complete sentence

Answer:"""
        
        return prompt
    
    def _calculate_context_tokens(self, context_chunks: List[Dict]) -> int:
        """
        Estimate token count for context chunks.
        
        Args:
            context_chunks: List of chunks with content
            
        Returns:
            Estimated token count
        """
        total_chars = sum(len(chunk.get('content', '')) for chunk in context_chunks)
        # Rough estimate: 4 chars per token
        return total_chars // 4
    
    def _enforce_token_budget(
        self, 
        context_chunks: List[Dict], 
        max_context_tokens: int = 1200
    ) -> List[Dict]:
        """
        Limit chunks to stay within token budget.
        
        Args:
            context_chunks: List of chunks (should be pre-ranked by relevance)
            max_context_tokens: Maximum tokens for context
            
        Returns:
            Filtered list of chunks within budget
        """
        selected_chunks = []
        current_tokens = 0
        
        for chunk in context_chunks:
            chunk_tokens = len(chunk.get('content', '')) // 4
            
            if current_tokens + chunk_tokens <= max_context_tokens:
                selected_chunks.append(chunk)
                current_tokens += chunk_tokens
            else:
                logger.info(
                    f"Token budget reached: {current_tokens}/{max_context_tokens} tokens, "
                    f"using {len(selected_chunks)}/{len(context_chunks)} chunks"
                )
                break
        
        return selected_chunks
    
    def check_availability(self) -> bool:
        """
        Check if the LLM service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        try:
            response = self._session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"LLM service not available: {e}")
            return False
    
    def get_model_info(self) -> Optional[Dict]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information or None if unavailable
        """
        try:
            response = self._session.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                for model in models:
                    if model.get('name', '').startswith(self.model):
                        return {
                            'name': model.get('name'),
                            'size': model.get('size'),
                            'modified': model.get('modified_at')
                        }
            return None
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return None


# Global LLM service instance
_llm_service = None


def get_llm_service(base_url: str = "http://localhost:11434", model: str = "qwen") -> LLMService:
    """
    Get or create the global LLM service instance.
    
    Args:
        base_url: Base URL for Ollama API
        model: Model name to use
        
    Returns:
        LLMService instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(base_url, model)
    return _llm_service

# Made with Bob
