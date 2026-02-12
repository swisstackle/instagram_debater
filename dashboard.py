"""
Production dashboard server for Instagram Debate Bot.
Provides a web interface to review and manage generated responses.
"""
import os
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from src.file_utils import load_json_file, save_json_file
from src.config import Config
from src.token_manager import TokenManager


def create_dashboard_app(state_dir: str = "state") -> FastAPI:
    """
    Create a dashboard FastAPI application.

    Args:
        state_dir: Directory to store state files (default: "state")

    Returns:
        FastAPI application instance
    """
    app = FastAPI()  # pylint: disable=redefined-outer-name

    # ================== STATE MANAGEMENT ==================
    def get_audit_log_path():
        return os.path.join(state_dir, "audit_log.json")

    def load_audit_log():
        return load_json_file(get_audit_log_path(), {"version": "1.0", "entries": []})

    def save_audit_log(data):
        save_json_file(get_audit_log_path(), data)

    # ================== DASHBOARD API ==================
    @app.get("/api/responses")
    async def get_responses():
        """Get all responses from audit log."""
        audit_log = load_audit_log()
        return {"responses": audit_log.get("entries", [])}

    @app.get("/api/responses/pending")
    async def get_pending_responses():
        """Get pending responses only."""
        audit_log = load_audit_log()
        entries = audit_log.get("entries", [])
        pending = [e for e in entries if e.get("status") == "pending_review"]
        return {"responses": pending}

    @app.post("/api/responses/{response_id}/approve")
    async def approve_response(response_id: str):
        """Approve a response."""
        audit_log = load_audit_log()
        entries = audit_log.get("entries", [])

        for entry in entries:
            if entry.get("id") == response_id:
                entry["status"] = "approved"
                entry["approved_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                save_audit_log(audit_log)
                return {"status": "ok", "response_id": response_id}

        raise HTTPException(status_code=404, detail="Response not found")

    @app.post("/api/responses/{response_id}/reject")
    async def reject_response(response_id: str, request: Request):
        """Reject a response."""
        data = await request.json()
        reason = data.get("reason", "No reason provided")

        audit_log = load_audit_log()
        entries = audit_log.get("entries", [])

        for entry in entries:
            if entry.get("id") == response_id:
                entry["status"] = "rejected"
                entry["rejected_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                entry["rejection_reason"] = reason
                save_audit_log(audit_log)
                return {"status": "ok", "response_id": response_id}

        raise HTTPException(status_code=404, detail="Response not found")

    @app.post("/api/responses/{response_id}/edit")
    async def edit_response(response_id: str, request: Request):
        """Edit a response."""
        data = await request.json()
        new_text = data.get("text", "")

        audit_log = load_audit_log()
        entries = audit_log.get("entries", [])

        for entry in entries:
            if entry.get("id") == response_id:
                entry["generated_response"] = new_text
                entry["edited_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                save_audit_log(audit_log)
                return {"status": "ok", "response_id": response_id}

        raise HTTPException(status_code=404, detail="Response not found")

    # ================== OAUTH ENDPOINTS ==================
    # Initialize config and token manager
    config = Config()
    token_manager = TokenManager(state_dir=state_dir)
    
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
        Initiate Instagram OAuth flow.
        Redirects user to Instagram authorization page.
        """
        import time
        
        # Clean up expired states
        cleanup_expired_states()
        
        # Generate CSRF state with timestamp
        state = secrets.token_urlsafe(32)
        oauth_states[state] = time.time()
        
        # Build OAuth URL
        params = {
            'client_id': config.instagram_client_id,
            'redirect_uri': config.instagram_redirect_uri,
            'scope': 'instagram_basic,instagram_manage_comments,pages_show_list',
            'response_type': 'code',
            'state': state
        }
        
        oauth_url = f"https://api.instagram.com/oauth/authorize?{urlencode(params)}"
        
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
        # Validate required parameters
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")
        
        if not state or state not in oauth_states:
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
                raise HTTPException(status_code=400, detail="Failed to exchange authorization code")
            
            # Step 2: Exchange short-lived token for long-lived token
            long_lived_data = exchange_for_long_lived_token(
                short_lived_token=short_lived_data['access_token'],
                client_secret=config.instagram_client_secret
            )
            
            if not long_lived_data:
                raise HTTPException(status_code=400, detail="Failed to get long-lived token")
            
            # Step 3: Store long-lived token
            token_manager.save_token(
                access_token=long_lived_data['access_token'],
                token_type=long_lived_data.get('token_type', 'bearer'),
                expires_in=long_lived_data.get('expires_in', 5184000),
                user_id=short_lived_data.get('user_id'),
                username=short_lived_data.get('username')
            )
            
            # Redirect to dashboard
            return RedirectResponse(url="/", status_code=303)
            
        except Exception as e:  # pylint: disable=broad-except
            raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}") from e

    @app.get("/auth/instagram/logout")
    async def instagram_oauth_logout():
        """
        Clear user session and logout.
        Removes stored token and clears session.
        """
        token_manager.clear_token()
        return RedirectResponse(url="/", status_code=303)

    # Helper functions for OAuth
    def exchange_code_for_token(code: str, client_id: str, client_secret: str, redirect_uri: str):
        """
        Exchange authorization code for short-lived access token.
        
        Args:
            code: Authorization code from Instagram
            client_id: Instagram client ID
            client_secret: Instagram client secret
            redirect_uri: Registered redirect URI
            
        Returns:
            Dictionary with token data or None if failed
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
                return response.json()
            return None
        except requests.RequestException:
            return None

    def exchange_for_long_lived_token(short_lived_token: str, client_secret: str):
        """
        Exchange short-lived token for long-lived token (60 days).
        
        Args:
            short_lived_token: Short-lived access token
            client_secret: Instagram client secret
            
        Returns:
            Dictionary with long-lived token data or None if failed
        """
        try:
            response = requests.get(
                'https://graph.instagram.com/access_token',
                params={
                    'grant_type': 'ig_exchange_token',
                    'client_secret': client_secret,
                    'access_token': short_lived_token
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except requests.RequestException:
            return None

    # ================== DASHBOARD UI ==================
    @app.get("/", response_class=HTMLResponse)
    async def dashboard_home():
        """Dashboard home page."""
        # Check if user is authenticated
        token_data = token_manager.get_token()
        is_authenticated = token_data is not None and not token_manager.is_token_expired()
        
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
    </style>
</head>
<body>
    <div class="header">
        <h1>Instagram Debate Bot Dashboard</h1>
        """ + auth_section + """
    </div>

    <div class="container">
        <div class="filters">
            <div class="filter-buttons">
                <button class="filter-btn active" data-filter="pending_review">Pending Review</button>
                <button class="filter-btn" data-filter="approved">Approved</button>
                <button class="filter-btn" data-filter="rejected">Rejected</button>
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

        // Load responses
        async function loadResponses() {
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
                    await loadResponses();
                }
            } catch (error) {
                console.error('Error saving edit:', error);
            }
        }

        // Cancel edit
        function cancelEdit(id) {
            loadResponses();
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

        // Auto-refresh every 5 seconds
        setInterval(loadResponses, 5000);
    </script>
</body>
</html>
    """
        return HTMLResponse(content=html_content)

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
