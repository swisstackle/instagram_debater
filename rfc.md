# RFC: Instagram Debate-Bot

**Status:** Draft
**Author:** fparticle team
**Created:** 2026-01-31
**Last Updated:** 2026-02-26

---

## 1. Introduction

### 1.1 What is the Instagram Debate-Bot?

The Instagram Debate-Bot is a lightweight, stateless automation tool that engages with Instagram post commenters by presenting counter-arguments drawn from multiple locally-stored Markdown articles. The bot monitors comments on designated Instagram posts, identifies claims or statements that can be debated, determines which articles are relevant, merges their content into a single combined context, and responds with arguments sourced from all matching articles. Articles can be numbered (with §X.Y.Z citations) or unnumbered (without citations).

### 1.2 Purpose

This tool is designed to:
- **Educate:** Share evidence-based arguments from curated articles with Instagram audiences
- **Engage:** Foster meaningful debate and discussion in comment sections
- **Scale:** Automate the process of responding to common misconceptions or opposing viewpoints
- **Maintain Quality:** Ensure all responses are grounded in vetted knowledge sources
- **Support Multiple Topics:** Consider all relevant articles per comment from multiple sources, merging their content within the prompt size budget

The bot is intended for accounts that share educational or advocacy content across multiple topics and want to systematically engage with commenters using well-researched arguments.

---

## 2. Goals

### 2.1 Primary Goals

1. **Accurate Citation:** Bot responses from numbered articles must cite specific sections (e.g., "§1.1.1", "§2.3"). Unnumbered articles do not require citations.
2. **Relevance Filtering:** Only respond to comments that present debatable claims related to the article's subject matter
3. **Human-Like Tone:** Generate responses that are conversational, respectful, and non-repetitive
4. **Full Transparency:** Clearly identify the bot as automated and provide links to the full article
5. **Zero Hallucination:** Never invent facts, citations, or arguments not present in the source article

### 2.2 Secondary Goals

1. **Minimal Infrastructure:** Run without persistent databases or vector stores
2. **Audit Trail:** Maintain human-readable logs of all interactions for review and improvement
3. **Human Oversight:** Enable manual review and approval of responses before posting (optional mode)
4. **Graceful Degradation:** Handle API rate limits, token limits, and edge cases without crashing

---

## 3. Hard Constraints

These constraints are **non-negotiable** and define the architecture:

1. **NO DATABASE:** The system must not use any persistent database (SQL, NoSQL, or otherwise)
2. **NO VECTOR STORE:** No embeddings, no semantic search, no vector databases (Pinecone, Chroma, FAISS, etc.)
3. **FULL ARTICLE FEED:** The entire source article must be fed to the LLM on every run, along with all relevant comment context
4. **ARTICLE SELECTION:** System selects ALL relevant articles per comment from available sources and merges them into a single combined context within the prompt size budget (primary article always included in full; secondary articles appended if they fit, otherwise summarised as title + summary; articles that cannot fit are excluded with a log message)
5. **STATELESS OPERATION:** Each run of the bot must be independent and self-contained (except for audit logs)
6. **FILE-BASED STATE:** Use simple JSON files on disk for tracking comments, pending responses, and audit logs

---

## 4. Design Principles

### 4.1 KISS (Keep It Simple, Stupid)

- Use the simplest possible solution for each component
- Prefer plain text files and JSON over complex data structures
- Avoid premature optimization
- Minimize dependencies

### 4.2 DRY (Don't Repeat Yourself)

- Template all prompt generation
- Reuse comment processing logic
- Centralize configuration
- Extract common validation rules

### 4.3 Explicit Over Implicit

- All behavior must be configurable and documented
- No "magic" defaults or hidden logic
- Clear error messages with actionable suggestions

---

## 5. Architecture Overview

### 5.1 High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Instagram Webhook                        │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────┐
│                   Webhook Receiver (FastAPI)                  │
│  - Verify webhook signature                                   │
│  - Extract comment data                                       │
│  - Filter own-account comments (self-reply prevention)        │
│  - Save via CommentExtractor interface                        │
└───────────────┬───────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────┐
│                  Main Processing Script                        │
│  1. Load article from articles/ directory                     │
│  2. Load pending comments via CommentExtractor                │
│  3. Filter own-account comments (defense-in-depth)            │
│  4. For each comment:                                         │
│     - Load full discussion context                            │
│     - Build LLM prompt with article + context                 │
│     - Request response from LLM                               │
│     - Validate response (citations, tone, relevance)          │
│     - Save via AuditLogExtractor interface                    │
│  5. Post approved responses to Instagram                      │
└───────────────┬───────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────┐
│              Modular Storage Architecture                      │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │          Base Classes (base_json_extractor.py)           │ │
│  │  • BaseLocalDiskExtractor - Common disk storage logic    │ │
│  │  • BaseTigrisExtractor - Common S3/Tigris logic          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │          Comment Storage (CommentExtractor)            │   │
│  │  ┌──────────────────┐    ┌──────────────────────┐     │   │
│  │  │ LocalDiskExtractor│    │  TigrisExtractor     │     │   │
│  │  │  (JSON files)    │    │  (S3-compatible)     │     │   │
│  │  └──────────────────┘    └──────────────────────┘     │   │
│  │  Configured via COMMENT_STORAGE_TYPE                   │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │       Audit Log Storage (AuditLogExtractor)            │   │
│  │  ┌──────────────────┐    ┌──────────────────────┐     │   │
│  │  │LocalDiskAudit    │    │  TigrisAudit         │     │   │
│  │  │Extractor         │    │  Extractor           │     │   │
│  │  └──────────────────┘    └──────────────────────┘     │   │
│  │  Configured via AUDIT_LOG_STORAGE_TYPE                 │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │        Auto-Post Mode Storage (ModeExtractor)          │   │
│  │  ┌──────────────────┐    ┌──────────────────────┐     │   │
│  │  │LocalDiskMode     │    │  TigrisMode          │     │   │
│  │  │Extractor         │    │  Extractor           │     │   │
│  │  └──────────────────┘    └──────────────────────┘     │   │
│  │  Configured via MODE_STORAGE_TYPE                      │   │
│  │  Shared by dashboard, processor, and webhook           │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │        Prompt Storage (PromptExtractor)                │   │
│  │  ┌──────────────────┐    ┌──────────────────────┐     │   │
│  │  │LocalDiskPrompt   │    │  TigrisPrompt        │     │   │
│  │  │Extractor         │    │  Extractor           │     │   │
│  │  └──────────────────┘    └──────────────────────┘     │   │
│  │  Configured via PROMPT_STORAGE_TYPE                    │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  All storage systems support:                                  │
│  - local: Uses state/*.json files                             │
│  - tigris: Uses Tigris object storage on Fly.io               │
│                                                                │
│  Other state files (local only):                              │
│  - no_match_log.json (comments that didn't warrant response)  │
│  - posted_ids.txt (simple list of already-responded IDs)      │
└───────────────────────────────────────────────────────────────┘
```

### 5.2 Directory Structure

```
/
├── articles/                               # Numbered articles with §X.Y.Z sections
│   └── arguments-against-the-big-three.md
├── articles_unnumbered/                    # Unnumbered articles without citations
│   └── general-fitness-guidelines.md
├── state/
│   ├── pending_comments.json               # When using local storage
│   ├── audit_log.json                      # When using local storage
│   ├── mode.json                           # When using local mode storage
│   ├── no_match_log.json                   # Always local
│   └── posted_ids.txt                      # Always local
├── src/
│   ├── base_json_extractor.py        # Base classes for extractors
│   ├── comment_extractor.py          # Abstract comment extractor interface
│   ├── comment_extractor_factory.py  # Factory for creating comment extractors
│   ├── local_disk_extractor.py       # Local disk comment implementation
│   ├── tigris_extractor.py           # Tigris/S3 comment implementation
│   ├── audit_log_extractor.py        # Abstract audit log extractor interface
│   ├── audit_log_extractor_factory.py # Factory for creating audit log extractors
│   ├── local_disk_audit_extractor.py # Local disk audit log implementation
│   ├── tigris_audit_extractor.py     # Tigris/S3 audit log implementation
│   ├── token_extractor.py            # Abstract token extractor interface
│   ├── token_extractor_factory.py    # Factory for creating token extractors
│   ├── local_disk_token_extractor.py # Local disk OAuth token implementation
│   ├── tigris_token_extractor.py     # Tigris/S3 OAuth token implementation
│   ├── env_var_token_extractor.py    # Environment variable token implementation
│   ├── mode_extractor.py             # Abstract mode extractor interface
│   ├── mode_extractor_factory.py     # Factory for creating mode extractors
│   ├── local_disk_mode_extractor.py  # Local disk auto-post mode implementation
│   ├── tigris_mode_extractor.py      # Tigris/S3 auto-post mode implementation
│   ├── webhook_receiver.py           # Webhook endpoint
│   ├── processor.py                  # Main processing loop
│   ├── instagram_api.py              # Instagram Graph API wrapper
│   ├── llm_client.py                 # LLM API wrapper
│   ├── validator.py                  # Response validation
│   └── config.py                     # Configuration
├── templates/
│   ├── debate_prompt.txt                   # For numbered articles
│   ├── debate_prompt_unnumbered.txt        # For unnumbered articles
│   └── match_check_prompt.txt              # Relevance check template
├── tests/
│   └── ...
├── .env.example
├── requirements.txt
└── README.md
```

### 5.3 Article Configuration

The processor resolves articles in this priority order:

1. **Article extractor** (`ARTICLE_STORAGE_TYPE`, primary source) — the processor calls `ArticleExtractor.get_articles()` first. Articles managed through the dashboard (local disk or Tigris) are returned here. When this returns one or more articles, `ARTICLES_CONFIG` is ignored entirely.
2. **`ARTICLES_CONFIG`** (fallback) — consulted only when the article extractor returns an empty list. Useful for local development or environments where articles exist as plain markdown files on disk.

`ARTICLES_CONFIG` is a JSON array with article configurations:

```json
[
  {
    "path": "articles/article1.md",
    "link": "https://example.com/article1",
    "is_numbered": true
  },
  {
    "path": "articles_unnumbered/article2.md",
    "link": "https://example.com/article2",
    "is_numbered": false
  }
]
```

- **is_numbered** (optional):
  - When loading from `ARTICLES_CONFIG`: defaults to `true` if omitted.
  - When loading from the article extractor: auto-detected from content (presence of `§` markers).
  - `true` - Article uses numbered sections (§X.Y.Z), responses include citations
  - `false` - Article without numbered sections, responses reference content naturally

> **For Tigris/distributed deployments:** set `ARTICLE_STORAGE_TYPE=tigris` and manage all articles via the dashboard. Leave `ARTICLES_CONFIG` unset — the processor will read articles directly from Tigris and ignore the fallback path.

### 5.4 Storage Configuration

The system supports modular storage backends for both comments and audit logs to enable distributed deployment:

**Base Classes:**
Both storage systems share common functionality through base classes (`base_json_extractor.py`):
- `BaseLocalDiskExtractor` - Provides common local disk JSON storage operations (file paths, load/save)
- `BaseTigrisExtractor` - Provides common S3/Tigris operations (credential handling, S3 client, read/write)

These base classes eliminate code duplication and ensure consistent behavior across storage backends.

**Environment Variables:**

*Comment Storage:*
- `COMMENT_STORAGE_TYPE` - Storage backend type (`local` or `tigris`, default: `local`)

*Audit Log Storage:*
- `AUDIT_LOG_STORAGE_TYPE` - Storage backend type (`local` or `tigris`, default: `local`)

*OAuth Token Storage:*
- `OAUTH_TOKEN_STORAGE_TYPE` - Storage backend type (`local`, `tigris`, or `env_var`, default: `local`)

*Auto-Post Mode Storage:*
- `MODE_STORAGE_TYPE` - Storage backend type (`local` or `tigris`, default: `local`)
  - **Use `tigris`** when the dashboard, processor, and webhook run on separate machines so they all share the same auto-post mode setting

*Prompt Storage:*
- `PROMPT_STORAGE_TYPE` - Storage backend type (`local` or `tigris`, default: `local`)
  - **Use `tigris`** when running distributed deployments so all process groups share the same custom prompt templates

*Self-Reply Prevention:*
- `INSTAGRAM_USERNAME` - (Optional) The bot's own Instagram username, used to discard self-replies. This is automatically read from the stored OAuth token when a user logs in via the dashboard; the env var is only a fallback for deployments that do not use the OAuth login flow. If `OAUTH_TOKEN_STORAGE_TYPE=env_var`, you must set `INSTAGRAM_USERNAME` explicitly because the token data does not include a username.

*Tigris/S3 Configuration (when using Tigris for either storage type):*
- `AWS_ACCESS_KEY_ID` - Tigris access key ID
- `AWS_SECRET_ACCESS_KEY` - Tigris secret access key
- `AWS_ENDPOINT_URL_S3` - S3 endpoint URL (default: https://fly.storage.tigris.dev)
- `TIGRIS_BUCKET_NAME` - Tigris bucket name
- `AWS_REGION` - AWS region (default: auto)

**Storage Backends:**

1. **Local Disk Storage** (`STORAGE_TYPE=local`)
   - Comments: `state/pending_comments.json`
   - Audit Logs: `state/audit_log.json`
   - Mode: `state/mode.json`
   - Prompts: `state/prompts.json`
   - Suitable for single-machine deployments
   - Default option, no additional configuration required

2. **Tigris Object Storage** (`STORAGE_TYPE=tigris`)
   - Comments: `state/pending_comments.json` (in S3 bucket)
   - Audit Logs: `state/audit_log.json` (in S3 bucket)
   - Mode: `state/mode.json` (in S3 bucket)
   - Prompts: `state/prompts.json` (in S3 bucket)
   - Suitable for distributed deployments on Fly.io
   - Allows webhook server, dashboard, and processor to run on different machines
   - Requires Tigris bucket creation: `fly storage create`
   - S3-compatible API using boto3 library

**Storage Implementations:**

*Comment Storage:*
- `LocalDiskExtractor` (extends `BaseLocalDiskExtractor`) - Local JSON file storage
- `TigrisExtractor` (extends `BaseTigrisExtractor`) - S3-compatible object storage
- Factory: `create_comment_extractor()` - Creates appropriate extractor based on `COMMENT_STORAGE_TYPE`

*Audit Log Storage:*
- `LocalDiskAuditExtractor` (extends `BaseLocalDiskExtractor`) - Local JSON file storage
- `TigrisAuditExtractor` (extends `BaseTigrisExtractor`) - S3-compatible object storage
- Factory: `create_audit_log_extractor()` - Creates appropriate extractor based on `AUDIT_LOG_STORAGE_TYPE`

*OAuth Token Storage:*
- `LocalDiskTokenExtractor` (extends `BaseLocalDiskExtractor`) - Local JSON file storage with automatic token refresh
- `TigrisTokenExtractor` (extends `BaseTigrisExtractor`) - S3-compatible object storage with automatic token refresh
- `EnvVarTokenExtractor` - Environment variable storage (read-only, no refresh capability)
- Factory: `create_token_extractor()` - Creates appropriate extractor based on `OAUTH_TOKEN_STORAGE_TYPE`

*Auto-Post Mode Storage:*
- `LocalDiskModeExtractor` (extends `BaseLocalDiskExtractor`) - Stores `state/mode.json` on local disk
- `TigrisModeExtractor` (extends `BaseTigrisExtractor`) - Stores `state/mode.json` in S3-compatible object storage
- Factory: `create_mode_extractor()` - Creates appropriate extractor based on `MODE_STORAGE_TYPE`

*Prompt Storage:*
- `LocalDiskPromptExtractor` (extends `BaseLocalDiskExtractor`) - Stores `state/prompts.json` on local disk
- `TigrisPromptExtractor` (extends `BaseTigrisExtractor`) - Stores `state/prompts.json` in S3-compatible object storage
- Factory: `create_prompt_extractor()` - Creates appropriate extractor based on `PROMPT_STORAGE_TYPE`

**Token Storage Use Cases:**
- **`local` (Default):** Single-machine deployments where OAuth tokens are automatically refreshed and persisted to local disk
- **`tigris`:** Distributed deployments where multiple processes need shared access to refreshable auth tokens
- **`env_var`:** Simple deployments where tokens are managed externally (e.g., CI/CD, secrets management) without automatic refresh

**Use Case:**
When running the bot on Fly.io with separate process groups (webhook, dashboard, scheduler), 
both the webhook server and processor can save/read comments and audit logs to/from Tigris storage, 
enabling true horizontal scaling without shared filesystem. Each component can independently 
configure its storage backends, allowing mixed configurations (e.g., local comments with Tigris audit logs).

Setting `MODE_STORAGE_TYPE=tigris` is strongly recommended for distributed deployments: 
the dashboard writes the auto-post mode to Tigris, and the processor reads it from Tigris 
on every run — no redeploy required to toggle between Auto and Manual modes.

---

## 6. Step-by-Step Processing Pipeline

### 6.1 Webhook Reception (Real-Time)

**Trigger:** Instagram sends a POST request when a new comment is created

1. **Verify Signature:**
   - Extract `X-Hub-Signature-256` header
   - Compute HMAC-SHA256 of request body using `APP_SECRET`
   - Compare computed signature with header value
   - Reject if mismatch

2. **Parse Payload:**
   - Extract: `comment_id`, `post_id`, `comment_text`, `user_id`, `username`, `timestamp`
   - Validate required fields are present

3. **Self-Reply Filter:**
   - Read the bot's own username from the stored OAuth token (via `TokenExtractor.get_token()`)
   - Compare comment `username` against bot's own username (case-insensitive)
   - If match → silently discard and do not save to pending queue
   - Falls back to `INSTAGRAM_USERNAME` env var if no OAuth token is available

4. **Check Duplicates:**
   - Read `posted_ids.txt`
   - If `comment_id` exists, ignore (already processed)

5. **Save to Pending:**
   - Save comment data via CommentExtractor interface
   - Format: `{"comment_id": "...", "post_id": "...", "text": "...", "user": "...", "timestamp": "..."}`
   - Storage location depends on configured backend (local or Tigris)

5. **Respond 200 OK:**
   - Immediately return success to Instagram (required within 5 seconds)

### 6.2 Main Processing Loop (Batch/Scheduled)

**Trigger:** Cron job every 5 minutes, or manual invocation

1. **Load Articles:**
   - Read Markdown articles from `articles/` directory
   - Parse each to extract numbered sections (§1.1, §1.1.1, etc.)
   - Store all articles in memory for this run

2. **Load Pending Comments:**
   - Load comments via CommentExtractor interface
   - Filter out any comments whose `username` matches the bot's own account (defense-in-depth self-reply guard)
   - If empty after filtering, exit gracefully
   - Otherwise, process each comment sequentially

3. **For Each Comment:**

   **3.1 Fetch Thread Context:**
   - Use Instagram Graph API to fetch:
     - Original post caption/text
     - Parent comment (if this is a reply)
     - All sequential comments in the thread
     - Previous bot responses in the same thread (if any)
   - Build conversation context string

   **3.2 Article Selection (LLM Call):**
   - For each available article, check relevance
   - Prompt LLM: "Is this content (post + comment + context) relevant to [article topic]?"
   - Collect **all** articles that return YES
   - If NO articles match → Log to `no_match_log.json`, continue to next comment
   - If one or more articles match → Proceed to response generation

   **3.3 Generate Response:**
   - Build combined article context from all matching articles:
     - Primary (first) article always included in full (truncated at paragraph boundary if it alone exceeds `max_chars`)
     - Each additional article appended with a separator if it fits within `max_chars`; otherwise only its title + summary is appended as a brief reference; if even the brief reference exceeds the budget the article is excluded with a log message
   - Build prompt using template (see §8)
   - Include: Combined article context, comment text, thread context
   - Call LLM API via OpenRouter
   - Parse response

   **3.4 Validate Response:**
   - Check all citations exist in article (e.g., "§1.1.1" is a valid section)
   - Verify no hallucinated facts
   - Check character length (Instagram limit: 2,200 chars)
   - Ensure respectful tone (no profanity, insults)
   - If validation fails → Log error, mark comment as failed

   **3.6 Store Result:**
   - Save via AuditLogExtractor interface with full metadata:
     ```json
     {
       "comment_id": "...",
       "comment_text": "...",
       "generated_response": "...",
       "citations_used": ["§1.1.1", "§2.3"],
       "article_used": {
         "path": "articles/article1.md",
         "link": "https://example.com/article1",
         "title": "Article Title"
       },
       "token_count": 450,
       "timestamp": "...",
       "status": "approved" | "rejected" | "pending_review"
     }
     ```

4. **Post Responses:**
   - Read current mode via `ModeExtractor.get_auto_mode()` (shared via Tigris in distributed deployments)
   - If auto-post enabled:
     - For each approved response, call Instagram API to post comment
     - Add `comment_id` to `posted_ids.txt`
   - If manual review mode:
     - Wait for human approval (external process/dashboard)

5. **Cleanup:**
   - Clear processed comments via CommentExtractor interface
   - This removes comments from storage (local file or Tigris)
   - Rotate logs if they exceed size limit

### 6.3 Human Review Workflow (Optional)

1. Dashboard displays audit_log entries with `status: "pending_review"`
2. Human reviews generated response
3. Human approves or rejects
4. If approved → Post to Instagram, update status
5. If rejected → Log reason, mark as rejected

---

## 7. Webhook Verification & Subscription

### 7.1 Initial Setup (One-Time)

Instagram requires a verification step before sending webhooks:

1. **Create Webhook Endpoint:**
   - URL: `https://yourdomain.com/webhook/instagram`
   - Must be publicly accessible and use HTTPS

2. **Implement Verification Handler:**
   
   When you configure webhooks in the App Dashboard, Instagram sends a GET request to verify your endpoint. The request includes these query parameters:
   
   - `hub.mode` - Will be "subscribe"
   - `hub.verify_token` - The verify token you configured in the dashboard
   - `hub.challenge` - A random string to echo back
   
   **Sample Verification Request:**
   ```
   GET https://yourdomain.com/webhook/instagram?
     hub.mode=subscribe&
     hub.challenge=1158201444&
     hub.verify_token=meatyhamhock
   ```
   
   **Verification Handler Implementation:**
   ```python
   @app.get("/webhook/instagram")
   def verify_webhook(request):
       mode = request.args.get('hub.mode')
       token = request.args.get('hub.verify_token')
       challenge = request.args.get('hub.challenge')
       
       # Verify the mode and token
       if mode == 'subscribe' and token == VERIFY_TOKEN:
           # Return the challenge value to complete verification
           return challenge, 200
       else:
           return "Forbidden", 403
   ```

3. **Configure in Meta Developer Console:**
   - Go to App Dashboard → Products → Webhooks
   - Subscribe to `comments` field for your Instagram account
   - Provide callback URL and verify token
   - Instagram will send GET request to verify
   - Your endpoint must return the `hub.challenge` value to complete verification

### 7.2 Ongoing Webhook Reception

After verification, Instagram sends POST requests for new comments:

```python
@app.post("/webhook/instagram")
def receive_webhook(request):
    # 1. Verify signature (see §6.1)
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.body, signature, APP_SECRET):
        return "Invalid signature", 403
    
    # 2. Parse payload
    data = request.json()
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            if change['field'] == 'comments':
                process_comment(change['value'])
    
    return "OK", 200
```

### 7.3 Subscription Management

- Use Instagram Graph API to manage subscriptions programmatically:
  ```
  POST /{app-id}/subscriptions
  ?object=instagram
  &callback_url={url}
  &fields=comments
  &verify_token={token}
  &access_token={app-token}
  ```

### 7.4 Replying to Comments

**Creating Replies:**

To post a reply to a comment, use the Instagram Graph API:

```
POST /{ig-comment-id}/replies?message={message}
```

This creates an IG Comment as a reply to an existing IG Comment.

**Query String Parameters:**
- `{message}` (required) — The text to be included in the reply

**Limitations:**
- You can only reply to top-level comments; replies to a reply will be added to the top-level comment
- You cannot reply to hidden comments
- You cannot reply to comments on a live video (use Instagram Messaging API for private replies instead)

**Required Permissions:**

A User access token from the User who created the comment, with:
- `instagram_basic`
- `instagram_manage_comments`
- `pages_show_list`
- `page_read_engagement`

If the token is from a User whose Page role was granted via Business Manager, also required:
- `ads_management` OR `ads_read`

**Sample Request:**
```
POST graph.facebook.com/17870913679156914/replies?message=Research shows...
```

**Sample Response:**
```json
{
  "id": "17873440459141021"
}
```

**Reading Replies:**

To get a list of replies on a comment:

```
GET /{ig-comment-id}/replies
```

Returns a list of IG Comments (replies) on an IG Comment.

---

## 8. Prompt Templates

### 8.1 Main Debate Response Prompt

**File:** `templates/debate_prompt.txt`

```
You are a debate assistant bot for an Instagram account focused on {{TOPIC}}.

Your task is to generate a polite, evidence-based response to the following Instagram comment.

RULES:
1. ONLY use arguments and evidence from the provided article below
2. Cite specific sections using the §X.Y.Z format (e.g., "§1.1.1")
3. Be conversational and respectful, not academic or robotic
4. If the comment agrees with the article, acknowledge it briefly
5. If the comment disagrees, present counter-evidence from the article
6. Keep response under 2,000 characters
7. Do NOT invent facts or citations not in the article
8. End with a question to encourage further discussion

ARTICLE:
{{FULL_ARTICLE_TEXT}}

---

INSTAGRAM POST CAPTION:
{{POST_CAPTION}}

COMMENT TO RESPOND TO:
User: {{USERNAME}}
Text: {{COMMENT_TEXT}}

{{#if THREAD_CONTEXT}}
PREVIOUS DISCUSSION IN THIS THREAD:
{{THREAD_CONTEXT}}
{{/if}}

---

Generate your response below. Be direct and concise - no greetings, acknowledgments, or filler words. Present counter-arguments with citations immediately. Keep responses short and to the point, even if it sounds snippy.

RESPONSE:
```

### 8.2 Post Topic Check Prompt

**File:** `templates/post_topic_check_prompt.txt`

```
You are a filter bot determining if an Instagram post is about the same topic as a specific article.

ARTICLE TOPIC:
{{ARTICLE_TITLE}}

ARTICLE SUMMARY:
{{ARTICLE_FIRST_PARAGRAPH}}

INSTAGRAM POST CAPTION:
"{{POST_CAPTION}}"

QUESTION:
Is this Instagram post about the same topic as this article? Consider the main subject matter, not just tangential mentions.

Answer ONLY with "YES" or "NO", followed by a one-sentence explanation.

ANSWER:
```

### 8.3 Comment Relevance Check Prompt

**File:** `templates/comment_relevance_check_prompt.txt`

```
You are a filter bot determining if an Instagram comment is relevant to a specific article.

ARTICLE TOPIC:
{{ARTICLE_TITLE}}

ARTICLE SUMMARY:
{{ARTICLE_FIRST_PARAGRAPH}}

COMMENT:
"{{COMMENT_TEXT}}"

QUESTION:
Does this comment present a claim, question, or viewpoint that can be meaningfully addressed using arguments from this article?

Answer ONLY with "YES" or "NO", followed by a one-sentence explanation.

ANSWER:
```

### 8.4 Response Format

All LLM responses should follow this structure:

```
@{{USERNAME}} Research shows that {{CLAIM}}. According to §1.1.1, {{EVIDENCE}}.

The data in §2.3 indicates {{EVIDENCE}}.

---
🤖 This is an automated response. Full article: {{ARTICLE_LINK}}
```

---

## 9. JSON Schemas

### 9.1 `pending_comments.json`

Stores comments awaiting processing.

```json
{
  "version": "1.0",
  "comments": [
    {
      "comment_id": "18123456789",
      "post_id": "17987654321",
      "username": "fitness_enthusiast",
      "user_id": "12345",
      "text": "But everyone says squats are the king of exercises!",
      "timestamp": "2026-01-31T04:15:00Z",
      "received_at": "2026-01-31T04:15:05Z"
    }
  ]
}
```

**Schema:**
- `version` (string): Schema version for future compatibility
- `comments` (array): List of comment objects
  - `comment_id` (string, required): Instagram comment ID
  - `post_id` (string, required): Instagram post ID
  - `username` (string, required): Commenter's username
  - `user_id` (string, required): Commenter's user ID
  - `text` (string, required): Comment text content
  - `timestamp` (string, required): When comment was created (ISO 8601)
  - `received_at` (string, required): When webhook was received (ISO 8601)

### 9.2 Audit Log Storage

Stores all generated responses with metadata. Can be stored locally or in Tigris object storage based on `AUDIT_LOG_STORAGE_TYPE` configuration.

**Storage Backends:**
- **Local**: `state/audit_log.json`
- **Tigris**: `state/audit_log.json` (in S3 bucket)

**Format:**
```json
{
  "version": "1.0",
  "entries": [
    {
      "id": "log_001",
      "comment_id": "18123456789",
      "post_id": "17987654321",
      "username": "fitness_enthusiast",
      "comment_text": "But everyone says squats are the king of exercises!",
      "generated_response": "@fitness_enthusiast I hear you – squats are often...",
      "citations_used": ["§1.1.1", "§1.2.1", "§1.3.1"],
      "token_count_in": 3500,
      "token_count_out": 450,
      "model": "gpt-4-turbo",
      "status": "approved",
      "posted": true,
      "posted_at": "2026-01-31T04:20:00Z",
      "reviewed_by": "human_operator_1",
      "timestamp": "2026-01-31T04:18:00Z",
      "validation_passed": true,
      "validation_errors": []
    }
  ]
}
```

**Access:**
- Saved via `AuditLogExtractor.save_entry(entry)`
- Loaded via `AuditLogExtractor.load_entries()`
- Updated via `AuditLogExtractor.update_entry(entry_id, updates)`

**Schema:**
- `version` (string): Schema version
- `entries` (array): List of log entries
  - `id` (string, required): Unique log entry ID
  - `comment_id` (string, required): Instagram comment ID
  - `post_id` (string, required): Instagram post ID
  - `username` (string, required): Commenter username
  - `comment_text` (string, required): Original comment
  - `generated_response` (string, required): Bot's generated response
  - `citations_used` (array of strings): Section references used (e.g., ["§1.1.1"])
  - `token_count_in` (integer): Input tokens to LLM
  - `token_count_out` (integer): Output tokens from LLM
  - `model` (string): LLM model identifier
  - `status` (enum): `"approved"`, `"rejected"`, `"pending_review"`
  - `posted` (boolean): Whether response was posted to Instagram
  - `posted_at` (string, nullable): When posted (ISO 8601)
  - `reviewed_by` (string, nullable): Human reviewer ID (if manual review)
  - `timestamp` (string, required): When log entry was created (ISO 8601)
  - `validation_passed` (boolean): Whether validation checks passed
  - `validation_errors` (array of strings): List of validation error messages

### 9.3 `no_match_log.json`

Stores comments deemed irrelevant or unmatchable.

```json
{
  "version": "1.0",
  "entries": [
    {
      "id": "nomatch_001",
      "comment_id": "18987654321",
      "post_id": "17987654321",
      "username": "random_user",
      "comment_text": "Nice photo!",
      "reason": "Generic praise, no debatable claim",
      "relevance_score": 0.1,
      "timestamp": "2026-01-31T04:16:00Z"
    }
  ]
}
```

**Schema:**
- `version` (string): Schema version
- `entries` (array): List of no-match entries
  - `id` (string, required): Unique entry ID
  - `comment_id` (string, required): Instagram comment ID
  - `post_id` (string, required): Instagram post ID
  - `username` (string, required): Commenter username
  - `comment_text` (string, required): Original comment
  - `reason` (string, required): Human-readable reason for not responding
  - `relevance_score` (float, optional): Numeric relevance score (0.0-1.0)
  - `timestamp` (string, required): When assessed (ISO 8601)

### 9.4 `mode.json`

Stores the auto-post mode setting. Used by the dashboard (write) and processor (read).

**Storage Backends:**
- **Local**: `state/mode.json`
- **Tigris**: `state/mode.json` (in S3 bucket) — use for distributed deployments

**Format:**
```json
{
  "auto_mode": false
}
```

**Schema:**
- `auto_mode` (boolean, required): `true` = auto-post enabled, `false` = manual review required

**Access:**
- Read via `ModeExtractor.get_auto_mode()` — returns `false` when file/object does not exist
- Written via `ModeExtractor.set_auto_mode(value)`
- `Config.auto_post_enabled` delegates to the mode extractor factory for all components

### 9.5 `articles.json`

Stores articles managed via the Article Manager dashboard. Used by the dashboard for CRUD operations.

**Storage Backends:**
- **Local**: `state/articles.json`
- **Tigris**: `state/articles.json` (in S3 bucket) — use for distributed deployments; configure via `ARTICLE_STORAGE_TYPE=tigris`

**Format:**
```json
{
  "articles": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Arguments Against the Big Three",
      "content": "# Arguments Against the Big Three\n\n...",
      "link": "https://example.com/article"
    }
  ]
}
```

**Schema:**
- `articles` (array, required): List of article objects
  - `id` (string, required): UUID assigned at creation time
  - `title` (string, required): Human-readable article title
  - `content` (string, required): Full article text in Markdown format
  - `link` (string): URL to the published article (may be empty)

**Access:**
- Read via `ArticleExtractor.get_articles()` / `ArticleExtractor.get_article(id)`
- Written via `ArticleExtractor.save_article(id, title, content, link)`
- Deleted via `ArticleExtractor.delete_article(id)` — returns `False` if ID not found
- Factory: `create_article_extractor()` selects backend based on `ARTICLE_STORAGE_TYPE` env var

### 9.6 `prompts.json`

Stores custom prompt templates managed via the Prompt Editor dashboard. Used by the dashboard for editing prompts.

**Storage Backends:**
- **Local**: `state/prompts.json`
- **Tigris**: `state/prompts.json` (in S3 bucket) — use for distributed deployments; configure via `PROMPT_STORAGE_TYPE=tigris`

**Format:**
```json
{
  "prompts": {
    "debate_prompt": "You are a debate assistant bot for an Instagram account...",
    "relevance_prompt": "Is this comment relevant to the article?"
  }
}
```

**Schema:**
- `prompts` (object, required): Mapping of prompt name to prompt content string

**Access:**
- Read via `PromptExtractor.get_prompt(name)` — returns empty string when not found
- Read all via `PromptExtractor.get_all_prompts()` — returns `{}` when no prompts stored
- Written via `PromptExtractor.set_prompt(name, content)`
- Factory: `create_prompt_extractor()` selects backend based on `PROMPT_STORAGE_TYPE` env var

---

## 10. Token Limit & Truncation Policy

### 10.1 Input Token Budget

**Target:** Keep total input under 100,000 tokens per request (for GPT-4 Turbo)

**Allocation:**
- **Article:** ~30,000 tokens (priority: keep full article)
- **System Prompt + Instructions:** ~2,000 tokens
- **Comment + Thread Context:** ~5,000 tokens
- **Buffer:** ~63,000 tokens remaining

---

## 11. Post-Generation Validation Rules

All generated responses must pass these checks before being saved or posted:

### 11.1 Citation Validation

- **Scope:** Applies only to numbered articles (is_numbered: true)
- **Rule:** Every citation (e.g., "§1.1.1") must exist in the source article
- **Check:** Regex match all `§\d+(\.\d+)*` patterns, verify against article structure
- **Failure:** If invalid citation found, reject response and log error
- **Unnumbered Articles:** Citation validation is skipped for articles marked as is_numbered: false

### 11.2 Hallucination Detection

- **Rule:** No facts or studies can be mentioned unless explicitly in article
- **Check:** 
  - Extract all claims from response
  - Verify each claim appears in article text
  - Use fuzzy matching for paraphrased content
- **Failure:** If novel claim detected, reject and flag for review

### 11.3 Length Validation

- **Rule:** Response must fit within Instagram's character limit (2,200 characters)
- **Check:** Attempt to post the comment to Instagram. If Instagram API returns an error indicating the comment is too long, loop the response back to the LLM with instruction to shorten it
- **Failure:** If too short (<200 characters), regenerate with "expand" instruction

---

## 12. Dashboard & Human Workflows

### 12.1 Review Dashboard

**Purpose:** Allow humans to review, approve, or reject generated responses.

**Features:**
- Display pending responses (status: "pending_review")
- Show:
  - Original comment
  - Generated response
  - Citations used
  - Validation status
- Actions:
  - Approve (posts to Instagram)
  - Reject (logs reason, doesn't post)
  - Edit (modify response, then approve)
- **Auto-post mode toggle** — switch between Auto and Manual modes at runtime without a redeploy

**Auto-Post Mode API:**
- `GET /api/mode` — returns `{"auto_mode": bool}`
- `POST /api/mode` — sets the mode; body: `{"auto_mode": true|false}`, validates boolean type (400 on invalid input)
- Reads/writes via `ModeExtractor`; set `MODE_STORAGE_TYPE=tigris` so the processor on a separate machine picks up the change immediately

### 12.2 Article Manager

**Purpose:** Allow humans to create, edit, and delete articles from the dashboard without manual file system access.

**Features:**
- List all managed articles (title + link displayed inline)
- Add a new article (title, content in Markdown, optional link)
- Edit an existing article in-place
- Delete an article with confirmation

**Article Manager API:**
- `GET /api/articles` — returns `{"articles": [{id, title, content, link}]}`
- `POST /api/articles` — creates article with auto-generated UUID; body: `{"title": "...", "content": "...", "link": "..."}` (title and content required, 400 on missing); returns `{"status": "ok", "article_id": "..."}`
- `PUT /api/articles/{id}` — updates an existing article; body: same as POST (404 if not found)
- `DELETE /api/articles/{id}` — deletes an article (404 if not found); returns `{"status": "ok", "article_id": "..."}`

**Storage:**
- Backed by `ArticleExtractor` — set `ARTICLE_STORAGE_TYPE=tigris` for distributed deployments so all process groups (dashboard, processor) share the same article data
- The processor always consults the article extractor **first**; `ARTICLES_CONFIG` is only used as a fallback when the extractor returns no articles

**Tech Stack:** Simple web UI (FastAPI + inline JavaScript)

### 12.3 Prompt Editor

**Purpose:** Allow humans to view and edit prompt templates from the dashboard without direct filesystem access.

**Features:**
- List all stored custom prompts
- Edit any prompt template (name + content) with a multi-line text editor
- Changes take effect immediately on the next processor run (no redeploy required)

**Prompt Editor API:**
- `GET /api/prompts` — returns all stored prompts as `{"prompts": {name: content}}`
- `GET /api/prompts/{name}` — returns a single prompt by name: `{"name": ..., "content": ...}` (content is empty string if not stored)
- `PUT /api/prompts/{name}` — creates or updates a prompt; body: `{"content": "..."}` (400 if content field missing); returns `{"status": "ok", "name": "..."}`

**Storage:**
- Backed by `PromptExtractor` — set `PROMPT_STORAGE_TYPE=tigris` for distributed deployments so all process groups share the same prompts

**Tech Stack:** Simple web UI (FastAPI + inline JavaScript)

### 12.4 Manual Workflows

**Daily Review (Recommended):**
1. Check `audit_log.json` for rejected responses
2. Review `no_match_log.json` to adjust relevance thresholds
3. Monitor token usage and costs
4. Read sample of posted responses for quality

**Weekly Review:**
1. Analyze response patterns (which citations used most)
2. Update article if common counter-arguments arise
3. Refine prompt templates based on tone/style feedback

**Monthly Review:**
1. Evaluate bot effectiveness (engagement metrics on Instagram)
2. All relevant articles are now considered per comment (multi-article context merging implemented)
3. Update validation rules based on edge cases

---

## 13. Implementation Details for LLM Integration

### 13.1 Technology Stack

**LLM Framework:**
- **OpenRouter SDK:** Use the OpenRouter SDK directly for LLM interactions and prompt management
- Provides simple API interface without additional abstraction layers
- Direct integration with multiple LLM providers through a unified API

**LLM Provider:**
- **Primary Model:** Gemini Flash 2.0 (via OpenRouter)
- Cost-effective option suitable for high-volume comment processing
- Good balance of quality and speed for debate responses
- OpenRouter provides unified API access and potential fallback options

**API Configuration:**
```python
# Example configuration
from openrouter import OpenRouter

client = OpenRouter(
    api_key=os.getenv("OPENROUTER_API_KEY")
)

MODEL_NAME = "google/gemini-flash-2.0"
MAX_TOKENS = 2000
TEMPERATURE = 0.7  # Balanced creativity for debate responses
```

### 13.2 OpenRouter SDK Integration

**Setup:**
```python
from openrouter import OpenRouter
import os

# Initialize OpenRouter client
client = OpenRouter(
    api_key=os.getenv("OPENROUTER_API_KEY")
)

def generate_response(prompt: str, max_tokens: int = 2000) -> str:
    """Generate LLM response using OpenRouter."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a debate assistant bot."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=TEMPERATURE
    )
    return response.choices[0].message.content
```

**Prompt Template Usage:**
- Load prompt templates from `templates/` directory as plain text files
- Perform string substitution for variables ({{VARIABLE}})
- Support for multi-turn conversations by building message arrays

**Processing Architecture:**
1. **Post Topic Check:** Verify post caption matches article topic before processing comments
2. **Relevance Check:** Lightweight filter to determine if comment is debatable and which articles are relevant
3. **Context Merging:** Build combined article context from all relevant articles within the prompt size budget (`build_combined_article_context`)
4. **Response Generation:** Main debate response using the combined article context
5. **Validation:** Verify citations (against the primary article) and check for hallucinations

---

## 14. Unit Testing & API Testing

### 14.1 Test-Driven Development Process

Follow this TDD workflow for all development:

1. **Create Method Signatures:** Define all function signatures with type hints but no implementation
2. **Write Tests First:** Create unit tests and API tests with mocks and stubs
3. **Run Tests (Expect Failures):** Execute tests to verify they fail without implementation
4. **Implement Functions:** Write actual implementation guided by test requirements
5. **Iterate:** Use test feedback to refine implementation until all tests pass

### 14.2 Testing Framework

**Unit Testing:**
- **Framework:** PyTest
- **Purpose:** Test individual functions and methods in isolation
- **Coverage Target:** Aim for high coverage of business logic

**API Testing:**
- **Framework:** PyTest with `requests-mock`
- **Purpose:** Test API interactions with mocked HTTP responses
- **Mock:** Instagram Graph API and OpenRouter API responses

### 14.3 Webhook Testing

**Test Instagram Webhooks:**
- Write tests that POST fake webhook payloads directly to your webhook endpoint
- Mock Instagram's webhook signature verification
- Test various webhook scenarios (new comment, reply, edge cases)

**Test Webhook Verification:**
- Create unit tests for the webhook verification endpoint (GET request handler)
- Mock the verification challenge flow with `hub.mode`, `hub.verify_token`, and `hub.challenge` parameters
- Verify that the endpoint correctly returns the challenge value when verification succeeds
- Test failure scenarios (incorrect token, missing parameters)

**Test Comment Reply Creation:**
- Write unit tests for functions that create replies to Instagram comments
- Mock the Instagram Graph API POST request to `/{ig-comment-id}/replies`
- Test successful reply creation and verify the response contains the comment ID
- Test error handling (API failures, rate limits, permission errors)
- Verify proper handling of reply limitations (top-level only, no hidden comments)

**Example Webhook Test Payload:**

```python
# Test payload for Instagram comment webhook
webhook_payload = {
    "object": "instagram",
    "entry": [
        {
            "id": "instagram-business-account-id",
            "time": 1704067200,
            "changes": [
                {
                    "value": {
                        "from": {
                            "id": "user-id",
                            "username": "test_user"
                        },
                        "media": {
                            "id": "media-id",
                            "media_product_type": "FEED"
                        },
                        "id": "comment-id",
                        "text": "This is a test comment"
                    },
                    "field": "comments"
                }
            ]
        }
    ]
}
```

### 14.4 Instagram API Response Formats

**Comment Object Structure:**
```json
{
  "id": "comment-id",
  "text": "Comment text here",
  "timestamp": "2024-01-01T12:00:00+0000",
  "from": {
    "id": "user-id",
    "username": "username"
  },
  "media": {
    "id": "media-id"
  }
}
```

### 14.5 Test Organization

**Directory Structure:**
```
tests/
├── unit/
│   ├── test_article_parser.py
│   ├── test_prompt_builder.py
│   ├── test_validator.py
│   └── test_state_manager.py
├── api/
│   ├── test_instagram_api.py
│   ├── test_openrouter_api.py
│   └── test_webhook_receiver.py
├── integration/
│   └── test_full_pipeline.py
└── fixtures/
    ├── sample_article.md
    ├── webhook_payloads.json
    └── api_responses.json
```

### 14.6 Key Testing Principles

1. **Mock External APIs:** Never make real API calls in tests
2. **Mock OpenRouter SDK:** Mock out the OpenRouter SDK objects (e.g., `OpenRouter` client) in tests so that you only test your own logic, not the SDK itself
3. **Test Edge Cases:** Empty responses, rate limits, malformed data
4. **Isolation:** Each test should be independent and not rely on others
5. **Descriptive Names:** Test function names should clearly indicate what they test

---

## 15. References & Resources

**Instagram Platform Documentation:**
- Webhooks: https://developers.facebook.com/docs/graph-api/webhooks/
- Comments API: https://developers.facebook.com/docs/instagram-api/guides/comments/
- Getting Started: https://developers.facebook.com/docs/instagram-api/getting-started/

**LLM APIs:**
- OpenAI: https://platform.openai.com/docs/
- Anthropic Claude: https://docs.anthropic.com/
- OpenRouter: https://openrouter.ai/docs
- Google Gemini: https://ai.google.dev/docs

**Python Libraries:**
- FastAPI: https://fastapi.tiangolo.com/
- Requests: https://docs.python-requests.org/
- Python-dotenv: https://pypi.org/project/python-dotenv/
- PyTest: https://docs.pytest.org/
- requests-mock: https://requests-mock.readthedocs.io/

**Best Practices:**
- Instagram Platform Terms: https://developers.facebook.com/terms/
- GDPR Compliance: https://gdpr.eu/
- Bot Disclosure Guidelines: https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers

---

**END OF RFC**

This document provides a complete, implementable specification for the Instagram Debate-Bot. All design decisions are justified, all edge cases are addressed, and the architecture is defined. This RFC is suitable for handoff to a code-generating LLM or a development team for implementation.
