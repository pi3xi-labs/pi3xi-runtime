# Audit Model (Draft v0.2, F.2)

> **Draft for Phase F.2. Does not amend `runtime-contract-v1.0`.** It complements F.1 `docs/audit-model.md`: G1 to G4 stay as defined in F.1, and F.2 adds byte-level evidence.

## Positive Tests

Every file in `fixtures/success/` and `fixtures/baseline/` must pass the format and hash stages. The baseline must also compare as identical to itself.

- The success fixtures are the F.1 illustrative example records, converted to canonical bytes by `tools/generate_success_fixtures.py`. The conversion removes whitespace outside strings; lexemes are copied verbatim.
- Tests: `tests/test_positive.py`, `tests/test_format.py`, `tests/test_hash.py`.

## Negative Tests

Each fixture in `fixtures/failure/NEG-XXX/` applies **exactly one mutation** to the baseline record bytes. For hash-stage cases the mutation applies to the baseline sidecar bytes instead.

Each fixture has a `meta.json` (validated by `schemas/negative-fixture.schema.json`) containing:

- `failure_id`
- `stage`
- `expected_reason`
- the mutation description

The audit's primary code must equal `expected_reason`. Tests: `tests/test_negative.py` and `tests/test_reason_coverage.py`.

Current count: **27 fixtures covering all 22 active codes.**

| Stage    | Fixtures | Codes |
|----------|----------|-------|
| format   | 13       | 12    |
| hash     | 4        | 3     |
| baseline | 10       | 7     |

## Replay: Byte Equality

For every positive record, the stored bytes are copied through a store/transfer step and re-read. The replayed bytes must equal the stored bytes exactly. No parsing is involved.

Tests: `tests/test_replay.py`. Evidence: `reports/replay.log`.

## Replay: SHA-256 Equality

The SHA-256 of the replayed bytes must equal the SHA-256 of the stored bytes and the sidecar content.

Evidence: `reports/replay.log` and `reports/hash.log`.

## Evidence Mapping

| Evidence             | Produced by                                  | Shows                                                                              |
|----------------------|----------------------------------------------|------------------------------------------------------------------------------------|
| `reports/pytest.xml` | `pytest --junitxml=reports/pytest.xml`       | every test result                                                                  |
| `reports/hash.log`   | `tools/audit.py`                             | hash-stage result per positive record and per negative fixture                     |
| `reports/replay.log` | `tools/audit.py`                             | bytes_equal, sha256_stored, sha256_replayed, sidecar_match per positive record     |
| `reports/audit.log`  | `tools/audit.py`                             | positive results, expected vs actual reason per negative fixture, vector checks (sha256, verdict, comparisons per raw vector file), summary |

Before pytest, CI runs `tools/verify_hashes.py` (step `Verify SHA-256 sidecars`). It checks every `.json` + `.json.sha256` pair under `fixtures/success`, `fixtures/baseline`, and `fixtures/vectors`, plus the digests in the vector index. `fixtures/failure` is excluded because its pairs are deliberately broken; `tests/test_negative.py` checks them instead.

Reports are CI artifacts and are not committed. CI also packages them into the deterministic `audit-package-v0.1.zip` (`tools/build_audit_package.py`). The control matrices (`matrices/*.csv`) map each control to its evidence and backing tests.

## Relation to F.1 Guarantees

| F.1 guarantee                 | F.2 evidence                                                                                              |
|-------------------------------|-----------------------------------------------------------------------------------------------------------|
| G1 event ordering             | not re-checked (F.1 validator); the record format keeps `event.sequence` lexemes byte-exact              |
| G2 observation persistence    | immutability: byte identity plus sidecar (`HASH_*` codes)                                                 |
| G3 invariant preservation     | `INVARIANT_REMOVED`, `INVARIANT_TYPE_CHANGED`, `INVARIANT_VALUE_CHANGED`, `NUMERIC_REPRESENTATION_CHANGE` versus baseline |
| G4 audit replay               | replay byte and SHA-256 equality                                                                          |
