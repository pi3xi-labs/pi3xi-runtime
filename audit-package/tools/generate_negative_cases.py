#!/usr/bin/env python3
"""Generate fixtures/failure/: negative fixtures, each made by exactly ONE mutation
of the baseline record bytes (or, for hash-stage cases, of the baseline sidecar bytes).

Each case directory NEG-XXX/ contains:
  record.json          candidate record bytes, or record.json.hex (lowercase hex of the
                       bytes + LF) when the bytes are not valid UTF-8 text (the
                       repository's only write path accepts text); tools and tests
                       decode it back to the exact bytes before auditing
  record.json.sha256   sidecar (recomputed for the mutated bytes, so that only the
                       intended stage fails; mutated or absent for hash-stage cases)
  meta.json            metadata validated by schemas/negative-fixture.schema.json

After writing, every case is audited against the baseline; generation fails if
the actual code differs from expected_reason.

Usage: python tools/generate_negative_cases.py [--out-dir fixtures/failure]
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import _paths  # noqa: F401
from pi3xi_audit.canonical import scan, sha256_hex
from pi3xi_audit.errors import REASON_BY_CODE
from pi3xi_audit.fixtures import materialize

BASELINE_REL = "fixtures/baseline/baseline.json"


def once(data: bytes, old: bytes) -> int:
    n = data.count(old)
    if n != 1:
        raise SystemExit(f"mutation anchor {old!r} occurs {n} times (expected exactly 1)")
    return data.index(old)


def replace(old: bytes, new: bytes):
    def fn(data):
        i = once(data, old)
        return data[:i] + new + data[i + len(old):]
    return fn


def insert_after(anchor: bytes, new: bytes):
    def fn(data):
        i = once(data, anchor) + len(anchor)
        return data[:i] + new + data[i:]
    return fn


def section_bytes(data: bytes, name: str) -> bytes:
    """The exact bytes '"name":<value>' of a top-level member (located by the scanner)."""
    _, node, _ = scan(data.decode("utf-8"))
    value = dict(node.members)[name]
    return f'"{name}":{value.raw}'.encode("utf-8")


def delete_section(name: str):
    def fn(data):
        return replace(b"," + section_bytes(data, name), b"")(data)
    return fn


def swap_sections(a: str, b: str):
    def fn(data):
        sa, sb = section_bytes(data, a), section_bytes(data, b)
        return replace(sa + b"," + sb, sb + b"," + sa)(data)
    return fn


def build_cases(baseline: bytes):
    sha = sha256_hex(baseline).encode("ascii")
    sidecar = sha + b"\n"
    flipped = (b"1" if sha[:1] == b"0" else b"0") + sha[1:] + b"\n"
    R, S = "record", "sidecar"
    # (expected_reason, target, operation, description, mutation on target bytes)
    return [
        ("INVALID_UTF8", R, "insert", "Insert byte 0xFF inside the string \"illustrative\" in invariant.",
         insert_after(b'"illustrative', b"\xff")),
        ("BOM_PRESENT", R, "insert", "Prepend the UTF-8 BOM EF BB BF.",
         lambda d: b"\xef\xbb\xbf" + d),
        ("INVALID_JSON", R, "delete", "Delete the final '}' that closes the top-level object.",
         lambda d: d[:-2] + d[-1:]),
        ("MISSING_FINAL_LF", R, "delete", "Delete the terminating LF.",
         lambda d: d[:-1]),
        ("TRAILING_DATA", R, "insert", "Append a second LF after the terminating LF.",
         lambda d: d + b"\n"),
        ("TRAILING_DATA", R, "insert", "Insert CR before the terminating LF (CRLF line ending).",
         lambda d: d[:-1] + b"\r\n"),
        ("NON_CANONICAL_WHITESPACE", R, "insert", "Insert one space after the first ':' (after \"intent\").",
         insert_after(b'{"intent":', b" ")),
        ("DUPLICATE_KEY", R, "insert", "Duplicate the member \"target\":\"contracts-v1.4.json\" inside intent.",
         insert_after(b'"target":"contracts-v1.4.json",', b'"target":"contracts-v1.4.json",')),
        ("INVARIANT_REMOVED", R, "delete", "Delete the top-level member ,\"invariant\":{...}.",
         delete_section("invariant")),
        ("MISSING_REQUIRED_FIELD", R, "delete", "Delete the top-level member ,\"meta\":{...}.",
         delete_section("meta")),
        ("UNEXPECTED_FIELD", R, "insert", "Insert a top-level member \"record_hash\" (hashes are kept outside records) before the final '}'.",
         lambda d: d[:-2] + b',"record_hash":"' + sha + b'"' + d[-2:]),
        ("FIELD_ORDER_VIOLATION", R, "swap", "Swap the top-level members intent and event.",
         swap_sections("intent", "event")),
        ("TYPE_MISMATCH", R, "replace", "Replace event.sequence 3 with the string \"3\".",
         replace(b'"sequence":3', b'"sequence":"3"')),
        ("HASH_FILE_MISSING", S, "delete", "Delete the sidecar file (record bytes unchanged).",
         lambda s: None),
        ("HASH_FORMAT_INVALID", S, "replace", "Uppercase the sidecar hex digits.",
         lambda s: s.upper()),
        ("HASH_FORMAT_INVALID", S, "insert", "Append '  record.json' (sha256sum style) before the sidecar LF.",
         lambda s: s[:-1] + b"  record.json\n"),
        ("HASH_MISMATCH", S, "replace", "Change the first hex digit of the sidecar digest.",
         lambda s: flipped),
        ("INTENT_MODIFIED", R, "replace", "Replace intent.target contracts-v1.4.json with contracts-v1.3.json.",
         replace(b'"target":"contracts-v1.4.json"', b'"target":"contracts-v1.3.json"')),
        ("INTENT_MODIFIED", R, "swap", "Swap the order of intent.id and intent.action (same values, different key order).",
         replace(b'"id":"intent-0003","action":"cosign.verify-blob"', b'"action":"cosign.verify-blob","id":"intent-0003"')),
        ("EVENT_MODIFIED", R, "replace", "Replace event.sequence 3 with 4.",
         replace(b'"sequence":3', b'"sequence":4')),
        ("OBSERVE_MODIFIED", R, "replace", "Replace observe.result \"Verified OK\" with \"rejected\".",
         replace(b'"result":"Verified OK"', b'"result":"rejected"')),
        ("META_MODIFIED", R, "replace", "Replace meta.runtime_version example-0.0.0 with example-0.0.1.",
         replace(b'"runtime_version":"example-0.0.0"', b'"runtime_version":"example-0.0.1"')),
        ("INVARIANT_TYPE_CHANGED", R, "replace", "Replace the invariant value (object) with null.",
         replace(b'"invariant":{"opaque":["illustrative",1,null]}', b'"invariant":null')),
        ("INVARIANT_VALUE_CHANGED", R, "replace", "Replace the number 1 in invariant with 2.",
         replace(b'"illustrative",1,null', b'"illustrative",2,null')),
        ("NUMERIC_REPRESENTATION_CHANGE", R, "replace", "Replace the number 1 in invariant with 1.0.",
         replace(b'"illustrative",1,null', b'"illustrative",1.0,null')),
        ("NUMERIC_REPRESENTATION_CHANGE", R, "replace", "Replace the number 1 in invariant with 1e0.",
         replace(b'"illustrative",1,null', b'"illustrative",1e0,null')),
        ("NUMERIC_REPRESENTATION_CHANGE", R, "replace", "Replace observe.outputs.exit_code 0 with 0.0.",
         replace(b'"exit_code":0', b'"exit_code":0.0')),
    ], sidecar


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(_paths.PACKAGE_ROOT / "fixtures" / "failure"))
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    baseline_path = _paths.PACKAGE_ROOT / BASELINE_REL
    baseline = baseline_path.read_bytes()
    cases, sidecar = build_cases(baseline)

    out.mkdir(parents=True, exist_ok=True)
    for old in sorted(out.glob("NEG-*")):
        shutil.rmtree(old)

    failures = 0
    for n, (reason, target, op, desc, fn) in enumerate(cases, 1):
        fid = f"NEG-{n:03d}"
        d = out / fid
        d.mkdir()
        if target == "record":
            record = fn(baseline)
            side = (sha256_hex(record) + "\n").encode("ascii")
        else:
            record = baseline
            side = fn(sidecar)
        is_text = True
        try:
            record.decode("utf-8")
        except UnicodeDecodeError:
            is_text = False
        record_file = "record.json" if is_text else "record.json.hex"
        if is_text:
            (d / "record.json").write_bytes(record)
        else:
            (d / "record.json.hex").write_bytes(record.hex().encode("ascii") + b"\n")
        if side is not None:
            (d / "record.json.sha256").write_bytes(side)
        meta = {
            "failure_id": fid,
            "stage": REASON_BY_CODE[reason]["stage"],
            "expected_reason": reason,
            "baseline": BASELINE_REL,
            "record": record_file,
            "record_encoding": "raw" if is_text else "hex",
            "sidecar": "record.json.sha256" if side is not None else None,
            "record_sha256": sha256_hex(record),
            "mutation": {"target": target, "operation": op, "description": desc},
        }
        (d / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        actual = materialize(d, baseline_path).code
        status = "OK" if actual == reason else "FAIL"
        failures += status == "FAIL"
        print(f"{fid} {status} expected={reason} actual={actual}")
    print(f"{len(cases)} negative case(s) generated")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
