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
    
    def generate_response(
        self,
        query: str,
        context_chunks: List[Dict],
        max_tokens: int = 1500,
        temperature: float = 0.15,
        max_context_tokens: int = 1200
    ) -> Dict:
        """
        Generate response with automatic validation and repair.
        
        Multi-stage pipeline:
        1. Generate initial answer
        2. Validate completion integrity
        3. If incomplete → hidden continuation
        4. If still incomplete/poor → hidden regeneration
        5. Return final answer with metadata
        
        Args:
            query: User's question
            context_chunks: Retrieved chunks with content and metadata
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0, default 0.15 for stability)
            max_context_tokens: Maximum tokens for context
            
        Returns:
            Dictionary with answer, metadata, and repair strategy
        """
        # Enforce token budget
        context_chunks = self._enforce_token_budget(context_chunks, max_context_tokens)
        context_tokens = self._calculate_context_tokens(context_chunks)
        
        logger.info(
            f"[LLM] Starting generation: {len(context_chunks)} chunks, "
            f"~{context_tokens} context tokens, query='{query[:50]}...'"
        )
        
        # Stage 1: Initial generation
        initial_result = self._generate_initial_answer(
            query, context_chunks, max_tokens, temperature
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
        temperature: float
    ) -> Dict:
        """Generate initial answer with strict source grounding."""
        prompt = self._build_prompt(query, context_chunks)
        
        try:
            response = requests.post(
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
            response = requests.post(
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
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": max(0.1, temperature - 0.05),  # Even lower
                        "top_p": 0.85,
                        "repeat_penalty": 1.15
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
    
    def _build_prompt(self, query: str, context_chunks: List[Dict]) -> str:
        """
        Build initial answer prompt with strict source grounding.
        
        Args:
            query: User's question
            context_chunks: Retrieved chunks with metadata
            
        Returns:
            Formatted prompt string
        """
        # Format context from chunks
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            doc_title = chunk.get('document', {}).get('title', 'Unknown')
            page_num = chunk.get('page_number', 'N/A')
            content = chunk.get('content', '')
            
            context_parts.append(
                f"[Source {i}: {doc_title}, Page {page_num}]\n{content}"
            )
        
        context_text = "\n\n".join(context_parts)
        
        # Strict evidence-backed prompt
        prompt = f"""You are LinuxONE Assistant, an evidence-backed assistant for LinuxONE and IBM technologies.

Answer the user's question using ONLY the provided source context.
Do not invent or infer information that is not supported by the sources.
If the sources do not contain enough information to answer confidently, say so clearly.

Context:
{context_text}

User question:
{query}

Instructions:
- Give a concise but complete answer.
- Use short paragraphs or bullet points when helpful.
- Base every claim on the provided sources only.
- Do not repeat yourself.
- If the evidence is limited, state that clearly.
- End with a complete sentence.
- Do not include filler or meta commentary.

Answer:"""
        
        return prompt
    
    def _build_continuation_prompt(
        self, 
        query: str, 
        context_chunks: List[Dict], 
        partial_answer: str
    ) -> str:
        """
        Build continuation prompt for truncated answers.
        
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
        
        prompt = f"""The previous answer was cut off and is incomplete.

Use ONLY the source context below and continue the answer from exactly where it stopped.

Context:
{context_text}

User question:
{query}

Partial answer:
{partial_answer}

Instructions:
- Continue from the partial answer.
- Do not restart the answer.
- Do not repeat prior content.
- Do not add unsupported information.
- Finish the answer cleanly.
- End with a complete sentence.

Continuation:"""
        
        return prompt
    
    def _build_regenerate_prompt(self, query: str, context_chunks: List[Dict]) -> str:
        """
        Build stricter regeneration prompt (fallback only).
        
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
        
        prompt = f"""You are LinuxONE Assistant, an evidence-backed assistant for LinuxONE and IBM technologies.

Generate a stable, complete answer using ONLY the source context below.
Do not infer unsupported details.
If the evidence is incomplete, say so clearly.

Context:
{context_text}

User question:
{query}

Instructions:
- Provide a complete answer.
- Prefer bullet points when the question asks for features, benefits, steps, or categories.
- Keep the answer grounded in the sources.
- Do not repeat yourself.
- End with a complete sentence.

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
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
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
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
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
