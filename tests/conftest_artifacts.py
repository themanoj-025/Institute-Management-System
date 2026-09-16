"""Test diagnostics for hard-to-reproduce CI failures.

These hooks are deliberately quiet when nothing unusual happens.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Matches coverage's numbered-copy artifacts (e.g. config-3.py): a module
# basename followed by "-<digits>.py" appearing in the project root.
_NUMBERED = re.compile(r"^[A-Za-z_]\w*-\d+\.py$")


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Log leftover numbered *.py artifacts so their creator is identifiable in CI."""
    leftovers = sorted(p.name for p in ROOT.glob("*.py") if _NUMBERED.match(p.name))
    if leftovers:
        print(f"\n=== leftover numbered *.py files after session: {leftovers} ===")
