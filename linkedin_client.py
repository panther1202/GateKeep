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
