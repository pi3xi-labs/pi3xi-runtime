import pytest
from conftest import BASELINE, code_of, positive_files, with_invariant

from pi3xi_audit.verify import verify_format


@pytest.mark.parametrize("path", positive_files(), ids=lambda p: p.name)
def test_positive_fixtures_pass_format(path):
    assert code_of(verify_format, path.read_bytes()) is None


def test_whitespace_inside_strings_allowed(baseline_bytes):
    data = with_invariant(baseline_bytes, '" a\\tb \\n "')
    assert code_of(verify_format, data) is None


@pytest.mark.parametrize("ws", [b" ", b"\t", b"\r", b"\n"])
def test_whitespace_outside_strings_rejected(baseline_bytes, ws):
    i = baseline_bytes.index(b'"event":') + len(b'"event":')
    assert code_of(verify_format, baseline_bytes[:i] + ws + baseline_bytes[i:]) == "NON_CANONICAL_WHITESPACE"


def test_leading_whitespace_rejected(baseline_bytes):
    assert code_of(verify_format, b" " + baseline_bytes) == "NON_CANONICAL_WHITESPACE"


def test_bom_rejected(baseline_bytes):
    assert code_of(verify_format, b"\xef\xbb\xbf" + baseline_bytes) == "BOM_PRESENT"


@pytest.mark.parametrize("bad", [b"\xff", b"\xc3", b"\xed\xa0\x80"])  # invalid byte, truncated sequence, encoded surrogate
def test_invalid_utf8_rejected(baseline_bytes, bad):
    i = baseline_bytes.index(b"illustrative")
    assert code_of(verify_format, baseline_bytes[:i] + bad + baseline_bytes[i:]) == "INVALID_UTF8"


@pytest.mark.parametrize("tail,code", [
    (b"", "MISSING_FINAL_LF"),
    (b"\n\n", "TRAILING_DATA"),
    (b"\r\n", "TRAILING_DATA"),
    (b" \n", "TRAILING_DATA"),
    (b"\nx", "TRAILING_DATA"),
    (b"\n", None),
])
def test_final_lf_rules(baseline_bytes, tail, code):
    assert code_of(verify_format, baseline_bytes[:-1] + tail) == code


def test_invalid_json_rejected(baseline_bytes):
    assert code_of(verify_format, baseline_bytes[:-2] + b"\n") == "INVALID_JSON"
    assert code_of(verify_format, with_invariant(baseline_bytes, "NaN")) == "INVALID_JSON"
    assert code_of(verify_format, with_invariant(baseline_bytes, "01")) == "INVALID_JSON"


def test_duplicate_key_nested_detected(baseline_bytes):
    assert code_of(verify_format, with_invariant(baseline_bytes, '{"a":1,"b":{"x":1,"x":1}}')) == "DUPLICATE_KEY"
    # duplicates compared after unescaping
    assert code_of(verify_format, with_invariant(baseline_bytes, '{"a":1,"\\u0061":1}')) == "DUPLICATE_KEY"


@pytest.mark.parametrize("name", ["record_hash", "contract_version", "schema_version", "record_version"])
def test_no_extra_top_level_fields(baseline_bytes, name):
    data = baseline_bytes[:-2] + f',"{name}":"x"'.encode() + baseline_bytes[-2:]
    assert code_of(verify_format, data) == "UNEXPECTED_FIELD"


def test_top_level_order_enforced(baseline_bytes):
    from pi3xi_audit.canonical import scan
    _, node, _ = scan(baseline_bytes.decode())
    parts = {k: f'"{k}":{v.raw}' for k, v in node.members}
    order = ["event", "intent", "observe", "meta", "invariant"]
    data = ("{" + ",".join(parts[k] for k in order) + "}\n").encode()
    assert code_of(verify_format, data) == "FIELD_ORDER_VIOLATION"


def test_missing_fields(baseline_bytes):
    from pi3xi_audit.canonical import scan
    _, node, _ = scan(baseline_bytes.decode())
    parts = {k: f'"{k}":{v.raw}' for k, v in node.members}
    no_inv = ("{" + ",".join(parts[k] for k in ["intent", "event", "observe", "meta"]) + "}\n").encode()
    no_intent = ("{" + ",".join(parts[k] for k in ["event", "observe", "meta", "invariant"]) + "}\n").encode()
    assert code_of(verify_format, no_inv) == "INVARIANT_REMOVED"
    assert code_of(verify_format, no_intent) == "MISSING_REQUIRED_FIELD"


def test_type_mismatch_uses_f1_schema(baseline_bytes):
    assert code_of(verify_format, baseline_bytes.replace(b'"sequence":3', b'"sequence":-1')) == "TYPE_MISMATCH"
    assert code_of(verify_format, baseline_bytes.replace(b'"result":"Verified OK",', b"")) == "TYPE_MISMATCH"
    assert code_of(verify_format, b"[]\n") == "TYPE_MISMATCH"


@pytest.mark.parametrize("lexeme", ["null", "{}", "[]", '""', "0", "true", "false", '"観測"', "-1.5e-3"])
def test_invariant_accepts_any_json_value(baseline_bytes, lexeme):
    assert code_of(verify_format, with_invariant(baseline_bytes, lexeme)) is None


def test_precedence_first_failing_check_wins(baseline_bytes):
    # BOM + trailing data -> BOM_PRESENT; whitespace + duplicate -> NON_CANONICAL_WHITESPACE
    assert code_of(verify_format, b"\xef\xbb\xbf" + baseline_bytes + b"\n") == "BOM_PRESENT"
    dup_ws = with_invariant(baseline_bytes, '{"x":1, "x":1}')
    assert code_of(verify_format, dup_ws) == "NON_CANONICAL_WHITESPACE"
    # trailing data beats inner whitespace
    assert code_of(verify_format, dup_ws + b"\n") == "TRAILING_DATA"


def test_format_check_order_matches_registry():
    from pi3xi_audit.errors import REASONS
    fmt = [r["code"] for r in REASONS if r["stage"] == "format"]
    assert fmt == ["INVALID_UTF8", "BOM_PRESENT", "INVALID_JSON", "MISSING_FINAL_LF", "TRAILING_DATA",
                   "NON_CANONICAL_WHITESPACE", "DUPLICATE_KEY", "INVARIANT_REMOVED", "MISSING_REQUIRED_FIELD",
                   "UNEXPECTED_FIELD", "FIELD_ORDER_VIOLATION", "TYPE_MISMATCH"]
    assert BASELINE.is_file()
