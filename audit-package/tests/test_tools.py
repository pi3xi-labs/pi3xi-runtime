import subprocess
import sys
import zipfile

from conftest import PACKAGE_ROOT

TOOLS = PACKAGE_ROOT / "tools"


def run(tool, *args, check=True):
    return subprocess.run([sys.executable, str(TOOLS / tool), *args], check=check, capture_output=True, text=True)


def test_verify_hashes_passes_on_committed_fixtures():
    r = run("verify_hashes.py")
    assert r.returncode == 0
    assert "0 failure(s)" in r.stdout
    assert "fixtures/failure" not in r.stdout
    assert "examples/" not in r.stdout


def test_verify_hashes_output_codes(tmp_path, monkeypatch, capsys):
    sys.path.insert(0, str(TOOLS))
    import verify_hashes
    fix = tmp_path / "fixtures"
    for sub in ("success", "baseline", "vectors"):
        (fix / sub).mkdir(parents=True)
    (fix / "success" / "a.json").write_bytes(b"{}\n")
    (fix / "success" / "b.json").write_bytes(b"{}\n")
    (fix / "success" / "b.json.sha256").write_bytes(b"ABC\n")
    (fix / "baseline" / "c.json").write_bytes(b"{}\n")
    (fix / "baseline" / "c.json.sha256").write_bytes(b"0" * 64 + b"\n")
    (fix / "vectors" / "vectors.json").write_text('{"vectors": []}\n')
    monkeypatch.setattr(verify_hashes, "FIX", fix)
    monkeypatch.setattr(verify_hashes._paths, "PACKAGE_ROOT", tmp_path)
    verify_hashes.main()
    out = capsys.readouterr().out
    assert "FAIL HASH_FILE_MISSING fixtures/success/a.json" in out
    assert "FAIL HASH_FORMAT_INVALID fixtures/success/b.json" in out
    assert "FAIL HASH_MISMATCH fixtures/baseline/c.json" in out


def test_audit_package_zip_is_deterministic(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "audit.log").write_text("SUMMARY result=PASS\n")
    a, b = tmp_path / "a.zip", tmp_path / "b.zip"
    run("build_audit_package.py", "--out", str(a), "--reports-dir", str(reports))
    run("build_audit_package.py", "--out", str(b), "--reports-dir", str(reports))
    assert a.read_bytes() == b.read_bytes()
    with zipfile.ZipFile(a) as zf:
        infos = zf.infolist()
        names = [i.filename for i in infos]
        assert names == sorted(names)
        assert all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in infos)
        assert all((i.external_attr >> 16) & 0o777 == 0o644 for i in infos)
        for required in ("README.md", "rfc/RFC-AUDIT-001.md", "spec/canonical-serialization-v1.md",
                         "schemas/negative-fixture.schema.json", "matrices/compatibility-matrix.csv",
                         "fixtures/vectors/vectors.json", "docs/responsibility-boundary.md", "docs/topology.md",
                         "rfc/RFC-INVARIANT-001.md", "matrices/audit-template.csv", "reports/audit.log"):
            assert required in names, required
        assert not any(n.startswith(("src/", "tests/", "tools/")) for n in names)


def test_audit_package_zip_without_reports(tmp_path):
    out = tmp_path / "x.zip"
    run("build_audit_package.py", "--out", str(out), "--no-reports")
    with zipfile.ZipFile(out) as zf:
        assert not any(n.startswith("reports/") for n in zf.namelist())
