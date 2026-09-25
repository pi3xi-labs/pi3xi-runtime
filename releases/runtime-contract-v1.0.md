# runtime-contract-v1.0 — Runtime Observation Contract

> Release notes draft. Not yet tagged.

## Summary

First runtime contract of the Pi³XI architecture (Phase F.1). It defines the runtime as an Observation Engine: what is observed, recorded, and guaranteed, never why.

- Canonical spec: `pi3xi-labs/pi3xi-canonical-spec` `spec-v1.0` @ `93656646fcf1aab3ef316a557b23885d66ebe30f`
- Lock enforced by CI in this repository: Structure
- Canonical Record: `{ intent, event, observe, meta, invariant }`, the sole exchange format
- Guarantees: G1 event ordering, G2 observation persistence, G3 invariant preservation, G4 audit replay
- Invariant field: **reserved**. Opaque, passthrough only. No rotation-invariance claim until the spec defines `d_KG`, `d_GF`, `d_KF`.

## Out of Scope

- Reference implementation (F.2)
- Record signing (F.3)

## Files

- `README.md`
- `GOVERNANCE.md`
- `LICENSE`
- `contracts/runtime-contract-v1.json`
- `schemas/intent.schema.json`
- `schemas/event.schema.json`
- `schemas/observe.schema.json`
- `schemas/meta.schema.json`
- `schemas/invariant.schema.json`
- `schemas/canonical-record.schema.json`
- `examples/verify-success.json` (illustrative)
- `examples/verify-fail.json` (illustrative)
- `examples/replay.json` (illustrative)
- `docs/runtime-model.md`
- `docs/audit-model.md`
- `releases/runtime-contract-v1.0.md`
- `tools/validate_runtime.py`
- `.github/workflows/runtime-check.yml`

## License

CC0 1.0 Universal
