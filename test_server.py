"""
Test server for dashboard E2E testing.
Includes mock Instagram API, OpenRouter API, and the dashboard app.
"""
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

app = FastAPI()

# ================== STATE MANAGEMENT ==================
STATE_DIR = "test_state"
os.makedirs(STATE_DIR, exist_ok=True)

def get_audit_log_path():
    return os.path.join(STATE_DIR, "audit_log.json")

def get_pending_comments_path():
    return os.path.join(STATE_DIR, "pending_comments.json")

def load_audit_log():
    path = get_audit_log_path()
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {"version": "1.0", "entries": []}

def save_audit_log(data):
    path = get_audit_log_path()
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def load_pending_comments():
    path = get_pending_comments_path()
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {"version": "1.0", "comments": []}

def save_pending_comments(data):
    path = get_pending_comments_path()
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# ================== MOCK INSTAGRAM API ==================
mock_instagram_state = {
    "posts": {},
    "comments": {},
    "replies": {}
}

@app.get("/mock-instagram/post/{post_id}")
async def mock_get_post(post_id: str):
    """Mock Instagram post endpoint."""
    if post_id in mock_instagram_state["posts"]:
        return mock_instagram_state["posts"][post_id]
    return {"id": post_id, "caption": "Test post caption about climate change"}

@app.get("/mock-instagram/comment/{comment_id}")
async def mock_get_comment(comment_id: str):
    """Mock Instagram comment endpoint."""
    if comment_id in mock_instagram_state["comments"]:
        return mock_instagram_state["comments"][comment_id]
    return {"id": comment_id, "text": "Test comment"}

@app.post("/mock-instagram/comment/{comment_id}/reply")
async def mock_post_reply(comment_id: str, request: Request):
    """Mock Instagram reply endpoint."""
    data = await request.json()
    reply_id = f"reply_{len(mock_instagram_state['replies']) + 1}"
    mock_instagram_state["replies"][reply_id] = {
        "id": reply_id,
        "comment_id": comment_id,
        "text": data.get("message", ""),
        "created_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    return {"id": reply_id}

@app.post("/mock-instagram/webhook/trigger")
async def mock_trigger_webhook(request: Request):
    """Trigger a mock webhook notification (for testing)."""
    data = await request.json()
    # Save to pending comments
    pending = load_pending_comments()
    pending["comments"].append({
        "comment_id": data.get("comment_id", f"comment_{len(pending['comments']) + 1}"),
        "post_id": data.get("post_id", "post_1"),
        "username": data.get("username", "test_user"),
        "user_id": data.get("user_id", "user_123"),
        "text": data.get("text", "This is a test comment"),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "received_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    })
    save_pending_comments(pending)
    return {"status": "ok"}

# ================== MOCK OPENROUTER API ==================
@app.post("/mock-openrouter/api/v1/chat/completions")
async def mock_openrouter_chat(request: Request):
    """Mock OpenRouter chat completions endpoint."""
    data = await request.json()
    messages = data.get("messages", [])
    
    # Simple mock response based on content
    user_message = ""
    for msg in messages:
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
    
    # Generate a simple mock response
    if "check_comment_relevance" in user_message or "CHECK_COMMENT_RELEVANCE" in user_message:
        response_text = "YES"
    elif "check_post_topic" in user_message or "CHECK_POST_TOPIC" in user_message:
        response_text = "YES"
    else:
        # Generate a mock debate response
        response_text = """According to the article (§1.2), climate change is a critical issue that requires immediate action. 

The evidence shows that global temperatures have risen significantly over the past century. This is supported by multiple scientific studies cited in §3.1.

I encourage you to read the full article for more context: [Article Link]"""
    
    return {
        "id": "chatcmpl-mock123",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": data.get("model", "google/gemini-flash-2.0"),
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }

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

@app.post("/api/test/reset")
async def reset_test_state():
    """Reset test state (for testing)."""
    # Clear state files
    save_audit_log({"version": "1.0", "entries": []})
    save_pending_comments({"version": "1.0", "comments": []})
    mock_instagram_state["posts"].clear()
    mock_instagram_state["comments"].clear()
    mock_instagram_state["replies"].clear()
    return {"status": "ok"}

@app.post("/api/test/seed")
async def seed_test_data(request: Request):
    """Seed test data for testing."""
    data = await request.json()
    
    if "audit_log" in data:
        save_audit_log(data["audit_log"])
    
    if "pending_comments" in data:
        save_pending_comments(data["pending_comments"])
    
    return {"status": "ok"}

# ================== DASHBOARD UI ==================
@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Dashboard home page."""
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
        }
        
        .header h1 {
            font-size: 1.5rem;
            color: #333;
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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5001, log_level="info")
