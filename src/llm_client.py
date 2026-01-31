"""
LLM client wrapper for OpenRouter API.
Handles prompt generation and LLM API calls.
"""
from typing import Dict, Any, Optional


class LLMClient:
    """Wrapper for OpenRouter LLM API."""
    
    def __init__(self, api_key: str, model_name: str, max_tokens: int = 2000, temperature: float = 0.7):
        """
        Initialize LLM client.
        
        Args:
            api_key: OpenRouter API key
            model_name: Model identifier (e.g., "google/gemini-flash-2.0")
            max_tokens: Maximum tokens for response
            temperature: Temperature for response generation
        """
        pass
    
    def generate_response(self, prompt: str) -> str:
        """
        Generate a response using the LLM.
        
        Args:
            prompt: Prompt text
            
        Returns:
            Generated response text
        """
        pass
    
    def load_template(self, template_name: str) -> str:
        """
        Load a prompt template from the templates directory.
        
        Args:
            template_name: Name of template file (e.g., "debate_prompt.txt")
            
        Returns:
            Template content
        """
        pass
    
    def fill_template(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Fill template with variables.
        
        Args:
            template: Template string with {{VARIABLE}} placeholders
            variables: Dictionary of variable names to values
            
        Returns:
            Filled template string
        """
        pass
    
    def check_post_topic_relevance(self, article_title: str, article_summary: str, post_caption: str) -> bool:
        """
        Check if a post is relevant to the article topic.
        
        Args:
            article_title: Title of the article
            article_summary: Summary/first paragraph of article
            post_caption: Instagram post caption
            
        Returns:
            True if post is relevant to article topic
        """
        pass
    
    def check_comment_relevance(self, article_title: str, article_summary: str, comment_text: str) -> bool:
        """
        Check if a comment is relevant to the article.
        
        Args:
            article_title: Title of the article
            article_summary: Summary/first paragraph of article
            comment_text: Comment text
            
        Returns:
            True if comment is relevant and debatable
        """
        pass
