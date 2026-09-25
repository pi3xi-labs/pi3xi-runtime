# RFC-AUDIT-001: Distributed Runtime Compatibility

| Field    | Value |
|----------|-------|
| Status   | **Draft** |
| Package  | F.2 Audit Package v0.1 |
| Depends  | Runtime Contract v1.0 (F.1, frozen), canonical-serialization-v1 |

## Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC 2119] [RFC 8174] when, and only when, they appear in all capitals, as shown here.

## 1. Abstract

Pi3xi records may be produced and audited by runtimes written in different languages. This document defines what it means for those runtimes to be *compatible*: they give identical audit results for identical input bytes. It defines four compatibility levels, the identity, replay, and rejection rules that every runtime has to follow, a shared set of test vectors, and a procedure for claiming conformance.

## 2. Scope

This RFC covers the audit behaviour of a runtime for Canonical Records as defined by Runtime Contract v1: serialization checks, identity, replay, and rejection.

Non-goals. This RFC does not define:

- invariant mathematics or the semantics of `invariant`, which stays opaque;
- distance functions or similarity measures between records;
- runtime execution models (scheduling, concurrency, storage, transport).

## 3. Compatibility Principle

Implementations MAY differ in language, parser, internal representation, and performance. Audit results MUST NOT differ. For the same input bytes, every compatible runtime MUST produce:

1. the same **identity** (SHA-256 hex digest),
2. the same **replay result** (equal or not equal, with the same code), and
3. the same **rejection code** (or the same acceptance).

## 4. Compatibility Levels

| Level | Name       | Requirement |
|-------|------------|-------------|
| L0    | Schema     | The runtime accepts and rejects the same inputs against the F.1 record schema. |
| L1    | Validation | For every failing input, the runtime emits the **same rejection code**. |
| L2    | Replay     | Replay compares the **same stored bytes** and reaches the same result. |
| L3    | Identity   | The runtime computes the **same SHA-256** for the same stored bytes. |

Levels are independent claims. A runtime MAY claim any subset of them. The reference implementation in F.2 (Python, `audit-package/src/pi3xi_audit`) targets **L3 plus L1**, and it also exercises L0 and L2.

## 5. Identity Rule

- Identity MUST be `SHA-256(saved bytes)` [FIPS 180-4], encoded as 64 lowercase hex characters.
- Implementations MUST NOT parse and re-serialize a record before hashing it.
- Implementations MUST NOT normalize Unicode, numbers, whitespace, key order, or escapes before hashing.
- The identity of a byte sequence does not depend on serialization rules. Only the accept/reject classification depends on canonical-serialization-v1.

## 6. Replay Rule

- Replay MUST compare the stored candidate bytes with the stored reference bytes, and their SHA-256 digests.
- Implementations MUST NOT regenerate, re-execute, or reinterpret a record in order to replay it.
- When the bytes differ, the classification MUST follow the documented baseline-stage rules (`spec/audit-model-v0.2.md`).

## 7. Rejection Rule

- A failing input MUST yield exactly one primary rejection code.
- That code is chosen by the documented precedence in `spec/rejection-reasons.json`, where the lowest precedence number wins.
- Implementations MUST emit only codes that are `active` in the registry. They MUST NOT invent codes, and they MUST NOT emit `reserved` codes.

## 8. Shared Test Vectors

- Every runtime MUST run the same vector set, `audit-package/fixtures/vectors/vectors.json`, with the raw byte files it references.
- Runtime-specific vector sets are forbidden as the basis of a conformance claim. New vectors MUST be added to the shared set.
- Vector payloads MUST be read as raw bytes from their files. They MUST NOT be embedded as parsed JSON.
- `expected_accept`, `expected_reason`, and comparison results are `provisional-until-spec-freeze`. `sha256` values are final, because identity does not depend on the spec.

## 9. Evidence

Evidence formats MAY differ between runtimes, for example JUnit XML, TAP, or plain logs. Conclusions MUST NOT differ. Each runtime's evidence MUST let a reviewer check, per vector and per control:

- the identity,
- the replay result, and
- the rejection code.

## 10. Conformance Claim Procedure

1. A runtime MAY claim a level only when CI evidence fills its column in `audit-package/matrices/compatibility-matrix.csv` for every row at that level.
2. A cell MAY be `PASS` only if it points to a test that runs and passes in CI.
3. A runtime with no implementation MUST be marked `Not implemented`.
4. A claim MUST name the commit, the CI run, and the vector-set digest (the SHA-256 of `vectors.json`).

## 11. Security Considerations

- **Integrity chain.** Each record, its sidecar, the vector index, and the reports form a chain of SHA-256 digests. Breaking any link MUST fail with `HASH_FILE_MISSING`, `HASH_FORMAT_INVALID`, or `HASH_MISMATCH`.
- **Duplicate keys.** RFC 8259 leaves the behaviour for duplicate object keys undefined, and common parsers disagree: some keep the first value, some the last, some raise an error. Runtimes MUST reject duplicates with `DUPLICATE_KEY` before interpreting any values.
- **Parser differentials.** Runtimes MUST NOT rely on a general-purpose JSON parser's normalization. This covers numbers (`1`, `1.0` and `1e0`), escapes, BOM handling, and trailing data. Classification is defined on bytes and lexemes, so two parsers cannot silently disagree.

## 12. IANA Considerations

This document has no IANA actions.

## 13. References

- canonical-serialization-v1: `audit-package/spec/canonical-serialization-v1.md`
- runtime-contract-v1.0: `contracts/runtime-contract-v1.json` at tag `runtime-contract-v1.0` (commit `103ae89`)
- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- [RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.
- [RFC 8259] Bray, T., Ed., "The JavaScript Object Notation (JSON) Data Interchange Format", STD 90, RFC 8259, December 2017.
- [FIPS 180-4] NIST, "Secure Hash Standard (SHS)", FIPS PUB 180-4, August 2015.
