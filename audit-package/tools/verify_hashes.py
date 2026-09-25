#!/usr/bin/env python3
"""Verify every <name>.json + <name>.json.sha256 pair under audit-package/fixtures/.

Scope: fixtures/success/, fixtures/baseline/, fixtures/vectors/. F.1 examples/ are
not in scope. fixtures/failure/ is excluded on purpose: it deliberately contains
broken pairs, which tests/test_negative.py checks against their expected codes.
Metadata files (meta.json, vectors.json) are not records and have no sidecar.
The vector index digests (vectors.json) are also checked against the file bytes.

Failures are reported with registry codes (HASH_FILE_MISSING, HASH_FORMAT_INVALID,
HASH_MISMATCH). Exit status is non-zero on any failure.

Usage: python tools/verify_hashes.py
"""

import json
import sys

import _paths  # noqa: F401
from pi3xi_audit.canonical import sha256_hex
from pi3xi_audit.errors import ValidationError
from pi3xi_audit.verify import sidecar_path, verify_hash_pair

FIX = _paths.PACKAGE_ROOT / "fixtures"
SCOPE = ["success", "baseline", "vectors"]
NOT_RECORDS = {"meta.json", "vectors.json"}


def main():
    failures = checked = 0
    for sub in SCOPE:
        for p in sorted((FIX / sub).glob("*.json")):
            if p.name in NOT_RECORDS:
                continue
            checked += 1
            sc = sidecar_path(p)
            rel = p.relative_to(_paths.PACKAGE_ROOT).as_posix()
            try:
                digest = verify_hash_pair(p.read_bytes(), sc.read_bytes() if sc.is_file() else None)
                print(f"PASS {digest} {rel}")
            except ValidationError as exc:
                failures += 1
                print(f"FAIL {exc.code} {rel} {exc.detail}")
    index = json.loads((FIX / "vectors" / "vectors.json").read_text(encoding="utf-8"))
    for v in index["vectors"]:
        p = FIX / "vectors" / v["file"]
        actual = sha256_hex(p.read_bytes()) if p.is_file() else None
        if actual is None:
            failures += 1
            print(f"FAIL HASH_FILE_MISSING index {v['id']} -> {v['file']}")
        elif actual != v["sha256"]:
            failures += 1
            print(f"FAIL HASH_MISMATCH index {v['id']} expected {v['sha256']} actual {actual}")
    print(f"{checked} sidecar pair(s), {len(index['vectors'])} index entr(ies) checked, {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
