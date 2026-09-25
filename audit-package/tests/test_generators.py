import filecmp
import subprocess
import sys

from conftest import FIXTURES, PACKAGE_ROOT

TOOLS = PACKAGE_ROOT / "tools"


def run(tool, *args):
    subprocess.run([sys.executable, str(TOOLS / tool), *args], check=True, capture_output=True)


def same_tree(a, b):
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    return not mismatch and not errors and all(same_tree(a / d, b / d) for d in cmp.common_dirs)


def test_negative_generator_deterministic(tmp_path):
    run("generate_negative_cases.py", "--out-dir", str(tmp_path / "a"))
    run("generate_negative_cases.py", "--out-dir", str(tmp_path / "b"))
    assert same_tree(tmp_path / "a", tmp_path / "b")
    for case in (tmp_path / "a").iterdir():
        assert same_tree(case, FIXTURES / "failure" / case.name)


def test_vector_generator_deterministic(tmp_path):
    run("generate_test_vectors.py", "--out-dir", str(tmp_path / "a"))
    run("generate_test_vectors.py", "--out-dir", str(tmp_path / "b"))
    assert same_tree(tmp_path / "a", tmp_path / "b")
    assert same_tree(tmp_path / "a", FIXTURES / "vectors")


def test_success_generator_deterministic(tmp_path):
    run("generate_success_fixtures.py", "--out-dir", str(tmp_path))
    for sub in ("success", "baseline"):
        for f in (tmp_path / sub).iterdir():
            assert f.read_bytes() == (FIXTURES / sub / f.name).read_bytes(), f.name


def test_vectors_match_implementation():
    import json

    from pi3xi_audit.canonical import sha256_hex
    vdir = FIXTURES / "vectors"
    doc = json.loads((vdir / "vectors.json").read_text(encoding="utf-8"))
    for v in doc["vectors"]:
        data = (vdir / v["file"]).read_bytes()
        assert sha256_hex(data) == v["sha256"], v["id"]
        assert len(data) == v["length_bytes"], v["id"]
        assert (vdir / (v["file"] + ".sha256")).read_bytes() == (v["sha256"] + "\n").encode()
