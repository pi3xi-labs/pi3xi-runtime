# Canonical Serialization v1 (Draft)

> **Draft, F.2 Audit Package v0.1.** Defines the byte format of a stored Canonical Record file. It does **not** amend `runtime-contract-v1.0` (F.1).

## Purpose

Fix a Canonical Record as an exact byte sequence, so that its identity, integrity, and replay can be checked by comparing bytes and SHA-256 digests only, with no interpretation and no re-serialization.

## Scope and Non-goals

In scope:

- the byte format of one record file
- the `.sha256` sidecar
- byte-level replay comparison

Not in scope:

- any invariant mathematics: the metrics `d_KG`, `d_GF`, `d_KF`, distance functions, and SO(2) rotation invariance
- record signing (F.3)
- how a runtime produces records (a generation-rules document is an open F.2 question)

The structure of a record is defined by F.1 (`schemas/canonical-record.schema.json`) and is not redefined here.

## Identity

The identity of a record file is **SHA-256 over the exact file bytes**, written as 64 lowercase hexadecimal characters. The hashed bytes include the terminating LF.

Identity is never computed from a parsed or re-serialized form. No JSON library round-trip (`json.loads` / `json.dumps` or equivalent) is used for identity or replay.

## Encoding

- UTF-8, strictly: overlong forms, encoded surrogates, and truncated sequences are rejected (`INVALID_UTF8`).
- No byte order mark (`BOM_PRESENT`).

## File Termination

The top-level JSON value is followed by **exactly one LF (0x0A)** and nothing else.

- Nothing after the value: `MISSING_FINAL_LF`.
- Anything else after the value, such as a second LF, CRLF, trailing spaces, or data: `TRAILING_DATA`.

## Whitespace

Compact form: no insignificant whitespace (space, tab, CR, LF) before the value or between tokens (`NON_CANONICAL_WHITESPACE`). Whitespace inside string literals is data and is preserved.

The check is done with a scanner over the bytes, not by re-dumping and comparing.

## Key Set and Order

- **Top level:** exactly `intent`, `event`, `observe`, `meta`, `invariant`, in this order, matching F.1. The codes are `INVARIANT_REMOVED`, `MISSING_REQUIRED_FIELD`, `UNEXPECTED_FIELD`, and `FIELD_ORDER_VIOLATION`.
- **Nested objects:** key order is whatever the producer wrote. It is part of identity and must never be changed.

## Duplicate Keys

Forbidden at every depth. Member names are compared after unescaping, so `"a"` and `"\u0061"` are duplicates (`DUPLICATE_KEY`).

## Arrays

Element order is preserved and is part of identity.

## Numbers

- RFC 8259 number grammar. `NaN`, `Infinity`, leading zeros, and `+` signs are `INVALID_JSON`.
- The **lexical form is part of identity**: `1`, `1.0`, `1e0`, `1E0`, and `10e-1` are distinct records.
- Numbers are never normalized.
- Against a baseline, a numerically equal but lexically different number is `NUMERIC_REPRESENTATION_CHANGE`. Equality is compared as exact decimals.

## Strings and Unicode

- No Unicode normalization (NFC/NFD are not applied).
- Escape sequences are kept as written: `"観測"` (UTF-8 `e8 a6 b3 e6 b8 ac`) and `"\u89b3\u6e2c"` are different bytes and therefore different records.
- Generators in this package write non-ASCII characters as raw UTF-8 and escape only what JSON requires.

## Null

`null` is a value and is preserved. It is distinct from absence: an absent `invariant` is `INVARIANT_REMOVED`, while `"invariant":null` is valid. It is also distinct from `{}`, `[]`, and `""`.

## Integrity Metadata (`.sha256` Sidecar)

- The digest is kept **outside** the record: `<name>.json` plus `<name>.json.sha256`. Records have no `record_hash` field.
- Sidecar content is **exactly 65 bytes**: 64 lowercase hex characters of the SHA-256 of `<name>.json`, then one LF. There is no file name, no `sha256sum`-style suffix, no CR, and no uppercase.
- Codes: `HASH_FILE_MISSING`, `HASH_FORMAT_INVALID`, `HASH_MISMATCH`.

## Replay

Replay is **re-reading the stored bytes** after a store/transfer step, then comparing:

1. byte-for-byte equality with the stored bytes, and
2. SHA-256 equality with the stored bytes and with the sidecar.

Replay never parses or re-serializes.

## Test Vectors

The vectors in `fixtures/vectors/` are **generated from the implementation of this spec** by `tools/generate_test_vectors.py`; nothing is hand-written. CI regenerates the whole directory and requires it to be byte-identical to the committed copy.

- Every vector is a **raw byte file**, `TV-XXX.json`, with a `TV-XXX.json.sha256` sidecar. Payloads are never embedded as parsed JSON.
- `vectors.json` is an index only. Each entry has `id`, `name`, `file`, `kind`, `length_bytes`, `sha256` (computed from the file bytes), `expected_accept`, `expected_reason`, and `status`. It also holds a `comparisons` list of baseline-stage expectations.
- The kinds are:
  - `identity-only` (TV-001..008): arbitrary JSON bytes such as `{}`, `{"value":1}`, `{"value":1.0}`, `{"value":1e0}`, 観測, `[3,2,1]`. They are used only for identity, so they have no accept/reject verdict (`status: not-applicable`).
  - `canonical-record` (TV-101..113): the success records and invariant variants. These are expected to be accepted.
  - `non-canonical` (TV-201..206): byte-level violations, each with its expected rejection code.
- **The identity SHA-256 of the given bytes does not depend on serialization rules.** It is final. Only the accept/reject classification and the comparison results depend on this spec, and they are marked `status: provisional-until-spec-freeze` until Spec v1 is frozen.
- Shared-vector requirements for other runtimes are in `rfc/RFC-AUDIT-001.md` §8.

## Relationship to F.1

- F.1 (`runtime-contract-v1.0`) defines the record structure and guarantees G1 to G4. This document adds a byte format and byte-level checks only.
- The F.1 schema is used unmodified as the structural check (`TYPE_MISMATCH`). The invariant accepts any JSON value, including `null`.
- This document does not amend `runtime-contract-v1.0`. It supersedes nothing in F.1. Version fields (`contract_version`, `schema_version`, `record_version`) are **not** added to v1 records (see `fixity-rules-v0.2.md`).
