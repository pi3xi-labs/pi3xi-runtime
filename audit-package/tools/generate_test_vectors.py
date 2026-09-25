#!/usr/bin/env python3
"""Generate the shared test vectors under fixtures/vectors/.

Every vector payload is stored as a raw byte file TV-XXX.json with a
TV-XXX.json.sha256 sidecar. vectors.json is only an index; it never embeds
payloads as parsed JSON. All digests and verdicts are computed by the code from
the file bytes, never written by hand.

Kinds:
  identity-only     arbitrary bytes; only the SHA-256 identity is asserted
  canonical-record  a Canonical Record expected to be accepted
  non-canonical     a record expected to be rejected with expected_reason

The SHA-256 identity of given bytes does not depend on any serialization rule.
Only the accept/reject classification depends on the Spec v1 freeze, so it
carries status "provisional-until-spec-freeze".

Usage: python tools/generate_test_vectors.py [--out-dir fixtures/vectors]
"""

import argparse
import json
import sys
from pathlib import Path

import _paths  # noqa: F401
from pi3xi_audit.canonical import scan, sha256_hex
from pi3xi_audit.errors import ValidationError
from pi3xi_audit.verify import compare_to_baseline, verify_format

FIX = _paths.PACKAGE_ROOT / "fixtures"
PROVISIONAL = "provisional-until-spec-freeze"


def splice_invariant(record: bytes, lexeme: str) -> bytes:
    text = record.decode("utf-8")
    _, node, _ = scan(text)
    inv = dict(node.members)["invariant"]
    return (text[:inv.start] + lexeme + text[inv.end:]).encode("utf-8")


def verdict(fn):
    try:
        fn()
        return None
    except ValidationError as exc:
        return exc.code


def build():
    base = (FIX / "baseline" / "baseline.json").read_bytes()
    success = {p.stem: p.read_bytes() for p in sorted((FIX / "success").glob("*.json"))}
    i = base.index(b'{"intent":') + len(b'{"intent":')
    vectors = [
        # identity-only: the digest of these bytes is fixed regardless of any serialization rule
        ("TV-001", "empty-object", "identity-only", b"{}\n"),
        ("TV-002", "value-int-1", "identity-only", b'{"value":1}\n'),
        ("TV-003", "value-decimal-1.0", "identity-only", b'{"value":1.0}\n'),
        ("TV-004", "value-exponent-1e0", "identity-only", b'{"value":1e0}\n'),
        ("TV-005", "value-unicode-kansoku", "identity-only", '{"value":"観測"}\n'.encode("utf-8")),
        ("TV-006", "array-3-2-1", "identity-only", b"[3,2,1]\n"),
        ("TV-007", "array-1-2-3", "identity-only", b"[1,2,3]\n"),
        ("TV-008", "value-unicode-kansoku-escaped", "identity-only", b'{"value":"\\u89b3\\u6e2c"}\n'),
        # canonical-record: success fixtures and invariant variants of the baseline
        ("TV-101", "success-verify-success", "canonical-record", success["verify-success"]),
        ("TV-102", "success-verify-fail", "canonical-record", success["verify-fail"]),
        ("TV-103", "success-replay-0002", "canonical-record", success["replay-0002"]),
        ("TV-104", "success-replay-0003-baseline", "canonical-record", success["replay-0003"]),
        ("TV-105", "invariant-int-1", "canonical-record", splice_invariant(base, "1")),
        ("TV-106", "invariant-decimal-1.0", "canonical-record", splice_invariant(base, "1.0")),
        ("TV-107", "invariant-exponent-1e0", "canonical-record", splice_invariant(base, "1e0")),
        ("TV-108", "invariant-unicode-kansoku", "canonical-record", splice_invariant(base, '"観測"')),
        ("TV-109", "invariant-unicode-kansoku-escaped", "canonical-record", splice_invariant(base, '"\\u89b3\\u6e2c"')),
        ("TV-110", "invariant-null", "canonical-record", splice_invariant(base, "null")),
        ("TV-111", "invariant-empty-object", "canonical-record", splice_invariant(base, "{}")),
        ("TV-112", "invariant-empty-array", "canonical-record", splice_invariant(base, "[]")),
        ("TV-113", "invariant-empty-string", "canonical-record", splice_invariant(base, '""')),
        # non-canonical: single byte-level deviations from the baseline
        ("TV-201", "bom-present", "non-canonical", b"\xef\xbb\xbf" + base),
        ("TV-202", "missing-final-lf", "non-canonical", base[:-1]),
        ("TV-203", "crlf-termination", "non-canonical", base[:-1] + b"\r\n"),
        ("TV-204", "space-after-colon", "non-canonical", base[:i] + b" " + base[i:]),
        ("TV-205", "duplicate-key", "non-canonical", base.replace(b'"sequence":3', b'"sequence":3,"sequence":3')),
        ("TV-206", "field-order-swapped", "non-canonical", _swap_intent_event(base)),
    ]
    comparisons = [
        ("TV-105", "TV-106"), ("TV-105", "TV-107"), ("TV-106", "TV-107"),
        ("TV-105", "TV-108"), ("TV-108", "TV-109"), ("TV-110", "TV-111"),
        ("TV-111", "TV-112"), ("TV-113", "TV-110"), ("TV-104", "TV-111"), ("TV-104", "TV-104"),
    ]
    return vectors, comparisons


def _swap_intent_event(base: bytes) -> bytes:
    _, node, _ = scan(base.decode("utf-8"))
    m = dict(node.members)
    a = f'"intent":{m["intent"].raw}'.encode("utf-8")
    b = f'"event":{m["event"].raw}'.encode("utf-8")
    return base.replace(a + b"," + b, b + b"," + a)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(FIX / "vectors"))
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("TV-*"):
        old.unlink()
    vectors, comparisons = build()
    by_id = {vid: data for vid, _, _, data in vectors}
    index = []
    for vid, name, kind, data in vectors:
        (out / f"{vid}.json").write_bytes(data)
        (out / f"{vid}.json.sha256").write_bytes((sha256_hex(data) + "\n").encode("ascii"))
        entry = {"id": vid, "name": name, "file": f"{vid}.json", "kind": kind,
                 "length_bytes": len(data), "sha256": sha256_hex(data)}
        if kind == "identity-only":
            entry.update(expected_accept=None, expected_reason=None, status="not-applicable")
        else:
            reason = verdict(lambda: verify_format(data))
            if (kind == "canonical-record") != (reason is None):
                raise SystemExit(f"{vid}: kind {kind} but format result {reason}")
            entry.update(expected_accept=reason is None, expected_reason=reason, status=PROVISIONAL)
        index.append(entry)
    comp = [{"reference": r, "candidate": c, "bytes_equal": by_id[r] == by_id[c],
             "expected_result": verdict(lambda: compare_to_baseline(by_id[c], by_id[r])),
             "status": PROVISIONAL} for r, c in comparisons]
    doc = {
        "generated_by": "tools/generate_test_vectors.py",
        "spec": "spec/canonical-serialization-v1.md",
        "note": ("Index only. Payloads are the raw bytes of each 'file' (with a .sha256 sidecar); they are never "
                 "embedded here. sha256 is computed from the file bytes and is independent of serialization rules. "
                 "expected_accept / expected_reason / comparison results depend on the Spec v1 freeze and are "
                 "provisional until then. Do not edit by hand."),
        "vectors": index,
        "comparisons": comp,
    }
    (out / "vectors.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(index)} vector(s), {len(comp)} comparison(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
