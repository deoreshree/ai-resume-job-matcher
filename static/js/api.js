/* API layer. Every call returns { ok, status, data, error, ... } and NEVER throws,
   so views can render a friendly message for any failure mode:
   network down, HTML instead of JSON, 4xx/5xx, timeouts, aborted requests. */
"use strict";

const API = (() => {
  const MAX_UPLOAD_MB = 8;                                     // mirrors config.MAX_UPLOAD_MB
  const ALLOWED_EXTENSIONS = [".pdf", ".docx"];                // mirrors config.ALLOWED_RESUME_EXTENSIONS
  const MIN_JD_LENGTH = 40;                                    // mirrors utils.validators

  const GENERIC_ERROR = "The request could not be completed. Please try again.";

  /** Human message for a response that was not JSON (e.g. an HTML error page). */
  function nonJsonError(status) {
    if (status >= 500) return "The server had an internal error while handling this request.";
    if (status === 404) return "The requested API route was not found on the server.";
    return "The server returned an unexpected response format. Please verify the backend is running correctly.";
  }

  /** Safely consume a fetch Response as { ok, status, data?, error? }. */
  async function safeFetch(url, options = {}, timeoutMs = 30000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    let response;
    try {
      response = await fetch(url, { ...options, signal: controller.signal });
    } catch (error) {
      if (error && error.name === "AbortError") return { ok: false, error: "The request timed out. Please try again." };
      return { ok: false, error: "Cannot reach the server. Check your connection and that the application is running." };
    } finally {
      clearTimeout(timer);
    }

    let text = "";
    try { text = await response.text(); } catch { /* body unreadable */ }

    let payload = null;
    try { payload = JSON.parse(text); } catch { payload = null; }
    if (payload === null || typeof payload !== "object") {
      return { ok: false, status: response.status, error: nonJsonError(response.status) };
    }
    if (!response.ok) {
      return { ok: false, status: response.status, error: payload.error || GENERIC_ERROR, data: payload };
    }
    return { ok: true, status: response.status, data: payload };
  }

  async function fetchRoles() {
    const result = await safeFetch("/api/roles", { method: "GET", headers: { Accept: "application/json" } }, 15000);
    if (!result.ok) return result;
    return { ok: true, roles: (result.data && result.data.roles) || [] };
  }

  /**
   * POST /api/analyze via XHR so real upload progress can be shown.
   * onUploadProgress(0-100) fires while the file is sent; afterwards the
   * caller can show an indeterminate "analyzing" state until the promise settles.
   */
  function analyzeResume({ file, mode, role, jobDescription, onUploadProgress }) {
    return new Promise((resolve) => {
      const form = new FormData();
      form.append("resume", file, file.name);
      form.append("target_mode", mode === "custom" ? "custom" : "role");
      form.append("job_role", role || "");
      form.append("job_description", jobDescription || "");

      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/analyze");
      xhr.timeout = 120000;
      xhr.responseType = "text";

      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable && typeof onUploadProgress === "function") {
          onUploadProgress(Math.round((event.loaded / event.total) * 100));
        }
      });

      const finish = (result) => resolve(result);

      xhr.addEventListener("load", () => {
        let payload = null;
        try { payload = JSON.parse(xhr.responseText); } catch { payload = null; }
        if (payload === null || typeof payload !== "object") return finish({ ok: false, status: xhr.status, error: nonJsonError(xhr.status) });
        if (xhr.status >= 200 && xhr.status < 300) return finish({ ok: true, status: xhr.status, analysis: payload.analysis });
        finish({ ok: false, status: xhr.status, error: payload.error || GENERIC_ERROR });
      });
      xhr.addEventListener("timeout", () => finish({ ok: false, error: "The analysis took too long and was cancelled. Please try again." }));
      xhr.addEventListener("abort", () => finish({ ok: false, error: "The upload was cancelled." }));
      xhr.addEventListener("error", () => finish({ ok: false, error: "Cannot reach the server. Check your connection and that the application is running." }));

      try { xhr.send(form); } catch (error) { finish({ ok: false, error: GENERIC_ERROR }); }
    });
  }

  /** POST /api/report — returns a Blob + suggested filename on success. */
  async function requestReport(analysis) {
    let response;
    try {
      response = await fetch("/api/report", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/html, application/json" },
        body: JSON.stringify({ analysis }),
      });
    } catch {
      return { ok: false, error: "Cannot reach the server. Check your connection and try again." };
    }

    const contentType = response.headers.get("Content-Type") || "";
    if (!response.ok) {
      let payload = null;
      if (contentType.includes("json")) {
        try { payload = JSON.parse(await response.text()); } catch { payload = null; }
      }
      return { ok: false, error: (payload && payload.error) || nonJsonError(response.status) };
    }
    try {
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const star = disposition.match(/filename\*=(?:UTF-8'')"?([^";]+)/i);
      const plain = disposition.match(/filename="?([^";]+)"?/i);
      const filename = (star && star[1]) || (plain && plain[1]) || "resume-match-report.html";
      return { ok: true, blob, filename: decodeURIComponent(filename) };
    } catch {
      return { ok: false, error: "The report could not be generated. Please try again." };
    }
  }

  return {
    MAX_UPLOAD_MB, ALLOWED_EXTENSIONS, MIN_JD_LENGTH,
    fetchRoles, analyzeResume, requestReport,
    validateFile(name, size) {
      const lower = (name || "").toLowerCase();
      if (!lower) return "Please choose a resume file first.";
      if (!ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))) {
        return `Unsupported file type. Please upload a ${ALLOWED_EXTENSIONS.join(" or ")} resume.`;
      }
      if (size > MAX_UPLOAD_MB * 1024 * 1024) {
        return `The resume is larger than ${MAX_UPLOAD_MB} MB. Please upload a smaller file.`;
      }
      if (size === 0) return "The selected file is empty. Please choose a valid resume.";
      return null;
    },
  };
})();

window.API = API;
