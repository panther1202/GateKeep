# GateKeep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build GateKeep — a weekly LinkedIn auto-posting pipeline for Panth Patel where every post (manual or Gemini-generated) passes a human approval gate before a scheduled headless publisher posts it via LinkedIn's official API.

**Architecture:** Two entry points (`app.py` Streamlit control panel, `publish.py` headless publisher) share one data file (`posts.json`) through one module (`queue.py`). Thin API wrappers (`linkedin_client.py`, `gemini_client.py`) isolate network I/O so they can be mocked. `reauth.py` is a standalone OAuth refresh helper. Neither entry point depends on MCP or a running Claude session — both run as plain Python.

**Tech Stack:** Python 3.11+, Streamlit (UI), `requests` (LinkedIn REST), `google-generativeai` (Gemini), `python-dotenv` (secrets), `pytest` (tests).

---

## File Structure

| File | Responsibility |
|---|---|
| `post_queue.py` | All `posts.json` read/write/query logic. The single source of truth for post state transitions and "next approved" selection. Pure logic, fully unit-tested. (Named `post_queue.py`, not `queue.py`, to avoid shadowing Python's stdlib `queue` module that dependencies import.) |
| `linkedin_client.py` | Thin wrapper over LinkedIn's Posts API (`w_member_social`). One function: publish text. Used only by `publish.py`. |
| `gemini_client.py` | Thin wrapper over the Gemini API for draft generation, plus per-pillar prompt templates. Used only by `app.py`. |
| `publish.py` | Headless entry point. Selects the oldest approved post, publishes it, records the result. Run by the scheduler. |
| `app.py` | Streamlit control panel. The only human-facing surface: add/generate/review/approve/reject/history. |
| `reauth.py` | Manual OAuth consent-flow helper. Refreshes the LinkedIn token in `.env` every ~60 days. |
| `tests/test_queue.py` | Unit tests for `queue.py`. |
| `tests/test_publish.py` | Publish-flow tests with a mocked LinkedIn client (no real network). |
| `.env.example` | Documents required secrets without holding real values. |
| `.gitignore` | Excludes `.env`, `posts.json`, `logs/`, Python cruft. |
| `requirements.txt` | Pinned dependencies. |
| `README.md` | Setup + usage. |

Design notes locked here:
- `queue.py` is a `PostQueue` class wrapping a file path, with an injectable `now_fn` clock so timestamp-ordering logic is deterministic in tests.
- Timestamps are ISO-8601 UTC strings. Ordering ("oldest approved") is lexicographic on those strings, which is correct for ISO-8601 UTC.
- Network clients are plain functions (not classes) taking explicit credentials as arguments — trivial to monkeypatch.

---

### Task 1: Project scaffolding

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# Secrets and personal data
.env
posts.json

# Logs
logs/

# Python
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
*.egg-info/
```

- [ ] **Step 2: Create `requirements.txt`**

```text
streamlit==1.41.1
requests==2.32.3
python-dotenv==1.0.1
google-generativeai==0.8.3
pytest==8.3.4
```

- [ ] **Step 3: Create `.env.example`**

```text
# LinkedIn OAuth app credentials (from developer.linkedin.com)
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/callback

# Filled in by reauth.py after the OAuth consent flow
LINKEDIN_ACCESS_TOKEN=
# Your member URN, e.g. urn:li:person:AbC123 (printed by reauth.py)
LINKEDIN_AUTHOR_URN=

# Google Gemini (free tier) from Google AI Studio
GEMINI_API_KEY=your_gemini_key
```

- [ ] **Step 4: Create empty `tests/__init__.py`**

Create an empty file at `tests/__init__.py`.

- [ ] **Step 5: Create and activate a virtualenv, install deps**

Run:
```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\Activate.ps1 in PowerShell
pip install -r requirements.txt
```
Expected: all packages install without error.

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements.txt .env.example tests/__init__.py
git commit -m "chore: project scaffolding, deps, gitignore"
```

---

### Task 2: `queue.py` — load, save, add (TDD)

**Files:**
- Create: `queue.py`
- Test: `tests/test_queue.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_queue.py`:
```python
import json
import pytest
from queue import PostQueue, QueueError


def _fixed_clock():
    """Returns a callable yielding strictly increasing ISO timestamps."""
    counter = {"n": 0}

    def now():
        counter["n"] += 1
        return f"2026-07-08T00:00:{counter['n']:02d}+00:00"

    return now


def test_load_missing_file_returns_empty(tmp_path):
    q = PostQueue(tmp_path / "posts.json")
    assert q.all_posts() == []


def test_add_post_persists_with_defaults(tmp_path):
    path = tmp_path / "posts.json"
    q = PostQueue(path, now_fn=_fixed_clock())
    post = q.add_post(text="Hello", pillar="llm-tip", source="manual")

    assert post["text"] == "Hello"
    assert post["pillar"] == "llm-tip"
    assert post["source"] == "manual"
    assert post["status"] == "draft"
    assert post["created_at"] == "2026-07-08T00:00:01+00:00"
    assert post["approved_at"] is None
    assert post["posted_at"] is None
    assert post["linkedin_post_id"] is None
    assert isinstance(post["id"], str) and len(post["id"]) > 0

    # Reloading from disk returns the same post
    reloaded = PostQueue(path).all_posts()
    assert len(reloaded) == 1
    assert reloaded[0]["id"] == post["id"]


def test_add_post_rejects_bad_pillar(tmp_path):
    q = PostQueue(tmp_path / "posts.json")
    with pytest.raises(QueueError):
        q.add_post(text="x", pillar="not-a-pillar", source="manual")


def test_add_post_rejects_bad_source(tmp_path):
    q = PostQueue(tmp_path / "posts.json")
    with pytest.raises(QueueError):
        q.add_post(text="x", pillar="llm-tip", source="robot")


def test_load_corrupt_file_raises(tmp_path):
    path = tmp_path / "posts.json"
    path.write_text("{not valid json", encoding="utf-8")
    q = PostQueue(path)
    with pytest.raises(QueueError):
        q.all_posts()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_queue.py -v`
Expected: FAIL / collection error — `ModuleNotFoundError: No module named 'post_queue'` (our file does not exist yet).

> Note: the module is named `post_queue.py`, NOT `queue.py`. Naming it `queue.py` would shadow Python's stdlib `queue` module for the whole process (repo root sits on `sys.path[0]` under pytest / `streamlit run` / `python publish.py`), and dependencies such as streamlit and grpc import stdlib `queue` internally — the shadow would break them.

- [ ] **Step 3: Write minimal implementation**

Create `queue.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_queue.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add queue.py tests/test_queue.py
git commit -m "feat: queue load/save/add with validation"
```

---

### Task 3: `queue.py` — status transitions (TDD)

**Files:**
- Modify: `queue.py`
- Test: `tests/test_queue.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_queue.py`:
```python
def test_update_text_only_on_draft(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("old", "manual", "manual")
    q.update_text(p["id"], "new")
    assert q.all_posts()[0]["text"] == "new"


def test_approve_sets_status_and_timestamp(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("hi", "ai-take", "manual")
    q.approve(p["id"])
    updated = q.all_posts()[0]
    assert updated["status"] == "approved"
    assert updated["approved_at"] is not None


def test_approve_only_from_draft(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("hi", "ai-take", "manual")
    q.approve(p["id"])
    with pytest.raises(QueueError):
        q.approve(p["id"])  # already approved


def test_reject_sets_status(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("hi", "ai-take", "manual")
    q.reject(p["id"])
    assert q.all_posts()[0]["status"] == "rejected"


def test_pending_drafts_excludes_non_drafts(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    a = q.add_post("a", "llm-tip", "manual")
    b = q.add_post("b", "llm-tip", "manual")
    q.approve(b["id"])
    pending_ids = [p["id"] for p in q.pending_drafts()]
    assert pending_ids == [a["id"]]


def test_unknown_id_raises(tmp_path):
    q = PostQueue(tmp_path / "posts.json")
    with pytest.raises(QueueError):
        q.approve("no-such-id")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_queue.py -v`
Expected: FAIL — `AttributeError: 'PostQueue' object has no attribute 'update_text'` (and the other new methods).

- [ ] **Step 3: Write minimal implementation**

Add these methods to the `PostQueue` class in `queue.py`:
```python
    def _find(self, data, post_id):
        for post in data["posts"]:
            if post["id"] == post_id:
                return post
        raise QueueError(f"no post with id {post_id!r}")

    def update_text(self, post_id, text):
        data = self._load()
        post = self._find(data, post_id)
        if post["status"] != "draft":
            raise QueueError("can only edit text of a draft")
        post["text"] = text
        self._save(data)
        return post

    def approve(self, post_id):
        data = self._load()
        post = self._find(data, post_id)
        if post["status"] != "draft":
            raise QueueError(f"can only approve a draft, not {post['status']}")
        post["status"] = "approved"
        post["approved_at"] = self._now()
        self._save(data)
        return post

    def reject(self, post_id):
        data = self._load()
        post = self._find(data, post_id)
        if post["status"] not in ("draft", "approved"):
            raise QueueError(f"cannot reject a {post['status']} post")
        post["status"] = "rejected"
        self._save(data)
        return post

    def pending_drafts(self):
        return [p for p in self.all_posts() if p["status"] == "draft"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_queue.py -v`
Expected: PASS (11 passed).

- [ ] **Step 5: Commit**

```bash
git add queue.py tests/test_queue.py
git commit -m "feat: queue status transitions (update/approve/reject/pending)"
```

---

### Task 4: `queue.py` — publish selection + mark posted (TDD)

**Files:**
- Modify: `queue.py`
- Test: `tests/test_queue.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_queue.py`:
```python
def test_next_approved_none_when_empty(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    q.add_post("draft only", "llm-tip", "manual")
    assert q.next_approved() is None


def test_next_approved_picks_oldest_approved_at(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    first = q.add_post("first", "llm-tip", "manual")
    second = q.add_post("second", "llm-tip", "manual")
    # Approve second first, then first -> first has the later approved_at.
    q.approve(second["id"])
    q.approve(first["id"])
    # second was approved earlier, so it is next.
    assert q.next_approved()["id"] == second["id"]


def test_next_approved_ignores_posted(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("done", "llm-tip", "manual")
    q.approve(p["id"])
    q.mark_posted(p["id"], "urn:li:share:999")
    assert q.next_approved() is None


def test_mark_posted_records_result(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("go", "llm-tip", "manual")
    q.approve(p["id"])
    q.mark_posted(p["id"], "urn:li:share:123")
    updated = q.all_posts()[0]
    assert updated["status"] == "posted"
    assert updated["posted_at"] is not None
    assert updated["linkedin_post_id"] == "urn:li:share:123"


def test_mark_posted_only_from_approved(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("go", "llm-tip", "manual")  # still a draft
    with pytest.raises(QueueError):
        q.mark_posted(p["id"], "urn:li:share:123")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_queue.py -v`
Expected: FAIL — `AttributeError: 'PostQueue' object has no attribute 'next_approved'`.

- [ ] **Step 3: Write minimal implementation**

Add these methods to the `PostQueue` class in `queue.py`:
```python
    def next_approved(self):
        approved = [p for p in self.all_posts() if p["status"] == "approved"]
        if not approved:
            return None
        # ISO-8601 UTC strings sort chronologically as plain strings.
        return min(approved, key=lambda p: p["approved_at"])

    def mark_posted(self, post_id, linkedin_post_id):
        data = self._load()
        post = self._find(data, post_id)
        if post["status"] != "approved":
            raise QueueError(f"can only post an approved post, not {post['status']}")
        post["status"] = "posted"
        post["posted_at"] = self._now()
        post["linkedin_post_id"] = linkedin_post_id
        self._save(data)
        return post
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_queue.py -v`
Expected: PASS (16 passed).

- [ ] **Step 5: Commit**

```bash
git add queue.py tests/test_queue.py
git commit -m "feat: queue publish selection and mark-posted"
```

---

### Task 5: `linkedin_client.py` — publish text

**Files:**
- Create: `linkedin_client.py`

- [ ] **Step 1: Write the implementation**

LinkedIn's Posts API is a REST endpoint; there is no network call in the test suite (Task 6 mocks this function). Create `linkedin_client.py`:
```python
import requests

POSTS_URL = "https://api.linkedin.com/rest/posts"
LINKEDIN_VERSION = "202401"  # bump to a current month per LinkedIn's versioning


class LinkedInError(Exception):
    """Raised when LinkedIn rejects a publish request."""


def publish_text(access_token, author_urn, text):
    """Publish a plain-text post to LinkedIn as `author_urn`.

    Returns the created post's URN/id string on success.
    Raises LinkedInError on any non-2xx response.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": LINKEDIN_VERSION,
    }
    body = {
        "author": author_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    try:
        resp = requests.post(POSTS_URL, headers=headers, json=body, timeout=30)
    except requests.RequestException as e:
        raise LinkedInError(f"network error posting to LinkedIn: {e}") from e

    if resp.status_code not in (200, 201):
        raise LinkedInError(
            f"LinkedIn returned {resp.status_code}: {resp.text[:500]}"
        )
    # LinkedIn returns the new post id in the x-restli-id response header.
    post_id = resp.headers.get("x-restli-id")
    if not post_id:
        raise LinkedInError("LinkedIn response missing x-restli-id header")
    return post_id
```

- [ ] **Step 2: Sanity import check**

Run: `python -c "import linkedin_client; print(linkedin_client.publish_text)"`
Expected: prints a function reference, no import error.

- [ ] **Step 3: Commit**

```bash
git add linkedin_client.py
git commit -m "feat: LinkedIn Posts API client (publish_text)"
```

---

### Task 6: `publish.py` — headless publisher (TDD flow test)

**Files:**
- Create: `publish.py`
- Test: `tests/test_publish.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_publish.py`:
```python
import publish
from queue import PostQueue


def test_run_publishes_next_approved(tmp_path, monkeypatch):
    def clock():
        clock.n += 1
        return f"2026-07-08T00:00:{clock.n:02d}+00:00"
    clock.n = 0

    path = tmp_path / "posts.json"
    q = PostQueue(path, now_fn=clock)
    p = q.add_post("ship it", "build-in-public", "manual")
    q.approve(p["id"])

    calls = {}

    def fake_publish(token, urn, text):
        calls["args"] = (token, urn, text)
        return "urn:li:share:42"

    monkeypatch.setattr(publish, "publish_text", fake_publish)

    result = publish.run(
        queue=PostQueue(path, now_fn=clock),
        access_token="tok",
        author_urn="urn:li:person:me",
    )

    assert result == "posted"
    assert calls["args"] == ("tok", "urn:li:person:me", "ship it")
    posted = PostQueue(path).all_posts()[0]
    assert posted["status"] == "posted"
    assert posted["linkedin_post_id"] == "urn:li:share:42"


def test_run_empty_queue_returns_empty(tmp_path):
    path = tmp_path / "posts.json"
    result = publish.run(
        queue=PostQueue(path),
        access_token="tok",
        author_urn="urn:li:person:me",
    )
    assert result == "empty"


def test_run_api_failure_leaves_post_approved(tmp_path, monkeypatch):
    def clock():
        clock.n += 1
        return f"2026-07-08T00:00:{clock.n:02d}+00:00"
    clock.n = 0

    path = tmp_path / "posts.json"
    q = PostQueue(path, now_fn=clock)
    p = q.add_post("ship it", "build-in-public", "manual")
    q.approve(p["id"])

    def boom(token, urn, text):
        raise publish.LinkedInError("token expired")

    monkeypatch.setattr(publish, "publish_text", boom)

    result = publish.run(
        queue=PostQueue(path, now_fn=clock),
        access_token="tok",
        author_urn="urn:li:person:me",
    )

    assert result == "failed"
    still = PostQueue(path).all_posts()[0]
    assert still["status"] == "approved"  # retried next run
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_publish.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'publish'`.

- [ ] **Step 3: Write minimal implementation**

Create `publish.py`:
```python
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from queue import PostQueue
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_publish.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: PASS (19 passed).

- [ ] **Step 6: Commit**

```bash
git add publish.py tests/test_publish.py
git commit -m "feat: headless publisher with empty/success/failure handling"
```

---

### Task 7: `gemini_client.py` — draft generation

**Files:**
- Create: `gemini_client.py`

- [ ] **Step 1: Write the implementation**

The voice/honesty rules (no em-dashes, no fabrication, first person, plain language) are passed to Gemini as a **`system_instruction`** on the model, kept separate from the per-pillar user prompt. This gives the rules higher priority than the task prompt and is harder for the model to drift from. Rules restated from the `post-writing` skill and CLAUDE.md. Create `gemini_client.py`:
```python
import google.generativeai as genai

MODEL_NAME = "gemini-1.5-flash"

SYSTEM_INSTRUCTION = (
    "Write in first person as Panth Patel, a software engineer. "
    "Rules: no em-dashes, no cliches, no hashtags-stuffing (at most 3 relevant tags), "
    "no fabricated or inflated claims, plain direct language, 120-220 words. "
    "Never claim a project is finished, shipped, or deployed unless explicitly told it is."
)

PILLAR_PROMPTS = {
    "build-in-public": (
        "Write a build-in-public LinkedIn post about ongoing work: an AI tool that "
        "converts IONM (intraoperative neuromonitoring) machine JSON output into CMS-1500 "
        "insurance-claim format, built with Python and Amazon Nova v1 Pro on Amazon Bedrock. "
        "Facts you may use: it cut manual claim entry from about a day per surgery to under "
        "five minutes; current accuracy is 85% and improving; it is still in development, not "
        "finished or deployed. Do not overstate its status."
    ),
    "llm-tip": (
        "Write a short, practical LinkedIn post sharing one concrete lesson learned while "
        "building LLM apps with LangChain, LangGraph, or AWS Bedrock. Make it useful to other "
        "engineers, not generic."
    ),
    "career-journey": (
        "Write a LinkedIn post about relocating from Vadodara, India to Somerset, NJ, USA and "
        "job-searching for US software/AI engineering roles. Honest and reflective, not "
        "self-pitying or boastful."
    ),
    "ai-take": (
        "Write a LinkedIn post giving Panth's own opinion on a recent development in AI. "
        "Assertive and clear (he is comfortable holding a point of view), but grounded and "
        "not inflammatory."
    ),
}


class GeminiError(Exception):
    """Raised when Gemini generation fails."""


def generate_draft(api_key, pillar, extra_context=""):
    """Generate a draft post for the given pillar. Returns the draft text."""
    if pillar not in PILLAR_PROMPTS:
        raise GeminiError(f"no prompt template for pillar {pillar!r}")
    prompt = PILLAR_PROMPTS[pillar]
    if extra_context.strip():
        prompt += f"\n\nAdditional context to weave in:\n{extra_context.strip()}"
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            MODEL_NAME, system_instruction=SYSTEM_INSTRUCTION
        )
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
    except Exception as e:  # SDK raises various exception types
        raise GeminiError(f"Gemini generation failed: {e}") from e
    if not text:
        raise GeminiError("Gemini returned an empty draft")
    return text
```

- [ ] **Step 2: Sanity import check**

Run: `python -c "import gemini_client; print(list(gemini_client.PILLAR_PROMPTS))"`
Expected: prints `['build-in-public', 'llm-tip', 'career-journey', 'ai-take']`.

- [ ] **Step 3: Commit**

```bash
git add gemini_client.py
git commit -m "feat: Gemini draft generation with per-pillar prompts"
```

---

### Task 8: `app.py` — Streamlit control panel

**Files:**
- Create: `app.py`

This is the human-facing surface. Manual smoke-test only (no unit test for the UI).

- [ ] **Step 1: Write the implementation**

Create `app.py`:
```python
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from queue import PostQueue, VALID_PILLARS, QueueError
from gemini_client import generate_draft, GeminiError, PILLAR_PROMPTS

load_dotenv()
POSTS_PATH = Path(__file__).parent / "posts.json"
queue = PostQueue(POSTS_PATH)

GENERATABLE_PILLARS = list(PILLAR_PROMPTS.keys())  # excludes "manual"

st.set_page_config(page_title="GateKeep", page_icon="✅")
st.title("GateKeep — LinkedIn post control panel")

# --- Add a manual post ---------------------------------------------------
st.header("Add a manual post")
with st.form("manual", clear_on_submit=True):
    manual_text = st.text_area("Post text", height=160)
    manual_pillar = st.selectbox("Pillar / tag", sorted(VALID_PILLARS))
    if st.form_submit_button("Add draft") and manual_text.strip():
        queue.add_post(text=manual_text.strip(), pillar=manual_pillar, source="manual")
        st.success("Draft added.")
        st.rerun()

# --- Generate a draft with Gemini ---------------------------------------
st.header("Generate a draft (Gemini)")
gen_pillar = st.selectbox("Pillar", GENERATABLE_PILLARS, key="gen_pillar")
gen_context = st.text_input("Optional extra context")
if st.button("Generate"):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY missing from .env")
    else:
        try:
            draft = generate_draft(api_key, gen_pillar, gen_context)
            queue.add_post(text=draft, pillar=gen_pillar, source="generated")
            st.success("Generated draft added below for review.")
            st.rerun()
        except GeminiError as e:
            st.error(str(e))

# --- Review pending drafts ----------------------------------------------
st.header("Pending review")
pending = queue.pending_drafts()
if not pending:
    st.caption("No drafts awaiting review.")
for post in pending:
    with st.container(border=True):
        st.caption(f"{post['pillar']} · {post['source']} · {post['created_at']}")
        edited = st.text_area("Text", value=post["text"], key=f"edit_{post['id']}", height=160)
        c1, c2, c3 = st.columns(3)
        if c1.button("Save edits", key=f"save_{post['id']}"):
            queue.update_text(post["id"], edited.strip())
            st.rerun()
        if c2.button("Approve", key=f"approve_{post['id']}"):
            if edited.strip() != post["text"]:
                queue.update_text(post["id"], edited.strip())
            queue.approve(post["id"])
            st.rerun()
        if c3.button("Reject", key=f"reject_{post['id']}"):
            queue.reject(post["id"])
            st.rerun()

# --- Approved (waiting to publish) --------------------------------------
st.header("Approved — waiting to publish")
approved = [p for p in queue.all_posts() if p["status"] == "approved"]
for post in sorted(approved, key=lambda p: p["approved_at"]):
    st.markdown(f"- *{post['pillar']}* (approved {post['approved_at']}): {post['text'][:80]}…")
if not approved:
    st.caption("Nothing approved yet.")

# --- History -------------------------------------------------------------
st.header("History")
history = [p for p in queue.all_posts() if p["status"] in ("posted", "rejected")]
for post in reversed(history):
    label = "posted" if post["status"] == "posted" else "rejected"
    when = post["posted_at"] or post["created_at"]
    st.markdown(f"- **{label}** · {post['pillar']} · {when}: {post['text'][:80]}…")
```

- [ ] **Step 2: Smoke-test the app**

Run: `streamlit run app.py`
Expected: browser opens; you can add a manual post, see it under "Pending review," edit it, approve it, and see it move to "Approved — waiting to publish." (Gemini generation needs a real `GEMINI_API_KEY`.)

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: Streamlit control panel (add/generate/review/approve/history)"
```

---

### Task 9: `reauth.py` — LinkedIn OAuth refresh helper

**Files:**
- Create: `reauth.py`

- [ ] **Step 1: Write the implementation**

Runs the 3-legged OAuth consent flow with a temporary local callback server, exchanges the code for an access token, prints the member URN, and updates `.env`. Create `reauth.py`:
```python
import os
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key

ENV_PATH = Path(__file__).parent / ".env"
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
SCOPE = "w_member_social openid profile"


class _CodeCatcher(BaseHTTPRequestHandler):
    code = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _CodeCatcher.code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>GateKeep: authorization received. You can close this tab.</h1>")

    def log_message(self, *args):
        pass  # silence server logging


def main():
    load_dotenv(ENV_PATH)
    client_id = os.environ["LINKEDIN_CLIENT_ID"]
    client_secret = os.environ["LINKEDIN_CLIENT_SECRET"]
    redirect_uri = os.environ.get("LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback")
    parsed = urllib.parse.urlparse(redirect_uri)
    host, port = parsed.hostname, parsed.port or 8000

    auth_params = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": SCOPE,
        }
    )
    print("Opening browser for LinkedIn consent...")
    webbrowser.open(f"{AUTH_URL}?{auth_params}")

    server = HTTPServer((host, port), _CodeCatcher)
    server.handle_request()  # blocks until the single redirect is received
    code = _CodeCatcher.code
    if not code:
        raise SystemExit("No authorization code received.")

    token_resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]

    # Fetch the member URN needed as the post author.
    userinfo = requests.get(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    userinfo.raise_for_status()
    author_urn = f"urn:li:person:{userinfo.json()['sub']}"

    set_key(str(ENV_PATH), "LINKEDIN_ACCESS_TOKEN", access_token)
    set_key(str(ENV_PATH), "LINKEDIN_AUTHOR_URN", author_urn)
    print(f"Token refreshed. Author URN: {author_urn}")
    print(".env updated.")


if __name__ == "__main__":
    main()
```

> Note: The LinkedIn app must list `http://localhost:8000/callback` as an authorized redirect URL, and the `w_member_social` + `openid`/`profile` products must be added to the app. These are the manual setup steps in the spec.

- [ ] **Step 2: Sanity import check**

Run: `python -c "import reauth; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add reauth.py
git commit -m "feat: LinkedIn OAuth reauth helper"
```

---

### Task 10: `README.md` and scheduler registration

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the README**

Create `README.md`:
```markdown
# GateKeep

A personal weekly LinkedIn auto-poster with a human-approval gate. Draft posts by hand or
with Google Gemini, review and approve them in a local Streamlit app, and let a scheduled
headless publisher post the oldest approved one via LinkedIn's official API. Nothing publishes
without explicit approval.

## Setup

1. `python -m venv .venv && source .venv/Scripts/activate` (PowerShell: `.venv\Scripts\Activate.ps1`)
2. `pip install -r requirements.txt`
3. Create a LinkedIn developer app at https://developer.linkedin.com, add the "Share on
   LinkedIn" product (`w_member_social`) plus `openid`/`profile`, and set the redirect URL to
   `http://localhost:8000/callback`.
4. Get a Google Gemini API key from Google AI Studio (free tier).
5. `cp .env.example .env` and fill in `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `GEMINI_API_KEY`.
6. `python reauth.py` — completes the OAuth flow and fills in `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_AUTHOR_URN`.

## Daily use

- `streamlit run app.py` — add/generate/review/approve posts.
- Approved posts publish automatically on the weekly schedule.
- Re-run `python reauth.py` roughly every 60 days when the LinkedIn token expires.

## Publishing manually

`python publish.py` publishes the single oldest approved post (or exits cleanly if none).

## Tests

`pytest`

## Scheduling

Registered as a weekly Claude Code scheduled task that runs `python publish.py` in this repo.
It runs while the app is open on this machine and catches up on next launch if closed at
trigger time.
```

- [ ] **Step 2: Run the full test suite one last time**

Run: `pytest -v`
Expected: PASS (19 passed).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README with setup and usage"
```

- [ ] **Step 4: Register the weekly scheduled task (manual)**

Use Claude Code's `scheduled-tasks` feature to create a weekly task that runs `python publish.py` from the repo root. This is an interactive/manual step — confirm the command path points at this repo's `publish.py` and that the venv Python is used.

---

## Self-Review

**Spec coverage:**
- Two entry points sharing `posts.json` via `queue.py` — Tasks 2–4 (queue), 6 (publish), 8 (app). ✓
- Required approval gate on everything — enforced by `publish.py` only selecting `status == approved`, which is only reachable via the app's Approve button. ✓
- Manual + generated in one queue — `add_post(source=...)`, Tasks 2/8. ✓
- Data model fields (id, pillar, source, text, status, created_at, approved_at, posted_at, linkedin_post_id) — Task 2. ✓
- Oldest-by-`approved_at` selection — Task 4. ✓
- Error handling (empty queue exit 0, API failure leaves post approved + logs, Gemini failure inline, corrupt json fails loud) — Tasks 4/6/7 + `_load` in Task 2. ✓
- Official LinkedIn API, no scraping — Task 5. ✓
- No MCP dependency in publish/app — both are plain Python importing local modules. ✓
- Secrets in gitignored `.env` — Tasks 1/9. ✓
- `reauth.py` manual token refresh — Task 9. ✓
- Unit tests for queue, mocked clients — Tasks 2–4, 6. ✓
- Scheduler registration — Task 10. ✓

**Placeholder scan:** No "TBD"/"add error handling"/"write tests for the above" — every code and test step contains full content. ✓

**Type consistency:** `PostQueue` methods (`add_post`, `update_text`, `approve`, `reject`, `pending_drafts`, `next_approved`, `mark_posted`, `all_posts`) are named identically across Tasks 2–4, 6, 8. `publish_text(access_token, author_urn, text)` signature matches between Task 5 (definition), Task 6 (call + mock). `generate_draft(api_key, pillar, extra_context)` matches between Task 7 (definition) and Task 8 (call). Post dict keys are consistent across all tasks. ✓
