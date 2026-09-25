import pytest
from conftest import code_of, with_invariant

from pi3xi_audit.canonical import sha256_hex
from pi3xi_audit.verify import compare_to_baseline, verify_format


def test_numeric_lexemes_have_distinct_identity(baseline_bytes):
    records = [with_invariant(baseline_bytes, lx) for lx in ("1", "1.0", "1e0", "1E0", "1e+0", "10e-1")]
    for r in records:
        assert code_of(verify_format, r) is None
    assert len({sha256_hex(r) for r in records}) == len(records)


@pytest.mark.parametrize("ref,cand", [("1", "1.0"), ("1", "1e0"), ("1.0", "1e0"), ("0", "-0"), ("100", "1e2")])
def test_numeric_representation_change_detected(baseline_bytes, ref, cand):
    assert code_of(compare_to_baseline, with_invariant(baseline_bytes, cand),
                   with_invariant(baseline_bytes, ref)) == "NUMERIC_REPRESENTATION_CHANGE"


def test_numeric_value_change_is_value_changed(baseline_bytes):
    assert code_of(compare_to_baseline, with_invariant(baseline_bytes, "1.5"),
                   with_invariant(baseline_bytes, "1")) == "INVARIANT_VALUE_CHANGED"


def test_numeric_change_outside_invariant(baseline_bytes):
    cand = baseline_bytes.replace(b'"exit_code":0', b'"exit_code":0e0')
    assert code_of(compare_to_baseline, cand, baseline_bytes) == "NUMERIC_REPRESENTATION_CHANGE"


def test_kansoku_bytes_and_escape_identity(baseline_bytes):
    raw = with_invariant(baseline_bytes, '"観測"')
    esc = with_invariant(baseline_bytes, '"\\u89b3\\u6e2c"')
    assert "観測".encode("utf-8") in raw
    assert "観測".encode("utf-8").hex() == "e8a6b3e6b8ac"
    assert sha256_hex(raw) != sha256_hex(esc)
    assert code_of(compare_to_baseline, esc, raw) == "INVARIANT_VALUE_CHANGED"
