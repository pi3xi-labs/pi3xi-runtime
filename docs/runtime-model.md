# Runtime Model

## Definition

The runtime is an **Observation Engine**. It receives Intents, records the Events that occur, records what is observed, and persists the result as Canonical Records.

The contract states only **what** is observed, recorded, and guaranteed. It never states **why**. Causes, reasons, and interpretations belong to higher layers, as the canonical spec's Observation First principle requires (`principles/observation-first.md`).

## Canonical Record

```
Canonical Record = { intent, event, observe, meta, invariant }
```

- It is the **sole exchange format**. The runtime accepts and emits nothing else.
- All five fields are required. No additional fields are allowed (`schemas/canonical-record.schema.json`).
- The canonical spec (spec-v1.0, `runtime/canonical-record.md`) leaves the record structure "To be specified in a later spec release". The structure here is defined at **contract** level for runtime-contract-v1. It does not amend the spec.

## Layers

The flow follows the canonical spec (`runtime/intent-event-observe-meta.md`):

```
Intent
  ↓
Event
  ↓
Observe
  ↓
Meta
        + Invariant (carried alongside, reserved in v1)
```

### Intent — `schemas/intent.schema.json`

Spec responsibility: *Desired action*.

- An Intent is a recorded **request**. It is an observation target, not a fact.
- Recording an Intent asserts only that the request was received. It does not assert that the action was carried out or succeeded.
- The Intent is recorded as submitted. The runtime does not interpret or rewrite it.

### Event — `schemas/event.schema.json`

Spec responsibility: *State transition*.

- An Event records that an occurrence (a state transition) took place, and when (`occurred_at`).
- **No inference.** An Event carries no cause, reason, or interpretation.
- `sequence` places the Event in the record stream (guarantee G1).
- `intent_ref`, when present, equals `intent.id` of the same record.

### Observe — `schemas/observe.schema.json`

Spec responsibility: *Observable result*.

- **Observation First:** record observations, not explanations.
- `result` holds the observed result as captured (for example a tool's literal output line). `outputs` holds other captured values (for example an exit status).
- There is deliberately no field for reasons or explanations, and `additionalProperties: false` prevents adding one.
- `event_ref` equals `event.id` of the same record. `observed_at` is not earlier than `event.occurred_at`.

### Meta — `schemas/meta.schema.json`

Spec responsibility: *Audit and governance metadata*.

- Audit auxiliaries: `record_id`, `timestamp` (persistence time), `runtime_version`, `contract` (tag), and optionally `spec` (tag and commit).
- Meta never carries observation content.
- `timestamp` is not earlier than `observe.observed_at`.

### Invariant — `schemas/invariant.schema.json`

Pi³XI invariant layer (spec-v1.0 `invariants/`, `principles/coordinate-invariant.md`).

**Reserved in v1.**

- The value is **opaque**: any JSON value, including `null`.
- The runtime **must not** compute, derive, normalise, reorder, truncate, re-encode, or otherwise alter it.
- The runtime guarantees only **value-identical passthrough** (byte-identical where carried as bytes). Preservation means non-modification.
- The runtime makes **no claim** that SO(2) rotational invariance, or any property of `I = (d_KG, d_GF, d_KF)`, has been computed or verified.

Why reserved: spec-v1.0 lists `d_KG`, `d_GF`, `d_KF` as "To be specified in a later spec release". Defining formulas here would contradict the spec's authority over invariants. Rotation-invariance semantics will be added in a later contract version, once the spec defines the metrics.

## Responsibility Boundaries

Following `principles/responsibility-boundaries.md`, no layer takes over another layer's responsibility:

| Must not appear in | Content                                         |
|--------------------|-------------------------------------------------|
| Intent             | Outcomes (an Intent is not evidence of success) |
| Event              | Causes or interpretations                       |
| Observe            | Explanations                                    |
| Meta               | Observation content                             |
| Invariant          | Runtime-computed values                         |
