"""
LLM client wrapper for OpenRouter API.
Handles prompt generation and LLM API calls.
"""
import os
from typing import Any, Dict, Optional

from openrouter import OpenRouter

from src.prompt_extractor import PromptExtractor


class LLMClient:
    """Wrapper for OpenRouter LLM API."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        prompt_extractor: Optional[PromptExtractor] = None,
    ):
        """
        Initialize LLM client.

        Args:
            api_key: OpenRouter API key
            model_name: Model identifier (e.g., "google/gemini-flash-2.0")
            max_tokens: Maximum tokens for response
            temperature: Temperature for response generation
            prompt_extractor: Optional prompt extractor for runtime-editable templates
                (defaults to factory-created instance based on PROMPT_STORAGE_TYPE)
        """
        self.api_key = api_key
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = OpenRouter(api_key=api_key)

        if prompt_extractor is None:
            from src.prompt_extractor_factory import create_prompt_extractor
            prompt_extractor = create_prompt_extractor()
            print("No prompt extractor provided, created using factory based on configuration.")
        self.prompt_extractor = prompt_extractor

    def generate_response(self, prompt: str) -> str:
        """
        Generate a response using the LLM.

        Args:
            prompt: Prompt text

        Returns:
            Generated response text
        """
        response = self.client.chat.send(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a debate assistant bot."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        return response.choices[0].message.content

    def load_template(self, template_name: str) -> str:
        """
        Load a prompt template. Checks the prompt extractor first (for runtime-editable
        templates), then falls back to the templates directory on disk.

        The lookup key is the template_name with the .txt extension stripped
        (e.g. "debate_prompt.txt" → "debate_prompt").

        Args:
            template_name: Name of template file (e.g., "debate_prompt.txt")

        Returns:
            Template content
        """
        # Strip .txt extension to get the storage key
        key = template_name[:-4] if template_name.endswith(".txt") else template_name

        # Check runtime-editable store first
        stored = self.prompt_extractor.get_prompt(key)
        if stored:
            return stored

        # Fall back to filesystem template
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        template_path = os.path.join(project_root, "templates", template_name)

        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def fill_template(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Fill template with variables.

        Args:
            template: Template string with {{VARIABLE}} placeholders
            variables: Dictionary of variable names to values

        Returns:
            Filled template string
        """
        result = template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result

    def check_post_topic_relevance(
        self, article_title: str, article_summary: str, post_caption: str
    ) -> bool:
        """
        Check if a post is relevant to the article topic.

        Args:
            article_title: Title of the article
            article_summary: Summary/first paragraph of article
            post_caption: Instagram post caption

        Returns:
            True if post is relevant to article topic
        """
        template = self.load_template("post_topic_check_prompt.txt")
        prompt = self.fill_template(template, {
            "ARTICLE_TITLE": article_title,
            "ARTICLE_FIRST_PARAGRAPH": article_summary,
            "POST_CAPTION": post_caption
        })

        response = self.generate_response(prompt)

        # Parse response - looking for YES or NO
        response_upper = response.upper()
        if "YES" in response_upper[:10]:
            return True
        return False

    def check_comment_relevance(
        self, article_title: str, article_summary: str, comment_text: str
    ) -> bool:
        """
        Check if a comment is relevant to the article.

        Args:
            article_title: Title of the article
            article_summary: Summary/first paragraph of article
            comment_text: Comment text

        Returns:
            True if comment is relevant and debatable
        """
        template = self.load_template("comment_relevance_check_prompt.txt")
        prompt = self.fill_template(template, {
            "ARTICLE_TITLE": article_title,
            "ARTICLE_FIRST_PARAGRAPH": article_summary,
            "COMMENT_TEXT": comment_text
        })

        response = self.generate_response(prompt)

        # Parse response - looking for YES or NO
        response_upper = response.upper()
        if "YES" in response_upper[:10]:
            return True
        return False

    def check_topic_relevance(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        article_title: str,
        article_summary: str,
        post_caption: str,
        comment_text: str,
        thread_context: str
    ) -> bool:
        """
        Check if content is relevant to the article topic.

        This method considers the post caption, comment, and conversation history
        to determine if the article is relevant.

        Args:
            article_title: Title of the article
            article_summary: Summary/first paragraph of article
            post_caption: Instagram post caption
            comment_text: Comment text
            thread_context: Thread conversation context

        Returns:
            True if content is relevant to article topic
        """
        template = self.load_template("topic_relevance_check_prompt.txt")

        thread_text = ""
        if thread_context:
            thread_text = f"\nTHREAD CONTEXT:\n{thread_context}"

        prompt = self.fill_template(template, {
            "ARTICLE_TITLE": article_title,
            "ARTICLE_FIRST_PARAGRAPH": article_summary,
            "POST_CAPTION": post_caption,
            "COMMENT_TEXT": comment_text,
            "THREAD_CONTEXT": thread_text
        })

        response = self.generate_response(prompt)

        # Parse response - looking for YES or NO
        response_upper = response.upper()
        if "YES" in response_upper[:10]:
            return True
        return False
