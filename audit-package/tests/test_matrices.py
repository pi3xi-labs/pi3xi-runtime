import ast
import csv

import pytest
from conftest import PACKAGE_ROOT

MATRICES = PACKAGE_ROOT / "matrices"
NAMES = ["record-controls", "replay-controls", "invariant-controls", "hash-controls", "release-controls"]
COLUMNS = ["ID", "Category", "Control", "Description", "ExpectedResult", "Owner", "Evidence",
           "RiskLevel", "Status", "LastVerified", "TestRef"]
RISK = {"Critical", "High", "Medium", "Low"}
STATUS = {"Planned", "Implemented", "Verified"}
REPORTS = {"pytest.xml", "replay.log", "hash.log", "audit.log"}
CRITICAL_CATEGORIES = {"Byte Identity", "Numeric Identity", "Hash Integrity", "Replay Byte Equality",
                       "Replay Hash Equality", "Invariant Lock", "Invariant Presence", "Invariant Type",
                       "Runtime Isolation"}
PREFIX = {"record-controls": "REC", "replay-controls": "RPL", "invariant-controls": "INV",
          "hash-controls": "HSH", "release-controls": "REL"}


def read(name):
    with open(MATRICES / f"{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def rows():
    out = []
    for n in NAMES:
        header, *body = read(n)
        out += [(n, dict(zip(header, r))) for r in body]
    return out


def test_matrix_files_present():
    assert sorted(p.stem for p in MATRICES.glob("*.csv")) == sorted(NAMES + ["compatibility-matrix"])
    assert (MATRICES / "README.md").is_file()


@pytest.mark.parametrize("name", NAMES)
def test_matrix_columns(name):
    header, *body = read(name)
    assert header == COLUMNS
    assert body
    assert all(len(r) == len(COLUMNS) for r in body)


def test_matrix_ids_unique_and_prefixed():
    ids = [r["ID"] for _, r in rows()]
    assert len(ids) == len(set(ids))
    for n, r in rows():
        assert r["ID"].startswith(PREFIX[n] + "-")


def test_matrix_allowed_values():
    for _, r in rows():
        assert r["RiskLevel"] in RISK, r["ID"]
        assert r["Status"] in STATUS, r["ID"]
        assert all(r[c].strip() for c in ("Category", "Control", "Description", "ExpectedResult", "Owner")), r["ID"]


def test_matrix_evidence_in_reports_list():
    for _, r in rows():
        ev = [e for e in r["Evidence"].split(";") if e]
        assert set(ev) <= REPORTS, r["ID"]
        if r["Status"] != "Planned":
            assert ev, f"{r['ID']}: non-planned control needs evidence"


def test_matrix_last_verified_rule():
    for _, r in rows():
        if r["Status"] != "Verified":
            assert r["LastVerified"] == "", r["ID"]
        else:
            assert r["LastVerified"], r["ID"]


def test_matrix_critical_categories():
    for _, r in rows():
        if r["Category"] in CRITICAL_CATEGORIES:
            assert r["RiskLevel"] == "Critical", r["ID"]


def _test_functions(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}


def test_matrix_testrefs_exist_and_status_consistent():
    for _, r in rows():
        refs = [t for t in r["TestRef"].split(";") if t]
        if r["Status"] == "Planned":
            assert not refs, f"{r['ID']}: planned control must not claim tests"
        else:
            assert refs, f"{r['ID']}: implemented control needs TestRef"
        for ref in refs:
            file, func = ref.split("::")
            path = PACKAGE_ROOT / file
            assert path.is_file(), ref
            assert func in _test_functions(path), ref
