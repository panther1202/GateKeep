import os
import socket
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


class _DualStackServer(HTTPServer):
    """Listen on both IPv4 and IPv6 loopback.

    Plain HTTPServer binds IPv4 127.0.0.1 only. On Windows, browsers often
    resolve `localhost` to IPv6 ::1 first and get "connection refused" while
    the server waits on 127.0.0.1. Binding an IPv6 socket with IPV6_V6ONLY=0
    accepts both stacks, so the OAuth callback is caught either way.
    """

    address_family = socket.AF_INET6

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            pass  # not supported here; IPv6-only bind still handles ::1
        super().server_bind()


def main():
    load_dotenv(ENV_PATH)
    client_id = os.environ["LINKEDIN_CLIENT_ID"]
    client_secret = os.environ["LINKEDIN_CLIENT_SECRET"]
    redirect_uri = os.environ.get("LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback")
    parsed = urllib.parse.urlparse(redirect_uri)
    port = parsed.port or 8000

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

    server = _DualStackServer(("", port), _CodeCatcher)
    print(f"Waiting for LinkedIn to redirect back to {redirect_uri} ...")
    # Keep serving until the callback carrying ?code= arrives. This tolerates
    # stray requests (favicon, prefetch) that would otherwise consume a single
    # handle_request() call and abort the flow before the real callback.
    while _CodeCatcher.code is None:
        server.handle_request()
    code = _CodeCatcher.code

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
