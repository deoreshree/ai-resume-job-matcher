# Technical Audit — AI Resume & Job Matcher

**Audit date:** 2026-08-31 · **Commit audited:** `238bca5` (main) · **Branch:** `arena/01a05817-ai-resume-job-matcher`

Everything below was verified by reading the code *and* executing the application and its test
suite (25/25 tests pass in a working environment). Method: fresh venv, module-by-module review,
live HTTP exercise of every route, edge-case probes against the parser/matcher/ATS/job analyzer,
data-consistency checks between `job_roles.json` and `skills.json`, and dependency-resolution
checks of every pin in `requirements.txt`.

---

## Executive summary

The application is **architecturally sound and mostly functional**. The Flask API, resume
parser, matcher, ATS analyzer, recommendation engine, interview generator, and report builder
all work, and the offline (no-API-key) degradation paths are genuinely well designed. The test
suite is real and passing.

However, the project **cannot be installed as documented** (`requirements.txt` contains pins
that do not exist / do not resolve on the Python version the Dockerfile uses), the **results UI
is visually broken** (missing CSS rules cause all seven result sections to render stacked
together), and there are several correctness bugs in experience estimation, name detection,
skill false-positives, and semantic-score calibration. The README's "100% DEVELOPED &
PRODUCTION-READY" claim is not accurate.

**Verdict: ~80% complete, with 1 deployment blocker, 1 major UI bug, and a series of
fixable correctness/calibration issues.**

---

## 1. What already works (verified live)

| Area | Status | Evidence |
|---|---|---|
| `GET /` serves the SPA | ✅ | 200, 7.3 KB HTML |
| `GET /api/roles` | ✅ | 200, returns 15 roles |
| `POST /api/analyze` (role mode) | ✅ | 200; full analysis payload with all 7 top-level keys |
| `POST /api/analyze` (custom JD mode) | ✅ | 200; skills/experience/education extracted from pasted JD |
| `POST /api/report` | ✅ | 200; self-contained HTML, properly escaped, served as attachment |
| PDF/DOCX text extraction | ✅ | pypdf + python-docx; encrypted-PDF and corrupt-file friendly errors |
| Section splitting, contact extraction | ✅ | 8 section aliases; email/phone/URL/LinkedIn/GitHub detection |
| Catalog skill extraction | ✅ | 67 skills / 7 categories; alias normalization (`sklearn`→`Scikit-learn`) |
| Skill & keyword matching | ✅ | Boundary-aware; required/preferred split; explainable gaps |
| Weighted scoring | ✅ | 5 components, weights sum validated, contributions exposed |
| ATS analyzer | ✅ | 5 weighted heuristic components + actionable recommendations |
| Recommendation engine | ✅ | Deterministic, honest ("consider learning") advice |
| Interview generator | ✅ | 4 groups (technical/project/HR/scenario), evidence-derived |
| GenAI advisor fallback | ✅ | Works with no key; `source`/`notice` fields are honest |
| Semantic fallback | ✅ | TF-IDF cosine when embeddings disabled/unavailable |
| Tests | ✅ | 25/25 pass in 1.4 s (heuristic mode, no spaCy model) |
| Data consistency | ✅ | Every required/preferred skill of all 15 roles exists in the skill catalog |
| XSS safety | ✅ | `escapeHtml()` used consistently in the frontend; `escape()` in reports (verified `<Candidate>` → `&lt;Candidate&gt;`) |

## 2. Partially implemented

1. **Semantic matching** — embeddings path exists but is opt-in (`ENABLE_EMBEDDINGS`) and
   silently falls back to TF-IDF; the TF-IDF path is systematically under-calibrated (§8).
2. **GenAI advice** — LLM path exists but is untested (no unit test mocks a successful LLM
   response); `OPENAI_MODEL`/`max_tokens` are fine on the pinned SDK but the pin is 3 years old.
3. **Custom JD analysis** — works, but a JD containing **zero catalog skills** yields a
   misleading skills score of 100 (§8) and noisy "keywords" (§11).
4. **Deployment** — Dockerfile/gunicorn/Procfile all exist but the image cannot build (§13) and
   runs as root with no `.dockerignore`.
5. **spaCy NER** — code path exists; without the model the parser falls back to heuristics,
   which mis-detects names (§7).

## 3. Broken

1. **`pip install -r requirements.txt` fails** — fatal for local setup *and* Docker build (§13).
2. **Results UI shows every section at once** — `static/css/style.css` has no `.view` /
   `.view.active` rules; the nav toggles a class that has no effect (§11).
3. **`utils/report_builder.build_html_report` crashes** (`AttributeError: 'NoneType' object has
   no attribute 'replace'`) when interview entries contain non-string fields — reachable via
   `POST /api/report` with a hand-edited payload; returns an HTML 500 page instead of JSON.
4. **README references a LICENSE file that does not exist.**
5. **`.gitignore` still contains a Streamlit section** (legacy of a pre-Flask architecture);
   `models/` directory is an unused vestige.

## 4. APIs / routes — correctness

Routes themselves are correct and consistent with the frontend. Findings:

- ✅ `/api/analyze` reads only the mode-relevant form fields, so the frontend sending both
  `job_role` and `job_description` is harmless (verified).
- ⚠️ **No `/api/health`** — the Docker healthcheck pokes `/` (HTML) instead; platforms expect a
  lightweight JSON liveness endpoint.
- ⚠️ **Unhandled exceptions return Flask's HTML 500 page** — a JSON API should always return
  JSON. No generic 500 handler exists.
- ⚠️ `RuntimeError` from `load_job_roles()` (missing/corrupt `data/job_roles.json`) is a 500
  with no friendly JSON message.
- ✅ 404 and 413 handlers return JSON.
- ✅ `/api/roles` deliberately returns only titles — matches frontend usage.

## 5. Frontend buttons/features that do nothing (or misbehave)

1. **Section navigation appears dead** — clicking nav links toggles `.active` on `.view`
   sections, but the CSS never defines `.view { display:none }` / `.view.active { display:block }`.
   Result: after the first analysis **all seven sections are stacked on one page** and nav clicks
   change almost nothing. This is the single biggest visible defect.
2. **Brand link (`ResumeMatch`) does nothing** — it is an `href="#dashboard"` anchor with no
   handler; it just sets the URL hash.
3. **Report filename**: the browser ignores the server's `download_name` and always saves
   `resume-match-report.html`.
4. Everything else (analyse button, mode toggle, file picker label, advice tabs, interview
   `<details>`, download button, disabled states, loading spinner) **works**.

## 6. JSON/API response mismatches

- ✅ Frontend ↔ backend contract is consistent for all rendered fields (checked every
  `data.x.y` access in `app.js` against live responses).
- ⚠️ Duplication: with no LLM key, `insights` and `advisor` in the response are two copies of
  the same rule-based content (wasted payload, mildly confusing to API consumers).
- ⚠️ No API versioning / OpenAPI spec (fine at this scale, noted only).
- ⚠️ Error responses from `/api/analyze` are JSON, but unexpected 500s are HTML (see §4).

## 7. Resume parsing problems (verified with probes)

1. **Experience inflation**: `estimate_years_of_experience(sections.get("experience") or cleaned)`
   (`modules/resume_parser.py:172`) — when no experience section is detected, the **whole
   resume** is scanned for date ranges, so education dates ("2018 - 2022") are counted as work
   experience. Probe: education-only resume → `years_experience = 4.0`. This corrupts the
   15%-weight experience component *and* fabricates a "meets minimum experience" strength.
2. **Name detection**: without the spaCy model, the first "looks like a name" line wins, so
   `Data Scientist\nJohn Doe` yields candidate name **"Data Scientist"**. Role-title lines are
   not filtered.
3. Missing heading aliases: "Relevant Experience", "Employment History", "Professional
   Background", "Selected Projects", "Skill Set" etc. are not recognized → triggers problem 1.
4. Two-column / image-only PDFs: extraction is single-pass pypdf (interleaved columns) — a known
   limitation, already documented in README; OCR is future work.
5. No cap on extracted text size (a crafted DOCX/PDF could decompress to an enormous string) —
   minor DoS hardening gap.

## 8. Job matching problems

1. **Short-alias false positives** (`modules/skill_extractor.py:64`): only `" c "` is guarded;
   `R` matches inside **"R&D"**, `Go` matches inside **"go-to-market"** (probe returned
   `['C++', 'R', 'Go']` for that sentence). Creates phantom "matching skills" and inflates ATS
   skill scores.
2. **Zero-skill JD scores 100 on skills** (`modules/matcher.py:46`): a custom JD with no
   catalog skills (e.g. a nursing job) gives skills component = 100 (40% of the total) — the
   user sees a falsely high match. Should be neutral (50) + an explicit warning surfaced to the UI.
3. **Semantic under-calibration** (`modules/matcher.py:96-105`): for predefined roles the
   profile text is ~20 words while the resume is hundreds; TF-IDF cosine is structurally
   crushed. Verified: a *Data Scientist* resume vs the **Data Scientist** role scores only
   **20.8%** semantic. Ordering is right (DS ≫ DevOps ≫ Frontend) but the absolute value drags
   every total down. Comparing a structured resume *digest* (skills + titles + keywords) as
   well and taking the better of the two lifts the true match to 25.2% while leaving
   unrelated roles at ~0 — still conservative but fairer; embeddings path remains the upgrade.
4. Keyword matching is exact-phrase (no stemming) — "predictive models" ≠ "predictive
   modeling". Documented behavior; acceptable, noted.

## 9. ATS scoring problems

- ✅ Structure/keywords/skills/readability/formatting weights (30/25/20/15/10) are applied
  correctly and bounded 0–100.
- ⚠️ The ATS **skills** component inherits both the false-positive bug (§8.1) and the
  empty-JD-100 bug (§8.2).
- ⚠️ `structure` requires 5 exact sections; partially-detected headings (§7.3) silently lower
  it. Improving aliases (§7.3) helps ATS accuracy too.
- ⚠️ Readability heuristic penalizes long sentences but ignores bullet density (formatting
  covers that) — fine, documented.

## 10. GenAI integration problems

1. `openai==1.3.0` (Nov 2022) is pinned — very old; works for `chat.completions.create` but is
   far behind fixes/deprecations. Should be a modern 1.x pin.
2. **The LLM success path has zero test coverage** — only the no-key fallback is tested.
   `_valid_response()` requires all 7 keys present and string lists; an LLM returning partial
   JSON silently falls back (good, but untested).
3. No timeout is set on the OpenAI call → a hung upstream stalls the request worker for the
   gunicorn timeout (30 s) and returns a generic fallback. A explicit short timeout is safer.
4. `max_tokens=1300` is deprecated on newer SDKs (still accepted on 1.x) — fine once pinned.

## 11. UI/UX problems

1. Missing `.view` CSS rules — the headline defect (§5.1).
2. Nav links `preventDefault` → no URL state / back-button support ( SPA-without-router smell).
3. No visible indication of *which* target (role vs JD) produced the score on the dashboard
   (it exists in the Match view) — minor.
4. No auto-dismiss of the success notice — minor.
5. Custom-JD keywords list is noisy (`_candidate_keywords` extracts any 2–3-word phrase;
   "equal opportunity employer"-style filler becomes "missing keywords") — minor quality issue.
6. The file input is visually hidden (styled label) — keyboard focus indicator not styled — minor.

## 12. Missing tests

- **No API/route tests at all** (`app.py` is untested: happy paths, error paths, 404/413, report).
- No tests for `utils/helpers.py` (date-range parsing, interval merging, experience estimation).
- No test for `modules/recommendation_engine.py`.
- No test for the LLM success path of `advise_resume` (mocked `generate_text`).
- No data-consistency test that every role skill exists in the catalog (protects future edits).
- No regression tests for the bugs found in this audit.
- No CI workflow (`.github/` absent).

## 13. Deployment problems

1. **`requirements.txt` is uninstallable** — verified against PyPI (2026-08-31):
   - `numpy==2.5.2` → requires Python ≥3.12; **Dockerfile uses `python:3.11-slim`** and README
     targets 3.10+. `pip install` aborts (also on the documented local-setup path).
   - `scipy==1.18.1` → **does not exist** (latest is 1.17.1).
   - `torch==2.1.0` + numpy 2.x → ABI incompatibility (`_ARRAY_API not found` crashes) even on
     Python 3.12, i.e. the file is broken for every interpreter.
   - `sentence-transformers==6.0.0` + `torch==2.1.0` pull ~2 GB of wheels into every deployment
     for a feature that is off by default.
2. **Dockerfile**: no `.dockerignore` (`.venv/`, `.git/`, test artifacts would be copied by
   `COPY . .`); runs as **root**; gunicorn `--bind 0.0.0.0:5000` ignores `$PORT` (breaks
   Heroku-style platforms; the Procfile handles `$PORT` but the image does not); builder stage
   copies packages from *both* `/root/.local` and `/usr/local/lib/.../site-packages`
   (double-copy confusion); healthcheck hits `/` (HTML) instead of a health endpoint.
3. **gunicorn.conf.py**: `workers = max(2, cpu_count())` — unbounded on large hosts; with
   sklearn+spaCy loaded per worker this can exhaust memory. A small cap is safer.
4. **Procfile** is correct.
5. README: "Status: ✅ 100% DEVELOPED & PRODUCTION-READY", Streamlit leftovers in docs/gitignore,
   references a missing LICENSE, `python -m sentence_transformers download ...` is not a real
   command for the pinned versions, and the "Memory Usage ~500MB" claim assumes models that the
   default install doesn't even load.

## 14. Security issues

- ✅ No storage of resumes (in-memory pipeline) — verified; no `open(..., 'w')` anywhere.
- ✅ File type + size validation; friendly errors; pypdf/docx failures handled.
- ✅ HTML escaping in reports and frontend (verified).
- ✅ API keys only from env; never echoed; `.env` gitignored.
- ⚠️ **No security headers** (no `X-Content-Type-Options`, `X-Frame-Options`/CSP,
  `Referrer-Policy`).
- ⚠️ **No rate limiting** on the CPU-bound `/api/analyze` (public deployments can be hammered).
- ⚠️ Container runs as root (§13).
- ⚠️ No cap on extracted text size (decompression-amplification, §7.5).
- ℹ️ No CSRF token on `/api/analyze` — acceptable for a stateless, no-cookie API (cross-site
  callers cannot read responses), noted for completeness.

## 15. Missing production features

1. `/api/health` liveness endpoint (JSON).
2. CI (GitHub Actions) running the test suite.
3. Rate limiting (best-effort, in-memory is fine for this architecture).
4. Non-root container + `.dockerignore`.
5. A LICENSE file.
6. Structured request/error logging hook (gunicorn access logs only).
7. Optional (documented future): OCR, multilingual, DB-backed history/auth, report PDF export.

---

# Prioritized implementation plan

**P0 — application cannot run / critical**

| # | Issue | Fix |
|---|---|---|
| P0-1 | `requirements.txt` uninstallable (numpy/scipy/torch) | Fix pins to py3.11-compatible versions; move `sentence-transformers`/`torch` to `requirements-embeddings.txt` (feature preserved, documented); bump `openai` pin to modern 1.x. Verify a fresh install from the file. |

**P1 — major feature failures**

| # | Issue | Fix |
|---|---|---|
| P1-1 | Results UI: all sections stacked (missing `.view` CSS) | Add `.view{display:none}` / `.view.active{display:block}` (+ print styles). |
| P1-2 | Experience inflated by education dates | Only scan date ranges in experience-like sections; exclude education/projects/certifications from the fallback; add missing heading aliases. |
| P1-3 | Name = job title (heuristic mode) | Skip title-like lines using the role catalog + title vocabulary before accepting a name. |
| P1-4 | Docker image broken / root / `$PORT` ignored / no `.dockerignore` | Rebuild Dockerfile (non-root, `$PORT`, layered caching, healthcheck on `/api/health`), add `.dockerignore`. |
| P1-5 | No `/api/health` | Add JSON health endpoint; align Docker healthcheck. |
| P1-6 | HTML 500 pages from a JSON API | Generic JSON 500 handler + defensive error handling in report builder. |

**P2 — incomplete features / correctness**

| # | Issue | Fix |
|---|---|---|
| P2-1 | Skill false positives (`R&D`→R, `go-to-market`→Go) | Generalize short-alias boundary rules (`len ≤ 2` aliases reject `-`/`&` adjacency); remove the `" c "` special case. |
| P2-2 | Zero-skill JD ⇒ skills score 100 | Neutral 50 when *both* required & preferred are empty, plus `warnings[]` on the profile surfaced in UI + report. |
| P2-3 | Semantic under-calibration | Also compare a structured resume digest and take the better score (embeddings path untouched). |
| P2-4 | Report builder crashes on malformed entries | Defensive string coercion in `_question_items`/`_items`. |
| P2-5 | Missing tests | Add API route tests, helpers tests, recommendation-engine tests, mocked-LLM advisor tests, data-consistency test, regression tests for every fix above. |
| P2-6 | README inaccuracies + missing LICENSE | Correct status/install/embeddings docs (Python 3.11+, extras file), add MIT LICENSE, remove Streamlit leftovers. |
| P2-7 | LLM call has no timeout | Add a request timeout to `generate_text`. |

**P3 — UI/UX improvements**

| # | Issue | Fix |
|---|---|---|
| P3-1 | Brand link does nothing | Route it to the dashboard view. |
| P3-2 | Report filename ignored | Honor server `Content-Disposition` filename. |
| P3-3 | No security headers | Add `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP via `after_request`. |
| P3-4 | Noisy JD keywords | Expand the blocked-phrase list in `_candidate_keywords`. |
| P3-5 | gunicorn worker explosion on big hosts | Cap workers (`min(4, …)`). |
| P3-6 | Text-size cap missing | Cap extracted resume text at a sane maximum (zip-bomb guard). |

**P4 — optional enhancements**

| # | Item |
|---|---|
| P4-1 | GitHub Actions CI (py3.11 + py3.12 matrix, pytest). *(implemented — cheap & high value)* |
| P4-2 | Best-effort in-memory rate limiting for `/api/analyze` (per-IP, configurable, default generous). *(implemented)* |
| P4-3 | OCR for image-only PDFs, multilingual parsing, PDF report export, DB history/auth — documented as future work, intentionally not attempted now. |

Non-goals (explicitly preserved): the Flask + static-SPA architecture, the module layout, the
scoring weights, the privacy model (in-memory, no storage), and all existing behavior that the
current test suite pins down.
