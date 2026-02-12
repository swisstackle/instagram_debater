<!-- 
This is an issue template for implementing Instagram Business Login OAuth.
Copy the content below and create a new GitHub issue.
-->

# Implement Instagram Business Login OAuth

## Overview

Implement Instagram Business Login using OAuth 2.0 to allow users to authenticate through the dashboard and obtain long-lived access tokens for Instagram API operations.

## Requirements

Based on research documented in [INSTAGRAM_OAUTH_RESEARCH.md](INSTAGRAM_OAUTH_RESEARCH.md):

### Core Requirements
- [ ] Users should be able to log into the dashboard using Instagram Business Login
- [ ] Implement OAuth endpoints in `dashboard.py`
- [ ] Support long-lived tokens (60-day validity with automatic refresh)
- [ ] Store and manage tokens securely
- [ ] Handle token expiration and refresh automatically

### Implementation Details

#### 1. OAuth Endpoints in dashboard.py

Add the following endpoints to `dashboard.py`:

```python
@app.route('/auth/instagram/login')
def instagram_oauth_login():
    """Initiate Instagram OAuth flow."""
    # Redirect to Instagram OAuth with proper params
    pass

@app.route('/auth/instagram/callback')
def instagram_oauth_callback():
    """Handle OAuth callback, exchange code for token, store long-lived token."""
    pass

@app.route('/auth/instagram/logout')
def instagram_oauth_logout():
    """Clear user session and logout."""
    pass
```

#### 2. Long-Lived Token Management

- Exchange short-lived token for long-lived token (60 days) immediately after OAuth callback
- Store token with expiration metadata in `state/instagram_token.json`
- Implement automatic refresh mechanism (refresh at day 50-55)
- Create `src/token_manager.py` module for token operations

#### 3. Configuration

OAuth credentials already added to config:
- `INSTAGRAM_CLIENT_ID` - Facebook App ID
- `INSTAGRAM_CLIENT_SECRET` - Facebook App Secret  
- `INSTAGRAM_REDIRECT_URI` - OAuth callback URL

#### 4. Dashboard UI Updates

- Add "Login with Instagram" button on dashboard
- Show authenticated user info (username, profile)
- Display token status (valid, expires in X days)
- Add logout functionality

#### 5. Security Requirements

- Use state parameter for CSRF protection
- Store tokens server-side only (not in client-side JS)
- Encrypt tokens at rest if storing in database
- Use HTTPS for production redirect URIs
- Validate redirect URI matches registered URI

## Technical Specifications

### OAuth Flow
```
User → Dashboard "Login" → Instagram OAuth → User Approves → 
Callback → Exchange code → Short-lived token → Exchange for long-lived token → 
Store token → Dashboard (authenticated)
```

### Token Exchange Endpoints

**Get short-lived token:**
```
POST https://api.instagram.com/oauth/access_token
Parameters: client_id, client_secret, grant_type, redirect_uri, code
```

**Exchange for long-lived token:**
```
GET https://graph.instagram.com/access_token
?grant_type=ig_exchange_token
&client_secret=YOUR_CLIENT_SECRET
&access_token=SHORT_LIVED_TOKEN
```

**Refresh long-lived token:**
```
GET https://graph.instagram.com/refresh_access_token
?grant_type=ig_refresh_token
&access_token=CURRENT_LONG_LIVED_TOKEN
```

### Required Scopes

Request these scopes during OAuth:
- `instagram_basic` - Basic profile info
- `instagram_manage_comments` - Read/manage comments (core bot functionality)
- `pages_show_list` - Access Facebook Pages (required for business accounts)

### Dependencies

Install if not already present:
```bash
pip install Authlib requests python-dotenv
```

Update `requirements.txt` accordingly.

## Implementation Checklist

### Phase 1: Basic OAuth Flow
- [ ] Add Authlib to dependencies
- [ ] Implement OAuth login endpoint in dashboard.py
- [ ] Implement OAuth callback endpoint
- [ ] Test OAuth flow with development redirect URI

### Phase 2: Long-Lived Token Management
- [ ] Create `src/token_manager.py` module
- [ ] Implement token exchange (short → long-lived)
- [ ] Implement token storage in `state/instagram_token.json`
- [ ] Add token metadata (expires_in, obtained_at)

### Phase 3: Token Refresh
- [ ] Implement token expiration check
- [ ] Implement automatic token refresh logic
- [ ] Add background task or startup check for token refresh
- [ ] Log token refresh events

### Phase 4: Dashboard UI
- [ ] Add "Login with Instagram" button
- [ ] Show authenticated user status
- [ ] Display token expiration info
- [ ] Add logout functionality
- [ ] Handle authentication errors gracefully

### Phase 5: Security & Testing
- [ ] Add state parameter for CSRF protection
- [ ] Validate redirect URI in callback
- [ ] Add unit tests for token_manager
- [ ] Add integration tests for OAuth flow (mocked)
- [ ] Test token refresh mechanism
- [ ] Security audit of token storage

### Phase 6: Documentation
- [ ] Update README with OAuth setup instructions
- [ ] Document how to register app in Meta Developer Console
- [ ] Document how to configure redirect URIs
- [ ] Add troubleshooting section

## References

All research and implementation details are documented in:
**[INSTAGRAM_OAUTH_RESEARCH.md](INSTAGRAM_OAUTH_RESEARCH.md)**

Key sections:
- [OAuth Flow Setup](INSTAGRAM_OAUTH_RESEARCH.md#oauth-flow-setup)
- [Redirect URL Configuration](INSTAGRAM_OAUTH_RESEARCH.md#redirect-url-configuration)
- [Token Types and Management](INSTAGRAM_OAUTH_RESEARCH.md#token-types-and-management)
- [Python Flask Implementation](INSTAGRAM_OAUTH_RESEARCH.md#python-flask-implementation)
- [Security Best Practices](INSTAGRAM_OAUTH_RESEARCH.md#security-best-practices)

### Official Documentation
- [Meta for Developers](https://developers.facebook.com/)
- [Instagram Graph API](https://developers.facebook.com/docs/instagram-api/)
- [Long-Lived Access Tokens](https://developers.facebook.com/docs/instagram-basic-display-api/guides/long-lived-access-tokens)

### Implementation Guides
- [Flask OAuth Tutorial](https://blog.miguelgrinberg.com/post/oauth-authentication-with-flask-in-2023)
- [Instagram Graph API User Login](https://dev.to/superface/instagram-graph-api-explained-how-to-log-in-users-lp8)
- [Token Management Guide](https://www.getfishtank.com/insights/renewing-instagram-access-token)

---

## Notes

- Current code already has OAuth config properties in `src/config.py`
- Current code already has tests for OAuth config in `tests/unit/test_config.py`
- Use existing project patterns (Config class, file_utils, etc.)
- Follow TDD approach as per project conventions
- Dashboard server runs on `127.0.0.1:5000` by default

## Success Criteria

✅ Users can click "Login with Instagram" on dashboard  
✅ OAuth flow successfully authenticates users  
✅ Long-lived tokens (60 days) are obtained and stored  
✅ Tokens automatically refresh before expiration  
✅ Dashboard shows authenticated user info  
✅ All security best practices implemented  
✅ Comprehensive test coverage  
✅ Documentation updated
