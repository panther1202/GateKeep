# GateKeep — LinkedIn Weekly Auto-Poster

## What this project is

**GateKeep** is a personal automation tool for Panth Patel: a weekly LinkedIn posting pipeline with a human-approval gate, built partly to grow his LinkedIn engagement during a US job search, and partly as a standalone portfolio project in its own right.

Design is complete and approved. Full spec: [docs/superpowers/specs/2026-07-08-linkedin-auto-poster-design.md](docs/superpowers/specs/2026-07-08-linkedin-auto-poster-design.md). **Next step for a new session: read that spec, then invoke the `superpowers:writing-plans` skill to produce an implementation plan.** Do not start implementing before that.

## Who this is for (context a fresh session won't have)

Panth Patel - Software Engineer at Sunflower Labs (Python, AI team), based in Vadodara, India, relocating to Somerset, NJ, USA within a couple months. Job-search targets US roles: Software Engineer (Python), AI Engineer, Backend/Full Stack Engineer. LinkedIn: https://www.linkedin.com/in/panthpatel0122/

His full career profile (education, experience, skills, behavioral/DISC assessment) lives in a **separate, related repo** on the same machine: `C:\Users\Admin\Desktop\ai-job-search` (also present as `C:\Users\Admin\Desktop\job finder\ai-job-search` - same content, treat as the same repo). Relevant files there if a post needs a fact-check or more detail:
- `ai-job-search/CLAUDE.md` - full profile summary
- `ai-job-search/.claude/skills/job-application-assistant/01-candidate-profile.md` - structured profile
- `ai-job-search/.claude/skills/job-application-assistant/02-behavioral-profile.md` - DISC (Dominance/Influence) behavioral profile
- `ai-job-search/.claude/skills/job-application-assistant/03-writing-style.md` - writing rules (no em-dashes, no cliches, no unverified claims) that should also govern LinkedIn post tone, since the same honesty/verification standard applies here

## Content pillars (source material for generated and manual posts)

1. **build-in-public** - progress on his current work project: an AI tool converting IONM (intraoperative neuromonitoring) machine JSON output into CMS 1500 insurance-claim format, built with Python + Amazon Nova v1 Pro on Amazon Bedrock. Real, ongoing, in development. Cut manual claim entry from ~1 day/surgery to under 5 minutes; currently 85% accuracy, improving. Do not claim it is finished or deployed - it is not.
2. **llm-tip** - short lessons learned using LangChain/LangGraph/AWS Bedrock.
3. **career-journey** - the India-to-US relocation and job search narrative.
4. **ai-take** - his own opinion on AI industry news (leverages his DISC Dominance/Influence profile - assertive, sociable, comfortable with a point of view).

**Critical constraint carried over from the ai-job-search project's own rules: never fabricate or inflate claims.** Panth's actual LinkedIn profile was already caught making unverifiable claims (a "Manager" role and "Agile/Scrum leadership" that didn't correspond to any real position) and those were removed during profile cleanup. Any generated post content must be checked against what's actually true - a discontinued project must say "70% complete, discontinued by client," not "shipped."

## MCP connectors: none required

This project does not use MCP servers for LinkedIn or Gemini. `publish.py` must run as a plain standalone Python script (invoked by the scheduled task via a shell command), independent of any Claude session or MCP tool availability - so it talks to both APIs directly over HTTP (`requests`/official SDKs), not through MCP. Do not introduce an MCP-based integration for the publish path; it would break headless/scheduled execution. Streamlit's `app.py` similarly should not depend on MCP tools, for the same reason (it's also meant to be run directly, not just from inside a Claude session).

## Key implementation constraints (from the design spec, worth restating)

- **Every post requires manual approval before publishing** - no exceptions, regardless of whether it was hand-written or LLM-generated.
- Scheduler is Claude Code's built-in `scheduled-tasks` feature - runs while the app is open on this machine (not a cloud-independent agent); catches up on next launch if the app was closed at trigger time.
- LinkedIn posting must go through LinkedIn's **official API** (Community Management API, `w_member_social` scope). Browser automation/scraping to post is a ToS violation and out of scope - never build that instead.
- Secrets (LinkedIn token, Gemini API key) live in a local `.env` file, gitignored, never committed.
- Generation LLM is Google Gemini (free tier).
