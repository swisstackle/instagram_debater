<!-- 
This is an issue template for implementing Instagram Business Login OAuth.
Copy the content below and create a new GitHub issue.
-->

# Implement Instagram Business Login OAuth

## Overview

Implement Instagram Business Login using OAuth 2.0 to allow users to authenticate through the dashboard and obtain long-lived access tokens for Instagram API operations.

## ⚠️ Development Approach: Test-Driven Development (TDD)

**This project follows Test-Driven Development principles. You MUST:**

1. **Create class/module skeletons first** - Define classes, methods, and interfaces with docstrings but minimal implementation
2. **Write tests second** - Create comprehensive unit tests and Playwright tests for the skeleton code
3. **Implement functionality last** - Make the tests pass by implementing the actual logic

**TDD Workflow:**
```
1. Write skeleton code (classes, method signatures, docstrings)
2. Write unit tests (pytest) for all methods
3. Write integration/E2E tests (Playwright) for UI flows
4. Run tests (they should fail)
5. Implement actual functionality
6. Run tests (they should pass)
7. Refactor and iterate
```

This approach ensures:
- ✅ Test coverage is complete from the start
- ✅ Clear API design before implementation
- ✅ Confidence that all functionality works as expected
- ✅ Easy refactoring with test safety net

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

## Implementation Checklist (TDD Approach)

### Phase 1: Project Setup & Dependencies
- [ ] Add Authlib to `requirements.txt`
- [ ] Install dependencies: `pip install Authlib requests python-dotenv playwright`
- [ ] Verify project structure and existing patterns

### Phase 2: Token Manager - Skeleton & Tests
**TDD Step 1: Create Skeleton**
- [ ] Create `src/token_manager.py` with `TokenManager` class skeleton
- [ ] Define method signatures: `save_token()`, `get_token()`, `is_token_expired()`, `refresh_token()`
- [ ] Add comprehensive docstrings for all methods

**TDD Step 2: Write Tests**
- [ ] Create `tests/unit/test_token_manager.py`
- [ ] Write unit tests for `save_token()` (test file creation, JSON format)
- [ ] Write unit tests for `get_token()` (test retrieval, missing file, expired token)
- [ ] Write unit tests for `is_token_expired()` (test expiration logic)
- [ ] Write unit tests for `refresh_token()` (test API call mocking)
- [ ] Run tests (expected to fail at this stage)

**TDD Step 3: Implement**
- [ ] Implement token storage in `state/instagram_token.json`
- [ ] Implement token retrieval logic
- [ ] Implement expiration check (refresh 5 days before expiry)
- [ ] Implement token refresh API call
- [ ] Run tests (all tests should now pass)

### Phase 3: OAuth Flow - Skeleton & Tests
**TDD Step 1: Create Skeleton**
- [ ] Add OAuth route skeletons to `dashboard.py`:
  - `instagram_oauth_login()` - Initiate OAuth
  - `instagram_oauth_callback()` - Handle callback
  - `instagram_oauth_logout()` - Clear session
- [ ] Add helper function skeletons: `exchange_for_long_lived_token()`, `validate_oauth_state()`
- [ ] Add comprehensive docstrings

**TDD Step 2: Write Tests**
- [ ] Create `tests/unit/test_oauth_endpoints.py`
- [ ] Write unit tests for login endpoint (test redirect URL generation)
- [ ] Write unit tests for callback endpoint (test token exchange, state validation)
- [ ] Write unit tests for logout endpoint (test session clearing)
- [ ] Write unit tests for `exchange_for_long_lived_token()` (mock API calls)
- [ ] Mock Instagram API responses using `requests-mock`
- [ ] Run tests (expected to fail at this stage)

**TDD Step 3: Implement**
- [ ] Configure OAuth with Authlib in dashboard.py
- [ ] Implement login endpoint (redirect to Instagram with state parameter)
- [ ] Implement callback endpoint (exchange code → short-lived → long-lived token)
- [ ] Implement logout endpoint (clear session)
- [ ] Implement helper functions
- [ ] Run tests (all tests should now pass)

### Phase 4: Dashboard UI - Skeleton & Tests
**TDD Step 1: Create Skeleton**
- [ ] Add HTML template skeletons for:
  - Login button/page
  - Authenticated user dashboard
  - Token status display
- [ ] Add route skeletons for UI endpoints

**TDD Step 2: Write Tests**
- [ ] Create `e2e/test_oauth_flow.js` (Playwright)
- [ ] Write E2E test: User clicks "Login with Instagram" button
- [ ] Write E2E test: OAuth redirect flow (mock Instagram OAuth)
- [ ] Write E2E test: Successful authentication shows user info
- [ ] Write E2E test: Token status displayed correctly
- [ ] Write E2E test: Logout clears session
- [ ] Write E2E test: Error handling (failed OAuth, expired token)
- [ ] Run tests (expected to fail at this stage)

**TDD Step 3: Implement**
- [ ] Create/update HTML templates with login UI
- [ ] Add "Login with Instagram" button to dashboard
- [ ] Display authenticated user info (username, profile)
- [ ] Show token status (valid, expires in X days)
- [ ] Add logout button and functionality
- [ ] Handle authentication errors gracefully
- [ ] Run tests (all tests should now pass)

### Phase 5: Token Refresh Automation - Skeleton & Tests
**TDD Step 1: Create Skeleton**
- [ ] Add background task skeleton for token refresh check
- [ ] Add startup check skeleton for token validation
- [ ] Add logging skeleton for refresh events

**TDD Step 2: Write Tests**
- [ ] Write unit tests for background refresh task
- [ ] Write unit tests for startup token validation
- [ ] Write tests for refresh logging
- [ ] Mock time/date for expiration scenarios
- [ ] Run tests (expected to fail at this stage)

**TDD Step 3: Implement**
- [ ] Implement background task or startup check for token refresh
- [ ] Add automatic refresh logic (trigger at day 55, which is 5 days before 60-day expiration)
- [ ] Add logging for token refresh events
- [ ] Run tests (all tests should now pass)

### Phase 6: Security - Tests & Implementation
**TDD Step 1: Write Security Tests**
- [ ] Write tests for CSRF protection (state parameter validation)
- [ ] Write tests for redirect URI validation
- [ ] Write tests for token storage security (server-side only)
- [ ] Write tests for HTTPS enforcement (production)
- [ ] Run tests (expected to fail at this stage)

**TDD Step 2: Implement Security**
- [ ] Implement state parameter generation and validation (CSRF)
- [ ] Validate redirect URI matches registered URI
- [ ] Ensure tokens stored server-side only
- [ ] Add HTTPS checks for production environment
- [ ] Run tests (all tests should now pass)

### Phase 7: Integration Testing
- [ ] Run all unit tests together: `pytest tests/unit/` (all should pass)
- [ ] Run all Playwright tests: `npx playwright test` (all should pass)
- [ ] Test full OAuth flow end-to-end manually
- [ ] Test token refresh mechanism
- [ ] Test error scenarios (network failures, invalid tokens)
- [ ] Verify all tests pass (100% pass rate expected)

### Phase 8: Documentation
- [ ] Update README with OAuth setup instructions
- [ ] Document how to register app in Meta Developer Console
- [ ] Document how to configure redirect URIs
- [ ] Add troubleshooting section
- [ ] Document testing procedures
- [ ] Add inline code comments for complex logic

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

- **IMPORTANT: Follow TDD approach strictly** - Skeleton → Tests → Implementation
- Current code already has OAuth config properties in `src/config.py`
- Current code already has tests for OAuth config in `tests/unit/test_config.py`
- Use existing project patterns (Config class, file_utils, etc.)
- Use pytest for unit tests, Playwright for E2E tests
- Dashboard server runs on `127.0.0.1:5000` by default

## Success Criteria

✅ All code written following TDD approach (skeleton → tests → implementation)  
✅ Comprehensive test coverage (unit tests + Playwright tests)  
✅ All tests passing (pytest + Playwright)  
✅ Users can click "Login with Instagram" on dashboard  
✅ OAuth flow successfully authenticates users  
✅ Long-lived tokens (60 days) are obtained and stored  
✅ Tokens automatically refresh before expiration  
✅ Dashboard shows authenticated user info  
✅ All security best practices implemented  
✅ Documentation updated
