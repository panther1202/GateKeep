import google.generativeai as genai

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "Write in first person as Panth Patel, a software engineer. "
    "Rules: no em-dashes, no cliches, no hashtags-stuffing (at most 3 relevant tags), "
    "no fabricated or inflated claims, plain direct language, 120-220 words. "
    "Never claim a project is finished, shipped, or deployed unless explicitly told it is."
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
        "Write a short, practical LinkedIn post sharing one concrete lesson learned while "
        "building LLM apps with LangChain, LangGraph, or AWS Bedrock. Make it useful to other "
        "engineers, not generic."
    ),
    "career-journey": (
        "Write a LinkedIn post about relocating from Vadodara, India to Somerset, NJ, USA and "
        "job-searching for US software/AI engineering roles. Honest and reflective, not "
        "self-pitying or boastful."
    ),
    "ai-take": (
        "Write a LinkedIn post giving Panth's own opinion on a recent development in AI. "
        "Assertive and clear (he is comfortable holding a point of view), but grounded and "
        "not inflammatory."
    ),
    "dev-perspective": (
        "Write a LinkedIn post from a software engineer's perspective. Cover exactly ONE "
        "of: an engineering craft lesson (architecture, tooling, debugging, workflow), a "
        "technical deep-dive into something I actually built (the IONM to CMS-1500 tool, "
        "Python with LangChain/LangGraph on AWS Bedrock, still in development), or an "
        "opinionated take on a language, framework, or tool. Engineer-to-engineer voice, "
        "one concrete point. A short code snippet is fine if it earns its place, but "
        "LinkedIn renders code as plain text, so keep it under about 8 lines. Do not "
        "overstate the project's status."
    ),
}
    

class GeminiError(Exception):
    """Raised when Gemini generation fails."""


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
    return text
