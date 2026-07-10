# Idea: factual-evaluator pre-check layer (NOT YET APPROVED / NOT IMPLEMENTED)

Status: parked thought, raised 2026-07-09. Do not build until draft-generation quality is
settled and this is discussed and approved via the brainstorming flow.

## The thought

Add an automated evaluator as a pre-check layer that sits **between draft generation and
Panth's final human approval**:

```
generate draft (gemini_client) -> [factual-evaluator] -> human review/approve (app.py) -> publish
```

The evaluator scores/annotates a draft for factual integrity before it reaches Panth, so the
human gate becomes a confirmation step rather than the first line of defense.

## What it might check (to be refined later)

- Fabricated specifics: invented metrics, dates, quotes, funding numbers, recent news.
- False personal-experience claims: attributing tools/projects to Panth that are not his real
  work/stack (only the IONM-to-CMS-1500 tool + Python/LangChain/LangGraph/Bedrock-Nova are his).
- Overstated project status (claiming finished/shipped/deployed).
- Style-rule violations already enforced deterministically (em-dashes) vs. those that are not
  (word count, buzzwords) - decide which belong in the evaluator vs. simple code checks.

## Open questions for the future discussion

- LLM-as-judge (second Gemini call with a rubric) vs. deterministic rule checks vs. both?
- Does it block, or just warn/annotate in the Streamlit UI for Panth to judge?
- Where does ground truth come from (the ai-job-search profile files? a facts allowlist)?
- Cost/latency of a second model call per draft on the free tier.

## Why parked

Per Panth: perfect the draft-creation prompt first, then discuss this. This file is only a
capture so the idea is not lost.
