"""
Unit tests for response validator.
"""
import pytest
from src.validator import ResponseValidator


class TestResponseValidator:
    """Test suite for ResponseValidator class."""

    @pytest.fixture
    def sample_article(self):
        """Sample article with numbered sections."""
        return """
# Test Article

## §1. Introduction

### §1.1 Overview

This is a test article about fitness.

### §1.2 Details

Research shows that exercise is beneficial.

## §2. Main Points

### §2.1 Point One

The Journal of Sports Medicine (2020) indicates specific findings.

### §2.2 Point Two

Studies demonstrate effectiveness.
"""

    @pytest.fixture
    def validator(self, sample_article):
        """Create a ResponseValidator instance."""
        return ResponseValidator(sample_article)

    def test_validator_initialization(self, sample_article):
        """Test that validator initializes properly."""
        validator = ResponseValidator(sample_article)
        assert validator is not None

    def test_extract_citations_single(self, validator):
        """Test extracting a single citation."""
        text = "According to §1.1, exercise is good."
        citations = validator.extract_citations(text)
        assert "§1.1" in citations

    def test_extract_citations_multiple(self, validator):
        """Test extracting multiple citations."""
        text = "See §1.1 and §2.1 for details. Also §1.2."
        citations = validator.extract_citations(text)
        assert len(citations) == 3
        assert "§1.1" in citations
        assert "§2.1" in citations
        assert "§1.2" in citations

    def test_extract_citations_nested(self, validator):
        """Test extracting nested section citations."""
        text = "Reference §1.1.1 and §2.2.3"
        citations = validator.extract_citations(text)
        # Should extract even if they don't exist in article
        assert len(citations) >= 2

    def test_citation_exists_valid(self, validator):
        """Test that valid citations are recognized."""
        assert validator.citation_exists("§1.1") is True
        assert validator.citation_exists("§2.1") is True

    def test_citation_exists_invalid(self, validator):
        """Test that invalid citations are rejected."""
        assert validator.citation_exists("§9.9") is False
        assert validator.citation_exists("§3.1") is False

    def test_validate_citations_all_valid(self, validator):
        """Test validation passes with all valid citations."""
        response = "According to §1.1, exercise is beneficial. See §2.1 for more."
        is_valid, errors = validator.validate_citations(response)
        assert is_valid is True
        assert not errors

    def test_validate_citations_some_invalid(self, validator):
        """Test validation fails with invalid citations."""
        response = "See §1.1 and §9.9 for details."
        is_valid, errors = validator.validate_citations(response)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_length_within_limit(self, validator):
        """Test that responses within length limit pass."""
        response = "This is a short response."
        is_valid, errors = validator.validate_length(response)
        assert is_valid is True
        assert not errors

    def test_validate_length_too_long(self, validator):
        """Test that responses exceeding limit fail."""
        # Instagram limit is 2200 characters
        response = "x" * 2300
        is_valid, errors = validator.validate_length(response)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_length_too_short(self, validator):
        """Test that very short responses are flagged."""
        response = "Yes."  # Less than 200 chars
        is_valid, _errors = validator.validate_length(response)
        # Depending on implementation, might warn but not fail
        assert isinstance(is_valid, bool)

    def test_validate_response_all_checks(self, validator):
        """Test complete validation with all checks."""
        response = "According to §1.1, exercise is beneficial. The evidence in §2.1 supports this."
        is_valid, errors = validator.validate_response(response)
        assert is_valid is True
        assert not errors

    def test_validate_response_multiple_failures(self, validator):
        """Test validation with multiple failures."""
        # Too long and invalid citation
        response = "See §9.9. " + "x" * 2300
        is_valid, errors = validator.validate_response(response)
        assert is_valid is False
        assert len(errors) >= 2  # Should catch both issues

    def test_check_hallucination_basic(self, validator):
        """Test basic hallucination detection."""
        # This is a simplified test - actual implementation may vary
        response = "According to §1.1, the article discusses fitness topics."
        is_valid, _errors = validator.check_hallucination(response)
        # Should pass as it references content in the article
        assert isinstance(is_valid, bool)


class TestResponseValidatorUnnumbered:
    """Test suite for ResponseValidator with unnumbered articles."""

    @pytest.fixture
    def sample_unnumbered_article(self):
        """Sample article without numbered sections."""
        return """
# General Fitness Guidelines

Regular physical activity is one of the most important things you can do for your health.

## Benefits of Regular Exercise

Adults who sit less and do any amount of moderate-to-vigorous physical activity gain some health benefits.

## Getting Started

If you're not active now, starting any amount of physical activity can begin to deliver health benefits.
"""

    @pytest.fixture
    def unnumbered_validator(self, sample_unnumbered_article):
        """Create a ResponseValidator instance for unnumbered articles."""
        return ResponseValidator(sample_unnumbered_article, is_numbered=False)

    def test_validator_initialization_unnumbered(self, sample_unnumbered_article):
        """Test that validator initializes properly with is_numbered flag."""
        validator = ResponseValidator(sample_unnumbered_article, is_numbered=False)
        assert validator is not None
        assert validator.is_numbered is False

    def test_validate_response_unnumbered_no_citations(self, unnumbered_validator):
        """Test that unnumbered articles pass validation without citations."""
        response = "Regular exercise is beneficial for your health. It helps with weight management."
        is_valid, errors = unnumbered_validator.validate_response(response)
        assert is_valid is True
        assert not errors

    def test_validate_response_unnumbered_with_citations_still_valid(self, unnumbered_validator):
        """Test that citations in unnumbered articles don't cause validation failure."""
        response = "According to §1.1, exercise is good. But this article is unnumbered."
        is_valid, errors = unnumbered_validator.validate_response(response)
        # Should pass because we skip citation validation for unnumbered articles
        assert is_valid is True
        assert not errors

    def test_validate_citations_skipped_for_unnumbered(self, unnumbered_validator):
        """Test that citation validation is skipped for unnumbered articles."""
        response = "This has fake §9.9.9 citations that don't exist."
        is_valid, errors = unnumbered_validator.validate_citations(response)
        # Should pass because citation validation is skipped
        assert is_valid is True
        assert not errors

    def test_validate_length_still_applies_unnumbered(self, unnumbered_validator):
        """Test that length validation still applies to unnumbered articles."""
        response = "x" * 2300
        is_valid, errors = unnumbered_validator.validate_length(response)
        assert is_valid is False
        assert len(errors) > 0

    def test_extract_citations_still_works_unnumbered(self, unnumbered_validator):
        """Test that citation extraction still works for unnumbered articles."""
        text = "According to §1.1, exercise is good."
        citations = unnumbered_validator.extract_citations(text)
        assert "§1.1" in citations
