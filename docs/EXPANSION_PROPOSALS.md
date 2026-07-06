# Expansion Proposals — AI CV Advisory Board

> **Implementation status (2026-07-04):** Everything below has been implemented except
> 3.2 (FastAPI backend decoupling) and the accounts/auth part of 3.3 — both are
> project-scale rearchitectures best done as their own effort. RAG (1.8) was **removed**
> rather than finished, per the maintainer's decision. 3.3 shipped as anonymous local
> SQLite persistence. See `CHANGELOG.md` for the full list.

This document proposes a major expansion of the project, based on a review of the current
codebase (Streamlit wizard + CrewAI pipeline + Gemini/OpenAI, YAML personas, optional
RAG/PDF flags). Proposals are grouped into four themes and ordered into a suggested
roadmap at the end.

---

## Theme 1 — Product features (user-facing value)

### 1.1 Structured ATS Match Score & Dashboard
Today the output is free-form markdown, and only the Matchmaker persona produces an ad-hoc
0–100 score buried in prose. Make scoring a first-class feature:

- Use CrewAI's `output_pydantic` on tasks so agents return structured data
  (score breakdown, missing keywords, red flags, per-section ratings) instead of raw text.
- Add a deterministic (non-LLM) ATS layer: keyword coverage vs. the job description,
  section detection, length/format checks. Cheap, instant, reproducible.
- Render a results dashboard: overall match gauge, keyword gap table,
  before/after score once the rewritten CV is generated.

This is the single highest-leverage change: structured output also unlocks diffing,
history, exports, and regression testing.

### 1.2 Cover Letter & Outreach Generator
The pipeline already has everything needed (CV, job description, board feedback).
Add a final optional agent that produces:
- A tailored cover letter.
- A short LinkedIn "connect" message and a recruiter follow-up email.
Add it as a step-7 tab next to the rewritten CV, with the same PDF export path.

### 1.3 Interview Preparation Module
Extend the existing "Board Interview" step (currently only used to gather details) into a
real interview-prep product:
- Generate likely interview questions from the gaps the board identified.
- Provide model answers built from the candidate's actual experience (STAR format).
- Optional mock-interview chat mode with one persona acting as the hiring manager.

### 1.4 Multi-Job Comparison
Let users paste 2–5 job postings and run a lighter "match only" crew per job, producing a
comparison matrix (match %, top gaps, effort to close them). Helps users decide where to
apply — a distinct feature competitors rarely have.

### 1.5 DOCX Support and Better Document Pipeline
- **Import**: accept `.docx` (via `python-docx`) alongside PDF/TXT — a huge share of CVs
  are Word files.
- **Export**: add DOCX export and fix PDF export to support Unicode
  (`fpdf2` with an embedded TTF font instead of the current Latin-1 sanitization,
  which mangles accented names — e.g. Spanish/Portuguese characters).
- Offer 2–3 PDF templates (classic, modern, compact) instead of the single hardcoded layout.

### 1.6 Robust Job Ingestion (beyond LinkedIn)
`scraper.py` only handles LinkedIn CSS classes and silently returns error strings.
Replace with a layered extractor:
1. Parse `schema.org/JobPosting` JSON-LD (used by LinkedIn, Indeed, Greenhouse, Lever,
   Workday and most boards) — one parser covers most of the market.
2. Fall back to a readability-style main-content extraction.
3. Fall back to manual paste (current behavior).
Also raise typed errors instead of returning error messages as content, so the UI can
react properly.

### 1.7 Persona Builder & Persona Packs
Personas are the identity of this project — lean into them:
- In-app persona editor (create/edit/save custom personas with role/goal/backstory),
  persisted per user, exportable as YAML.
- Ship industry packs: `finance.yaml`, `healthcare.yaml`, `academia.yaml`,
  `sales_marketing.yaml`, `data_ai.yaml`.
- Migrate all persona YAMLs from the legacy `name`/`prompt` schema to the full
  `role`/`goal`/`backstory` schema the `Persona` model already supports.

### 1.8 Real RAG Benchmarking
`ENABLE_RAG` exists but the ChromaDB path only lives in the legacy `crew_logic.py` and
never gets a populated vector store. Either finish it or remove it. Finishing it means:
- A curated, anonymized corpus of strong CV bullet points per role family.
- An ingestion script + versioned collection.
- The Benchmarking Specialist agent wired into `AnalysisService` behind the flag.

---

## Theme 2 — AI & orchestration

### 2.1 Add Anthropic Claude (and local models) as Providers
`AppConfig.llm_provider` is a hardcoded Google/OpenAI binary spread across services and UI.
Refactor to a provider registry (LiteLLM already supports this under CrewAI) and add:
- **Anthropic Claude** (e.g. `claude-sonnet-5` for analysis quality).
- **Ollama** for a fully local/free mode — great for privacy-sensitive users, and pairs
  well with the privacy story in 4.3.

### 2.2 Board Debate Mode
All agents currently run independently (`async_execution=True`) and the Board Head
synthesizes. Add an optional second round where specialists see each other's findings and
can rebut before synthesis (CrewAI hierarchical process or an explicit critique round).
Differentiates the "advisory board" concept from a plain multi-prompt fan-out.

### 2.3 Cost, Token & Progress Transparency
- Surface CrewAI usage metrics (`crew.usage_metrics`) after each run: tokens, estimated
  cost per provider/model.
- Stream agent progress with `step_callback` so users see live "Recruiter is thinking…"
  updates instead of tab placeholders only.
- Add per-run tracing (Langfuse or OpenTelemetry) behind a flag for debugging quality.

### 2.4 Resilience: Retries, Timeouts, Fallback Models
A single LLM failure currently kills the whole run. Add:
- Retry with backoff at the service layer.
- A cheaper fallback model per provider.
- Graceful partial results (show the specialist reports even if the reformatter fails).

---

## Theme 3 — Architecture & platform

### 3.1 Delete the Legacy Layer (quick win)
`crew_logic.py`, `persona_utils.py`, and `session_utils.py` are superseded by
`services/` + `state_manager.py` but still ship (and the only test in the repo tests the
legacy `persona_utils`). Remove them, port the test to `PersonaService`, and the codebase
becomes what the README already claims it is.

### 3.2 Decouple Backend from Streamlit
Analysis runs synchronously inside a Streamlit rerun — long-running, blocking,
lost on refresh. Extract a FastAPI backend:
- `POST /analyses` → job id; worker (RQ/Celery/arq) runs the crew; UI polls or uses SSE.
- Streamlit (or later a Next.js front end) becomes a thin client.
- Enables the public demo to queue instead of tying one server thread per user, and
  unlocks a future API product ("CV analysis as an API").

### 3.3 Persistence & Accounts
Everything dies with the session today. Add SQLite (SQLAlchemy, trivially upgradable to
Postgres) for: saved analyses, CV versions with diffs between runs, custom personas, and
usage history. Start with anonymous local persistence; add lightweight auth
(e.g. streamlit-authenticator or the FastAPI layer) when hosting.

### 3.4 Configuration Hygiene
- Replace scattered `os.getenv` calls with a single `pydantic-settings` `Settings` object.
- Stop mutating `os.environ` with user API keys (`GEMINI_API_KEY`/`OPENAI_API_KEY` are set
  process-wide in `crew_logic.py`/`personalize.py` — on a shared host, user A's key can
  leak into user B's run). Pass keys explicitly via CrewAI's `LLM(api_key=...)`, which
  `AnalysisService` already does correctly — make it the only path.

### 3.5 Docker & Deployment Story
Add a `Dockerfile` + `docker-compose.yml` (app + ChromaDB), and document deployment to
Streamlit Cloud vs. self-host. The `.devcontainer` exists; align it with the same image.

---

## Theme 4 — Quality, CI & trust

### 4.1 Fix and Extend CI (quick win)
- `lint.yml` has a bug: `python-level: '3.10'` should be `python-version: '3.10'`.
- Add a `test` job running `pytest` with coverage; add `mypy` (the codebase is typed but
  never checked).
- Consider consolidating black/isort/flake8 into `ruff` (one tool, same pre-commit).

### 4.2 A Real Test Suite
Current coverage: one file, testing the legacy loader. Priorities:
- Unit tests for every service (`CVService` parsing/PDF, `ConfigService`, `JobService`
  with mocked HTTP, `PersonaService` with tmp dirs).
- A fake-LLM harness for `AnalysisService` so crew wiring is tested without API calls.
- Golden-file tests on the deterministic ATS scorer (1.1) — that's where regression
  testing becomes genuinely possible.

### 4.3 Privacy & Security Posture
CVs are PII. As the app grows this becomes the trust differentiator:
- Never log CV content (audit current logger usage).
- Explicit data-retention statement in the UI; one-click "delete my data" once
  persistence (3.3) lands.
- Rate limiting + max upload size on the hosted demo; API keys kept per-session only.

### 4.4 Docs & Community
- Split the README: user guide vs. contributor guide; add architecture diagram.
- `CHANGELOG.md`, versioned releases, and a public roadmap issue.
- Persona contribution guide (the easiest way for outside contributors to add value).

---

## Suggested roadmap

| Phase | Focus | Items |
|-------|-------|-------|
| **0 — Quick wins (days)** | Clean base | 3.1 legacy removal, 4.1 CI fix, 3.4 env-var key fix, 1.6 typed scraper errors |
| **1 — Core value (2–4 wks)** | Better results | 1.1 structured output + ATS score, 1.5 DOCX/Unicode PDF, 2.3 cost/progress, 4.2 tests |
| **2 — Breadth (4–8 wks)** | More product | 1.2 cover letters, 1.3 interview prep, 1.7 persona builder + packs, 2.1 Claude/Ollama providers |
| **3 — Platform (8+ wks)** | Scale & retention | 3.2 FastAPI backend, 3.3 persistence/accounts, 1.4 multi-job compare, 2.2 debate mode, 1.8 real RAG |

The recommended starting point is **1.1 (structured outputs + ATS scoring)** — it upgrades
the core deliverable, and nearly every other feature (dashboards, diffs, comparisons,
tests) builds on it.
