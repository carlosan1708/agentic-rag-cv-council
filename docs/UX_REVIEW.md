# UI/UX Review

Reviewed against live screenshots captured with Playwright (`scripts/record_demo.py` regenerates
them under `docs/assets/`). Items marked ✅ were fixed as part of this review.

## What works well

- **The wizard metaphor is clear.** The stepper plus "Step N: ..." headers keep users oriented, and
  each step has exactly one primary action styled as the primary button.
- **The results screen is the strongest part of the product.** Tabs separate the narrative report,
  the actionable tweaks, the score dashboard, and the deliverables — matching how users actually
  consume the output (read → act → verify → download).
- **The ATS dashboard communicates instantly**: before/after metrics with a delta, a progress bar,
  and a section checklist read at a glance (see `assets/results_ats.png`).
- **Demo mode removes the biggest onboarding wall.** Previously a visitor had to produce an API key
  before seeing any value; now the second button on the welcome screen shows the full product in
  under ten seconds.

## Findings and fixes

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | Persona list rendered in filesystem order: healthcare packs first, the default-selected "LinkedIn Matchmaker" buried at the bottom of 20 checkboxes (`assets/team.png`). Users couldn't see *why* something was pre-selected. | High | ✅ Recommended packs (matchmaker, general) now sort first, rest alphabetical |
| 2 | First-run friction: the app opened on an API-key form — the least motivating first screen possible. | High | ✅ "Try the Demo" on the welcome screen bypasses it entirely |
| 3 | The optional Personalize step (step 6) was invisible in the stepper — users landing there had no orientation. | Medium | ✅ Stepper now shows a sixth "Polish" step and renders on step 6 |
| 4 | Pre-run screen stacked three message boxes (summary + "click the button below" + time warning) before the CTA (`assets/pre_run.png`). | Low | ✅ Redundant "click the button" box removed |
| 5 | Welcome copy said "Configuration → …" while the stepper says "Setup" — same step, two names. | Low | ✅ Copy aligned with stepper labels |
| 6 | Personalize step had two stacked "Back" buttons (one in the container, one outside). | Low | ✅ Fixed earlier in the expansion |
| 7 | "Logged in as" indicator lives in the collapsed sidebar, effectively invisible. | Low | Open — consider a header chip instead |
| 8 | Persona labels expose the source filename ("(sales_marketing)") — functional but technical. | Low | Open — consider human-friendly pack names ("Sales & Marketing") |
| 9 | The results tab count grows with options (up to 6 tabs); on mobile widths the tab bar scrolls. | Low | Open — acceptable for now; revisit if more tabs are added |
| 10 | Streamlit's default "Deploy" toolbar button shows in production. | Cosmetic | Open — can be hidden via `.streamlit/config.toml` `toolbarMode = "minimal"` |

## Recommendations for a future pass

1. **Upload before configure.** Asking for the CV first (value) and the provider/key at analysis
   time (cost) would follow the "commitment gradient" pattern; demo mode softens this today.
2. **Named persona packs.** Map file stems to display names and show a small pack badge instead of
   the parenthesized filename.
3. **Progress skeletons during analysis.** The live tabs update on task completion; a per-specialist
   progress list ("Recruiter ✅ / Matchmaker ⏳") would make the 2-minute wait feel shorter.
4. **A header account chip** (email + logout) when AUTH_MODE=approval, replacing the sidebar text.

## Screenshots

| Screen | File |
|--------|------|
| Welcome | `assets/welcome.png` |
| Team selection | `assets/team.png` |
| Pre-run summary | `assets/pre_run.png` |
| Board report | `assets/results_board.png` |
| Minimal changes | `assets/results_changes.png` |
| ATS dashboard | `assets/results_ats.png` |
| Final CV + downloads | `assets/results_cv.png` |
| Cover letter | `assets/results_cover.png` |
| Interview prep | `assets/results_interview.png` |
