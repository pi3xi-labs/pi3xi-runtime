# RFC-INVARIANT-001: Median Model Invariants

| Field    | Value |
|----------|-------|
| Status   | **Draft** |
| Category | Governance |
| Package  | F.2 Audit Package v0.1 |
| Depends  | Runtime Contract v1.0 (F.1, frozen), `spec/canonical-serialization-v1.md`, `rfc/RFC-AUDIT-001.md` |

## Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC 2119] [RFC 8174] when, and only when, they appear in all capitals, as shown here.

## 1. Abstract

Pi³XI is built and reviewed by several AI models and by several runtime implementations. This document lists the properties that MUST hold no matter which model or implementation is used. It defines five invariants: topology, identity, evidence, compatibility, and governance. These invariants constrain artifacts (records, digests, evidence, audit results). They do not constrain how a model reasons.

The informative layer picture is in `docs/topology.md`.

## 2. Invariants

### I1. Topology Invariance

These responsibility boundaries MUST remain stable:

```
Observation | Memory | Knowledge | Execution | Verification
```

Each boundary is owned by one layer (see `docs/topology.md`). Implementations of any layer MAY change. A change MUST NOT move a responsibility across a boundary. For example, Verification MUST NOT generate or modify records, and Execution MUST NOT decide audit outcomes.

### I2. Identity Invariance

The identity of a record MUST be the SHA-256 of its saved bytes, as defined in `spec/canonical-serialization-v1.md`:

```
identity = SHA256(saved_bytes)
```

Identity MUST NOT depend on:

- model output (which model produced, reviewed, or described the record),
- the runtime language, or
- implementation details (parser, internal representation, re-serialization).

A verifier MUST hash the stored bytes as they are and MUST NOT re-serialize before hashing.

### I3. Evidence Invariance

Audit evidence MUST come from these sources only:

1. RFCs (this document, RFC-AUDIT-001)
2. Schemas (F.1 `schemas/`, `audit-package/schemas/`)
3. Test vectors (`audit-package/fixtures/vectors/`)
4. CI results (the `audit-package` and `runtime-check` workflows)
5. Audit logs (`pytest.xml`, `hash.log`, `replay.log`, `audit.log`)

Conversation history with any model MAY help to interpret these sources. It MUST NOT replace them. A matrix cell or claim that is supported only by conversation history MUST NOT be marked `PASS` or `Verified`.

### I4. Compatibility Invariance

Implementations (for example Python, Rust, Node, Go) MAY differ. Audit outcomes MUST NOT differ. For the same input bytes, implementations MUST NOT produce:

- different hashes,
- different replay results, or
- different rejection codes.

The levels and rules are defined in `rfc/RFC-AUDIT-001.md`. Conformance is recorded in `matrices/compatibility-matrix.csv`. A runtime with no implementation is `Not implemented`, never `PASS`.

### I5. Governance Invariance

This sequence MUST be preserved:

```
Observe -> Remember -> Structure -> Execute -> Verify
```

A step MUST NOT be skipped or reordered. Verification is the last step. It reads the saved bytes and produces evidence. It never feeds changes back into the record it verifies.

## 3. Relationship to Other Documents

This RFC sits in the trust order of `AGENTS.md` as follows:

1. Runtime Contract v1 (`contracts/runtime-contract-v1.json`) and the F.1 schemas: higher
2. `spec/canonical-serialization-v1.md`: higher
3. `rfc/RFC-AUDIT-001.md` and **this RFC (RFC-INVARIANT-001)**: same level
4. Rejection-code registry, test vectors, CI results, other documents: lower

If this RFC conflicts with a higher artifact, the higher artifact wins and this RFC is corrected. RFC-AUDIT-001 and this RFC are designed not to overlap. RFC-AUDIT-001 gives the detailed compatibility rules, and I4 above only restates the principle.

## 4. Security Considerations

- **Integrity chain.** I2 and I3 together mean that every audit conclusion can be traced to saved bytes, their SHA-256, and a CI run. Breaking any link (re-serializing, citing conversation instead of CI) breaks the chain.
- **Model substitution.** Replacing one model with another MUST NOT change any identity, replay result, or rejection code. If it does, that is a defect in the implementation, not a new result.
- **Parser differentials.** These are covered by RFC-AUDIT-001 (duplicate keys, numeric lexemes, Unicode escapes).

## 5. Non-Goals

This RFC:

- does not constrain model reasoning, prompts, or conversation style. It constrains artifacts only;
- does not define invariant mathematics, distance functions, or the semantics of `invariant`, which stays opaque;
- does not define the internals of the planned Bagua and Provence layers.

## 6. IANA Considerations

None.

## 7. References

- `contracts/runtime-contract-v1.json`: Runtime Contract v1.0 (F.1)
- `audit-package/spec/canonical-serialization-v1.md`
- `audit-package/rfc/RFC-AUDIT-001.md`: Distributed Runtime Compatibility
- `audit-package/docs/topology.md` (informative)
- `AGENTS.md`: trust hierarchy
- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- [RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.
- [FIPS 180-4] NIST, "Secure Hash Standard (SHS)", August 2015.
