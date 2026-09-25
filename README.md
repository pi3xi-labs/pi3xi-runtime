# Pi³XI Runtime Contract

> The runtime is an Observation Engine. This contract states only what is observed, recorded, and guaranteed — never why.

Phase **F.1 — Runtime Contract v1**. This repository defines the contract only. It contains no runtime implementation.

## Status

- **Status:** Draft (no tag or release yet)
- **Contract version:** `runtime-contract-v1.0` (planned tag)
- **Canonical spec:** [`pi3xi-labs/pi3xi-canonical-spec`](https://github.com/pi3xi-labs/pi3xi-canonical-spec) `spec-v1.0` @ `93656646fcf1aab3ef316a557b23885d66ebe30f`
- **Lock enforced by CI:** Structure (schemas, examples, ordering and passthrough checks)

## Runtime Model

The runtime is organized around the **Canonical Record**, as in the canonical spec (`runtime/canonical-record.md`). This contract fixes the record's structure for v1:

```
Canonical Record = { intent, event, observe, meta, invariant }
```

The Canonical Record is the **sole exchange format** of the runtime. No other fields are allowed.

| Layer     | Spec responsibility (spec-v1.0) | Contract role (v1)                                             |
|-----------|---------------------------------|----------------------------------------------------------------|
| Intent    | Desired action                  | A recorded request. An observation target, not a fact.         |
| Event     | State transition                | A record that an occurrence took place. No inference.          |
| Observe   | Observable result               | The observation result. Observation First.                     |
| Meta      | Audit and governance metadata   | Audit auxiliaries: record_id, timestamp, runtime_version, etc. |
| Invariant | Pi³XI invariants (`invariants/`) | **RESERVED.** Opaque value, passed through unchanged.         |

See [`docs/runtime-model.md`](docs/runtime-model.md).

## Guarantees

| ID | Guarantee                | Statement                                                                                   |
|----|--------------------------|---------------------------------------------------------------------------------------------|
| G1 | Event ordering           | `event.sequence` strictly increases; `event.occurred_at` and `meta.timestamp` never decrease. |
| G2 | Observation persistence  | A persisted record is append-only; the runtime does not modify or delete it.                |
| G3 | Invariant preservation   | `invariant` is value-identical to what was submitted (preservation = non-modification).     |
| G4 | Audit replay             | Reading records in sequence order reproduces the recorded history, unchanged.               |

See [`docs/audit-model.md`](docs/audit-model.md).

## Invariant (reserved in v1)

The canonical spec names the Phase 1 invariant vector `I = (d_KG, d_GF, d_KF)` and the protected property SO(2) rotational invariance. The metrics are still "To be specified in a later spec release".

So in v1 the `invariant` field is **reserved**:

- The value is opaque (any JSON value, including `null`).
- The runtime must not compute, derive, or alter it.
- The only guarantee is value-identical (byte-identical where carried as bytes) passthrough.
- This contract does **not** claim that rotation invariance is computed or verified. Those semantics come in a later contract version, once the spec defines the metrics.

## Repository Layout

```
README.md
GOVERNANCE.md
LICENSE
contracts/
  runtime-contract-v1.json
schemas/                      JSON Schema draft 2020-12
  intent.schema.json
  event.schema.json
  observe.schema.json
  meta.schema.json
  invariant.schema.json
  canonical-record.schema.json
examples/                     illustrative only
  verify-success.json
  verify-fail.json
  replay.json
docs/
  runtime-model.md
  audit-model.md
releases/
  runtime-contract-v1.0.md
tools/
  validate_runtime.py
.github/workflows/
  runtime-check.yml
```

## Examples

The files in `examples/` are **illustrative examples**, not logs of real runtime executions (no runtime exists yet). Their scenario is modelled on the documented `contracts-v1.4` Sigstore verification of the Sentinel Observation Contract:

- identity `https://github.com/pi3xi-labs/sentinel-observation-contract/.github/workflows/sign-release.yml@refs/tags/contracts-v1.4`
- issuer `https://token.actions.githubusercontent.com`
- success result `Verified OK`; failure: wrong issuer is rejected

Identifiers, timestamps, `runtime_version`, and invariant values in the examples are placeholders.

## Validation

```
pip install "jsonschema==4.26.0"
python tools/validate_runtime.py
python tools/validate_runtime.py --self-test
```

The self-test mutates valid examples (reordered sequence, modified invariant, added explanation, and so on) and requires each mutation to be rejected.

## Related Repositories

- **Canonical spec (parent):** [pi3xi-labs/pi3xi-canonical-spec](https://github.com/pi3xi-labs/pi3xi-canonical-spec)
- **Sentinel Observation Contract:** [pi3xi-labs/sentinel-observation-contract](https://github.com/pi3xi-labs/sentinel-observation-contract)

## Governance

See [`GOVERNANCE.md`](GOVERNANCE.md).

## License

[CC0 1.0 Universal](LICENSE)
