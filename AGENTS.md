# AGENTS.md: Orientation for AI Agents

This file is for AI coding agents working in this repository (Grok, GitHub Copilot, and others). Read it before you change anything.

## Purpose

Pi³XI defines a **Canonical Record** (`intent, event, observe, meta, invariant`) and audits it at the byte level.

- **F.1 Runtime Contract v1** defines the record. It is frozen.
- **F.2 Audit Package** checks the record bytes: serialization, identity, and replay. It emits audit evidence.

## Repository Map

| Path | Owner | State |
|------|-------|-------|
| `README.md`, `GOVERNANCE.md`, `LICENSE`, `contracts/`, `schemas/`, `examples/`, `docs/`, `releases/`, `tools/validate_runtime.py`, `.github/workflows/runtime-check.yml` | F.1 | **Frozen** at tag `runtime-contract-v1.0` (commit `103ae89`). Do not edit. |
| `audit-package/` | F.2 | Draft v0.1 (branch `f2-audit`). |
| `audit-package/rfc/` | F.2 | RFC-AUDIT-001, Distributed Runtime Compatibility (Draft); RFC-INVARIANT-001, Median Model Invariants (Draft, Governance). |
| `audit-package/spec/` | F.2 | Canonical serialization, fixity rules, audit model, rejection-code registry. |
| `audit-package/fixtures/` | F.2 | success/, baseline/, failure/ (NEG-XXX), vectors/ (TV-XXX raw bytes plus index). All generated. |
| `audit-package/matrices/` | F.2 | Control matrices, `compatibility-matrix.csv`, and the blank `audit-template.csv`. |
| `audit-package/docs/responsibility-boundary.md` | F.2 | F.1 / F.2 boundary diagram. |
| `audit-package/docs/topology.md` | F.2 | Layer topology (Observation, Bagua, Provence, Pi³XI Runtime, Audit, Identity). Informative. Bagua and Provence are planned; "Provence" is the intended name, not a typo. |
| `.github/workflows/audit-package.yml` | F.2 | F.2 CI. |

## Trust Hierarchy (When Artifacts Conflict)

Higher entries win. Fix the lower artifact, never the higher one.

1. Runtime Contract v1 (`contracts/runtime-contract-v1.json`) and the F.1 schemas (`schemas/`)
2. `audit-package/spec/canonical-serialization-v1.md`
3. `audit-package/rfc/RFC-AUDIT-001.md` and `audit-package/rfc/RFC-INVARIANT-001.md` (same level)
4. Rejection-code registry: `audit-package/spec/rejection-reasons.json`
5. Test vectors: `audit-package/fixtures/vectors/`
6. CI results (`audit-package` and `runtime-check` workflows)
7. All other documentation

## Do Not Assume

- **Invariant math.** `invariant` is opaque. Do not interpret it, compute with it, or give it a schema.
- **Distance functions.** No similarity or distance between records is defined.
- **Replay regeneration.** Replay compares stored bytes. It never re-runs, regenerates, or re-serializes a record.
- **New rejection codes.** Use only `active` codes from the registry. Never emit `reserved` codes.
- **Editing frozen files.** Do not modify F.1 files or `main`, and do not create tags or releases. `audit-package/tests/test_f1_boundary.py` pins the SHA-256 of every F.1 file.
- **PASS without CI evidence.** A `PASS` in any matrix requires an existing test that runs in CI. A runtime with no implementation is `Not implemented`. A control is `Verified` only if it cites a passing CI run (`CI run <id> @<commit>`) with a `LastVerified` date. Conversation history is never evidence (RFC-INVARIANT-001, I3).
- Also: do not hand-edit generated fixtures or vectors, and do not "fix" formatting in fixture files. Their bytes are their identity.

## Rules

- **Identity:** `SHA-256(stored bytes)`, as 64 lowercase hex characters. The sidecar is `<name>.json.sha256`: 64 hex characters plus LF. Never parse and re-serialize before hashing. `1`, `1.0`, and `1e0` are distinct, and there is no Unicode normalization.
- **Replay:** re-read the stored bytes, then compare byte-for-byte and by SHA-256 with the reference.
- **Validation:** exactly one primary rejection code per failing input, chosen by registry precedence (lowest number wins). The stages are format, then hash, then baseline.
- **Compatibility:** implementations may differ; audit results (identity, replay result, rejection code) must not. The levels are L0 Schema, L1 Validation, L2 Replay, and L3 Identity (RFC-AUDIT-001). All runtimes use the same shared vector set.

## How to Verify State

```
cd audit-package
pip install -r requirements-dev.txt          # jsonschema==4.26.0, pytest==9.1.1
python tools/generate_success_fixtures.py
python tools/generate_negative_cases.py
python tools/generate_test_vectors.py
git diff --exit-code -- . && test -z "$(git status --porcelain -- .)"
python tools/verify_hashes.py                # SHA-256 sidecars
python -m pytest --junitxml=reports/pytest.xml
python tools/audit.py --reports-dir reports  # SUMMARY ... result=PASS
python tools/build_audit_package.py --out audit-package-v0.1.zip --reports-dir reports
cd .. && python tools/validate_runtime.py     # F.1 validator
```

CI runs `.github/workflows/audit-package.yml` on Python 3.11 and 3.12 with these steps:

1. Regenerate
2. Verify SHA-256 sidecars
3. Tests
4. Audit
5. Build ZIP
6. Upload the reports and ZIP artifacts

`runtime-check.yml` covers F.1.

## Primary Artifacts

- `contracts/runtime-contract-v1.json`, `schemas/canonical-record.schema.json` (F.1)
- `audit-package/spec/canonical-serialization-v1.md`
- `audit-package/rfc/RFC-AUDIT-001.md`
- `audit-package/rfc/RFC-INVARIANT-001.md`
- `audit-package/spec/rejection-reasons.json` (+ `rejection-reasons.md`)
- `audit-package/fixtures/vectors/vectors.json` and `TV-XXX.json`
- `audit-package/matrices/*.csv` (including `compatibility-matrix.csv` and `audit-template.csv`)
- `audit-package/docs/responsibility-boundary.md`, `audit-package/docs/topology.md`
- CI artifacts: `audit-reports-py<ver>` (pytest.xml, hash.log, replay.log, audit.log) and `audit-package-v0.1-py<ver>` (ZIP)
