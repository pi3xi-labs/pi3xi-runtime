import json
import os

import pytest
from conftest import PACKAGE_ROOT, positive_files

from pi3xi_audit import canonical, verify
from pi3xi_audit.verify import replay_compare


@pytest.mark.parametrize("path", positive_files(), ids=lambda p: p.name)
def test_replay_byte_and_hash_equality(path):
    r = replay_compare(path)
    assert r.bytes_equal
    assert r.sha256_stored == r.sha256_replayed
    assert r.sidecar_match
    assert r.ok


def test_replay_never_reserializes(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("json (de)serialization used during replay")
    monkeypatch.setattr(json, "loads", boom)
    monkeypatch.setattr(json, "dumps", boom)
    monkeypatch.setattr(canonical, "scan", boom)
    monkeypatch.setattr(verify, "check_format", boom)
    for p in positive_files():
        assert replay_compare(p).ok


def test_replay_detects_sidecar_mismatch(tmp_path, baseline_bytes):
    rec = tmp_path / "r.json"
    rec.write_bytes(baseline_bytes)
    (tmp_path / "r.json.sha256").write_bytes(b"0" * 64 + b"\n")
    r = replay_compare(rec)
    assert r.bytes_equal and not r.sidecar_match and not r.ok


def test_audit_does_not_modify_inputs(tmp_path):
    """Runtime isolation: running the full audit never writes to fixture files."""
    import subprocess
    import sys
    files = sorted(p for p in (PACKAGE_ROOT / "fixtures").rglob("*") if p.is_file())
    before = {p: (p.read_bytes(), os.stat(p).st_mtime_ns) for p in files}
    subprocess.run([sys.executable, str(PACKAGE_ROOT / "tools" / "audit.py"), "--reports-dir", str(tmp_path)],
                   check=True, capture_output=True)
    after_files = sorted(p for p in (PACKAGE_ROOT / "fixtures").rglob("*") if p.is_file())
    assert after_files == files
    for p in files:
        assert (p.read_bytes(), os.stat(p).st_mtime_ns) == before[p]
    assert (tmp_path / "audit.log").read_text().splitlines()[-1].endswith("result=PASS")
