import json

import pytest
from conftest import FIXTURES, PACKAGE_ROOT
from jsonschema import Draft202012Validator

from pi3xi_audit.errors import ACTIVE_CODES, REASONS, RESERVED_CODES
from pi3xi_audit.fixtures import load_meta, negative_cases

SCHEMAS = PACKAGE_ROOT / "schemas"
CASES = negative_cases(FIXTURES / "failure")


def schema(name):
    s = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(s)
    return Draft202012Validator(s)


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.name)
def test_meta_valid_against_schema(case):
    errors = list(schema("negative-fixture.schema.json").iter_errors(load_meta(case)))
    assert not errors, [e.message for e in errors]


def test_failure_ids_unique_and_match_dir():
    ids = [load_meta(c)["failure_id"] for c in CASES]
    assert ids == [c.name for c in CASES]
    assert len(set(ids)) == len(ids)


def test_meta_stage_matches_registry():
    stage = {r["code"]: r["stage"] for r in REASONS}
    for c in CASES:
        m = load_meta(c)
        assert m["stage"] == stage[m["expected_reason"]]


def test_registry_entries_valid():
    v = schema("rejection-reason.schema.json")
    for r in REASONS:
        assert not list(v.iter_errors(r)), r["code"]


def test_registry_precedence_contiguous_and_unique():
    assert [r["precedence"] for r in REASONS] == list(range(1, len(REASONS) + 1))
    assert len({r["code"] for r in REASONS}) == len(REASONS)
    assert RESERVED_CODES == ["UNSUPPORTED_SCHEMA_VERSION"]


def test_negative_schema_enum_matches_registry():
    s = json.loads((SCHEMAS / "negative-fixture.schema.json").read_text(encoding="utf-8"))
    assert s["properties"]["expected_reason"]["enum"] == ACTIVE_CODES


def test_rejection_reasons_md_lists_all_codes():
    md = (PACKAGE_ROOT / "spec" / "rejection-reasons.md").read_text(encoding="utf-8")
    for r in REASONS:
        assert f"`{r['code']}`" in md, r["code"]
