# runtime-contract-v1.0 — Runtime Observation Contract

> Release notes draft. Not yet tagged.

## Position

This release defines the Runtime Observation Contract v1.

This contract specifies how observation records are exchanged and validated.

It is a **contract**, not a reference implementation.

## Scope

Included:

- Runtime Contract v1 (`contracts/runtime-contract-v1.json`)
- Schemas (6, JSON Schema draft 2020-12): intent, event, observe, meta, invariant, canonical-record
- Validation Rules: layer rules and guarantees G1 event ordering, G2 observation persistence, G3 invariant preservation, G4 audit replay
- Canonical Record: `{ intent, event, observe, meta, invariant }`, the sole exchange format
- Examples (illustrative): success, failure, replay
- Validator (`tools/validate_runtime.py`) and CI (`runtime-check`)

## Non-goals

Not included:

- Invariant computation
- Mathematical definitions
- Distance functions
- Rotation-invariant formulas
- Reference implementation (F.2)
- Record signing (F.3)

## Invariant

Invariant values are treated as opaque, read-only data. Runtime implementations MUST NOT create, modify, normalize, reinterpret, or recalculate invariant values.

1 and 1.0 are distinct values.

## Canonical Record

Canonical Record is the immutable audit artifact produced by a runtime.

## Relation to the Canonical Spec

Derived from `pi3xi-labs/pi3xi-canonical-spec` `spec-v1.0` @ `93656646fcf1aab3ef316a557b23885d66ebe30f`. The Canonical Record structure and the Invariant layer are contract-level choices. They are not amendments to spec-v1.0.

## Verification

- CI: `runtime-check` (Structure Lock), which runs `python tools/validate_runtime.py`
- Negative self-test: `python tools/validate_runtime.py --self-test`. It checks that 15 mutated inputs are rejected and that the 2 unmutated examples are accepted.

## Future

Future specifications MAY define mathematical invariant systems and replay models.
