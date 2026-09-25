"""Verification API: format, hash pair, baseline comparison, replay.

All functions operate on exact bytes. None of them re-serializes a record.
"""

import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .canonical import (TOP_LEVEL_ORDER, check_format, json_type, numeric_only_difference,
                        sections, sha256_hex)
from .errors import BaselineError, ValidationError, primary

SIDECAR_SUFFIX = ".sha256"
SIDECAR_RE = re.compile(rb"[0-9a-f]{64}\n")


def sidecar_path(record_path) -> Path:
    p = Path(record_path)
    return p.with_name(p.name + SIDECAR_SUFFIX)


def verify_format(data: bytes):
    """Format stage. Returns the SHA-256 identity of data; raises ValidationError."""
    check_format(data)
    return sha256_hex(data)


def verify_hash_pair(record_bytes: bytes, sidecar_bytes):
    """Hash stage. sidecar_bytes is None when the sidecar file is missing.
    Returns the digest; raises ValidationError."""
    if sidecar_bytes is None:
        raise ValidationError("HASH_FILE_MISSING", "no .sha256 sidecar")
    if not SIDECAR_RE.fullmatch(sidecar_bytes):
        raise ValidationError("HASH_FORMAT_INVALID", f"sidecar is {len(sidecar_bytes)} byte(s), expected 64 lowercase hex + LF")
    actual = sha256_hex(record_bytes)
    expected = sidecar_bytes[:64].decode("ascii")
    if actual != expected:
        raise ValidationError("HASH_MISMATCH", f"sidecar {expected} != actual {actual}")
    return actual


def compare_to_baseline(candidate: bytes, reference: bytes):
    """Baseline stage. Both inputs must be format-valid. Returns None if byte-identical;
    otherwise raises ValidationError classifying the first differing top-level section."""
    if candidate == reference:
        return None
    try:
        ref = sections(check_format(reference))
    except ValidationError as exc:
        raise BaselineError(f"reference record is not canonical: {exc}") from None
    cand = sections(check_format(candidate))
    for name in TOP_LEVEL_ORDER:
        c, r = cand[name], ref[name]
        if c.raw == r.raw:
            continue
        if name == "invariant":
            if json_type(c) != json_type(r):
                raise ValidationError("INVARIANT_TYPE_CHANGED", f"{json_type(r)} -> {json_type(c)}")
            if numeric_only_difference(c, r):
                raise ValidationError("NUMERIC_REPRESENTATION_CHANGE", "invariant: numeric lexical form changed")
            raise ValidationError("INVARIANT_VALUE_CHANGED", "invariant value differs")
        if numeric_only_difference(c, r):
            raise ValidationError("NUMERIC_REPRESENTATION_CHANGE", f"{name}: numeric lexical form changed")
        raise ValidationError(f"{name.upper()}_MODIFIED", f"first differing section: {name}")
    raise AssertionError("bytes differ but no top-level section differs")  # unreachable for canonical input


@dataclass
class AuditResult:
    path: str
    sha256: str
    code: object = None                           # primary reason code, None = accepted
    findings: list = field(default_factory=list)  # [(stage, code, detail)]

    @property
    def ok(self):
        return self.code is None


def audit_record(record_path, baseline_path=None) -> AuditResult:
    """Run all stages on one record file and pick the primary code by precedence.

    Format and hash stages always run. The baseline stage runs only when a
    baseline is given and the candidate passed the format stage.
    """
    record_path = Path(record_path)
    data = record_path.read_bytes()
    sc = sidecar_path(record_path)
    sidecar = sc.read_bytes() if sc.is_file() else None
    findings = []
    format_ok = True
    for stage, fn in (("format", lambda: verify_format(data)),
                      ("hash", lambda: verify_hash_pair(data, sidecar))):
        try:
            fn()
        except ValidationError as exc:
            findings.append((stage, exc.code, exc.detail))
            format_ok = format_ok and stage != "format"
    if baseline_path is not None and format_ok:
        reference = Path(baseline_path).read_bytes()
        ref_sidecar = sidecar_path(baseline_path)
        try:
            verify_format(reference)
            verify_hash_pair(reference, ref_sidecar.read_bytes() if ref_sidecar.is_file() else None)
        except ValidationError as exc:
            raise BaselineError(f"baseline {baseline_path} is invalid: {exc}") from None
        try:
            compare_to_baseline(data, reference)
        except ValidationError as exc:
            findings.append(("baseline", exc.code, exc.detail))
    return AuditResult(str(record_path), sha256_hex(data), primary(c for _, c, _ in findings), findings)


@dataclass
class ReplayResult:
    path: str
    sha256_stored: str
    sha256_replayed: str
    bytes_equal: bool
    sidecar_match: bool

    @property
    def ok(self):
        return self.bytes_equal and self.sha256_stored == self.sha256_replayed and self.sidecar_match


def replay_compare(record_path, workdir=None) -> ReplayResult:
    """Replay = copy the stored bytes through a store/transfer step (binary file copy
    into a separate directory), re-read them, and compare byte-for-byte and by SHA-256,
    also against the stored sidecar. Never parses or re-serializes."""
    record_path = Path(record_path)
    stored = record_path.read_bytes()
    with tempfile.TemporaryDirectory(dir=workdir) as tmp:
        replay_path = Path(tmp) / record_path.name
        shutil.copyfile(record_path, replay_path)
        replayed = replay_path.read_bytes()
    sc = sidecar_path(record_path)
    sidecar = sc.read_bytes() if sc.is_file() else b""
    return ReplayResult(
        path=str(record_path),
        sha256_stored=sha256_hex(stored),
        sha256_replayed=sha256_hex(replayed),
        bytes_equal=stored == replayed,
        sidecar_match=sidecar == (sha256_hex(replayed) + "\n").encode("ascii"),
    )
