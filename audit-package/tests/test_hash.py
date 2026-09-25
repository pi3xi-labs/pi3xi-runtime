import hashlib

import pytest
from conftest import code_of, positive_files

from pi3xi_audit.canonical import sha256_hex
from pi3xi_audit.verify import sidecar_path, verify_hash_pair


def test_identity_is_sha256_of_exact_bytes(baseline_bytes):
    assert sha256_hex(baseline_bytes) == hashlib.sha256(baseline_bytes).hexdigest()
    assert sha256_hex(baseline_bytes) != sha256_hex(baseline_bytes[:-1])  # the final LF is hashed


@pytest.mark.parametrize("path", positive_files(), ids=lambda p: p.name)
def test_positive_sidecars_match(path):
    side = sidecar_path(path).read_bytes()
    assert len(side) == 65
    assert code_of(verify_hash_pair, path.read_bytes(), side) is None


def test_hash_missing(baseline_bytes):
    assert code_of(verify_hash_pair, baseline_bytes, None) == "HASH_FILE_MISSING"


@pytest.mark.parametrize("mutate", [
    lambda s: s.upper(),
    lambda s: s[:-1],
    lambda s: s[:-1] + b"\r\n",
    lambda s: s[:-1] + b"  record.json\n",
    lambda s: s[1:],
    lambda s: s + b"\n",
    lambda s: b"",
], ids=["upper", "no-lf", "crlf", "sha256sum-style", "63-hex", "extra-lf", "empty"])
def test_sidecar_format_exact(baseline_bytes, mutate):
    side = (sha256_hex(baseline_bytes) + "\n").encode()
    assert code_of(verify_hash_pair, baseline_bytes, mutate(side)) == "HASH_FORMAT_INVALID"


def test_hash_mismatch(baseline_bytes):
    other = (sha256_hex(baseline_bytes + b"x") + "\n").encode()
    assert code_of(verify_hash_pair, baseline_bytes, other) == "HASH_MISMATCH"
