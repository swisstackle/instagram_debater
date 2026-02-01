# Instagram Debate-Bot

An automated Instagram comment responder that engages with commenters using evidence-based arguments from curated articles.

## Overview

The Instagram Debate-Bot is a lightweight, stateless automation tool that:
- Monitors comments on designated Instagram posts
- Identifies debatable claims using AI
- Selects the most relevant article from multiple sources
- Responds with relevant citations and arguments from the selected article
- Maintains transparency by identifying itself as a bot
- Operates without persistent databases or vector stores

## Project Structure

```
.
├── articles/           # Source articles for debate responses
├── src/               # Core application code
│   ├── config.py          # Configuration management
│   ├── file_utils.py      # File utility functions
│   ├── instagram_api.py   # Instagram Graph API wrapper
│   ├── llm_client.py      # OpenRouter LLM client
│   ├── processor.py       # Main processing loop
│   ├── validator.py       # Response validation
│   └── webhook_receiver.py # Webhook handling
├── templates/         # Prompt templates for LLM
├── tests/             # Test suite
│   ├── unit/              # Unit tests
│   ├── api/               # API tests with mocking
│   └── fixtures/          # Test fixtures
├── state/             # Runtime state files (gitignored)
└── requirements.txt   # Python dependencies
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Required environment variables:**
   - `INSTAGRAM_APP_SECRET` - Instagram app secret for webhook verification
   - `INSTAGRAM_ACCESS_TOKEN` - Instagram access token
   - `INSTAGRAM_VERIFY_TOKEN` - Webhook verification token
   - `OPENROUTER_API_KEY` - OpenRouter API key for LLM access
   - `MODEL_NAME` - LLM model (default: google/gemini-flash-2.0)

4. **Article configuration:**
   - `ARTICLES_CONFIG` - JSON array with article configurations
   ```json
   [
     {"path": "articles/article1.md", "link": "https://example.com/article1"},
     {"path": "articles/article2.md", "link": "https://example.com/article2"}
   ]
   ```

## Development

This project follows **Test-Driven Development (TDD)** principles:

1. Write tests first
2. Run tests (they fail)
3. Implement functionality
4. Run tests (they pass)
5. Refactor and iterate

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/unit/test_validator.py

# Run with coverage
pytest --cov=src tests/
```

## Architecture

### Core Components

1. **Webhook Receiver** (`webhook_receiver.py`)
   - Receives Instagram webhook notifications
   - Verifies webhook signatures
   - Saves comments to pending queue

2. **Comment Processor** (`processor.py`)
   - Loads pending comments
   - Selects relevant article from multiple sources
   - Checks relevance using LLM
   - Generates responses with citations
   - Validates responses
   - Posts approved responses

3. **Instagram API** (`instagram_api.py`)
   - Fetches comment data
   - Posts replies
   - Manages rate limits

4. **LLM Client** (`llm_client.py`)
   - Generates debate responses
   - Determines article relevance
   - Checks topic relevance
   - Checks comment relevance

5. **Validator** (`validator.py`)
   - Validates citations
   - Checks response length
   - Detects hallucinations

## Design Principles

- **No Database**: Uses JSON files for state management
- **No Vector Store**: Feeds full article to LLM each time
- **Stateless**: Each run is independent
- **Multiple Sources**: Supports multiple articles, selects most relevant per comment
- **Zero Hallucination**: All responses cite article content
- **Transparent**: Clearly identifies as a bot

## API Reference

### Webhook Endpoints

- `GET /webhook/instagram` - Webhook verification
- `POST /webhook/instagram` - Receive comment notifications

## Contributing

Follow TDD principles:
1. Write tests first
2. Implement functionality
3. Ensure all tests pass
4. Submit PR with test coverage

## License

See LICENSE file for details.

## References

- [Instagram Platform Documentation](https://developers.facebook.com/docs/instagram-api/)
- [OpenRouter API](https://openrouter.ai/docs)
- [RFC Document](rfc.md) - Complete specification

---

**Note**: This bot is designed for educational and advocacy purposes. Always comply with Instagram's Terms of Service and platform policies.
