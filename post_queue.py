import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

VALID_PILLARS = {"build-in-public", "llm-tip", "career-journey", "ai-take", "manual"}
VALID_SOURCES = {"manual", "generated"}


class QueueError(Exception):
    """Raised for invalid queue operations or corrupt data."""


def _utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


class PostQueue:
    def __init__(self, path, now_fn=_utcnow_iso):
        self.path = Path(path)
        self._now = now_fn

    def _load(self):
        if not self.path.exists():
            return {"posts": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise QueueError(f"posts.json is corrupt: {e}") from e
        if not isinstance(data, dict) or not isinstance(data.get("posts"), list):
            raise QueueError("posts.json must be an object with a 'posts' list")
        return data

    def _save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def all_posts(self):
        return self._load()["posts"]

    def add_post(self, text, pillar, source):
        if pillar not in VALID_PILLARS:
            raise QueueError(f"invalid pillar: {pillar!r}")
        if source not in VALID_SOURCES:
            raise QueueError(f"invalid source: {source!r}")
        data = self._load()
        post = {
            "id": str(uuid.uuid4()),
            "pillar": pillar,
            "source": source,
            "text": text,
            "status": "draft",
            "created_at": self._now(),
            "approved_at": None,
            "posted_at": None,
            "linkedin_post_id": None,
        }
        data["posts"].append(post)
        self._save(data)
        return post
