# Instagram Debate-Bot

An automated Instagram comment responder that engages with commenters using evidence-based arguments from curated articles.

## Overview

The Instagram Debate-Bot is a lightweight, stateless automation tool that:
- Monitors comments on designated Instagram posts
- MAINTAINS TRANSPARENCY BY IDENTIFYING ITSELF AS A BOT
- Identifies debatable claims using AI
- Selects the most relevant article from multiple sources
- Responds with relevant citations and arguments from the selected article

- Operates without persistent databases or vector stores

## Project Structure

```
.
├── articles/           # Source articles with numbered sections (§X.Y.Z)
├── articles_unnumbered/ # Source articles without numbered sections
├── src/               # Core application code
│   ├── base_json_extractor.py       # Base classes for JSON storage extractors
│   ├── audit_log_extractor.py       # Abstract audit log extractor interface
│   ├── audit_log_extractor_factory.py # Factory for creating audit log extractors
│   ├── local_disk_audit_extractor.py # Local disk audit log storage (implements audit_log_extractor)
│   ├── tigris_audit_extractor.py    # Tigris/S3 audit log storage (implements audit_log_extractor)
│   ├── comment_extractor.py         # Abstract comment extractor interface
│   ├── comment_extractor_factory.py # Factory for creating comment extractors
│   ├── local_disk_extractor.py      # Local disk storage implementation (implements comment_extractor)
│   ├── tigris_extractor.py          # Tigris/S3 storage implementation (implements comment_extractor)
│   ├── token_extractor.py           # Abstract token extractor interface
│   ├── token_extractor_factory.py   # Factory for creating token extractors
│   ├── local_disk_token_extractor.py # Local disk OAuth token storage (implements token_extractor)
│   ├── tigris_token_extractor.py    # Tigris/S3 OAuth token storage (implements token_extractor)
│   ├── env_var_token_extractor.py   # Environment variable token storage (implements token_extractor)
│   ├── mode_extractor.py            # Abstract mode extractor interface
│   ├── mode_extractor_factory.py    # Factory for creating mode extractors
│   ├── local_disk_mode_extractor.py # Local disk auto-post mode storage (implements mode_extractor)
│   ├── tigris_mode_extractor.py     # Tigris/S3 auto-post mode storage (implements mode_extractor)
│   ├── config.py                    # Configuration management
│   ├── file_utils.py                # File utility functions
│   ├── instagram_api.py             # Instagram Graph API wrapper
│   ├── llm_client.py                # OpenRouter LLM client
│   ├── processor.py                 # Main processing loop
│   ├── validator.py                 # Response validation
│   └── webhook_receiver.py          # Webhook handling
├── templates/         # Prompt templates for LLM
│   ├── debate_prompt.txt           # For numbered articles
│   └── debate_prompt_unnumbered.txt # For unnumbered articles
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
   - `INSTAGRAM_ACCESS_TOKEN` - Instagram access token (or use OAuth login)
   - `INSTAGRAM_VERIFY_TOKEN` - Webhook verification token
   - `OPENROUTER_API_KEY` - OpenRouter API key for LLM access
   - `MODEL_NAME` - LLM model (default: google/gemini-flash-2.0)

4. **OAuth configuration (for Instagram Business Login):**
   - `INSTAGRAM_CLIENT_ID` - Facebook App ID
   - `INSTAGRAM_CLIENT_SECRET` - Facebook App Secret
   - `INSTAGRAM_REDIRECT_URI` - OAuth callback URL (default: http://127.0.0.1:5000/auth/instagram/callback)
   
   **Setting up OAuth:**
   1. Create a Facebook App at [Meta for Developers](https://developers.facebook.com/)
   2. Add Instagram Basic Display API or Instagram Graph API
   3. Configure OAuth redirect URIs in the app settings
   4. Add the credentials to your `.env` file
   5. Start the dashboard and click "Login with Instagram"
   6. The bot will automatically obtain and refresh long-lived tokens (60 days)

5. **Optional server configuration:**
   - `DASHBOARD_PORT` - Dashboard server port (default: 5000)
   - `DASHBOARD_HOST` - Dashboard server host (default: 127.0.0.1)
   - `WEBHOOK_PORT` - Webhook server port (default: 8000)
   - `WEBHOOK_HOST` - Webhook server host (default: 0.0.0.0)

6. **Storage configuration:**
   
   **Comment storage:**
   - `COMMENT_STORAGE_TYPE` - Storage backend for pending comments (`local` or `tigris`, default: `local`)
     - `local` - Uses local disk storage (`state/pending_comments.json`)
     - `tigris` - Uses Tigris object storage on Fly.io (S3-compatible)
   
   **Audit log storage:**
   - `AUDIT_LOG_STORAGE_TYPE` - Storage backend for audit logs (`local` or `tigris`, default: `local`)
     - `local` - Uses local disk storage (`state/audit_log.json`)
     - `tigris` - Uses Tigris object storage on Fly.io (S3-compatible)
   
   **OAuth token storage:**
   - `OAUTH_TOKEN_STORAGE_TYPE` - Storage backend for OAuth tokens (`local`, `tigris`, or `env_var`, default: `local`)
     - `local` - Uses local disk storage (`state/instagram_token.json`) with automatic OAuth refresh
     - `tigris` - Uses Tigris object storage on Fly.io (S3-compatible, recommended for distributed deployments)
     - `env_var` - Reads token directly from `INSTAGRAM_ACCESS_TOKEN` environment variable (read-only, no refresh)
   
   **Auto-post mode storage:**
   - `MODE_STORAGE_TYPE` - Storage backend for the auto-post mode toggle (`local` or `tigris`, default: `local`)
     - `local` - Stores mode in `state/mode.json` on local disk (single-machine deployments)
     - `tigris` - Stores mode in Tigris object storage (`state/mode.json` in S3 bucket); use this when dashboard, processor, and webhook run on separate machines so all components read the same value
   
   **For Tigris storage (only needed when `COMMENT_STORAGE_TYPE=tigris` or `AUDIT_LOG_STORAGE_TYPE=tigris`):**
   - `AWS_ACCESS_KEY_ID` - Tigris access key ID
   - `AWS_SECRET_ACCESS_KEY` - Tigris secret access key
   - `AWS_ENDPOINT_URL_S3` - Tigris endpoint URL (default: https://fly.storage.tigris.dev)
   - `TIGRIS_BUCKET_NAME` - Tigris bucket name
   - `AWS_REGION` - AWS region (default: auto)
   
   **Setting up Tigris storage:**
   1. Create a Tigris bucket on Fly.io: `fly storage create`
   2. Copy the generated credentials to your `.env` file
   3. Set `COMMENT_STORAGE_TYPE=tigris` and/or `AUDIT_LOG_STORAGE_TYPE=tigris`
   4. The bot will automatically use Tigris for storing pending comments and/or audit logs
   5. Set `MODE_STORAGE_TYPE=tigris` so the auto-post mode toggle is shared across all machines
   
   This is useful when running distributed systems where the webhook server, dashboard, 
   and comment processor are on different machines and need shared storage for both 
   pending comments and audit logs.

7. **Article configuration:**
   - `ARTICLES_CONFIG` - JSON array with article configurations
   - Each article can specify `is_numbered` (default: true)
     - `is_numbered: true` - Article uses numbered sections (§X.Y.Z) and requires citations
     - `is_numbered: false` - Article without numbered sections, no citations required
   ```json
   [
     {"path": "articles/article1.md", "link": "https://example.com/article1", "is_numbered": true},
     {"path": "articles_unnumbered/article2.md", "link": "https://example.com/article2", "is_numbered": false}
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
   - Saves comments to pending queue via comment extractor

2. **Storage Extractors** (modular interfaces with base classes)
   
   **Base Classes** (`base_json_extractor.py`)
   - `BaseLocalDiskExtractor` - Common functionality for local disk JSON storage
   - `BaseTigrisExtractor` - Common functionality for S3/Tigris object storage
   
   These base classes eliminate code duplication between comment and audit log extractors by providing:
   - Shared state directory management
   - Common JSON file load/save operations
   - Unified S3 client initialization and credential handling
   - Reusable S3 read/write helper methods
   
   **Comment Extractor** (modular interface)
   - **Abstract Interface** (`comment_extractor.py`) - Defines the contract for storage backends
   - **Local Disk Extractor** (`local_disk_extractor.py`) - Stores comments in local JSON files (extends `BaseLocalDiskExtractor`)
   - **Tigris Extractor** (`tigris_extractor.py`) - Stores comments in Tigris object storage (extends `BaseTigrisExtractor`)
   - **Factory** (`comment_extractor_factory.py`) - Creates appropriate extractor based on `COMMENT_STORAGE_TYPE`
   
   **Audit Log Extractor** (modular interface)
   - **Abstract Interface** (`audit_log_extractor.py`) - Defines the contract for audit log storage
   - **Local Disk Audit Extractor** (`local_disk_audit_extractor.py`) - Stores audit logs in local JSON files (extends `BaseLocalDiskExtractor`)
   - **Tigris Audit Extractor** (`tigris_audit_extractor.py`) - Stores audit logs in Tigris object storage (extends `BaseTigrisExtractor`)
   - **Factory** (`audit_log_extractor_factory.py`) - Creates appropriate extractor based on `AUDIT_LOG_STORAGE_TYPE`
   
   This modular design allows the webhook server, dashboard, and comment processor to run on 
   different machines while sharing common storage backends for both comments and audit logs.

3. **Comment Processor** (`processor.py`)
   - Loads pending comments via comment extractor
   - Selects relevant article from multiple sources
   - Checks relevance using LLM
   - Generates responses with citations
   - Validates responses
   - Posts approved responses
   - Saves audit log entries via audit log extractor

4. **Instagram API** (`instagram_api.py`)
   - Fetches comment data
   - Posts replies
   - Manages rate limits

5. **LLM Client** (`llm_client.py`)
   - Generates debate responses
   - Determines article relevance
   - Checks topic relevance
   - Checks comment relevance

6. **Validator** (`validator.py`)
   - Validates citations
   - Checks response length
   - Detects hallucinations

    **Token Extractor** (modular interface)
   - **Abstract Interface** (`token_extractor.py`) - Defines the contract for token storage
   - **Local Disk Token Extractor** (`local_disk_token_extractor.py`) - Stores tokens in local JSON files (extends `BaseLocalDiskExtractor`)
   - **Tigris Token Extractor** (`tigris_token_extractor.py`) - Stores tokens in Tigris object storage (extends `BaseTigrisExtractor`)
   - **Factory** (`token_extractor_factory.py`) - Creates appropriate extractor based on `OAUTH_TOKEN_STORAGE_TYPE`
   
   Features:
   - Manages OAuth access tokens with automatic refresh
   - Stores long-lived tokens (60-day validity)
   - Automatically refreshes tokens before expiration (5-day buffer)
   - Supports distributed deployments with shared Tigris storage
   - Handles token expiration checks

8. **Mode Extractor** (modular interface)
   - **Abstract Interface** (`mode_extractor.py`) - Defines the contract for mode storage (`get_auto_mode`, `set_auto_mode`)
   - **Local Disk Mode Extractor** (`local_disk_mode_extractor.py`) - Stores mode in `state/mode.json` (extends `BaseLocalDiskExtractor`)
   - **Tigris Mode Extractor** (`tigris_mode_extractor.py`) - Stores mode in Tigris object storage (extends `BaseTigrisExtractor`)
   - **Factory** (`mode_extractor_factory.py`) - Creates appropriate extractor based on `MODE_STORAGE_TYPE`
   
   Enables all distributed components (dashboard, processor, webhook) to share the same auto-post mode setting.

9. **Dashboard** (`dashboard.py`)
   - Web interface for reviewing responses
   - OAuth login/logout functionality
   - Displays authentication status
   - Shows token expiration information
   - Uses audit log extractor for reading/updating responses
   - **Auto-post mode toggle** — switches between Auto and Manual modes; reads/writes via mode extractor so the change is immediately visible to the processor on any machine

## Design Principles

- **No Database**: Uses simple storage backends (JSON files or object storage)
- **No Vector Store**: Feeds full article to LLM each time
- **Stateless**: Each run is independent
- **Multiple Sources**: Supports multiple articles, selects most relevant per comment
- **Zero Hallucination**: All responses cite article content
- **Modular Storage**: Pluggable storage backends allow distributed deployment
- **Transparent**: Clearly identifies as a bot

## API Reference

### Webhook Endpoints

- `GET /webhook/instagram` - Webhook verification
- `POST /webhook/instagram` - Receive comment notifications

### Dashboard Endpoints

- `GET /api/mode` — returns `{"auto_mode": bool}`
- `POST /api/mode` — sets the auto-post mode; body: `{"auto_mode": true|false}`

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
