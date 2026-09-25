import pytest
from conftest import FIXTURES

from pi3xi_audit.errors import ACTIVE_CODES, RESERVED_CODES, ValidationError
from pi3xi_audit.fixtures import load_meta, negative_cases


def test_every_active_code_has_fixture():
    covered = {load_meta(c)["expected_reason"] for c in negative_cases(FIXTURES / "failure")}
    missing = [c for c in ACTIVE_CODES if c not in covered]
    assert not missing, missing


def test_reserved_codes_not_emitted():
    covered = {load_meta(c)["expected_reason"] for c in negative_cases(FIXTURES / "failure")}
    assert not covered & set(RESERVED_CODES)
    for code in RESERVED_CODES:
        with pytest.raises(ValueError):
            ValidationError(code)
