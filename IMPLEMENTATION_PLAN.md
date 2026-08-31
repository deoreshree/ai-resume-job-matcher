# Implementation Plan & Execution Log

Companion to `AUDIT.md` (the full technical audit). Every item below was executed on branch
`arena/01a05817-ai-resume-job-matcher`. "Preserve" rules applied throughout: no architecture
changes, no feature removals, existing modules reused; every pre-existing test kept passing.

Legend: ✅ done · 🔶 done with scope note · ⬜ deliberately not attempted (documented)

## P0 — Application cannot run / critical

| # | Issue | Action taken | Status |
|---|---|---|---|
| P0-1 | `requirements.txt` uninstallable (`numpy==2.5.2` needs py≥3.12, `scipy==1.18.1` does not exist, `torch==2.1.0` ABI-incompatible with numpy 2.x, `spacy==3.8.1` yanked from PyPI) | Re-pinned to verified py3.11-compatible versions (`numpy==2.2.6`, `scipy==1.17.1`, `spacy==3.8.16`, `openai==1.109.1`); moved `sentence-transformers`/`torch` to optional `requirements-embeddings.txt` (feature preserved & documented); removed unused `python-multipart`; verified with a clean resolve + fresh-venv install + full test run | ✅ |

## P1 — Major feature failures

| # | Issue | Action taken | Status |
|---|---|---|---|
| P1-1 | All seven result sections rendered at once; nav appeared broken (no `.view` CSS rules) | Added `.view{display:none}` / `.view.active{display:block}` + subtle transition + print styles | ✅ |
| P1-2 | Education year ranges counted as work experience (`years_experience=4.0` for a fresh graduate) | Date ranges now only trusted from experience sections; fallback excludes education/projects/certifications/achievements/skills; added missing heading aliases (`Relevant Experience`, `Employment History`, `Professional Background`, `Career History`, `Skill Set`, `Selected Projects`, …) | ✅ |
| P1-3 | Candidate name detected as job title ("Data Scientist") when spaCy model absent | Header lines matching the role catalog or a title vocabulary are skipped before accepting a name | ✅ |
| P1-4 | Docker image unbuildable / root user / `$PORT` ignored / no `.dockerignore` | Rebuilt multi-stage Dockerfile (venv-based, non-root `appuser`, `EXPOSE`, healthcheck on `/api/health`, CMD via `gunicorn.conf.py` which honors `$PORT`); added `.dockerignore` excluding secrets | ✅ |
| P1-5 | No health endpoint | `GET /api/health` → `{"status":"ok"}`; Docker healthcheck aligned | ✅ |
| P1-6 | JSON API returned HTML 500 pages on unexpected errors | Generic JSON handlers for 500 & 405; `analyze` wraps unexpected failures; report builder hardened (no crash on tampered payloads) | ✅ |

## P2 — Incomplete features / correctness

| # | Issue | Action taken | Status |
|---|---|---|---|
| P2-1 | Skill false positives: `R&D`→R, `go-to-market`→Go (and the `" c "` guard was dead code) | Generalized boundary rule for aliases ≤2 chars (reject `-`/`&` adjacency); dead special case removed; R/Go still detected legitimately | ✅ |
| P2-2 | Custom JD with zero catalog skills ⇒ skills component = free 100% | Neutral 50% when required+preferred both empty; `warnings[]` added to profile; surfaced in Match view and HTML report | ✅ |
| P2-3 | Semantic component systematically crushed (20.8% for a true Data-Scientist match) | Matcher now also compares a structured resume digest (skills/degrees/titles/keywords) and takes the better score; embeddings path untouched | ✅ |
| P2-4 | `build_html_report` crashed on malformed entries | Defensive coercion (`_safe`, `_as_float`, dict/type checks) throughout | ✅ |
| P2-5 | Missing tests (no API/helper/rec-engine/LLM-path/consistency tests) | Added 6 test modules; suite grew 25 → 71 tests covering routes, helpers, recommendations, mocked-LLM advisor paths, catalog consistency, and regressions for every audit fix | ✅ |
| P2-6 | README overclaims ("100% production-ready"), missing LICENSE, stale Streamlit artifacts | README corrected (status, Python 3.11+, endpoints, embeddings extras, new env vars, file tree); MIT LICENSE added (change it if you prefer another); Streamlit section removed from `.gitignore` | 🔶 (LICENSE choice is yours to confirm) |
| P2-7 | LLM call had no timeout | `LLM_TIMEOUT_SECONDS` (default 20 s) passed to the OpenAI client | ✅ |

## P3 — UI/UX & polish

| # | Issue | Action taken | Status |
|---|---|---|---|
| P3-1 | Brand link did nothing | Clicking now returns to the dashboard view | ✅ |
| P3-2 | Report download ignored the server filename | Frontend parses `Content-Disposition` (incl. `filename*`) | ✅ |
| P3-3 | No security headers | `after_request` sets nosniff, frame denial, referrer policy, CSP | ✅ |
| P3-4 | Noisy custom-JD keywords ("equal opportunity employer" etc.) | Blocked-phrase list + leading/trailing stopword filtering | ✅ |
| P3-5 | Unbounded gunicorn workers on large hosts | `workers = min(4, max(2, cpu_count))` | ✅ |
| P3-6 | No cap on extracted resume text (decompression amplification) | `MAX_RESUME_TEXT_CHARS` cap (default 400k) in the parser | ✅ |

## P4 — Optional enhancements

| # | Item | Status |
|---|---|---|
| P4-1 | GitHub Actions CI (pytest on py3.11 & 3.12 + boot smoke test) | ✅ `.github/workflows/ci.yml` |
| P4-2 | Best-effort in-memory rate limiting for `/api/analyze` (per-IP sliding window, `RATE_LIMIT_PER_MINUTE`, default 30, 0=off, 429 + `Retry-After`) with unit tests | ✅ |
| P4-3 | OCR for image-only resumes, multilingual parsing, PDF report export, persistence/auth, resume comparison | ⬜ Future work — intentionally not attempted to avoid architecture churn |

## Verification performed

1. `pytest -q` → **71/71 pass** (was 25).
2. Fresh venv `pip install -r requirements.txt` → clean install, no warnings; app boots; full
   endpoint exercise passes (`/`, `/api/roles`, `/api/health`, `/api/analyze` role+custom,
   `/api/report`, error paths, 429 limiter).
3. Regression probes from the audit re-run: education-only experience = 0.0; title-line name
   detection fixed; `R&D`/`go-to-market` no longer produce skills; zero-skill JD warns and
   scores neutral; semantic ordering preserved with fairer absolute values.
4. Live UI check of the served frontend: `.view` toggling now hides/shows sections correctly.
