# Verified Post-Source Facts (Panth Patel)

Every claim below is traceable to Panth's general resume:
`C:\Users\Admin\Desktop\ai-job-search\cv\main_general.html` (and the matching
`main_general.pdf`). **Only draw first-person "I built / I used" claims from this
file or `CLAUDE.md`.** If material is not here, it is not verified — do not
invent it. Passes the interview-backtrack test: Panth can defend every line.

Honesty caveats that never drop:
- The IONM→CMS-1500 pipeline is **in development, ~85% extraction accuracy, not
  finished or deployed**. Never imply otherwise.
- Do NOT position Panth as a teacher/tutor (project voice rule) even though the
  resume lists a past "Teacher" role — that is history, not a post angle.

---

## Current role (the richest source — feeds build-in-public, dev-perspective, llm-tip)

**Software Engineer, Sunflower Labs (Vadodara, India, Feb 2026–present).**
End-to-end feature ownership on a **client multi-tenant healthcare SaaS
platform**: schema-per-tenant PostgreSQL on AWS ECS, ~11 repositories — data
model, migrations, FastAPI service, workflow engine, React UI, tests, QA sign-off.

Concrete, defensible work items (each is a whole post's worth of one specific detail):

| Fact | Postable angle |
|---|---|
| **Generative-AI claims pipeline:** Amazon **Nova v1 Pro on Bedrock** parses IONM (intraoperative neuromonitoring) machine JSON into **CMS 1500** records. Manual entry dropped from **~1 day/surgery to under 5 minutes** at **85% extraction accuracy**. Still in development. | build-in-public, llm-tip (structured-output extraction + validation), ai-take (LLM in regulated/healthcare data) |
| **Concurrency-safe booking:** patient self-service reschedule with a DOB identity gate, JWT sessions, a **DST-safe slot engine**, and **row-level + PostgreSQL advisory locks** guaranteeing **one-winner slot booking**. | dev-perspective (concurrency, distributed systems), the "bug only distributed systems have" angle |
| **Distributed race-condition repair:** the durable workflow engine failed to serialize suspended runs, so one SMS reply woke only one parked workflow. Rebuilt with **per-patient ownership locks, a FIFO grant queue, and TTL crash recovery**. | dev-perspective / llm-tip (real debugging war story — strongest "I can diagnose hard problems" material) |
| **Bi-directional EMR integration** over **SNS → SQS FIFO → Mirth Connect (HL7) → REST**: a stable external-ID backbone replaced fragile index matching, plus **E.164 phone normalization** and provider de-duplication. | dev-perspective (integration architecture), craft lesson on stable IDs vs positional matching |
| **Mass-messaging feature, end to end:** data model, S3 pipeline, scheduler, 5-step wizard, dashboard, permissions, migrations, and a **45-case QA matrix** — reusing existing workflow primitives. | build-in-public (shipping a full feature), craft lesson on reuse |
| **Multi-channel delivery tracking** (SMS / email / voice): JSONB status column, expansion API, channel-aware dashboard, and a TTS panel that **blocks publishing unreadable scripts**. | dev-perspective (data modeling with JSONB), product-safety guardrail angle |
| **Spec-first delivery with Claude Code** as an agentic coding assistant, plus a standalone **pytest end-to-end harness** covering workflows, campaigns, webhooks, and delivery. | dev-perspective / ai-take (working alongside agentic coding tools), testing-strategy craft |

## Verified tech stack (safe to claim hands-on)

- **Backend:** Python, FastAPI, **async SQLAlchemy 2.0**, Pydantic, asyncpg, REST APIs, pytest, Git
- **AI / LLM:** Amazon Bedrock, OpenAI, LangChain, LangGraph, prompt design, structured-output extraction and validation
- **Data & distributed:** PostgreSQL (**advisory locks, JSONB, schema-per-tenant**), **Inngest durable workflows**, AWS Lambda / SNS / SQS / S3 / ECS, **Mirth Connect (HL7 engine)**, Docker
- **Frontend:** React 18, TypeScript, Redux Toolkit, React Query, Tailwind, AG Grid, FullCalendar, vitest
- **Healthcare domain:** CMS 1500 claims, insurance data models, EMR integration, HL7, TCPA compliance, DST-safe clinical scheduling

> All of the above is verified and postable. The `gemini_client.py` system
> instruction and pillar prompts were enriched from this bank, so app-generated
> drafts can now use this material too.

## Projects (secondary material)

- **Loan Qualification Engine** (academic): Python ML pipeline, real-time loan
  decisions, Logistic Regression vs Random Forest.
- **Holiday Notification Service** (academic): scheduled engine, FastAPI + Firebase.
- **Image Color-Pattern Clustering Tool** (freelance, Apr–Sep 2024): Python +
  OpenCV, user-defined color-pattern detection.

## career-journey material

- Relocating to **Somerset, NJ, USA**; from Vadodara, India.
- Education: **PG Diploma, Software Development – AI, Algonquin College (Ottawa, 2024–2025)**;
  PG Diploma, Project Management, Fleming College (2023–2024); B.E. Computer
  Science & Engineering, Indus University (2020–2023); Diploma, Computer Science,
  L.J. Polytechnic (2017–2020).
- Certification: **CAPM®**. Languages: English, Hindi, Gujarati (fluent).
- Earlier roles (context only, not post angles): Teacher (Aarham Academy, 2023),
  Python Intern (InfoLabz, 2021), QA Tester (Sunflower Labs, 2020).

## Contact (do not put in posts; identity reference only)

LinkedIn: linkedin.com/in/panthpatel0122
