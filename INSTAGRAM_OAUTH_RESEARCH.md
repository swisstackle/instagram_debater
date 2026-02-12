# Instagram Business Login OAuth Research

This document provides comprehensive research on implementing Instagram Business Login using OAuth, including redirect URL configuration and implementation details.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [OAuth Flow Setup](#oauth-flow-setup)
- [Redirect URL Configuration](#redirect-url-configuration)
- [OAuth Authorization Flow](#oauth-authorization-flow)
- [Token Types and Management](#token-types-and-management)
- [Required Scopes and Permissions](#required-scopes-and-permissions)
- [Python Flask Implementation](#python-flask-implementation)
- [Security Best Practices](#security-best-practices)
- [References](#references)

## Overview

Instagram Business Login uses Facebook's OAuth 2.0 authentication system since Instagram is now part of Meta's infrastructure. This allows applications to authenticate users and obtain access tokens to interact with the Instagram Graph API on behalf of business and creator accounts.

**Key Concept: Redirect URL**
The redirect URL (also called callback URL) is the endpoint in your application where Instagram/Facebook sends users after they authorize your app. This URL must be:
- Registered in your Meta App settings
- Publicly accessible (for production)
- An exact match to what's configured in Meta Developer console
- HTTPS in production (HTTP allowed for localhost development)

## Prerequisites

### 1. Instagram Account Requirements
- Instagram account must be a **Professional Account** (Business or Creator)
- Can be converted via Instagram app: `Settings → Account → Switch to Professional Account`
- Source: [Instagram API Integration Guide](https://gist.github.com/PrenSJ2/0213e60e834e66b7e09f7f93999163fc)

### 2. Facebook Page Connection
- Professional Instagram account must be linked to a Facebook Page
- This is required for Instagram Graph API access

### 3. Meta Developer Account
- Register at [Meta for Developers](https://developers.facebook.com/)
- Create a new app or use existing one

## OAuth Flow Setup

### Step 1: Create a Meta Developer App

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Click **"Create App"**
3. Select **"Business"** as the app type
4. Provide app details (name, contact email, etc.)
5. In the app dashboard, add **Instagram** product:
   - Click "Add Product"
   - Select "Instagram" or "Instagram Graph API"

**Reference:** [Meta Developer Registration](https://developers.facebook.com/docs/development/register/)

### Step 2: Configure OAuth Settings

Navigate to your app's settings and configure OAuth:

1. Go to **Settings → Basic** or **Instagram → API Setup**
2. Find the **Valid OAuth Redirect URIs** field
3. Add your redirect URIs:

**Development Example:**
```
http://localhost:8000/api/instagram/oauth-callback
http://localhost:5000/auth/instagram/callback
http://127.0.0.1:8000/auth/callback
```

**Production Example:**
```
https://yourdomain.com/api/instagram/oauth-callback
https://yourdomain.com/auth/instagram/callback
```

**Important Notes:**
- URLs must match **exactly** (including trailing slashes if present)
- Both HTTP and HTTPS localhost URLs are allowed for development
- Production must use HTTPS
- You can register multiple redirect URIs

**References:**
- [Instagram Integration Documentation](https://docs.postiz.com/providers/instagram)
- [Google Cloud Instagram Connector Configuration](https://docs.cloud.google.com/integration-connectors/docs/connectors/instagram/configure)

## Redirect URL Configuration

### What is a Redirect URL?

The redirect URL is where Instagram/Facebook sends the user after they complete the OAuth authorization. The URL will include:
- **Authorization Code** (in query parameter): Used to exchange for access token
- **State** (optional): For CSRF protection

### Redirect URL Flow

```
1. User clicks "Login with Instagram" in your app
2. Your app redirects to Instagram OAuth URL with:
   - client_id (your app ID)
   - redirect_uri (must match registered URI)
   - scope (permissions requested)
   - state (random string for security)

3. User sees Instagram/Facebook login and permission consent screen
4. User approves permissions
5. Instagram redirects to: redirect_uri?code=AUTHORIZATION_CODE&state=YOUR_STATE
6. Your app receives the code at the redirect_uri endpoint
7. Your backend exchanges code for access token
```

### Example OAuth Authorization URL

```
https://api.instagram.com/oauth/authorize
  ?client_id=YOUR_CLIENT_ID
  &redirect_uri=https://yourdomain.com/auth/instagram/callback
  &scope=instagram_basic,instagram_manage_comments
  &response_type=code
  &state=RANDOM_STATE_STRING
```

**Reference:** [Pathfix Instagram Graph API Integration](https://docs.pathfix.com/integrating-with-instagram-graph-api)

## OAuth Authorization Flow

### Complete Flow Diagram

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │ 1. Clicks "Login with Instagram"
       ▼
┌─────────────────────┐
│   Your App          │
│  (Login Endpoint)   │
└──────┬──────────────┘
       │ 2. Redirects to Instagram OAuth
       ▼
┌─────────────────────┐
│   Instagram         │
│  (OAuth Authorize)  │
└──────┬──────────────┘
       │ 3. User logs in and approves
       │ 4. Redirects with code
       ▼
┌─────────────────────┐
│   Your App          │
│ (Redirect URI/      │
│   Callback)         │
└──────┬──────────────┘
       │ 5. Exchanges code for access token
       ▼
┌─────────────────────┐
│   Instagram API     │
│  (Token Exchange)   │
└──────┬──────────────┘
       │ 6. Returns access token
       ▼
┌─────────────────────┐
│   Your App          │
│  (Stores token,     │
│   makes API calls)  │
└─────────────────────┘
```

### Step-by-Step Implementation

#### Step 1: User Initiates Login
User clicks a "Login with Instagram" button in your application.

#### Step 2: Redirect to Instagram
Your app redirects to Instagram's authorization endpoint with required parameters.

#### Step 3: User Authorizes
User logs into Instagram/Facebook (if not already logged in) and sees permission consent screen showing what access your app requests.

#### Step 4: Authorization Code Returned
Instagram redirects back to your registered redirect URI with an authorization code.

#### Step 5: Exchange Code for Token
Your backend makes a server-to-server request to exchange the authorization code for an access token.

**Token Exchange Endpoint:**
```
POST https://api.instagram.com/oauth/access_token
```

**Parameters:**
- `client_id`: Your app ID
- `client_secret`: Your app secret
- `grant_type`: "authorization_code"
- `redirect_uri`: Same URI used in authorization
- `code`: The authorization code received

#### Step 6: Receive Access Token
Instagram returns a JSON response with:
- `access_token`: Short-lived user access token (1 hour validity)
- `user_id`: Instagram user ID

**References:**
- [Instagram Graph API User Login Explanation](https://dev.to/superface/instagram-graph-api-explained-how-to-log-in-users-lp8)
- [Instagram API Integration Tutorial](https://www.todaysmm.com/en/blog/instagram-api-integration)

## Token Types and Management

### Short-Lived User Access Token

**Characteristics:**
- **Validity:** ~1 hour
- **Usage:** Immediate use after OAuth login
- **Obtained:** Through the initial OAuth authorization flow

### Long-Lived Access Token

**Characteristics:**
- **Validity:** 60 days
- **Usage:** Long-term integrations, scheduled tasks, analytics
- **Must be refreshed:** At least once every 60 days to maintain access
- **Same permissions:** Inherits all scopes from the short-lived token

**How to Obtain Long-Lived Token:**

After receiving a short-lived token, exchange it for a long-lived token:

```
GET https://graph.instagram.com/access_token
  ?grant_type=ig_exchange_token
  &client_secret=YOUR_CLIENT_SECRET
  &access_token=SHORT_LIVED_TOKEN
```

**Response:**
```json
{
  "access_token": "LONG_LIVED_ACCESS_TOKEN",
  "token_type": "bearer",
  "expires_in": 5184000  // 60 days in seconds
}
```

### Token Refresh

Before the 60-day expiration, refresh the long-lived token:

```
GET https://graph.instagram.com/refresh_access_token
  ?grant_type=ig_refresh_token
  &access_token=CURRENT_LONG_LIVED_TOKEN
```

**Best Practice:** Set up automatic token refresh at day 50-55 to ensure continuous access.

**References:**
- [Instagram Authentication Guide](https://github.com/rshtechpy/n8n-nodes-instagram-integrations/blob/master/AUTHENTICATION_GUIDE.md)
- [Long-Lived Token Management](https://www.getfishtank.com/insights/renewing-instagram-access-token)
- [Token Refresh Tutorial](https://reshmeeauckloo.com/posts/powerautomate_instagram-refresh-longlived-token/)

### Token Comparison Table

| Feature | Short-Lived Token | Long-Lived Token |
|---------|-------------------|------------------|
| **Validity** | ~1 hour | 60 days (renewable) |
| **Use Case** | Immediate, interactive | Background tasks, scheduled jobs |
| **Obtained Via** | OAuth authorization flow | Exchange from short-lived token |
| **Refresh Required** | No (expires quickly) | Yes (before 60 days) |
| **Permissions** | User-consented scopes | Same as short-lived token |

## Required Scopes and Permissions

### Common Instagram Graph API Scopes

When redirecting users to OAuth, request only the permissions your app needs:

| Scope | Description | Use Case |
|-------|-------------|----------|
| `instagram_basic` | Read basic profile info | User profile, media |
| `instagram_manage_insights` | Read analytics data | Post metrics, engagement stats |
| `instagram_manage_comments` | Read and manage comments | Comment moderation, replies |
| `instagram_content_publish` | Publish content | Post photos/videos |
| `pages_show_list` | Access to Facebook Pages | Required for business accounts |
| `pages_read_engagement` | Read page engagement | Page-level metrics |

### Requesting Scopes in OAuth URL

```
scope=instagram_basic,instagram_manage_comments,instagram_manage_insights
```

**Important Notes:**
- Only request scopes your app actually needs
- Users see the permissions you request and can decline
- Some permissions require App Review for public apps
- Business accounts typically need `pages_show_list` scope

**References:**
- [Facebook Permissions Reference](https://developers.facebook.com/docs/permissions/reference)
- [Instagram API Scopes Overview](https://www.getphyllo.com/post/instagram-graph-apis-what-are-they-and-how-do-developers-access-them)

## Python Flask Implementation

### Installation

```bash
pip install Flask Authlib requests python-dotenv
```

### Environment Configuration

Create `.env` file:

```bash
# Instagram OAuth Configuration
INSTAGRAM_CLIENT_ID=your_facebook_app_id
INSTAGRAM_CLIENT_SECRET=your_facebook_app_secret
INSTAGRAM_REDIRECT_URI=http://localhost:5000/auth/instagram/callback

# App Configuration
SECRET_KEY=your_random_secret_key_here
```

### Basic Flask OAuth Implementation

```python
from flask import Flask, redirect, url_for, request, session, jsonify
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Configure OAuth
oauth = OAuth(app)
instagram = oauth.register(
    name='instagram',
    client_id=os.getenv('INSTAGRAM_CLIENT_ID'),
    client_secret=os.getenv('INSTAGRAM_CLIENT_SECRET'),
    access_token_url='https://api.instagram.com/oauth/access_token',
    authorize_url='https://api.instagram.com/oauth/authorize',
    api_base_url='https://graph.instagram.com/',
    client_kwargs={
        'scope': 'instagram_basic,instagram_manage_comments'
    },
)

@app.route('/')
def index():
    """Homepage with login link."""
    user = session.get('user')
    if user:
        return f'''
            <h1>Welcome, {user['username']}!</h1>
            <p>User ID: {user['id']}</p>
            <a href="/logout">Logout</a>
        '''
    return '<a href="/login">Login with Instagram</a>'

@app.route('/login')
def login():
    """Initiate OAuth login by redirecting to Instagram."""
    redirect_uri = url_for('auth_callback', _external=True)
    return instagram.authorize_redirect(redirect_uri)

@app.route('/auth/instagram/callback')
def auth_callback():
    """
    OAuth callback endpoint - Instagram redirects here after user authorizes.
    This is the redirect URI that must be registered in Meta Developer console.
    """
    try:
        # Exchange authorization code for access token
        token = instagram.authorize_access_token()
        
        # Get user profile information
        resp = instagram.get('me?fields=id,username')
        profile = resp.json()
        
        # Store user info in session
        session['user'] = profile
        session['access_token'] = token['access_token']
        
        return redirect('/')
    except Exception as e:
        return f'Error during authentication: {str(e)}', 400

@app.route('/logout')
def logout():
    """Clear session and logout."""
    session.clear()
    return redirect('/')

@app.route('/api/user')
def api_user():
    """API endpoint to get current user info."""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify(user)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### Advanced Implementation with Long-Lived Token

```python
import requests
from datetime import datetime, timedelta

def exchange_for_long_lived_token(short_lived_token, client_secret):
    """
    Exchange short-lived token for long-lived token (60 days).
    
    Args:
        short_lived_token: Token received from OAuth
        client_secret: Your app's client secret
        
    Returns:
        dict: Response with long-lived token and expiration
    """
    url = 'https://graph.instagram.com/access_token'
    params = {
        'grant_type': 'ig_exchange_token',
        'client_secret': client_secret,
        'access_token': short_lived_token
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def refresh_long_lived_token(current_token):
    """
    Refresh long-lived token before it expires.
    
    Args:
        current_token: Current long-lived token
        
    Returns:
        dict: Response with refreshed token
    """
    url = 'https://graph.instagram.com/refresh_access_token'
    params = {
        'grant_type': 'ig_refresh_token',
        'access_token': current_token
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

# Updated callback with long-lived token exchange
@app.route('/auth/instagram/callback')
def auth_callback_with_long_lived():
    """OAuth callback with long-lived token exchange."""
    try:
        # Exchange authorization code for short-lived token
        token_data = instagram.authorize_access_token()
        short_lived_token = token_data['access_token']
        
        # Exchange for long-lived token
        long_lived_data = exchange_for_long_lived_token(
            short_lived_token,
            os.getenv('INSTAGRAM_CLIENT_SECRET')
        )
        
        # Get user profile
        headers = {'Authorization': f'Bearer {long_lived_data["access_token"]}'}
        resp = requests.get(
            'https://graph.instagram.com/me?fields=id,username',
            headers=headers
        )
        profile = resp.json()
        
        # Store in session or database
        session['user'] = profile
        session['access_token'] = long_lived_data['access_token']
        session['token_expires_in'] = long_lived_data['expires_in']
        session['token_obtained_at'] = datetime.utcnow().isoformat()
        
        return redirect('/')
    except Exception as e:
        return f'Error: {str(e)}', 400
```

### Testing the Implementation

1. Start the Flask app:
   ```bash
   python app.py
   ```

2. Navigate to `http://localhost:5000`

3. Click "Login with Instagram"

4. You'll be redirected to Instagram/Facebook login

5. After authorizing, you'll be redirected back to your app at the callback URL

6. Your app will have the access token to make Instagram API calls

**References:**
- [Flask OAuth Tutorial by Miguel Grinberg](https://blog.miguelgrinberg.com/post/oauth-authentication-with-flask-in-2023)
- [Flask OAuth Example Repository](https://github.com/miguelgrinberg/flask-oauth-example)
- [Python OAuth Implementation Guide](https://www.w3computing.com/articles/implementing-oauth-authentication-in-python-web-apps/)
- [OAuth 2.0 in Flask Applications](https://codezup.com/implementing-oauth-2-0-authentication-in-flask-applications/)

## Security Best Practices

### 1. Use State Parameter for CSRF Protection

Always include a random `state` parameter in your OAuth URL:

```python
import secrets

state = secrets.token_urlsafe(32)
session['oauth_state'] = state

# In authorization URL:
url = f"https://api.instagram.com/oauth/authorize?...&state={state}"

# In callback, verify:
if request.args.get('state') != session.get('oauth_state'):
    return 'Invalid state parameter', 403
```

### 2. Secure Token Storage

- **Never** store tokens in client-side JavaScript or local storage
- Store tokens server-side (session, database, encrypted storage)
- Use environment variables for secrets
- Encrypt tokens at rest in database

### 3. HTTPS in Production

- Always use HTTPS for production redirect URIs
- Tokens transmitted over HTTP can be intercepted
- Meta requires HTTPS for production apps

### 4. Token Expiration Handling

```python
from datetime import datetime, timedelta

def is_token_expired(token_obtained_at, expires_in):
    """Check if token needs refresh."""
    obtained = datetime.fromisoformat(token_obtained_at)
    expiry = obtained + timedelta(seconds=expires_in)
    # Refresh 5 days before expiration
    refresh_threshold = expiry - timedelta(days=5)
    return datetime.utcnow() >= refresh_threshold
```

### 5. Validate Redirect URI

- Whitelist allowed redirect URIs in your app
- Verify redirect URI matches registered URI before processing
- Prevent open redirect vulnerabilities

### 6. Minimal Scope Requests

- Only request scopes your app needs
- More permissions = more user friction
- Reduces security risk if token is compromised

### 7. Regular Security Audits

- Monitor for unusual API usage
- Implement rate limiting
- Log authentication attempts
- Rotate client secrets periodically

## Implementation Recommendations for This Project

Based on the current codebase structure, here are specific recommendations:

### 1. Add OAuth Routes to Dashboard

Since the project has a `dashboard.py`, consider adding OAuth endpoints there:

```python
# In dashboard.py
@app.route('/auth/instagram/login')
def instagram_oauth_login():
    """Initiate Instagram OAuth flow."""
    # Implementation here
    pass

@app.route('/auth/instagram/callback')
def instagram_oauth_callback():
    """Handle OAuth callback and store token."""
    # Implementation here
    pass
```

### 2. Update Configuration

Add OAuth settings to `src/config.py`:

```python
@property
def instagram_client_id(self) -> str:
    """Get Instagram OAuth client ID."""
    return os.getenv("INSTAGRAM_CLIENT_ID", "")

@property
def instagram_client_secret(self) -> str:
    """Get Instagram OAuth client secret."""
    return os.getenv("INSTAGRAM_CLIENT_SECRET", "")

@property
def instagram_redirect_uri(self) -> str:
    """Get Instagram OAuth redirect URI."""
    return os.getenv("INSTAGRAM_REDIRECT_URI", "")
```

### 3. Update .env.example

Add OAuth configuration:

```bash
# Instagram OAuth Configuration (for obtaining access tokens)
INSTAGRAM_CLIENT_ID=your_facebook_app_id_here
INSTAGRAM_CLIENT_SECRET=your_facebook_app_secret_here
INSTAGRAM_REDIRECT_URI=http://localhost:5000/auth/instagram/callback
```

### 4. Token Management Module

Create `src/token_manager.py`:

```python
"""Token management for Instagram access tokens."""
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
import requests

class TokenManager:
    """Manages Instagram access tokens with automatic refresh."""
    
    def __init__(self, token_file: str = "state/instagram_token.json"):
        self.token_file = token_file
        
    def save_token(self, access_token: str, expires_in: int):
        """Save token with expiration timestamp."""
        data = {
            'access_token': access_token,
            'expires_in': expires_in,
            'obtained_at': datetime.utcnow().isoformat()
        }
        os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
        with open(self.token_file, 'w') as f:
            json.dump(data, f)
    
    def get_token(self) -> Optional[str]:
        """Get current valid token, refresh if needed."""
        # Implementation here
        pass
```

### 5. Documentation Updates

Update `README.md` to include OAuth setup instructions for obtaining tokens.

### 6. Testing Considerations

Add OAuth mock tests in `tests/unit/`:

```python
def test_oauth_callback_success(monkeypatch):
    """Test successful OAuth callback."""
    # Test implementation
    pass

def test_token_exchange(monkeypatch):
    """Test token exchange for long-lived token."""
    # Test implementation
    pass
```

## References

### Official Documentation
- [Meta for Developers](https://developers.facebook.com/)
- [Instagram Platform API Documentation](https://developers.facebook.com/docs/instagram-api/)
- [Instagram Graph API Getting Started](https://developers.facebook.com/docs/instagram-api/getting-started)
- [Facebook OAuth Documentation](https://developers.facebook.com/docs/facebook-login/manually-build-a-login-flow)
- [Facebook Permissions Reference](https://developers.facebook.com/docs/permissions/reference)
- [Long-Lived Access Tokens](https://developers.facebook.com/docs/instagram-basic-display-api/guides/long-lived-access-tokens)

### Tutorials and Guides
- [Instagram API Integration Guide for Developers (2025)](https://www.todaysmm.com/en/blog/instagram-api-integration)
- [Instagram Graph API User Login Explained](https://dev.to/superface/instagram-graph-api-explained-how-to-log-in-users-lp8)
- [Comprehensive Instagram Publishing Guide](https://gist.github.com/PrenSJ2/0213e60e834e66b7e09f7f93999163fc)
- [Integrating with Instagram Graph API - Pathfix](https://docs.pathfix.com/integrating-with-instagram-graph-api)
- [Instagram Provider Setup - Postiz](https://docs.postiz.com/providers/instagram)
- [Instagram Authentication Guide](https://github.com/rshtechpy/n8n-nodes-instagram-integrations/blob/master/AUTHENTICATION_GUIDE.md)

### Token Management
- [How To Renew Instagram Long-Lived Access Token](https://www.getfishtank.com/insights/renewing-instagram-access-token)
- [Refresh Long-Lived Token via Instagram Graph API](https://reshmeeauckloo.com/posts/powerautomate_instagram-refresh-longlived-token/)
- [Generate Instagram & Facebook Long-Lived Token](https://imanetworks.ch/generate-instagram-facebook-long-lived-token/)

### Python Implementation
- [OAuth Authentication with Flask in 2023](https://blog.miguelgrinberg.com/post/oauth-authentication-with-flask-in-2023)
- [Flask OAuth Example Repository](https://github.com/miguelgrinberg/flask-oauth-example)
- [Implementing OAuth Authentication in Python Web Apps](https://www.w3computing.com/articles/implementing-oauth-authentication-in-python-web-apps/)
- [OAuth 2.0 Authentication in Flask Applications](https://codezup.com/implementing-oauth-2-0-authentication-in-flask-applications/)
- [OmniAuth Instagram Graph](https://jetrockets.github.io/omniauth-instagram-graph/)

### Additional Resources
- [Instagram Graph APIs Overview](https://www.getphyllo.com/post/instagram-graph-apis-what-are-they-and-how-do-developers-access-them)
- [Instagram API Documentation (GitHub)](https://github.com/Z786ZA/instagram-api-documentation)
- [Google Cloud Instagram Connector](https://docs.cloud.google.com/integration-connectors/docs/connectors/instagram/configure)
- [Instagram Graph API Python Tutorial (Video)](https://www.youtube.com/watch?v=4lsdOSfu64U)

---

**Last Updated:** February 2026

**Note:** Instagram API policies and authentication methods may change. Always refer to the official Meta for Developers documentation for the most current information.
