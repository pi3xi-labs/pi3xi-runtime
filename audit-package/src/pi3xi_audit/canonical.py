"""Canonical record format checks (spec/canonical-serialization-v1.md).

Everything here works on the exact file bytes. Nothing is re-serialized: the
scanner keeps the raw lexeme of every token, so numeric lexical form
(1 vs 1.0 vs 1e0), string escapes, key order and duplicates stay visible.
json.loads / json.dumps are never used on record bytes.
"""

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .errors import PACKAGE_ROOT, ValidationError

TOP_LEVEL_ORDER = ("intent", "event", "observe", "meta", "invariant")
BOM = b"\xef\xbb\xbf"
WHITESPACE = " \t\n\r"
F1_SCHEMA_DIR = PACKAGE_ROOT.parent / "schemas"


def sha256_hex(data: bytes) -> str:
    """Identity: SHA-256 over the exact file bytes, lowercase hex."""
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- scanner

class ParseError(Exception):
    def __init__(self, pos, message):
        super().__init__(f"offset {pos}: {message}")
        self.pos = pos


@dataclass
class Node:
    kind: str                 # object | array | string | number | true | false | null
    start: int                # character offsets into the decoded text
    end: int
    raw: str                  # exact source text of the value
    members: list = field(default_factory=list)  # object: [(key, Node)], array: [Node]
    value: object = None      # decoded string for kind == "string"


class Scanner:
    """Strict RFC 8259 recursive-descent scanner that preserves raw lexemes.

    Insignificant whitespace is tolerated (so that it can be reported as
    NON_CANONICAL_WHITESPACE rather than INVALID_JSON) and its first offset is
    recorded. Duplicate member names are recorded, not rejected.
    """

    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.first_whitespace = None
        self.first_duplicate = None

    def parse_top(self):
        self._ws()
        node = self._value()
        return node, self.text[self.pos:]

    # -- helpers
    def _ws(self):
        t, n = self.text, len(self.text)
        while self.pos < n and t[self.pos] in WHITESPACE:
            if self.first_whitespace is None:
                self.first_whitespace = self.pos
            self.pos += 1

    def _peek(self):
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def _expect(self, ch):
        if self._peek() != ch:
            raise ParseError(self.pos, f"expected {ch!r}, found {self._peek()!r}")
        self.pos += 1

    # -- grammar
    def _value(self):
        ch = self._peek()
        if ch == "{":
            return self._object()
        if ch == "[":
            return self._array()
        if ch == '"':
            return self._string()
        if ch == "-" or ch.isdigit():
            return self._number()
        for lit in ("true", "false", "null"):
            if self.text.startswith(lit, self.pos):
                start = self.pos
                self.pos += len(lit)
                return Node(lit, start, self.pos, lit)
        raise ParseError(self.pos, f"unexpected {ch!r}" if ch else "unexpected end of input")

    def _object(self):
        start = self.pos
        self._expect("{")
        members, seen = [], set()
        self._ws()
        if self._peek() == "}":
            self.pos += 1
            return Node("object", start, self.pos, self.text[start:self.pos], members)
        while True:
            self._ws()
            if self._peek() != '"':
                raise ParseError(self.pos, "expected member name")
            key = self._string()
            if key.value in seen and self.first_duplicate is None:
                self.first_duplicate = (key.start, key.value)
            seen.add(key.value)
            self._ws()
            self._expect(":")
            self._ws()
            members.append((key.value, self._value()))
            self._ws()
            if self._peek() == ",":
                self.pos += 1
                continue
            self._expect("}")
            return Node("object", start, self.pos, self.text[start:self.pos], members)

    def _array(self):
        start = self.pos
        self._expect("[")
        items = []
        self._ws()
        if self._peek() == "]":
            self.pos += 1
            return Node("array", start, self.pos, self.text[start:self.pos], items)
        while True:
            self._ws()
            items.append(self._value())
            self._ws()
            if self._peek() == ",":
                self.pos += 1
                continue
            self._expect("]")
            return Node("array", start, self.pos, self.text[start:self.pos], items)

    _ESC = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}

    def _string(self):
        start = self.pos
        self._expect('"')
        out, t, n = [], self.text, len(self.text)
        while True:
            if self.pos >= n:
                raise ParseError(self.pos, "unterminated string")
            ch = t[self.pos]
            if ch == '"':
                self.pos += 1
                return Node("string", start, self.pos, t[start:self.pos], value="".join(out))
            if ord(ch) < 0x20:
                raise ParseError(self.pos, "unescaped control character in string")
            if ch == "\\":
                esc = t[self.pos + 1:self.pos + 2]
                if esc in self._ESC:
                    out.append(self._ESC[esc])
                    self.pos += 2
                elif esc == "u":
                    hexdigits = t[self.pos + 2:self.pos + 6]
                    if len(hexdigits) != 4 or any(c not in "0123456789abcdefABCDEF" for c in hexdigits):
                        raise ParseError(self.pos, "invalid \\u escape")
                    out.append(chr(int(hexdigits, 16)))
                    self.pos += 6
                else:
                    raise ParseError(self.pos, "invalid escape")
                continue
            out.append(ch)
            self.pos += 1

    def _number(self):
        t, start = self.text, self.pos

        def digits():
            s = self.pos
            while self.pos < len(t) and t[self.pos].isdigit() and t[self.pos].isascii():
                self.pos += 1
            return self.pos - s

        if self._peek() == "-":
            self.pos += 1
        if self._peek() == "0":
            self.pos += 1
        elif digits() == 0:
            raise ParseError(self.pos, "invalid number")
        if self._peek() == ".":
            self.pos += 1
            if digits() == 0:
                raise ParseError(self.pos, "invalid fraction")
        if self._peek() in ("e", "E"):
            self.pos += 1
            if self._peek() in ("+", "-"):
                self.pos += 1
            if digits() == 0:
                raise ParseError(self.pos, "invalid exponent")
        return Node("number", start, self.pos, t[start:self.pos])


def scan(text):
    """Scan text. Returns (scanner, top-level node, remaining text). Raises ParseError."""
    s = Scanner(text)
    node, rest = s.parse_top()
    return s, node, rest


# --------------------------------------------------------------------------- helpers

def to_python(node):
    """Structural view for F.1 schema validation only (never used for identity)."""
    if node.kind == "object":
        return {k: to_python(v) for k, v in node.members}
    if node.kind == "array":
        return [to_python(v) for v in node.members]
    if node.kind == "string":
        return node.value
    if node.kind == "number":
        return int(node.raw) if not any(c in node.raw for c in ".eE") else float(node.raw)
    return {"true": True, "false": False, "null": None}[node.kind]


def json_type(node):
    return {"true": "boolean", "false": "boolean"}.get(node.kind, node.kind)


def numeric_only_difference(a, b):
    """True if a and b are identical except for the lexical form of numerically equal numbers."""
    if a.kind != b.kind:
        return False
    if a.kind == "number":
        return Decimal(a.raw) == Decimal(b.raw)
    if a.kind == "object":
        return (len(a.members) == len(b.members)
                and all(ka == kb and numeric_only_difference(va, vb)
                        for (ka, va), (kb, vb) in zip(a.members, b.members)))
    if a.kind == "array":
        return len(a.members) == len(b.members) and all(
            numeric_only_difference(x, y) for x, y in zip(a.members, b.members))
    return a.raw == b.raw


def minify(text):
    """Remove whitespace outside string literals. Used ONLY by the fixture generator
    to derive canonical bytes from the pretty-printed F.1 examples; lexemes are kept verbatim."""
    out, in_str, esc = [], False, False
    for ch in text:
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
            out.append(ch)
        elif ch not in WHITESPACE:
            out.append(ch)
    return "".join(out)


_validator = None


def f1_validator():
    """Validator for the F.1 structural schema (schemas/canonical-record.schema.json), unmodified."""
    global _validator
    if _validator is None:
        schemas = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(F1_SCHEMA_DIR.glob("*.schema.json"))]
        registry = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in schemas)
        root = next(s for s in schemas if s["$id"].endswith("/canonical-record.schema.json"))
        _validator = Draft202012Validator(root, registry=registry)
    return _validator


# --------------------------------------------------------------------------- format stage

def check_format(data: bytes):
    """Format stage. Returns the parsed top-level Node of a canonical record.

    Raises ValidationError with the highest-precedence format code. Checks run
    in precedence order, so the first failing check is the reported code.
    """
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValidationError("INVALID_UTF8", f"byte offset {exc.start}") from None
    if data.startswith(BOM):
        raise ValidationError("BOM_PRESENT", "file starts with EF BB BF")
    try:
        scanner, node, rest = scan(text)
    except ParseError as exc:
        raise ValidationError("INVALID_JSON", str(exc)) from None
    if rest == "":
        raise ValidationError("MISSING_FINAL_LF", "no LF after the top-level value")
    if rest != "\n":
        raise ValidationError("TRAILING_DATA", f"{len(rest)} character(s) after the top-level value: {rest[:16]!r}")
    if scanner.first_whitespace is not None:
        raise ValidationError("NON_CANONICAL_WHITESPACE", f"character offset {scanner.first_whitespace}")
    if scanner.first_duplicate is not None:
        pos, key = scanner.first_duplicate
        raise ValidationError("DUPLICATE_KEY", f"member {key!r} repeated at character offset {pos}")
    if node.kind != "object":
        raise ValidationError("TYPE_MISMATCH", f"top-level value is {json_type(node)}, not object")
    keys = [k for k, _ in node.members]
    if "invariant" not in keys:
        raise ValidationError("INVARIANT_REMOVED", "top-level 'invariant' is absent")
    missing = [k for k in TOP_LEVEL_ORDER if k not in keys]
    if missing:
        raise ValidationError("MISSING_REQUIRED_FIELD", f"missing: {', '.join(missing)}")
    extra = [k for k in keys if k not in TOP_LEVEL_ORDER]
    if extra:
        raise ValidationError("UNEXPECTED_FIELD", f"unexpected: {', '.join(extra)}")
    if tuple(keys) != TOP_LEVEL_ORDER:
        raise ValidationError("FIELD_ORDER_VIOLATION", f"order: {', '.join(keys)}")
    errors = sorted(f1_validator().iter_errors(to_python(node)), key=lambda e: list(map(str, e.absolute_path)))
    if errors:
        e = errors[0]
        raise ValidationError("TYPE_MISMATCH", f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}")
    return node


def sections(node):
    """Top-level members of a format-valid record, as {name: Node}."""
    return dict(node.members)


def load_bytes(path) -> bytes:
    return Path(path).read_bytes()
