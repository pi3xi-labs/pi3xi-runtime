import hashlib

import pytest
from conftest import PACKAGE_ROOT

REPO_ROOT = PACKAGE_ROOT.parent

# SHA-256 of every F.1 file at main 103ae899378ca9438c5ecc740938d518171392fc
# (the commit to be tagged runtime-contract-v1.0). F.2 must not modify them.
F1_FILES = {
    "README.md": "14481668f1ea1e47b579c59716bc0c62b4f553523d7b1af6f486aa63723e1772",
    "GOVERNANCE.md": "652125bba50ce6814ad9e1c6300355f05d5d62976f3faace7d65de57d1e730c5",
    "LICENSE": "a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499",
    "contracts/runtime-contract-v1.json": "3e3d41e25dd1ec46046d1bce282105b411470ad265b3874d40cd29ea59b85970",
    "schemas/canonical-record.schema.json": "95e4ee4eb81c7caab81ac8c49a58236d5a2431278caae4449f857f4b22592eba",
    "schemas/event.schema.json": "3f9dd25b65793ae1eefc714142d7934565409020a4e586acdae5bfd6581402a2",
    "schemas/intent.schema.json": "3b9bf7fd4d84db8fb9607d1f28becb8655e4c19cfa934984406511ec8adcee7b",
    "schemas/invariant.schema.json": "7e816676abb4e81679677206454084d9c3ee634942b85788ab06940adbd525f9",
    "schemas/meta.schema.json": "4cc45c01d23e766f629aece81af9559c5a3183d0a5d9cc4906a9b4036c952330",
    "schemas/observe.schema.json": "afda368c05521713594a080706f75b763158cf9ab74891b1222d19e20835a1b1",
    "examples/replay.json": "5640ca9dc64643e30d2d1501921006433b6fa26ddc5e2c1aa984507a94a881b4",
    "examples/verify-fail.json": "df87203313b8e1ddcb82c12c0cfd1bf1c5e2e06f802fa166efa804a87c6e2a19",
    "examples/verify-success.json": "d0b9e1406832385ae51f73ac3fb46d5fb2e676e90c33783284b555acc408f5e2",
    "docs/audit-model.md": "44ab6af160e5e7bd7ad4032f260b429b65a37d0296025066cc5b7806ebd4b771",
    "docs/canonical-record-fixity.md": "b2224a7a513629a1e1814f5838cd5a7935108a222b0aa79b06b626ed29c19966",
    "docs/runtime-model.md": "d4dd5f6025cb7a3a776ad6908a6e0b676307938adf1003bf4016eacac8eefe3e",
    "releases/runtime-contract-v1.0.md": "d332b0b0ea3a4d4c034e2e05d33abe42d3897b842a9b69999e14104cb5e0061d",
    "tools/validate_runtime.py": "e95086f7833fbf67cb761dfe0c9f2e38ec83fcaa1a8e84a8ed9401a56f7386c8",
    ".github/workflows/runtime-check.yml": "d518dd788f0a43615b207ad7ee13bff9257473a2c511b09ff15fc56527c054d3",
}


@pytest.mark.parametrize("rel", sorted(F1_FILES))
def test_f1_file_unchanged(rel):
    assert hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest() == F1_FILES[rel]


def test_no_new_files_in_f1_directories():
    for d in ("contracts", "schemas", "examples", "docs", "releases"):
        present = {p.relative_to(REPO_ROOT).as_posix() for p in (REPO_ROOT / d).iterdir() if p.is_file()}
        assert present <= set(F1_FILES), present - set(F1_FILES)
