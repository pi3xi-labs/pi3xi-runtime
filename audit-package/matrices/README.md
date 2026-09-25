# Control Matrices (F.2 Audit Package v0.1)

Five control matrices plus one compatibility matrix (UTF-8, LF line endings, RFC 4180 quoting):

| File                     | ID prefix | Scope                                              |
|--------------------------|-----------|----------------------------------------------------|
| `record-controls.csv`    | `REC-`    | byte format, structure, numeric identity, isolation |
| `replay-controls.csv`    | `RPL-`    | replay byte and SHA-256 equality                   |
| `invariant-controls.csv` | `INV-`    | invariant presence, type, value, opacity           |
| `hash-controls.csv`      | `HSH-`    | sidecar integrity and format, test vectors         |
| `release-controls.csv`   | `REL-`    | reproducibility, F.1 boundary, release steps       |

## Columns

`ID,Category,Control,Description,ExpectedResult,Owner,Evidence,RiskLevel,Status,LastVerified,TestRef`

| Column         | Rule |
|----------------|------|
| `ID`           | Unique across all matrices; prefix per file. |
| `Category`     | Control family. These categories are always `Critical`: Byte Identity, Numeric Identity, Hash Integrity, Replay Byte Equality, Replay Hash Equality, Invariant Lock, Invariant Presence, Invariant Type, Runtime Isolation. |
| `Evidence`     | `;`-separated names from the reports list: `pytest.xml`, `replay.log`, `hash.log`, `audit.log` (CI artifact `reports/`). Empty only for `Planned` controls. |
| `RiskLevel`    | `Critical`, `High`, `Medium`, or `Low`. |
| `Status`       | `Planned`, `Implemented`, or `Verified`. **Implemented** means backed by tests that run in CI. **Planned** means a manual or release step not yet performed. **Verified** is reserved for a recorded human verification. |
| `LastVerified` | Empty unless `Status` is `Verified`. All values are empty in v0.1. |
| `TestRef`      | Added column. `;`-separated pytest references `tests/<file>.py::<function>`. Required for `Implemented`, empty for `Planned`. |

The rules are enforced by `tests/test_matrices.py`. It checks the columns, unique IDs, allowed values, that evidence names are in the reports list, the LastVerified rule, the Critical categories, and that every TestRef names an existing test function.

## Counts (v0.1)

33 controls in total: 29 Implemented, 4 Planned, 0 Verified.

| File      | Controls |
|-----------|----------|
| record    | 11 |
| replay    | 4  |
| invariant | 5  |
| hash      | 5  |
| release   | 8  |

The Planned controls are:

- REL-005 fresh clone verification
- REL-006 tag verification
- REL-007 audit bundle
- REL-008 CI hardening review

## Compatibility Matrix

`compatibility-matrix.csv` tracks cross-runtime compatibility as defined in `rfc/RFC-AUDIT-001.md`.

Columns: `ID,Control,Level,Expected,Python,Rust,Node,Go,Evidence`

| Column | Rule |
|--------|------|
| `Level` | `L0` Schema, `L1` Validation (same rejection code), `L2` Replay (same bytes), `L3` Identity (same SHA-256). |
| Runtime cells | `PASS`, `FAIL`, `Not run`, or `Not implemented`. |
| `Evidence` | `;`-separated pytest references. A `PASS` cell requires at least one, and each must name an existing test function that runs in CI. |

Rust, Node, and Go have no implementation in this repository, so their cells are `Not implemented`. The test suite rejects any other value for them.

The matrix has 10 rows (X-01 to X-10), and Python is `PASS` on all of them. `tests/test_compatibility_matrix.py` enforces these rules.
