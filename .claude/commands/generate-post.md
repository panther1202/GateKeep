# /generate-post - Draft a New Post via Gemini

Generate a new LinkedIn post draft and add it to the queue as `status: draft`.

## Steps

1. If `$ARGUMENTS` names a pillar (`build-in-public`, `llm-tip`, `career-journey`, `ai-take`), use it. Otherwise ask the user which pillar, or suggest one based on what's least-recently used in `posts.json`.
2. Read the pillar's source material from `CLAUDE.md` (content pillars section) - do not invent facts not present there or in the linked `ai-job-search` profile files.
3. Apply the writing rules from `.claude/skills/post-writing/SKILL.md` (voice, structure, honesty constraints).
4. Call `gemini_client.py` to draft the post text.
5. Append the result to `posts.json` via `queue.py` as a new entry: `source: generated`, `status: draft`, `pillar: <chosen pillar>`.
6. Show the drafted text to the user directly in this conversation (don't make them open Streamlit just to see it) and remind them it still needs approval - either here by explicit confirmation (which you then apply via `queue.py`), or later in the Streamlit app.

## Notes

- This command drafts into the queue; it does not publish. Publishing only happens via the scheduled `publish.py` run on posts with `status: approved`.
- If Gemini generation fails, report the error - do not fall back to writing the post yourself unprompted, since that would bypass the intended generation path silently. Ask the user how they want to proceed.
