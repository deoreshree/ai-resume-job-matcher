/* Application controller: routing, shared state, upload flow, report download.
   Depends on ui.js, api.js, views.js (loaded first via defer). */
"use strict";

(() => {
  const { byId, qs, qsa, escapeHtml, icon, showToast, setButtonBusy, showFieldError, setStatus, toneFor } = window.UI;
  const API_REF = window.API;

  const ROUTES = ["home", "analyze", "resume", "match", "dashboard", "about"];
  const state = {
    route: "home",
    file: null,          // currently selected File (kept in memory for job matching)
    analysis: null,      // latest successful analysis payload
    roles: [],
    history: [],         // in-memory session history: { time, role, overall, ats, analysis }
    busy: false,
  };

  /* ---------------- Router ---------------- */

  function currentRoute() {
    const raw = (location.hash || "#/home").replace(/^#\/?/, "").split("?")[0];
    return ROUTES.includes(raw) ? raw : "home";
  }

  function navigate(route) {
    if (location.hash !== `#/${route}`) location.hash = `#/${route}`;
    else renderRoute();
  }

  function renderRoute() {
    const route = currentRoute();
    state.route = route;

    qsa(".view").forEach((view) => view.classList.toggle("active", view.dataset.route === route));
    qsa(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.route === route));
    closeMobileMenu();
    byId("nav-report").hidden = !state.analysis;

    try {
      if (route === "resume") window.VIEWS.renderResume(byId("resume-content"), ctx());
      if (route === "match") window.VIEWS.renderMatch(byId("match-results"), ctx());
      if (route === "dashboard") window.VIEWS.renderDashboard(byId("dashboard-content"), ctx());
    } catch (error) {
      console.error("Failed to render view:", error);
      showToast("Something went wrong while displaying the results. Please refresh the page.", "error");
    }

    window.scrollTo({ top: 0, behavior: "auto" });
  }

  const ctx = () => ({ state, actions: { navigate, openHistory, downloadReport } });

  /* ---------------- Mobile nav ---------------- */

  function closeMobileMenu() {
    const menu = byId("nav-menu");
    const toggle = byId("nav-toggle");
    menu.classList.remove("open");
    toggle.setAttribute("aria-expanded", "false");
  }

  function wireNav() {
    byId("nav-toggle").addEventListener("click", () => {
      const menu = byId("nav-menu");
      const open = menu.classList.toggle("open");
      byId("nav-toggle").setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeMobileMenu(); });
    qsa(".nav-link, .brand, .nav-cta").forEach((link) => link.addEventListener("click", closeMobileMenu));
    byId("nav-report").addEventListener("click", downloadReport);
    qsa(".js-report").forEach((button) => button.addEventListener("click", downloadReport));
  }

  /* ---------------- Roles ---------------- */

  async function loadRoles() {
    const select = byId("job-role");
    const result = await API_REF.fetchRoles();
    if (result.ok) {
      state.roles = result.roles;
      select.innerHTML = state.roles.map((role) => `<option value="${escapeHtml(role.title)}">${escapeHtml(role.title)}</option>`).join("");
      if (!state.roles.length) select.innerHTML = '<option value="">No roles configured</option>';
    } else {
      select.innerHTML = '<option value="">Roles unavailable</option>';
      showToast("Job roles could not be loaded. Refresh the page to retry.", "error");
    }
  }

  /* ---------------- Upload / dropzone ---------------- */

  function acceptedFile(file) {
    const error = API_REF.validateFile(file?.name, file?.size);
    return error ? null : file;
  }

  function showFileCard(file) {
    const dropzone = byId("dropzone");
    byId("dropzone-idle").hidden = true;
    byId("file-card").hidden = false;
    byId("file-name").textContent = file.name;
    byId("file-name").title = file.name;
    byId("file-size").textContent = window.UI.fmtBytes(file.size);
    byId("file-ready").hidden = false;
    dropzone.dataset.state = "ready";
    showFieldError(byId("file-error"), null);
  }

  function clearFile({ silent = false } = {}) {
    state.file = null;
    byId("resume-input").value = "";
    byId("dropzone-idle").hidden = false;
    byId("file-card").hidden = true;
    byId("dropzone").dataset.state = "idle";
    showFieldError(byId("file-error"), null);
    if (!silent) setStatus(byId("analyze-status"), "");
  }

  function setFile(file) {
    const validationError = API_REF.validateFile(file?.name, file?.size);
    if (validationError) {
      state.file = null;
      byId("dropzone").dataset.state = "error";
      showFieldError(byId("file-error"), validationError);
      showToast(validationError, "error");
      return;
    }
    state.file = file;
    showFileCard(file);
  }

  function wireDropzone() {
    const input = byId("resume-input");
    const dropzone = byId("dropzone");

    input.addEventListener("change", () => { if (input.files[0]) setFile(input.files[0]); });
    qs("#dropzone-idle").addEventListener("click", () => input.click());
    qs("#dropzone-idle").addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); input.click(); }
    });
    byId("file-remove").addEventListener("click", () => clearFile());

    ["dragenter", "dragover"].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      if (!state.file) dropzone.dataset.state = "drag";
    }));
    ["dragleave", "drop"].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      if (!state.file) dropzone.dataset.state = "idle";
    }));
    dropzone.addEventListener("drop", (event) => {
      const file = event.dataTransfer?.files?.[0];
      if (file) setFile(file);
    });

    // Keep the whole page from navigating on stray drops.
    ["dragover", "drop"].forEach((eventName) => window.addEventListener(eventName, (event) => {
      if (!dropzone.contains(event.target)) event.preventDefault();
    }));
  }

  /* ---------------- Analysis pipeline ---------------- */

  const ANALYZE_STEPS = ["upload", "parse", "match", "insight"];
  let stepTimer = null;

  function setStep(activeStep) {
    qsa("#analysis-steps li").forEach((item) => {
      const index = ANALYZE_STEPS.indexOf(item.dataset.step);
      const activeIndex = ANALYZE_STEPS.indexOf(activeStep);
      item.classList.toggle("active", item.dataset.step === activeStep);
      item.classList.toggle("done", index < activeIndex);
    });
  }

  function startStepTicker() {
    // Upload completes against real progress; later phases are fast server work,
    // so cycle the indicator to show continuous activity.
    let index = 1;
    const messages = ["Extracting skills & experience…", "Matching against the target…", "Preparing recommendations…"];
    setStatus(byId("analyze-status"), messages[0]);
    stepTimer = setInterval(() => {
      setStep(ANALYZE_STEPS[Math.min(index + 1, ANALYZE_STEPS.length - 1)]);
      setStatus(byId("analyze-status"), messages[Math.min(index, messages.length - 1)]);
      index = Math.min(index + 1, messages.length - 1);
    }, 1300);
  }

  function stopStepTicker(completed = false) {
    if (stepTimer) clearInterval(stepTimer);
    stepTimer = null;
    if (completed) qsa("#analysis-steps li").forEach((item) => { item.classList.add("done"); item.classList.remove("active"); });
  }

  function resetAnalyzeUi() {
    byId("upload-progress").hidden = true;
    window.UI.setBarWidth(byId("upload-bar"), 0);
    stopStepTicker();
    setStatus(byId("analyze-status"), "");
    setStep("upload");
    setButtonBusy(byId("analyze-button"), false);
  }

  async function runAnalysis({ file, mode, role, jobDescription, button, errorEl, statusEl, destination = "dashboard" }) {
    if (state.busy) return;
    state.busy = true;

    const validationError = API_REF.validateFile(file?.name, file?.size);
    if (validationError) {
      showFieldError(errorEl, validationError);
      showToast(validationError, "error");
      state.busy = false;
      return;
    }
    if (mode === "custom" && (jobDescription || "").trim().length < API_REF.MIN_JD_LENGTH) {
      const message = `Paste a fuller job description (at least ${API_REF.MIN_JD_LENGTH} characters).`;
      showFieldError(errorEl, message);
      showToast(message, "error");
      state.busy = false;
      return;
    }

    showFieldError(errorEl, null);
    setButtonBusy(button, true, { busyLabel: "Analyzing…" });
    byId("upload-progress").hidden = false;
    setStep("upload");

    const result = await API_REF.analyzeResume({
      file, mode, role, jobDescription,
      onUploadProgress: (percent) => {
        window.UI.setBarWidth(byId("upload-bar"), percent);
        if (percent >= 100) { setStep("parse"); startStepTicker(); }
      },
    });

    state.busy = false;
    stopStepTicker(true);
    setButtonBusy(button, false);
    setStatus(statusEl, "");
    byId("upload-progress").hidden = true;
    window.UI.setBarWidth(byId("upload-bar"), 0);

    if (!result.ok) {
      byId("dropzone").dataset.state = state.file ? "ready" : "idle";
      showFieldError(errorEl, result.error);
      showToast(result.error, "error", 6500);
      stopStepTicker();
      setStep("upload");
      return;
    }

    state.analysis = result.analysis;
    state.file = file;
    recordHistory(result.analysis);
    if (mode === "custom") byId("match-jd").value = jobDescription || "";
    updateMatchFileNote();
    showToast("Analysis complete — explore your results.", "success");
    setTimeout(() => { resetAnalyzeUi(); navigate(destination); }, 450);
  }

  function recordHistory(analysis) {
    const entry = {
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      role: analysis.job_profile?.title || "Custom role",
      overall: analysis.match?.overall_score || 0,
      ats: analysis.ats?.score || 0,
      analysis,
    };
    state.history.unshift(entry);
    state.history = state.history.slice(0, 6);
  }

  function openHistory(index) {
    const entry = state.history[index];
    if (!entry) return;
    state.analysis = entry.analysis;
    navigate("dashboard");
    showToast(`Showing analysis for ${entry.role}.`, "info");
  }

  /* ---------------- Forms ---------------- */

  function targetMode() {
    return qs('input[name="target_mode"]:checked')?.value || "role";
  }

  function wireAnalyzeForm() {
    qsa('input[name="target_mode"]').forEach((radio) => radio.addEventListener("change", () => {
      const custom = targetMode() === "custom";
      byId("role-control").hidden = custom;
      byId("custom-control").hidden = !custom;
    }));

    byId("analysis-form").addEventListener("submit", (event) => {
      event.preventDefault();
      runAnalysis({
        file: state.file || byId("resume-input").files[0],
        mode: targetMode(),
        role: byId("job-role").value,
        jobDescription: byId("job-description").value.trim(),
        button: byId("analyze-button"),
        errorEl: byId("file-error"),
        statusEl: byId("analyze-status"),
      });
    });
  }

  function wireMatchForm() {
    byId("match-jd").addEventListener("input", (event) => { state.lastJd = event.target.value; });
    byId("match-form").addEventListener("submit", (event) => {
      event.preventDefault();
      runAnalysis({
        file: state.file || byId("resume-input").files[0],
        mode: "custom",
        jobDescription: byId("match-jd").value.trim(),
        button: byId("match-button"),
        errorEl: byId("match-error"),
        statusEl: byId("match-status"),
        destination: "match",
      });
    });
  }

  function updateMatchFileNote() {
    const note = byId("match-file-note");
    if (!note) return;
    note.textContent = state.file
      ? `Using ${state.file.name} from your latest analysis.`
      : "Upload a resume first — this matcher reuses your selected file.";
  }

  /* ---------------- Report ---------------- */

  async function downloadReport(event) {
    if (event) event.preventDefault();
    if (!state.analysis) {
      showToast("Run an analysis first — the report needs current results.", "error");
      return;
    }
    const button = (event && event.currentTarget instanceof HTMLElement) ? event.currentTarget : qs("#view-dashboard .js-report");
    setButtonBusy(button, true, { busyLabel: "Generating report…" });
    const result = await API_REF.requestReport(state.analysis);
    setButtonBusy(button, false);

    if (!result.ok) {
      showToast(result.error, "error", 6500);
      return;
    }
    try {
      const url = URL.createObjectURL(result.blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = result.filename;
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      showToast("Report generated successfully.", "success");
      const label = qs(".js-report-label", button);
      if (label) { label.textContent = "Report generated successfully"; setTimeout(() => { label.textContent = "Download Analysis Report"; }, 2600); }
    } catch (error) {
      console.error(error);
      showToast("The report could not be saved by your browser.", "error");
    }
  }

  /* ---------------- Boot ---------------- */

  function boot() {
    wireNav();
    wireDropzone();
    wireAnalyzeForm();
    wireMatchForm();
    updateMatchFileNote();
    loadRoles();
    window.addEventListener("hashchange", renderRoute);
    window.addEventListener("error", (event) => console.error("Unexpected error:", event.error || event.message));
    window.addEventListener("unhandledrejection", (event) => {
      console.error("Unexpected rejection:", event.reason);
      event.preventDefault();
    });
    renderRoute();
  }

  document.addEventListener("DOMContentLoaded", boot);
  window.APP = { state, navigate };
})();
