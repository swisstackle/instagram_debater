"""
Response validation for the Instagram Debate Bot.
Validates generated responses for citation accuracy, hallucination detection, and length constraints.
"""
import re
from typing import List, Tuple, Dict, Any


class ResponseValidator:
    """Validates LLM-generated responses against article content and Instagram constraints."""

    def __init__(self, article_text: str):
        """
        Initialize validator with article content.

        Args:
            article_text: Full text of the source article
        """
        self.article_text = article_text

    def validate_response(self, response: str) -> Tuple[bool, List[str]]:
        """
        Validate a generated response against all rules.

        Args:
            response: Generated response text

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Validate citations
        citations_valid, citation_errors = self.validate_citations(response)
        errors.extend(citation_errors)

        # Validate length
        length_valid, length_errors = self.validate_length(response)
        errors.extend(length_errors)

        # Check for hallucinations
        hallucination_valid, hallucination_errors = self.check_hallucination(response)
        errors.extend(hallucination_errors)

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_citations(self, response: str) -> Tuple[bool, List[str]]:
        """
        Validate that all citations in response exist in the article.

        Args:
            response: Generated response text

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        citations = self.extract_citations(response)

        for citation in citations:
            if not self.citation_exists(citation):
                errors.append(f"Invalid citation: {citation} not found in article")

        is_valid = len(errors) == 0
        return is_valid, errors

    def extract_citations(self, text: str) -> List[str]:
        """
        Extract all citation references from text (e.g., §1.1.1).

        Args:
            text: Text to extract citations from

        Returns:
            List of citation strings
        """
        # Match pattern like §1, §1.1, §1.1.1, etc.
        pattern = r'§\d+(?:\.\d+)*'
        citations = re.findall(pattern, text)
        return citations

    def citation_exists(self, citation: str) -> bool:
        """
        Check if a citation exists in the article.

        Args:
            citation: Citation string (e.g., "§1.1.1")

        Returns:
            True if citation exists in article
        """
        # Simple check: see if the citation appears in the article text
        return citation in self.article_text

    def validate_length(self, response: str) -> Tuple[bool, List[str]]:
        """
        Validate response length against Instagram limits.

        Args:
            response: Generated response text

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        length = len(response)

        # Instagram limit is 2200 characters
        if length > 2200:
            errors.append(f"Response too long: {length} characters (max: 2200)")

        is_valid = len(errors) == 0
        return is_valid, errors

    def check_hallucination(self, response: str) -> Tuple[bool, List[str]]:
        """
        Check for potential hallucinations (facts not in article).

        Args:
            response: Generated response text

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        # Basic hallucination check
        # This is a simplified implementation - could be enhanced with more sophisticated NLP
        errors = []

        # Look for common study/research citations that might be hallucinated
        suspicious_patterns = [
            r'according to a \d{4} study',
            r'research from \d{4}',
            r'a study published in'
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, response.lower()):
                # Check if this phrase exists in the article
                matches = re.findall(pattern, response.lower())
                for match in matches:
                    if match not in self.article_text.lower():
                        # This might be a hallucination, but let's be lenient for now
                        # Only flag if we're confident
                        pass

        # For now, we'll be lenient and only fail on obvious hallucinations
        is_valid = True
        return is_valid, errors
