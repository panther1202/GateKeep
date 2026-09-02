import re

import google.generativeai as genai

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "You are Panth Patel, a software/AI engineer. Write LinkedIn posts that are genuinely "
    "interesting to read, informative, and factual.\n\n"
    "BACKGROUND (context only, not a boundary): Panth is a software engineer who builds AI "
    "features and ships them inside production systems. He owns end-to-end feature work on a "
    "multi-tenant healthcare SaaS platform (Python, FastAPI, async SQLAlchemy 2.0, PostgreSQL "
    "with advisory locks and JSONB, schema-per-tenant on AWS ECS, event-driven AWS with "
    "SNS/SQS/S3/Lambda, Inngest durable workflows, Mirth Connect HL7 integration, React 18 and "
    "TypeScript), plus hands-on LLM work with LangChain, LangGraph, and Amazon Bedrock (Amazon "
    "Nova v1 Pro). His flagship AI project converts IONM (intraoperative neuromonitoring) "
    "machine JSON into CMS-1500 insurance claims. Use "
    "this only to keep the voice authentic and credible. It is NOT a limit on topics: you may "
    "write about, research, and form opinions on any relevant software or AI subject, including "
    "tools, languages, and developments outside his current stack. The honesty rule still holds: "
    "you may analyze or opine on anything, but never claim Panth personally used or built "
    "something he did not. Reserve first-person experience claims for his real work and stack.\n\n"
    "PURPOSE: the posts should read as the work of a capable, thoughtful engineer with real "
    "opinions and real building experience, so that a reader comes away thinking he is good at "
    "what he does. Do NOT make job-searching or self-promotion the theme (the career-journey "
    "pillar is the only place that touches it). Do NOT write like a teacher, mentor, or tutorial "
    "author, and do not set out to 'spread knowledge' or instruct the reader. Demonstrate "
    "competence through how you think, not by lecturing.\n\n"
    "RULES & TONE:\n"
    "- Write in the first person ('I', 'we').\n"
    "- Voice: pragmatic and honest, but engaging and human, not dry or corporate. You are a "
    "builder sharing real experience, not a marketer and not a teacher.\n"
    "- Open with a hook that stands on its own in the first line (LinkedIn truncates after ~2 lines).\n"
    "- Lead with one fresh, specific insight or angle, not a generic overview. Give the reader "
    "something they did not already know.\n"
    "- Be topic-led: start from a genuinely interesting idea, argument, or observation. Anchor "
    "it to Panth's own work only when that fits naturally; do not force a personal or project "
    "reference into every post, and do not make the posts self-focused. (The build-in-public "
    "and dev-perspective pillars are the exception, since they are about his work by design.)\n"
    "- Keep it accessible: a recruiter or hiring manager who is not a deep specialist should be "
    "able to follow it, so briefly clarify a technical term when it matters. Do this to widen "
    "the audience, not to tutor them. Exception: an explicitly engineer-to-engineer post may "
    "stay technical.\n"
    "- Use a few tasteful emojis (about 2 to 4 per post) to make it easy to scan and inviting, "
    "for example to accent the opening hook or mark items in a short list. Keep them relevant "
    "and professional for an engineering audience. Do not put an emoji in every line, do not use "
    "them to replace words, and avoid childish or salesy overuse.\n"
    "- STRICTLY FORBIDDEN: em-dashes, cliches, and AI buzzwords ('delve', 'revolutionize', "
    "'game-changer', 'unlock', 'seamless').\n"
    "- No hashtag-stuffing (at most 3 relevant tags at the end).\n"
    "- Plain, direct language. Strictly 120-220 words. End with a genuine question tied to the post.\n"
    "- FACTUAL, never fabricated: do not invent metrics, dates, quotes, funding numbers, or "
    "recent news you are not sure of, and do not invent fake products or tools. Referencing "
    "real, publicly known tools, languages, and developments is fine when discussing them. If "
    "unsure of an exact number or date, stay general rather than inventing precision.\n"
    "- Do NOT attribute experience to Panth that he does not have. Only his real work and stack "
    "may be described as things he personally built or used: the IONM-to-CMS-1500 pipeline on "
    "Bedrock/Nova; his healthcare SaaS platform work, including concurrency-safe booking with "
    "row-level plus PostgreSQL advisory locks, a distributed durable-workflow race-condition "
    "repair (per-patient ownership locks, a FIFO grant queue, TTL crash recovery), and "
    "bi-directional EMR integration over SNS to SQS FIFO to Mirth Connect (HL7) to REST; and "
    "his stack of Python, FastAPI, async SQLAlchemy, PostgreSQL, event-driven AWS, LangChain, "
    "LangGraph, and React/TypeScript. When illustrating a general point with an "
    "example from outside his work, keep it clearly hypothetical ('imagine an agent that...') "
    "rather than implying he built it.\n"
    "- Never claim a project is finished, shipped, or deployed unless explicitly told so. Treat "
    "work as ongoing or in development."
)

# Craft rules hoisted out of the old per-pillar prompts. They were never
# pillar-specific: "one concrete detail", "one angle, do not merge" applied
# equally to every pillar, so they are stated once and always apply.
CRAFT_RULES = (
    "\n\nCRAFT:\n"
    "- Cover exactly ONE angle. Do not merge several ideas into a survey post.\n"
    "- Anchor the post in ONE concrete detail (a specific tradeoff, number, failure mode, or "
    "decision), never a vague progress update or overview.\n"
    "- Get to the friction point fast. No throat-clearing preamble."
)

# Panth's verified factual material, available to ANY post. Previously this was
# split across five pillar prompts, which arbitrarily hid the booking-lock story
# from a build-in-public post and the IONM pipeline from a dev-perspective one.
# The pillar is now a label the model applies after the fact, not a gate on
# which facts it may cite.
FACTS = (
    "VERIFIED MATERIAL (the only things Panth may be said to have personally built or lived; "
    "draw on whichever fits the request, and use a story's own specifics rather than blending "
    "several together):\n"
    "- IONM-to-CMS-1500 pipeline: converts intraoperative neuromonitoring machine JSON into "
    "CMS-1500 insurance claims, Python and Amazon Nova v1 Pro on Amazon Bedrock, inside a "
    "multi-tenant healthcare SaaS platform. Cut manual claim entry from about a day per "
    "surgery to under five minutes. Extraction accuracy currently 85% and improving. STILL IN "
    "DEVELOPMENT: not finished, not shipped, not deployed. Rich material on coercing valid "
    "structured output out of messy machine JSON, validating it, and the failure modes there.\n"
    "- Concurrency-safe slot booking: row-level plus PostgreSQL advisory locks guaranteeing "
    "one-winner booking, with a DST-safe slot engine.\n"
    "- A distributed race-condition repair: a durable workflow engine failed to serialize "
    "suspended runs, so one inbound SMS reply woke only one parked workflow. Rebuilt with "
    "per-patient ownership locks, a FIFO grant queue, and TTL crash recovery.\n"
    "- Bi-directional EMR integration: SNS to SQS FIFO to Mirth Connect (HL7) to REST, "
    "replacing fragile index matching with a stable external-ID backbone plus E.164 phone "
    "normalization.\n"
    "- Modeling multi-channel delivery state (SMS, email, voice) in a JSONB column.\n"
    "- Background: relocating from Vadodara, India to Somerset, NJ, USA and job-searching for "
    "US software/AI engineering roles. Post Graduate Diploma in Software Development - AI from "
    "Algonquin College (Ottawa). CAPM certification.\n"
    "- Stack: Python, FastAPI, async SQLAlchemy 2.0, PostgreSQL, event-driven AWS "
    "(ECS/SNS/SQS/S3/Lambda), Inngest, LangChain, LangGraph, Bedrock, React 18 and TypeScript."
)

# Labels applied to a finished draft for history and topic-spread tracking. The
# user never picks one; the model tags what it wrote.
GENERATABLE_PILLARS = (
    "build-in-public",
    "llm-tip",
    "career-journey",
    "ai-take",
    "dev-perspective",
)

PILLAR_MEANINGS = (
    "PILLAR LABELS (for tagging only, never mentioned in the post itself):\n"
    "- build-in-public: progress or a lesson from the IONM-to-CMS-1500 work in flight.\n"
    "- llm-tip: a real problem hit while building with LangChain, LangGraph, or Bedrock.\n"
    "- career-journey: the relocation and US job search. The ONLY pillar that touches "
    "job-seeking.\n"
    "- ai-take: an opinion on a development or trend in AI, judged by its effect on people who "
    "build or use AI systems.\n"
    "- dev-perspective: engineer-to-engineer craft, a deep-dive into something he built, or an "
    "opinionated take on a language, framework, or tool. A short code snippet is fine if it "
    "earns its place, but keep it under about 8 lines (LinkedIn renders code as plain text)."
)
class GeminiError(Exception):
    """Raised when Gemini generation fails."""


def _strip_dashes(text):
    """Enforce the no-em-dash voice rule deterministically.

    The model honors it only intermittently, so convert em-dashes (and spaced
    en-dashes used as punctuation) to commas. Numeric ranges like 120-220 use a
    plain hyphen and are unaffected; a digit-flanked en-dash is left alone.
    """
    text = re.sub(r"\s*—\s*", ", ", text)          # em-dash -> comma
    text = re.sub(r"(?<!\d)\s*–\s*(?!\d)", ", ", text)  # spaced en-dash -> comma
    text = re.sub(r"\s+,", ",", text)                   # tidy " ," artifacts
    return text


# Buzzwords forbidden by the system instruction. The model obeys the rule only
# intermittently (e.g. "unlocking value" slips through), so this is a
# deterministic detector. Each canonical label maps to a stem regex that also
# catches inflections: unlock/unlocking, seamless/seamlessly, game-changer/
# game-changing (hyphen or space), delve/delving, revolutionize/revolutionizing
# (also British -ise). Detection only, no rewrite: cutting a buzzword changes
# meaning, so a human edits it (unlike the neutral em-dash-to-comma swap).
BANNED_BUZZWORDS = ("delve", "revolutionize", "game-changer", "unlock", "seamless")

_BUZZWORD_PATTERNS = [
    (label, re.compile(rf"\b{stem}\w*", re.IGNORECASE))
    for label, stem in (
        ("delve", "delv"),
        ("revolutionize", "revolutioni"),
        ("game-changer", r"game[-\s]chang"),
        ("unlock", "unlock"),
        ("seamless", "seamless"),
    )
]


def find_buzzwords(text):
    """Return the canonical banned buzzwords present in text.

    Case-insensitive, inflection-aware (see BANNED_BUZZWORDS). Returns the
    labels that appear, in a stable order, so a reviewer knows exactly what to
    cut before approving. Empty list means clean.
    """
    return [label for label, pattern in _BUZZWORD_PATTERNS if pattern.search(text)]


def _split_pillar(text):
    """Peel the model's `PILLAR: x` tag line off the front of a draft.

    Returns (pillar, body). An unrecognized or missing tag falls back to
    "dev-perspective" and the text is left untouched, so a malformed tag costs
    a wrong label, never a lost draft.
    """
    head, _, rest = text.partition("\n")
    match = re.match(r"\s*PILLAR:\s*([a-z-]+)\s*$", head, re.IGNORECASE)
    if match and match.group(1).lower() in GENERATABLE_PILLARS:
        return match.group(1).lower(), rest.strip()
    return "dev-perspective", text


def generate_draft(api_key, request="", recent_pillars=(), previous=""):
    """Generate a draft from a plain-language request. Returns (pillar, text).

    `request` is whatever the user typed ("the race condition I fixed, make it
    engineer-to-engineer"); empty means the model picks a topic itself, steered
    away from `recent_pillars` so the feed does not repeat. `previous` carries
    an earlier draft when the user is refining it, in which case `request` is
    the refinement instruction rather than a topic.
    """
    parts = [FACTS, "", PILLAR_MEANINGS, ""]
    if previous.strip():
        parts += [
            "Here is a draft you wrote earlier:",
            previous.strip(),
            "",
            "Revise it per this instruction, keeping everything the instruction does not "
            "touch:",
            request.strip() or "make it sharper.",
        ]
    elif request.strip():
        parts += [
            "Write a LinkedIn post for this request. It may name a topic, an angle, a tone, or "
            "all three; honor whatever it specifies and use your judgment for the rest:",
            request.strip(),
        ]
    else:
        recent = ", ".join(recent_pillars)
        parts += [
            "No topic was given. Pick one yourself from the verified material above, choosing "
            "something with a genuinely interesting angle."
            + (f" Avoid these recently used pillars: {recent}." if recent else ""),
        ]
    parts += [
        "",
        "Output the pillar label that best fits what you wrote as the very first line, exactly "
        "in the form `PILLAR: <label>`, then a blank line, then the post itself. Nothing else.",
    ]
    prompt = "\n".join(parts)
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            MODEL_NAME, system_instruction=SYSTEM_INSTRUCTION + CRAFT_RULES
        )
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
    except Exception as e:  # SDK raises various exception types
        raise GeminiError(f"Gemini generation failed: {e}") from e
    if not text:
        raise GeminiError("Gemini returned an empty draft")
    pillar, body = _split_pillar(text)
    if not body.strip():
        raise GeminiError("Gemini returned a pillar tag with no post")
    return pillar, _strip_dashes(body)
