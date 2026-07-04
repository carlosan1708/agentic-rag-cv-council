# Changelog

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
