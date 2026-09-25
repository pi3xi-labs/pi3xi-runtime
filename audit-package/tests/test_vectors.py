import json

import pytest
from conftest import FIXTURES

from pi3xi_audit.canonical import sha256_hex
from pi3xi_audit.errors import ACTIVE_CODES, ValidationError
from pi3xi_audit.verify import compare_to_baseline, verify_format

VDIR = FIXTURES / "vectors"
INDEX = json.loads((VDIR / "vectors.json").read_text(encoding="utf-8"))
VECTORS = {v["id"]: v for v in INDEX["vectors"]}
KINDS = {"identity-only", "canonical-record", "non-canonical"}
FIELDS = ["id", "name", "file", "kind", "length_bytes", "sha256", "expected_accept", "expected_reason", "status"]


def data(vid):
    return (VDIR / VECTORS[vid]["file"]).read_bytes()


def code(fn, *args):
    try:
        fn(*args)
        return None
    except ValidationError as exc:
        return exc.code


def test_required_raw_vectors():
    assert data("TV-001") == b"{}\n"
    assert data("TV-002") == b'{"value":1}\n'
    assert data("TV-003") == b'{"value":1.0}\n'
    assert data("TV-004") == b'{"value":1e0}\n'
    assert "観測".encode("utf-8") in data("TV-005")
    assert data("TV-006") == b"[3,2,1]\n"


def test_numeric_vectors_pairwise_distinct_sha():
    shas = [sha256_hex(data(v)) for v in ("TV-002", "TV-003", "TV-004")]
    assert len(set(shas)) == 3


def test_array_order_changes_identity():
    assert sha256_hex(data("TV-006")) != sha256_hex(data("TV-007"))


def test_unicode_escape_changes_identity():
    assert sha256_hex(data("TV-005")) != sha256_hex(data("TV-008"))


def test_index_structure():
    ids = [v["id"] for v in INDEX["vectors"]]
    assert len(ids) == len(set(ids))
    for v in INDEX["vectors"]:
        assert list(v) == FIELDS, v["id"]
        assert v["kind"] in KINDS
        assert v["file"] == f"{v['id']}.json"
        if v["kind"] == "identity-only":
            assert v["expected_accept"] is None and v["expected_reason"] is None and v["status"] == "not-applicable"
        else:
            assert v["status"] == "provisional-until-spec-freeze"
            assert v["expected_accept"] == (v["expected_reason"] is None)
            assert v["expected_reason"] is None or v["expected_reason"] in ACTIVE_CODES
    assert {v["kind"] for v in INDEX["vectors"]} == KINDS


def test_index_never_embeds_payloads():
    text = (VDIR / "vectors.json").read_text(encoding="utf-8")
    for v in INDEX["vectors"]:
        assert set(v) == set(FIELDS)
    assert '"intent"' not in text and '"value"' not in text


@pytest.mark.parametrize("vid", [v for v in VECTORS if VECTORS[v]["kind"] != "identity-only"])
def test_record_vector_classification(vid):
    assert code(verify_format, data(vid)) == VECTORS[vid]["expected_reason"]


@pytest.mark.parametrize("comp", INDEX["comparisons"], ids=lambda c: f"{c['reference']}-{c['candidate']}")
def test_vector_comparisons(comp):
    got = code(compare_to_baseline, data(comp["candidate"]), data(comp["reference"]))
    assert got == comp["expected_result"]
    assert comp["status"] == "provisional-until-spec-freeze"
