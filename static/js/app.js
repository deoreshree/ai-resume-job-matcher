/**
 * AI RESUME & JOB MATCHER — PRODUCTION APPLICATION CLIENT (v2.0)
 * Includes AI Career & Company Fit Intelligence
 */

"use strict";

// Application State
const state = {
  currentAnalysis: null,
  activeView: "dashboard",
  rolesCatalog: [],
  selectedFile: null,
  matrixFilter: {
    search: "",
    company: "",
    role: "",
    sort: "fit_desc",
  },
};

// DOM Cache Helper
function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// --------------------------------------------------------------------------
// Initialization & Event Listeners
// --------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initFormControls();
  initDropzone();
  initModal();
  loadRoles();

  // Bind top actions
  byId("sample-btn")?.addEventListener("click", loadSampleResume);
  byId("hero-sample-btn")?.addEventListener("click", loadSampleResume);
  byId("report-button")?.addEventListener("click", downloadReport);
  byId("reset-btn")?.addEventListener("click", resetAnalysis);
  byId("notice-close")?.addEventListener("click", hideNotice);
  byId("mobile-toggle")?.addEventListener("click", toggleMobileSidebar);
  byId("dash-explore-career-btn")?.addEventListener("click", () => switchView("career"));
});

// --------------------------------------------------------------------------
// Navigation & Views
// --------------------------------------------------------------------------
function initNavigation() {
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const view = item.getAttribute("data-view");
      if (view) switchView(view);
    });
  });

  // Handle hash changes
  window.addEventListener("hashchange", () => {
    const hash = window.location.hash.replace("#", "");
    if (hash && document.querySelector(`[data-view="${hash}"]`)) {
      switchView(hash);
    }
  });
}

function switchView(viewId) {
  state.activeView = viewId;

  // Update Nav Items
  document.querySelectorAll(".nav-item").forEach((item) => {
    if (item.getAttribute("data-view") === viewId) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Update View Panels
  document.querySelectorAll(".view-panel").forEach((panel) => {
    if (panel.getAttribute("data-view-content") === viewId) {
      panel.classList.add("active");
    } else {
      panel.classList.remove("active");
    }
  });

  // Update Top Header Title
  const titles = {
    dashboard: "Dashboard Overview",
    career: "AI Career & Company Fit Intelligence",
    resume: "Extracted Resume Profile",
    match: "Job Requirement Alignment",
    gap: "Skill Gap Roadmaps",
    advice: "AI Recommendations & Advisor",
    interview: "Targeted Interview Preparation",
    ats: "ATS Compatibility Scanner",
    about: "About & Privacy Architecture",
  };
  const titleEl = byId("page-title");
  if (titleEl) titleEl.textContent = titles[viewId] || "Dashboard Overview";

  // Auto close mobile sidebar
  byId("app-sidebar")?.classList.remove("open");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function toggleMobileSidebar() {
  byId("app-sidebar")?.classList.toggle("open");
}

// --------------------------------------------------------------------------
// Form Controls & Mode Toggle
// --------------------------------------------------------------------------
function initFormControls() {
  const form = byId("analysis-form");
  const modeRadios = document.querySelectorAll('input[name="target_mode"]');
  const roleControl = byId("role-control");
  const customControl = byId("custom-control");
  const jdTextarea = byId("job-description");
  const charCount = byId("jd-char-count");

  // Mode Toggle
  modeRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      if (radio.value === "custom") {
        roleControl.hidden = true;
        customControl.hidden = false;
        byId("job-role").required = false;
        jdTextarea.required = true;
      } else {
        roleControl.hidden = false;
        customControl.hidden = true;
        byId("job-role").required = true;
        jdTextarea.required = false;
      }
    });
  });

  // Character Counter for JD Textarea
  jdTextarea?.addEventListener("input", () => {
    const len = jdTextarea.value.length;
    charCount.textContent = `${len.toLocaleString()} chars`;
    if (len < 50) {
      charCount.style.color = "var(--color-danger)";
    } else {
      charCount.style.color = "var(--text-subtle)";
    }
  });

  // Form Submit Handler
  form?.addEventListener("submit", (e) => {
    e.preventDefault();
    submitAnalysis();
  });
}

// --------------------------------------------------------------------------
// Dropzone & File Handling
// --------------------------------------------------------------------------
function initDropzone() {
  const dropzone = byId("dropzone");
  const fileInput = byId("resume");
  const fileBadge = byId("file-badge");
  const clearBtn = byId("clear-file-btn");

  if (!dropzone || !fileInput) return;

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
      handleFileSelected(fileInput.files[0]);
    }
  });

  clearBtn?.addEventListener("click", () => {
    state.selectedFile = null;
    fileInput.value = "";
    dropzone.hidden = false;
    fileBadge.hidden = true;
  });
}

function handleFileSelected(file) {
  const ext = file.name.split(".").pop().toLowerCase();
  if (!["pdf", "docx"].includes(ext)) {
    showNotice("Please upload a valid .PDF or .DOCX resume document.", "error");
    return;
  }
  if (file.size > 8 * 1024 * 1024) {
    showNotice("The file size exceeds the 8 MB limit.", "error");
    return;
  }

  state.selectedFile = file;
  updateFileSelection(file);
}

function updateFileSelection(file) {
  const dropzone = byId("dropzone");
  const fileBadge = byId("file-badge");
  const fileNameText = byId("file-name");
  const fileTypeIcon = byId("file-type-icon");

  if (file && dropzone && fileBadge) {
    dropzone.hidden = true;
    fileBadge.hidden = false;
    fileNameText.textContent = file.name;
    const ext = file.name.split(".").pop().toUpperCase();
    fileTypeIcon.textContent = ext;
  }
}

// --------------------------------------------------------------------------
// Predefined Roles Loader
// --------------------------------------------------------------------------
async function loadRoles() {
  const select = byId("job-role");
  if (!select) return;

  try {
    const res = await fetch("/api/roles");
    if (!res.ok) throw new Error("Could not load roles catalog");
    const data = await res.json();
    state.rolesCatalog = data.roles || [];

    select.innerHTML = '<option value="">-- Choose a Target Role --</option>';
    state.rolesCatalog.forEach((role) => {
      const opt = document.createElement("option");
      opt.value = role.title;
      opt.textContent = role.title;
      select.appendChild(opt);
    });

    if (state.rolesCatalog.length > 0) {
      select.selectedIndex = 1; // Default to first role
    }
  } catch (err) {
    select.innerHTML = '<option value="">Error loading roles</option>';
    showNotice("Failed to load predefined job roles catalog.", "warning");
  }
}

// --------------------------------------------------------------------------
// Sample Resume Generator & 1-Click Demo
// --------------------------------------------------------------------------
function createMinimalPdfBlob(text) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const commands = ["BT", "/F1 10 Tf", "50 750 Td"];
  lines.slice(0, 40).forEach((line, index) => {
    const escaped = line.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
    if (index > 0) commands.push("0 -14 Td");
    commands.push(`(${escaped}) Tj`);
  });
  commands.push("ET");
  const stream = commands.join("\n");
  const streamLen = new TextEncoder().encode(stream).length;
  const content = `<< /Length ${streamLen} >>\nstream\n${stream}\nendstream`;
  const pdfString = `%PDF-1.4
1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj
2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj
3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj
4 0 obj{content}endobj
5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj
xref
0 6
0000000000 65535 f 
trailer<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF
`;
  return new Blob([pdfString], { type: "application/pdf" });
}

async function loadSampleResume() {
  const sampleResumeContent = `John Doe
Data Scientist
john.doe@email.com
+1 (415) 555-0199
https://github.com/johndoe
linkedin.com/in/johndoe

SUMMARY
Experienced Data Scientist with 3+ years in machine learning, Python development, statistical modeling, and data analytics pipelines.

EDUCATION
B.Tech in Computer Science
State Institute of Technology
2018 - 2022

EXPERIENCE
Machine Learning Engineer at Acme Analytics
Jan 2022 - Present
- Built classification and regression models using Python, Pandas, NumPy, and scikit-learn
- Collaborated with cross-functional product teams on production scoring pipelines
- Automated ETL scripts in SQL and PostgreSQL to process customer behavioral metrics

Data Science Intern at Insight Labs
Jun 2021 - Dec 2021
- Analyzed survey data and created interactive dashboards using Tableau and Python
- Designed predictive churn indicators that improved user retention tracking

PROJECTS
Customer Churn Prediction Engine
- Trained a scikit-learn classification model to forecast customer churn with 88% precision
- Technologies: Python, Scikit-learn, Pandas, FastAPI, Docker

SKILLS
Python, Machine Learning, Pandas, NumPy, Scikit-learn, SQL, Statistics, Data Visualization, Git, Docker, Communication

CERTIFICATIONS
AWS Certified Cloud Practitioner

ACHIEVEMENTS
Dean's List for Academic Excellence (2020, 2021)
`;

  const blob = createMinimalPdfBlob(sampleResumeContent);
  const file = new File([blob], "sample_data_scientist_resume.pdf", {
    type: "application/pdf",
  });

  // Ensure mode is set to role and role is Data Scientist
  document.querySelector('input[name="target_mode"][value="role"]').checked = true;
  byId("role-control").hidden = false;
  byId("custom-control").hidden = true;

  const select = byId("job-role");
  select.value = "Data Scientist";

  updateFileSelection(file);
  state.selectedFile = file;
  submitAnalysis();
}

// --------------------------------------------------------------------------
// Submit Analysis Pipeline
// --------------------------------------------------------------------------
async function submitAnalysis() {
  const file = state.selectedFile || byId("resume")?.files?.[0];
  if (!file) {
    showNotice("Please upload your PDF or DOCX resume document.", "warning");
    return;
  }

  const mode = document.querySelector('input[name="target_mode"]:checked')?.value || "role";
  const formData = new FormData();
  formData.append("resume", file);
  formData.append("target_mode", mode);

  if (mode === "custom") {
    const jd = byId("job-description")?.value?.trim() || "";
    if (jd.length < 30) {
      showNotice("Please paste a meaningful job description (minimum 30 characters).", "warning");
      return;
    }
    formData.append("job_description", jd);
  } else {
    const role = byId("job-role")?.value || "";
    if (!role) {
      showNotice("Please select a target job role from the dropdown.", "warning");
      return;
    }
    formData.append("job_role", role);
  }

  // Display Loading UI
  setLoadingState(true);
  hideNotice();

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Analysis failed. Please try again.");
    }

    state.currentAnalysis = data.analysis;
    renderAllViews(data.analysis);
    showNotice("Resume analysis & AI Career Intelligence generated successfully!", "success");

    // Enable Report Export Button
    const reportBtn = byId("report-button");
    if (reportBtn) reportBtn.disabled = false;

    // Switch to Dashboard view
    switchView("dashboard");
  } catch (err) {
    showNotice(err.message || "An unexpected error occurred during analysis.", "error");
  } finally {
    setLoadingState(false);
  }
}

// --------------------------------------------------------------------------
// Multi-Step Loading Simulator
// --------------------------------------------------------------------------
function setLoadingState(isLoading) {
  const emptyState = byId("empty-state");
  const loadingState = byId("loading-state");
  const resultContent = byId("result-content");
  const submitBtn = byId("analyse-button");
  const activeActions = byId("active-actions");

  if (isLoading) {
    emptyState.hidden = true;
    loadingState.hidden = false;
    resultContent.hidden = true;
    submitBtn.disabled = true;
    submitBtn.querySelector(".btn-text").textContent = "Analyzing Profile...";
    simulateProgress();
  } else {
    loadingState.hidden = true;
    submitBtn.disabled = false;
    submitBtn.querySelector(".btn-text").textContent = "Run Match Analysis";
    if (state.currentAnalysis) {
      emptyState.hidden = true;
      resultContent.hidden = false;
      activeActions.hidden = false;
    } else {
      emptyState.hidden = false;
      resultContent.hidden = true;
      activeActions.hidden = true;
    }
  }
}

function simulateProgress() {
  const steps = [1, 2, 3, 4];
  steps.forEach((step, idx) => {
    setTimeout(() => {
      const el = byId(`prog-step-${step}`);
      if (el) {
        el.classList.add("active");
        if (idx > 0) {
          const prev = byId(`prog-step-${steps[idx - 1]}`);
          prev?.classList.remove("active");
          prev?.classList.add("completed");
        }
      }
    }, idx * 400);
  });
}

function resetAnalysis() {
  state.currentAnalysis = null;
  state.selectedFile = null;
  byId("analysis-form")?.reset();
  byId("dropzone").hidden = false;
  byId("file-badge").hidden = true;
  byId("empty-state").hidden = false;
  byId("result-content").hidden = true;
  byId("active-actions").hidden = true;
  byId("report-button").disabled = true;
  byId("dash-score-badge").hidden = true;
  hideNotice();
  switchView("dashboard");
}

// --------------------------------------------------------------------------
// MASTER VIEW RENDERER
// --------------------------------------------------------------------------
function renderAllViews(analysis) {
  renderDashboard(analysis);
  renderCareerIntelligence(analysis.career_intelligence, analysis);
  renderResumeAnalysis(analysis.resume);
  renderJobMatch(analysis.match, analysis.job_profile);
  renderSkillGapRoadmap(analysis.match, analysis.insights);
  renderAiAdvisor(analysis.insights, analysis.advisor);
  renderInterviewPrep(analysis.interview);
  renderAtsScan(analysis.ats);
}

// --------------------------------------------------------------------------
// VIEW 1: DASHBOARD
// --------------------------------------------------------------------------
function renderDashboard(analysis) {
  const match = analysis.match || {};
  const ats = analysis.ats || {};
  const resume = analysis.resume || {};
  const career = analysis.career_intelligence || {};
  const overall = Number(match.overall_score || 0).toFixed(1);

  // Update Nav Score Badge
  const badge = byId("dash-score-badge");
  if (badge) {
    badge.textContent = `${Math.round(overall)}%`;
    badge.hidden = false;
  }

  // 1. Render 6 Metric KPI Tiles
  const metricsGrid = byId("metrics-grid");
  if (metricsGrid) {
    metricsGrid.innerHTML = `
      <div class="metric-tile">
        <span class="tile-label">Overall Match Fit</span>
        <strong class="tile-value">${overall}%</strong>
        <span class="tile-sub">Weighted 5-Factor Score</span>
      </div>
      <div class="metric-tile">
        <span class="tile-label">ATS Compatibility</span>
        <strong class="tile-value">${Number(ats.score || 0).toFixed(0)}/100</strong>
        <span class="tile-sub">Structure &amp; Readability</span>
      </div>
      <div class="metric-tile">
        <span class="tile-label">Skills Verified</span>
        <strong class="tile-value">${resume.skills?.length || 0}</strong>
        <span class="tile-sub">Catalog Entities Found</span>
      </div>
      <div class="metric-tile">
        <span class="tile-label">Experience Track</span>
        <strong class="tile-value">${Number(resume.years_experience || 0).toFixed(1)} yrs</strong>
        <span class="tile-sub">Documented Work History</span>
      </div>
      <div class="metric-tile">
        <span class="tile-label">Estimated Level</span>
        <strong class="tile-value compact">${escapeHtml(career.career_level?.level_category || "General")}</strong>
        <span class="tile-sub">${career.career_level?.confidence_score || 80}% Confidence</span>
      </div>
      <div class="metric-tile">
        <span class="tile-label">Top Company Fit</span>
        <strong class="tile-value">${career.company_matches?.top_company?.fit_score || 85}%</strong>
        <span class="tile-sub">${escapeHtml(career.company_matches?.top_company?.name || "Tier-1 Tech")}</span>
      </div>
    `;
  }

  // 2. Render Career Highlight Banner on Dashboard
  if (career.top_role && career.company_matches?.top_company) {
    const topRole = career.top_role;
    const topComp = career.company_matches.top_company;
    byId("dash-career-role").textContent = `Best Role Fit: ${topRole.title} (${topRole.overall_score}%)`;
    byId("dash-career-fit").textContent = `${topComp.fit_score}%`;
    byId("dash-career-company").textContent = topComp.name;

    const pills = byId("dash-career-pills");
    if (pills) {
      pills.innerHTML = `
        <span class="mini-pill">🎯 Top Role: ${escapeHtml(topRole.title)}</span>
        <span class="mini-pill">🏢 Strongest Fit: ${escapeHtml(topComp.name)}</span>
        <span class="mini-pill">📈 Level: ${escapeHtml(career.career_level?.level_title || "Practitioner")}</span>
      `;
    }
  }

  // 3. Render 5-Component Score Breakdown
  const compList = byId("score-breakdown");
  if (compList) {
    const components = match.components || {};
    const labels = {
      skills: "Skills Match (40%)",
      semantic: "Semantic Similarity (25%)",
      experience: "Experience Match (15%)",
      education: "Education Match (10%)",
      keywords: "Keyword Coverage (10%)",
    };
    compList.innerHTML = Object.entries(labels)
      .map(([key, label]) => {
        const score = Number(components[key] || 0).toFixed(1);
        return `
          <div class="score-row-item">
            <span class="score-name">${label}</span>
            <div class="score-track">
              <div class="score-fill" style="width: ${Math.min(100, Math.max(0, score))}%"></div>
            </div>
            <span class="score-percent">${score}%</span>
            <span class="score-weight-tag">${key === "skills" ? "0.40" : key === "semantic" ? "0.25" : key === "experience" ? "0.15" : "0.10"}</span>
          </div>
        `;
      })
      .join("");
  }

  // 4. Render Core Skill Coverage Donut
  const skillMatch = match.skill_match || {};
  const matching = skillMatch.matching_skills || [];
  const missingReq = skillMatch.missing_required || [];
  const totalReq = matching.length + missingReq.length;
  const coveragePercent = totalReq > 0 ? Math.round((matching.length / totalReq) * 100) : 100;

  const donut = byId("skill-donut");
  const donutText = byId("donut-percent");
  if (donut && donutText) {
    donutText.textContent = `${coveragePercent}%`;
    donut.style.background = `conic-gradient(var(--brand-teal) ${coveragePercent}%, #e2e8f0 ${coveragePercent}% 100%)`;
  }

  const skillCounts = byId("skill-counts");
  if (skillCounts) {
    skillCounts.innerHTML = `
      <span><b>${matching.length}</b> Matched</span>
      <span><b>${missingReq.length}</b> Missing Required</span>
    `;
  }

  // 5. Render Matching & Missing Chips Summary
  const matchedContainer = byId("dashboard-matching-skills");
  const missingContainer = byId("dashboard-missing-skills");

  if (matchedContainer) {
    byId("matched-skills-count").textContent = `${matching.length} verified`;
    matchedContainer.innerHTML = matching.length
      ? matching.map((s) => `<span class="skill-chip matched">✓ ${escapeHtml(s)}</span>`).join("")
      : '<span class="text-muted">No catalog skills detected in target role requirements.</span>';
  }

  if (missingContainer) {
    const allGaps = skillMatch.missing_skills || [];
    byId("missing-skills-count").textContent = `${allGaps.length} gaps`;
    missingContainer.innerHTML = allGaps.length
      ? allGaps.map((s) => `<span class="skill-chip gap">⚠ ${escapeHtml(s)}</span>`).join("")
      : '<span class="badge-success">✓ 100% Skill coverage for target role!</span>';
  }
}

// --------------------------------------------------------------------------
// VIEW: AI CAREER & COMPANY FIT INTELLIGENCE (NEW FEATURE)
// --------------------------------------------------------------------------
function renderCareerIntelligence(career, analysis) {
  const container = byId("career-content");
  if (!container || !career) return;

  const level = career.career_level || {};
  const topRoles = career.role_recommendations || [];
  const companies = career.company_matches || {};
  const matrix = career.company_role_matrix || [];
  const opportunities = career.skill_opportunity_map || [];
  const roadmap = career.career_roadmap || {};
  const strategy = career.job_search_strategy || {};

  container.innerHTML = `
    <!-- 1. Career Level & Synthesized Summary Card -->
    <div class="level-meter-card">
      <div class="level-meta-box">
        <span class="level-badge-large">📈 Estimated Career Standing</span>
        <h3 class="level-title-text">${escapeHtml(level.level_title || "Technical Practitioner")}</h3>
        <p class="level-summary-text">${escapeHtml(career.career_summary || "")}</p>
        
        <div class="level-evidence-list">
          ${(level.evidence || [])
            .map(
              (ev) => `
            <div class="evidence-bullet">
              <span>✓</span>
              <span>${escapeHtml(ev)}</span>
            </div>
          `
            )
            .join("")}
        </div>
      </div>

      <div class="level-gauge-box">
        <div class="gauge-circle">
          <strong>${level.confidence_score || 85}%</strong>
          <span>Confidence</span>
        </div>
        <span class="text-muted" style="font-size:12px; font-weight:600;">Based on ${Number(level.years_experience || 0).toFixed(1)} yrs documented work history</span>
      </div>
    </div>

    <!-- 2. 🎯 Best Roles For You (Role Recommendation Engine) -->
    <div class="dashboard-panel">
      <div class="panel-header">
        <div>
          <span class="eyebrow">ROLE RECOMMENDATION ENGINE</span>
          <h3 class="panel-title">🎯 Best Job Roles For Your Profile</h3>
        </div>
        <span class="badge-neutral">Ranked by 5-Factor Alignment</span>
      </div>

      <div class="roles-ranked-grid">
        ${topRoles
          .slice(0, 6)
          .map(
            (role) => `
          <div class="role-rank-card">
            <div>
              <span class="rank-badge">#${role.rank} RANKED</span>
              <h4 class="role-card-title">${escapeHtml(role.title)}</h4>
              <div class="role-fit-bar-container">
                <div class="role-fit-track">
                  <div class="role-fit-fill" style="width: ${role.overall_score}%"></div>
                </div>
                <span class="role-fit-percent">${role.overall_score}%</span>
              </div>
              <div class="role-why-box">
                ${(role.why_fit || []).slice(0, 2).map((w) => `• ${escapeHtml(w)}`).join("<br>")}
              </div>
            </div>
            <div class="chips-container" style="margin-top: 8px;">
              ${(role.matching_skills || [])
                .slice(0, 3)
                .map((s) => `<span class="skill-chip matched" style="font-size:11px; padding:3px 7px;">✓ ${escapeHtml(s)}</span>`)
                .join("")}
            </div>
          </div>
        `
          )
          .join("")}
      </div>
    </div>

    <!-- 3. 🏢 Companies That Match Your Profile -->
    <div class="dashboard-panel">
      <div class="panel-header">
        <div>
          <span class="eyebrow">COMPANY FIT ESTIMATION</span>
          <h3 class="panel-title">🏢 Companies That Match Your Profile</h3>
        </div>
        <span class="badge-neutral">${companies.all_matches?.length || 0} Companies Benchmarked</span>
      </div>

      <div class="company-tier-grid">
        ${(companies.all_matches || [])
          .slice(0, 9)
          .map(
            (comp) => `
          <div class="company-card-item">
            <div>
              <div class="company-top">
                <div>
                  <h4 class="company-name-text">${escapeHtml(comp.name)}</h4>
                  <span class="company-industry-text">${escapeHtml(comp.industry)}</span>
                </div>
                <span class="tier-badge-pill ${comp.tier_code}">${comp.tier_badge}</span>
              </div>

              <div class="company-fit-score-box" style="margin: 12px 0;">
                <span class="comp-fit-num">${comp.fit_score}%</span>
                <span class="comp-fit-label">Estimated Compatibility Fit</span>
              </div>

              <div class="company-roles-list">
                <strong>Suitable Target Roles</strong>
                <span>${(comp.suitable_roles || []).map((r) => `${escapeHtml(r.title)} (${r.score}%)`).join(", ") || "Software Engineer"}</span>
              </div>

              <div class="company-why-box" style="margin-top:10px; font-size:12px; color:var(--text-muted);">
                ${(comp.why_matched || []).map((w) => `✓ ${escapeHtml(w)}`).join("<br>")}
              </div>

              ${
                comp.skill_gaps?.length
                  ? `
                <div class="company-gaps-box" style="margin-top:10px;">
                  <strong style="font-size:11px; text-transform:uppercase; display:block;">Key Skill Gaps:</strong>
                  <span>${comp.skill_gaps.map((g) => escapeHtml(g)).join(", ")}</span>
                </div>
              `
                  : ""
              }
            </div>

            <button class="btn-practice-company" type="button" onclick="loadCompanyInterviewPractice('${escapeHtml(comp.name)}', '${escapeHtml(comp.suitable_roles?.[0]?.title || "Software Engineer")}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
              <span>Practice ${escapeHtml(comp.name)} Questions</span>
            </button>
          </div>
        `
          )
          .join("")}
      </div>
    </div>

    <!-- 4. 📊 Interactive Company + Role Matrix -->
    <div class="matrix-container-card">
      <div class="panel-header">
        <div>
          <span class="eyebrow">INTERACTIVE MATRIX</span>
          <h3 class="panel-title">📊 Company &amp; Role Fit Matrix</h3>
        </div>
      </div>

      <div class="matrix-controls-bar">
        <input type="text" id="matrix-search" class="matrix-search-input" placeholder="Search company or role (e.g. Microsoft, ML Engineer)..." value="${escapeHtml(state.matrixFilter.search)}">
        <select id="matrix-company-filter" class="matrix-filter-select">
          <option value="">All Companies</option>
          ${Array.from(new Set(matrix.map((m) => m.company)))
            .map((c) => `<option value="${escapeHtml(c)}" ${state.matrixFilter.company === c ? "selected" : ""}>${escapeHtml(c)}</option>`)
            .join("")}
        </select>
        <select id="matrix-role-filter" class="matrix-filter-select">
          <option value="">All Roles</option>
          ${Array.from(new Set(matrix.map((m) => m.role)))
            .map((r) => `<option value="${escapeHtml(r)}" ${state.matrixFilter.role === r ? "selected" : ""}>${escapeHtml(r)}</option>`)
            .join("")}
        </select>
        <select id="matrix-sort" class="matrix-filter-select">
          <option value="fit_desc">Highest Fit First</option>
          <option value="fit_asc">Lowest Fit First</option>
          <option value="company_asc">Company A-Z</option>
        </select>
      </div>

      <div style="overflow-x:auto;">
        <table class="matrix-data-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Target Role</th>
              <th>Industry</th>
              <th>Fit Score</th>
              <th>Why Match</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody id="matrix-tbody">
            <!-- Dynamic Matrix Rows Rendered via renderMatrixTable() -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- 5. 🚀 What Should You Learn Next? (Skill Gap → Opportunity) -->
    <div class="dashboard-panel">
      <div class="panel-header">
        <div>
          <span class="eyebrow">OPPORTUNITY ACCELERATOR</span>
          <h3 class="panel-title">🚀 What Should You Learn Next?</h3>
        </div>
        <span class="badge-neutral">High-Leverage Skill Upgrades</span>
      </div>

      <div class="opportunities-grid">
        ${opportunities
          .map(
            (opp) => `
          <div class="opportunity-card">
            <div>
              <div class="opp-top">
                <span class="opp-priority-tag ${opp.priority_class}">${opp.priority_label}</span>
                <span class="badge-neutral" style="font-size:10px;">High Impact</span>
              </div>
              <h4 class="opp-skill-title">${escapeHtml(opp.skill)}</h4>
              <p class="text-muted" style="font-size:12px; margin: 6px 0 12px;">${escapeHtml(opp.learning_path)}</p>
              
              <div class="opp-impact-box">
                <strong>🎯 Unlocks Roles:</strong>
                <span>${opp.unlocked_roles.map((r) => escapeHtml(r)).join(", ")}</span>
                <strong style="margin-top:6px; display:block;">🏢 Boosts Company Fit:</strong>
                <span>${opp.boosted_companies.map((c) => escapeHtml(c)).join(", ")}</span>
              </div>
            </div>
            <p style="font-size:11px; color:var(--text-muted); line-height:1.4;">${escapeHtml(opp.impact_summary)}</p>
          </div>
        `
          )
          .join("")}
      </div>
    </div>

    <!-- 6. 🗺️ Your AI Career Roadmap (4-Phase Timeline) -->
    <div class="dashboard-panel">
      <div class="panel-header">
        <div>
          <span class="eyebrow">CHRONOLOGICAL ROADMAP</span>
          <h3 class="panel-title">🗺️ Your AI Career Roadmap (90-Day Plan)</h3>
        </div>
      </div>

      <div class="roadmap-timeline-grid">
        <div class="roadmap-phase-card">
          <span class="phase-step-badge">Phase 1 &bull; ${escapeHtml(roadmap.phase_1_now?.timeframe || "Days 1–7")}</span>
          <h4 class="phase-heading">${escapeHtml(roadmap.phase_1_now?.title || "NOW")}</h4>
          <ul class="phase-goals-list">
            ${(roadmap.phase_1_now?.goals || []).map((g) => `<li>${escapeHtml(g)}</li>`).join("")}
          </ul>
        </div>

        <div class="roadmap-phase-card">
          <span class="phase-step-badge">Phase 2 &bull; ${escapeHtml(roadmap.phase_2_30_days?.timeframe || "Days 8–30")}</span>
          <h4 class="phase-heading">${escapeHtml(roadmap.phase_2_30_days?.title || "30 DAYS")}</h4>
          <ul class="phase-goals-list">
            ${(roadmap.phase_2_30_days?.goals || []).map((g) => `<li>${escapeHtml(g)}</li>`).join("")}
          </ul>
        </div>

        <div class="roadmap-phase-card">
          <span class="phase-step-badge">Phase 3 &bull; ${escapeHtml(roadmap.phase_3_60_days?.timeframe || "Days 31–60")}</span>
          <h4 class="phase-heading">${escapeHtml(roadmap.phase_3_60_days?.title || "60 DAYS")}</h4>
          <ul class="phase-goals-list">
            ${(roadmap.phase_3_60_days?.goals || []).map((g) => `<li>${escapeHtml(g)}</li>`).join("")}
          </ul>
        </div>

        <div class="roadmap-phase-card">
          <span class="phase-step-badge">Phase 4 &bull; ${escapeHtml(roadmap.phase_4_90_days?.timeframe || "Days 61–90")}</span>
          <h4 class="phase-heading">${escapeHtml(roadmap.phase_4_90_days?.title || "90 DAYS")}</h4>
          <ul class="phase-goals-list">
            ${(roadmap.phase_4_90_days?.goals || []).map((g) => `<li>${escapeHtml(g)}</li>`).join("")}
          </ul>
        </div>
      </div>
    </div>

    <!-- 7. 💼 Recommended Job Search Strategy -->
    <div class="dashboard-panel">
      <div class="panel-header">
        <div>
          <span class="eyebrow">TARGETING STRATEGY</span>
          <h3 class="panel-title">💼 Recommended Job Search Strategy</h3>
        </div>
      </div>

      <div class="strategy-columns-grid">
        <!-- Column 1: Apply Now -->
        <div class="strategy-column-card">
          <div class="strategy-col-header">
            <span style="color:var(--color-success); font-size:18px;">🟢</span>
            <h4 class="strategy-col-title">Apply Now (Fit &ge; 75%)</h4>
          </div>
          <div class="strategy-roles-list">
            ${
              (strategy.apply_now || []).length
                ? strategy.apply_now
                    .map(
                      (item) => `
                  <div class="strategy-role-item">
                    <div class="strat-role-top">
                      <span class="strat-role-title">${escapeHtml(item.title)}</span>
                      <span class="strat-role-score">${item.score}%</span>
                    </div>
                    <span class="strat-role-sub">${item.matching_count} verified skills &bull; Ready to apply</span>
                  </div>
                `
                    )
                    .join("")
                : '<p class="text-muted" style="font-size:12px;">Prioritize building 1-2 core skills to unlock High Fit roles.</p>'
            }
          </div>
        </div>

        <!-- Column 2: Improve First -->
        <div class="strategy-column-card">
          <div class="strategy-col-header">
            <span style="color:var(--color-warning); font-size:18px;">🟡</span>
            <h4 class="strategy-col-title">Improve First (Fit 55%–74%)</h4>
          </div>
          <div class="strategy-roles-list">
            ${
              (strategy.improve_first || []).length
                ? strategy.improve_first
                    .map(
                      (item) => `
                  <div class="strategy-role-item">
                    <div class="strat-role-top">
                      <span class="strat-role-title">${escapeHtml(item.title)}</span>
                      <span class="strat-role-score">${item.score}%</span>
                    </div>
                    <span class="strat-role-sub">Missing: ${(item.top_gaps || []).map((g) => escapeHtml(g)).join(", ") || "Specialized Tools"}</span>
                  </div>
                `
                    )
                    .join("")
                : '<p class="text-muted" style="font-size:12px;">No roles in intermediate bracket.</p>'
            }
          </div>
        </div>

        <!-- Column 3: Long-Term Target -->
        <div class="strategy-column-card">
          <div class="strategy-col-header">
            <span style="color:var(--brand-cyan); font-size:18px;">🔵</span>
            <h4 class="strategy-col-title">Long-Term Target (&lt; 55%)</h4>
          </div>
          <div class="strategy-roles-list">
            ${
              (strategy.long_term_target || []).length
                ? strategy.long_term_target
                    .slice(0, 4)
                    .map(
                      (item) => `
                  <div class="strategy-role-item">
                    <div class="strat-role-top">
                      <span class="strat-role-title">${escapeHtml(item.title)}</span>
                      <span class="strat-role-score">${item.score}%</span>
                    </div>
                    <span class="strat-role-sub">${item.gap_count} gaps &bull; Requires foundational prep</span>
                  </div>
                `
                    )
                    .join("")
                : '<p class="text-muted" style="font-size:12px;">All catalog roles meet intermediate readiness threshold.</p>'
            }
          </div>
        </div>
      </div>
    </div>

    <!-- 8. 🏢 Company Practice Interview Pack -->
    <div class="dashboard-panel" id="company-interview-section">
      <div class="panel-header">
        <div>
          <span class="eyebrow">COMPANY INTERVIEW PREPARATION</span>
          <h3 class="panel-title">🏢 Company-Specific Practice Questions</h3>
        </div>
        <span class="badge-neutral">AI-Generated Practice Questions</span>
      </div>

      <div id="company-interview-questions-list" class="content-stack">
        ${(career.company_interview_pack || [])
          .map(
            (q, idx) => `
          <div class="question-accordion" style="background:#ffffff;">
            <div style="padding:16px 18px; display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
              <div>
                <span class="badge-neutral" style="font-size:10px; margin-bottom:4px; display:inline-block;">${escapeHtml(q.category)}</span>
                <strong style="display:block; font-size:14px; color:var(--brand-navy); margin-top:2px;">${escapeHtml(q.question)}</strong>
              </div>
              <button class="btn-copy" type="button" onclick="copyText('${escapeHtml(q.question).replace(/'/g, "\\'")}', this)">Copy</button>
            </div>
            <div style="padding:12px 18px 16px; background:var(--bg-canvas); border-top:1px solid var(--border-light); font-size:13px;">
              <p style="color:var(--text-muted); margin-bottom:8px;"><strong>Why asked:</strong> ${escapeHtml(q.why_asked)}</p>
              <div class="answer-guide-box">
                <strong>Standout Answer Strategy:</strong>
                <span>${escapeHtml(q.strong_answer)}</span>
              </div>
            </div>
          </div>
        `
          )
          .join("")}
      </div>
    </div>
  `;

  // Initialize Matrix Interactive Events
  initMatrixInteractivity(matrix);
}

// --------------------------------------------------------------------------
// Interactive Matrix Table Logic
// --------------------------------------------------------------------------
function initMatrixInteractivity(matrix) {
  const searchInput = byId("matrix-search");
  const companySelect = byId("matrix-company-filter");
  const roleSelect = byId("matrix-role-filter");
  const sortSelect = byId("matrix-sort");

  const filterAndRender = () => {
    state.matrixFilter.search = searchInput?.value?.toLowerCase() || "";
    state.matrixFilter.company = companySelect?.value || "";
    state.matrixFilter.role = roleSelect?.value || "";
    state.matrixFilter.sort = sortSelect?.value || "fit_desc";

    let filtered = matrix.filter((item) => {
      const matchSearch =
        !state.matrixFilter.search ||
        item.company.toLowerCase().includes(state.matrixFilter.search) ||
        item.role.toLowerCase().includes(state.matrixFilter.search) ||
        item.industry.toLowerCase().includes(state.matrixFilter.search);

      const matchCompany = !state.matrixFilter.company || item.company === state.matrixFilter.company;
      const matchRole = !state.matrixFilter.role || item.role === state.matrixFilter.role;

      return matchSearch && matchCompany && matchRole;
    });

    // Sorting
    if (state.matrixFilter.sort === "fit_desc") {
      filtered.sort((a, b) => b.fit_score - a.fit_score);
    } else if (state.matrixFilter.sort === "fit_asc") {
      filtered.sort((a, b) => a.fit_score - b.fit_score);
    } else if (state.matrixFilter.sort === "company_asc") {
      filtered.sort((a, b) => a.company.localeCompare(b.company));
    }

    renderMatrixTable(filtered);
  };

  searchInput?.addEventListener("input", filterAndRender);
  companySelect?.addEventListener("change", filterAndRender);
  roleSelect?.addEventListener("change", filterAndRender);
  sortSelect?.addEventListener("change", filterAndRender);

  // Initial render of matrix rows
  filterAndRender();
}

function renderMatrixTable(rows) {
  const tbody = byId("matrix-tbody");
  if (!tbody) return;

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:24px; color:var(--text-muted);">No matching company + role combinations found.</td></tr>`;
    return;
  }

  tbody.innerHTML = rows
    .slice(0, 20)
    .map(
      (row, idx) => `
    <tr>
      <td><strong>${escapeHtml(row.company)}</strong></td>
      <td>${escapeHtml(row.role)}</td>
      <td style="color:var(--text-muted); font-size:12px;">${escapeHtml(row.industry)}</td>
      <td>
        <strong style="color:var(--brand-teal); font-family:'JetBrains Mono', monospace;">${row.fit_score}%</strong>
      </td>
      <td style="font-size:12px; color:var(--text-muted); max-width:240px;">
        ${(row.why || []).slice(0, 1).map((w) => escapeHtml(w)).join("") || "Complementary tech background"}
      </td>
      <td>
        <button class="btn-why-match" type="button" onclick="openWhyMatchModal(${idx})">
          Why this match?
        </button>
      </td>
    </tr>
  `
    )
    .join("");

  // Attach matrix row cache for modal
  window._currentMatrixRows = rows;
}

// --------------------------------------------------------------------------
// "Why This Match?" Explainability Modal
// --------------------------------------------------------------------------
function initModal() {
  const modal = byId("match-modal");
  const backdrop = byId("modal-backdrop");
  const closeBtn = byId("modal-close-btn");

  const closeModal = () => {
    if (modal) modal.hidden = true;
  };

  backdrop?.addEventListener("click", closeModal);
  closeBtn?.addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal && !modal.hidden) closeModal();
  });
}

window.openWhyMatchModal = function (rowIndex) {
  const modal = byId("match-modal");
  const body = byId("modal-body");
  const title = byId("modal-title");
  const row = window._currentMatrixRows?.[rowIndex];

  if (!modal || !body || !row) return;

  title.textContent = `${row.company} — ${row.role} (${row.fit_score}% Fit)`;

  body.innerHTML = `
    <div style="background:var(--bg-canvas); border-radius:var(--radius-md); padding:14px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span class="eyebrow">ESTIMATED FIT SCORE</span>
        <strong style="font-size:22px; color:var(--brand-teal); font-family:'JetBrains Mono', monospace;">${row.fit_score}%</strong>
      </div>
      <p style="font-size:12px; color:var(--text-muted); line-height:1.45;">
        Estimated compatibility score blending company technical stack coverage (35%), keyword density (20%), target role alignment (25%), and experience/education evidence (20%).
      </p>
    </div>

    <div>
      <h4 style="font-size:14px; font-weight:700; margin-bottom:8px; color:var(--color-success);">✓ Matching Candidate Evidence</h4>
      <div class="chips-container">
        ${(row.matching_skills || [])
          .map((s) => `<span class="skill-chip matched">✓ ${escapeHtml(s)}</span>`)
          .join("") || '<span class="text-muted" style="font-size:12px;">Fundamental analytical & problem solving skills.</span>'}
      </div>
    </div>

    <div>
      <h4 style="font-size:14px; font-weight:700; margin-bottom:8px; color:var(--color-warning);">⚠️ Missing Recommended Skills</h4>
      <div class="chips-container">
        ${(row.missing_skills || [])
          .map((s) => `<span class="skill-chip gap">⚠ ${escapeHtml(s)}</span>`)
          .join("") || '<span class="badge-success">✓ No significant skill gaps identified!</span>'}
      </div>
    </div>

    <div>
      <h4 style="font-size:14px; font-weight:700; margin-bottom:8px; color:var(--brand-navy);">🔍 Alignment Highlights</h4>
      <ul style="padding-left:18px; font-size:13px; color:#334155; line-height:1.5;">
        ${(row.why || []).map((w) => `<li>${escapeHtml(w)}</li>`).join("")}
        <li>Tier Profile: ${escapeHtml(row.tier || "Enterprise Tech")} &bull; ${escapeHtml(row.industry || "Technology")}</li>
      </ul>
    </div>
  `;

  modal.hidden = false;
};

// --------------------------------------------------------------------------
// Company Practice Interview Loader
// --------------------------------------------------------------------------
window.loadCompanyInterviewPractice = async function (companyName, roleTitle) {
  const list = byId("company-interview-questions-list");
  if (!list) return;

  list.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">Generating practice questions for ${escapeHtml(companyName)}...</div>`;
  
  // Scroll to section smoothly
  byId("company-interview-section")?.scrollIntoView({ behavior: "smooth" });

  try {
    const res = await fetch("/api/company-interview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company: companyName,
        role: roleTitle,
        resume: state.currentAnalysis?.resume || {},
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load questions");

    const questions = data.questions || [];
    list.innerHTML = questions
      .map(
        (q) => `
      <div class="question-accordion" style="background:#ffffff;">
        <div style="padding:16px 18px; display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
          <div>
            <span class="badge-neutral" style="font-size:10px; margin-bottom:4px; display:inline-block;">${escapeHtml(q.category)}</span>
            <strong style="display:block; font-size:14px; color:var(--brand-navy); margin-top:2px;">${escapeHtml(q.question)}</strong>
          </div>
          <button class="btn-copy" type="button" onclick="copyText('${escapeHtml(q.question).replace(/'/g, "\\'")}', this)">Copy</button>
        </div>
        <div style="padding:12px 18px 16px; background:var(--bg-canvas); border-top:1px solid var(--border-light); font-size:13px;">
          <p style="color:var(--text-muted); margin-bottom:8px;"><strong>Why ${escapeHtml(companyName)} asks this:</strong> ${escapeHtml(q.why_asked)}</p>
          <div class="answer-guide-box">
            <strong>Standout Answer Strategy:</strong>
            <span>${escapeHtml(q.strong_answer)}</span>
          </div>
        </div>
      </div>
    `
      )
      .join("");
  } catch (err) {
    list.innerHTML = `<div style="color:var(--color-danger); padding:14px;">Error: ${escapeHtml(err.message)}</div>`;
  }
};

// --------------------------------------------------------------------------
// VIEW 2: RESUME ANALYSIS
// --------------------------------------------------------------------------
function renderResumeAnalysis(resume) {
  const container = byId("resume-content");
  if (!container || !resume) return;

  const contact = resume.contact || {};
  const skillsByCategory = resume.skills_by_category || {};
  const experiences = resume.experience || [];
  const projects = resume.projects || [];
  const education = resume.education || [];

  container.innerHTML = `
    <!-- Contact & Skills Matrix -->
    <div class="cards-grid-2">
      <!-- Identity & Contact Information Card -->
      <div class="info-card">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
          Candidate Identity &amp; Contact
        </h3>
        <div class="contact-table">
          <div class="contact-row">
            <span class="contact-label">Full Name:</span>
            <strong class="contact-value">${escapeHtml(resume.name || "Candidate")}</strong>
            <button class="btn-copy" type="button" onclick="copyText('${escapeHtml(resume.name || "")}', this)">Copy</button>
          </div>
          <div class="contact-row">
            <span class="contact-label">Target Title:</span>
            <span class="contact-value">${escapeHtml(resume.title || "Not stated")}</span>
            <span></span>
          </div>
          <div class="contact-row">
            <span class="contact-label">Email:</span>
            <span class="contact-value">${contact.email ? `<a href="mailto:${escapeHtml(contact.email)}">${escapeHtml(contact.email)}</a>` : '<span class="text-muted">Not detected</span>'}</span>
            ${contact.email ? `<button class="btn-copy" type="button" onclick="copyText('${escapeHtml(contact.email)}', this)">Copy</button>` : "<span></span>"}
          </div>
          <div class="contact-row">
            <span class="contact-label">Phone:</span>
            <span class="contact-value">${contact.phone ? `<a href="tel:${escapeHtml(contact.phone)}">${escapeHtml(contact.phone)}</a>` : '<span class="text-muted">Not detected</span>'}</span>
            ${contact.phone ? `<button class="btn-copy" type="button" onclick="copyText('${escapeHtml(contact.phone)}', this)">Copy</button>` : "<span></span>"}
          </div>
          <div class="contact-row">
            <span class="contact-label">LinkedIn:</span>
            <span class="contact-value">${contact.linkedin ? `<a href="${escapeHtml(contact.linkedin)}" target="_blank" rel="noopener">${escapeHtml(contact.linkedin)}</a>` : '<span class="text-muted">Not detected</span>'}</span>
            ${contact.linkedin ? `<button class="btn-copy" type="button" onclick="copyText('${escapeHtml(contact.linkedin)}', this)">Copy</button>` : "<span></span>"}
          </div>
          <div class="contact-row">
            <span class="contact-label">GitHub:</span>
            <span class="contact-value">${contact.github ? `<a href="${escapeHtml(contact.github)}" target="_blank" rel="noopener">${escapeHtml(contact.github)}</a>` : '<span class="text-muted">Not detected</span>'}</span>
            ${contact.github ? `<button class="btn-copy" type="button" onclick="copyText('${escapeHtml(contact.github)}', this)">Copy</button>` : "<span></span>"}
          </div>
        </div>
      </div>

      <!-- Verified Skills by Category -->
      <div class="info-card">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          Extracted Skills by Category (${resume.skills?.length || 0})
        </h3>
        <div class="skills-matrix">
          ${
            Object.keys(skillsByCategory).length
              ? Object.entries(skillsByCategory)
                  .map(
                    ([cat, items]) => `
                <div class="matrix-row">
                  <span class="matrix-category">${escapeHtml(cat)} (${items.length})</span>
                  <div class="chips-container">
                    ${items.map((s) => `<span class="skill-chip neutral">${escapeHtml(s)}</span>`).join("")}
                  </div>
                </div>
              `
                  )
                  .join("")
              : '<span class="text-muted">No categorized skills found.</span>'
          }
        </div>
      </div>
    </div>

    <!-- Experience Timeline Section -->
    <div class="dashboard-panel">
      <div class="panel-header">
        <div>
          <span class="eyebrow">CAREER HISTORY</span>
          <h3 class="panel-title">Work Experience (${Number(resume.years_experience || 0).toFixed(1)} Years Total)</h3>
        </div>
      </div>
      <div class="content-stack">
        ${
          experiences.length
            ? experiences
                .map(
                  (exp) => `
              <div class="timeline-card">
                <div class="timeline-header">
                  <h4 class="timeline-title">${escapeHtml(exp.title || "Position")}</h4>
                  ${exp.duration ? `<span class="timeline-duration">${escapeHtml(exp.duration)}</span>` : ""}
                </div>
                <div class="timeline-org">${escapeHtml(exp.organization || "Company")}</div>
                ${exp.bullets?.length ? `<ul class="timeline-bullets">${exp.bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>` : ""}
              </div>
            `
                )
                .join("")
            : '<div class="timeline-card"><p class="text-muted">No explicit dated work experience blocks parsed.</p></div>'
        }
      </div>
    </div>

    <!-- Technical Projects Section -->
    <div class="dashboard-panel">
      <div class="panel-header">
        <div>
          <span class="eyebrow">PORTFOLIO &amp; ARTIFACTS</span>
          <h3 class="panel-title">Technical Projects (${projects.length})</h3>
        </div>
      </div>
      <div class="content-stack">
        ${
          projects.length
            ? projects
                .map(
                  (proj) => `
              <div class="timeline-card">
                <h4 class="timeline-title" style="margin-bottom: 8px;">${escapeHtml(proj.name || "Project")}</h4>
                ${proj.technologies?.length ? `<div class="chips-container" style="margin-bottom: 10px;">${proj.technologies.map((t) => `<span class="skill-chip neutral">${escapeHtml(t)}</span>`).join("")}</div>` : ""}
                ${proj.bullets?.length ? `<ul class="timeline-bullets">${proj.bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>` : ""}
              </div>
            `
                )
                .join("")
            : '<div class="timeline-card"><p class="text-muted">No distinct project sections detected in resume.</p></div>'
        }
      </div>
    </div>

    <!-- Education Credentials Section -->
    <div class="dashboard-panel">
      <div class="panel-header">
        <div>
          <span class="eyebrow">ACADEMIC BACKGROUND</span>
          <h3 class="panel-title">Education &amp; Degrees (${education.length})</h3>
        </div>
      </div>
      <div class="content-stack">
        ${
          education.length
            ? education
                .map(
                  (edu) => `
              <div class="timeline-card">
                <div class="timeline-header">
                  <h4 class="timeline-title">${escapeHtml(edu.degree || edu.raw || "Degree")}</h4>
                  ${edu.year ? `<span class="timeline-duration">${escapeHtml(edu.year)}</span>` : ""}
                </div>
                <div class="timeline-org">${escapeHtml(edu.institution || "")}</div>
              </div>
            `
                )
                .join("")
            : '<div class="timeline-card"><p class="text-muted">No formal educational degrees parsed.</p></div>'
        }
      </div>
    </div>
  `;
}

// --------------------------------------------------------------------------
// VIEW 3: JOB MATCH FIT
// --------------------------------------------------------------------------
function renderJobMatch(match, profile) {
  const container = byId("match-content");
  if (!container || !match) return;

  const components = match.components || {};
  const weights = match.weights || {};
  const skillMatch = match.skill_match || {};
  const kwMatch = match.keyword_match || {};

  container.innerHTML = `
    <!-- Match Score Hero Banner -->
    <div class="match-hero-card">
      <div class="match-hero-info">
        <span class="eyebrow" style="color:var(--brand-cyan);">TARGET BENCHMARK</span>
        <h3>${escapeHtml(profile?.title || "Target Role")}</h3>
        <p>Minimum Experience Required: <strong>${profile?.minimum_experience || 0} yrs</strong> &bull; Education: <strong>${escapeHtml(profile?.education_requirements?.[0] || "Technical Degree")}</strong></p>
      </div>
      <div class="match-score-bubble">
        <strong>${Number(match.overall_score || 0).toFixed(1)}%</strong>
        <span>Overall Fit</span>
      </div>
    </div>

    <!-- 5-Component Mathematical Breakdown Table -->
    <div class="formula-table-card">
      <h3 style="font-size:16px; font-weight:700; margin-bottom:4px;">Mathematical Formula &amp; Weight Contribution</h3>
      <p class="text-muted" style="font-size:13px;">Final Fit = (0.40 &times; Skills) + (0.25 &times; Semantic) + (0.15 &times; Exp) + (0.10 &times; Edu) + (0.10 &times; Keywords)</p>
      <table class="formula-table">
        <thead>
          <tr>
            <th>Scoring Factor</th>
            <th>Calculated Score</th>
            <th>Target Weight</th>
            <th>Net Contribution</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Skills Match</strong></td>
            <td>${Number(components.skills || 0).toFixed(1)}%</td>
            <td>40% (0.40)</td>
            <td><strong>+${((components.skills || 0) * 0.4).toFixed(1)}%</strong></td>
          </tr>
          <tr>
            <td><strong>Semantic Similarity</strong></td>
            <td>${Number(components.semantic || 0).toFixed(1)}%</td>
            <td>25% (0.25)</td>
            <td><strong>+${((components.semantic || 0) * 0.25).toFixed(1)}%</strong></td>
          </tr>
          <tr>
            <td><strong>Experience Match</strong></td>
            <td>${Number(components.experience || 0).toFixed(1)}%</td>
            <td>15% (0.15)</td>
            <td><strong>+${((components.experience || 0) * 0.15).toFixed(1)}%</strong></td>
          </tr>
          <tr>
            <td><strong>Education Match</strong></td>
            <td>${Number(components.education || 0).toFixed(1)}%</td>
            <td>10% (0.10)</td>
            <td><strong>+${((components.education || 0) * 0.1).toFixed(1)}%</strong></td>
          </tr>
          <tr>
            <td><strong>Keyword Coverage</strong></td>
            <td>${Number(components.keywords || 0).toFixed(1)}%</td>
            <td>10% (0.10)</td>
            <td><strong>+${((components.keywords || 0) * 0.1).toFixed(1)}%</strong></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Side-by-Side Skills Comparison -->
    <div class="cards-grid-2">
      <div class="info-card">
        <h3>Matching Required Skills (${skillMatch.matching_skills?.length || 0})</h3>
        <div class="chips-container">
          ${
            skillMatch.matching_skills?.length
              ? skillMatch.matching_skills.map((s) => `<span class="skill-chip matched">✓ ${escapeHtml(s)}</span>`).join("")
              : '<span class="text-muted">No required skills matched.</span>'
          }
        </div>
      </div>

      <div class="info-card">
        <h3>Missing Required Skills (${skillMatch.missing_required?.length || 0})</h3>
        <div class="chips-container">
          ${
            skillMatch.missing_required?.length
              ? skillMatch.missing_required.map((s) => `<span class="skill-chip gap">⚠ ${escapeHtml(s)}</span>`).join("")
              : '<span class="badge-success">✓ 100% Required skills matched!</span>'
          }
        </div>
      </div>
    </div>

    <!-- Matched vs Missing Keywords -->
    <div class="cards-grid-2">
      <div class="info-card">
        <h3>Matched Keywords (${kwMatch.matching_keywords?.length || 0})</h3>
        <div class="chips-container">
          ${
            kwMatch.matching_keywords?.length
              ? kwMatch.matching_keywords.map((k) => `<span class="skill-chip matched">✓ ${escapeHtml(k)}</span>`).join("")
              : '<span class="text-muted">No keywords matched.</span>'
          }
        </div>
      </div>

      <div class="info-card">
        <h3>Missing Target Keywords (${kwMatch.missing_keywords?.length || 0})</h3>
        <div class="chips-container">
          ${
            kwMatch.missing_keywords?.length
              ? kwMatch.missing_keywords.map((k) => `<span class="skill-chip gap">⚠ ${escapeHtml(k)}</span>`).join("")
              : '<span class="badge-success">✓ All target keywords present.</span>'
          }
        </div>
      </div>
    </div>
  `;
}

// --------------------------------------------------------------------------
// VIEW 4: SKILL GAP ROADMAP
// --------------------------------------------------------------------------
function renderSkillGapRoadmap(match, insights) {
  const container = byId("gap-content");
  if (!container || !match) return;

  const gaps = match.skill_match?.skill_gaps || [];

  if (!gaps.length) {
    container.innerHTML = `
      <div class="info-card" style="text-align:center; padding:36px;">
        <h3 style="color:var(--color-success); border:none; justify-content:center;">✓ Complete Skill Alignment!</h3>
        <p class="text-muted">Your resume demonstrates verified evidence for all required and preferred skills for this role.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="content-stack">
      ${gaps
        .map(
          (gap) => `
        <div class="gap-card-item ${gap.priority === "high" ? "high" : ""}">
          <div class="gap-card-top">
            <span class="gap-skill-name">${escapeHtml(gap.skill)}</span>
            <span class="gap-priority-badge">${gap.priority === "high" ? "Priority Gap (Required)" : "Secondary Gap (Preferred)"}</span>
          </div>
          <p class="gap-reason">Target role expectation: ${escapeHtml(gap.importance || "Essential for daily responsibilities")}</p>
          <div class="gap-roadmap-box">
            <strong>Recommended Step-by-Step Learning Path:</strong>
            <span>${escapeHtml(gap.learning_path || "Study official documentation, build a documented portfolio project, and practice hands-on implementations.")}</span>
          </div>
        </div>
      `
        )
        .join("")}
    </div>
  `;
}

// --------------------------------------------------------------------------
// VIEW 5: AI RECOMMENDATIONS & ADVISOR
// --------------------------------------------------------------------------
function renderAiAdvisor(insights, advisor) {
  const container = byId("advice-content");
  if (!container || !insights) return;

  const source = advisor?.source || "Deterministic rule-based heuristics";

  container.innerHTML = `
    <div class="source-badge">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
      <span>Advisor Engine: ${escapeHtml(source)}</span>
    </div>

    <div class="advice-tabs-header">
      <button class="advice-tab-btn active" type="button" data-tab="strengths">🌟 Strengths (${insights.strengths?.length || 0})</button>
      <button class="advice-tab-btn" type="button" data-tab="gaps">⚠️ Identified Gaps (${insights.gaps?.length || 0})</button>
      <button class="advice-tab-btn" type="button" data-tab="improvements">💡 Improvements (${insights.improvements?.length || 0})</button>
      <button class="advice-tab-btn" type="button" data-tab="projects">📁 Project Ideas (${insights.project_suggestions?.length || 0})</button>
      <button class="advice-tab-btn" type="button" data-tab="ats-tips">🤖 ATS Suggestions (${insights.ats_suggestions?.length || 0})</button>
    </div>

    <!-- Tab 1: Strengths -->
    <div class="advice-tab-content active" id="tab-strengths">
      <div class="advice-list">
        ${(insights.strengths || []).map((s) => `<div class="advice-item-card"><span class="item-bullet">✓</span><span>${escapeHtml(s)}</span></div>`).join("")}
      </div>
    </div>

    <!-- Tab 2: Gaps -->
    <div class="advice-tab-content" id="tab-gaps">
      <div class="advice-list">
        ${(insights.gaps || []).map((g) => `<div class="advice-item-card"><span class="item-bullet" style="color:var(--color-danger);">⚠</span><span>${escapeHtml(g)}</span></div>`).join("")}
      </div>
    </div>

    <!-- Tab 3: Improvements -->
    <div class="advice-tab-content" id="tab-improvements">
      <div class="advice-list">
        ${(insights.improvements || []).map((i) => `<div class="advice-item-card"><span class="item-bullet" style="color:var(--brand-cyan);">💡</span><span>${escapeHtml(i)}</span></div>`).join("")}
      </div>
    </div>

    <!-- Tab 4: Projects -->
    <div class="advice-tab-content" id="tab-projects">
      <div class="advice-list">
        ${(insights.project_suggestions || []).map((p) => `<div class="advice-item-card"><span class="item-bullet" style="color:var(--brand-purple);">🚀</span><span>${escapeHtml(p)}</span></div>`).join("")}
      </div>
    </div>

    <!-- Tab 5: ATS Tips -->
    <div class="advice-tab-content" id="tab-ats-tips">
      <div class="advice-list">
        ${(insights.ats_suggestions || []).map((a) => `<div class="advice-item-card"><span class="item-bullet" style="color:var(--color-warning);">📝</span><span>${escapeHtml(a)}</span></div>`).join("")}
      </div>
    </div>
  `;

  // Attach tab switching logic
  container.querySelectorAll(".advice-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      container.querySelectorAll(".advice-tab-btn").forEach((b) => b.classList.remove("active"));
      container.querySelectorAll(".advice-tab-content").forEach((c) => c.classList.remove("active"));

      btn.classList.add("active");
      const targetId = `tab-${btn.getAttribute("data-tab")}`;
      byId(targetId)?.classList.add("active");
    });
  });
}

// --------------------------------------------------------------------------
// VIEW 6: INTERVIEW PREPARATION PACK
// --------------------------------------------------------------------------
function renderInterviewPrep(interview) {
  const container = byId("interview-content");
  if (!container || !interview) return;

  const categories = [
    { key: "technical_questions", title: "Technical & Architecture Questions" },
    { key: "project_questions", title: "Project & Implementation Questions" },
    { key: "hr_questions", title: "Behavioral & Collaboration Questions" },
    { key: "scenario_questions", title: "Practical Problem-Solving Scenarios" },
  ];

  container.innerHTML = `
    <div class="content-stack">
      ${categories
        .map((cat) => {
          const questions = interview[cat.key] || [];
          if (!questions.length) return "";
          return `
            <div class="interview-group-card">
              <h3>${escapeHtml(cat.title)} (${questions.length})</h3>
              <div class="questions-list">
                ${questions
                  .map(
                    (q) => `
                  <div class="question-accordion">
                    <div style="padding:16px 18px; display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
                      <strong style="font-size:14px; color:var(--brand-navy); line-height:1.4;">${escapeHtml(q.question)}</strong>
                      <button class="btn-copy" type="button" onclick="copyText('${escapeHtml(q.question).replace(/'/g, "\\'")}', this)">Copy</button>
                    </div>
                    <div class="question-body">
                      <p style="color:var(--text-muted);"><strong>Why interviewers ask this:</strong> ${escapeHtml(q.why_interviewer_may_ask || "")}</p>
                      <div class="answer-guide-box">
                        <strong>Standout Answer Blueprint:</strong>
                        <span>${escapeHtml(q.strong_answer_should_cover || "")}</span>
                      </div>
                    </div>
                  </div>
                `
                  )
                  .join("")}
              </div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

// --------------------------------------------------------------------------
// VIEW 7: ATS COMPATIBILITY SCAN
// --------------------------------------------------------------------------
function renderAtsScan(ats) {
  const container = byId("ats-content");
  if (!container || !ats) return;

  const components = ats.components || {};
  const sections = ats.sections_detected || {};
  const score = Number(ats.score || 0).toFixed(0);

  const rating = score >= 80 ? "Excellent ATS Readiness" : score >= 60 ? "Moderate ATS Compatibility" : "Needs Optimization";

  container.innerHTML = `
    <!-- ATS Score Hero Meter -->
    <div class="ats-hero-card">
      <div class="ats-score-meter">
        <div class="ats-score-circle">${score}</div>
        <div class="ats-score-meta">
          <h3>${rating}</h3>
          <p>Scored out of 100 based on standard industry parser heuristics.</p>
        </div>
      </div>
      <span class="badge-neutral">5 Heuristic Weightings</span>
    </div>

    <!-- ATS 5 Component Breakdown -->
    <div class="ats-components-grid">
      <div class="ats-mini-tile">
        <span>Keywords (30%)</span>
        <strong>${Number(components.keywords || 0).toFixed(0)}%</strong>
      </div>
      <div class="ats-mini-tile">
        <span>Structure (25%)</span>
        <strong>${Number(components.structure || 0).toFixed(0)}%</strong>
      </div>
      <div class="ats-mini-tile">
        <span>Skills (20%)</span>
        <strong>${Number(components.skills || 0).toFixed(0)}%</strong>
      </div>
      <div class="ats-mini-tile">
        <span>Readability (15%)</span>
        <strong>${Number(components.readability || 0).toFixed(0)}%</strong>
      </div>
      <div class="ats-mini-tile">
        <span>Formatting (10%)</span>
        <strong>${Number(components.formatting || 0).toFixed(0)}%</strong>
      </div>
    </div>

    <!-- Standard Section Headings Audit -->
    <div class="sections-audit-card">
      <h3 style="font-size:16px; font-weight:700;">Standard Section Headings Audit</h3>
      <p class="text-muted" style="font-size:13px; margin-top:2px;">Applicant Tracking Systems look for explicit, standardized section titles.</p>
      <div class="sections-checklist">
        <div class="section-check-item ${sections.summary ? "detected" : "missing"}">
          <span>${sections.summary ? "✓" : "✗"}</span>
          <span>Summary / Profile</span>
        </div>
        <div class="section-check-item ${sections.experience ? "detected" : "missing"}">
          <span>${sections.experience ? "✓" : "✗"}</span>
          <span>Work Experience</span>
        </div>
        <div class="section-check-item ${sections.education ? "detected" : "missing"}">
          <span>${sections.education ? "✓" : "✗"}</span>
          <span>Education</span>
        </div>
        <div class="section-check-item ${sections.skills ? "detected" : "missing"}">
          <span>${sections.skills ? "✓" : "✗"}</span>
          <span>Skills Catalog</span>
        </div>
        <div class="section-check-item ${sections.projects ? "detected" : "missing"}">
          <span>${sections.projects ? "✓" : "✗"}</span>
          <span>Projects</span>
        </div>
      </div>
    </div>

    <!-- Recommendations List -->
    <div class="dashboard-panel" style="margin-top:20px;">
      <h3 style="font-size:16px; font-weight:700; margin-bottom:12px;">Parser Recommendations</h3>
      <div class="advice-list">
        ${(ats.recommendations || []).map((r) => `<div class="advice-item-card"><span class="item-bullet">✓</span><span>${escapeHtml(r)}</span></div>`).join("")}
      </div>
    </div>
  `;
}

// --------------------------------------------------------------------------
// HTML Report Downloader
// --------------------------------------------------------------------------
async function downloadReport() {
  if (!state.currentAnalysis) return;

  const btn = byId("report-button");
  if (btn) btn.disabled = true;

  try {
    const res = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis: state.currentAnalysis }),
    });

    if (!res.ok) throw new Error("Could not export HTML report");

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    const name = state.currentAnalysis?.resume?.name || "candidate";
    const cleanName = name.replace(/[^a-zA-Z0-9_-]/g, "");
    a.href = url;
    a.download = `resume-match-report-${cleanName || "candidate"}.html`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    showNotice("Report downloaded successfully!", "success");
  } catch (err) {
    showNotice(err.message || "Failed to download report.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

// --------------------------------------------------------------------------
// Utility & Toast Helpers
// --------------------------------------------------------------------------
function showNotice(message, type = "info") {
  const banner = byId("notice");
  const text = byId("notice-text");
  const icon = byId("notice-icon");
  if (!banner || !text) return;

  banner.className = `notice-banner ${type}`;
  text.textContent = message;

  const icons = {
    success: "✓",
    error: "✕",
    warning: "⚠️",
    info: "ℹ️",
  };
  if (icon) icon.textContent = icons[type] || "ℹ️";

  banner.hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function hideNotice() {
  const banner = byId("notice");
  if (banner) banner.hidden = true;
}

window.copyText = function (text, btn) {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    if (btn) {
      const orig = btn.textContent;
      btn.textContent = "Copied!";
      btn.style.color = "var(--color-success)";
      setTimeout(() => {
        btn.textContent = orig;
        btn.style.color = "";
      }, 1800);
    }
  });
};
