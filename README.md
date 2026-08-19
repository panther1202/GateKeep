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

## Documentation

Full technical docs live in [`docs/`](docs/README.md):

- [use-case.md](docs/use-case.md) — who it is for, the problem, the workflow, constraints
- [architecture.md](docs/architecture.md) — components, `posts.json` model, state machine, data flow
- [models.md](docs/models.md) — Gemini 2.5 Flash generation, prompts, honesty guardrails
- [api.md](docs/api.md) — LinkedIn (OAuth + Posts) and Gemini API reference

## Layout

| File | Role |
|---|---|
| `app.py` | Streamlit control panel (the only human-facing surface) |
| `publish.py` | Headless weekly publisher |
| `post_queue.py` | Shared `posts.json` read/write/query logic |
| `linkedin_client.py` | LinkedIn Posts API wrapper |
| `gemini_client.py` | Gemini draft-generation wrapper |
| `reauth.py` | Manual LinkedIn OAuth token refresh |
