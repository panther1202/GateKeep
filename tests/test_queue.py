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
