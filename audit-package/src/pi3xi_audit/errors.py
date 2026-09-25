"""Rejection reasons and the ValidationError type.

The registry of reason codes is spec/rejection-reasons.json (single source of truth).
"""

import json
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # audit-package/
REGISTRY_PATH = PACKAGE_ROOT / "spec" / "rejection-reasons.json"

with open(REGISTRY_PATH, encoding="utf-8") as _f:
    REASONS = json.load(_f)

REASON_BY_CODE = {r["code"]: r for r in REASONS}
PRECEDENCE = {r["code"]: r["precedence"] for r in REASONS}
ACTIVE_CODES = [r["code"] for r in REASONS if r["status"] == "active"]
RESERVED_CODES = [r["code"] for r in REASONS if r["status"] == "reserved"]


class ValidationError(Exception):
    """A record, sidecar, or baseline comparison was rejected.

    .code   one of the active reason codes in spec/rejection-reasons.json
    .stage  'format', 'hash' or 'baseline'
    .detail human-readable detail (not part of the contract)
    """

    def __init__(self, code, detail=""):
        if code not in REASON_BY_CODE or REASON_BY_CODE[code]["status"] != "active":
            raise ValueError(f"unknown or non-active reason code: {code}")
        self.code = code
        self.stage = REASON_BY_CODE[code]["stage"]
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


class BaselineError(Exception):
    """The reference (baseline) record itself is not valid. This is a usage error, not a rejection reason."""


def primary(codes):
    """Return the code with the lowest precedence number (highest priority), or None."""
    codes = list(codes)
    return min(codes, key=lambda c: PRECEDENCE[c]) if codes else None
