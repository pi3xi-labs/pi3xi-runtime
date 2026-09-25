# F.2 Audit Package v0.1 (Draft)

Byte-level fixity checks for Pi³XI Canonical Records defined by F.1 (`runtime-contract-v1.0`).

> **Draft, branch `f2-audit`.** This package does not amend the F.1 contract. It adds a byte format, integrity sidecars, replay checks, negative fixtures, and control matrices.

## Boundary with F.1

| F.1 (unchanged, tag `runtime-contract-v1.0` @ `103ae89`)             | F.2 (this directory)                                             |
|------------------------------------------------------------------------|------------------------------------------------------------------|
| Record structure: `schemas/canonical-record.schema.json`               | Used unmodified as the structural check (`TYPE_MISMATCH`)        |
| Guarantees G1 to G4, invariant reserved and opaque                     | Byte identity, `.sha256` sidecar, replay byte/SHA equality       |
| `tools/validate_runtime.py`, `runtime-check.yml`                       | `tools/audit.py`, `tests/`, `audit-package.yml`                  |
| `docs/canonical-record-fixity.md` (Draft v0.1)                         | superseded for F.2 by `spec/fixity-rules-v0.2.md`                |

`tests/test_f1_boundary.py` pins the SHA-256 of every F.1 file and fails if any of them changes.

## Layout

```
audit-package/
  spec/        canonical-serialization-v1.md, fixity-rules-v0.2.md, audit-model-v0.2.md,
               rejection-reasons.md, rejection-reasons.json (registry)
  schemas/     rejection-reason.schema.json, negative-fixture.schema.json
  src/pi3xi_audit/  errors.py, canonical.py, verify.py, fixtures.py
  tools/       audit.py, generate_success_fixtures.py, generate_negative_cases.py, generate_test_vectors.py
  fixtures/    success/ (4), baseline/ (1), failure/ (27 x NEG-XXX), vectors/vectors.json
  tests/       pytest suite
  matrices/    5 control matrices (CSV) + README.md
```

## Run Locally

Requires Python 3.11 or later. Run from `audit-package/`:

```
pip install -r requirements-dev.txt

# regenerate fixtures and vectors; the committed files must not change
python tools/generate_success_fixtures.py
python tools/generate_negative_cases.py
python tools/generate_test_vectors.py
git diff --exit-code -- . && test -z "$(git status --porcelain -- .)"

pytest --junitxml=reports/pytest.xml
python tools/audit.py --reports-dir reports
```

Expected output:

- `generate_negative_cases.py` prints `NEG-001 OK …` through `NEG-027 OK …` and `27 negative case(s) generated`.
- `pytest` reports all tests passed.
- `tools/audit.py` prints `SUMMARY positives=5 negatives=27 vectors=10 comparisons=10 failures=0 result=PASS` and writes `reports/hash.log`, `reports/replay.log`, and `reports/audit.log`.
- `reports/` is not committed (`.gitignore`). CI uploads it as an artifact.

## Key Decisions (Locked)

- **Identity:** SHA-256 of the exact file bytes. Records are never re-serialized for identity or replay.
- **File format:** UTF-8, no BOM, compact JSON, exactly one final LF, top-level order `intent, event, observe, meta, invariant`.
  - The numeric lexical form is identity: `1`, `1.0`, and `1e0` are distinct.
  - No Unicode normalization. Duplicate keys are forbidden.
- **Hash placement:** `<name>.json.sha256`, containing 64 lowercase hex characters and one LF (65 bytes). There is no hash field inside records.
- **Replay:** re-read the stored bytes, then compare byte-for-byte and by SHA-256.
- **Version fields:** `contract_version`, `schema_version`, and `record_version` are not in v1 records. They are described as a future record format only.

## Examples Are Illustrative

All fixtures derive from the F.1 illustrative examples (see `fixtures/success/README.md`). They are not logs of a real runtime.
