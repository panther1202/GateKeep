import os

import requests

POSTS_URL = "https://api.linkedin.com/rest/posts"
# LinkedIn versions (YYYYMM) are retired roughly yearly. `publish_text` tries
# the configured version first, then these fallbacks (newest first) if LinkedIn
# reports the version is not active. Override the primary via LINKEDIN_API_VERSION
# in .env. Refresh this list when they all eventually lapse.
DEFAULT_LINKEDIN_VERSION = "202606"
FALLBACK_VERSIONS = ["202607", "202606", "202605", "202603", "202601", "202509"]


class LinkedInError(Exception):
    """Raised when LinkedIn rejects a publish request."""


def _post_once(access_token, author_urn, text, version):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": version,
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
        return requests.post(POSTS_URL, headers=headers, json=body, timeout=30)
    except requests.RequestException as e:
        raise LinkedInError(f"network error posting to LinkedIn: {e}") from e


def _is_retired_version(resp):
    return resp.status_code == 426 and "NONEXISTENT_VERSION" in resp.text


def publish_text(access_token, author_urn, text):
    """Publish a plain-text post to LinkedIn as `author_urn`.

    Tries the configured LinkedIn-Version first, then FALLBACK_VERSIONS if the
    version is reported retired (426 NONEXISTENT_VERSION). Returns the created
    post's URN/id on success. Raises LinkedInError on any other failure, or if
    no version LinkedIn accepts is found.
    """
    primary = os.environ.get("LINKEDIN_API_VERSION", DEFAULT_LINKEDIN_VERSION)
    # Ordered, de-duplicated: primary first, then the fallbacks.
    versions = [primary] + [v for v in FALLBACK_VERSIONS if v != primary]

    tried_retired = []
    for version in versions:
        resp = _post_once(access_token, author_urn, text, version)
        if _is_retired_version(resp):
            tried_retired.append(version)
            continue  # a 426 means nothing was posted; safe to retry
        if resp.status_code not in (200, 201):
            raise LinkedInError(
                f"LinkedIn returned {resp.status_code}: {resp.text[:500]}"
            )
        # LinkedIn returns the new post id in the x-restli-id response header.
        post_id = resp.headers.get("x-restli-id")
        if not post_id:
            raise LinkedInError("LinkedIn response missing x-restli-id header")
        return post_id

    raise LinkedInError(
        "no active LinkedIn-Version found; all retired: "
        f"{tried_retired}. Set a current LINKEDIN_API_VERSION in .env."
    )
