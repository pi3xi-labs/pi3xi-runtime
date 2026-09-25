import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

FIXTURES = PACKAGE_ROOT / "fixtures"
BASELINE = FIXTURES / "baseline" / "baseline.json"


def success_files():
    return sorted((FIXTURES / "success").glob("*.json"))


def positive_files():
    return success_files() + [BASELINE]


@pytest.fixture
def baseline_bytes():
    return BASELINE.read_bytes()


def with_invariant(baseline: bytes, lexeme: str) -> bytes:
    """Splice an invariant lexeme into the baseline record bytes (no re-serialization)."""
    from pi3xi_audit.canonical import scan
    text = baseline.decode("utf-8")
    _, node, _ = scan(text)
    inv = dict(node.members)["invariant"]
    return (text[:inv.start] + lexeme + text[inv.end:]).encode("utf-8")


def code_of(fn, *args):
    from pi3xi_audit.errors import ValidationError
    try:
        fn(*args)
        return None
    except ValidationError as exc:
        return exc.code
