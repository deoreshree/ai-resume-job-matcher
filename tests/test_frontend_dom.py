"""Optional DOM integration tests via jsdom (run when Node + jsdom are available).

The harness in tests/frontend/dom-test.js loads the real index.html plus the
real JS bundle into a simulated browser, stubs fetch/XHR, and drives the full
user journey (upload → analyze → dashboard → match → report → error paths).

Install once to enable:  cd tests/frontend && npm install jsdom
(Already exercised during development; skipped automatically otherwise.)
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND_DIR = Path(__file__).parent / "frontend"
HARNESS = FRONTEND_DIR / "dom-test.js"


def _jsdom_available() -> bool:
    node = shutil.which("node")
    if not node or not HARNESS.exists():
        return False
    try:
        probe = subprocess.run(
            ["node", "-e", "require.resolve('jsdom')"],
            cwd=FRONTEND_DIR, capture_output=True, timeout=60,
        )
        return probe.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


pytestmark = pytest.mark.skipif(not _jsdom_available(), reason="node + jsdom not installed (cd tests/frontend && npm install jsdom)")


def test_dom_integration_suite():
    result = subprocess.run(
        ["node", HARNESS.name],
        cwd=FRONTEND_DIR, capture_output=True, text=True, timeout=300,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"DOM integration suite failed:\n{output[-4000:]}"
    assert "passed, 0 failed" in output
