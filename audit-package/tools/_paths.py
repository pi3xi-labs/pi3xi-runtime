"""Shared path setup for tools (adds src/ to sys.path)."""

import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent  # audit-package/
REPO_ROOT = PACKAGE_ROOT.parent
sys.path.insert(0, str(PACKAGE_ROOT / "src"))
