# Audit Model

## Minimal Guarantees

Runtime Contract v1 makes exactly four guarantees. Anything not listed here is not guaranteed.

### G1 — Event Ordering

Within a record stream:

- `event.sequence` is **strictly increasing**.
- `event.occurred_at` is **non-decreasing** in sequence order.
- `meta.timestamp` is **non-decreasing** in sequence order.

Within one record: `event.occurred_at ≤ observe.observed_at ≤ meta.timestamp`.

Checked by `tools/validate_runtime.py` on `examples/replay.json`.

### G2 — Observation Persistence

The Canonical Record is the immutable audit artifact produced by a runtime. Once a Canonical Record is persisted, it is **append-only**. The runtime does not modify or delete it. Corrections are new records, not edits.

This cannot be checked from static examples, so it is not machine-checked in v1. It is normative for implementations (F.2). Cryptographic tamper evidence (record signing) is out of scope until F.3.

### G3 — Invariant Preservation

The `invariant` value of every record is **value-identical** to the invariant value submitted to the runtime. Preservation means non-modification. JSON type, key order, and numeric representation must all be kept (for example `1` must not become `1.0`; `1` and `1.0` are distinct values).

Invariant values are treated as opaque, read-only data. Runtime implementations MUST NOT create, modify, normalize, reinterpret, or recalculate invariant values (see `docs/runtime-model.md` → Invariant).

Checked by `tools/validate_runtime.py`: in every example that provides a `submission`, `record.invariant` must equal `submission.invariant` exactly. The Intent must likewise be recorded as submitted.

### G4 — Audit Replay

Reading the persisted records in `event.sequence` order **reproduces the recorded history unchanged**.

- Replay **reads** records. It does not re-execute Intents.
- Replay does not re-interpret observations or recompute invariants.
- Two replays of the same persisted stream yield identical records in identical order.

`examples/replay.json` is an illustrative stream. The validator checks its schema conformance and G1 ordering.

## Draft: Fixity Rules for F.2

[`canonical-record-fixity.md`](canonical-record-fixity.md) (Draft v0.1, **non-normative** for runtime-contract-v1.0) proposes stricter byte-level fixity rules for F.2: deterministic serialization and byte-identical replay.

## Audit Questions a Record Answers

| Question                         | Field                          |
|----------------------------------|--------------------------------|
| What was requested?              | `intent`                       |
| What occurred, and in what order?| `event` (`sequence`, `occurred_at`) |
| What was observed?               | `observe` (`result`, `outputs`)|
| When was it recorded, and by what?| `meta` (`timestamp`, `runtime_version`, `contract`) |
| What invariant value was carried?| `invariant` (opaque, unchanged)|

A record never answers **why**.

## Example Files

All example files are wrapped in an envelope whose `example.illustrative` is `true`. The validator rejects any example that is not labelled this way.

| File                          | Content                                                          |
|-------------------------------|------------------------------------------------------------------|
| `examples/verify-success.json`| Approved issuer and identity; observed result `Verified OK`      |
| `examples/verify-fail.json`   | Wrong issuer (`https://example.invalid`); observed result `rejected` |
| `examples/replay.json`        | Ordered stream of three records (sequence 1, 2, 3)               |

The scenario is modelled on the `contracts-v1.4` Sigstore verification documented in `pi3xi-labs/sentinel-observation-contract` (identity `https://github.com/pi3xi-labs/sentinel-observation-contract/.github/workflows/sign-release.yml@refs/tags/contracts-v1.4`, issuer `https://token.actions.githubusercontent.com`). Timestamps, identifiers, `runtime_version`, and invariant values are placeholders. They do not record when or by what any real verification ran.

## Negative Self-Tests

`python tools/validate_runtime.py --self-test` mutates valid examples and requires every mutation to be rejected. The mutations include:

- non-increasing or reordered sequence
- decreasing timestamp
- modified invariant, including a type-only or number-format-only change
- removed invariant or meta
- explanation added to observe
- extra top-level field
- broken `event_ref`
- rewritten intent
- example not labelled illustrative
- contract referencing a missing schema

The same self-test also confirms that the unmutated examples are still accepted.
