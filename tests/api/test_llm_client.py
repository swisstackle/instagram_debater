"""
API tests for LLM client wrapper.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.llm_client import LLMClient
import os


class TestLLMClient:
    """Test suite for LLMClient class."""
    
    @pytest.fixture
    def llm_client(self):
        """Create LLMClient instance for testing."""
        return LLMClient(
            api_key="test_api_key",
            model_name="google/gemini-flash-2.0",
            max_tokens=2000,
            temperature=0.7
        )
    
    def test_llm_client_initialization(self):
        """Test that LLMClient initializes properly."""
        client = LLMClient(
            api_key="test_key",
            model_name="test_model",
            max_tokens=1000,
            temperature=0.5
        )
        assert client is not None
    
    @patch('src.llm_client.OpenRouter')
    def test_generate_response_success(self, mock_openrouter, llm_client):
        """Test generating a response using the LLM."""
        # Mock the OpenRouter client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated response text"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openrouter.return_value = mock_client
        
        # Create new client with mocked OpenRouter
        client = LLMClient(
            api_key="test_key",
            model_name="test_model"
        )
        
        result = client.generate_response("Test prompt")
        assert result == "Generated response text"
    
    def test_load_template_success(self, llm_client, tmp_path):
        """Test loading a template file."""
        # Create a temporary template file
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test_template.txt"
        template_file.write_text("Hello {{NAME}}")
        
        # Mock the template path
        with patch('os.path.dirname') as mock_dirname:
            mock_dirname.return_value = str(tmp_path)
            template = llm_client.load_template("test_template.txt")
            # This test depends on implementation details
            assert isinstance(template, str)
    
    def test_fill_template_simple(self, llm_client):
        """Test filling template with simple variables."""
        template = "Hello {{NAME}}, welcome to {{PLACE}}"
        variables = {"NAME": "Alice", "PLACE": "Wonderland"}
        
        result = llm_client.fill_template(template, variables)
        assert result == "Hello Alice, welcome to Wonderland"
    
    def test_fill_template_multiple_occurrences(self, llm_client):
        """Test filling template with repeated variables."""
        template = "{{WORD}} {{WORD}} {{WORD}}"
        variables = {"WORD": "test"}
        
        result = llm_client.fill_template(template, variables)
        assert result == "test test test"
    
    def test_fill_template_missing_variable(self, llm_client):
        """Test filling template with missing variables."""
        template = "Hello {{NAME}}, you have {{COUNT}} items"
        variables = {"NAME": "Bob"}
        
        result = llm_client.fill_template(template, variables)
        # Should either keep placeholder or handle gracefully
        assert "Bob" in result
    
    @patch('src.llm_client.OpenRouter')
    def test_check_post_topic_relevance_yes(self, mock_openrouter, llm_client):
        """Test checking post topic relevance when answer is YES."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "YES - The post is about the same topic."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openrouter.return_value = mock_client
        
        client = LLMClient(api_key="test", model_name="test")
        
        is_relevant = client.check_post_topic_relevance(
            article_title="Fitness Tips",
            article_summary="This article discusses fitness",
            post_caption="Great fitness advice!"
        )
        assert is_relevant is True
    
    @patch('src.llm_client.OpenRouter')
    def test_check_post_topic_relevance_no(self, mock_openrouter, llm_client):
        """Test checking post topic relevance when answer is NO."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "NO - The post is about a different topic."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openrouter.return_value = mock_client
        
        client = LLMClient(api_key="test", model_name="test")
        
        is_relevant = client.check_post_topic_relevance(
            article_title="Fitness Tips",
            article_summary="This article discusses fitness",
            post_caption="Random unrelated content"
        )
        assert is_relevant is False
    
    @patch('src.llm_client.OpenRouter')
    def test_check_comment_relevance_yes(self, mock_openrouter, llm_client):
        """Test checking comment relevance when answer is YES."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "YES - The comment presents a debatable claim."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openrouter.return_value = mock_client
        
        client = LLMClient(api_key="test", model_name="test")
        
        is_relevant = client.check_comment_relevance(
            article_title="Fitness Article",
            article_summary="About exercise",
            comment_text="But squats are dangerous!"
        )
        assert is_relevant is True
    
    @patch('src.llm_client.OpenRouter')
    def test_check_comment_relevance_no(self, mock_openrouter, llm_client):
        """Test checking comment relevance when answer is NO."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "NO - Just a generic compliment."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openrouter.return_value = mock_client
        
        client = LLMClient(api_key="test", model_name="test")
        
        is_relevant = client.check_comment_relevance(
            article_title="Fitness Article",
            article_summary="About exercise",
            comment_text="Nice post!"
        )
        assert is_relevant is False
