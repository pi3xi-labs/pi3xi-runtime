import pytest
from conftest import BASELINE, FIXTURES

from pi3xi_audit.canonical import sha256_hex
from pi3xi_audit.fixtures import load_meta, materialize, negative_cases, record_bytes

CASES = negative_cases(FIXTURES / "failure")


def test_negative_fixtures_exist():
    assert len(CASES) >= 22


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.name)
def test_negative_fixture_reason(case):
    meta = load_meta(case)
    res = materialize(case, BASELINE)
    assert res.code == meta["expected_reason"], res.findings


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.name)
def test_negative_fixture_single_target(case):
    """Exactly one of record bytes / sidecar bytes differs from the baseline pair."""
    meta = load_meta(case)
    data = record_bytes(case)
    assert sha256_hex(data) == meta["record_sha256"]
    base = BASELINE.read_bytes()
    base_side = (sha256_hex(base) + "\n").encode()
    side_path = case / "record.json.sha256"
    side = side_path.read_bytes() if side_path.is_file() else None
    if meta["mutation"]["target"] == "record":
        assert data != base
        assert side == (sha256_hex(data) + "\n").encode()
    else:
        assert data == base
        assert side != base_side
