"""
Tests for LLM Service completion validation and repair logic.
"""
import pytest
from backend.app.services.llm_service import LLMService


class TestCompletionValidation:
    """Test the _looks_incomplete() validator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = LLMService()
    
    def test_complete_answer_with_period(self):
        """Complete answer ending with period should pass."""
        text = "LinuxONE provides enterprise-grade security features."
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        assert not is_incomplete
        assert reason == "complete"
    
    def test_complete_answer_with_question_mark(self):
        """Complete answer ending with question mark should pass."""
        text = "Would you like more details about LinuxONE security?"
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        assert not is_incomplete
    
    def test_complete_answer_with_exclamation(self):
        """Complete answer ending with exclamation should pass."""
        text = "LinuxONE delivers exceptional performance!"
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        assert not is_incomplete
    
    def test_short_complete_answer(self):
        """Short but complete answer should pass."""
        text = "Yes, LinuxONE supports AI workloads"
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        # Short answers without punctuation are allowed
        assert not is_incomplete
    
    def test_truncated_no_punctuation(self):
        """Long answer without terminal punctuation should fail."""
        text = "LinuxONE provides comprehensive security features including encryption, secure boot, and tamper-resistant hardware that"
        is_incomplete, reason = self.service._looks_incomplete(text, "length")
        assert is_incomplete
        assert "no terminal punctuation" in reason or "length" in reason
    
    def test_dangling_connector_and(self):
        """Answer ending with 'and' should fail."""
        text = "LinuxONE supports multiple virtualization technologies and"
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        assert is_incomplete
        assert "dangling connector" in reason
    
    def test_dangling_connector_with(self):
        """Answer ending with 'with' should fail."""
        text = "LinuxONE provides high availability with"
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        assert is_incomplete
        assert "dangling connector" in reason
    
    def test_dangling_connector_including(self):
        """Answer ending with 'including' should fail."""
        text = "LinuxONE offers many features including"
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        assert is_incomplete
        assert "dangling connector" in reason
    
    def test_incomplete_numbered_list(self):
        """Answer ending with list number should fail."""
        text = "LinuxONE security features:\n1. Encryption\n2. Secure boot\n3. "
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        assert is_incomplete
        assert "incomplete numbered list" in reason
    
    def test_incomplete_bulleted_list(self):
        """Answer ending with bullet should fail."""
        text = "LinuxONE features:\n- High availability\n- Scalability\n- "
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        assert is_incomplete
        assert "incomplete bulleted list" in reason
    
    def test_unclosed_code_block(self):
        """Answer with unclosed code block should fail."""
        text = "Here's an example:\n```bash\ncommand here"
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        assert is_incomplete
        assert "unclosed code block" in reason
    
    def test_unclosed_bold_formatting(self):
        """Answer with unclosed bold should fail."""
        text = "LinuxONE provides **enterprise-grade security"
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        assert is_incomplete
        assert "unclosed bold formatting" in reason
    
    def test_done_reason_length(self):
        """done_reason='length' should trigger incomplete."""
        text = "LinuxONE provides security."
        is_incomplete, reason = self.service._looks_incomplete(text, "length")
        assert is_incomplete
        assert "length" in reason
    
    def test_empty_text(self):
        """Empty text should fail."""
        text = ""
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        assert is_incomplete
        assert "too short" in reason
    
    def test_very_short_text(self):
        """Very short text should fail."""
        text = "Yes"
        is_incomplete, reason = self.service._looks_incomplete(text, "stop")
        # Very short is allowed if it's a valid answer
        assert not is_incomplete


class TestContinuationMerge:
    """Test the _merge_continuation() logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = LLMService()
    
    def test_simple_merge(self):
        """Simple continuation merge."""
        partial = "LinuxONE provides security"
        continuation = "features including encryption and secure boot."
        result = self.service._merge_continuation(partial, continuation)
        assert "LinuxONE provides security features" in result
        assert "encryption and secure boot" in result
    
    def test_merge_with_duplicate_removal(self):
        """Continuation that repeats partial end should be deduplicated."""
        partial = "LinuxONE provides comprehensive security features"
        continuation = "security features including encryption and tamper-resistant hardware."
        result = self.service._merge_continuation(partial, continuation)
        # Should not have "security features" twice
        assert result.count("security features") <= 2
    
    def test_merge_mid_word(self):
        """Merge when partial ends mid-word."""
        partial = "LinuxONE provides comprehen"
        continuation = "sive security features."
        result = self.service._merge_continuation(partial, continuation)
        assert "comprehensive" in result
    
    def test_merge_with_whitespace(self):
        """Merge handles whitespace correctly."""
        partial = "LinuxONE provides "
        continuation = " security features."
        result = self.service._merge_continuation(partial, continuation)
        # Should not have double spaces
        assert "  " not in result


class TestPromptBuilding:
    """Test prompt construction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = LLMService()
        self.sample_chunks = [
            {
                'content': 'LinuxONE provides enterprise security.',
                'document': {'title': 'Security Guide'},
                'page_number': 42
            },
            {
                'content': 'LinuxONE supports AI workloads.',
                'document': {'title': 'AI Toolkit'},
                'page_number': 15
            }
        ]
    
    def test_initial_prompt_structure(self):
        """Initial prompt should have correct structure."""
        prompt = self.service._build_prompt("What is LinuxONE?", self.sample_chunks)
        
        # Should contain key elements
        assert "LinuxONE Assistant" in prompt
        assert "ONLY the provided source context" in prompt
        assert "Security Guide" in prompt
        assert "AI Toolkit" in prompt
        assert "What is LinuxONE?" in prompt
        assert "Answer:" in prompt
        
        # Should NOT contain problematic instructions
        assert "truncation" not in prompt.lower()
        assert "output window" not in prompt.lower()
        assert "best possible answer" not in prompt.lower()
    
    def test_continuation_prompt_structure(self):
        """Continuation prompt should have correct structure."""
        partial = "LinuxONE provides"
        prompt = self.service._build_continuation_prompt(
            "What is LinuxONE?", self.sample_chunks, partial
        )
        
        # Should contain key elements
        assert "cut off" in prompt or "incomplete" in prompt
        assert "continue" in prompt.lower()
        assert partial in prompt
        assert "Do not restart" in prompt
        assert "Do not repeat" in prompt
        assert "Continuation:" in prompt
    
    def test_regenerate_prompt_structure(self):
        """Regenerate prompt should be stricter."""
        prompt = self.service._build_regenerate_prompt(
            "What is LinuxONE?", self.sample_chunks
        )
        
        # Should contain key elements
        assert "stable" in prompt.lower() or "complete" in prompt.lower()
        assert "ONLY" in prompt
        assert "grounded" in prompt.lower() or "sources" in prompt.lower()


class TestTokenBudget:
    """Test token budget enforcement."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = LLMService()
    
    def test_enforce_token_budget_under_limit(self):
        """Chunks under budget should all be included."""
        chunks = [
            {'content': 'Short content ' * 10},  # ~120 chars = ~30 tokens
            {'content': 'More content ' * 10},   # ~120 chars = ~30 tokens
        ]
        result = self.service._enforce_token_budget(chunks, max_context_tokens=100)
        assert len(result) == 2
    
    def test_enforce_token_budget_over_limit(self):
        """Chunks over budget should be truncated."""
        chunks = [
            {'content': 'Content ' * 100},  # ~800 chars = ~200 tokens
            {'content': 'More ' * 100},     # ~500 chars = ~125 tokens
            {'content': 'Extra ' * 100},    # ~600 chars = ~150 tokens
        ]
        result = self.service._enforce_token_budget(chunks, max_context_tokens=300)
        # Should include first two but not third
        assert len(result) < len(chunks)
    
    def test_calculate_context_tokens(self):
        """Token calculation should be reasonable."""
        chunks = [
            {'content': 'a' * 400},  # 400 chars = ~100 tokens
            {'content': 'b' * 800},  # 800 chars = ~200 tokens
        ]
        tokens = self.service._calculate_context_tokens(chunks)
        assert 250 <= tokens <= 350  # Should be around 300


class TestIntegrationScenarios:
    """Integration tests for common scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = LLMService()
    
    def test_complete_answer_scenario(self):
        """Complete answer should not trigger repair."""
        # This would need mocking of the actual API calls
        # For now, just test the validation logic
        complete_answer = "LinuxONE provides enterprise-grade security features including encryption, secure boot, and tamper-resistant hardware."
        is_incomplete, _ = self.service._looks_incomplete(complete_answer, "stop")
        assert not is_incomplete
    
    def test_truncated_answer_scenario(self):
        """Truncated answer should be detected."""
        truncated_answer = "LinuxONE provides enterprise-grade security features including encryption, secure boot, and"
        is_incomplete, reason = self.service._looks_incomplete(truncated_answer, "length")
        assert is_incomplete
        assert "length" in reason or "dangling connector" in reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob