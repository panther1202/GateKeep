---
name: post-writing
description: Voice, structure, and honesty rules for drafting LinkedIn posts for Panth Patel. Applies whenever generating or editing post text for this project - triggers on "generate", "draft a post", "/generate-post", pillar names (build-in-public, llm-tip, career-journey, ai-take).
---

# LinkedIn Post Writing Rules

## Honesty (non-negotiable, carried over from the ai-job-search project)

- Never state or imply a project is finished, deployed, or successful if it isn't. The IONM/CMS1500 tool is **in development, 85% accuracy, not deployed** - say so.
- Never invent a role, title, or achievement not present in `CLAUDE.md` or the linked `ai-job-search` profile files.
- If a fact is genuinely uncertain (exact date, exact metric), leave it vague rather than inventing precision.
- Apply the "interview backtrack test" from `ai-job-search/.claude/skills/job-application-assistant/03-writing-style.md`: could Panth comfortably explain this line in person without backtracking? If not, cut it or soften it.

## Voice

- First person, active voice. "I built" not "a tool was built."
- Matches Panth's DISC profile (Dominance/Influence): direct, confident, opinionated where appropriate - not hedgy, not falsely humble.
- No em-dashes. Use commas or periods, or restructure the sentence.
- No cliches or empty filler: cut "passionate about," "leverage my skills," "hit the ground running," "game-changer," "synergies."
- No unverified company/industry claims. If a post references something outside Panth's own direct experience, flag it as needing verification before drafting.

## Structure (LinkedIn-specific, from the engagement plan)

- **First line is the hook** - LinkedIn truncates after ~2 lines before "see more." The hook must work standalone.
- Short paragraphs, generous line breaks. No text walls.
- End with a genuine question inviting comment - not a generic "thoughts?" tacked on, tie it to the post's actual content.
- 3-5 hashtags max, relevant ones (e.g. #AI #Python #MachineLearning), not stuffed.
- A few tasteful emojis (roughly 2-4) are fine to make the post scannable and inviting - accent the hook or mark short-list items. Keep them relevant and professional; not one per line, not as word replacements, never childish or salesy.
- If the post needs to reference a link, note in the draft that the link belongs in the first comment, not the post body - LinkedIn suppresses reach on posts with outbound links.
- Target length: enough to be substantive, short enough to read on a phone without much scrolling. No hard word cap, but if a draft exceeds ~200 words, look for what to cut before publishing.

## Per-pillar guidance

- **build-in-public**: one concrete detail per post (a specific tradeoff, a specific number, a specific bug/lesson) rather than a vague progress update. "Cut entry time from a day to 5 minutes" is stronger than "made good progress this week."
- **llm-tip**: one lesson, one example. Not a listicle.
- **career-journey**: personal and specific to Panth's actual relocation (Vadodara to Somerset, NJ) - not generic immigrant-journey platitudes.
- **ai-take**: a real opinion, not a neutral summary of news. Should be something Panth could defend if challenged in the comments.
- **dev-perspective**: engineer-to-engineer. One concrete point, one angle (craft lesson, technical deep-dive of real work, or a language/framework/tool opinion). A short code snippet is fine only if it earns its place - LinkedIn shows code as plain text, so keep it under ~8 lines and readable on a phone. Same honesty rule: illustrative snippets only, never imply the IONM tool is finished or deployed.
