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
- `requirements.txt` - Added Authlib dependency
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
