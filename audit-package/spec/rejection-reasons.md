# Rejection Reasons (Draft, F.2 Audit Package v0.1)

> Draft for Phase F.2. Does not amend `runtime-contract-v1.0`.

The machine-readable registry is [`rejection-reasons.json`](rejection-reasons.json). Each entry is validated by [`../schemas/rejection-reason.schema.json`](../schemas/rejection-reason.schema.json). The registry is the single source of truth: `src/pi3xi_audit/errors.py` loads it, and a test checks that this document lists every code.

## Stages

| Stage    | Input                                   | Runs when                                                    |
|----------|-----------------------------------------|--------------------------------------------------------------|
| format   | the record file bytes only              | always                                                       |
| hash     | the record bytes + `<name>.json.sha256` | always (independent of the format result)                    |
| baseline | candidate bytes + reference record bytes| only when a baseline is given **and** the format stage passed |

Within the format stage, checks run in precedence order and stop at the first failure, so at most one format code is produced. The hash stage produces at most one code. The baseline stage classifies only the **first differing top-level section**, in the order intent, event, observe, meta, invariant, so it also produces at most one code.

## Precedence

When several codes apply, the reported (primary) code is the one with the **lowest precedence number**. The order is byte-level, then syntax, then structure, then integrity, then content comparison:

| # | Code | Stage | Category | Status | Meaning |
|---|------|-------|----------|--------|---------|
| 1 | `INVALID_UTF8` | format | encoding | active | The file bytes are not valid UTF-8. |
| 2 | `BOM_PRESENT` | format | encoding | active | The file starts with a UTF-8 byte order mark (EF BB BF). |
| 3 | `INVALID_JSON` | format | syntax | active | The bytes do not form exactly one syntactically valid JSON value (RFC 8259) at the start of the file. |
| 4 | `MISSING_FINAL_LF` | format | termination | active | The top-level JSON value is not followed by any byte: the single terminating LF (0x0A) is missing. |
| 5 | `TRAILING_DATA` | format | termination | active | The top-level JSON value is followed by something other than exactly one LF (e.g. a second LF, CRLF, a space, or other data). |
| 6 | `NON_CANONICAL_WHITESPACE` | format | whitespace | active | Insignificant whitespace (space, tab, CR, LF) occurs outside string literals before or inside the top-level value. |
| 7 | `DUPLICATE_KEY` | format | syntax | active | An object at any depth contains the same member name more than once (compared after unescaping). |
| 8 | `INVARIANT_REMOVED` | format | invariant | active | The top-level 'invariant' member is absent. |
| 9 | `MISSING_REQUIRED_FIELD` | format | structure | active | A top-level member other than 'invariant' (intent, event, observe, meta) is absent. |
| 10 | `UNEXPECTED_FIELD` | format | structure | active | The top-level object contains a member not in {intent, event, observe, meta, invariant}. |
| 11 | `FIELD_ORDER_VIOLATION` | format | structure | active | The top-level members are exactly the required set but not in the order intent, event, observe, meta, invariant. |
| 12 | `TYPE_MISMATCH` | format | structure | active | The record violates the F.1 structural schema (schemas/canonical-record.schema.json) in any way not covered by the codes above, including a top-level value that is not an object. |
| 13 | `HASH_FILE_MISSING` | hash | integrity | active | The '<name>.json.sha256' sidecar does not exist. |
| 14 | `HASH_FORMAT_INVALID` | hash | integrity | active | The sidecar is not exactly 64 lowercase hexadecimal characters followed by one LF (65 bytes). |
| 15 | `HASH_MISMATCH` | hash | integrity | active | The sidecar digest differs from the SHA-256 of the record file bytes. |
| 16 | `INTENT_MODIFIED` | baseline | modification | active | The first differing top-level section versus the reference is 'intent'. |
| 17 | `EVENT_MODIFIED` | baseline | modification | active | The first differing top-level section versus the reference is 'event'. |
| 18 | `OBSERVE_MODIFIED` | baseline | modification | active | The first differing top-level section versus the reference is 'observe'. |
| 19 | `META_MODIFIED` | baseline | modification | active | The first differing top-level section versus the reference is 'meta'. |
| 20 | `INVARIANT_TYPE_CHANGED` | baseline | invariant | active | The first differing section is 'invariant' and the JSON type of its value changed (object, array, string, number, boolean, null). |
| 21 | `INVARIANT_VALUE_CHANGED` | baseline | invariant | active | The first differing section is 'invariant', its JSON type is unchanged, and it differs other than only by numeric lexical form. |
| 22 | `NUMERIC_REPRESENTATION_CHANGE` | baseline | numeric | active | The first differing section differs only in the lexical form of one or more numbers whose numeric values are equal (e.g. 1 vs 1.0 vs 1e0). |
| 23 | `UNSUPPORTED_SCHEMA_VERSION` | reserved | versioning | reserved | Reserved for a future record format carrying version fields. Not emitted in v0.1. |

Examples:

- A file with a BOM and a second trailing LF is reported as `BOM_PRESENT`.
- A file with inner whitespace and a duplicate key is reported as `NON_CANONICAL_WHITESPACE`.
- A canonical record whose sidecar is stale and whose invariant changed is reported as `HASH_MISMATCH`. The baseline finding is still listed in the audit findings.

## Precise Definitions

- **Termination.** Let *V* be the top-level JSON value. The bytes after *V* must be exactly `0A`.
  - Nothing after *V* is reported as `MISSING_FINAL_LF`.
  - Anything else after *V* is reported as `TRAILING_DATA`. This includes `0A 0A`, `0D 0A`, `20 0A`, and `0A` followed by more data.
- **Whitespace.** Whitespace before *V* is reported as `NON_CANONICAL_WHITESPACE`. So is whitespace between tokens inside *V*: space, tab, CR, or LF anywhere outside a string literal. Whitespace after *V* is a termination error, not a whitespace error.
- **Invariant removal.** `INVARIANT_REMOVED` is a single-file (format stage) check. Removing the invariant is detectable without a baseline, because F.1 requires the member. It takes precedence over `MISSING_REQUIRED_FIELD`, which covers intent, event, observe, and meta.
- **Invariant types.** `INVARIANT_TYPE_CHANGED` compares the JSON type of the top-level invariant value: object, array, string, number, boolean, or null. Integer versus decimal is not a JSON type distinction, so `1` to `1.0` is `NUMERIC_REPRESENTATION_CHANGE`.
- **Numeric representation.** `NUMERIC_REPRESENTATION_CHANGE` applies to whichever section differs first. It requires the two sections to be identical in structure, key names and order, strings, and literals, with every differing number numerically equal (exact decimal comparison, no binary floating point).
- **String escapes.** A change in string escaping with the same decoded text (for example `"観測"` versus `"\u89b3\u6e2c"`) is not a numeric change. It is reported as `INVARIANT_VALUE_CHANGED` (invariant) or `<SECTION>_MODIFIED` (other sections).
- **Key reordering.** Reordering keys inside a section (same values) is reported as `<SECTION>_MODIFIED`, or `INVARIANT_VALUE_CHANGED` for the invariant.

## Reserved

`UNSUPPORTED_SCHEMA_VERSION` is reserved for a future record format that carries version fields (see `fixity-rules-v0.2.md` → Future record format). It is not emitted in v0.1, and `ValidationError` refuses to construct it.

## Coverage

Every active code is the `expected_reason` of at least one negative fixture in `fixtures/failure/` (enforced by `tests/test_reason_coverage.py`). v0.1 has **22 active codes**, **1 reserved code**, and **27 negative fixtures**.
