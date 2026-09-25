#!/usr/bin/env python3
"""Build a deterministic audit-package-v0.1.zip.

Contents (paths inside the ZIP are relative to audit-package/):
  README.md, rfc/, spec/, schemas/, matrices/, fixtures/, docs/, and reports/ (if given)

Determinism: files sorted by path, every entry timestamp 1980-01-01 00:00:00,
permissions 0644, DEFLATE level 9, no directory entries, no extra fields. The
same inputs always produce the same ZIP bytes.

Usage:
  python tools/build_audit_package.py --out audit-package-v0.1.zip --reports-dir reports
  python tools/build_audit_package.py --out /path/x.zip --no-reports
"""

import argparse
import sys
import zipfile
from pathlib import Path

import _paths  # noqa: F401
from pi3xi_audit.canonical import sha256_hex

ROOT = _paths.PACKAGE_ROOT
INCLUDE = ["README.md", "rfc", "spec", "schemas", "matrices", "fixtures", "docs"]
EPOCH = (1980, 1, 1, 0, 0, 0)


def collect(reports_dir=None):
    files = []
    for item in INCLUDE:
        p = ROOT / item
        if p.is_file():
            files.append((item, p))
        else:
            files += [(f.relative_to(ROOT).as_posix(), f) for f in p.rglob("*")
                      if f.is_file() and "__pycache__" not in f.parts]
    if reports_dir is not None:
        rd = Path(reports_dir)
        files += [("reports/" + f.relative_to(rd).as_posix(), f) for f in rd.rglob("*") if f.is_file()]
    return sorted(files)


def build(out, reports_dir=None):
    files = collect(reports_dir)
    with zipfile.ZipFile(out, "w") as zf:
        for arcname, path in files:
            info = zipfile.ZipInfo(arcname, date_time=EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.create_system = 3
            zf.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return files


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="audit-package-v0.1.zip")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--reports-dir")
    group.add_argument("--no-reports", action="store_true")
    args = ap.parse_args(argv)
    files = build(args.out, None if args.no_reports else args.reports_dir)
    data = Path(args.out).read_bytes()
    print(f"{args.out}: {len(files)} file(s), {len(data)} bytes, sha256 {sha256_hex(data)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
