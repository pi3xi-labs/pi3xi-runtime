"""Helpers for negative fixtures (fixtures/failure/NEG-XXX/)."""

import json
import shutil
import tempfile
from pathlib import Path

from .verify import audit_record


def load_meta(case_dir):
    return json.loads((Path(case_dir) / "meta.json").read_text(encoding="utf-8"))


def record_bytes(case_dir) -> bytes:
    """Exact candidate bytes of a negative fixture (decodes record.json.hex if used)."""
    case_dir = Path(case_dir)
    meta = load_meta(case_dir)
    raw = (case_dir / meta["record"]).read_bytes()
    if meta["record_encoding"] == "hex":
        return bytes.fromhex(raw.decode("ascii").strip())
    return raw


def materialize(case_dir, baseline_path):
    """Audit a negative fixture: copy its exact bytes (and sidecar, if any) to a
    temporary directory as record.json / record.json.sha256 and audit against the baseline."""
    case_dir = Path(case_dir)
    meta = load_meta(case_dir)
    with tempfile.TemporaryDirectory() as tmp:
        rec = Path(tmp) / "record.json"
        rec.write_bytes(record_bytes(case_dir))
        if meta["sidecar"]:
            shutil.copyfile(case_dir / meta["sidecar"], Path(tmp) / "record.json.sha256")
        result = audit_record(rec, baseline_path)
    result.path = str(case_dir / meta["record"])
    return result


def negative_cases(failure_dir):
    return sorted(p for p in Path(failure_dir).glob("NEG-*") if p.is_dir())
