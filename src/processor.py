"""
Main processor for the Instagram Debate Bot.
Handles the batch processing of pending comments.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.file_utils import load_json_file, save_json_file


class CommentProcessor:
    """Main processing loop for handling pending comments."""

    def __init__(self, instagram_api, llm_client, validator, config):
        """
        Initialize comment processor.

        Args:
            instagram_api: InstagramAPI instance
            llm_client: LLMClient instance
            validator: ResponseValidator instance
            config: Config instance
        """
        self.instagram_api = instagram_api
        self.llm_client = llm_client
        self.validator = validator
        self.config = config

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
            articles_config: List of article configs with 'path' and 'link' keys

        Returns:
            List of article dictionaries with content, metadata, path, and link
        """
        articles = []
        for config in articles_config:
            content = self.load_article(config["path"])
            metadata = self.parse_article_metadata(content)
            articles.append({
                "path": config["path"],
                "link": config["link"],
                "content": content,
                "title": metadata["title"],
                "summary": metadata["summary"]
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
        Load pending comments from JSON file.

        Returns:
            List of pending comment dictionaries
        """
        pending_file = os.path.join("state", "pending_comments.json")
        data = load_json_file(pending_file, {"version": "1.0", "comments": []})
        return data.get("comments", [])

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
        self, comment: Dict[str, Any], article_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single comment and generate response.

        Args:
            comment: Comment data dictionary
            article_text: Full article text

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
        template = self.llm_client.load_template("debate_prompt.txt")
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

        # Validate response
        is_valid, errors = self.validator.validate_response(response_text)

        if not is_valid:
            return {
                "comment_id": comment["comment_id"],
                "status": "failed",
                "errors": errors
            }

        # Extract citations
        citations = self.validator.extract_citations(response_text)

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
        template = self.llm_client.load_template("debate_prompt.txt")
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

        # Validate response
        is_valid, errors = self.validator.validate_response(response_text)

        if not is_valid:
            return {
                "comment_id": comment["comment_id"],
                "status": "failed",
                "errors": errors
            }

        # Extract citations
        citations = self.validator.extract_citations(response_text)

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
        os.makedirs("state", exist_ok=True)
        audit_file = os.path.join("state", "audit_log.json")

        # Load existing log
        if os.path.exists(audit_file):
            with open(audit_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"version": "1.0", "entries": []}

        # Add entry ID
        log_entry["id"] = f"log_{len(data['entries']) + 1:03d}"

        # Append entry
        data["entries"].append(log_entry)

        # Save
        with open(audit_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

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

    def post_approved_responses(self) -> None:
        """Post all approved responses to Instagram.

        Posts any response with status='approved' and posted=False, regardless of
        AUTO_POST_ENABLED setting. This allows manually approved responses from the
        dashboard to be posted by the processor.
        """
        audit_file = os.path.join("state", "audit_log.json")
        if not os.path.exists(audit_file):
            return

        with open(audit_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for entry in data["entries"]:
            if entry.get("status") == "approved" and not entry.get("posted", False):
                try:
                    # Post reply
                    _result = self.instagram_api.post_reply(
                        entry["comment_id"],
                        entry["generated_response"]
                    )

                    # Update entry
                    entry["posted"] = True
                    entry["posted_at"] = (
                        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    )

                    # Save posted ID
                    posted_file = os.path.join("state", "posted_ids.txt")
                    with open(posted_file, 'a', encoding='utf-8') as f:
                        f.write(entry["comment_id"] + "\n")

                except Exception as e:  # pylint: disable=broad-exception-caught
                    entry["post_error"] = str(e)

        # Save updated audit log
        with open(audit_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def clear_pending_comments(self) -> None:
        """Clear processed comments from pending list."""
        pending_file = os.path.join("state", "pending_comments.json")
        if os.path.exists(pending_file):
            save_json_file(pending_file, {"version": "1.0", "comments": []}, ensure_dir=False)

    def run(self) -> None:
        """Main processing loop entry point."""
        # Check if multi-article mode is enabled
        articles_config = self.config.articles_config

        # Load pending comments
        comments = self.load_pending_comments()

        if not comments:
            print("No pending comments to process")
            return

        print(f"Processing {len(comments)} pending comment(s)...")

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
        else:
            # Single-article mode
            if not articles_config:
                print("No articles configured. Set ARTICLES_CONFIG environment variable.")
                return

            article_text = self.load_article(articles_config[0]["path"])

            for comment in comments:
                print(f"Processing comment {comment.get('comment_id')}...")
                result = self.process_comment(comment, article_text)

                if result:
                    self.save_audit_log(result)
                    print(f"  - Generated response, status: {result.get('status')}")
                else:
                    print("  - Skipped (not relevant)")

        # Post approved responses (both auto-approved and manually approved)
        print("Posting approved responses...")
        self.post_approved_responses()

        # Clear pending comments
        self.clear_pending_comments()

        print("Processing complete!")
