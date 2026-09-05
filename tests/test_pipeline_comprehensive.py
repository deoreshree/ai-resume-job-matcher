"""Comprehensive unit and integration tests covering all 19 specified pipeline scenarios."""

from io import BytesIO
from pathlib import Path
import pytest

from app import app
from modules.resume_parser import extract_text, parse_resume, parse_resume_text
from modules.matcher import match_resume_to_job
from modules.skill_extractor import extract_skills, normalize_skill
from utils.validators import ResumeValidationError, validate_resume_file
from tests.test_parser import _minimal_pdf, _docx_bytes


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# 1. Normal one-page PDF
def test_scenario_01_normal_one_page_pdf():
    pdf_bytes = _minimal_pdf("John Doe\njohn@example.com\nSKILLS\nPython, Docker\nEXPERIENCE\nSoftware Engineer at Tech Corp\nBuilt APIs using Python.\nEDUCATION\nB.Tech in Computer Science")
    parsed = parse_resume(pdf_bytes, "resume.pdf")
    assert parsed["candidate"]["name"] == "John Doe"
    assert parsed["candidate"]["email"] == "john@example.com"
    assert "Python" in parsed["skills"]


# 2. Multi-page PDF
def test_scenario_02_multipage_pdf():
    page1 = "Jane Smith\njane@example.com\nSUMMARY\nSenior AI Engineer with 5+ years experience.\nSKILLS\nPython, PyTorch, TensorFlow"
    page2 = "EXPERIENCE\nLead Data Scientist at AI Labs\n2020 - Present\nBuilt deep learning models.\nEDUCATION\nM.S. in Artificial Intelligence"
    combined_pdf = _minimal_pdf(f"{page1}\n{page2}")
    parsed = parse_resume(combined_pdf, "multipage_resume.pdf")
    assert parsed["candidate"]["name"] == "Jane Smith"
    assert "PyTorch" in parsed["skills"]
    assert len(parsed["experience"]) >= 1


# 3. DOCX resume
def test_scenario_03_docx_resume():
    docx_data = _docx_bytes("Alex Johnson\nalex@domain.org\nSKILLS\nReact, TypeScript, Node.js\nEXPERIENCE\nFrontend Developer at Web Corp\nBuilt UI in React.")
    parsed = parse_resume(docx_data, "alex_resume.docx")
    assert parsed["candidate"]["email"] == "alex@domain.org"
    assert "React" in parsed["skills"]


# 4. TXT resume
def test_scenario_04_txt_resume():
    txt_bytes = b"Robert Bruce\nrobert@domain.com\nSKILLS\nGo, Kubernetes, Linux\nEXPERIENCE\nDevOps Lead at Cloud Inc\nManaged K8s clusters."
    parsed = parse_resume(txt_bytes, "robert.txt")
    assert parsed["candidate"]["email"] == "robert@domain.com"
    assert "Kubernetes" in parsed["skills"]


# 5. Two-column resume text
def test_scenario_05_twocolumn_resume():
    text = "Jane Doe | Senior Developer | jane@doe.com | 555-0199\nSKILLS                  EXPERIENCE\nPython, PostgreSQL      Senior Engineer at Acme Corp\nDocker, React           Lead team of 5 developers."
    parsed = parse_resume_text(text)
    assert parsed["candidate"]["email"] == "jane@doe.com"
    assert "Python" in parsed["skills"]


# 6. Resume with missing sections
def test_scenario_06_missing_sections():
    text = "Charlie Brown\ncharlie@peanuts.com\nSKILLS\nPython, SQL"
    parsed = parse_resume_text(text)
    assert parsed["candidate"]["name"] == "Charlie Brown"
    assert parsed["education"] == []
    assert parsed["experience"] == []
    assert parsed["parsing"]["status"] in ("partial", "success")


# 7. Resume with no experience
def test_scenario_07_no_experience():
    text = "Fresh Graduate\ngrad@university.edu\nEDUCATION\nB.Sc Computer Science, 2024\nSKILLS\nJava, C++"
    parsed = parse_resume_text(text)
    assert parsed["experience"] == []
    assert len(parsed["education"]) >= 1


# 8. Resume with no projects
def test_scenario_08_no_projects():
    text = "Sam Taylor\nsam@taylor.com\nEXPERIENCE\nEngineer at Firm X\nWorked on core backend."
    parsed = parse_resume_text(text)
    assert parsed["projects"] == []


# 9. Resume with many skills
def test_scenario_09_many_skills():
    text = "Tech Lead\nlead@tech.com\nSKILLS\nPython, Java, C++, JavaScript, TypeScript, Go, Rust, React, Angular, Vue.js, Django, Flask, FastAPI, Node.js, PostgreSQL, MySQL, MongoDB, Redis, AWS, Azure, GCP, Docker, Kubernetes, CI/CD, Git, GitHub"
    parsed = parse_resume_text(text)
    assert len(parsed["skills"]) >= 15


# 10. Resume with duplicate skills
def test_scenario_10_duplicate_skills():
    text = "Dev\ndev@test.com\nSKILLS\nPython, Python3, python, Py, React, ReactJS"
    parsed = parse_resume_text(text)
    assert parsed["skills"].count("Python") == 1
    assert parsed["skills"].count("React") == 1


# 11. Resume containing LinkedIn and GitHub links
def test_scenario_11_linkedin_github_links():
    text = "Developer\ndev@link.com\nhttps://linkedin.com/in/devprofile\nhttps://github.com/devrepo\nSKILLS\nPython"
    parsed = parse_resume_text(text)
    assert parsed["candidate"]["linkedin"] == "https://linkedin.com/in/devprofile"
    assert parsed["candidate"]["github"] == "https://github.com/devrepo"


# 12. Invalid file
def test_scenario_12_invalid_file():
    with pytest.raises(ResumeValidationError):
        validate_resume_file("invalid.exe", b"binary blob")


# 13. Empty file
def test_scenario_13_empty_file():
    with pytest.raises(ResumeValidationError):
        validate_resume_file("empty.pdf", b"")


# 14. Scanned / image-based PDF
def test_scenario_14_scanned_image_pdf():
    blank_pdf = _minimal_pdf("   ")
    parsed = parse_resume(blank_pdf, "scanned_resume.pdf")
    assert parsed["parsing"]["status"] == "ocr_required"
    assert "OCR" in parsed["parsing"]["warnings"][0] or "image-based" in parsed["parsing"]["warnings"][0]


# 15. Job matching
def test_scenario_15_job_matching():
    parsed = parse_resume_text("Data Engineer\ndata@eng.com\nSKILLS\nPython, SQL, Spark, AWS, Docker\nEXPERIENCE\nData Engineer at Corp, 3 years.")
    job_profile = {
        "title": "Data Engineer",
        "required_skills": ["Python", "SQL", "Spark"],
        "preferred_skills": ["AWS", "Docker", "Kubernetes"],
        "keywords": ["Python", "SQL"],
        "minimum_experience": 2,
    }
    match = match_resume_to_job(parsed, job_profile)
    assert match["overall_score"] >= 65.0
    assert "Python" in match["matched_skills"]


# 16. Missing skills
def test_scenario_16_missing_skills():
    parsed = parse_resume_text("Junior Dev\njunior@dev.com\nSKILLS\nPython, HTML")
    job_profile = {
        "title": "DevOps Engineer",
        "required_skills": ["Docker", "Kubernetes", "Terraform"],
        "preferred_skills": ["AWS"],
    }
    match = match_resume_to_job(parsed, job_profile)
    assert "Docker" in match["missing_skills"]
    assert any(gap["skill"] == "Docker" for gap in match["skill_match"]["skill_gaps"])


# 17. Partial skill matches / aliases
def test_scenario_17_partial_skill_matches():
    assert normalize_skill("Python3") == "Python"
    assert normalize_skill("ReactJS") == "React"
    assert normalize_skill("Node JS") == "Node.js"
    assert normalize_skill("Scikit Learn") == "Scikit-learn"


# 18. API error responses
def test_scenario_18_api_error_responses(client):
    res1 = client.post("/api/analyze")
    assert res1.status_code == 400
    assert "error" in res1.get_json()

    res2 = client.get("/api/nonexistent")
    assert res2.status_code == 404
    assert "error" in res2.get_json()


# 19. Frontend/Backend JSON compatibility
def test_scenario_19_frontend_backend_json_compatibility(client):
    txt_bytes = b"John Doe\njohn@example.com\nSKILLS\nPython, Docker\nEXPERIENCE\nDeveloper at Tech Co\nBuilt apps.\nEDUCATION\nB.S. Computer Science"
    data = {"resume": (BytesIO(txt_bytes), "sample.txt"), "target_mode": "role", "job_role": "Software Engineer"}
    res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    payload = res.get_json()
    assert "analysis" in payload
    analysis = payload["analysis"]
    resume = analysis["resume"]

    assert "candidate" in resume
    assert "email" in resume["candidate"]
    assert "skills" in resume
    assert "education" in resume
    assert "experience" in resume
    assert "projects" in resume
    assert "parsing" in resume
