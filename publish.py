import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from post_queue import PostQueue, QueueError
from linkedin_client import publish_text, LinkedInError

POSTS_PATH = Path(__file__).parent / "posts.json"
LOG_PATH = Path(__file__).parent / "logs" / "publish.log"


def _configure_logging():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def publish_one(queue, post_id, access_token, author_urn):
    """Publish one specific post to LinkedIn right now.

    If the post is still a draft, it is approved first (the caller's explicit
    click is the manual approval). Only drafts and approved posts can be
    published this way. Returns the LinkedIn post id. Raises LinkedInError on
    API failure (the post is left approved so it can be retried) and QueueError
    if the post is not in a publishable state.
    """
    post = next((p for p in queue.all_posts() if p["id"] == post_id), None)
    if post is None:
        raise QueueError(f"no post with id {post_id!r}")
    if post["status"] == "draft":
        queue.approve(post_id)
    elif post["status"] != "approved":
        raise QueueError(f"cannot publish a {post['status']} post")
    post_urn = publish_text(access_token, author_urn, post["text"])
    queue.mark_posted(post_id, post_urn)
    logging.info("Published post %s on demand as %s", post_id, post_urn)
    return post_urn


def run(queue, access_token, author_urn):
    """Publish the oldest approved post. Returns 'posted', 'empty', or 'failed'."""
    post = queue.next_approved()
    if post is None:
        logging.warning("No approved posts in queue; nothing to publish.")
        return "empty"
    try:
        post_id = publish_text(access_token, author_urn, post["text"])
    except LinkedInError as e:
        logging.error("Publish failed for post %s: %s", post["id"], e)
        return "failed"
    queue.mark_posted(post["id"], post_id)
    logging.info("Published post %s as %s", post["id"], post_id)
    return "posted"


def main():
    _configure_logging()
    load_dotenv()
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    urn = os.environ.get("LINKEDIN_AUTHOR_URN")
    if not token or not urn:
        logging.error("Missing LINKEDIN_ACCESS_TOKEN or LINKEDIN_AUTHOR_URN in .env")
        sys.exit(1)
    queue = PostQueue(POSTS_PATH)
    result = run(queue, token, urn)
    # 'failed' is the only nonzero exit; 'empty' is a normal no-op.
    sys.exit(1 if result == "failed" else 0)


if __name__ == "__main__":
    main()
