# Canonical Record Fixity Rules (Draft v0.1)

> **NON-NORMATIVE for `runtime-contract-v1.0`.** This is a draft for Phase F.2 (reference implementation). Nothing here changes the v1 contract, schemas, or validator. A rule becomes normative only through a new contract version.

## Purpose

Define how a Canonical Record stays fixed, meaning bit-for-bit unchanged, from the moment a runtime produces it, through storage, transfer, and replay. The goal is that the record can serve as audit evidence.

## Immutability

Once produced, a Canonical Record must not be changed. The following are forbidden:

- changing a value
- changing a type
- adding a field
- removing a field
- reordering keys or array elements
- normalization (for example Unicode, whitespace, number, or timestamp normalization)
- recalculation of any value

Example: turning `1` into `1.0` (or `1.0` into `1`) is forbidden. They are distinct values.

## Opaque Invariant

The `invariant` field is opaque. Runtime implementations MUST NOT create, modify, reinterpret, recalculate, or normalize invariant values.

Permitted operations:

- store
- transfer
- compare
- verify (for example checking identity against a submitted value)

## Stable Structure

A Canonical Record has exactly these top-level fields:

```
intent, event, observe, meta, invariant
```

Proposed for a **future record version** (explicitly **NOT** added to the v1 schemas):

| Field              | Purpose                                              |
|--------------------|------------------------------------------------------|
| `contract_version` | Contract version the record conforms to              |
| `schema_version`   | Schema version used to validate the record           |
| `record_version`   | Version of the record format itself                  |

In v1, `meta.contract` already carries the contract tag. These proposals are not part of v1.

## Deterministic Serialization

A serialized record should be reproducible byte for byte:

- encoding: UTF-8
- fixed key names
- fixed key order
- fixed array order
- fixed number representation
- fixed timestamp representation

Example of a forbidden change (key reorder):

```
{"observe": {"id": "observe-0001", "result": "Verified OK"}}
```

must not become

```
{"observe": {"result": "Verified OK", "id": "observe-0001"}}
```

The two are equal as JSON objects, but not as bytes.

## Replay Requirement

The input record and the post-replay record must be **byte-identical** in:

- structure
- values
- types
- order
- invariant

## Version Evolution

- v1 is never redefined.
- Changes are made only through new versions (see `GOVERNANCE.md` → Versioning).

## Audit Principle

Record what happened, not why.

## Open Questions for F.2

1. **Generation rules.** Should a separate document define how a runtime generates records (field population, timestamp source, id allocation)?
2. **How to pin serialization.** One option is RFC 8785 JSON Canonicalization Scheme (JCS). The other is fixity over the raw bytes as produced. Note that JCS normalizes numbers (for example `1.0` serializes as `1`), which is incompatible with treating `1` and `1.0` as distinct values. Byte-level fixity is therefore the likely choice. **This is an open question, not a decision.**
