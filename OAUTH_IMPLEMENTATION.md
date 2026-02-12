# Instagram Business Login OAuth Implementation

## Overview

This implementation adds Instagram Business Login using OAuth 2.0 to the Instagram Debate Bot dashboard. Users can now authenticate through Instagram to obtain long-lived access tokens (60-day validity) that are automatically refreshed.

## Implementation Summary

### 1. OAuth Configuration (`src/config.py`)
Added three new configuration properties:
- `instagram_client_id`: Facebook App ID
- `instagram_client_secret`: Facebook App Secret  
- `instagram_redirect_uri`: OAuth callback URL (default: http://127.0.0.1:5000/auth/instagram/callback)

### 2. Token Manager (`src/token_manager.py`)
Created a comprehensive token management module with:
- **Token Storage**: Saves tokens to `state/instagram_token.json` with metadata
- **Token Retrieval**: Loads stored tokens with validation
- **Expiration Checking**: Checks if tokens will expire within a buffer period (default: 5 days)
- **Token Refresh**: Automatically refreshes tokens via Instagram Graph API
- **Token Clearing**: Removes tokens during logout

### 3. OAuth Endpoints (`dashboard.py`)
Implemented three OAuth endpoints:

#### `/auth/instagram/login`
- Generates secure CSRF state token
- Redirects user to Instagram OAuth authorization page
- Requests required scopes: `instagram_basic`, `instagram_manage_comments`, `pages_show_list`

#### `/auth/instagram/callback`
- Validates CSRF state parameter
- Exchanges authorization code for short-lived token
- Exchanges short-lived token for long-lived token (60 days)
- Stores token with user metadata
- Redirects to dashboard

#### `/auth/instagram/logout`
- Clears stored access token
- Redirects to dashboard

### 4. Dashboard UI Updates (`dashboard.py`)
Enhanced the dashboard header to show authentication status:

**Not Authenticated:**
- Yellow warning badge: "⚠ Not Authenticated"
- Blue "Login with Instagram" button

**Authenticated:**
- Green success badge: "✓ Authenticated"
- Username and User ID display
- Gray "Logout" button

### 5. Security Features
- **CSRF Protection**: State parameter validates OAuth callback
- **Token Security**: Tokens stored server-side only (not in client JS)
- **Automatic Refresh**: Tokens refresh 5 days before expiration
- **Secure Storage**: Tokens stored in gitignored `state/` directory

## Testing

### Unit Tests (29 new tests)
1. **Config Tests** (6 tests): OAuth configuration properties
2. **Token Manager Tests** (16 tests): All token operations
3. **OAuth Helper Tests** (7 tests): OAuth flow validation

**Total Test Coverage**: 51 tests pass (100% success rate)

### Manual Testing
- Dashboard displays correctly in both authenticated and non-authenticated states
- Login flow redirects to Instagram (manual OAuth requires actual credentials)
- Logout functionality clears tokens and updates UI
- UI properly shows user information when authenticated

## OAuth Flow

```
1. User clicks "Login with Instagram"
   ↓
2. Redirect to Instagram OAuth (with state parameter)
   ↓
3. User authorizes app on Instagram
   ↓
4. Instagram redirects to callback with code
   ↓
5. Validate state (CSRF protection)
   ↓
6. Exchange code for short-lived token
   ↓
7. Exchange short-lived for long-lived token (60 days)
   ↓
8. Save token to state/instagram_token.json
   ↓
9. Redirect to dashboard (now authenticated)
```

## Token Refresh Strategy

- Long-lived tokens valid for 60 days
- Automatic check on dashboard load
- Token refresh triggers when < 5 days until expiration
- Refresh extends validity for another 60 days
- Failed refresh prompts user to re-authenticate

## How the Long-Lived Token is Used in the Codebase

After successful OAuth authentication, the long-lived access token is stored in `state/instagram_token.json` and used throughout the application for Instagram API operations.

### Token Storage Location

```
state/instagram_token.json
```

**File Structure:**
```json
{
  "access_token": "long_lived_token_abc123...",
  "token_type": "bearer",
  "expires_at": "2026-04-13T01:30:00Z",
  "saved_at": "2026-02-12T01:30:00Z",
  "user_id": "123456789",
  "username": "testuser"
}
```

### Token Retrieval Flow

The token is accessed through two main paths:

#### 1. Environment Variable (Legacy Method)

**Location:** `src/config.py:38-40`

```python
@property
def instagram_access_token(self) -> str:
    """Get Instagram access token."""
    return os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
```

This property reads from the `INSTAGRAM_ACCESS_TOKEN` environment variable, which can be:
- Manually set in `.env` file (legacy approach)
- OR retrieved from the OAuth token storage (future enhancement)

#### 2. Token Manager (OAuth Method)

**Location:** `src/token_manager.py`

```python
from src.token_manager import TokenManager

manager = TokenManager(state_dir="state")
token_data = manager.get_token()
access_token = token_data["access_token"]
```

### Where the Token is Used for Comment Management

#### Main Entry Point: `main.py`

**Location:** `main.py:19-22`

```python
instagram_api = InstagramAPI(
    access_token=config.instagram_access_token,  # ← Token used here
    app_secret=config.instagram_app_secret
)
```

The `InstagramAPI` class is initialized with the access token, which is then used for ALL Instagram Graph API operations.

#### Comment Retrieval Operations

**Location:** `src/instagram_api.py`

The access token is used in these API operations:

1. **Get Comment Details** (`get_comment()` - Line 61-79)
   ```python
   url = f"{self.BASE_URL}/{comment_id}"
   params = {
       "access_token": self.access_token,  # ← Token used here
       "fields": "id,text,timestamp,from,media"
   }
   response = requests.get(url, params=params, timeout=30)
   ```

2. **Get Comment Replies** (`get_comment_replies()` - Line 81-99)
   ```python
   url = f"{self.BASE_URL}/{comment_id}/replies"
   params = {
       "access_token": self.access_token,  # ← Token used here
   }
   response = requests.get(url, params=params, timeout=30)
   ```

3. **Get Post Caption** (`get_post_caption()` - Line 101-120)
   ```python
   url = f"{self.BASE_URL}/{post_id}"
   params = {
       "access_token": self.access_token,  # ← Token used here
       "fields": "caption"
   }
   response = requests.get(url, params=params, timeout=30)
   ```

4. **Post Reply to Comment** (`post_reply()` - Line 122-141)
   ```python
   url = f"{self.BASE_URL}/{comment_id}/replies"
   params = {
       "access_token": self.access_token,  # ← Token used here
       "message": message
   }
   response = requests.post(url, params=params, timeout=30)
   ```

#### Comment Processing Flow

**Location:** `src/processor.py`

The processor uses the `InstagramAPI` instance (with the token) to:

1. **Fetch Post Caption** (Line 167)
   ```python
   post_caption = self.instagram_api.get_post_caption(comment["post_id"])
   ```

2. **Build Thread Context** (Line 338)
   ```python
   replies = self.instagram_api.get_comment_replies(comment_id)
   ```

3. **Post Approved Responses** (Line 431-434)
   ```python
   _result = self.instagram_api.post_reply(
       entry["comment_id"],
       entry["generated_response"]
   )
   ```

### Complete Usage Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User authenticates via OAuth                             │
│    (dashboard.py: /auth/instagram/callback)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Long-lived token stored in state/instagram_token.json   │
│    (token_manager.py: save_token())                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Bot main process starts (main.py)                        │
│    - Reads config.instagram_access_token                    │
│    - Currently from INSTAGRAM_ACCESS_TOKEN env var          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. InstagramAPI initialized with token                      │
│    (main.py: InstagramAPI(access_token=...))                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Token used for all Instagram API operations:             │
│    • Fetch comments (get_comment)                           │
│    • Get comment replies (get_comment_replies)              │
│    • Get post captions (get_post_caption)                   │
│    • Post replies (post_reply)                              │
└─────────────────────────────────────────────────────────────┘
```

### Current State vs. Future Enhancement

**Current Implementation:**
- OAuth flow stores token in `state/instagram_token.json`
- Dashboard uses token to display auth status
- **Main bot process still reads from `INSTAGRAM_ACCESS_TOKEN` environment variable**
- User must manually sync OAuth token to environment variable

**Recommended Future Enhancement:**

Modify `src/config.py` to prioritize OAuth token:

```python
@property
def instagram_access_token(self) -> str:
    """Get Instagram access token."""
    # Try OAuth token first
    from src.token_manager import TokenManager
    manager = TokenManager(state_dir="state")
    token_data = manager.get_token()
    
    if token_data and not manager.is_token_expired():
        return token_data["access_token"]
    
    # Fall back to environment variable
    return os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
```

This would enable **fully automated token management** where:
1. User authenticates once via OAuth
2. Bot automatically uses the OAuth token
3. Token refreshes automatically
4. No manual environment variable updates needed

### Architecture: Single-Account Design

**Important:** The current bot architecture is designed for **single-account operation**, not multi-account.

#### How It Works

1. **main.py is executed once per bot run**
   - Each execution processes pending comments for ONE Instagram account
   - The token is loaded at startup and used throughout that execution
   - When execution completes, the process ends

2. **Single Token Storage**
   - Only ONE token stored in `state/instagram_token.json` at a time
   - New OAuth login overwrites the previous token
   - Dashboard shows authentication status for the currently stored token

3. **Execution Model**
   ```
   Run 1: python main.py → Uses Token A → Processes comments → Exits
   Run 2: python main.py → Uses Token A → Processes comments → Exits
   Run 3: python main.py → Uses Token A → Processes comments → Exits
   ```

4. **Account Switching**
   - To switch accounts: Login via OAuth with a different account
   - New token replaces old token in `state/instagram_token.json`
   - Next `main.py` execution will use the new account's token

#### Why Single-Account?

The bot is designed as a **single-purpose automation tool** for one Instagram Business account:
- Monitors comments on that account's posts
- Responds using that account's identity
- Manages that account's comment threads

This design is intentional because:
- Most use cases involve managing one brand/account
- Simpler architecture without session/user management complexity
- Clearer audit trail and logging
- Easier to deploy and maintain

#### Multi-Account Support (Not Currently Implemented)

To support multiple accounts simultaneously, you would need:

1. **Session Management**
   - Store multiple tokens with account identifiers
   - Dashboard tracks which user is logged in
   - Token storage: `state/tokens/<user_id>/instagram_token.json`

2. **Process-per-Account Model**
   ```python
   # main.py would need to accept an account parameter
   python main.py --account=user1
   python main.py --account=user2
   ```

3. **Modified Config Class**
   ```python
   def __init__(self, account_id: Optional[str] = None):
       self.account_id = account_id
       self.token_manager = TokenManager(
           state_dir=f"state/accounts/{account_id or 'default'}"
       )
   ```

4. **Dashboard Changes**
   - Multi-user authentication
   - Account selector in UI
   - Separate audit logs per account

**Current Recommendation:** Deploy separate bot instances for each Instagram account, each with its own token and state directory.

### Summary

**Where the token is used:**
- **Storage:** `state/instagram_token.json` (via TokenManager) - ONE token for ONE account
- **Retrieval:** `src/config.py` → `config.instagram_access_token` property
- **Initialization:** `main.py` → `InstagramAPI(access_token=...)` - Happens once per execution
- **Operations:** All Instagram Graph API calls in `src/instagram_api.py`
  - Fetching comments and replies
  - Getting post captions
  - Posting replies to comments

**Key Point:** `main.py` is executed once per bot run, loads the token at startup, processes comments for that ONE account, then exits. It's not a long-running server that handles multiple accounts - it's a single-execution batch processor for a single Instagram account.

## API Endpoints Used

1. **Authorization**: `https://api.instagram.com/oauth/authorize`
2. **Token Exchange**: `https://api.instagram.com/oauth/access_token`
3. **Long-Lived Token**: `https://graph.instagram.com/access_token?grant_type=ig_exchange_token`
4. **Token Refresh**: `https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token`

## Files Modified/Created

### Created:
- `src/token_manager.py` - Token management module
- `tests/unit/test_token_manager.py` - Token manager tests
- `tests/unit/test_oauth_endpoints.py` - OAuth helper tests
- `OAUTH_IMPLEMENTATION.md` - This documentation

### Modified:
- `src/config.py` - Added OAuth config properties
- `dashboard.py` - Added OAuth endpoints and UI updates
- `tests/unit/test_config.py` - Added OAuth config tests
- `README.md` - Added OAuth setup documentation
- `.env.example` - Added OAuth environment variables

## Dependencies

No additional dependencies required - OAuth implementation uses:
- Python standard library (`secrets`, `json`, `datetime`)
- `requests` library (already in requirements.txt)

## Environment Variables

```bash
# Required for OAuth
INSTAGRAM_CLIENT_ID=your_facebook_app_id
INSTAGRAM_CLIENT_SECRET=your_facebook_app_secret
INSTAGRAM_REDIRECT_URI=http://127.0.0.1:5000/auth/instagram/callback
```

## Setup Instructions

1. **Create Facebook App**:
   - Go to https://developers.facebook.com/
   - Create a new app
   - Add Instagram Graph API or Instagram Basic Display API

2. **Configure OAuth**:
   - Add redirect URI: `http://127.0.0.1:5000/auth/instagram/callback`
   - For production, use your domain's HTTPS URL

3. **Update Environment**:
   ```bash
   INSTAGRAM_CLIENT_ID=your_app_id
   INSTAGRAM_CLIENT_SECRET=your_app_secret
   INSTAGRAM_REDIRECT_URI=http://127.0.0.1:5000/auth/instagram/callback
   ```

4. **Start Dashboard**:
   ```bash
   python dashboard.py
   ```

5. **Login**:
   - Navigate to http://127.0.0.1:5000
   - Click "Login with Instagram"
   - Authorize the app
   - Token automatically saved and refreshed

## Screenshots

### Not Authenticated State
![Not Authenticated](https://github.com/user-attachments/assets/647cc62f-5889-4e69-bea8-f9784c09c113)

### Authenticated State
![Authenticated](https://github.com/user-attachments/assets/e11d81ed-fb99-4b02-91b1-91c627e11090)

## Future Enhancements

Potential improvements for future iterations:
- [ ] Add session management with Redis for multi-instance deployments
- [ ] Implement token refresh background task (cron/scheduler)
- [ ] Add user role management (admin, viewer, etc.)
- [ ] Display token expiration countdown in UI
- [ ] Add email notifications for token expiration
- [ ] Support multiple authenticated users
- [ ] Add audit log for authentication events

## Production Considerations

1. **HTTPS Required**: Use HTTPS redirect URIs in production
2. **Session Storage**: Consider Redis/Memcached for session state in multi-instance deployments
3. **Token Encryption**: Consider encrypting tokens at rest in database
4. **Rate Limiting**: Implement rate limiting on OAuth endpoints
5. **Monitoring**: Add logging and monitoring for OAuth flows
6. **Error Handling**: Enhance error messages for users

## References

- [Instagram Graph API Documentation](https://developers.facebook.com/docs/instagram-api/)
- [Long-Lived Access Tokens Guide](https://developers.facebook.com/docs/instagram-basic-display-api/guides/long-lived-access-tokens)
- [OAuth 2.0 Specification](https://oauth.net/2/)
