# Governance

## Purpose

This document defines how the Pi³XI Runtime Contract is governed: its scope, how it relates to the canonical spec, how it is versioned, and how releases are named.

## Scope

This repository covers Phase **F.1 — Runtime Contract** only:

- the Canonical Record structure (`schemas/`)
- the layer rules and minimal guarantees (`contracts/runtime-contract-v1.json`, `docs/`)
- illustrative examples and their validation (`examples/`, `tools/`)

It contains **no implementation**.

### Out of Scope

| Item                          | Phase    |
|-------------------------------|----------|
| Reference implementation      | F.2      |
| Record signing                | F.3      |
| Invariant metric computation  | Pending: the canonical spec must define `d_KG`, `d_GF`, `d_KF` first |
| Mathematical definitions, distance functions, rotation-invariant formulas | Pending canonical spec |

## Relation to Other Repositories

```
Pi³XI Canonical Spec (parent)        spec-v1.0
  ↓
Pi³XI Runtime Contract (derived)     runtime-contract-v1.x
```

- **Canonical spec:** `pi3xi-labs/pi3xi-canonical-spec`, tag `spec-v1.0`, commit `93656646fcf1aab3ef316a557b23885d66ebe30f`. This contract uses the spec's runtime terminology (Canonical Record; Intent / Event / Observe / Meta) and principles (Observation First, Responsibility Boundaries, Coordinate Invariance). It must not contradict the spec. Where the spec says "To be specified in a later spec release", this contract either defines contract-level structure that stays consistent with the spec, or reserves the item (see Invariant below).
- **Sentinel Observation Contract:** `pi3xi-labs/sentinel-observation-contract`. A sibling contract derived from the same spec. This repository follows its conventions (lock-level vocabulary, tag-format checks, release naming, CI permissions). Its `contracts-v1.4` Sigstore verification is used only as the scenario for the illustrative examples. There is no normative dependency.

## Invariant Reservation

In v1 the `invariant` field is reserved. Invariant values are treated as opaque, read-only data. Runtime implementations MUST NOT create, modify, normalize, reinterpret, or recalculate invariant values. `1` and `1.0` are distinct values. Adding invariant semantics (such as SO(2) rotational invariance of `I = (d_KG, d_GF, d_KF)`) requires:

1. a canonical spec release that defines the metrics, and
2. a new runtime contract version that references that spec release.

## Draft Documents

`docs/canonical-record-fixity.md` (Canonical Record Fixity Rules, Draft v0.1) is **non-normative** for `runtime-contract-v1.0`. It collects proposals for F.2 and may only become normative through a new contract version.

## Lock Levels

Only **Structure Lock** is enforced by CI at `runtime-contract-v1.0`: the required files, the schemas, schema conformance of the examples, the record-internal references, G1 event ordering, and G3 invariant passthrough in the examples (`tools/validate_runtime.py`, `.github/workflows/runtime-check.yml`).

Higher lock levels (Behavior, Integrity, Signature) are applied in later phases, for example record signing in F.3.

## Versioning

- `MAJOR.MINOR`.
- **Minor** versions may add optional fields, new examples, or clarifications. A record that is valid under `vX.Y` stays valid under `vX.(Y+1)`.
- **Major** versions are required for any breaking change, for example a new required field, a removed field, a changed guarantee, or giving the `invariant` field a structure that rejects previously valid values.
- Changes to the guarantees (G1–G4) or to the invariant reservation require governance review.

## Tag Format

Tags must match `runtime-contract-vMAJOR.MINOR` (regular expression `^runtime-contract-v[0-9]+\.[0-9]+$`). CI checks this on tag pushes.

## Release Naming

Release titles use the format:

```
<tag> — <milestone>
```

Example:

```
runtime-contract-v1.0 — Runtime Observation Contract
```

Release titles are descriptive only. Validity is determined by the tag and the tagged commit.

## Change Process

- All changes must pass `python tools/validate_runtime.py` and `python tools/validate_runtime.py --self-test`.
- Example records must be labelled as illustrative (`"illustrative": true`). No fabricated data may be presented as a real observation.
- Breaking changes are made only in major versions.
