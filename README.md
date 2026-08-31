# AI Resume & Job Match Predictor

An **offline-first Flask REST API** that reads a candidate's PDF or DOCX resume, compares evidence from it with a job role or job description, and produces transparent career guidance. It is designed to be privacy-first, explainable, and production-ready.

**Status**: ✅ **Feature-complete and deployable.** Core analysis, matching, ATS, guidance, interview prep, reports, and deployment all work. See `AUDIT.md` for a full technical audit (including known limitations) and `IMPLEMENTATION_PLAN.md` for the prioritized roadmap that was executed. Optional enhancements (OCR, PDF export, multilingual parsing) remain future work.

---

## Problem Statement

Candidates often have difficulty understanding how their documented experience relates to a role. Manual comparison is slow and can overlook terminology, transferable evidence, and practical learning paths. This tool provides **evidence-based, transparent matching** without storing personal data.

---

## Features

✅ **Resume Parsing**
- PDF and DOCX extraction with validation
- Hybrid NLP/heuristic parsing for sections, contact, education, experience, projects, certifications
- Skill extraction from resume text with catalog normalization

✅ **Job Matching**
- 15 predefined job roles (Data Scientist, Software Engineer, etc.)
- Custom job description analysis
- Exact skill and keyword matching
- TF-IDF semantic similarity (+ optional sentence-transformers)
- Multi-component weighted scoring (Skills 40%, Semantic 25%, Experience 15%, Education 10%, Keywords 10%)

✅ **ATS Analysis**
- Resume structure assessment
- Keyword evidence detection
- Readability and formatting scoring
- Actionable recommendations

✅ **Career Guidance**
- Rule-based recommendations (no API key needed)
- Optional AI-enhanced advice (with OpenAI key)
- Personalized interview questions (Technical, HR, Project, Scenario)
- HTML report generation and download

✅ **Modern Frontend**
- Responsive HTML/CSS/JavaScript
- Dashboard with score breakdown
- Multiple analysis views
- Real-time form validation
- Progress indicators

✅ **Production Ready**
- Docker containerization (multi-stage, non-root user, healthcheck)
- Cloud deployment (Render, Heroku)
- Gunicorn WSGI server
- Environment variable configuration
- In-memory processing (no disk storage)
- Security headers (CSP, nosniff, frame denial)
- Best-effort rate limiting on the analysis endpoint
- Comprehensive test suite (71+ tests) with CI

---

## Technology Stack

**Backend**: Flask 3.1+, Python 3.11+
**ML/NLP**: scikit-learn, spaCy, sentence-transformers (optional), nltk
**Resume Parsing**: pypdf, python-docx
**Optional AI**: OpenAI SDK
**Production**: Gunicorn, Docker
**Testing**: pytest

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flask REST API                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend (HTML/CSS/JS)  ←→  Backend (Python Flask)        │
│                                                              │
│  Endpoints:                                                 │
│  • GET  /             → Serve index.html                   │
│  • GET  /api/roles    → List predefined job roles          │
│  • GET  /api/health   → JSON liveness check                │
│  • POST /api/analyze  → Parse resume & calculate match     │
│  • POST /api/report   → Generate downloadable report       │
└─────────────────────────────────────────────────────────────┘
         ↓
    ┌─────────────────────────────────────────────────┐
    │           Core Processing Pipeline             │
    ├─────────────────────────────────────────────────┤
    │ 1. Resume Extract (PDF/DOCX → text)            │
    │ 2. Resume Parse (text → structured data)       │
    │ 3. Skill Extract (catalog-backed)              │
    │ 4. Job Analysis (role or custom description)   │
    │ 5. Matching (skills, semantic, keywords)       │
    │ 6. Scoring (weighted multi-component)          │
    │ 7. ATS Analysis (structure, readability)       │
    │ 8. Insights (rule-based or AI-enhanced)        │
    │ 9. Report Build (in-memory HTML)               │
    └─────────────────────────────────────────────────┘
```

---

## Installation & Setup

### Prerequisites
- Python 3.11 or higher (the version the Docker image uses; 3.12 also works)
- pip (Python package manager)

### Local Development

```bash
# Clone the repository
git clone https://github.com/deoreshree/ai-resume-job-matcher.git
cd ai-resume-job-matcher

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (optional, for NER enhancement)
python -m spacy download en_core_web_sm
```

### Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env (optional - all features work without keys)
# OPENAI_API_KEY=sk-...          # Optional: for AI-enhanced advice
# ENABLE_EMBEDDINGS=false         # Optional: enable after downloading model
```

---

## Running the Application

### Local Development (Flask Development Server)

```bash
python app.py
```

The application will start on `http://localhost:5000`

### Production (Gunicorn)

```bash
gunicorn app:app
```

Or with custom configuration:

```bash
gunicorn -c gunicorn.conf.py app:app
```

### Docker

**Build the image:**
```bash
docker build -t ai-resume-matcher .
```

**Run the container:**
```bash
docker run -p 5000:5000 \
  -e OPENAI_API_KEY=sk-... \
  ai-resume-matcher
```

### Cloud Deployment

**Render.com** (using Procfile):
```bash
git push origin main
# Render auto-detects Procfile and deploys
```

**Heroku**:
```bash
heroku create your-app-name
git push heroku main
```

---

## API Endpoints

### GET `/`
Returns the static HTML frontend.

### GET `/api/roles`
Returns available predefined job roles.

**Response:**
```json
{
  "roles": [
    {"title": "Data Scientist"},
    {"title": "Software Engineer"},
    ...
  ]
}
```

### POST `/api/analyze`
Analyzes a resume against a job role or custom description.

**Request (form-data):**
- `resume`: PDF or DOCX file
- `target_mode`: "role" or "custom"
- `job_role`: (if mode=role) Role title
- `job_description`: (if mode=custom) Job description text

**Response:**
```json
{
  "analysis": {
    "resume": {
      "name": "John Doe",
      "email": "john@example.com",
      "skills": ["Python", "Pandas", ...],
      "experience": [...],
      "years_experience": 2.5,
      ...
    },
    "job_profile": {
      "title": "Data Scientist",
      "required_skills": [...],
      "preferred_skills": [...]
    },
    "match": {
      "overall_score": 78.5,
      "components": {
        "skills": 75,
        "semantic": 82,
        "experience": 85,
        "education": 90,
        "keywords": 70
      },
      "skill_match": {
        "matching_skills": ["Python", "Pandas"],
        "missing_required": ["SQL"],
        "missing_skills": ["SQL", "Scikit-learn"]
      }
    },
    "ats": {
      "score": 82,
      "components": {...},
      "recommendations": [...]
    },
    "insights": {
      "strengths": [...],
      "weaknesses": [...],
      "improvements": [...]
    },
    "advisor": {
      "source": "Rule-based guidance",
      "notice": "...",
      "strengths": [...],
      "improvements": [...]
    },
    "interview": {
      "technical_questions": [...],
      "project_questions": [...],
      "hr_questions": [...],
      "scenario_questions": [...]
    }
  }
}
```

### POST `/api/report`
Generates a downloadable HTML report.

**Request (JSON):**
```json
{
  "analysis": {...}  // Complete analysis object from /api/analyze
}
```

**Response:** HTML file download

---

## Testing

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_parser.py -v

# Run with coverage
pytest --cov=modules --cov=genai --cov=utils tests/
```

**Test Coverage:**
- Resume parsing (PDF/DOCX extraction, section detection)
- Skill extraction and catalog matching
- Job description analysis
- Matching algorithms and scoring
- ATS analysis
- GenAI fallback behavior
- Report generation

---

## Configuration

### Environment Variables

**Optional (with sensible defaults):**
- `OPENAI_API_KEY` - OpenAI API key (enables AI advice)
- `LLM_API_KEY` - Alternative LLM API key
- `OPENAI_MODEL` - Model selection (default: gpt-4o-mini)
- `OPENAI_BASE_URL` - API endpoint override
- `ENABLE_EMBEDDINGS` - Enable sentence-transformers (default: false; first run `pip install -r requirements-embeddings.txt` and download the model — see `.env.example`)
- `RATE_LIMIT_PER_MINUTE` - Best-effort per-IP analysis limit (default: 30, `0` disables)
- `LLM_TIMEOUT_SECONDS` - Timeout for optional AI advice calls (default: 20)
- `EMBEDDING_MODEL` - Model name (default: all-MiniLM-L6-v2)
- `SPACY_MODEL` - spaCy model (default: en_core_web_sm)
- `PORT` - Server port (default: 5000, set by deployment platform)
- `FLASK_ENV` - Flask environment (development/production)

### Skills Catalog

Edit `data/skills.json` to add/modify skills:
```json
{
  "version": 1,
  "categories": {
    "Programming": [
      {"name": "Python", "aliases": ["python", "python3"]},
      ...
    ],
    ...
  }
}
```

### Job Roles

Edit `data/job_roles.json` to add/modify predefined roles:
```json
{
  "version": 1,
  "roles": [
    {
      "title": "Data Scientist",
      "required_skills": ["Python", "SQL", "Pandas"],
      "preferred_skills": ["TensorFlow", "AWS"],
      ...
    },
    ...
  ]
}
```

---

## Scoring Formula

```
Overall Score = (
  Skills Match × 0.40 +
  Semantic Similarity × 0.25 +
  Experience Match × 0.15 +
  Education Match × 0.10 +
  Keyword Coverage × 0.10
) × 100
```

Each component is transparent and explained in the results.

---

## Security & Privacy

✅ **No Data Storage**
- Resumes processed in memory only
- No files written to disk
- No contact details logged

✅ **HTML Escaping**
- All user input escaped in reports
- XSS protection enabled

✅ **API Keys**
- Never hardcoded
- Environment variables only
- Not exposed in responses

✅ **Validation**
- File type validation (PDF/DOCX only)
- Size limits enforced
- Input sanitization

---

## File Structure

```
ai-resume-job-matcher/
├── app.py                    # Flask REST API entry point
├── config.py                 # Configuration and constants
├── requirements.txt          # Python dependencies
├── requirements-embeddings.txt # Optional ML extras (ENABLE_EMBEDDINGS)
├── gunicorn.conf.py         # Production WSGI settings
├── Procfile                 # Cloud deployment config
├── Dockerfile               # Container configuration
├── .dockerignore            # Keeps secrets/venv/git out of the image
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore patterns
├── AUDIT.md                 # Technical audit findings
├── IMPLEMENTATION_PLAN.md   # Prioritized roadmap executed for this revision
├── LICENSE                  # MIT license
├── README.md                # This file
│
├── data/
│   ├── skills.json          # Editable skill catalog
│   └── job_roles.json       # Predefined job roles
│
├── modules/                 # Core NLP/ML modules
│   ├── resume_parser.py     # PDF/DOCX parsing
│   ├── skill_extractor.py   # Skill extraction
│   ├── job_analyzer.py      # Job description analysis
│   ├── matcher.py           # Skill/keyword/semantic matching
│   ├── scoring.py           # Score calculation
│   ├── semantic_matcher.py  # TF-IDF/embeddings similarity
│   ├── ats_analyzer.py      # ATS compatibility
│   └── recommendation_engine.py  # Rule-based guidance
│
├── genai/                   # Optional AI features
│   ├── llm_client.py        # OpenAI/LLM integration
│   ├── resume_advisor.py    # AI-enhanced advice
│   └── interview_generator.py  # Interview questions
│
├── utils/                   # Utilities
│   ├── text_cleaner.py      # Text normalization
│   ├── validators.py        # Input validation
│   ├── helpers.py           # Helper functions
│   └── report_builder.py    # HTML report generation
│
├── static/                  # Frontend assets
│   ├── index.html           # Main HTML file
│   ├── css/
│   │   └── style.css        # Styling
│   └── js/
│       └── app.js           # JavaScript logic
│
└── tests/                   # Test suite
    ├── test_parser.py       # Parser tests
    ├── test_skill_extractor.py
    ├── test_matcher.py
    ├── test_scoring.py
    ├── test_job_and_ats.py
    ├── test_genai_and_report.py
    ├── conftest.py          # pytest configuration
    └── fixtures/
        └── sample_resume.txt  # Test data
```

---

## Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make changes**
   - Update code in modules/utils/tests
   - Update data files (skills.json, job_roles.json)

3. **Test locally**
   ```bash
   pytest -v
   python app.py  # Test manually
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "Add: your feature description"
   git push origin feature/your-feature
   ```

5. **Create pull request**
   - Describe changes
   - Reference issues
   - Ensure tests pass

---

## Performance Notes

- **Resume Parsing**: ~500ms per PDF/DOCX (varies by file size)
- **Skill Matching**: ~100ms (catalog-backed, deterministic)
- **Semantic Similarity**: ~200ms (TF-IDF), ~500ms (embeddings)
- **Full Analysis**: ~2-3 seconds (all components)
- **Memory Usage**: ~500MB at startup, grows with model downloads

---

## Known Limitations

⚠️ **Scanned/Image-Only Resumes**
- OCR not yet implemented
- Text extraction fails on PDF images

⚠️ **Non-Standard Formats**
- Assumes conventional section headings
- Heuristic parsing may fail on unusual layouts

⚠️ **Language**
- English only (spaCy model)
- Non-Latin characters handled but not optimized

⚠️ **API Key Optional**
- AI features degrade gracefully without OpenAI key
- Rule-based fallback always available

---

## Troubleshooting

### "spaCy model not found"
```bash
python -m spacy download en_core_web_sm
```

### "PDF extraction failed"
- Ensure PDF is readable (not image-only, not corrupted)
- Try extracting text in Adobe Reader first
- Convert to DOCX as alternative

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### Port already in use
```bash
# Use different port
PORT=8000 python app.py
```

### Docker build fails
```bash
# Clear Docker cache
docker build --no-cache -t ai-resume-matcher .
```

---

## Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] All tests passing (`pytest`)
- [ ] `.env.example` updated with new variables
- [ ] README.md current
- [ ] No hardcoded secrets
- [ ] No debug mode in production
- [ ] Requirements.txt up-to-date
- [ ] Dockerfile tested locally
- [ ] Procfile matches `gunicorn app:app`
- [ ] PORT environment variable configured
- [ ] OPENAI_API_KEY optional (app works without)

---

## License

This project was built as an internship project. See LICENSE file for details.

---

## Support

For issues, questions, or feature requests:
1. Check existing GitHub issues
2. Create a new issue with detailed description
3. Include sample resume if possible (redacted)
4. Describe expected vs actual behavior

---

## Future Enhancements

- [ ] OCR for image-only resumes
- [ ] Multiple resume comparison
- [ ] User-controlled score weights
- [ ] Multilingual support
- [ ] PDF export with styling
- [ ] Real-time collaboration features
- [ ] Resume template suggestions
- [ ] Career pathway recommendations

---

**Last Updated**: August 29, 2026
**Version**: 1.0.0
**Status**: ✅ Production Ready
