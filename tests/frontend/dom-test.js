/* DOM integration test: loads the real index.html + JS bundle into jsdom,
   stubs fetch/XHR, and drives the full user journey a browser would take. */
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const REPO = "/home/user/ai-resume-job-matcher";

/* Inline the deferred scripts (same order) so jsdom executes them without network. */
function buildHtml() {
  let html = fs.readFileSync(path.join(REPO, "static/index.html"), "utf8");
  html = html.replace(/<link rel="stylesheet"[^>]*>/, "");
  for (const file of ["ui.js", "api.js", "views.js", "app.js"]) {
    const code = fs.readFileSync(path.join(REPO, "static/js", file), "utf8");
    html = html.replace(`<script src="/static/js/${file}" defer></script>`, `<script>\n${code}\n</script>`);
  }
  if (html.includes('src="/static/js/')) throw new Error("a script was not inlined");
  return html;
}

/* ---------------- controlled stubs ---------------- */
let analyzeResponder = null; // (form) => { status, body }
let reportResponse = null;
let rolesResponse = null;

class FakeXHR {
  constructor() {
    this.uploadListeners = {};
    this.listeners = {};
    this.timeout = 0;
    this.status = 0;
    this.responseText = "";
    this.upload = { addEventListener: (type, fn) => { (this.uploadListeners[type] ||= []).push(fn); } };
  }
  open(method, url) { this.url = url; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  _fire(map, type, event) { (map[type] || []).forEach((fn) => fn(event)); }
  send() {
    setTimeout(() => {
      [30, 100].forEach((pct) => this._fire(this.uploadListeners, "progress", { lengthComputable: true, loaded: pct, total: 100 }));
      const result = analyzeResponder ? analyzeResponder(this.url) : { status: 200, body: "{}" };
      setTimeout(() => {
        this.status = result.status;
        this.responseText = result.body;
        this._fire(this.listeners, "load", {});
      }, 30);
    }, 10);
  }
}

function jsonResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (name) => (name.toLowerCase() === "content-type" ? "application/json" : null) },
    text: async () => JSON.stringify(data),
    json: async () => data,
  };
}

/* ---------------- assertions ---------------- */
let passed = 0; const failures = [];
function check(name, condition, detail = "") {
  if (condition) { passed++; console.log(`  ✓ ${name}`); }
  else { failures.push(`${name} ${detail}`); console.log(`  ✗ ${name} ${detail}`); }
}
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function buildDom() {
  const dom = new JSDOM(buildHtml(), {
    runScripts: "dangerously",
    pretendToBeVisual: true,
    url: "http://localhost/",
  });
  const { window } = dom;
  window.XMLHttpRequest = FakeXHR;
  window.URL.createObjectURL = () => "blob:fake-url";
  window.URL.revokeObjectURL = () => {};
  window.fetch = async (url, options = {}) => {
    if (String(url).includes("/api/roles")) {
      if (rolesResponse) return rolesResponse;
      return jsonResponse({ roles: [{ title: "Data Scientist" }, { title: "DevOps Engineer" }] });
    }
    if (String(url).includes("/api/report")) {
      return reportResponse || { ok: true, status: 200, headers: { get: () => "attachment; filename=resume-match-report-Test.html" }, blob: async () => ({ size: 100 }) };
    }
    return jsonResponse({ error: "unknown route" }, 404);
  };
  window.scrollTo = () => {};
  if (window.document.readyState !== "complete") await new Promise((resolve) => window.addEventListener("load", resolve));
  else await sleep(50);
  return dom;
}

const SAMPLE_ANALYSIS = (() => {
  const resume = {
    name: "John Doe", email: "john.doe@email.com", phone: "+1 415 555 0199", linkedin: null, github: "github.com/johndoe", portfolio: null,
    education: [{ degree: "B.Tech", institution: "State Institute of Technology", year: "2022", raw: "B.Tech" }],
    skills: ["Python", "Machine Learning", "Pandas"], skill_details: { by_category: { Programming: ["Python"], "AI/ML": ["Machine Learning"] } },
    experience: [{ title: "ML Engineer", organization: "Acme", duration: "Jan 2022 - Present", responsibilities: ["Built models"] }],
    projects: [{ title: "Churn Predictor", description: "Trained a model", technologies: ["Python"] }],
    certifications: ["AWS Cloud Practitioner"], achievements: ["Dean's list"], keywords: ["Python"], years_experience: 4.5,
  };
  const job_profile = { title: "Data Scientist", required_skills: ["Python", "SQL"], preferred_skills: ["Docker"], keywords: ["predictive models", "data analysis"], education: ["Bachelor's"], minimum_experience: 1, technologies: ["Python"], source: "predefined" };
  const match = {
    overall_score: 72.5, components: { skills: 75, semantic: 62, experience: 100, education: 100, keywords: 40 }, weights: { skills: 0.4, semantic: 0.25, experience: 0.15, education: 0.1, keywords: 0.1 },
    contributions: {}, explanation: [], semantic_method: "TF-IDF cosine similarity", semantic_similarity: 62, experience_score: 100, education_score: 100,
    skill_match: { matching_skills: ["Python"], required_matches: ["Python"], preferred_matches: [], missing_required: ["SQL"], missing_preferred: ["Docker"], missing_skills: ["SQL", "Docker"], skill_gaps: [{ skill: "SQL", importance: "High", reason: "required" }, { skill: "Docker", importance: "Medium", reason: "preferred" }], required_coverage: 0.5, preferred_coverage: 0, score: 50 },
    keyword_match: { matched_keywords: ["predictive models"], missing_keywords: ["data analysis"], coverage: 0.5, score: 50 },
  };
  const ats = { score: 81, components: { keywords: 50, structure: 100, skills: 50, readability: 92, formatting: 85 }, issues: [], recommendations: ["Use standard headings."], detected_sections: ["experience", "education"], missing_sections: ["summary"] };
  const insights = { strengths: ["Solid Python evidence."], weaknesses: ["No evidence of SQL was found in the resume."], improvements: ["Consider learning SQL."], missing_keywords: ["data analysis"], skill_recommendations: ["SQL: practice joins."], project_suggestions: ["Quantify the churn project."], ats_suggestions: [] };
  const advisor = { ...insights, source: "Rule-based guidance", notice: "Add OPENAI_API_KEY to .env to enable optional AI-written advice." };
  const interview = {
    technical_questions: [{ question: "How have you used Python?", why_interviewer_may_ask: "Python appears in the analysis.", strong_answer_should_cover: "A real context." }],
    project_questions: [], hr_questions: [], scenario_questions: [{ question: "A requirement is ambiguous — what do you do?", why_interviewer_may_ask: "Judgement.", strong_answer_should_cover: "Clarify, then act." }],
  };
  return { resume, job_profile, match, ats, insights, advisor, interview };
})();

(async () => {
  console.log("\n— boot —");
  const dom = await buildDom();
  const { window } = dom;
  const doc = window.document;
  const $ = (sel, scope = doc) => scope.querySelector(sel);
  const $$ = (sel, scope = doc) => Array.from(scope.querySelectorAll(sel));
  await sleep(80);

  check("landing view visible on load", $("#view-home").classList.contains("active"));
  check("roles loaded into selector", $("#job-role").options.length === 2 && $("#job-role").options[0].value === "Data Scientist");
  check("report button hidden before analysis", $("#nav-report").hidden === true);

  console.log("\n— mobile nav —");
  $("#nav-toggle").dispatchEvent(new window.Event("click", { bubbles: true }));
  check("hamburger opens menu", $("#nav-menu").classList.contains("open") && $("#nav-toggle").getAttribute("aria-expanded") === "true");
  $("#nav-toggle").dispatchEvent(new window.Event("click", { bubbles: true }));
  check("hamburger closes menu", !$("#nav-menu").classList.contains("open"));

  console.log("\n— navigation —");
  window.location.hash = "#/about";
  await sleep(30);
  check("hash routing switches views", $("#view-about").classList.contains("active") && !$("#view-home").classList.contains("active"));
  check("nav link active state", $('.nav-link[data-route="about"]').classList.contains("active"));
  window.location.hash = "#/dashboard";
  await sleep(30);
  check("dashboard shows empty state without analysis", !!$("#dashboard-content .empty-state"));

  console.log("\n— upload validation —");
  window.location.hash = "#/analyze";
  await sleep(30);
  const input = $("#resume-input");
  Object.defineProperty(input, "files", { value: [{ name: "resume.txt", size: 500 }], configurable: true });
  input.dispatchEvent(new window.Event("change", { bubbles: true }));
  check("invalid extension rejected", $("#file-error").hidden === false && /Unsupported/.test($("#file-error").textContent));
  check("dropzone shows error state", $("#dropzone").dataset.state === "error");

  Object.defineProperty(input, "files", { value: [new window.File(["x"], "resume.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" })], configurable: true });
  input.dispatchEvent(new window.Event("change", { bubbles: true }));
  await sleep(20);
  check("valid file shows ready card", $("#file-card").hidden === false && $("#file-name").textContent === "resume.docx" && $("#dropzone").dataset.state === "ready");
  check("file size rendered", /B$|KB|MB/.test($("#file-size").textContent));

  console.log("\n— analyze success flow —");
  analyzeResponder = () => ({ status: 200, body: JSON.stringify({ analysis: SAMPLE_ANALYSIS }) });
  $("#analysis-form").dispatchEvent(new window.Event("submit", { cancelable: true, bubbles: true }));
  await sleep(120);
  check("upload progress ran to 100%", $("#upload-bar").style.width === "100%" || window.APP.state.analysis);
  check("steps ticker advanced", $("#analysis-steps li[data-step='parse']").classList.contains("done") || $("#analysis-steps li[data-step='match']").classList.contains("active"));
  await sleep(650);
  check("analysis stored in state", window.APP.state.analysis && window.APP.state.analysis.match.overall_score === 72.5);
  check("auto-navigated to dashboard", window.location.hash === "#/dashboard" && $("#view-dashboard").classList.contains("active"));
  check("success toast shown", !!doc.querySelector(".toast-success"));
  check("metric cards rendered", $$("#dashboard-content .metric").length === 6);
  check("metrics contain no raw HTML leakage", $$("#dashboard-content .metric").every((m) => !m.textContent.includes("<span") && !m.textContent.includes("<")));
  check("nav report button now visible", $("#nav-report").hidden === false);
  check("ATS metric shows score", $$("#dashboard-content .metric").some((m) => m.textContent.includes("ATS") && m.textContent.includes("81")));

  console.log("\n— dashboard tabs (nested groups) —");
  const dashTabs = $$("#dash-tabs-card > .tabs .tab");
  check("four dashboard tabs", dashTabs.length === 4);
  const interviewTab = dashTabs.find((tab) => tab.dataset.tab === "interview");
  interviewTab.click();
  await sleep(20);
  const interviewPanel = $('#dash-tabs-card > [data-tab-panel="interview"]');
  const outerPanelsHidden = $$('#dash-tabs-card > [data-tab-panel]').filter((panel) => panel.hidden).length;
  check("interview panel visible, others hidden", !interviewPanel.hidden && outerPanelsHidden === 3);
  const subTabs = $$(":scope > .tabs .tab", interviewPanel);
  check("interview sub-tabs present", subTabs.length === 4 && subTabs[0].textContent.includes("Technical"));
  subTabs[3].click();
  await sleep(20);
  const scenarioPanel = $(':scope > [data-tab-panel="q-scenario_questions"]', interviewPanel);
  check("nested sub-tab switches panel", !scenarioPanel.hidden && scenarioPanel.textContent.includes("ambiguous"));
  const recTab = dashTabs.find((tab) => tab.dataset.tab === "recommendations");
  recTab.click();
  await sleep(20);
  check("recommendation cards rendered", $$('#dash-tabs-card > [data-tab-panel="recommendations"] .rec-card').length === 5);
  const historyTab = dashTabs.find((tab) => tab.dataset.tab === "history");
  historyTab.click();
  await sleep(20);
  check("history records the analysis", $('#dash-tabs-card > [data-tab-panel="history"]').textContent.includes("Data Scientist"));

  console.log("\n— resume analysis view —");
  window.location.hash = "#/resume";
  await sleep(40);
  check("ATS ring mounted with value", $("#ats-ring-mount svg") && $("#ats-ring-mount svg").getAttribute("aria-valuenow") === "81");
  check("ATS ring offset applied via CSSOM", $("#ats-ring-mount .ring-fill").style.strokeDashoffset !== "");
  check("component bars activated", $$("#ats-component-bars .bar-fill").every((bar) => bar.style.width.endsWith("%")));
  check("candidate contact rendered", $("#resume-content").textContent.includes("john.doe@email.com"));
  check("matched & missing skills chips", !!$("#resume-content .chip-match") && !!$("#resume-content .chip-gap"));
  check("strengths and improvements lists", $$("#resume-content .list-check li").length >= 1 && $$("#resume-content .list-warn li").length >= 1);

  console.log("\n— job match view —");
  window.location.hash = "#/match";
  await sleep(40);
  check("match ring rendered", $("#match-ring-mount svg") && $("#match-ring-mount svg").getAttribute("aria-valuenow") === "73");
  check("comparison table has rows", $$("#match-results .compare-table tbody tr").length >= 3);
  check("comparison shows evidence + gaps", !!$$("#match-results .compare-table .compare-ok").length && !!$$("#match-results .compare-table .compare-miss").length);
  const gapTab = $$("#match-results .tabs .tab").find((tab) => tab.dataset.tab === "gaps");
  gapTab.click();
  await sleep(20);
  check("gap bars + learning paths", !!$('#match-results [data-tab-panel="gaps"] .bar-fill') && $("#match-results").textContent.includes("practice joins"));
  check("file note shows resume name", $("#match-file-note").textContent.includes("resume.docx"));

  console.log("\n— custom JD re-analysis via match form —");
  analyzeResponder = () => {
    const custom = JSON.parse(JSON.stringify(SAMPLE_ANALYSIS));
    custom.job_profile = { ...custom.job_profile, title: "Custom ML Role", source: "custom", warnings: ["No skills from the catalog were recognised."] };
    return { status: 200, body: JSON.stringify({ analysis: custom }) };
  };
  $("#match-jd").value = "Machine Learning Engineer with Python, SQL, and Docker. 3+ years of experience. Bachelor's degree required.";
  $("#match-form").dispatchEvent(new window.Event("submit", { cancelable: true, bubbles: true }));
  await sleep(700);
  check("custom analysis applied", window.APP.state.analysis.job_profile.source === "custom");
  check("profile warning surfaced", $("#match-results").textContent.includes("No skills from the catalog"));
  check("history keeps both analyses", window.APP.state.history.length === 2);
  const openButtons = $$("#dashboard-content [data-history]");
  window.location.hash = "#/dashboard";
  await sleep(40);
  $$("#dashboard-content [data-history]")[1]?.click();
  await sleep(30);
  check("history restore works", window.APP.state.analysis.job_profile.title === "Data Scientist");

  console.log("\n— report download —");
  reportResponse = { ok: true, status: 200, headers: { get: () => "attachment; filename=resume-match-report-JohnDoe.html" }, blob: async () => ({ size: 9000 }) };
  $("#view-dashboard .js-report").click();
  await sleep(60);
  check("report success toast", $$(".toast").some((toast) => toast.textContent.includes("Report generated successfully")));

  console.log("\n— error handling —");
  reportResponse = { ok: false, status: 500, headers: { get: () => "application/json" }, text: async () => JSON.stringify({ error: "boom" }) };
  await sleep(3000); // let success toast clear
  $("#view-dashboard .js-report").click();
  await sleep(60);
  check("report failure surfaces error toast", $$(".toast").some((toast) => toast.textContent.includes("boom")));

  window.location.hash = "#/analyze";
  await sleep(30);
  analyzeResponder = () => ({ status: 400, body: JSON.stringify({ error: "The resume could not be read." }) });
  $("#analysis-form").dispatchEvent(new window.Event("submit", { cancelable: true, bubbles: true }));
  await sleep(120);
  check("400 error shown inline", $("#file-error").textContent.includes("could not be read"));
  check("error toast shown", $$(".toast-error").some((toast) => toast.textContent.includes("could not be read")));
  check("app did not navigate away", window.location.hash === "#/analyze");

  analyzeResponder = () => ({ status: 500, body: "<html><body>Internal Server Error</body></html>" }); // HTML, not JSON
  $("#analysis-form").dispatchEvent(new window.Event("submit", { cancelable: true, bubbles: true }));
  await sleep(120);
  check("HTML response handled gracefully", $$(".toast-error").some((toast) => /internal error|unexpected response/i.test(toast.textContent)));

  rolesResponse = jsonResponse({}, 200); // malformed roles payload
  await buildDom().then((d2) => d2.window.close()).catch(() => {});
  const dom3 = await (async () => { rolesResponse = { ok: false, status: 502, headers: { get: () => "text/html" }, text: async () => "<html>bad gateway</html>" }; return buildDom(); })();
  await sleep(120);
  check("roles failure degrades gracefully", dom3.window.document.querySelector("#job-role").textContent.includes("Roles unavailable") || dom3.window.document.querySelector("#job-role option").textContent.includes("Roles unavailable"));
  check("roles error toast shown", !!dom3.window.document.querySelector(".toast-error"));
  dom3.window.close();

  console.log(`\n========= ${passed} passed, ${failures.length} failed =========`);
  if (failures.length) { failures.forEach((failure) => console.log("FAILED:", failure)); process.exit(1); }
  dom.window.close();
  process.exit(0);
})().catch((error) => { console.error("TEST HARNESS ERROR:", error); process.exit(2); });
