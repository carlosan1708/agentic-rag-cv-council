# Changelog

## [0.5.0] - 2026-07-06 — Tracker: kanban board, nudges, CV diff, timeline-aware prep

### Added
- **Kanban board view** for the tracker (list/board toggle): one column per status, cards move
  with ◀ ▶ controls and every move is logged in the application's timeline.
- **Stale-application nudges**: active applications with no activity for 7+ days surface on the
  dashboard with a ready-to-send follow-up draft and a one-click "log sent" timeline entry.
- **CV version diff**: compare any two CV versions you applied with, as a unified diff.
- **Timeline-aware interview prep**: "Prep me for the next round" feeds the application's
  timeline (interview notes, feedback), CV version and job into the AI coach - insights from
  the process so far, focus areas, STAR practice answers, and questions to ask.


## [0.4.1] - 2026-07-06 — Application activity timeline

### Added
- **Activity timeline per application**: log dated entries during the process and after
  interviews - Interview, Recruiter call, Assessment, Feedback, Follow-up, Offer details, or a
  plain Note. Entries can be deleted; status changes are logged into the timeline automatically
  (e.g. "Applied → Interviewing").
- Timeline works on both storage backends (SQLite/GCS); existing local databases are migrated
  automatically. CSV export gains an activity count column.

### Fixed
- Application details crashed with "Expanders may not be nested" whenever a stored CV version
  was present (found via screenshot review); previews now use toggles, with an E2E regression test.


## [0.4.0] - 2026-07-06 — Job Tracker with CV versioning

### Added
- **Job Tracker** (full version only): track every application with the exact CV version and
  cover letter used to apply. Statuses (Saved/Applied/Interviewing/Offer/Rejected), notes,
  per-application CV downloads (PDF/DOCX), and CSV export.
- **Tracker dashboard**: KPI tiles (applications, active, interviews, offers, response rate),
  average ATS score of tracked CV versions, and a status pipeline breakdown.
- **"📌 Track this application"** on the results screen: company/title auto-extracted from the
  job posting, stores the optimized CV + cover letter + ATS score. Manual add for jobs applied
  to outside the app.
- Storage follows the existing pattern: SQLite locally, GCS objects
  (`applications/{owner}/{id}.json`) when hosted; owner-scoped like history.
- 11 new unit tests + 5 new E2E tests (31 E2E total); tracker GIF in the README.


## [0.3.1] - 2026-07-06 — Demo is now a teaser; full version differentiated

### Changed
- **Demo mode is now a limited teaser** instead of the full product with canned answers:
  fixed sample CV/job (upload and job steps become read-only previews with an "Exit demo"
  button), fixed 2-specialist board, and visible 🔒 locks on Persona Builder, Debate round,
  multi-job comparison, job-URL extraction, DOCX export, and the Personalize step.
- The full version (own API key or local Ollama) keeps everything; the README now carries a
  Demo-vs-Full comparison table and the GIFs show the difference.
- E2E suite extended to 26 tests: new demo-lock tests, and the persona-builder/custom-specialist
  tests now walk the REAL wizard (stub Ollama provider, actual file upload) instead of demo mode.


## [0.3.0] - 2026-07-05 — Demo mode, access control, E2E tests

### Added
- **Demo mode**: "🎮 Try the Demo" on the welcome screen loads a sample candidate and
  pre-computed board results instantly - no API key, no cost. Wired through the full flow
  (results, cover letter, interview prep, personalize).
- **Login after approval** (`AUTH_MODE=approval`): visitors request access with their email and
  receive an access code; an admin approves requests in-app (`ADMIN_CODE` panel); approved users
  log in with email + code. Users persist in SQLite locally or GCS when hosted. Demo mode remains
  available without login.
- **Playwright E2E suite**: 21 browser tests covering the wizard, the full demo analysis flow
  (all result tabs, downloads, history) and the complete request → approve → login journey.
  Runs in CI on every push.
- **README GIFs recorded from the real app**: `scripts/record_demo.py` drives the demo flow with
  Playwright and assembles `docs/assets/demo.gif` + `ats_score.gif` (plus the UX-review screenshots).
- **UI/UX review** (`docs/UX_REVIEW.md`) with screenshot evidence.

### Changed (UX quick wins from the review)
- Persona list now shows recommended packs (matchmaker, general) first instead of filesystem order.
- The optional Personalize step is visible in the stepper as a sixth "Polish" step.
- Pre-run screen decluttered; welcome copy aligned with the stepper labels.


## [0.2.0] - 2026-07-04 — Google Cloud hosting

### Added
- **Google Cloud Storage history backend**: when `GCS_BUCKET` is set, analysis history is stored
  as JSON objects in the bucket (`history/{owner}/{id}.json`) instead of local SQLite — required
  because Cloud Run's filesystem is ephemeral. Backend is selected automatically.
- **Session-scoped history** (`HISTORY_SCOPE=session`): on shared/hosted deployments each browser
  session gets its own history owner, so visitors never see each other's analyses; "delete my
  data" removes only their objects.
- **Cloud Run deployment**: `scripts/deploy_gcp.sh` (APIs, bucket + least-privilege IAM, Secret
  Manager key, build & deploy) and a full guide in `docs/DEPLOY_GCP.md`.
- Dockerfile now honors the `PORT` env var (Cloud Run contract).


## [0.1.0] - 2026-07-04 — Major expansion

### Added
- **ATS Match Score** (`ats_service.py`): deterministic keyword/section/length scoring with a results
  dashboard, before/after comparison of the original vs. optimized CV, and missing-keyword analysis.
- **Multi-job comparison**: score your CV against several job descriptions at once (Step 3) and pick
  the best target — instant, no AI tokens used.
- **Cover letter & outreach generator** (opt-in): tailored cover letter, LinkedIn note and follow-up
  email, with PDF export.
- **Interview prep**: likely interview questions plus STAR model answers generated from the board's
  gap analysis (Results step).
- **Debate round** (opt-in): a Devil's Advocate agent challenges the specialists' findings before the
  Board Head synthesis.
- **DOCX support**: upload `.docx` CVs and download the optimized CV as DOCX.
- **Unicode PDF export**: embedded DejaVu font when available (accented names no longer mangled).
- **New providers**: Anthropic Claude and local Ollama, alongside Google Gemini and OpenAI.
- **Persona packs**: finance, healthcare, academia, sales & marketing, data & AI (11 packs total).
- **Persona Builder**: create custom specialists with role/goal/backstory and export them as YAML.
- **Local history**: completed analyses persist to a local SQLite database with view/delete and a
  one-click "delete my data" (Welcome step).
- **Robust job extraction**: schema.org/JobPosting JSON-LD parsing covers LinkedIn, Indeed,
  Greenhouse, Lever, Workday and most boards, with selector and main-content fallbacks.
- **Token usage reporting** after each run and **automatic retry with backoff** on transient failures.
- **Docker support**: `Dockerfile` + `docker-compose.yml`.
- **Test suite**: 42 tests covering all services; CI now runs pytest in addition to linting.

### Changed
- Persona YAMLs migrated to the `role`/`goal`/`backstory` schema (legacy `prompt` still loads).
- Job step accepts any job posting URL, not only LinkedIn.
- Results are extracted by agent role rather than task position (robust to optional agents).
- CI workflow fixed (`python-version` typo) and upgraded to actions/checkout@v4, Python 3.11.
- Upload size enforced server-side (5 MB) to match the UI check.

### Removed
- Legacy modules `crew_logic.py`, `persona_utils.py`, `session_utils.py` (superseded by the
  services layer).
- Unfinished RAG/ChromaDB integration and the `ENABLE_RAG` flag; dropped unused dependencies
  (`chromadb`, `duckduckgo-search`, `tiktoken`).

### Security
- User API keys are no longer written to process-wide environment variables (they could leak
  between users on a shared host); keys are passed per-request to the LLM client.
- Privacy note in the UI; CV content is never logged.

## [0.0.2] - earlier
- Improve UX - split results, key handling fixes, welcome page.

## [0.0.1] - earlier
- Initial MVP: CrewAI board, Streamlit wizard, PDF export.
