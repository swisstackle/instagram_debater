"""
Test server for dashboard E2E testing.
Includes mock Instagram API, OpenRouter API, and imports the dashboard app.
"""
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
from dashboard import create_dashboard_app

# Create the main test server app
app = FastAPI()

# Create and mount the dashboard app with test state directory
dashboard_app = create_dashboard_app(state_dir="test_state")

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

# ================== TEST UTILITY ENDPOINTS ==================
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

# ================== MOUNT DASHBOARD APP ==================
# Mount the dashboard app to handle all dashboard routes
app.mount("/", dashboard_app)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5001, log_level="info")
