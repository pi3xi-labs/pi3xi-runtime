"""Lint checks for the Markdown documents (Mermaid label quoting, arrows only in code blocks)."""
import re

import pytest
from conftest import PACKAGE_ROOT

MERMAID = re.compile(r"```mermaid\n(.*?)```", re.S)
# Node shape brackets: A[...], A(...), A{...}; the label is everything inside the outer bracket.
NODE = re.compile(r"\b[A-Za-z0-9_]+\[(.*?)\](?=\s|$|-->|--)")
NEEDS_QUOTES = ("(", ")", "³", "<br/>")
DOCS = sorted((PACKAGE_ROOT / "docs").glob("*.md"))
RFCS = sorted((PACKAGE_ROOT / "rfc").glob("*.md"))


def test_expected_docs_present():
    names = {p.name for p in DOCS} | {p.name for p in RFCS}
    assert {"topology.md", "responsibility-boundary.md", "RFC-AUDIT-001.md", "RFC-INVARIANT-001.md"} <= names


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_mermaid_labels_quoted(path):
    blocks = MERMAID.findall(path.read_text(encoding="utf-8"))
    for block in blocks:
        for line in block.splitlines():
            for label in NODE.findall(line):
                if any(ch in label for ch in NEEDS_QUOTES):
                    assert label.startswith('"') and label.endswith('"'), f"{path.name}: unquoted label {label!r}"


def test_topology_has_two_diagrams_and_notes():
    text = (PACKAGE_ROOT / "docs" / "topology.md").read_text(encoding="utf-8")
    blocks = MERMAID.findall(text)
    assert len(blocks) == 2
    assert blocks[0].startswith("flowchart TD") and blocks[1].startswith("flowchart LR")
    assert "Informative" in text and "not a misspelling" in text and "Planned" in text
    assert "RFC-INVARIANT-001.md" in text and "responsibility-boundary.md" in text


def test_rfc_invariant_structure_and_arrows_only_in_code():
    text = (PACKAGE_ROOT / "rfc" / "RFC-INVARIANT-001.md").read_text(encoding="utf-8")
    for heading in ("I1. Topology Invariance", "I2. Identity Invariance", "I3. Evidence Invariance",
                    "I4. Compatibility Invariance", "I5. Governance Invariance", "Requirements Language",
                    "Relationship to Other Documents", "Security Considerations", "Non-Goals"):
        assert heading in text, heading
    assert "RFC 2119" in text and "RFC 8174" in text and "**Draft**" in text and "Governance" in text
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    assert "->" not in prose and "→" not in prose
