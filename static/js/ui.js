/* Shared UI components and helpers (no application logic).
   Convention: dynamic visual values (bar widths, ring offsets) are applied
   via CSSOM (el.style.*) because the backend CSP blocks inline style attrs. */
"use strict";

const byId = (id) => document.getElementById(id);
const qs = (selector, scope = document) => scope.querySelector(selector);
const qsa = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

/** Escape any value before inserting into HTML template strings. */
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

const icon = (name, cls = "icon") => `<svg class="${cls}" aria-hidden="true"><use href="#i-${name}"/></svg>`;
const fmtPct = (value) => Math.round(Number(value || 0));
const fmtNum = (value, digits = 1) => Number(value || 0).toFixed(digits);

function fmtBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const power = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** power).toFixed(power >= 2 ? 1 : 0)} ${units[power]}`;
}

/** Deterministic tone for a 0-100 score: success / warn / danger. */
function toneFor(score) {
  if (score >= 75) return "success";
  if (score >= 50) return "warn";
  return "danger";
}

/* ---------------- Toasts ---------------- */
function showToast(message, type = "info", timeoutMs = 4600) {
  const region = byId("toast-region");
  if (!region) return;
  const iconName = type === "success" ? "check" : type === "error" ? "alert" : "info";
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.setAttribute("role", type === "error" ? "alert" : "status");
  toast.innerHTML = `${icon(iconName)}<span>${escapeHtml(message)}</span>`;
  const dismiss = () => {
    toast.classList.add("leaving");
    setTimeout(() => toast.remove(), 240);
  };
  toast.addEventListener("click", dismiss);
  region.append(toast);
  if (timeoutMs > 0) setTimeout(dismiss, timeoutMs);
  return toast;
}

/* ---------------- Progress ring (SVG) ---------------- */
const RING_CIRCUMFERENCE = 2 * Math.PI * 52; // r = 52

/**
 * Build an accessible animated score ring.
 * Returns { wrap, set } where set(percent) animates the arc via CSSOM.
 */
function createScoreRing({ size = 170, label = "" } = {}) {
  const wrap = document.createElement("div");
  wrap.className = "score-ring-wrap";
  wrap.innerHTML = `
    <svg class="score-ring" viewBox="0 0 120 120" role="progressbar" aria-label="${escapeHtml(label)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
      <circle class="ring-track" cx="60" cy="60" r="52"></circle>
      <circle class="ring-fill tone-brand" cx="60" cy="60" r="52" stroke-dasharray="${RING_CIRCUMFERENCE}" stroke-dashoffset="${RING_CIRCUMFERENCE}"></circle>
    </svg>
    <div class="score-ring-label"><strong>–</strong><span>${escapeHtml(label)}</span></div>`;
  const fill = qs(".ring-fill", wrap);
  const strong = qs("strong", wrap);
  const svg = qs("svg", wrap);
  if (size !== 170) svg.setAttribute("width", size), svg.setAttribute("height", size);
  const set = (percent, { animate = true } = {}) => {
    const pct = Math.max(0, Math.min(100, fmtPct(percent)));
    const tone = toneFor(pct);
    svg.setAttribute("aria-valuenow", String(pct));
    fill.classList.remove("tone-success", "tone-warn", "tone-danger", "tone-brand");
    fill.classList.add(`tone-${tone}`);
    strong.textContent = `${pct}%`;
    const offset = RING_CIRCUMFERENCE * (1 - pct / 100);
    requestAnimationFrame(() => { fill.style.strokeDashoffset = String(offset); });
    if (!animate) fill.style.transition = "none";
    return pct;
  };
  return { wrap, set };
}

/** Apply a width to a bar fill via CSSOM so the CSS transition animates it. */
function setBarWidth(fillEl, percent) {
  if (!fillEl) return;
  const pct = Math.max(0, Math.min(100, Number(percent) || 0));
  requestAnimationFrame(() => { fillEl.style.width = `${pct}%`; });
}

/** Standard labelled progress bar row (label ..... value% + track). */
function barRow(label, value, { tone = null, caption = null } = {}) {
  const pct = fmtPct(value);
  const toneClass = tone ? `tone-${tone}` : "";
  return `
    <div class="bar-row">
      <div class="bar-head"><span>${escapeHtml(label)}</span><span>${pct}%</span></div>
      <div class="bar" role="progressbar" aria-label="${escapeHtml(label)}" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
        <span class="bar-fill ${toneClass}" data-width="${pct}"></span>
      </div>
      ${caption ? `<p class="muted">${escapeHtml(caption)}</p>` : ""}
    </div>`;
}

/** Activate every [data-width] bar fill inside a container (CSSOM widths). */
function activateBars(scope) {
  qsa(".bar-fill[data-width]", scope).forEach((el) => setBarWidth(el, el.dataset.width));
}

/* ---------------- Chips / badges / lists ---------------- */
function chipList(items, variant = "neutral", { empty = "None identified", withIcon = false } = {}) {
  const list = (items || []).filter((item) => item !== null && item !== undefined && item !== "");
  if (!list.length) return `<span class="chip chip-neutral">${escapeHtml(empty)}</span>`;
  const iconName = variant === "match" ? "check" : variant === "gap" ? "alert" : null;
  return `<div class="chips">${list.map((item) =>
    `<span class="chip chip-${variant}">${withIcon && iconName ? icon(iconName) : ""}${escapeHtml(item)}</span>`
  ).join("")}</div>`;
}

function listHTML(items, { check = true, empty = "No items identified." } = {}) {
  const list = (items || []).filter(Boolean);
  if (!list.length) return `<p class="muted">${escapeHtml(empty)}</p>`;
  return `<ul class="${check ? "list-check" : "list-warn"}">${list.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

/* ---------------- Tabs (accessible) ---------------- */
/**
 * Wire one tab group. Pass the `.tabs` element; panels are the *direct*
 * children of its parent that carry [data-tab-panel]. Scoping to direct
 * children lets tab groups nest (e.g. interview categories inside a panel).
 */
function initTabs(tabsElement, { onChange = null } = {}) {
  if (!tabsElement) return null;
  const tabs = qsa(".tab", tabsElement).filter((tab) => tab.dataset.tab);
  if (!tabs.length) return null;
  const scope = tabsElement.parentElement;
  tabsElement.setAttribute("role", "tablist");

  const panels = () => qsa(":scope > [data-tab-panel]", scope);
  const select = (target, focus = false) => {
    tabs.forEach((tab) => {
      const selected = tab.dataset.tab === target;
      tab.setAttribute("aria-selected", selected ? "true" : "false");
      tab.tabIndex = selected ? 0 : -1;
      if (focus && selected) tab.focus({ preventScroll: true });
    });
    panels().forEach((panel) => { panel.hidden = panel.dataset.tabPanel !== target; });
    if (onChange) onChange(target);
  };

  tabs.forEach((tab, index) => {
    tab.setAttribute("role", "tab");
    tab.tabIndex = -1;
    tab.addEventListener("click", () => select(tab.dataset.tab));
    tab.addEventListener("keydown", (event) => {
      const keys = { ArrowRight: 1, ArrowLeft: -1, Home: "first", End: "last" };
      if (!(event.key in keys)) return;
      event.preventDefault();
      let nextIndex = index;
      if (keys[event.key] === "first") nextIndex = 0;
      else if (keys[event.key] === "last") nextIndex = tabs.length - 1;
      else nextIndex = (index + keys[event.key] + tabs.length) % tabs.length;
      select(tabs[nextIndex].dataset.tab, true);
    });
  });
  panels().forEach((panel) => panel.setAttribute("role", "tabpanel"));

  const initial = tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
  select(initial.dataset.tab);
  return { select };
}

/* ---------------- Empty states / skeletons ---------------- */
function emptyStateHTML({ title, text, ctaHash = "#/analyze", ctaLabel = "Analyze your resume", iconName = "file" }) {
  return `
    <div class="empty-state">
      ${icon(iconName)}
      <h2>${escapeHtml(title)}</h2>
      <p>${escapeHtml(text)}</p>
      <a class="btn btn-primary" href="${escapeHtml(ctaHash)}">${escapeHtml(ctaLabel)}</a>
    </div>`;
}

function skeletonGrid(count = 4) {
  return `<div class="skeleton-grid">${'<div class="skeleton"></div>'.repeat(count)}</div>`;
}

/* ---------------- Buttons helpers ---------------- */
function setButtonBusy(button, busy, { busyLabel = "Working…" } = {}) {
  if (!button) return;
  const spinner = qs(".spinner", button);
  const label = qs(".btn-label > span:last-child, .js-report-label, span:not(.spinner)", button);
  if (busy) {
    button.dataset.originalLabel = (label && label.textContent) || button.textContent.trim();
    button.disabled = true;
    if (spinner) spinner.hidden = false;
    if (label && button.dataset.originalLabel) label.textContent = busyLabel;
  } else {
    button.disabled = false;
    if (spinner) spinner.hidden = true;
    if (label && button.dataset.originalLabel) label.textContent = button.dataset.originalLabel;
  }
}

function showFieldError(element, message) {
  if (!element) return;
  element.textContent = message || "";
  element.hidden = !message;
}

function setStatus(element, message) {
  if (!element) return;
  element.textContent = message || "";
  element.hidden = !message;
}

window.UI = { byId, qs, qsa, escapeHtml, icon, fmtPct, fmtNum, fmtBytes, toneFor, showToast, createScoreRing, setBarWidth, barRow, activateBars, chipList, listHTML, initTabs, emptyStateHTML, skeletonGrid, setButtonBusy, showFieldError, setStatus };
