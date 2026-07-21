import pytest

import linkedin_client
from linkedin_client import publish_text, LinkedInError, _escape_commentary


class FakeResp:
    def __init__(self, status_code, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


def _fake_post_sequence(responses):
    seq = iter(responses)
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(headers["LinkedIn-Version"])
        return next(seq)

    fake_post.calls = calls
    return fake_post


@pytest.fixture(autouse=True)
def _no_env_version(monkeypatch):
    # Keep tests independent of any LINKEDIN_API_VERSION in the real environment.
    monkeypatch.delenv("LINKEDIN_API_VERSION", raising=False)


def test_publish_success_first_version(monkeypatch):
    fp = _fake_post_sequence([FakeResp(201, headers={"x-restli-id": "urn:li:share:1"})])
    monkeypatch.setattr(linkedin_client.requests, "post", fp)
    assert publish_text("t", "urn:li:person:x", "hi") == "urn:li:share:1"
    assert len(fp.calls) == 1


def test_publish_falls_back_on_retired_version(monkeypatch):
    fp = _fake_post_sequence(
        [
            FakeResp(426, text='{"code":"NONEXISTENT_VERSION"}'),
            FakeResp(201, headers={"x-restli-id": "urn:li:share:2"}),
        ]
    )
    monkeypatch.setattr(linkedin_client.requests, "post", fp)
    assert publish_text("t", "urn:li:person:x", "hi") == "urn:li:share:2"
    assert len(fp.calls) == 2  # first retired, second accepted


def test_publish_non_version_error_raises_immediately(monkeypatch):
    fp = _fake_post_sequence([FakeResp(403, text="forbidden")])
    monkeypatch.setattr(linkedin_client.requests, "post", fp)
    with pytest.raises(LinkedInError):
        publish_text("t", "urn:li:person:x", "hi")
    assert len(fp.calls) == 1  # non-version error does not retry


def test_publish_all_versions_retired_raises(monkeypatch):
    fp = _fake_post_sequence([FakeResp(426, text="NONEXISTENT_VERSION")] * 20)
    monkeypatch.setattr(linkedin_client.requests, "post", fp)
    with pytest.raises(LinkedInError) as exc:
        publish_text("t", "urn:li:person:x", "hi")
    assert "no active LinkedIn-Version" in str(exc.value)


def test_escape_commentary_escapes_reserved_keeps_hash():
    assert (
        _escape_commentary("IONM (x) *a* _b_ #tag")
        == "IONM \\(x\\) \\*a\\* \\_b\\_ #tag"
    )


def test_escape_commentary_escapes_backslash():
    assert _escape_commentary("a\\b") == "a\\\\b"


def test_publish_sends_escaped_commentary(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["json"] = json
        return FakeResp(201, headers={"x-restli-id": "urn:li:share:9"})

    monkeypatch.setattr(linkedin_client.requests, "post", fake_post)
    publish_text("t", "urn:li:person:x", "see (this) and #tag")
    assert captured["json"]["commentary"] == "see \\(this\\) and #tag"
