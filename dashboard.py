"""
Production dashboard server for Instagram Debate Bot.
Provides a web interface to review and manage generated responses.
"""
import os
import uuid
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, Response, JSONResponse

from src.file_utils import load_json_file, save_json_file
from src.config import Config
from src.token_extractor_factory import create_token_extractor
from src.audit_log_extractor_factory import create_audit_log_extractor
from src.audit_log_extractor import AuditLogExtractor
from src.mode_extractor_factory import create_mode_extractor
from src.mode_extractor import ModeExtractor
from src.article_extractor_factory import create_article_extractor
from src.article_extractor import ArticleExtractor
from src.prompt_extractor_factory import create_prompt_extractor
from src.prompt_extractor import PromptExtractor

# Configure dashboard logger
logger = logging.getLogger('dashboard')
logger.setLevel(logging.INFO)

# Add console handler if not already present
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def sanitize_log_input(value: str) -> str:
    """
    Sanitize user input for logging to prevent log injection attacks.
    Removes newlines and other control characters that could be used for log forging.
    
    Args:
        value: The user input to sanitize
        
    Returns:
        Sanitized string safe for logging
    """
    if not isinstance(value, str):
        value = str(value)
    # Replace newlines, carriage returns, and other control characters
    sanitized = value.replace('\n', '_').replace('\r', '_').replace('\t', '_')
    # Truncate to reasonable length to prevent log flooding
    return sanitized[:200]


def create_dashboard_app(state_dir: str = "state", audit_log_extractor: AuditLogExtractor = None, mode_extractor: ModeExtractor = None, article_extractor: ArticleExtractor = None, prompt_extractor: PromptExtractor = None) -> FastAPI:
    """
    Create a dashboard FastAPI application.

    Args:
        state_dir: Directory to store state files (default: "state").
            Used when no audit_log_extractor is provided and storage type is local disk.
        audit_log_extractor: Optional audit log extractor instance (defaults to factory-created)
        mode_extractor: Optional mode extractor instance (defaults to factory-created)
        article_extractor: Optional article extractor instance (defaults to factory-created)
        prompt_extractor: Optional prompt extractor instance (defaults to factory-created)

    Returns:
        FastAPI application instance
    """
    app = FastAPI()  # pylint: disable=redefined-outer-name
    
    # Use provided audit log extractor or create one via factory
    if audit_log_extractor is None:
        audit_log_extractor = create_audit_log_extractor(state_dir=state_dir)

    # Use provided mode extractor or create one via factory
    if mode_extractor is None:
        mode_extractor = create_mode_extractor()

    # Use provided article extractor or create one via factory
    if article_extractor is None:
        article_extractor = create_article_extractor(state_dir=state_dir)

    # Use provided prompt extractor or create one via factory
    if prompt_extractor is None:
        prompt_extractor = create_prompt_extractor(state_dir=state_dir)

    # ================== STATE MANAGEMENT ==================
    def load_audit_log():
        """Load audit log entries."""
        entries = audit_log_extractor.load_entries()
        return {"version": "1.0", "entries": entries}

    def update_audit_entry(entry_id: str, updates: dict):
        """Update a specific audit log entry."""
        audit_log_extractor.update_entry(entry_id, updates)

    # ================== DASHBOARD API ==================
    @app.get("/api/responses")
    async def get_responses():
        """Get all responses from audit log."""
        logger.info("GET /api/responses")
        audit_log = load_audit_log()
        response = JSONResponse(content={"responses": audit_log.get("entries", [])})
        return response

    @app.get("/api/responses/pending")
    async def get_pending_responses():
        """Get pending responses only."""
        logger.info("GET /api/responses/pending")
        audit_log = load_audit_log()
        entries = audit_log.get("entries", [])
        pending = [e for e in entries if e.get("status") == "pending_review"]
        response = JSONResponse(content={"responses": pending})
        return response

    @app.get("/api/responses/posted")
    async def get_posted_responses():
        """Get posted responses only."""
        logger.info("GET /api/responses/posted")
        audit_log = load_audit_log()
        entries = audit_log.get("entries", [])
        posted = [e for e in entries if e.get("posted", False)]
        response = JSONResponse(content={"responses": posted})
        return response

    @app.post("/api/responses/{response_id}/approve")
    async def approve_response(response_id: str):
        """Approve a response."""
        sanitized_id = sanitize_log_input(response_id)
        logger.info(f"POST /api/responses/{sanitized_id}/approve")
        audit_log = load_audit_log()
        entries = audit_log.get("entries", [])

        for entry in entries:
            if entry.get("id") == response_id:
                updates = {
                    "status": "approved",
                    "approved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }
                update_audit_entry(response_id, updates)
                logger.info(f"POST /api/responses/{sanitized_id}/approve - 200")
                response = JSONResponse(content={"status": "ok", "response_id": response_id})
                return response

        logger.warning(f"POST /api/responses/{sanitized_id}/approve - 404 Response not found")
        raise HTTPException(status_code=404, detail="Response not found")

    @app.post("/api/responses/{response_id}/reject")
    async def reject_response(response_id: str, request: Request):
        """Reject a response."""
        sanitized_id = sanitize_log_input(response_id)
        logger.info(f"POST /api/responses/{sanitized_id}/reject")
        data = await request.json()
        reason = data.get("reason", "No reason provided")

        audit_log = load_audit_log()
        entries = audit_log.get("entries", [])

        for entry in entries:
            if entry.get("id") == response_id:
                updates = {
                    "status": "rejected",
                    "rejected_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "rejection_reason": reason
                }
                update_audit_entry(response_id, updates)
                logger.info(f"POST /api/responses/{sanitized_id}/reject - 200")
                response = JSONResponse(content={"status": "ok", "response_id": response_id})
                return response

        logger.warning(f"POST /api/responses/{sanitized_id}/reject - 404 Response not found")
        raise HTTPException(status_code=404, detail="Response not found")

    @app.post("/api/responses/{response_id}/edit")
    async def edit_response(response_id: str, request: Request):
        """Edit a response."""
        sanitized_id = sanitize_log_input(response_id)
        logger.info(f"POST /api/responses/{sanitized_id}/edit")
        data = await request.json()
        new_text = data.get("text", "")

        audit_log = load_audit_log()
        entries = audit_log.get("entries", [])

        for entry in entries:
            if entry.get("id") == response_id:
                updates = {
                    "generated_response": new_text,
                    "edited_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }
                update_audit_entry(response_id, updates)
                logger.info(f"POST /api/responses/{sanitized_id}/edit - 200")
                response = JSONResponse(content={"status": "ok", "response_id": response_id})
                return response

        logger.warning(f"POST /api/responses/{sanitized_id}/edit - 404 Response not found")
        raise HTTPException(status_code=404, detail="Response not found")

    # ================== MODE EDITOR ENDPOINTS ==================
    @app.get("/api/mode")
    async def get_mode():
        """Get the current auto mode setting."""
        logger.info("GET /api/mode")
        auto_mode = mode_extractor.get_auto_mode()
        response = JSONResponse(content={"auto_mode": auto_mode})
        logger.info(f"GET /api/mode - 200 auto_mode={auto_mode}")
        return response

    @app.post("/api/mode")
    async def set_mode(request: Request):
        """Set the auto mode setting."""
        logger.info("POST /api/mode")
        data = await request.json()
        if "auto_mode" not in data or not isinstance(data["auto_mode"], bool):
            logger.warning("POST /api/mode - 400 Invalid or missing auto_mode field")
            raise HTTPException(status_code=400, detail="auto_mode field must be a boolean")
        auto_mode = data["auto_mode"]
        mode_extractor.set_auto_mode(auto_mode)
        response = JSONResponse(content={"status": "ok", "auto_mode": auto_mode})
        logger.info(f"POST /api/mode - 200 auto_mode={auto_mode}")
        return response

    # ================== ARTICLE MANAGER ENDPOINTS ==================
    @app.get("/api/articles")
    async def get_articles():
        """Get all articles."""
        logger.info("GET /api/articles")
        articles = article_extractor.get_articles()
        response = JSONResponse(content={"articles": articles})
        logger.info(f"GET /api/articles - 200 count={len(articles)}")
        return response

    @app.post("/api/articles")
    async def create_article(request: Request):
        """Create a new article."""
        logger.info("POST /api/articles")
        data = await request.json()
        title = data.get("title", "").strip()
        content = data.get("content", "").strip()
        link = data.get("link", "").strip()
        if not title:
            logger.warning("POST /api/articles - 400 Missing title")
            raise HTTPException(status_code=400, detail="title field is required")
        if not content:
            logger.warning("POST /api/articles - 400 Missing content")
            raise HTTPException(status_code=400, detail="content field is required")
        article_id = str(uuid.uuid4())
        article_extractor.save_article(article_id, title, content, link)
        logger.info(f"POST /api/articles - 200 article_id={article_id}")
        return JSONResponse(content={"status": "ok", "article_id": article_id})

    @app.put("/api/articles/{article_id}")
    async def update_article(article_id: str, request: Request):
        """Update an existing article."""
        sanitized_id = sanitize_log_input(article_id)
        logger.info(f"PUT /api/articles/{sanitized_id}")
        existing = article_extractor.get_article(article_id)
        if existing is None:
            logger.warning(f"PUT /api/articles/{sanitized_id} - 404 Article not found")
            raise HTTPException(status_code=404, detail="Article not found")
        data = await request.json()
        title = data.get("title", existing.get("title", "")).strip()
        content = data.get("content", existing.get("content", "")).strip()
        link = data.get("link", existing.get("link", "")).strip()
        article_extractor.save_article(article_id, title, content, link)
        logger.info(f"PUT /api/articles/{sanitized_id} - 200")
        return JSONResponse(content={"status": "ok", "article_id": article_id})

    @app.delete("/api/articles/{article_id}")
    async def delete_article(article_id: str):
        """Delete an article."""
        sanitized_id = sanitize_log_input(article_id)
        logger.info(f"DELETE /api/articles/{sanitized_id}")
        deleted = article_extractor.delete_article(article_id)
        if not deleted:
            logger.warning(f"DELETE /api/articles/{sanitized_id} - 404 Article not found")
            raise HTTPException(status_code=404, detail="Article not found")
        logger.info(f"DELETE /api/articles/{sanitized_id} - 200")
        return JSONResponse(content={"status": "ok", "article_id": article_id})

    # ================== PROMPT EDITOR ENDPOINTS ==================
    @app.get("/api/prompts")
    async def get_prompts():
        """Get all stored prompt templates."""
        logger.info("GET /api/prompts")
        prompts = prompt_extractor.get_all_prompts()
        response = JSONResponse(content={"prompts": prompts})
        logger.info(f"GET /api/prompts - 200 count={len(prompts)}")
        return response

    @app.get("/api/prompts/{name}")
    async def get_prompt(name: str):
        """Get a single prompt template by name."""
        sanitized_name = sanitize_log_input(name)
        logger.info(f"GET /api/prompts/{sanitized_name}")
        content = prompt_extractor.get_prompt(name)
        response = JSONResponse(content={"name": name, "content": content})
        logger.info(f"GET /api/prompts/{sanitized_name} - 200")
        return response

    @app.put("/api/prompts/{name}")
    async def set_prompt(name: str, request: Request):
        """Create or update a prompt template by name."""
        sanitized_name = sanitize_log_input(name)
        logger.info(f"PUT /api/prompts/{sanitized_name}")
        data = await request.json()
        if "content" not in data:
            logger.warning(f"PUT /api/prompts/{sanitized_name} - 400 Missing content field")
            raise HTTPException(status_code=400, detail="content field is required")
        content = data["content"]
        prompt_extractor.set_prompt(name, content)
        response = JSONResponse(content={"status": "ok", "name": name})
        logger.info(f"PUT /api/prompts/{sanitized_name} - 200")
        return response

    # ================== OAUTH ENDPOINTS ==================
    # Initialize config
    config = Config()
    
    # Store OAuth state with timestamps (in production, use session storage or Redis)
    oauth_states = {}
    
    def cleanup_expired_states():
        """Remove OAuth states older than 10 minutes."""
        import time
        current_time = time.time()
        expired = [state for state, timestamp in oauth_states.items() 
                   if current_time - timestamp > 600]  # 10 minutes
        for state in expired:
            del oauth_states[state]
    
    @app.get("/auth/instagram/login")
    async def instagram_oauth_login():
        """
        Initiate Instagram OAuth flow for Business accounts.
        Redirects user to Instagram authorization page with business scopes.
        Uses www.instagram.com endpoint as per Facebook documentation.
        """
        logger.info("GET /auth/instagram/login")
        import time
        
        # Clean up expired states
        cleanup_expired_states()
        
        # Generate CSRF state with timestamp
        state = secrets.token_urlsafe(32)
        oauth_states[state] = time.time()
        
        # Build OAuth URL with business scopes
        # Using www.instagram.com endpoint for Instagram Business/Graph API
        print("Redirect URL: ", config.instagram_redirect_uri)
        params = {
            'force_reauth': 'true',  # String 'true' required by Instagram OAuth API
            'client_id': config.instagram_client_id,
            'redirect_uri': config.instagram_redirect_uri,
            'response_type': 'code',
            # Instagram Login supports instagram_business_* scopes only.
            'scope': 'instagram_business_basic,instagram_business_manage_comments',
            'state': state
        }
        print("OAuth Params: ", params)
        
        oauth_url = f"https://www.instagram.com/oauth/authorize?{urlencode(params)}"
        
        logger.info("GET /auth/instagram/login - 307 Redirecting to Instagram OAuth")
        return RedirectResponse(url=oauth_url, status_code=307)

    @app.get("/auth/instagram/callback")
    async def instagram_oauth_callback(code: str = None, state: str = None):
        """
        Handle OAuth callback from Instagram.
        Exchange authorization code for short-lived token,
        then exchange for long-lived token and store.
        
        Args:
            code: Authorization code from Instagram
            state: CSRF protection state parameter
        """
        logger.info("GET /auth/instagram/callback")
        # Validate required parameters
        if not code:
            logger.error("GET /auth/instagram/callback - 400 Missing authorization code")
            raise HTTPException(status_code=400, detail="Missing authorization code")
        
        if not state or state not in oauth_states:
            logger.error("GET /auth/instagram/callback - 400 Invalid state parameter")
            raise HTTPException(status_code=400, detail="Invalid state parameter (CSRF protection)")
        
        # Remove used state
        del oauth_states[state]
        
        try:
            # Step 1: Exchange code for short-lived token
            short_lived_data = exchange_code_for_token(
                code=code,
                client_id=config.instagram_client_id,
                client_secret=config.instagram_client_secret,
                redirect_uri=config.instagram_redirect_uri
            )
            
            if not short_lived_data:
                logger.error("GET /auth/instagram/callback - 400 Failed to exchange authorization code")
                raise HTTPException(status_code=400, detail="Failed to exchange authorization code")
            
            # Step 2: Exchange short-lived token for long-lived token
            long_lived_data = exchange_for_long_lived_token(
                short_lived_token=short_lived_data['access_token'],
                client_secret=config.instagram_client_secret
            )
            
            if not long_lived_data:
                logger.error("GET /auth/instagram/callback - 400 Failed to get long-lived token")
                raise HTTPException(status_code=400, detail="Failed to get long-lived token")
            
            # Step 3: Store long-lived token
            token_extractor = create_token_extractor()
            token_extractor.save_token(
                access_token=long_lived_data['access_token'],
                token_type=long_lived_data.get('token_type', 'bearer'),
                expires_in=long_lived_data.get('expires_in', 5184000),
                user_id=short_lived_data.get('user_id'),
                username=short_lived_data.get('username')
            )

            # Step 4: Subscribe this account to webhook events
            subscribed = subscribe_instagram_webhooks(
                access_token=long_lived_data['access_token']
            )
            if not subscribed:
                logger.error("GET /auth/instagram/callback - 400 Failed to subscribe webhook events")
                raise HTTPException(status_code=400, detail="Failed to subscribe webhook events")
            
            # Redirect to dashboard
            logger.info("GET /auth/instagram/callback - 303 OAuth successful, redirecting to dashboard")
            return RedirectResponse(url="/", status_code=303)
            
        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:  # pylint: disable=broad-except
            # Log generic error without sensitive details
            logger.error("GET /auth/instagram/callback - 500 OAuth flow failed")
            raise HTTPException(status_code=500, detail="OAuth authentication failed") from e

    @app.get("/auth/instagram/logout")
    async def instagram_oauth_logout():
        """
        Clear user session and logout.
        Removes stored token and clears session.
        """
        logger.info("GET /auth/instagram/logout")
        token_extractor = create_token_extractor()
        token_data = token_extractor.get_token()

        # Unsubscribe account-level webhooks before clearing local token
        if token_data and token_data.get('access_token'):
            unsubscribed = unsubscribe_instagram_webhooks(token_data['access_token'])
            if not unsubscribed:
                logger.error("GET /auth/instagram/logout - 502 Failed to unsubscribe webhook events")
                raise HTTPException(status_code=502, detail="Failed to unsubscribe webhook events")

        token_extractor.clear_token()
        logger.info("GET /auth/instagram/logout - 303 Token cleared, redirecting to dashboard")
        return RedirectResponse(url="/", status_code=303)

    # Helper functions for OAuth
    def exchange_code_for_token(
        code: str, 
        client_id: str, 
        client_secret: str, 
        redirect_uri: str
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for short-lived access token.
        
        Args:
            code: Authorization code from Instagram
            client_id: Instagram client ID
            client_secret: Instagram client secret
            redirect_uri: Registered redirect URI
            
        Returns:
            Dictionary with token data (access_token, user_id, permissions) or None if failed
        """
        try:
            response = requests.post(
                'https://api.instagram.com/oauth/access_token',
                data={
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'grant_type': 'authorization_code',
                    'redirect_uri': redirect_uri,
                    'code': code
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Token exchange response: {data}")
                # Instagram API returns data wrapped in a 'data' array
                # Extract and return the first element
                if 'data' in data and len(data['data']) > 0:
                    return data['data'][0]
                # Fallback if format is different
                return data
            else:
                logger.error(f"Token exchange failed with status {response.status_code}: {response.text}")
            return None
        except requests.RequestException as e:
            logger.error(f"Token exchange request failed: {e}")
            return None

    def exchange_for_long_lived_token(
        short_lived_token: str, 
        client_secret: str
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange short-lived token for long-lived token (60 days).
        
        Args:
            short_lived_token: Short-lived access token
            client_secret: Instagram client secret
            
        Returns:
            Dictionary with long-lived token data or None if failed
        """
        try:
            response = requests.post(
                'https://graph.instagram.com/access_token',
                data={
                    'grant_type': 'ig_exchange_token',
                    'client_secret': client_secret,
                    'access_token': short_lived_token
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Long-lived token exchange successful: expires_in={data.get('expires_in')}")
                return data
            else:
                logger.error(f"Long-lived token exchange failed with status {response.status_code}: {response.text}")
            return None
        except requests.RequestException as e:
            logger.error(f"Long-lived token exchange request failed: {e}")
            return None

    def subscribe_instagram_webhooks(access_token: str) -> bool:
        """
        Subscribe the logged-in Instagram account to app webhooks.

        Args:
            access_token: Long-lived access token

        Returns:
            True when subscription succeeds, False otherwise
        """
        if not access_token:
            return False

        try:
            response = requests.post(
                'https://graph.instagram.com/v25.0/me/subscribed_apps',
                data={
                    'subscribed_fields': 'comments,mentions',
                    'access_token': access_token
                },
                timeout=30
            )

            return response.status_code == 200
        except requests.RequestException:
            return False

    def unsubscribe_instagram_webhooks(access_token: str) -> bool:
        """
        Unsubscribe the logged-in Instagram account from app webhooks.

        Args:
            access_token: Long-lived access token

        Returns:
            True when unsubscription succeeds, False otherwise
        """
        if not access_token:
            return False

        try:
            response = requests.delete(
                'https://graph.instagram.com/v25.0/me/subscribed_apps',
                params={
                    'access_token': access_token
                },
                timeout=30
            )

            return response.status_code == 200
        except requests.RequestException:
            return False

    # ================== DASHBOARD UI ==================
    @app.get("/", response_class=HTMLResponse)
    async def dashboard_home():
        """Dashboard home page."""
        logger.info("GET /")
        # Check if user is authenticated
        token_extractor = create_token_extractor()
        token_data = token_extractor.get_token()
        is_authenticated = token_data is not None and not token_extractor.is_token_expired()
        
        # Build auth section HTML
        if is_authenticated:
            username = token_data.get('username', 'User')
            user_id = token_data.get('user_id', 'N/A')
            auth_section = f"""
                <div class="auth-info">
                    <span class="auth-status authenticated">✓ Authenticated</span>
                    <span class="user-info">@{username} (ID: {user_id})</span>
                    <a href="/auth/instagram/logout" class="btn-logout">Logout</a>
                </div>
            """
        else:
            auth_section = """
                <div class="auth-info">
                    <span class="auth-status not-authenticated">⚠ Not Authenticated</span>
                    <a href="/auth/instagram/login" class="btn-login">Login with Instagram</a>
                </div>
            """
        
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Debate Bot - Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
        }

        .header {
            background: #fff;
            border-bottom: 1px solid #ddd;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 1.5rem;
            color: #333;
        }

        .auth-info {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .auth-status {
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 600;
        }

        .auth-status.authenticated {
            background: #d4edda;
            color: #155724;
        }

        .auth-status.not-authenticated {
            background: #fff3cd;
            color: #856404;
        }

        .user-info {
            font-size: 0.875rem;
            color: #666;
        }

        .btn-login, .btn-logout {
            padding: 0.5rem 1.5rem;
            border-radius: 4px;
            text-decoration: none;
            font-size: 0.875rem;
            font-weight: 600;
            transition: all 0.2s;
        }

        .btn-login {
            background: #0095f6;
            color: #fff;
        }

        .btn-login:hover {
            background: #007cc2;
        }

        .btn-logout {
            background: #6c757d;
            color: #fff;
        }

        .btn-logout:hover {
            background: #5a6268;
        }

        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }

        .filters {
            background: #fff;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .filter-buttons {
            display: flex;
            gap: 0.5rem;
        }

        .filter-btn {
            padding: 0.5rem 1rem;
            border: 1px solid #ddd;
            background: #fff;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .filter-btn:hover {
            background: #f5f5f5;
        }

        .filter-btn.active {
            background: #007bff;
            color: #fff;
            border-color: #007bff;
        }

        .response-card {
            background: #fff;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .response-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .response-meta {
            flex: 1;
        }

        .response-id {
            font-size: 0.875rem;
            color: #666;
            font-weight: 500;
        }

        .response-status {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-top: 0.5rem;
        }

        .status-pending_review {
            background: #fff3cd;
            color: #856404;
        }

        .status-approved {
            background: #d4edda;
            color: #155724;
        }

        .status-rejected {
            background: #f8d7da;
            color: #721c24;
        }

        .response-section {
            margin-bottom: 1rem;
        }

        .response-section h3 {
            font-size: 0.875rem;
            color: #666;
            margin-bottom: 0.5rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .comment-text {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            border-left: 3px solid #007bff;
            font-size: 0.95rem;
            line-height: 1.5;
        }

        .generated-response {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            border-left: 3px solid #28a745;
            font-size: 0.95rem;
            line-height: 1.6;
            white-space: pre-wrap;
        }

        .editable-response {
            width: 100%;
            min-height: 150px;
            padding: 1rem;
            border: 2px solid #007bff;
            border-radius: 4px;
            font-family: inherit;
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .citations {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .citation-tag {
            background: #e9ecef;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.875rem;
            color: #495057;
        }

        .actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 1rem;
        }

        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            transition: all 0.2s;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .btn-approve {
            background: #28a745;
            color: #fff;
        }

        .btn-reject {
            background: #dc3545;
            color: #fff;
        }

        .btn-edit {
            background: #007bff;
            color: #fff;
        }

        .btn-cancel {
            background: #6c757d;
            color: #fff;
        }

        .btn-save {
            background: #28a745;
            color: #fff;
        }

        .btn-article-save {
            background: #28a745;
            color: #fff;
        }

        .rejection-form {
            margin-top: 1rem;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 4px;
        }

        .rejection-form textarea {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            min-height: 80px;
            font-family: inherit;
        }

        .rejection-form .actions {
            margin-top: 0.5rem;
        }

        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #666;
        }

        .empty-state-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }

        .mode-toggle-section {
            background: #fff;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .mode-toggle-label {
            font-size: 0.9rem;
            font-weight: 600;
            color: #333;
        }

        .mode-toggle {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .mode-toggle input[type="checkbox"] {
            width: 44px;
            height: 24px;
            appearance: none;
            background: #ccc;
            border-radius: 12px;
            cursor: pointer;
            position: relative;
            transition: background 0.2s;
        }

        .mode-toggle input[type="checkbox"]:checked {
            background: #28a745;
        }

        .mode-toggle input[type="checkbox"]::after {
            content: '';
            position: absolute;
            width: 20px;
            height: 20px;
            background: #fff;
            border-radius: 50%;
            top: 2px;
            left: 2px;
            transition: left 0.2s;
        }

        .mode-toggle input[type="checkbox"]:checked::after {
            left: 22px;
        }

        .mode-status {
            font-size: 0.875rem;
            font-weight: 600;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
        }

        .mode-status.auto {
            background: #d4edda;
            color: #155724;
        }

        .mode-status.manual {
            background: #fff3cd;
            color: #856404;
        }

        .article-manager-section {
            background: #fff;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .article-manager-section h2 {
            font-size: 1.1rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 1rem;
        }

        .article-list {
            list-style: none;
            margin-bottom: 1rem;
        }

        .article-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 1rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 0.5rem;
            background: #f8f9fa;
        }

        .article-item-title {
            font-weight: 500;
            font-size: 0.95rem;
            color: #333;
            flex: 1;
        }

        .article-item-link {
            font-size: 0.8rem;
            color: #666;
            margin-left: 1rem;
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .article-item-actions {
            display: flex;
            gap: 0.5rem;
            margin-left: 1rem;
        }

        .btn-add-article {
            background: #28a745;
            color: #fff;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
        }

        .article-form {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 1rem;
            margin-top: 1rem;
            background: #f8f9fa;
            display: none;
        }

        .article-form.active {
            display: block;
        }

        .article-form input,
        .article-form textarea {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: inherit;
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
        }

        .article-form textarea {
            min-height: 120px;
            resize: vertical;
        }

        .article-form label {
            font-size: 0.875rem;
            font-weight: 500;
            color: #555;
            display: block;
            margin-bottom: 0.25rem;
        }

        .prompt-editor-section {
            background: #fff;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .prompt-editor-section h2 {
            font-size: 1.1rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 1rem;
        }

        .prompt-list {
            list-style: none;
            margin-bottom: 1rem;
        }

        .prompt-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 1rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 0.5rem;
            background: #f8f9fa;
        }

        .prompt-item-name {
            font-weight: 500;
            font-size: 0.95rem;
            color: #333;
            flex: 1;
            font-family: monospace;
        }

        .prompt-item-actions {
            display: flex;
            gap: 0.5rem;
            margin-left: 1rem;
        }

        .prompt-form {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 1rem;
            margin-top: 1rem;
            background: #f8f9fa;
            display: none;
        }

        .prompt-form.active {
            display: block;
        }

        .prompt-form input,
        .prompt-form textarea {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.85rem;
            margin-bottom: 0.75rem;
        }

        .prompt-form textarea {
            min-height: 200px;
            resize: vertical;
        }

        .prompt-form label {
            font-size: 0.875rem;
            font-weight: 500;
            color: #555;
            display: block;
            margin-bottom: 0.25rem;
        }

        .btn-prompt-save {
            background: #28a745;
            color: #fff;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Instagram Debate Bot Dashboard</h1>
        """ + auth_section + """
    </div>

    <div class="container">
        <div class="mode-toggle-section">
            <span class="mode-toggle-label">Auto Mode:</span>
            <div class="mode-toggle">
                <input type="checkbox" id="auto-mode-toggle" onchange="toggleAutoMode(this.checked)">
                <span class="mode-status manual" id="mode-status-label">Manual</span>
            </div>
        </div>

        <div class="article-manager-section" id="article-manager">
            <h2>📄 Article Manager</h2>
            <ul class="article-list" id="article-list">
                <!-- Articles will be loaded here -->
            </ul>
            <button class="btn btn-add-article" onclick="showAddArticleForm()">+ Add Article</button>
            <div class="article-form" id="article-form">
                <input type="hidden" id="article-form-id" value="">
                <label for="article-form-title">Title</label>
                <input type="text" id="article-form-title" placeholder="Article title">
                <label for="article-form-link">Link (URL)</label>
                <input type="text" id="article-form-link" placeholder="https://example.com/article">
                <label for="article-form-content">Content (Markdown)</label>
                <textarea id="article-form-content" placeholder="# Article content..."></textarea>
                <div class="actions">
                    <button class="btn btn-article-save" onclick="submitArticleForm()">Save</button>
                    <button class="btn btn-cancel" onclick="hideArticleForm()">Cancel</button>
                </div>
            </div>
        </div>

        <div class="prompt-editor-section" id="prompt-editor">
            <h2>✏️ Prompt Editor</h2>
            <ul class="prompt-list" id="prompt-list">
                <!-- Prompts will be loaded here -->
            </ul>
            <div class="prompt-form" id="prompt-form">
                <input type="hidden" id="prompt-form-name" value="">
                <label for="prompt-form-name-display">Prompt Name</label>
                <input type="text" id="prompt-form-name-display" placeholder="e.g. debate_prompt" readonly>
                <label for="prompt-form-content">Content</label>
                <textarea id="prompt-form-content" placeholder="Enter prompt template content..."></textarea>
                <div class="actions">
                    <button class="btn btn-prompt-save" onclick="submitPromptForm()">Save</button>
                    <button class="btn btn-cancel" onclick="hidePromptForm()">Cancel</button>
                </div>
            </div>
        </div>

        <div class="filters">
            <div class="filter-buttons">
                <button class="filter-btn active" data-filter="pending_review">Pending Review</button>
                <button class="filter-btn" data-filter="approved">Approved</button>
                <button class="filter-btn" data-filter="rejected">Rejected</button>
                <button class="filter-btn" data-filter="posted">Posted</button>
                <button class="filter-btn" data-filter="all">All</button>
            </div>
        </div>

        <div id="responses-container">
            <!-- Responses will be loaded here -->
        </div>
    </div>

    <script>
        let currentFilter = 'pending_review';
        let responses = [];
        let editingId = null;

        // Load responses
        async function loadResponses() {
            if (editingId !== null) {
                return;
            }
            try {
                const response = await fetch('/api/responses');
                const data = await response.json();
                responses = data.responses;
                renderResponses();
            } catch (error) {
                console.error('Error loading responses:', error);
            }
        }

        // Filter responses
        function getFilteredResponses() {
            if (currentFilter === 'all') {
                return responses;
            }
            if (currentFilter === 'posted') {
                return responses.filter(r => r.posted === true);
            }
            if (currentFilter === 'approved') {
                return responses.filter(r => r.status === 'approved' && !r.posted);
            }
            return responses.filter(r => r.status === currentFilter);
        }

        // Render responses
        function renderResponses() {
            const container = document.getElementById('responses-container');
            const filtered = getFilteredResponses();

            if (filtered.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <p>No responses found</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = filtered.map(response => `
                <div class="response-card" data-id="${response.id}">
                    <div class="response-header">
                        <div class="response-meta">
                            <div class="response-id">${response.id}</div>
                            <span class="response-status status-${response.status}">${response.status.replace('_', ' ')}</span>
                        </div>
                    </div>

                    <div class="response-section">
                        <h3>Original Comment</h3>
                        <div class="comment-text">${escapeHtml(response.comment_text || 'N/A')}</div>
                    </div>

                    <div class="response-section">
                        <h3>Generated Response</h3>
                        <div class="generated-response" data-response-id="${response.id}">${escapeHtml(response.generated_response || 'N/A')}</div>
                        <textarea class="editable-response" data-response-id="${response.id}" style="display: none;">${escapeHtml(response.generated_response || '')}</textarea>
                    </div>

                    ${response.citations_used && response.citations_used.length > 0 ? `
                    <div class="response-section">
                        <h3>Citations Used</h3>
                        <div class="citations">
                            ${response.citations_used.map(c => `<span class="citation-tag">${escapeHtml(c)}</span>`).join('')}
                        </div>
                    </div>
                    ` : ''}

                    ${response.status === 'pending_review' ? `
                    <div class="actions" id="main-actions-${response.id}">
                        <button class="btn btn-approve" onclick="approveResponse('${response.id}')">Approve</button>
                        <button class="btn btn-reject" onclick="showRejectForm('${response.id}')">Reject</button>
                        <button class="btn btn-edit" onclick="editResponse('${response.id}')">Edit</button>
                    </div>
                    <div class="rejection-form" id="reject-form-${response.id}" style="display: none;">
                        <textarea placeholder="Reason for rejection..." id="reject-reason-${response.id}"></textarea>
                        <div class="actions">
                            <button class="btn btn-reject btn-confirm-reject" onclick="confirmReject('${response.id}')">Confirm Reject</button>
                            <button class="btn btn-cancel" onclick="hideRejectForm('${response.id}')">Cancel</button>
                        </div>
                    </div>
                    ` : ''}

                    ${response.status === 'rejected' && response.rejection_reason ? `
                    <div class="response-section">
                        <h3>Rejection Reason</h3>
                        <div class="comment-text">${escapeHtml(response.rejection_reason)}</div>
                    </div>
                    ` : ''}

                    ${response.posted ? `
                    <div class="response-section">
                        <h3>Posted Comment ID</h3>
                        <div class="comment-text">${escapeHtml(response.comment_id || 'N/A')}</div>
                    </div>
                    ` : ''}
                </div>
            `).join('');
        }

        // Escape HTML
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Approve response
        async function approveResponse(id) {
            try {
                const response = await fetch(`/api/responses/${id}/approve`, {
                    method: 'POST'
                });
                if (response.ok) {
                    await loadResponses();
                }
            } catch (error) {
                console.error('Error approving response:', error);
            }
        }

        // Show reject form
        function showRejectForm(id) {
            document.getElementById(`reject-form-${id}`).style.display = 'block';
        }

        // Hide reject form
        function hideRejectForm(id) {
            document.getElementById(`reject-form-${id}`).style.display = 'none';
        }

        // Confirm reject
        async function confirmReject(id) {
            const reason = document.getElementById(`reject-reason-${id}`).value;
            try {
                const response = await fetch(`/api/responses/${id}/reject`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({reason})
                });
                if (response.ok) {
                    await loadResponses();
                }
            } catch (error) {
                console.error('Error rejecting response:', error);
            }
        }

        // Edit response
        function editResponse(id) {
            editingId = id;
            const responseDiv = document.querySelector(`.generated-response[data-response-id="${id}"]`);
            const textarea = document.querySelector(`.editable-response[data-response-id="${id}"]`);
            const card = document.querySelector(`.response-card[data-id="${id}"]`);

            responseDiv.style.display = 'none';
            textarea.style.display = 'block';

            // Update actions
            const actionsDiv = card.querySelector('.actions');
            actionsDiv.innerHTML = `
                <button class="btn btn-save" onclick="saveEdit('${id}')">Save</button>
                <button class="btn btn-cancel" onclick="cancelEdit('${id}')">Cancel</button>
            `;
        }

        // Save edit
        async function saveEdit(id) {
            const textarea = document.querySelector(`.editable-response[data-response-id="${id}"]`);
            const newText = textarea.value;

            try {
                const response = await fetch(`/api/responses/${id}/edit`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: newText})
                });
                if (response.ok) {
                    editingId = null;
                    await loadResponses();
                }
            } catch (error) {
                console.error('Error saving edit:', error);
            }
        }

        // Cancel edit
        function cancelEdit(id) {
            editingId = null;
            loadResponses();
        }

        // Load and display current auto mode
        async function loadMode() {
            try {
                const response = await fetch('/api/mode');
                const data = await response.json();
                const toggle = document.getElementById('auto-mode-toggle');
                const label = document.getElementById('mode-status-label');
                if (toggle && label) {
                    toggle.checked = data.auto_mode;
                    label.textContent = data.auto_mode ? 'Auto' : 'Manual';
                    label.className = 'mode-status ' + (data.auto_mode ? 'auto' : 'manual');
                }
            } catch (error) {
                console.error('Error loading mode:', error);
            }
        }

        // Toggle auto mode
        async function toggleAutoMode(enabled) {
            try {
                const response = await fetch('/api/mode', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({auto_mode: enabled})
                });
                const data = await response.json();
                const label = document.getElementById('mode-status-label');
                if (label) {
                    label.textContent = data.auto_mode ? 'Auto' : 'Manual';
                    label.className = 'mode-status ' + (data.auto_mode ? 'auto' : 'manual');
                }
            } catch (error) {
                console.error('Error toggling mode:', error);
            }
        }

        // ================== ARTICLE MANAGER ==================
        // Cache article data by ID to avoid HTML attribute escaping issues
        let _articleDataMap = {};

        async function loadArticles() {
            try {
                const response = await fetch('/api/articles');
                const data = await response.json();
                renderArticles(data.articles);
            } catch (error) {
                console.error('Error loading articles:', error);
            }
        }

        function renderArticles(articles) {
            const list = document.getElementById('article-list');
            if (!list) return;
            _articleDataMap = {};
            articles.forEach(a => { _articleDataMap[a.id] = a; });
            if (articles.length === 0) {
                list.innerHTML = '<li style="color:#888;font-size:0.9rem;">No articles yet.</li>';
                return;
            }
            list.innerHTML = articles.map(article => `
                <li class="article-item" data-article-id="${escapeHtml(article.id)}">
                    <span class="article-item-title">${escapeHtml(article.title)}</span>
                    <span class="article-item-link">${escapeHtml(article.link || '')}</span>
                    <div class="article-item-actions">
                        <button class="btn btn-edit" onclick="editArticleFromItem(this)">Edit</button>
                        <button class="btn btn-reject" onclick="deleteArticleFromItem(this)">Delete</button>
                    </div>
                </li>
            `).join('');
        }

        function showAddArticleForm() {
            document.getElementById('article-form-id').value = '';
            document.getElementById('article-form-title').value = '';
            document.getElementById('article-form-link').value = '';
            document.getElementById('article-form-content').value = '';
            document.getElementById('article-form').classList.add('active');
        }

        function hideArticleForm() {
            document.getElementById('article-form').classList.remove('active');
        }

        function editArticleFromItem(btn) {
            const li = btn.closest('.article-item');
            const id = li.dataset.articleId;
            const article = _articleDataMap[id] || {};
            document.getElementById('article-form-id').value = id;
            document.getElementById('article-form-title').value = article.title || '';
            document.getElementById('article-form-link').value = article.link || '';
            document.getElementById('article-form-content').value = article.content || '';
            document.getElementById('article-form').classList.add('active');
        }

        function deleteArticleFromItem(btn) {
            const id = btn.closest('.article-item').dataset.articleId;
            deleteArticle(id);
        }

        async function submitArticleForm() {
            const id = document.getElementById('article-form-id').value;
            const title = document.getElementById('article-form-title').value;
            const link = document.getElementById('article-form-link').value;
            const content = document.getElementById('article-form-content').value;
            try {
                let resp;
                if (id) {
                    resp = await fetch(`/api/articles/${id}`, {
                        method: 'PUT',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({title, content, link})
                    });
                } else {
                    resp = await fetch('/api/articles', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({title, content, link})
                    });
                }
                if (resp.ok) {
                    hideArticleForm();
                    await loadArticles();
                } else {
                    const err = await resp.json();
                    alert('Error: ' + (err.detail || 'Failed to save article'));
                }
            } catch (error) {
                console.error('Error saving article:', error);
            }
        }

        async function deleteArticle(id) {
            if (!confirm('Delete this article?')) return;
            try {
                const resp = await fetch(`/api/articles/${id}`, {method: 'DELETE'});
                if (resp.ok) {
                    await loadArticles();
                }
            } catch (error) {
                console.error('Error deleting article:', error);
            }
        }

        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.filter;
                renderResponses();
            });
        });

        // Initial load
        loadResponses();
        loadMode();
        loadArticles();
        loadPrompts();

        // Auto-refresh every 5 seconds
        setInterval(loadResponses, 5000);

        // ================== PROMPT EDITOR ==================
        async function loadPrompts() {
            try {
                const response = await fetch('/api/prompts');
                const data = await response.json();
                renderPrompts(data.prompts);
            } catch (error) {
                console.error('Error loading prompts:', error);
            }
        }

        function renderPrompts(prompts) {
            const list = document.getElementById('prompt-list');
            if (!list) return;
            const names = Object.keys(prompts);
            if (names.length === 0) {
                list.innerHTML = '<li style="color:#888;font-size:0.9rem;">No custom prompts stored. Click a prompt name to edit it.</li>';
            } else {
                list.innerHTML = names.map(name => `
                    <li class="prompt-item" data-prompt-name="${escapeHtml(name)}">
                        <span class="prompt-item-name">${escapeHtml(name)}</span>
                        <div class="prompt-item-actions">
                            <button class="btn btn-edit" onclick="editPromptFromItem(this)">Edit</button>
                        </div>
                    </li>
                `).join('');
            }
        }

        function editPromptFromItem(btn) {
            const li = btn.closest('.prompt-item');
            const name = li.dataset.promptName;
            showPromptForm(name);
        }

        async function showPromptForm(name) {
            document.getElementById('prompt-form-name').value = name || '';
            document.getElementById('prompt-form-name-display').value = name || '';
            document.getElementById('prompt-form-content').value = '';
            document.getElementById('prompt-form').classList.add('active');
            if (name) {
                try {
                    const response = await fetch(`/api/prompts/${encodeURIComponent(name)}`);
                    const data = await response.json();
                    document.getElementById('prompt-form-content').value = data.content || '';
                } catch (error) {
                    console.error('Error loading prompt:', error);
                }
            }
        }

        function hidePromptForm() {
            document.getElementById('prompt-form').classList.remove('active');
        }

        async function submitPromptForm() {
            const name = document.getElementById('prompt-form-name').value || document.getElementById('prompt-form-name-display').value;
            const content = document.getElementById('prompt-form-content').value;
            if (!name) {
                alert('Prompt name is required');
                return;
            }
            try {
                const resp = await fetch(`/api/prompts/${encodeURIComponent(name)}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({content})
                });
                if (resp.ok) {
                    hidePromptForm();
                    await loadPrompts();
                } else {
                    const err = await resp.json();
                    alert('Error: ' + (err.detail || 'Failed to save prompt'));
                }
            } catch (error) {
                console.error('Error saving prompt:', error);
            }
        }
    </script>
</body>
</html>
    """
        return HTMLResponse(content=html_content)

    @app.get("/privacy", response_class=PlainTextResponse)
    async def privacy_policy():
        """Return plain text privacy policy."""
        privacy_text = """Privacy Policy for [Your Instagram Bot Name]
Last Updated: [Date]

This Privacy Policy explains how [Your Instagram Bot Name] (“we,” “our,” or “the bot”) collects, uses, and protects information when you use our Instagram automation service.

1. Information We Collect
1.1 User-Provided Information
- Instagram username or ID
- Messages or commands sent to the bot
- Any data voluntarily provided for the bot to function

1.2 Automatically Collected Data
- Basic Instagram profile data allowed by Instagram’s API
- Usage logs such as command history and timestamps
- Technical information such as IP address or device type (if applicable)
We do not collect passwords or sensitive authentication data.

2. How We Use the Information
- Operate and improve the bot’s functionality
- Respond to user commands or messages
- Provide features such as analytics, automated actions, or notifications
- Maintain performance and security
We do not sell, rent, or trade user data.

3. Data Storage and Security
- Data is stored securely and only as long as necessary to provide the service.
- We take reasonable measures to protect information from unauthorized access or misuse.
- Users may request deletion of their data at any time.

4. Sharing of Information
We do not share personal data except:
- With service providers necessary to operate the bot (e.g., hosting services)
- If required by law or legal process
- To prevent fraud, abuse, or security threats

5. Third-Party Services
This bot interacts with Instagram and may rely on external APIs or platforms. Use of those services is governed by their own privacy policies.

6. User Rights
Users may:
- Request access to stored data
- Request deletion of their data
- Stop using the bot at any time
Contact: [Your Contact Email]

7. Children’s Privacy
This bot is not intended for children under 13, and we do not knowingly collect information from minors.

8. Changes to This Policy
We may update this Privacy Policy from time to time. Updates will be posted with a new “Last Updated” date.

9. Contact
For questions about this Privacy Policy, contact: [Your Contact Email]"""
        return PlainTextResponse(content=privacy_text)

    return app


# Create the default app instance for production use
app = create_dashboard_app()


if __name__ == "__main__":
    import uvicorn
    import sys
    from src.config import Config

    config = Config()

    # Allow command-line argument to override environment variable
    port = config.dashboard_port
    host = config.dashboard_host

    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)

    print(f"Starting Instagram Debate Bot Dashboard on http://{host}:{port}")
    print(f"State directory: {os.path.abspath('state')}")
    print("Press Ctrl+C to stop")

    uvicorn.run(app, host=host, port=port, log_level="info")
