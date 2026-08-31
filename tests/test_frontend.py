"""Static frontend integrity tests.

These run with the normal pytest suite (no browser needed) and catch the most
common SPA breakages: missing element IDs, dangling asset references, inline
styles blocked by the CSP, unknown icon references, and API URLs that do not
match backend routes.
"""

from __future__ import annotations

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
JS_FILES = ["ui.js", "api.js", "views.js", "app.js"]
JS = "\n".join((STATIC / "js" / name).read_text(encoding="utf-8") for name in JS_FILES)
CSS = (STATIC / "css" / "style.css").read_text(encoding="utf-8")
APP_PY = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")


def test_script_and_stylesheet_references_resolve():
    for reference in re.findall(r'(?:src|href)="(/static/[^"]+)"', HTML):
        assert (Path(__file__).resolve().parents[1] / reference.lstrip("/")).exists(), reference


def test_all_element_ids_referenced_by_js_exist():
    used = set(re.findall(r'(?:getElementById|byId)\(\s*"([^"]+)"', JS))
    defined_in_html = set(re.findall(r'id="([^"]+)"', HTML))
    created_in_js = set(re.findall(r'id="([^"]+)"', JS))
    missing = sorted(used - defined_in_html - created_in_js)
    assert not missing, f"JS references missing element IDs: {missing}"


def test_no_inline_styles_or_handlers_csp_compatible():
    """The backend CSP blocks inline style attributes and inline handlers."""
    assert not re.findall(r'style="', HTML), "index.html must not use inline style attributes"
    assert not re.findall(r'style="', JS), "JS templates must set styles via CSSOM, not style=\"\" attributes"
    for attribute in ("onclick=", "onchange=", "onsubmit=", "onload=", "onerror="):
        assert attribute not in HTML, f"index.html must not use inline {attribute} handlers"


def test_api_urls_match_backend_routes():
    routes = set(re.findall(r'@app\.(?:get|post)\("([^"]+)"', APP_PY))
    referenced = set(re.findall(r'["\'](/api/[a-z]+)["\']', JS))
    assert referenced <= routes, f"JS calls unknown API routes: {referenced - routes}"


def test_icon_references_exist_in_sprite():
    sprite_symbols = set(re.findall(r'<symbol id="i-([a-z-]+)"', HTML))
    used = set(re.findall(r'#i-([a-z-]+)', HTML + JS))
    # Names built dynamically via the icon()/metric() helpers with literal args.
    used |= set(re.findall(r'\bicon\("([a-z-]+)"\)', JS))
    used |= set(re.findall(r'\bmetric\("([a-z-]+)"', JS))
    used |= set(re.findall(r'iconName = "([a-z-]+)"', JS))
    missing = sorted(name for name in used if name not in sprite_symbols)
    assert not missing, f"Icon references missing from sprite: {missing}"


def test_view_routing_css_rules_exist():
    for rule in (".view {", ".view.active {"):
        assert rule in CSS, f"style.css must define {rule}"
    assert "[hidden]" in CSS


def test_component_classes_used_by_js_exist_in_css():
    for cls in (
        "chip-match", "chip-gap", "chip-neutral", "bar-fill", "bar-row",
        "toast", "toast-success", "toast-error", "metric", "metrics-grid",
        "rec-card", "gap-card", "question", "compare-table", "compare-ok",
        "compare-miss", "empty-state", "skeleton", "score-ring", "ring-fill",
        "tab", "history-item", "badge-easy", "badge-medium", "badge-hard",
        "source-note", "list-check", "list-warn", "notice-info", "status-line",
        "field-error", "dropzone", "progress-track", "spinner",
    ):
        assert f".{cls}" in CSS, f"style.css is missing the .{cls} component class"


def test_every_view_section_has_a_route_and_nav_link():
    views = set(re.findall(r'data-route="([a-z]+)"', HTML))
    nav_links = set(re.findall(r'class="nav-link" data-route="([a-z]+)"', HTML))
    assert views == {"home", "analyze", "resume", "match", "dashboard", "about"}
    assert nav_links == views - {"analyze"}  # analyze is reached via the CTA


def test_escaping_helper_is_used_for_user_data():
    assert "function escapeHtml" in JS
    assert JS.count("escapeHtml(") >= 20, "escapeHtml should be applied throughout rendered templates"
    # Raw API/state objects must never be assigned straight into the DOM.
    for forbidden in ("innerHTML = analysis", "innerHTML = payload", "innerHTML = result.data", "innerHTML = JSON.stringify"):
        assert forbidden not in JS
