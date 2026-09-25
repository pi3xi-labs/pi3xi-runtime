#!/usr/bin/env python3
"""Validation for the Pi³XI Runtime Contract v1.

Checks:
  1. Required files exist and are non-empty (structure).
  2. Every schema is a valid JSON Schema draft 2020-12 document.
  3. The contract file references only schema/example files that exist,
     and references the canonical spec commit.
  4. Every example validates against the schemas (envelope + Canonical Record).
  5. Record-internal references (intent_ref, event_ref) and time order
     (occurred_at <= observed_at <= meta.timestamp).
  6. G1 event ordering in replay streams: strictly increasing event.sequence,
     non-decreasing event.occurred_at and meta.timestamp.
  7. G3 invariant passthrough: record.invariant is value-identical to the
     submitted invariant (and the Intent is recorded as submitted).

Usage:
  python tools/validate_runtime.py              # validate the repository
  python tools/validate_runtime.py --self-test  # negative self-tests: mutated
                                                # inputs must be rejected

Requires: jsonschema (see .github/workflows/runtime-check.yml for the pinned version).
"""

import copy
import json
import sys
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parent.parent

SPEC_COMMIT = "93656646fcf1aab3ef316a557b23885d66ebe30f"
CONTRACT = "contracts/runtime-contract-v1.json"
SCHEMA_NAMES = ["intent", "event", "observe", "meta", "invariant", "canonical-record"]
RECORD_FIELDS = ["intent", "event", "observe", "meta", "invariant"]

REQUIRED_FILES = [
    "README.md",
    "GOVERNANCE.md",
    "LICENSE",
    CONTRACT,
    *[f"schemas/{n}.schema.json" for n in SCHEMA_NAMES],
    "examples/verify-success.json",
    "examples/verify-fail.json",
    "examples/replay.json",
    "docs/runtime-model.md",
    "docs/audit-model.md",
    "releases/runtime-contract-v1.0.md",
    "tools/validate_runtime.py",
    ".github/workflows/runtime-check.yml",
]

# Envelope for example files. Examples must be explicitly marked illustrative.
EXAMPLE_META = {
    "type": "object",
    "properties": {
        "illustrative": {"const": True},
        "notice": {"type": "string", "minLength": 1},
        "scenario": {"type": "string", "minLength": 1},
    },
    "required": ["illustrative", "notice", "scenario"],
    "additionalProperties": False,
}
SUBMISSION = {
    "type": "object",
    "properties": {
        "record_id": {"type": "string", "minLength": 1},
        "intent": {"type": "object"},
        "invariant": True,
    },
    "required": ["record_id", "intent", "invariant"],
    "additionalProperties": False,
}
SINGLE_ENVELOPE = {
    "type": "object",
    "properties": {"example": EXAMPLE_META, "submission": SUBMISSION, "record": {"type": "object"}},
    "required": ["example", "record"],
    "additionalProperties": False,
}
STREAM_ENVELOPE = {
    "type": "object",
    "properties": {
        "example": EXAMPLE_META,
        "submissions": {"type": "array", "items": SUBMISSION},
        "records": {"type": "array", "items": {"type": "object"}, "minItems": 1},
    },
    "required": ["example", "records"],
    "additionalProperties": False,
}


def load_json(rel):
    with open(ROOT / rel, encoding="utf-8") as f:
        return json.load(f)


def load_schemas():
    schemas = {n: load_json(f"schemas/{n}.schema.json") for n in SCHEMA_NAMES}
    registry = Registry().with_resources(
        (s["$id"], Resource.from_contents(s)) for s in schemas.values()
    )
    return schemas, registry


def parse_ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def schema_errors(instance, schema, registry, label):
    kwargs = {"registry": registry} if registry is not None else {}
    v = Draft202012Validator(schema, format_checker=FormatChecker(), **kwargs)
    return [
        f"{label}: {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in sorted(v.iter_errors(instance), key=lambda e: list(map(str, e.absolute_path)))
    ]


def check_record(record, schemas, registry, label):
    """Schema conformance plus record-internal consistency of one Canonical Record."""
    errors = schema_errors(record, schemas["canonical-record"], registry, label)
    if errors:
        return errors
    intent, event, observe, meta = (record[k] for k in ("intent", "event", "observe", "meta"))
    if "intent_ref" in event and event["intent_ref"] != intent["id"]:
        errors.append(f"{label}: event.intent_ref {event['intent_ref']!r} != intent.id {intent['id']!r}")
    if observe["event_ref"] != event["id"]:
        errors.append(f"{label}: observe.event_ref {observe['event_ref']!r} != event.id {event['id']!r}")
    try:
        t_ev, t_ob, t_me = (parse_ts(x) for x in (event["occurred_at"], observe["observed_at"], meta["timestamp"]))
    except ValueError as exc:
        return errors + [f"{label}: unparsable timestamp: {exc}"]
    if not t_ev <= t_ob:
        errors.append(f"{label}: observe.observed_at is earlier than event.occurred_at")
    if not t_ob <= t_me:
        errors.append(f"{label}: meta.timestamp is earlier than observe.observed_at")
    return errors


def check_ordering(records, label):
    """G1 event ordering over a stream of (already schema-valid) records."""
    errors = []
    for i in range(1, len(records)):
        prev, cur = records[i - 1], records[i]
        if not cur["event"]["sequence"] > prev["event"]["sequence"]:
            errors.append(
                f"{label}: records[{i}] event.sequence {cur['event']['sequence']} "
                f"not strictly greater than {prev['event']['sequence']} (G1)"
            )
        for path in (("event", "occurred_at"), ("meta", "timestamp")):
            a, b = parse_ts(prev[path[0]][path[1]]), parse_ts(cur[path[0]][path[1]])
            if b < a:
                errors.append(f"{label}: records[{i}] {'.'.join(path)} decreases (G1)")
    ids = [r["meta"]["record_id"] for r in records]
    if len(ids) != len(set(ids)):
        errors.append(f"{label}: duplicate meta.record_id in stream")
    return errors


def same_value(a, b):
    """Value-identical: deep equality that also distinguishes JSON types (1 vs 1.0 vs true)."""
    return json.dumps(a, sort_keys=False, ensure_ascii=False) == json.dumps(b, sort_keys=False, ensure_ascii=False)


def check_passthrough(submission, record, label):
    """G3 invariant preservation (non-modification); Intent recorded as submitted."""
    errors = []
    if submission["record_id"] != record["meta"]["record_id"]:
        errors.append(f"{label}: submission.record_id {submission['record_id']!r} != meta.record_id")
        return errors
    if not same_value(submission["invariant"], record["invariant"]):
        errors.append(f"{label}: invariant was modified (submitted != recorded) (G3)")
    if not same_value(submission["intent"], record["intent"]):
        errors.append(f"{label}: intent was not recorded as submitted")
    return errors


def check_example(doc, schemas, registry, label):
    errors = []
    if "records" in doc:
        errors += schema_errors(doc, STREAM_ENVELOPE, None, label)
        if errors:
            return errors
        records = doc["records"]
        for i, r in enumerate(records):
            errors += check_record(r, schemas, registry, f"{label} records[{i}]")
        if errors:
            return errors
        errors += check_ordering(records, label)
        subs = doc.get("submissions", [])
        if subs and len(subs) != len(records):
            errors.append(f"{label}: submissions and records differ in length")
        for i, (s, r) in enumerate(zip(subs, records)):
            errors += check_passthrough(s, r, f"{label} records[{i}]")
    else:
        errors += schema_errors(doc, SINGLE_ENVELOPE, None, label)
        if errors:
            return errors
        errors += check_record(doc["record"], schemas, registry, f"{label} record")
        if not errors and "submission" in doc:
            errors += check_passthrough(doc["submission"], doc["record"], label)
    return errors


def check_contract(contract, root=ROOT):
    errors = []
    paths = [contract.get("canonical_record", {}).get("schema")]
    paths += [layer.get("schema") for layer in contract.get("layers", [])]
    paths += contract.get("examples", [])
    for p in paths:
        if not p or not (root / p).is_file():
            errors.append(f"contract: referenced file missing: {p!r}")
    layer_fields = [layer.get("field") for layer in contract.get("layers", [])]
    if layer_fields != RECORD_FIELDS:
        errors.append(f"contract: layer fields {layer_fields} != {RECORD_FIELDS}")
    if contract.get("canonical_record", {}).get("fields") != RECORD_FIELDS:
        errors.append("contract: canonical_record.fields mismatch")
    spec = contract.get("spec_reference", {})
    if spec.get("tag") != "spec-v1.0" or spec.get("commit") != SPEC_COMMIT:
        errors.append("contract: spec_reference must be spec-v1.0 @ " + SPEC_COMMIT)
    if contract.get("invariant_rules", {}).get("status") != "reserved":
        errors.append("contract: invariant_rules.status must be 'reserved' in v1")
    ids = [g.get("id") for g in contract.get("guarantees", [])]
    if ids != ["G1", "G2", "G3", "G4"]:
        errors.append(f"contract: guarantees must be G1..G4, got {ids}")
    return errors


def run_checks():
    failures = 0

    def report(label, errors):
        nonlocal failures
        if errors:
            failures += 1
            print(f"FAIL: {label}")
            for e in errors:
                print(f"    {e}")
        else:
            print(f"PASS: {label}")

    for rel in REQUIRED_FILES:
        p = ROOT / rel
        report(f"file exists and non-empty: {rel}",
               [] if p.is_file() and p.read_text(encoding="utf-8").strip() else ["missing or empty"])
    if failures:
        return failures

    schemas, registry = load_schemas()
    for n, s in schemas.items():
        try:
            Draft202012Validator.check_schema(s)
            errs = [] if s.get("$schema") == "https://json-schema.org/draft/2020-12/schema" else ["$schema is not draft 2020-12"]
        except Exception as exc:  # noqa: BLE001
            errs = [str(exc)]
        report(f"schema valid (draft 2020-12): {n}", errs)

    contract = load_json(CONTRACT)
    report(f"contract references: {CONTRACT}", check_contract(contract))

    for rel in contract["examples"]:
        report(f"example: {rel}", check_example(load_json(rel), schemas, registry, rel))
    return failures


def self_test():
    """Negative self-tests: each mutation of a valid example MUST be rejected."""
    schemas, registry = load_schemas()
    success = load_json("examples/verify-success.json")
    replay = load_json("examples/replay.json")
    contract = load_json(CONTRACT)

    def mutate(doc, fn):
        d = copy.deepcopy(doc)
        fn(d)
        return d

    def set_(obj, key, value):
        obj[key] = value

    cases = [
        ("replay: event.sequence not strictly increasing",
         mutate(replay, lambda d: set_(d["records"][1]["event"], "sequence", d["records"][0]["event"]["sequence"]))),
        ("replay: records out of order",
         mutate(replay, lambda d: d["records"].reverse() or d["submissions"].reverse())),
        ("replay: timestamps decrease across records (record-internally consistent)",
         mutate(replay, lambda d: (
             set_(d["records"][2]["event"], "occurred_at", "2026-01-01T00:00:05Z"),
             set_(d["records"][2]["observe"], "observed_at", "2026-01-01T00:00:06Z"),
             set_(d["records"][2]["meta"], "timestamp", "2026-01-01T00:00:07Z")))),
        ("replay: meta.timestamp earlier than observe.observed_at",
         mutate(replay, lambda d: set_(d["records"][2]["meta"], "timestamp", "2025-12-31T23:59:59Z"))),
        ("replay: invariant modified in stream",
         mutate(replay, lambda d: set_(d["records"][2], "invariant", {"opaque": ["illustrative", 1.0, None]}))),
        ("success: invariant modified",
         mutate(success, lambda d: set_(d["record"], "invariant", "illustrative-opaque-value-B"))),
        ("success: invariant type changed (string -> null)",
         mutate(success, lambda d: set_(d["record"], "invariant", None))),
        ("success: invariant field removed",
         mutate(success, lambda d: d["record"].pop("invariant"))),
        ("success: explanation added to observe (Observation First)",
         mutate(success, lambda d: set_(d["record"]["observe"], "explanation", "because the issuer matched"))),
        ("success: extra top-level field in Canonical Record",
         mutate(success, lambda d: set_(d["record"], "reason", "x"))),
        ("success: meta missing",
         mutate(success, lambda d: d["record"].pop("meta"))),
        ("success: observe.event_ref mismatch",
         mutate(success, lambda d: set_(d["record"]["observe"], "event_ref", "event-9999"))),
        ("success: intent rewritten",
         mutate(success, lambda d: set_(d["record"]["intent"], "action", "something-else"))),
        ("success: not marked illustrative",
         mutate(success, lambda d: set_(d["example"], "illustrative", False))),
        ("success: bad contract tag in meta",
         mutate(success, lambda d: set_(d["record"]["meta"], "contract", "runtime-contract-1.0"))),
    ]
    failures = 0
    for label, doc in cases:
        errors = check_example(doc, schemas, registry, "mutated")
        ok = bool(errors)
        print(f"{'PASS' if ok else 'FAIL'}: rejected: {label}" + (f"  [{errors[0]}]" if ok else "  (was accepted)"))
        failures += not ok

    bad_contract = copy.deepcopy(contract)
    bad_contract["layers"][0]["schema"] = "schemas/missing.schema.json"
    ok = bool(check_contract(bad_contract))
    print(f"{'PASS' if ok else 'FAIL'}: rejected: contract references missing schema")
    failures += not ok

    # Sanity: the unmutated inputs must still be accepted.
    for label, doc in (("verify-success.json", success), ("replay.json", replay)):
        ok = not check_example(doc, schemas, registry, label)
        print(f"{'PASS' if ok else 'FAIL'}: accepted unmutated: {label}")
        failures += not ok
    return failures


def main(argv):
    failures = self_test() if "--self-test" in argv else run_checks()
    print()
    if failures:
        print(f"RESULT: FAIL ({failures} check(s) failed)")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
