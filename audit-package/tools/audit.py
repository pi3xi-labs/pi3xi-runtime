#!/usr/bin/env python3
"""Run the full F.2 audit and write reports.

  reports/hash.log    hash-stage result for every positive record (success + baseline)
  reports/replay.log  replay byte/SHA-256 equality for every positive record
  reports/audit.log   format+hash results for positives, expected vs actual reason
                      for every negative fixture, vector re-verification, summary

Exit status is non-zero if any check fails. Output is deterministic (no timestamps).

Usage: python tools/audit.py [--reports-dir reports]
"""

import argparse
import json
import sys
from pathlib import Path

import _paths  # noqa: F401
from pi3xi_audit.canonical import sha256_hex
from pi3xi_audit.errors import ValidationError
from pi3xi_audit.fixtures import load_meta, materialize, negative_cases
from pi3xi_audit.verify import (audit_record, compare_to_baseline, replay_compare, sidecar_path,
                                verify_format, verify_hash_pair)

ROOT = _paths.PACKAGE_ROOT
FIX = ROOT / "fixtures"
BASELINE = FIX / "baseline" / "baseline.json"


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def positives():
    return sorted((FIX / "success").glob("*.json")) + [BASELINE]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports-dir", default=str(ROOT / "reports"))
    args = ap.parse_args(argv)
    out = Path(args.reports_dir)
    out.mkdir(parents=True, exist_ok=True)
    failures = 0
    hash_log, replay_log, audit_log = [], [], []

    # Hash stage and replay on positives
    for p in positives():
        data = p.read_bytes()
        sc = sidecar_path(p)
        try:
            digest = verify_hash_pair(data, sc.read_bytes() if sc.is_file() else None)
            hash_log.append(f"PASS {digest} {rel(p)}")
        except ValidationError as exc:
            failures += 1
            hash_log.append(f"FAIL {exc.code} {rel(p)} {exc.detail}")
        r = replay_compare(p)
        failures += not r.ok
        replay_log.append(
            f"{'PASS' if r.ok else 'FAIL'} {rel(p)} bytes_equal={str(r.bytes_equal).lower()} "
            f"sha256_stored={r.sha256_stored} sha256_replayed={r.sha256_replayed} "
            f"sidecar_match={str(r.sidecar_match).lower()}")

    # Positives: all stages (baseline compare only for the baseline copy in success/)
    for p in positives():
        res = audit_record(p, BASELINE if p.read_bytes() == BASELINE.read_bytes() else None)
        failures += not res.ok
        audit_log.append(f"POSITIVE {'PASS' if res.ok else 'FAIL'} {rel(p)} sha256={res.sha256} code={res.code}")

    # Negatives: actual primary code must equal expected_reason
    cases = negative_cases(FIX / "failure")
    for d in cases:
        meta = load_meta(d)
        res = materialize(d, BASELINE)
        ok = res.code == meta["expected_reason"]
        failures += not ok
        audit_log.append(f"NEGATIVE {'PASS' if ok else 'FAIL'} {meta['failure_id']} stage={meta['stage']} "
                         f"expected={meta['expected_reason']} actual={res.code}")
        hash_findings = [c for s, c, _ in res.findings if s == "hash"]
        hash_log.append(f"NEGATIVE {meta['failure_id']} hash_stage={hash_findings[0] if hash_findings else 'PASS'}")

    # Vectors: recompute digests and verdicts from the raw vector files
    vdir = FIX / "vectors"
    doc = json.loads((vdir / "vectors.json").read_text(encoding="utf-8"))
    by_id = {v["id"]: (vdir / v["file"]).read_bytes() for v in doc["vectors"]}
    for v in doc["vectors"]:
        data = by_id[v["id"]]
        ok = sha256_hex(data) == v["sha256"]
        if v["kind"] != "identity-only":
            try:
                verify_format(data)
                fmt = None
            except ValidationError as exc:
                fmt = exc.code
            ok = ok and fmt == v["expected_reason"] and (fmt is None) == v["expected_accept"]
        failures += not ok
        audit_log.append(f"VECTOR {'PASS' if ok else 'FAIL'} {v['id']} kind={v['kind']} sha256={sha256_hex(data)} "
                         f"expected_reason={v['expected_reason']}")
    for c in doc["comparisons"]:
        try:
            compare_to_baseline(by_id[c["candidate"]], by_id[c["reference"]])
            got = None
        except ValidationError as exc:
            got = exc.code
        ok = got == c["expected_result"]
        failures += not ok
        audit_log.append(f"COMPARISON {'PASS' if ok else 'FAIL'} {c['reference']} -> {c['candidate']} result={got}")

    summary = (f"SUMMARY positives={len(positives())} negatives={len(cases)} vectors={len(doc['vectors'])} "
               f"comparisons={len(doc['comparisons'])} failures={failures} "
               f"result={'PASS' if failures == 0 else 'FAIL'}")
    audit_log.append(summary)
    for name, lines in (("hash.log", hash_log), ("replay.log", replay_log), ("audit.log", audit_log)):
        (out / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
