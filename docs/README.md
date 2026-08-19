# GateKeep Documentation

GateKeep is a personal, single-user LinkedIn posting pipeline with a mandatory
human-approval gate. Posts are drafted by hand or generated with Google Gemini,
reviewed and approved in a local Streamlit app, and published to LinkedIn through
its official API — either on a weekly schedule or on demand. **Nothing reaches
LinkedIn without an explicit human approval click.**

## Documentation map

| Document | What it covers | Read it when |
|---|---|---|
| [use-case.md](use-case.md) | Who this is for, the problem it solves, the end-to-end workflow, and design constraints | You want to understand *why* GateKeep exists and how it is used day to day |
| [architecture.md](architecture.md) | Components, the `posts.json` data model, state machine, data flow, and key design decisions | You are modifying the code or need the system's shape |
| [models.md](models.md) | The generation model (Gemini 2.5 Flash), prompt design, the honesty guardrails, and the LLM inside the *subject* project (Amazon Nova) | You are tuning generation quality or auditing what the model is told |
| [api.md](api.md) | The two external HTTP APIs — LinkedIn (OAuth + Posts) and Gemini — with request/response shapes, auth, versioning, and error handling | You are debugging a publish failure or the OAuth flow |

## Quick orientation

```
Draft (manual or Gemini)  →  Review + Approve (human)  →  Publish (LinkedIn API)
        app.py                     app.py                  publish.py / app.py
```

- **Human surface:** `app.py` (Streamlit). The only place a human interacts.
- **Headless publisher:** `publish.py` (plain Python, runnable from a scheduled task).
- **Shared state:** `posts.json`, a flat file managed by `post_queue.py`.
- **API wrappers:** `linkedin_client.py`, `gemini_client.py`.
- **Token refresh:** `reauth.py` (LinkedIn OAuth).

## Project facts

- **Owner:** Panth Patel — Software/AI Engineer.
- **Purpose:** grow LinkedIn engagement during a US job search; also a standalone portfolio project.
- **Stack:** Python 3.13, Streamlit, `requests`, `google-generativeai`, `python-dotenv`.
- **No MCP dependency:** the publish and generation paths talk to APIs directly over HTTP so they run headless, independent of any Claude/MCP session.
- **Secrets:** live in a gitignored `.env`, never committed.

See the root [README.md](../README.md) for setup and the design spec at
[docs/superpowers/specs/2026-07-08-linkedin-auto-poster-design.md](superpowers/specs/2026-07-08-linkedin-auto-poster-design.md).
