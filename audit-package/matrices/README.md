# Control Matrices (F.2 Audit Package v0.1)

Five control matrices, one compatibility matrix, and one blank audit template (UTF-8, LF line endings, RFC 4180 quoting):

| File                     | ID prefix | Scope                                              |
|--------------------------|-----------|----------------------------------------------------|
| `record-controls.csv`    | `REC-`    | byte format, structure, numeric identity, isolation |
| `replay-controls.csv`    | `RPL-`    | replay byte and SHA-256 equality                   |
| `invariant-controls.csv` | `INV-`    | invariant presence, type, value, opacity           |
| `hash-controls.csv`      | `HSH-`    | sidecar integrity and format, test vectors         |
| `release-controls.csv`   | `REL-`    | reproducibility, F.1 boundary, release steps       |
| `compatibility-matrix.csv` | `X-`    | cross-runtime compatibility (RFC-AUDIT-001)        |
| `audit-template.csv`     | `A-` to `E-`, `X-` | blank audit table to fill in             |

## Columns

`ID,Category,Control,Description,ExpectedResult,ObservedResult,Owner,Evidence,RiskLevel,Status,LastVerified,TestRef`

| Column         | Rule |
|----------------|------|
| `ID`           | Unique across all matrices; prefix per file. |
| `Category`     | Control family. These categories are always `Critical`: Byte Identity, Numeric Identity, Hash Integrity, Replay Byte Equality, Replay Hash Equality, Invariant Lock, Invariant Presence, Invariant Type, Runtime Isolation. |
| `ObservedResult` | Added column. What CI actually observed. Empty unless `Status` is `Verified`; for `Verified` it starts with `PASS`. |
| `Evidence`     | `;`-separated items. Each item is a report name (`pytest.xml`, `replay.log`, `hash.log`, `audit.log`, from the CI artifact `reports/`) or one CI token `CI run <run id> @<commit>`. `Planned` controls have no evidence. Non-planned controls name at least one report. The CI token only appears on `Verified` controls. |
| `RiskLevel`    | `Critical`, `High`, `Medium`, or `Low`. |
| `Status`       | `Planned`, `Implemented`, or `Verified`. **Planned** means a manual or release step not yet performed. **Implemented** means backed by tests that run in CI, with no CI result recorded yet. **Verified** means the TestRef tests passed in a recorded CI run: the row needs the CI token in `Evidence`, a `LastVerified` date, a `PASS` `ObservedResult`, and a TestRef. |
| `LastVerified` | `YYYY-MM-DD` of the CI run for `Verified` controls; empty otherwise. |
| `TestRef`      | Added column. `;`-separated pytest references `tests/<file>.py::<function>`. Required for `Implemented`, empty for `Planned`. |

The rules are enforced by `tests/test_matrices.py`. It checks the columns, unique IDs, allowed values, the evidence rules, the Verified rules (CI token, date, ObservedResult, TestRef), the LastVerified rule, the Critical categories, that REL-005 to REL-008 stay Planned, and that every TestRef names an existing test function.

## Verified Status and Its CI Evidence

Every control that was Implemented is now **Verified**, cited as `CI run 36130810196 @4691767`:

- Workflow `audit-package`, run 36130810196, on commit `46917671961a28800cb7aeb0a8aebffc72031254`.
- Both jobs passed, `audit (3.11)` and `audit (3.12)`, with `249 passed` and no failures or skips. The results are in the `pytest.xml` of the artifacts `audit-reports-py3.11` and `audit-reports-py3.12`.
- `LastVerified` is 2026-09-25.

That run happened **before** the commit that records it, since a commit cannot cite a CI run of itself. The run on the new head checks the same TestRef tests again. If it fails, the affected rows go back to `Implemented`. No control is marked Verified without a passing CI test, and REL-005 to REL-008 (manual release steps) stay Planned.

## Counts (v0.1)

33 controls in total: 29 Verified, 0 Implemented, 4 Planned.

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

## Audit Template

`audit-template.csv` is a blank audit table for a manual or release audit. It has 16 rows:

- A-01 to A-04: Record
- B-01 and B-02: Replay
- C-01 and C-02: Invariant
- D-01 and D-02: Hash
- E-01 and E-02: Release (Owner Maintainer)
- X-01: Python, expected PASS
- X-02 to X-04: Rust, Node, Go, expected `Not implemented`

Columns: `ID,Category,Control,Description,ExpectedResult,ObservedResult,Owner,Evidence,RiskLevel,Status,LastVerified,Notes`

In `ExpectedResult`, `PASS` means the input is accepted and `FAIL` means the audit rejects it with the code named in `Notes`.

Fill it in three steps:

1. **Design.** Keep ID, Category, Control, Description, ExpectedResult, Owner, and RiskLevel as committed. Status is `Planned`.
2. **Observation.** Run the audit (CI, or `tools/audit.py` from a fresh clone). Record the actual outcome in `ObservedResult`.
3. **Evidence.** Cite the evidence (`CI run <id> @<commit>` plus report names) and set `LastVerified`. Set `Status` to `Verified` only if the evidence is a passing CI run. A local run or a conversation is not enough.

The committed file stays blank: ObservedResult, Evidence, and LastVerified are empty, and every Status is `Planned`. `tests/test_matrices.py` enforces this. Filled copies belong with the audit record of a release. They are not committed over the template.
