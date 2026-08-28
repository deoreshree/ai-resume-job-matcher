const state = { analysis: null, view: "dashboard", roles: [] };

const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
const labels = { dashboard: "Dashboard", resume: "Resume analysis", match: "Job match", gap: "Skill gap", advice: "AI recommendations", interview: "Interview questions", ats: "ATS analysis", about: "About" };

function showNotice(message, kind = "error") {
  const notice = byId("notice");
  notice.textContent = message;
  notice.className = `notice ${kind === "success" ? "success" : ""}`;
  notice.hidden = !message;
}

function setBusy(isBusy) {
  byId("loading-state").hidden = !isBusy;
  byId("analyse-button").disabled = isBusy;
  if (isBusy) {
    byId("empty-state").hidden = true;
    byId("result-content").hidden = true;
  }
}

function setView(view) {
  state.view = view;
  byId("page-title").textContent = labels[view];
  document.querySelectorAll(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.view === view));
  document.querySelectorAll(".view").forEach((panel) => panel.classList.toggle("active", panel.dataset.viewContent === view));
  const hasContent = Boolean(state.analysis) || view === "about";
  byId("empty-state").hidden = hasContent;
  byId("result-content").hidden = !hasContent;
  byId("report-button").disabled = !state.analysis;
}

function chips(items, type = "match") {
  if (!items?.length) return '<span class="chip neutral">No evidence identified</span>';
  const icon = type === "gap" ? "⚠" : "✓";
  return items.map((item) => `<span class="chip ${type === "gap" ? "gap" : ""}">${icon} ${escapeHtml(item)}</span>`).join("");
}

function metric(label, value, compact = false) {
  return `<article class="metric"><span>${escapeHtml(label)}</span><strong class="${compact ? "small" : ""}">${escapeHtml(value)}</strong></article>`;
}

function listItems(items) {
  return items?.length ? `<ul class="recommendation-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : '<p class="muted">No items identified.</p>';
}

function renderDashboard(data) {
  const { resume, job_profile: profile, match, ats } = data;
  byId("metrics").innerHTML = [
    metric("Candidate", resume.name || "Not identified", (resume.name || "").length > 15),
    metric("Target role", profile.title || "Custom role", (profile.title || "").length > 15),
    metric("Overall match", `${Math.round(match.overall_score)}%`),
    metric("ATS score", `${Math.round(ats.score)}/100`),
    metric("Skills found", resume.skills?.length || 0),
    metric("Experience", `${Number(resume.years_experience || 0).toFixed(1)} yrs`),
  ].join("");
  const componentNames = { skills: "Skills match", semantic: "Semantic relevance", experience: "Experience", education: "Education", keywords: "Keywords" };
  byId("score-breakdown").innerHTML = Object.entries(componentNames).map(([key, name]) => {
    const score = Number(match.components[key] || 0);
    return `<div class="score-row"><span>${name}</span><div class="bar"><i style="width:${Math.max(0, Math.min(100, score))}%"></i></div><strong>${score.toFixed(0)}%</strong></div>`;
  }).join("");
  const coverage = Math.round(Number(match.skill_match.required_coverage || 0) * 100);
  byId("skill-donut").style.background = `conic-gradient(#188473 0 ${coverage}%,#eef2f6 ${coverage}% 100%)`;
  byId("skill-donut").innerHTML = `<div><strong>${coverage}%</strong><span>required skills</span></div>`;
  byId("skill-counts").innerHTML = `<span><b>${match.skill_match.matching_skills?.length || 0}</b> matching</span><span><b>${match.skill_match.missing_skills?.length || 0}</b> gaps</span>`;
  byId("matching-skills").innerHTML = chips(match.skill_match.matching_skills);
  byId("missing-skills").innerHTML = chips(match.skill_match.missing_skills, "gap");
}

function renderResume(data) {
  const { resume } = data;
  const contacts = [["Name", resume.name], ["Email", resume.email], ["Phone", resume.phone], ["LinkedIn", resume.linkedin], ["GitHub", resume.github], ["Portfolio", resume.portfolio]];
  const contactHtml = contacts.filter(([, value]) => value).map(([label, value]) => {
    const linked = /^(https?:\/\/|www\.|linkedin\.com|github\.com)/i.test(value);
    const href = value.startsWith("http") ? value : `https://${value}`;
    return `<div class="key-value"><b>${label}</b>${linked ? `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">${escapeHtml(value)}</a>` : `<span>${escapeHtml(value)}</span>`}</div>`;
  }).join("") || '<p class="muted">No contact details identified.</p>';
  const education = resume.education?.map((item) => `<div class="item-row"><h4>${escapeHtml(item.degree || "Education")}</h4><p>${escapeHtml(item.institution || "Institution not identified")}${item.year ? ` · ${escapeHtml(item.year)}` : ""}</p></div>`).join("") || '<p class="muted">No education section identified.</p>';
  const skills = Object.entries(resume.skill_details?.by_category || {}).map(([category, values]) => `<div class="item-row"><h4>${escapeHtml(category)}</h4><div class="chips">${chips(values)}</div></div>`).join("") || '<p class="muted">No catalogue skills identified.</p>';
  const experience = resume.experience?.map((item) => `<article class="details-card"><h3>${escapeHtml(item.title || "Experience")}</h3><p class="muted">${escapeHtml(item.organization || "Organisation not identified")}${item.duration ? ` · ${escapeHtml(item.duration)}` : ""}</p>${item.responsibilities?.length ? `<ul class="recommendation-list">${item.responsibilities.map((bullet) => `<li>${escapeHtml(bullet)}</li>`).join("")}</ul>` : ""}</article>`).join("") || '<article class="details-card"><p class="muted">No experience section identified.</p></article>';
  const projects = resume.projects?.map((project) => `<article class="details-card"><h3>${escapeHtml(project.title || "Project")}</h3><p class="muted">${escapeHtml(project.description || "No description identified.")}</p><div class="chips">${chips(project.technologies)}</div></article>`).join("") || '<article class="details-card"><p class="muted">No projects section identified.</p></article>';
  byId("resume-content").innerHTML = `<div class="details-grid"><article class="details-card"><h2>Contact details</h2>${contactHtml}</article><article class="details-card"><h2>Education</h2>${education}</article><article class="details-card"><h2>Skills detected</h2>${skills}</article><article class="details-card"><h2>Certifications</h2><div class="chips">${chips(resume.certifications)}</div></article></div><h3 class="subsection-title">Experience</h3><div class="details-grid">${experience}</div><h3 class="subsection-title">Projects</h3><div class="details-grid">${projects}</div>`;
}

function renderMatch(data) {
  const { job_profile: profile, match } = data;
  const formula = Object.entries({ skills: "Skills match", semantic: "Semantic relevance", experience: "Experience fit", education: "Education", keywords: "Keyword coverage" }).map(([key, label]) => `<div><span>${label}: ${Number(match.components[key] || 0).toFixed(1)}%</span><strong>× ${Math.round(Number(match.weights[key] || 0) * 100)}%</strong></div>`).join("");
  byId("match-content").innerHTML = `<div class="role-summary"><article class="panel"><div class="score-hero"><div class="score-number">${Math.round(match.overall_score)}%</div><p><strong>${escapeHtml(profile.title)}</strong><br>Semantic comparison: ${escapeHtml(match.semantic_method)}</p></div><p class="eyebrow">TRANSPARENT FORMULA</p><div class="formula">${formula}</div></article><article class="panel"><p class="eyebrow">ROLE REQUIREMENTS</p><h2>Skills requested</h2><div class="item-row"><h4>Required</h4><div class="chips">${chips(profile.required_skills)}</div></div><div class="item-row"><h4>Preferred</h4><div class="chips">${chips(profile.preferred_skills)}</div></div></article></div><div class="two-column"><article class="panel"><p class="eyebrow">EVIDENCE FOUND</p><h2>Matching skills and keywords</h2><div class="item-row"><h4>Skills</h4><div class="chips">${chips(match.skill_match.matching_skills)}</div></div><div class="item-row"><h4>Keywords</h4><div class="chips">${chips(match.keyword_match.matched_keywords)}</div></div></article><article class="panel"><p class="eyebrow">EVIDENCE TO BUILD</p><h2>Missing skills and keywords</h2><div class="item-row"><h4>Skills</h4><div class="chips">${chips(match.skill_match.missing_skills, "gap")}</div></div><div class="item-row"><h4>Keywords</h4><div class="chips">${chips(match.keyword_match.missing_keywords, "gap")}</div></div></article></div>`;
}

function renderGap(data) {
  const gaps = data.match.skill_match.skill_gaps || [];
  const recommendations = data.insights.skill_recommendations || [];
  byId("gap-content").innerHTML = gaps.length ? gaps.map((gap) => {
    const path = recommendations.find((item) => item.toLowerCase().startsWith(`${gap.skill}:`.toLowerCase()))?.split(":").slice(1).join(":").trim() || `Learn the fundamentals of ${gap.skill}, practise them in a small project, and only list the skill once you can support it with genuine evidence.`;
    return `<article class="gap-card ${gap.importance === "High" ? "high" : ""}"><h3>${escapeHtml(gap.skill)}</h3><span class="priority">${escapeHtml(gap.importance)} priority</span><p><strong>Why:</strong> ${escapeHtml(gap.reason)}</p><p><strong>Suggested learning path:</strong> ${escapeHtml(path)}</p></article>`;
  }).join("") : '<article class="panel"><h2>No catalogue skill gap identified</h2><p class="muted">Continue preparing examples that substantiate your matching skills in interviews.</p></article>';
}

function renderAdvice(data) {
  const advisor = data.advisor;
  const panels = { strengths: "Strengths", weaknesses: "Gaps", improvements: "Improvements", project_suggestions: "Projects", ats_suggestions: "ATS" };
  const buttons = Object.entries(panels).map(([key, label], index) => `<button class="tab-button ${index === 0 ? "active" : ""}" data-tab="${key}" type="button">${label}</button>`).join("");
  const contents = Object.entries(panels).map(([key], index) => `<div class="tab-panel ${index === 0 ? "active" : ""}" data-tab-panel="${key}">${listItems(advisor[key])}</div>`).join("");
  byId("advice-content").innerHTML = `<div class="source-note"><strong>${escapeHtml(advisor.source)}</strong> · ${escapeHtml(advisor.notice)}</div><article class="panel"><div class="tab-buttons">${buttons}</div>${contents}</article>`;
  byId("advice-content").querySelectorAll(".tab-button").forEach((button) => button.addEventListener("click", () => {
    const target = button.dataset.tab;
    byId("advice-content").querySelectorAll(".tab-button").forEach((item) => item.classList.toggle("active", item === button));
    byId("advice-content").querySelectorAll(".tab-panel").forEach((item) => item.classList.toggle("active", item.dataset.tabPanel === target));
  }));
}

function renderInterview(data) {
  const groups = { technical_questions: "Technical", project_questions: "Projects", hr_questions: "HR", scenario_questions: "Scenarios" };
  byId("interview-content").innerHTML = Object.entries(groups).map(([key, title]) => `<article class="panel interview-group"><p class="eyebrow">${title.toUpperCase()}</p><h2>${title} questions</h2>${(data.interview[key] || []).map((question, index) => `<details class="question"><summary>${index + 1}. ${escapeHtml(question.question)}</summary><p><strong>Why interviewer may ask:</strong> ${escapeHtml(question.why_interviewer_may_ask)}</p><p><strong>A strong answer should cover:</strong> ${escapeHtml(question.strong_answer_should_cover)}</p></details>`).join("")}</article>`).join("");
}

function renderAts(data) {
  const { ats } = data;
  const componentNames = { keywords: "Keywords", structure: "Structure", skills: "Skills", readability: "Readability", formatting: "Formatting" };
  byId("ats-content").innerHTML = `<div class="score-hero panel"><div class="score-number">${Math.round(ats.score)}</div><p><strong>ATS Compatibility Score</strong><br>This is a transparent resume-readability and role-alignment heuristic, not a hiring decision.</p></div><div class="ats-grid">${Object.entries(componentNames).map(([key, label]) => `<article class="ats-mini"><span>${label}</span><strong>${Math.round(ats.components[key] || 0)}%</strong></article>`).join("")}</div><div class="two-column"><article class="panel"><p class="eyebrow">RECOMMENDATIONS</p><h2>Improve parsing clarity</h2>${listItems(ats.recommendations)}</article><article class="panel"><p class="eyebrow">POTENTIAL ISSUES</p><h2>What to review</h2>${ats.issues?.length ? ats.issues.map((issue) => `<p class="issue">${escapeHtml(issue)}</p>`).join("") : '<p class="muted">No parsing issues identified by these checks.</p>'}</article></div>`;
}

function renderAll(data) {
  renderDashboard(data);
  renderResume(data);
  renderMatch(data);
  renderGap(data);
  renderAdvice(data);
  renderInterview(data);
  renderAts(data);
}

async function loadRoles() {
  const select = byId("job-role");
  try {
    const response = await fetch("/api/roles");
    const payload = await response.json();
    state.roles = payload.roles || [];
    select.innerHTML = state.roles.map((role) => `<option value="${escapeHtml(role.title)}">${escapeHtml(role.title)}</option>`).join("");
  } catch {
    select.innerHTML = "<option>Unable to load roles</option>";
    showNotice("Job roles could not be loaded. Refresh the page and try again.");
  }
}

async function submitAnalysis(event) {
  event.preventDefault();
  const file = byId("resume").files[0];
  const mode = document.querySelector('input[name="target_mode"]:checked').value;
  const description = byId("job-description").value.trim();
  if (!file) return showNotice("Choose a PDF or DOCX resume first.");
  if (mode === "custom" && description.length < 40) return showNotice("Paste a fuller job description (at least 40 characters). ");
  setBusy(true);
  showNotice("");
  try {
    const form = new FormData();
    form.append("resume", file);
    form.append("target_mode", mode);
    form.append("job_role", byId("job-role").value);
    form.append("job_description", description);
    const response = await fetch("/api/analyze", { method: "POST", body: form });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "The analysis could not be completed.");
    state.analysis = payload.analysis;
    renderAll(state.analysis);
    setView("dashboard");
    showNotice("Analysis complete. Explore each section for detailed, evidence-based guidance.", "success");
  } catch (error) {
    state.analysis = null;
    setView("dashboard");
    showNotice(error.message || "The analysis could not be completed.");
  } finally {
    setBusy(false);
  }
}

async function downloadReport() {
  if (!state.analysis) return;
  const button = byId("report-button");
  button.disabled = true;
  button.textContent = "Preparing report…";
  try {
    const response = await fetch("/api/report", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ analysis: state.analysis }) });
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.error || "The report could not be generated.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "resume-match-report.html";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    showNotice(error.message || "The report could not be generated.");
  } finally {
    button.disabled = false;
    button.textContent = "↓ Download report";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadRoles();
  byId("resume").addEventListener("change", (event) => { byId("file-name").textContent = event.target.files[0]?.name || "No file selected"; });
  document.querySelectorAll('input[name="target_mode"]').forEach((input) => input.addEventListener("change", () => {
    const custom = input.value === "custom" && input.checked;
    byId("role-control").hidden = custom;
    byId("custom-control").hidden = !custom;
  }));
  byId("analysis-form").addEventListener("submit", submitAnalysis);
  byId("report-button").addEventListener("click", downloadReport);
  document.querySelectorAll(".nav-link").forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); setView(link.dataset.view); }));
  setView("dashboard");
});
