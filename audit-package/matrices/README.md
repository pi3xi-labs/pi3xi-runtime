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

## Audit Readiness Checklist

| Check | Status | Basis |
|-------|--------|-------|
| Audit scope documented | Yes | `README.md`, `docs/responsibility-boundary.md`, `rfc/RFC-AUDIT-001.md` |
| Verification matrices present | Yes | 5 control CSVs, `compatibility-matrix.csv`, `audit-template.csv`; checked by `tests/test_matrices.py::test_matrix_files_present` |
| Control-matrix statuses | Verified or Planned only (0 Implemented) | 29 Verified, 4 Planned. `Implemented` is still an allowed value (`tests/test_matrices.py`, `STATUS`) |
| Evidence recorded for all Verified rows | Yes | Enforced by `tests/test_matrices.py::test_matrix_verified_requires_ci_evidence` |
| CI run id recorded | Yes | `CI run 36130810196` in the `Evidence` column |
| Commit SHA recorded | Yes | `@4691767` in the `Evidence` column (full SHA `46917671961a28800cb7aeb0a8aebffc72031254` above) |
| Test artifact reference recorded | Yes | `pytest.xml` in the `Evidence` column (artifacts `audit-reports-py3.11`, `audit-reports-py3.12`) |
| Python versions documented | Yes | 3.11 and 3.12 (`.github/workflows/audit-package.yml` matrix, `ObservedResult` column) |
| Re-verification evidence | Yes | Run 36131874712 at commit `8249b62`: success on 3.11 and 3.12 |
| Mermaid diagrams | Render locally; labels quoted | Rendered without errors with `@mermaid-js/mermaid-cli` on 2026-09-25. Quoting of labels with parentheses, `³` or `<br/>` is enforced by `tests/test_docs.py::test_mermaid_labels_quoted`. Rendering is not part of CI. |
| Terminology | Documented | `docs/topology.md`: Provence is the Knowledge Governance layer (an intentional name, not "Provenance") |
| License | CC0 1.0 Universal | Repository `LICENSE` is "Creative Commons Legal Code, CC0 1.0 Universal". It covers docs and code alike. A split between CC0 docs and MIT code is only an idea for the planned Bagua/Provence repositories and does not apply here. |
| Planned items separated | Yes | REL-005 to REL-008; enforced by `tests/test_matrices.py::test_matrix_release_manual_controls_stay_planned` |
| Change history recorded | Yes | "Change History" section below |

## Final Audit Matrix Delta

| Item | Value |
|------|-------|
| Controls changed | 29, from `Implemented` to `Verified`. The previous status was checked in git history: before commit `8249b62` all 29 were `Implemented`. |
| Evidence run | `audit-package` run 36130810196 |
| Evidence commit | `4691767` (`46917671961a28800cb7aeb0a8aebffc72031254`) |
| Evidence run completed | 2026-09-25 20:42:19 JST (11:42:19 UTC) |
| Python versions | 3.11, 3.12 |
| Tests in evidence run | 249 passed, 0 failed, 0 skipped (both versions) |
| Re-verification run | `audit-package` run 36131874712 at commit `8249b62` (`8249b629efd9831a91d18031601213cc2af8b0c6`), completed 2026-09-25 20:53:55 JST. Success on 3.11 and 3.12, with 259 tests (10 added in that commit). |
| Still Planned | REL-005, REL-006, REL-007, REL-008 |
| Column added | `ObservedResult` (five control matrices) |
| File added | `audit-template.csv` |

## Change History

### 2026-09-25

- 29 controls were updated from `Implemented` to `Verified` based on `audit-package` run 36130810196 (commit `4691767`, completed 20:42:19 JST, Python 3.11 and 3.12, 249 tests passed).
- Subsequently re-verified by run 36131874712 (commit `8249b62`, completed 20:53:55 JST, 259 tests passed).
- The `ObservedResult` column and `audit-template.csv` were added in the same change.

## Audit Status Summary

As of 2026-09-25, every control supported by automated CI evidence is marked `Verified`. REL-005 through REL-008 remain `Planned`. They are manual release steps and are excluded from current verification claims.
