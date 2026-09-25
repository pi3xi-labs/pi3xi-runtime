# Canonical Record Fixity Rules (Draft v0.2)

> **Draft for Phase F.2. NON-NORMATIVE for `runtime-contract-v1.0`.** For F.2, this document supersedes `docs/canonical-record-fixity.md` (Draft v0.1). The v0.1 file is left unchanged as part of the F.1 tree.

## What Changed Since v0.1

| Topic                     | v0.1 (open)                         | v0.2 (decided for F.2)                                           |
|---------------------------|-------------------------------------|------------------------------------------------------------------|
| How to pin serialization  | RFC 8785 JCS or raw bytes (open question) | **Raw bytes.** Identity = SHA-256 of the exact file bytes. JCS is not used because it normalizes numbers (`1.0` becomes `1`). |
| File format               | not fixed                           | UTF-8, no BOM, compact JSON, exactly one final LF (`canonical-serialization-v1.md`) |
| Where the hash lives      | not fixed                           | Outside the record, in a `<name>.json.sha256` sidecar            |
| Replay                    | byte-identical (principle)          | Re-read stored bytes; compare bytes and SHA-256; never re-serialize |
| Rejection reasons         | none                                | Registry of 22 active codes plus 1 reserved, with fixed precedence |

## Immutability

After a record file is written, its bytes never change. The following are all forbidden:

- value or type changes
- adding or removing fields
- reordering keys or array elements
- Unicode, whitespace, number, or timestamp normalization
- recalculation of any value

`1` to `1.0` is forbidden.

## Opaque Invariant

Runtime implementations and audit tools MUST NOT create, modify, reinterpret, recalculate, or normalize invariant values.

Permitted operations:

- store
- transfer
- compare (bytes, digests, and the lexeme-level classification in `rejection-reasons.md`)
- verify

## Stable Structure

Top-level members are `intent`, `event`, `observe`, `meta`, `invariant`, in this order, as defined by F.1.

## Future Record Format (not v1)

`contract_version`, `schema_version`, and `record_version` are **not** part of v1 records, and adding them to a v1 record is rejected as `UNEXPECTED_FIELD`. They are documented only as candidates for a future record format, **runtime-contract-v1.1 / record format v2**. Such a format would need a new F.1 contract version and schema. `UNSUPPORTED_SCHEMA_VERSION` is reserved for it.

## Deterministic Serialization

See `canonical-serialization-v1.md`. Summary:

- UTF-8, no BOM
- compact form
- one final LF
- fixed top-level order
- producer-given nested order preserved
- numeric lexical form preserved
- no Unicode normalization
- no duplicate keys

## Replay Requirement

The stored record and the replayed record must be byte-identical and have identical SHA-256 digests. Both must also match the sidecar.

## Version Evolution

v1 is never redefined. Any change is a new version.

## Audit Principle

Record what happened, not why.

## Open Questions (Remaining for F.2)

1. A generation-rules document covering how a runtime populates fields, the timestamp source, and id allocation.
2. Whether record streams (for G1 ordering) get their own file format, for example one record per file or a manifest.
