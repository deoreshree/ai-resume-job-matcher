# AI Resume & Job Match Predictor

An offline-first Streamlit application that reads a candidate's PDF or DOCX resume, compares evidence from it with a job role or job description, and produces transparent career guidance. It is designed as an AIML internship and portfolio project—not as an automated hiring decision.

## Problem statement

Candidates often have difficulty understanding how their documented experience relates to a role. Manual comparison is slow and can overlook terminology, transferable evidence, and practical learning gaps. This project turns that comparison into a private, explainable workflow.

## Objectives

- Extract readable resume content without permanently saving the uploaded file.
- Identify contact information, education, experience, projects, certifications, and catalogued skills.
- Analyse either a predefined role or a pasted job description.
- Calculate an auditable weighted match score and ATS compatibility score.
- Provide truthful skill-gap, resume-improvement, and interview-preparation guidance.

## Features

- PDF and DOCX extraction with friendly validation for empty, damaged, oversized, encrypted, or unsupported files.
- Editable skills catalog and 15 predefined roles.
- Hybrid NLP/heuristic parsing for resume sections, contact details, education, experience, projects, and certifications.
- Exact skill and keyword matching plus local TF-IDF cosine similarity; an installed local sentence-transformer can be enabled optionally.
- Weighted score: Skills 40%, Semantic similarity 25%, Experience 15%, Education 10%, Keywords 10%.
- ATS diagnostics for keyword evidence, section structure, skills, readability, and formatting.
- Offline rule-based advice and interview questions; optional OpenAI-compatible advice when configured.
- Professional Streamlit dashboard with charts, tabs, progress indicators, and downloadable HTML analysis report.

## Technology stack

Python, Streamlit, pypdf, python-docx, spaCy (optional enrichment), scikit-learn, sentence-transformers (optional local embeddings), Plotly, OpenAI SDK (optional), and pytest.

## Architecture and data flow

```text
PDF/DOCX upload (memory only)
  -> text extraction and cleaning
  -> hybrid resume parsing + catalog skill extraction
  -> selected role or custom job-description analysis
  -> skill / keyword / semantic / experience / education matching
  -> weighted score + ATS analysis
  -> deterministic insights + interview pack (+ optional LLM phrasing)
  -> Streamlit dashboard and HTML report download
```

Key directories:

```text
app.py                 Streamlit entry point
data/                  Editable skills and job-role catalogs
modules/               Parsing, extraction, matching, scoring, ATS, insights
genai/                 Optional LLM wrapper, advisor, interview generator
utils/                 Text, validation, and in-memory report utilities
tests/                 Parser, extraction, matching, scoring, ATS, job tests
```

## NLP and ML methodology

The parser uses regular expressions for reliable fields such as email, phone, URLs, dates, and degrees; section-aware heuristics for resume structure; and spaCy named-entity/keyphrase enrichment when its local model is installed. Skills are matched against an editable alias catalog with word boundaries, preventing common false positives (for example, matching `Java` inside `JavaScript`).

The matcher calculates exact skill coverage, job-keyword coverage, years-of-experience coverage, and degree evidence. Semantic relevance uses TF-IDF with unigrams and bigrams plus cosine similarity entirely locally. Set `ENABLE_EMBEDDINGS=true` only after placing the configured sentence-transformer model in the local cache; otherwise TF-IDF is the deliberate, transparent fallback.

## Match score formula

```text
overall = skills × 0.40
        + semantic similarity × 0.25
        + experience × 0.15
        + education × 0.10
        + keyword coverage × 0.10
```

Every component and weighted contribution is shown in the application so the final percentage can be inspected.

## Optional GenAI methodology

The core app never requires an API key. When `OPENAI_API_KEY` or `LLM_API_KEY` is configured, the advisor receives only structured facts extracted from the active resume and role analysis. Its prompt explicitly forbids inventing skills, companies, projects, credentials, achievements, or numbers. Service errors and invalid responses fall back to deterministic guidance.

## Installation

Prerequisites: Python 3.10+ and a readable PDF/DOCX resume.

```powershell
# From the downloaded project folder
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If you want optional spaCy enrichment, install its language model after the dependencies:

```powershell
python -m spacy download en_core_web_sm
```

The app continues with heuristic parsing when that model is absent.

## Environment variables

Copy `.env.example` to `.env`. No key is needed for the normal analysis flow.

```dotenv
OPENAI_API_KEY=
# or
LLM_API_KEY=
OPENAI_MODEL=gpt-4o-mini
ENABLE_EMBEDDINGS=false
```

Never commit `.env`. The provided `.gitignore` excludes keys, virtual environments, temporary files, and uploaded resume locations.

## Running the app

```powershell
.\.venv\Scripts\streamlit run app.py
```

Open the local URL Streamlit prints. Upload a PDF/DOCX, select a predefined role or paste a complete job description, then click **Analyse resume**.

## Testing

```powershell
.\.venv\Scripts\python -m pytest -q
```

The suite covers PDF/DOCX parsing, validation, skill aliases and false-positive resistance, job extraction, matching, semantic fallback, score math, and ATS output.

## Screenshots

Run the application locally and add screenshots of the Dashboard, Job Match, Skill Gap, and ATS Analysis tabs here for a GitHub portfolio presentation. Do not include a real resume's contact details in public screenshots.

## Privacy and limitations

Uploaded files are processed in memory and the application does not write their content to disk or log contact details. Output quality depends on an extractable PDF/DOCX and conventional headings. Semantic similarity is a relevance signal, not proof of qualification, and the app should not be used as the sole basis for hiring or career decisions. Users must verify all extracted information and advice.

## Future enhancements

- OCR for image-only resumes after an explicit privacy review.
- Multiple role comparison and user-controlled score weights.
- Additional local embedding models and multilingual extraction.
- Export to styled PDF and accessibility/usability evaluation.

## Author

Built as an AI/ML internship project. Update this section with your name, institution, and repository link before publishing.
