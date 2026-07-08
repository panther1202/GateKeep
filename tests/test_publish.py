import publish
from post_queue import PostQueue


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
