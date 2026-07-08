# LinkedIn Weekly Auto-Poster - Design

Date: 2026-07-08
Owner: Panth Patel

## Purpose

Automate weekly posting to Panth's LinkedIn profile to build engagement/visibility during his US job search. Content can be written by hand or drafted with an LLM (Google Gemini, free tier), but nothing publishes without explicit human approval. Publishing itself runs on a schedule with no manual step required once a post is approved.

This is also intended as a standalone personal/portfolio project - own repo, own git history.

## Non-goals (v1)

- No fully autonomous posting (every post requires approval regardless of source - see Decisions)
- No automatic LinkedIn OAuth token refresh (manual re-auth every ~60 days, see Token Refresh)
- No image/media post support (text-only posts for v1)
- No multi-platform posting (LinkedIn only)

## Key Decisions

| Decision | Choice | Why |
|---|---|---|
| Location | New standalone repo: `C:\Users\Admin\Desktop\GateKeep` | Doubles as its own portfolio project, not entangled with ai-job-search |
| Content sources | Both: manual entries + Gemini-generated drafts, same queue | User wants both; unified queue keeps publish logic simple |
| Approval gate | **Required on everything**, manual and generated alike | LLM-drafted posts under a real name carry factual/tone risk; user explicitly chose the strictest option over "AI-only gate" or "no gate" |
| Approval UI | Streamlit local web app | User's preference over CLI-only or hand-editing the queue file |
| Scheduler | Claude Code's built-in `scheduled-tasks` (runs while the app is open on this machine; catches up on next launch if closed at trigger time) | No cloud VM or Windows Task Scheduler needed; runs with direct local file access, no git push/pull round-trip required |
| Publish mechanism | Official LinkedIn API (Community Management API / `w_member_social` scope via a self-service "Share on LinkedIn" app) | Browser-automation/scraping-based posting violates LinkedIn ToS and risks account ban - explicitly ruled out |
| Generation LLM | Google Gemini (free tier) | User already plans to hold a Gemini API key |
| Secrets storage | Local `.env` file, gitignored | Simplest safe option for a single-user local tool; user confirmed |

## Architecture

Two entry points sharing one data file (`posts.json`) and one shared module (`queue.py`) for reading/writing it:

```
┌─────────────────┐         ┌──────────────────┐
│  app.py          │         │  publish.py       │
│  (Streamlit)     │         │  (headless)       │
│                  │         │                   │
│ - add manual post│         │ - read posts.json │
│ - generate draft │ ──────► │ - find oldest     │
│   (Gemini)       │ posts   │   status=approved │
│ - review/edit/   │  .json  │ - POST to LinkedIn│
│   approve/reject │ ◄────── │ - mark posted     │
│ - view history   │         │                   │
└─────────────────┘         └──────────────────┘
        │                            │
        ▼                            ▼
   gemini_client.py            linkedin_client.py
```

- **app.py** (Streamlit): the only human-facing surface. Run manually, on demand, whenever Panth wants to add or review content. Not scheduled.
- **publish.py**: no UI. Invoked weekly by a Claude Code scheduled task. Does one thing: publish the next approved post, or exit cleanly if the queue has none.
- **queue.py**: shared read/write/query logic over `posts.json`, used by both entry points. Single source of truth for what "next approved post" means (oldest by `approved_at`).
- **linkedin_client.py**: thin wrapper around LinkedIn's Community Management API (`w_member_social` scope). Used only by `publish.py`.
- **gemini_client.py**: thin wrapper around the Gemini API for draft generation. Used only by `app.py`.
- **reauth.py**: standalone manual script to redo the LinkedIn OAuth consent flow and refresh the token in `.env`. Run by Panth every ~60 days when the token expires.

## Data Model

`posts.json`:

```json
{
  "posts": [
    {
      "id": "uuid",
      "pillar": "build-in-public | llm-tip | career-journey | ai-take | manual",
      "source": "manual | generated",
      "text": "...",
      "status": "draft | approved | rejected | posted",
      "created_at": "ISO timestamp",
      "approved_at": "ISO timestamp | null",
      "posted_at": "ISO timestamp | null",
      "linkedin_post_id": "string | null"
    }
  ]
}
```

Content pillars (used both as generation prompts in Gemini and as free-form tags for manual posts):
1. **build-in-public** - progress on the IONM-to-CMS1500 AI tool (accuracy milestones, technical tradeoffs)
2. **llm-tip** - short LangChain/AWS Bedrock lessons learned
3. **career-journey** - India-to-US relocation and job search narrative
4. **ai-take** - Panth's own opinion on AI industry news

`posts.json` itself is gitignored (contains personal drafts/opinions, not meant to be public repo content even though the repo is a portfolio piece - the code is the portfolio artifact, not the post drafts).

## Data Flow

1. **Draft creation** (via Streamlit): Panth either types a post directly (`source: manual`, `status: draft`) or picks a pillar and clicks "Generate," which calls `gemini_client.py`, and the result is appended to `posts.json` as `source: generated`, `status: draft`.
2. **Review** (via Streamlit): pending drafts are listed; Panth can edit the text inline, then Approve (→ `status: approved`, stamps `approved_at`) or Reject (→ `status: rejected`, kept for history, excluded from publish selection).
3. **Publish** (via scheduled `publish.py`, weekly): reads `posts.json`, filters `status == approved`, picks the one with the oldest `approved_at`. Calls `linkedin_client.py` to POST it. On success: `status: posted`, stamps `posted_at`, stores `linkedin_post_id`. On failure: post stays `approved` (retried next run), error is logged.

## Error Handling

- **Empty approved queue**: `publish.py` logs a warning and exits 0 (not an error state). The scheduled task's completion notification surfaces this so Panth knows to approve more posts.
- **LinkedIn API failure** (expired token, rate limit, network error): logged to `logs/publish.log` with full error detail; post remains `approved` so the next scheduled run retries it automatically; scheduled-task notification surfaces the failure.
- **Gemini generation failure**: surfaced inline in the Streamlit UI as an error message; nothing is written to `posts.json` on failure.
- **Malformed/corrupt `posts.json`**: both entry points fail loudly on startup (no silent data loss) rather than attempting auto-repair.

## Token Refresh (explicitly out of scope for automation in v1)

LinkedIn's OAuth access token expires roughly every 60 days. `reauth.py` is a manual script Panth runs periodically: it walks through the OAuth consent flow again (opens LinkedIn's auth page, captures the redirect, exchanges the code for a new token) and overwrites the token in `.env`. No auto-refresh, no expiry-tracking automation in v1 - this is a known, accepted manual step.

## Testing

- Unit tests for `queue.py`: read/write round-trip, "pick oldest approved" selection logic, status transitions.
- `linkedin_client.py` and `gemini_client.py` calls are mocked in tests - no real network calls in the test suite.
- No end-to-end test against the live LinkedIn API (would post for real); manual smoke-test only.

## Folder Structure

```
GateKeep/
├── .env                  (gitignored - LinkedIn token, Gemini key)
├── .gitignore
├── posts.json            (gitignored - personal draft content)
├── app.py                (Streamlit control panel)
├── publish.py            (headless weekly publisher)
├── reauth.py             (manual LinkedIn OAuth refresh helper)
├── linkedin_client.py    (LinkedIn API wrapper)
├── gemini_client.py      (Gemini API wrapper)
├── queue.py              (shared posts.json read/write logic)
├── tests/
│   └── test_queue.py
├── requirements.txt
└── README.md
```

## Setup Steps Requiring Manual/Interactive Action (cannot be automated by Claude)

1. Create a LinkedIn Developer app at developer.linkedin.com, request the "Share on LinkedIn" product (`w_member_social` scope).
2. Complete the OAuth consent flow as Panth's own LinkedIn account to obtain the initial access token (interactive browser login - Panth does this himself).
3. Obtain a Google Gemini API key (free tier) from Google AI Studio.
4. Populate `.env` with both credentials.
5. Register the weekly run in Claude Code's `scheduled-tasks` pointing at `publish.py` in this repo.
