import csv

from conftest import PACKAGE_ROOT
from test_matrices import _test_functions

PATH = PACKAGE_ROOT / "matrices" / "compatibility-matrix.csv"
COLUMNS = ["ID", "Control", "Level", "Expected", "Python", "Rust", "Node", "Go", "Evidence"]
LEVELS = {"L0", "L1", "L2", "L3"}
CELL = {"PASS", "FAIL", "Not run", "Not implemented"}
# Runtimes with no implementation in this repository. PASS/FAIL/Not run are forbidden for them.
ABSENT_RUNTIMES = ["Rust", "Node", "Go"]


def load():
    with open(PATH, newline="", encoding="utf-8") as f:
        header, *body = list(csv.reader(f))
    return header, [dict(zip(header, r)) for r in body]


def test_columns_and_ids():
    header, rows = load()
    assert header == COLUMNS
    assert [r["ID"] for r in rows] == [f"X-{i:02d}" for i in range(1, len(rows) + 1)]
    assert len(rows) >= 10


def test_allowed_values():
    _, rows = load()
    for r in rows:
        assert r["Level"] in LEVELS, r["ID"]
        for rt in ["Python"] + ABSENT_RUNTIMES:
            assert r[rt] in CELL, (r["ID"], rt)


def test_absent_runtimes_never_claim_results():
    _, rows = load()
    for r in rows:
        for rt in ABSENT_RUNTIMES:
            assert r[rt] == "Not implemented", (r["ID"], rt)


def test_python_pass_backed_by_existing_tests():
    _, rows = load()
    for r in rows:
        refs = [t for t in r["Evidence"].split(";") if t]
        if r["Python"] == "PASS":
            assert refs, f"{r['ID']}: PASS needs test evidence"
        for ref in refs:
            file, func = ref.split("::")
            path = PACKAGE_ROOT / file
            assert path.is_file(), ref
            assert func in _test_functions(path), ref


def test_levels_cover_f2_targets():
    _, rows = load()
    assert {r["Level"] for r in rows} == LEVELS
