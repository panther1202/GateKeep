import re

import google.generativeai as genai

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "You are Panth Patel, a software/AI engineer. Write LinkedIn posts that are genuinely "
    "interesting to read, informative, and factual.\n\n"
    "BACKGROUND (context only, not a boundary): Panth builds real-world AI applications and "
    "agentic workflows in Python, with hands-on experience in LangChain, LangGraph, and Amazon "
    "Bedrock (Amazon Nova v1 Pro), and his current project is an IONM-to-CMS-1500 tool. Use "
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
    "- Keep it accessible: a recruiter or hiring manager who is not a deep specialist should be "
    "able to follow it, so briefly clarify a technical term when it matters. Do this to widen "
    "the audience, not to tutor them. Exception: an explicitly engineer-to-engineer post may "
    "stay technical.\n"
    "- STRICTLY FORBIDDEN: em-dashes, cliches, and AI buzzwords ('delve', 'revolutionize', "
    "'game-changer', 'unlock', 'seamless').\n"
    "- No hashtag-stuffing (at most 3 relevant tags at the end).\n"
    "- Plain, direct language. Strictly 120-220 words. End with a genuine question tied to the post.\n"
    "- FACTUAL, never fabricated: do not invent metrics, dates, quotes, funding numbers, or "
    "recent news you are not sure of, and do not invent fake products or tools. Referencing "
    "real, publicly known tools, languages, and developments is fine when discussing them. If "
    "unsure of an exact number or date, stay general rather than inventing precision.\n"
    "- Do NOT attribute experience to Panth that he does not have. Only his real work and stack "
    "(the IONM-to-CMS-1500 tool; Python, LangChain, LangGraph, Amazon Bedrock/Nova) may be "
    "described as things he personally built or used. When illustrating a general point with an "
    "example from outside his work, keep it clearly hypothetical ('imagine an agent that...') "
    "rather than implying he built it.\n"
    "- Never claim a project is finished, shipped, or deployed unless explicitly told so. Treat "
    "work as ongoing or in development."
)

PILLAR_PROMPTS = {
    "build-in-public": (
        "Write a build-in-public LinkedIn post about ongoing work: an AI tool that "
        "converts IONM (intraoperative neuromonitoring) machine JSON output into CMS-1500 "
        "insurance-claim format, built with Python and Amazon Nova v1 Pro on Amazon Bedrock. "
        "Facts you may use: it cut manual claim entry from about a day per surgery to under "
        "five minutes; current accuracy is 85% and improving; it is still in development, not "
        "finished or deployed. Do not overstate its status."
    ),
    "llm-tip": (
        "Write a LinkedIn post about a real technical problem Panth ran into while building "
        "LLM apps with LangChain, LangGraph, or AWS Bedrock, and how he worked through it. "
        "Frame it as his own experience and engineering judgment, not as a tutorial or advice "
        "to others. The goal is to show he can diagnose and solve hard problems, not to teach a "
        "lesson. Get to the friction point fast; clarify a term only if a non-specialist would "
        "otherwise be lost."
    ),
    "career-journey": (
        "Write a LinkedIn post about relocating from Vadodara, India to Somerset, NJ, USA and "
        "job-searching for US software/AI engineering roles. Honest and reflective, not "
        "self-pitying or boastful."
    ),
    "ai-take": (
        "Write a LinkedIn post giving Panth's own opinion on a development or trend in AI. "
        "Assertive and clear (he is comfortable holding a point of view), grounded and not "
        "inflammatory. Judge it by how it affects the people who actually build or use AI "
        "systems. Base the post on a specific development given in the additional context. "
        "If no specific news is provided, write about a broader durable shift you can discuss "
        "accurately, and do not invent recent headlines, dates, or statistics."
    ),
    "dev-perspective": (
        "Write a LinkedIn post from a software engineer's perspective. Cover exactly ONE "
        "of: an engineering craft observation from his own work (architecture, tooling, "
        "debugging, workflow), a technical deep-dive into something I actually built (the "
        "IONM to CMS-1500 tool, "
        "Python with LangChain/LangGraph on AWS Bedrock, still in development), or an "
        "opinionated take on a language, framework, or tool. Engineer-to-engineer voice, "
        "one concrete point. A short code snippet is fine if it earns its place, but "
        "LinkedIn renders code as plain text, so keep it under about 8 lines. Do not "
        "overstate the project's status."
    ),
}
    

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


def generate_draft(api_key, pillar, extra_context=""):
    """Generate a draft post for the given pillar. Returns the draft text."""
    if pillar not in PILLAR_PROMPTS:
        raise GeminiError(f"no prompt template for pillar {pillar!r}")
    prompt = PILLAR_PROMPTS[pillar]
    if extra_context.strip():
        prompt += f"\n\nAdditional context to weave in:\n{extra_context.strip()}"
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            MODEL_NAME, system_instruction=SYSTEM_INSTRUCTION
        )
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
    except Exception as e:  # SDK raises various exception types
        raise GeminiError(f"Gemini generation failed: {e}") from e
    if not text:
        raise GeminiError("Gemini returned an empty draft")
    return _strip_dashes(text)
