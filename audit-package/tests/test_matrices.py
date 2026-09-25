import ast
import csv
import re

import pytest
from conftest import PACKAGE_ROOT

MATRICES = PACKAGE_ROOT / "matrices"
NAMES = ["record-controls", "replay-controls", "invariant-controls", "hash-controls", "release-controls"]
COLUMNS = ["ID", "Category", "Control", "Description", "ExpectedResult", "ObservedResult", "Owner",
           "Evidence", "RiskLevel", "Status", "LastVerified", "TestRef"]
TEMPLATE = "audit-template"
TEMPLATE_COLUMNS = ["ID", "Category", "Control", "Description", "ExpectedResult", "ObservedResult", "Owner",
                    "Evidence", "RiskLevel", "Status", "LastVerified", "Notes"]
TEMPLATE_IDS = ["A-01", "A-02", "A-03", "A-04", "B-01", "B-02", "C-01", "C-02", "D-01", "D-02",
                "E-01", "E-02", "X-01", "X-02", "X-03", "X-04"]
TEMPLATE_EXPECTED = {"PASS", "FAIL", "Not implemented"}
# A CI evidence token: "CI run <numeric run id> @<commit sha, 7 to 40 hex>".
CI_TOKEN = re.compile(r"^CI run [0-9]+ @[0-9a-f]{7,40}$")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
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
    assert sorted(p.stem for p in MATRICES.glob("*.csv")) == sorted(NAMES + ["compatibility-matrix", TEMPLATE])
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
        ci = [e for e in ev if CI_TOKEN.match(e)]
        assert set(ev) - set(ci) <= REPORTS, r["ID"]
        if r["Status"] == "Planned":
            assert not ev, f"{r['ID']}: planned control must not claim evidence"
        else:
            assert set(ev) - set(ci), f"{r['ID']}: non-planned control needs a report name"
        if r["Status"] != "Verified":
            assert not ci, f"{r['ID']}: CI run evidence only belongs to Verified controls"


def test_matrix_verified_requires_ci_evidence():
    for _, r in rows():
        if r["Status"] != "Verified":
            continue
        ev = [e for e in r["Evidence"].split(";") if e]
        assert len([e for e in ev if CI_TOKEN.match(e)]) == 1, f"{r['ID']}: Verified needs one CI run token"
        assert DATE.match(r["LastVerified"]), r["ID"]
        assert r["ObservedResult"].startswith("PASS"), r["ID"]
        assert r["TestRef"], f"{r['ID']}: Verified needs TestRef"


def test_matrix_last_verified_rule():
    for _, r in rows():
        if r["Status"] != "Verified":
            assert r["LastVerified"] == "", r["ID"]
            assert r["ObservedResult"] == "", r["ID"]
        else:
            assert r["LastVerified"], r["ID"]


def test_matrix_release_manual_controls_stay_planned():
    status = {r["ID"]: r["Status"] for _, r in rows()}
    for i in ("REL-005", "REL-006", "REL-007", "REL-008"):
        assert status[i] == "Planned", i


def read_template():
    header, *body = read(TEMPLATE)
    return header, [dict(zip(header, r)) for r in body]


def test_template_columns_and_ids():
    header, body = read_template()
    assert header == TEMPLATE_COLUMNS
    assert [r["ID"] for r in body] == TEMPLATE_IDS
    assert all(len(r) == len(TEMPLATE_COLUMNS) for r in body)


def test_template_is_blank():
    _, body = read_template()
    for r in body:
        assert r["ObservedResult"] == "" and r["Evidence"] == "" and r["LastVerified"] == "", r["ID"]
        assert r["Status"] == "Planned", r["ID"]
        assert r["ExpectedResult"] in TEMPLATE_EXPECTED, r["ID"]
        assert r["RiskLevel"] in RISK, r["ID"]
        assert all(r[c].strip() for c in ("Category", "Control", "Description", "Owner")), r["ID"]


def test_template_absent_runtimes_not_implemented():
    _, body = read_template()
    by_id = {r["ID"]: r for r in body}
    assert by_id["X-01"]["ExpectedResult"] == "PASS"
    for i in ("X-02", "X-03", "X-04"):
        assert by_id[i]["ExpectedResult"] == "Not implemented", i
    for i in ("E-01", "E-02"):
        assert by_id[i]["Owner"] == "Maintainer", i


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
