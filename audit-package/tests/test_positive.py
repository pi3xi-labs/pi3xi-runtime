import pytest
from conftest import BASELINE, success_files

from pi3xi_audit.verify import audit_record


def test_at_least_two_success_fixtures():
    assert len(success_files()) >= 2


@pytest.mark.parametrize("path", success_files(), ids=lambda p: p.name)
def test_success_fixtures_accepted(path):
    res = audit_record(path)
    assert res.ok, res.findings


def test_baseline_identical_to_itself():
    res = audit_record(BASELINE, BASELINE)
    assert res.ok and res.findings == []
