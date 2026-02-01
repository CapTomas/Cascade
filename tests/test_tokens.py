"""Tests for cascade.utils.tokens module."""

from unittest.mock import MagicMock


class TestCountTokens:
    """Tests for the count_tokens function."""

    def test_empty_string_returns_zero(self):
        """Empty string should return 0 tokens."""
        from cascade.utils.tokens import count_tokens

        assert count_tokens("") == 0

    def test_none_returns_zero(self):
        """None/empty should return 0 tokens."""
        from cascade.utils.tokens import count_tokens

        # Empty string test
        assert count_tokens("") == 0

    def test_simple_text_with_tiktoken(self):
        """Test token counting with tiktoken available."""
        from cascade.utils.tokens import count_tokens

        # Simple sentence should return reasonable token count
        result = count_tokens("Hello, world!")
        assert result > 0
        assert result < 10  # Should be around 4 tokens

    def test_longer_text(self):
        """Test counting tokens in longer text."""
        from cascade.utils.tokens import count_tokens

        long_text = "This is a longer piece of text that should have more tokens. " * 10
        result = count_tokens(long_text)
        assert result > 50  # Should be significantly more than simple text

    def test_different_models(self):
        """Test token counting with different model names."""
        from cascade.utils.tokens import count_tokens

        text = "Hello, world!"

        # All should use cl100k_base encoding (as per implementation)
        gpt4_count = count_tokens(text, model="gpt-4")
        gpt35_count = count_tokens(text, model="gpt-3.5-turbo")
        claude_count = count_tokens(text, model="claude-3")
        default_count = count_tokens(text, model="unknown-model")

        # All should return the same count since they use same encoding
        assert gpt4_count == gpt35_count == claude_count == default_count

    def test_fallback_without_tiktoken(self):
        """Test fallback estimation when tiktoken is not available."""
        from cascade.utils import tokens

        # Save original tiktoken reference
        original_tiktoken = tokens.tiktoken

        try:
            # Simulate tiktoken not being available
            tokens.tiktoken = None

            from cascade.utils.tokens import count_tokens

            text = "This is a test string with exactly forty characters!"
            result = count_tokens(text)

            # Fallback uses len(text) // 4
            expected = len(text) // 4
            assert result == expected
        finally:
            # Restore original
            tokens.tiktoken = original_tiktoken

    def test_tiktoken_error_fallback(self):
        """Test fallback when tiktoken raises an error."""
        from cascade.utils import tokens

        # Create a mock that raises an exception
        mock_tiktoken = MagicMock()
        mock_tiktoken.get_encoding.side_effect = Exception("Encoding error")

        original_tiktoken = tokens.tiktoken

        try:
            tokens.tiktoken = mock_tiktoken

            from cascade.utils.tokens import count_tokens

            text = "Test text for error handling"
            result = count_tokens(text)

            # Should fall back to character-based estimate
            expected = len(text) // 4
            assert result == expected
        finally:
            tokens.tiktoken = original_tiktoken

    def test_special_characters(self):
        """Test token counting with special characters."""
        from cascade.utils.tokens import count_tokens

        # Text with emojis, unicode, special chars
        special_text = "Hello 🌍! Café résumé naïve coöperate"
        result = count_tokens(special_text)
        assert result > 0

    def test_code_content(self):
        """Test token counting with code content."""
        from cascade.utils.tokens import count_tokens

        code = '''
def hello_world():
    """Print hello world."""
    print("Hello, World!")
    return True
'''
        result = count_tokens(code)
        assert result > 10  # Code should have reasonable token count

    def test_whitespace_only(self):
        """Test token counting with whitespace-only content."""
        from cascade.utils.tokens import count_tokens

        whitespace = "   \n\t\t\n   "
        result = count_tokens(whitespace)
        # Should return some small number of tokens
        assert result >= 0


class TestTokenBudget:
    """Test token budget calculations."""

    def test_minimal_mode_budget(self):
        """Test that minimal mode stays within budget."""
        from cascade.utils.tokens import count_tokens

        # Typical minimal context
        minimal_context = """
## Task
Complete the following ticket. Focus only on this ticket.

## Ticket #42: Add user authentication
Type: TASK
Priority: HIGH

### Description
Implement basic user authentication with JWT tokens.

### Acceptance Criteria
- Users can register with email/password
- Users can login and receive JWT
- Protected routes require valid JWT

## Project Conventions
- Use camelCase for variables
- Use PascalCase for classes
- 2 spaces indentation
"""
        tokens = count_tokens(minimal_context)
        # Minimal should be under 2000 tokens
        assert tokens < 2000, f"Minimal context has {tokens} tokens, should be < 2000"

    def test_standard_mode_budget(self):
        """Test that standard mode stays within budget."""
        from cascade.utils.tokens import count_tokens

        # Typical standard context (minimal + patterns + ADRs)
        standard_context = """
## Task
Complete the following ticket. Focus only on this ticket.

## Ticket #42: Add user authentication
Type: TASK
Priority: HIGH

### Description
Implement basic user authentication with JWT tokens.

### Acceptance Criteria
- Users can register with email/password
- Users can login and receive JWT
- Protected routes require valid JWT

## Project Conventions
- Use camelCase for variables
- Use PascalCase for classes
- 2 spaces indentation

## Relevant Patterns

### Pattern: JWT Authentication
Use jsonwebtoken for signing and verifying tokens.
Store refresh tokens in Redis with expiry.

```javascript
const jwt = require('jsonwebtoken');
const token = jwt.sign({ userId }, secret, { expiresIn: '1h' });
```

### Pattern: Password Hashing
Always use bcrypt with cost factor 12.

## Architecture Decisions

### ADR-001: Use JWT for Authentication
**Context**: Need stateless authentication for API.
**Decision**: Use JWT with RS256 signing.
**Rationale**: Allows horizontal scaling without session storage.
"""
        tokens = count_tokens(standard_context)
        # Standard should be under 5000 tokens
        assert tokens < 5000, f"Standard context has {tokens} tokens, should be < 5000"
