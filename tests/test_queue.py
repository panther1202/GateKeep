import json
import pytest
from post_queue import PostQueue, QueueError


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


def test_update_text_only_on_draft(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("old", "manual", "manual")
    q.update_text(p["id"], "new")
    assert q.all_posts()[0]["text"] == "new"


def test_update_text_on_approved_post(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("old", "manual", "manual")
    q.approve(p["id"])
    q.update_text(p["id"], "edited after approval")
    updated = q.all_posts()[0]
    assert updated["text"] == "edited after approval"
    assert updated["status"] == "approved"  # stays approved, no re-review needed


def test_update_text_rejects_posted(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("x", "manual", "manual")
    q.approve(p["id"])
    q.mark_posted(p["id"], "urn:li:share:1")
    with pytest.raises(QueueError):
        q.update_text(p["id"], "too late")


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


def test_delete_removes_a_draft(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    a = q.add_post("a", "llm-tip", "manual")
    b = q.add_post("b", "llm-tip", "manual")
    deleted = q.delete_post(a["id"])
    assert deleted["id"] == a["id"]
    remaining = [p["id"] for p in q.all_posts()]
    assert remaining == [b["id"]]


def test_delete_removes_an_approved_post(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("a", "llm-tip", "manual")
    q.approve(p["id"])
    q.delete_post(p["id"])
    assert q.all_posts() == []


def test_delete_rejects_posted(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("a", "llm-tip", "manual")
    q.approve(p["id"])
    q.mark_posted(p["id"], "urn:li:share:1")
    with pytest.raises(QueueError):
        q.delete_post(p["id"])  # posted history is protected


def test_delete_rejects_rejected(tmp_path):
    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("a", "llm-tip", "manual")
    q.reject(p["id"])
    with pytest.raises(QueueError):
        q.delete_post(p["id"])  # rejected history is protected


def test_delete_unknown_id_raises(tmp_path):
    q = PostQueue(tmp_path / "posts.json")
    with pytest.raises(QueueError):
        q.delete_post("no-such-id")


def test_dev_perspective_is_a_valid_pillar(tmp_path):
    from gemini_client import GENERATABLE_PILLARS

    q = PostQueue(tmp_path / "posts.json", now_fn=_fixed_clock())
    p = q.add_post("dev post", "dev-perspective", "manual")
    assert p["pillar"] == "dev-perspective"
    # Also a label the model may tag a draft with.
    assert "dev-perspective" in GENERATABLE_PILLARS
