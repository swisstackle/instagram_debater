"""
Main processor for the Instagram Debate Bot.
Handles the batch processing of pending comments.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.comment_extractor import CommentExtractor
from src.audit_log_extractor import AuditLogExtractor
from src.file_utils import load_json_file, save_json_file
from src.validator import ResponseValidator


class CommentProcessor:
    """Main processing loop for handling pending comments."""

    def __init__(self, instagram_api, llm_client, validator, config, comment_extractor: CommentExtractor = None, audit_log_extractor: AuditLogExtractor = None):
        """
        Initialize comment processor.

        Args:
            instagram_api: InstagramAPI instance
            llm_client: LLMClient instance
            validator: ResponseValidator instance
            config: Config instance
            comment_extractor: CommentExtractor instance (optional, defaults to factory-created)
            audit_log_extractor: AuditLogExtractor instance (optional, defaults to factory-created)
        """
        self.instagram_api = instagram_api
        self.llm_client = llm_client
        self.validator = validator
        self.config = config
        
        # Use provided extractor or create one via factory
        if comment_extractor is None:
            from src.comment_extractor_factory import create_comment_extractor
            comment_extractor = create_comment_extractor()
        self.comment_extractor = comment_extractor
        
        # Use provided audit log extractor or create one via factory
        if audit_log_extractor is None:
            from src.audit_log_extractor_factory import create_audit_log_extractor
            audit_log_extractor = create_audit_log_extractor()
        self.audit_log_extractor = audit_log_extractor

    def load_article(self, article_path: str) -> str:
        """
        Load article content from file.

        Args:
            article_path: Path to article file

        Returns:
            Article text content
        """
        with open(article_path, 'r', encoding='utf-8') as f:
            return f.read()

    def load_articles(self, articles_config: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Load multiple articles from configuration.

        Args:
            articles_config: List of article configs with 'path', 'link', and
                optional 'is_numbered' keys

        Returns:
            List of article dictionaries with content, metadata, path, link,
                and is_numbered flag
        """
        articles = []
        for config in articles_config:
            content = self.load_article(config["path"])
            metadata = self.parse_article_metadata(content)
            # Default to True for backward compatibility
            is_numbered = config.get("is_numbered", True)
            articles.append({
                "path": config["path"],
                "link": config["link"],
                "content": content,
                "title": metadata["title"],
                "summary": metadata["summary"],
                "is_numbered": is_numbered
            })
        return articles

    def parse_article_metadata(self, article_text: str) -> Dict[str, str]:
        """
        Parse article title and summary from content.

        Args:
            article_text: Full article text

        Returns:
            Dictionary with 'title' and 'summary' keys
        """
        lines = article_text.split('\n')
        title = ""
        summary = ""

        # Find first # heading as title
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break

        # Get first paragraph as summary (first non-empty line after headers)
        in_content = False
        for line in lines:
            if line.strip() and not line.startswith('#'):
                in_content = True
            if in_content and line.strip() and not line.startswith('#'):
                summary = line.strip()
                break

        return {
            "title": title,
            "summary": summary
        }

    def load_pending_comments(self) -> List[Dict[str, Any]]:
        """
        Load pending comments using the configured extractor.

        Returns:
            List of pending comment dictionaries
        """
        return self.comment_extractor.load_pending_comments()

    def select_relevant_article(
        self,
        articles: List[Dict[str, Any]],
        post_caption: str,
        comment_text: str,
        thread_context: str
    ) -> Optional[Dict[str, Any]]:
        """
        Select the first relevant article from a list based on content.

        Args:
            articles: List of article dictionaries
            post_caption: Post caption
            comment_text: Comment text
            thread_context: Thread conversation context

        Returns:
            First matching article dictionary or None if no match
        """
        for article in articles:
            if self.llm_client.check_topic_relevance(
                article["title"],
                article["summary"],
                post_caption,
                comment_text,
                thread_context
            ):
                return article
        return None

    def process_comment(
        self, comment: Dict[str, Any], article_text: str, is_numbered: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single comment and generate response.

        Args:
            comment: Comment data dictionary
            article_text: Full article text
            is_numbered: Whether the article uses numbered sections (default: True)

        Returns:
            Result dictionary with response and metadata, or None if skipped
        """
        # Parse article metadata
        metadata = self.parse_article_metadata(article_text)

        # Check if post is relevant to article topic
        try:
            post_caption = self.instagram_api.get_post_caption(comment["post_id"])
        except Exception:  # pylint: disable=broad-exception-caught
            post_caption = ""

        if post_caption and not self.llm_client.check_post_topic_relevance(
            metadata["title"], metadata["summary"], post_caption
        ):
            return None

        # Check if comment is relevant
        if not self.llm_client.check_comment_relevance(
            metadata["title"], metadata["summary"], comment["text"]
        ):
            self.save_no_match_log(comment, "Comment not relevant to article topic")
            return None

        # Build thread context
        thread_context = self.build_thread_context(
            comment["comment_id"],
            comment["post_id"]
        )

        # Generate response using LLM
        # Choose template based on whether article is numbered
        template_name = "debate_prompt.txt" if is_numbered else "debate_prompt_unnumbered.txt"
        template = self.llm_client.load_template(template_name)
        prompt = self.llm_client.fill_template(template, {
            "TOPIC": metadata["title"],
            "FULL_ARTICLE_TEXT": article_text,
            "POST_CAPTION": post_caption,
            "USERNAME": comment["username"],
            "COMMENT_TEXT": comment["text"],
            "THREAD_CONTEXT": (
                f"\nPREVIOUS DISCUSSION IN THIS THREAD:\n{thread_context}"
                if thread_context else ""
            )
        })

        response_text = self.llm_client.generate_response(prompt)

        # Create validator with is_numbered flag
        validator = ResponseValidator(article_text, is_numbered=is_numbered)

        # Validate response
        is_valid, errors = validator.validate_response(response_text)

        if not is_valid:
            return {
                "comment_id": comment["comment_id"],
                "status": "failed",
                "errors": errors
            }

        # Extract citations
        citations = validator.extract_citations(response_text)

        result = {
            "comment_id": comment["comment_id"],
            "comment_text": comment["text"],
            "generated_response": response_text,
            "citations_used": citations,
            "status": "approved" if self.config.auto_post_enabled else "pending_review",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "validation_passed": True,
            "validation_errors": []
        }

        return result

    def process_comment_multi_article(
        self, comment: Dict[str, Any], articles: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single comment with multiple articles available.

        Args:
            comment: Comment data dictionary
            articles: List of article dictionaries

        Returns:
            Result dictionary with response and metadata, or None if skipped
        """
        # Get post caption and thread context
        try:
            post_caption = self.instagram_api.get_post_caption(comment["post_id"])
        except Exception:  # pylint: disable=broad-exception-caught
            post_caption = ""

        # Build thread context
        thread_context = self.build_thread_context(
            comment["comment_id"],
            comment["post_id"]
        )

        # Select relevant article
        selected_article = self.select_relevant_article(
            articles,
            post_caption,
            comment["text"],
            thread_context
        )

        if not selected_article:
            self.save_no_match_log(comment, "No relevant article found for this comment")
            return None

        # Generate response using selected article
        # Choose template based on whether article is numbered
        is_numbered = selected_article.get("is_numbered", True)
        template_name = "debate_prompt.txt" if is_numbered else "debate_prompt_unnumbered.txt"
        template = self.llm_client.load_template(template_name)
        prompt = self.llm_client.fill_template(template, {
            "TOPIC": selected_article["title"],
            "FULL_ARTICLE_TEXT": selected_article["content"],
            "POST_CAPTION": post_caption,
            "USERNAME": comment["username"],
            "COMMENT_TEXT": comment["text"],
            "THREAD_CONTEXT": (
                f"\nPREVIOUS DISCUSSION IN THIS THREAD:\n{thread_context}"
                if thread_context else ""
            )
        })

        response_text = self.llm_client.generate_response(prompt)

        # Create validator with is_numbered flag
        validator = ResponseValidator(selected_article["content"], is_numbered=is_numbered)

        # Validate response
        is_valid, errors = validator.validate_response(response_text)

        if not is_valid:
            return {
                "comment_id": comment["comment_id"],
                "status": "failed",
                "errors": errors
            }

        # Extract citations
        citations = validator.extract_citations(response_text)

        result = {
            "comment_id": comment["comment_id"],
            "comment_text": comment["text"],
            "generated_response": response_text,
            "citations_used": citations,
            "status": "approved" if self.config.auto_post_enabled else "pending_review",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "validation_passed": True,
            "validation_errors": [],
            "article_used": {
                "path": selected_article["path"],
                "link": selected_article["link"],
                "title": selected_article["title"]
            }
        }

        return result

    def build_thread_context(self, comment_id: str, post_id: str = None) -> str:  # pylint: disable=unused-argument
        """
        Build conversation context for a comment.

        Args:
            comment_id: Comment ID
            post_id: Post ID

        Returns:
            Formatted thread context string
        """
        try:
            replies = self.instagram_api.get_comment_replies(comment_id)
            if replies:
                context_lines = []
                for reply in replies[:5]:  # Limit to 5 most recent
                    username = reply.get("from", {}).get("username", "unknown")
                    text = reply.get("text", "")
                    context_lines.append(f"@{username}: {text}")
                return "\n".join(context_lines)
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        return ""

    def save_audit_log(self, log_entry: Dict[str, Any]) -> None:
        """
        Save processing result to audit log.

        Args:
            log_entry: Log entry data
        """
        self.audit_log_extractor.save_entry(log_entry)

    def save_no_match_log(self, comment: Dict[str, Any], reason: str) -> None:
        """
        Save non-matching comment to no_match_log.

        Args:
            comment: Comment data
            reason: Reason for not matching
        """
        os.makedirs("state", exist_ok=True)
        no_match_file = os.path.join("state", "no_match_log.json")

        # Load existing log
        if os.path.exists(no_match_file):
            with open(no_match_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"version": "1.0", "entries": []}

        # Create entry
        entry = {
            "id": f"nomatch_{len(data['entries']) + 1:03d}",
            "comment_id": comment.get("comment_id"),
            "post_id": comment.get("post_id"),
            "username": comment.get("username"),
            "comment_text": comment.get("text"),
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

        # Append and save
        data["entries"].append(entry)

        with open(no_match_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _extract_graph_api_error(self, exc: Exception) -> Optional[Any]:
        """
        Extract Graph API error body from an exception.

        Attempts multiple strategies to extract error details from various
        exception formats that SDKs might use.

        Args:
            exc: Exception that may contain Graph API error information

        Returns:
            Parsed JSON dict/list, or dict with text wrapper, or None if nothing found
        """
        try:
            # Strategy 1: Check if exception has a response attribute with json() method
            if hasattr(exc, 'response'):
                resp = exc.response
                # Try calling json() method
                if hasattr(resp, 'json') and callable(resp.json):
                    try:
                        return resp.json()
                    except Exception:  # pylint: disable=broad-exception-caught
                        pass
                
                # Try accessing text attribute and parsing as JSON
                if hasattr(resp, 'text'):
                    try:
                        return json.loads(resp.text)
                    except Exception:  # pylint: disable=broad-exception-caught
                        # Return raw text wrapped in dict
                        return {"text": resp.text}
            
            # Strategy 2: Check common attribute names (before checking args)
            for attr_name in ['body', 'result', 'error_data']:
                if hasattr(exc, attr_name):
                    attr_value = getattr(exc, attr_name)
                    if attr_value is not None:
                        # If it's already structured, return it
                        if isinstance(attr_value, (dict, list)):
                            return attr_value
                        # Try parsing as JSON
                        if isinstance(attr_value, (bytes, str)):
                            try:
                                if isinstance(attr_value, bytes):
                                    attr_value = attr_value.decode('utf-8')
                                return json.loads(attr_value)
                            except Exception:  # pylint: disable=broad-exception-caught
                                return {"text": str(attr_value)}
            
            # Strategy 3: Check exception args for structured data
            if hasattr(exc, 'args') and exc.args:
                for arg in exc.args:
                    # If arg is already a dict or list, return it
                    if isinstance(arg, (dict, list)):
                        return arg
                    
                    # Try parsing bytes/str as JSON
                    if isinstance(arg, (bytes, str)):
                        try:
                            # Handle bytes
                            if isinstance(arg, bytes):
                                arg = arg.decode('utf-8')
                            return json.loads(arg)
                        except Exception:  # pylint: disable=broad-exception-caught
                            # Don't return plain text from args - continue looking
                            pass
            
            # Nothing found
            return None
            
        except Exception as e:  # pylint: disable=broad-exception-caught
            # If extraction itself fails, return error info
            return {"error_extraction_failed": str(e)}

    def _ensure_valid_token(self) -> None:
        """
        Ensure the Instagram access token is valid.
        
        Checks for OAuth token expiration and attempts refresh if needed.
        Logs token validation status for debugging.
        Uses configured token storage backend (local or Tigris).
        """
        try:
            from src.token_extractor_factory import create_token_extractor  # pylint: disable=import-outside-toplevel
            
            extractor = create_token_extractor()
            
            # Check if OAuth token exists and is expired
            if extractor.get_token():
                if extractor.is_token_expired(buffer_days=5):
                    print("Token expiring soon, attempting refresh...")
                    app_secret = self.config.instagram_app_secret
                    if app_secret:
                        success = extractor.refresh_token(app_secret)
                        if success:
                            print("Token refreshed successfully")
                        else:
                            print("Token refresh failed, will use env var token if available")
                    else:
                        print("Cannot refresh token: app secret not configured")
                else:
                    print("OAuth token is valid")
            else:
                print("No OAuth token found, using environment variable token")
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Token validation warning: {e}")
            # Don't fail - env var token might still be valid

    def post_approved_responses(self) -> None:
        """Post all approved responses to Instagram.

        Posts any response with status='approved' and posted=False, regardless of
        AUTO_POST_ENABLED setting. This allows manually approved responses from the
        dashboard to be posted by the processor.
        """
        # Ensure token is valid before attempting to post
        self._ensure_valid_token()
        
        entries = self.audit_log_extractor.load_entries()
        print(f"Found {len(entries)} approved responses to post")
        for entry in entries:
            if entry.get("status") == "approved" and not entry.get("posted", False):
                try:
                    # Post reply
                    _result = self.instagram_api.post_reply(
                        entry["comment_id"],
                        entry["generated_response"]
                    )
                    print("Posted response")

                    # Update entry
                    updates = {
                        "posted": True,
                        "posted_at": (
                            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                        )
                    }
                    self.audit_log_extractor.update_entry(entry["id"], updates)

                    # Save posted ID
                    posted_file = os.path.join("state", "posted_ids.txt")
                    os.makedirs("state", exist_ok=True)
                    with open(posted_file, 'a', encoding='utf-8') as f:
                        f.write(entry["comment_id"] + "\n")

                except Exception as e:  # pylint: disable=broad-exception-caught
                    # Extract Graph API error details
                    graph_body = self._extract_graph_api_error(e)
                    
                    # Build structured error payload
                    post_error_payload = {"message": str(e)}
                    if graph_body is not None:
                        post_error_payload["graph_api_error"] = graph_body
                        print("Graph API error details: %s", graph_body)
                    
                    # Log the error details
                    try:
                        error_log = json.dumps(post_error_payload, indent=2)
                        print(f"Error posting response: {error_log}")
                    except Exception:  # pylint: disable=broad-exception-caught
                        # Fallback if JSON serialization fails
                        print(f"Error posting response: {post_error_payload}")
                    
                    # Update audit log with structured error
                    updates = {"post_error": post_error_payload}
                    self.audit_log_extractor.update_entry(entry["id"], updates)

    def clear_pending_comments(self) -> None:
        """Clear processed comments from pending list using the configured extractor."""
        self.comment_extractor.clear_pending_comments()

    def run(self) -> None:
        """Main processing loop entry point."""
        # Check if multi-article mode is enabled
        articles_config = self.config.articles_config

        # Load pending comments
        comments = self.load_pending_comments()

        if not comments:
            print("No pending comments to process")
        else:
            print(f"Processing {len(comments)} pending comment(s)...")

            # Track whether we successfully processed comments
            comments_processed = False

            # Multi-article or single-article mode
            if len(articles_config) > 1:
                # Multi-article mode
                print(f"Running in multi-article mode with {len(articles_config)} articles")
                articles = self.load_articles(articles_config)

                for comment in comments:
                    print(f"Processing comment {comment.get('comment_id')}...")
                    result = self.process_comment_multi_article(comment, articles)

                    if result:
                        self.save_audit_log(result)
                        article_title = result.get("article_used", {}).get("title", "unknown")
                        status = result.get('status')
                        print(f"  - Generated response using '{article_title}', status: {status}")
                    else:
                        print("  - Skipped (not relevant)")
                
                comments_processed = True
            else:
                # Single-article mode
                if not articles_config:
                    print("No articles configured. Set ARTICLES_CONFIG environment variable.")
                    # Don't mark as processed since we couldn't process them
                else:
                    article_text = self.load_article(articles_config[0]["path"])
                    is_numbered = articles_config[0].get("is_numbered", True)

                    for comment in comments:
                        print(f"Processing comment {comment.get('comment_id')}...")
                        result = self.process_comment(comment, article_text, is_numbered=is_numbered)

                        if result:
                            self.save_audit_log(result)
                            print(f"  - Generated response, status: {result.get('status')}")
                        else:
                            print("  - Skipped (not relevant)")
                    
                    comments_processed = True

            # Only clear pending comments if we actually processed them
            if comments_processed:
                self.clear_pending_comments()

        # Post approved responses (both auto-approved and manually approved)
        # This runs even when there are no pending comments to process,
        # ensuring manually approved responses are posted
        print("Posting approved responses...")
        self.post_approved_responses()

        print("Processing complete!")
