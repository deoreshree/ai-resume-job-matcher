/* View renderers. Each takes { state, actions } and fills its container.
   All dynamic strings are escaped; all dynamic styles go through CSSOM. */
"use strict";

const VIEWS = (() => {
  const { escapeHtml, icon, fmtPct, fmtNum, toneFor, createScoreRing, barRow, activateBars, chipList, listHTML, initTabs, emptyStateHTML, qs, qsa } = window.UI;

  const COMPONENT_LABELS = { skills: "Skills match", semantic: "Semantic relevance", experience: "Experience fit", education: "Education", keywords: "Keyword coverage" };
  const ATS_COMPONENT_LABELS = { keywords: "Keywords", structure: "Structure", skills: "Skills", readability: "Readability", formatting: "Formatting" };
  // Backend question groups mapped to the four preparation categories shown in the UI.
  const INTERVIEW_TABS = [
    { key: "technical_questions", label: "Technical", difficulty: "Medium" },
    { key: "hr_questions", label: "HR", difficulty: "Easy" },
    { key: "project_questions", label: "Resume Based", difficulty: "Medium" },
    { key: "scenario_questions", label: "Job Specific", difficulty: "Hard" },
  ];

  const sourceBadge = (profile) => profile?.source === "custom"
    ? `<span class="badge badge-info">custom job description</span>`
    : `<span class="badge badge-info">predefined role</span>`;

  /* ================= RESUME ANALYSIS ================= */

  function renderResume(container, { state }) {
    const analysis = state.analysis;
    if (!analysis) {
      container.innerHTML = emptyStateHTML({
        title: "No analysis yet",
        text: "Upload a PDF or DOCX resume to see its ATS score, parsed sections, and skills.",
        iconName: "file",
      });
      return;
    }
    const { resume, ats, match, job_profile: profile } = analysis;
    container.innerHTML = `
      <div class="panel-grid">
        <div class="grid-2">
          <article class="card" id="ats-ring-card">
            <p class="eyebrow">ATS score</p>
            <div class="score-ring-wrap" id="ats-ring-mount"></div>
            <p class="muted">Resume parsing compatibility heuristic — not a hiring decision.</p>
          </article>
          <article class="card">
            <p class="eyebrow">ATS components</p>
            <div id="ats-component-bars">
              ${Object.entries(ATS_COMPONENT_LABELS).map(([key, label]) => barRow(label, ats.components?.[key] || 0)).join("")}
            </div>
            <div class="divider"></div>
            <p class="eyebrow">Detected sections</p>
            ${chipList(ats.detected_sections, "match", { empty: "No standard sections detected" })}
            <p class="eyebrow">Missing sections</p>
            ${chipList(ats.missing_sections, "gap", { empty: "None — all key sections detected" })}
          </article>
        </div>

        <div class="grid-2">
          <article class="card">
            <p class="eyebrow">Parsing issues</p>
            ${ats.issues?.length ? `<ul class="list-warn">${ats.issues.map((issue) => `<li>${escapeHtml(issue)}</li>`).join("")}</ul>` : `<ul class="list-check"><li>No parsing issues detected by these checks.</li></ul>`}
            <div class="divider"></div>
            <p class="eyebrow">ATS recommendations</p>
            ${listHTML(ats.recommendations)}
          </article>
          <article class="card">
            <p class="eyebrow">Candidate overview</p>
            ${resumeOverview(resume)}
          </article>
        </div>

        <div class="grid-2">
          <article class="card">
            <p class="eyebrow">Matched skills — evidence found</p>
            ${chipList(match.skill_match?.matching_skills, "match", { empty: "No target skills evidenced yet" })}
            <p class="muted">Against <strong>${escapeHtml(profile?.title || "the target role")}</strong> ${sourceBadge(profile)}</p>
          </article>
          <article class="card">
            <p class="eyebrow">Missing skills — to develop</p>
            ${chipList(match.skill_match?.missing_skills, "gap", { empty: "No skill gaps identified" })}
            <p class="muted">Priority learning focus: <strong>${escapeHtml((match.skill_match?.missing_required || [])[0] || "none — strong coverage")}</strong></p>
          </article>
        </div>

        <article class="card">
          <p class="eyebrow">Resume strengths</p>
          ${listHTML(analysis.advisor?.strengths || analysis.insights?.strengths)}
        </article>
        <article class="card">
          <p class="eyebrow">Resume improvements</p>
          ${listHTML(analysis.advisor?.improvements || analysis.insights?.improvements, { check: false })}
        </article>
      </div>`;

    // Wire dynamic visuals (CSSOM only — CSP blocks inline style attributes).
    const ring = createScoreRing({ label: "ATS score" });
    qs("#ats-ring-mount", container).append(ring.wrap);
    ring.set(ats.score || 0);
    activateBars(container);
  }

  function resumeOverview(resume) {
    const contact = [
      ["Name", resume.name], ["Email", resume.email], ["Phone", resume.phone],
      ["LinkedIn", resume.linkedin], ["GitHub", resume.github], ["Portfolio", resume.portfolio],
    ].filter(([, value]) => value);
    const contactHTML = contact.length
      ? `<div class="kv">${contact.map(([key, value]) => {
          const isLink = /^(https?:\/\/|www\.|linkedin\.com|github\.com)/i.test(value);
          const href = value.startsWith("http") ? value : `https://${value}`;
          return `<b>${escapeHtml(key)}</b>${isLink ? `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">${escapeHtml(value)}</a>` : `<span>${escapeHtml(value)}</span>`}`;
        }).join("")}</div>`
      : `<p class="muted">No contact details identified.</p>`;

    const educationHTML = (resume.education || []).length
      ? resume.education.map((entry) => `<div class="entry"><h4>${escapeHtml(entry.degree || "Education")} <span class="when">${escapeHtml(entry.year || "")}</span></h4><p>${escapeHtml(entry.institution || "Institution not identified")}</p></div>`).join("")
      : `<p class="muted">No education section identified.</p>`;

    const experienceHTML = (resume.experience || []).length
      ? resume.experience.map((entry) => `<div class="entry"><h4>${escapeHtml(entry.title || "Experience")} <span class="when">${escapeHtml(entry.duration || "")}</span></h4><p class="muted">${escapeHtml(entry.organization || "Organisation not identified")}</p>${(entry.responsibilities || []).length ? `<ul>${entry.responsibilities.map((bullet) => `<li>${escapeHtml(bullet)}</li>`).join("")}</ul>` : ""}</div>`).join("")
      : `<p class="muted">No experience section identified.</p>`;

    const projectsHTML = (resume.projects || []).length
      ? resume.projects.map((project) => `<div class="entry"><h4>${escapeHtml(project.title || "Project")}</h4><p>${escapeHtml(project.description || "")}</p>${chipList(project.technologies, "info", { empty: "" })}</div>`).join("")
      : `<p class="muted">No projects section identified.</p>`;

    const skillsHTML = Object.entries(resume.skill_details?.by_category || {}).length
      ? Object.entries(resume.skill_details.by_category).map(([category, values]) => `<p class="eyebrow">${escapeHtml(category)}</p>${chipList(values, "info", { empty: "" })}`).join("")
      : chipList(resume.skills, "info");

    return `
      ${contactHTML}
      <div class="divider"></div>
      <p class="eyebrow">Experience · ${fmtNum(resume.years_experience)} yrs detected</p>
      ${experienceHTML}
      <div class="divider"></div>
      <p class="eyebrow">Education</p>
      ${educationHTML}
      <div class="divider"></div>
      <p class="eyebrow">Skills by category</p>
      ${skillsHTML}
      <div class="divider"></div>
      <p class="eyebrow">Projects</p>
      ${projectsHTML}
      <div class="divider"></div>
      <p class="eyebrow">Certifications</p>
      ${chipList(resume.certifications, "info")}
      <p class="eyebrow">Achievements</p>
      ${listHTML(resume.achievements)}`;
  }

  /* ================= JOB MATCH ================= */

  function renderMatch(container, { state }) {
    const analysis = state.analysis;
    if (!analysis) {
      container.innerHTML = emptyStateHTML({
        title: "Match against a job first",
        text: "Analyze your resume, then paste a job description here to see how well you fit.",
        iconName: "target",
      });
      return;
    }
    const { match, job_profile: profile, resume } = analysis;
    const skill = match.skill_match || {};
    const requiredCoverage = Math.round((skill.required_coverage || 0) * 100);
    const preferredCoverage = Math.round((skill.preferred_coverage || 0) * 100);
    const keywordCoverage = Math.round((match.keyword_match?.coverage || 0) * 100);

    container.innerHTML = `
      ${profile.warnings?.length ? `<div class="notice notice-info">${profile.warnings.map((warning) => escapeHtml(warning)).join(" ")}</div>` : ""}
      <div class="grid-2">
        <article class="card">
          <p class="eyebrow">Job match score</p>
          <div class="score-ring-wrap" id="match-ring-mount"></div>
          <p class="muted"><strong>${escapeHtml(profile.title || "Custom role")}</strong> ${sourceBadge(profile)}<br>Semantic comparison: ${escapeHtml(match.semantic_method)}</p>
        </article>
        <article class="card">
          <p class="eyebrow">Requirements coverage</p>
          ${barRow("Required skills", requiredCoverage, { tone: toneFor(requiredCoverage) })}
          ${barRow("Preferred skills", preferredCoverage, { tone: toneFor(preferredCoverage) })}
          ${barRow("Job keywords", keywordCoverage, { tone: toneFor(keywordCoverage) })}
          <div class="divider"></div>
          <div class="kv">
            <b>Experience</b><span>${escapeHtml(String(profile.minimum_experience ? `${fmtNum(profile.minimum_experience)}+ yrs required` : "Not specified"))} · you: ${fmtNum(resume.years_experience)} yrs</span>
            <b>Education</b><span>${escapeHtml((profile.education || [])[0] || "Not specified")}</span>
          </div>
        </article>
      </div>

      <div class="card" id="match-tabs-card">
        <div class="tabs" role="tablist" aria-label="Job match details">
          <button class="tab" type="button" data-tab="overview">Overview</button>
          <button class="tab" type="button" data-tab="gaps">Skill gaps</button>
          <button class="tab" type="button" data-tab="keywords">Keywords</button>
        </div>

        <div data-tab-panel="overview">
          <div class="table-scroll">
            <table class="compare-table" aria-label="Resume versus job skill comparison">
              <thead><tr><th scope="col">Skill</th><th scope="col">Your resume</th><th scope="col">Job asks</th></tr></thead>
              <tbody>
                ${compareRows(skill, profile)}
              </tbody>
            </table>
          </div>
        </div>

        <div data-tab-panel="gaps" hidden>
          ${gapVisualization(analysis)}
        </div>

        <div data-tab-panel="keywords" hidden>
          <p class="eyebrow">Matched keywords</p>
          ${chipList(match.keyword_match?.matched_keywords, "match", { empty: "No keywords matched yet" })}
          <div class="divider"></div>
          <p class="eyebrow">Missing keywords — use only where truthful</p>
          ${chipList(match.keyword_match?.missing_keywords, "gap", { empty: "No keyword gaps" })}
        </div>
      </div>`;

    const ring = createScoreRing({ label: "Job match" });
    qs("#match-ring-mount", container).append(ring.wrap);
    ring.set(match.overall_score || 0);
    activateBars(container);
    qsa(".tabs", container).forEach((group) => initTabs(group));
  }

  function compareRows(skill, profile) {
    const matched = new Set((skill.matching_skills || []).map((item) => item.toLowerCase()));
    const rows = [];
    const push = (items, tag) => (items || []).forEach((skillName) => {
      rows.push({ skillName, tag, has: matched.has(skillName.toLowerCase()) });
    });
    push(profile.required_skills, "Required");
    push(profile.preferred_skills.filter((item) => !(profile.required_skills || []).includes(item)), "Preferred");
    if (!rows.length) return `<tr><td colspan="3">No skill requirements detected in this job description.</td></tr>`;
    return rows.map((row) => `
      <tr>
        <td><strong>${escapeHtml(row.skillName)}</strong></td>
        <td>${row.has ? `<span class="compare-ok">${icon("check")} evidenced</span>` : `<span class="compare-miss">${icon("x")} not evidenced</span>`}</td>
        <td><span class="badge ${row.tag === "Required" ? "badge-danger" : "badge-warn"}">${row.tag}</span></td>
      </tr>`).join("");
  }

  function gapVisualization(analysis) {
    const { match, job_profile: profile, insights } = analysis;
    const matched = new Set((match.skill_match?.matching_skills || []).map((item) => item.toLowerCase()));
    const rows = [...(profile.required_skills || []), ...(profile.preferred_skills || [])]
      .filter((item, index, list) => list.indexOf(item) === index);
    const bars = rows.map((skillName) => {
      const has = matched.has(skillName.toLowerCase());
      return barRow(skillName, has ? 100 : 8, { tone: has ? "success" : "danger" });
    }).join("");

    const gaps = match.skill_match?.skill_gaps || [];
    const recommendations = insights?.skill_recommendations || [];
    const pathFor = (skillName) => recommendations.find((item) => item.toLowerCase().startsWith(`${skillName}:`.toLowerCase()))?.split(":").slice(1).join(":").trim();

    return `
      <p class="eyebrow">Your skills vs required skills</p>
      ${bars || `<p class="muted">No skill requirements detected.</p>`}
      <div class="divider"></div>
      <p class="eyebrow">Suggested learning paths</p>
      ${gaps.length ? gaps.map((gap) => `
        <div class="gap-card ${gap.importance === "High" ? "high" : ""}">
          <h3>${escapeHtml(gap.skill)} <span class="badge ${gap.importance === "High" ? "badge-danger" : "badge-warn"}">${escapeHtml(gap.importance)} priority</span></h3>
          <p>${escapeHtml(gap.reason)}</p>
          ${pathFor(gap.skill) ? `<p><strong>Suggested path:</strong> ${escapeHtml(pathFor(gap.skill))}</p>` : ""}
        </div>`).join("") : `<p class="muted">No catalogue skill gaps for this target.</p>`}`;
  }

  /* ================= DASHBOARD ================= */

  function renderDashboard(container, { state, actions }) {
    const analysis = state.analysis;
    if (!analysis) {
      container.innerHTML = emptyStateHTML({
        title: "Nothing analyzed yet",
        text: "Your dashboard fills up once you analyze a resume — scores, gaps, recommendations, and interview prep in one place.",
        iconName: "home",
      });
      return;
    }
    const { resume, job_profile: profile, match, ats, advisor, interview } = analysis;
    const skill = match.skill_match || {};

    container.innerHTML = `
      <div class="metrics-grid">
        ${metric("target", "Target role", profile.title || "Custom role", profile?.source === "custom" ? "custom job description" : "predefined role")}}
        ${metric("target", "Job match", `${fmtPct(match.overall_score)}%`, toneFor(match.overall_score) === "success" ? "strong fit" : "see breakdown")}
        ${metric("shield", "ATS score", `${fmtPct(ats.score)}/100`, toneFor(ats.score) === "success" ? "parser friendly" : "improvements available")}
        ${metric("layers", "Skills found", `${(skill.matching_skills || []).length}`, `of ${(profile.required_skills || []).length + (profile.preferred_skills || []).length} listed`)}
        ${metric("alert", "Skill gaps", `${(skill.missing_skills || []).length}`, (skill.missing_required || []).length ? `${skill.missing_required.length} high priority` : "none critical")}
        ${metric("clock", "Experience", `${fmtNum(resume.years_experience)} yrs`, profile.minimum_experience ? `${fmtNum(profile.minimum_experience)}+ required` : "no minimum")}
      </div>

      <div class="grid-2">
        <article class="card">
          <p class="eyebrow">Score breakdown — how the match is composed</p>
          ${Object.entries(COMPONENT_LABELS).map(([key, label]) => barRow(`${label} · ${Math.round((match.weights?.[key] || 0) * 100)}% weight`, match.components?.[key] || 0)).join("")}
          <p class="muted">Semantic method: ${escapeHtml(match.semantic_method)} · experience ${fmtNum(match.experience_score)}% · education ${fmtNum(match.education_score)}%</p>
        </article>
        <article class="card" id="dash-tabs-card">
          <div class="tabs" role="tablist" aria-label="Analysis details">
            <button class="tab" type="button" data-tab="insights">Strengths &amp; improvements</button>
            <button class="tab" type="button" data-tab="recommendations">Recommendations</button>
            <button class="tab" type="button" data-tab="interview">Interview prep</button>
            <button class="tab" type="button" data-tab="history">Recent analyses</button>
          </div>
          <div data-tab-panel="insights">
            <p class="eyebrow">Strengths</p>
            ${listHTML(advisor?.strengths || [])}
            <div class="divider"></div>
            <p class="eyebrow">Improvements</p>
            ${listHTML(advisor?.improvements || [], { check: false })}
          </div>
          <div data-tab-panel="recommendations" hidden>${recommendationCards(advisor, analysis)}</div>
          <div data-tab-panel="interview" hidden>${interviewPanel(interview)}</div>
          <div data-tab-panel="history" hidden>${historyPanel(state, actions)}</div>
        </article>
      </div>`;

    activateBars(container);
    qsa(".tabs", container).forEach((group) => initTabs(group));
    qsa("[data-history]", container).forEach((button) =>
      button.addEventListener("click", () => actions.openHistory(Number(button.dataset.history))));
  }

  function metric(iconName, label, value, note) {
    return `
      <article class="metric">
        <span>${icon(iconName)} ${escapeHtml(label)}</span>
        <strong title="${escapeHtml(value)}">${escapeHtml(value)}</strong>
        ${note ? `<small>${escapeHtml(note)}</small>` : ""}
      </article>`;
  }

  function recommendationCards(advisor, analysis) {
    const a = advisor || {};
    const cards = [
      { emoji: "🎯", title: "Skills to learn", items: a.skill_recommendations },
      { emoji: "📄", title: "Resume improvements", items: [...(a.improvements || []), ...(a.ats_suggestions || [])] },
      { emoji: "💼", title: "Experience gaps", items: a.weaknesses },
      { emoji: "🔑", title: "Keywords to add", items: (a.missing_keywords || []).length ? a.missing_keywords.map((keyword) => `Where truthful, connect your work to “${keyword}”.`) : [] },
      { emoji: "🚀", title: "Project suggestions", items: a.project_suggestions },
    ];
    return `
      <div class="source-note">${icon("info")} <span><strong>${escapeHtml(a.source || "Rule-based guidance")}</strong> — ${escapeHtml(a.notice || "")}</span></div>
      <div class="grid-2">
        ${cards.map((card) => `
          <article class="rec-card">
            <h3><span aria-hidden="true">${card.emoji}</span> ${escapeHtml(card.title)}</h3>
            ${listHTML(card.items, { check: true, empty: "Nothing identified in this category." })}
          </article>`).join("")}
      </div>`;
  }

  function interviewPanel(interview) {
    const groups = interview || {};
    const tabs = INTERVIEW_TABS.map((tab, index) => {
      const count = (groups[tab.key] || []).length;
      return `<button class="tab" type="button" data-tab="q-${tab.key}" ${index === 0 ? 'aria-selected="true"' : 'aria-selected="false"'}>${escapeHtml(tab.label)} (${count})</button>`;
    }).join("");
    const panels = INTERVIEW_TABS.map((tab, index) => {
      const questions = groups[tab.key] || [];
      const cards = questions.map((question, qIndex) => `
        <details class="question">
          <summary>
            <span class="q-index">Q${qIndex + 1}</span>
            <span class="q-text">${escapeHtml(question.question)}</span>
            <span class="badge badge-${tab.difficulty.toLowerCase()}">${tab.difficulty}</span>
            <svg class="icon chevron" aria-hidden="true"><use href="#i-arrow"/></svg>
          </summary>
          <div class="q-body">
            <p><strong>Why an interviewer may ask:</strong> ${escapeHtml(question.why_interviewer_may_ask)}</p>
            <p><strong>A strong answer covers:</strong> ${escapeHtml(question.strong_answer_should_cover)}</p>
          </div>
        </details>`).join("");
      return `<div data-tab-panel="q-${tab.key}" ${index === 0 ? "" : "hidden"}>${cards || `<p class="muted">No questions in this category.</p>`}</div>`;
    }).join("");
    return `
      <p class="muted">Difficulty badges are guidance levels estimated from the question category. Expand any card for coaching notes.</p>
      <div class="tabs" role="tablist" aria-label="Interview question categories">${tabs}</div>
      ${panels}`;
  }

  function historyPanel(state, actions) {
    const history = state.history || [];
    if (!history.length) return `<p class="muted">Analyses from this session will appear here.</p>`;
    return `
      <p class="muted">This session only — nothing is stored on the server.</p>
      ${history.map((entry, index) => `
        <div class="history-item">
          <span class="h-time">${icon("clock")} ${escapeHtml(entry.time)}</span>
          <span class="h-role">${escapeHtml(entry.role)}</span>
          <span class="badge badge-info">${fmtPct(entry.overall)}% match</span>
          <span class="badge badge-success">ATS ${fmtPct(entry.ats)}</span>
          <button class="btn btn-outline btn-sm" type="button" data-history="${index}">Open</button>
        </div>`).join("")}`;
  }

  return { renderResume, renderMatch, renderDashboard };
})();

window.VIEWS = VIEWS;
