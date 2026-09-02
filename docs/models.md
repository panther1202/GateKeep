# Models

Two distinct AI models appear in this project. Do not confuse them:

1. **The generation model** — Google **Gemini 2.5 Flash**, which drafts LinkedIn
   posts inside GateKeep itself.
2. **The subject model** — Amazon **Nova v1 Pro** on Bedrock, which powers the
   *IONM-to-CMS-1500 tool that some posts are about*. GateKeep does not call
   Nova; it only writes about it.

## 1. Generation model — Gemini 2.5 Flash

| Property | Value |
|---|---|
| Model id | `gemini-2.5-flash` (`gemini_client.MODEL_NAME`) |
| SDK | `google-generativeai` 0.8.3 |
| Access | Google AI Studio API key (free tier), `GEMINI_API_KEY` in `.env` |
| Called from | `gemini_client.generate_draft()`, invoked by `app.py` |
| Output | One draft post, 120–220 words, returned as text |

### Why Flash

The task is short-form text generation at low volume (a handful of drafts a
week) with a human editing every result. Flash is fast and free-tier friendly;
higher-cost models buy little when a human polishes the output anyway.

### How generation is structured

Generation is one prompt layer plus a deterministic post-process. The user types
a plain-language request; there is no pillar picker.

```
system_instruction + CRAFT_RULES (fixed voice, honesty, craft)  <- who Panth is, how to write
        +
FACTS (the whole verified fact bank)                            <- what he may claim as his own
        +
PILLAR_MEANINGS (label definitions, for tagging only)
        +
the user's request, OR a refinement of an earlier draft         <- "the race condition, opinionated"
        v
   Gemini 2.5 Flash
        v
   _split_pillar()                                              <- peel the `PILLAR: x` tag line
        v
   _strip_dashes()                                              <- enforce no-em-dash rule
        v
   (pillar, draft text)
```

- **System instruction** (`gemini_client.SYSTEM_INSTRUCTION`) sets the persona
  (Panth, a builder, not a teacher or marketer), the voice, and the hard rules:
  first person, a standalone hook line, one fresh insight, accessible to a
  recruiter, 2 to 4 tasteful emojis, at most 3 hashtags, 120-220 words, ending on
  a genuine question. It forbids em-dashes, cliches, and AI buzzwords ("delve",
  "revolutionize", "game-changer", "unlock", "seamless"). `CRAFT_RULES` is
  appended to it: one angle, one concrete detail, no preamble.
- **`FACTS`** is the single bank of verified material Panth may claim as his own.
  It is deliberately *not* partitioned by pillar: any post may cite any real
  story, and the model picks what fits the request.
- **`PILLAR_MEANINGS`** defines the five labels so the model can tag what it
  wrote. The pillar is an output, not an input. It is stored on the post for
  history and topic-spread only, and never appears in the post text.
- **Modes.** With a request, the model writes to it. With an empty request, it
  picks a topic and is steered away from `recent_pillars` (the last 3 posts) so
  the feed does not repeat. With `previous=` set, the request is read as a
  revision instruction against that earlier draft (the app's Refine box).

### The honesty guardrails (in the prompt)

Because this profile is used in a live job search, the system instruction hard-codes
the project's anti-fabrication rule:

- Never invent metrics, dates, quotes, funding numbers, or recent news.
- Never invent fake products or tools.
- Only Panth's **real** work and stack (the IONM-to-CMS-1500 tool; Python,
  LangChain, LangGraph, Amazon Bedrock/Nova) may be described as things he
  personally built or used. External examples must stay hypothetical
  ("imagine an agent that…").
- Never claim a project is finished, shipped, or deployed unless explicitly told
  so — treat work as ongoing.

These prompt-level rules are a first line of defense. The **human approval gate**
is the real enforcement: a person reads and approves every post.

### Deterministic post-processing

The model obeys the no-em-dash rule only intermittently, so
`gemini_client._strip_dashes()` applies it deterministically after generation:

- `—` (em-dash) → `, `
- spaced `–` (en-dash used as punctuation) → `, `
- digit-flanked en-dash (a numeric range like `120–220`) → left untouched

`_split_pillar()` runs first, peeling the model's `PILLAR: <label>` tag line off
the front. An unrecognized or missing tag falls back to `dev-perspective` and
leaves the text intact: a malformed tag costs a label, never a draft.

If Gemini returns empty text (or a tag with no post after it), `generate_draft`
raises `GeminiError` rather than queuing a blank draft.

## 2. Subject model — Amazon Nova v1 Pro (context only)

This model is **not part of GateKeep's runtime**. It is named here because it is
the subject of `build-in-public` and some `dev-perspective` posts, and accurate
documentation should distinguish "the model we use" from "the model we write
about".

| Property | Value |
|---|---|
| Model | Amazon Nova v1 Pro |
| Platform | Amazon Bedrock |
| Used in | Panth's real work project: an AI tool converting IONM (intraoperative neuromonitoring) machine JSON output into CMS-1500 insurance-claim format |
| Status (as documented) | In development — cut manual claim entry from ~1 day/surgery to under 5 minutes; ~85% accuracy and improving; **not finished or deployed** |

Any post referencing this tool must respect its real status. See
[use-case.md](use-case.md) and the honesty rules above.
