# -*- coding: utf-8 -*-
"""Shared vault primitives for the Isopoda pipeline.

One home for the path resolution, filename sanitiser, YAML-frontmatter
reader/writer, and atomic file writer that every other script needs. The
frontmatter writers here are the *correct* implementations — they replace the
three ad-hoc copies that previously lived in atlas.py, which mis-handled
backslashes in re.sub replacements, silently folded multi-line YAML values into
scalars, and emitted invalid YAML for several metacharacters.

Design rules honoured throughout:
  * replacement is done with a *function* replacement, so a value containing a
    backslash or a "\\1" is never re-interpreted as a regex escape;
  * a key whose value is a YAML *block* (blank header + indented continuation)
    is never rewritten — we refuse rather than corrupt it;
  * writes are atomic (temp file + os.replace) and newline-exact (LF, matching
    .gitattributes), and skipped entirely when the content is unchanged.

Python 3.9+.
"""
import os
import re
from pathlib import Path

# ---------------------------------------------------------------- paths
# Derive the vault root from this file's location (scripts/ lives inside the
# vault). An explicit ISOPOD_VAULT env var wins, for running against a copy.
VAULT = Path(os.environ.get("ISOPOD_VAULT") or Path(__file__).resolve().parent.parent)
ISOPODA = VAULT / "Isopoda"
HOBBY = VAULT / "Hobby"
MAPS = VAULT / "Maps"
DATA = VAULT / "data"

# ---------------------------------------------------------------- names
_FORBIDDEN = re.compile(r'[\\/:*?"<>|]')


def safe(name):
    """Sanitise a taxon name for use as a path segment (cross-platform)."""
    return _FORBIDDEN.sub("-", name).strip()


# ---------------------------------------------------------------- YAML scalars
_YAML_SPECIAL = re.compile(r'[:#\[\]{}",]')
_YAML_LOOKALIKE = {"yes", "no", "true", "false", "on", "off", "null", "~", "y", "n"}
_YAML_LEAD = tuple("*&!%@`>|?-,[]{}#\"'")


def emit_val(v):
    """Serialise a Python value as a single-line YAML scalar, quoting (and
    escaping) whenever a bare form would be misread. Returns "" for empty."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None or v == "":
        return ""
    if isinstance(v, list):
        return "[" + ", ".join(str(x) for x in v) + "]"
    s = str(v)
    needs_quote = (
        _YAML_SPECIAL.search(s)
        or s != s.strip()
        or s[:1] in _YAML_LEAD
        or s.lower() in _YAML_LOOKALIKE
    )
    if needs_quote:
        return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')
    return s


# ---------------------------------------------------------------- frontmatter
# group(1)=opening '---\n', group(2)=body of frontmatter, group(3)=closing
# '---\n', group(4)=note body.
_FM = re.compile(r"\A(---\r?\n)(.*?\r?\n)(---\r?\n)(.*)\Z", re.S)


def parse_frontmatter(text):
    """Return (open, fm, close, body) or None if there's no frontmatter block."""
    m = _FM.match(text)
    return (m.group(1), m.group(2), m.group(3), m.group(4)) if m else None


_SYNONYM = re.compile(r"^type:[ \t]*synonym[ \t]*$", re.M)


def is_synonym_note(path):
    """True if the note is a synonym record rather than an accepted species.

    Synonym records live in the tree (they document the superseded name and link
    to the accepted one) but must never be counted as accepted species."""
    text = read_text(path)
    if not text:
        return False
    parsed = parse_frontmatter(text)
    return bool(_SYNONYM.search(parsed[1])) if parsed else False


def species_note_paths(root=None):
    """Every accepted-species note under `root` (default: Isopoda/), excluding
    index notes (leading underscore) and synonym records."""
    base = root or ISOPODA
    for p in sorted(base.rglob("*.md")):
        if p.name.startswith("_") or is_synonym_note(p):
            continue
        yield p


def is_block_value(fm, key):
    """True if `key` holds a multi-line YAML value (blank header followed by an
    indented continuation line, e.g. a block list). Such values must never be
    rewritten by the single-line setters below."""
    return re.search(r"^%s:[ \t]*\r?\n[ \t]+\S" % re.escape(key), fm, re.M) is not None


def set_field(fm, key, value, before="tags"):
    """Set `key` to `value` in a frontmatter string (overwrite or insert).

    A blank/empty value is a no-op. A block-valued key is left untouched.
    Insertion places the new key immediately before `before` (default: tags),
    or appends if that anchor is absent. Returns the new frontmatter string."""
    val = emit_val(value)
    if val == "" or is_block_value(fm, key):
        return fm
    if re.search(r"^%s:" % re.escape(key), fm, re.M):
        # function replacement -> the value is never scanned for regex escapes
        return re.sub(r"^%s:.*$" % re.escape(key),
                      lambda _m: "%s: %s" % (key, val), fm, count=1, flags=re.M)
    line = "%s: %s\n" % (key, val)
    anchor = re.search(r"^%s:" % re.escape(before), fm, re.M)
    return (fm[:anchor.start()] + line + fm[anchor.start():]) if anchor else (fm + line)


def ensure_field(fm, key, value, before="tags"):
    """Guarantee `key` exists. If present and blank and `value` is given, fill
    it; if present and already populated, leave it (hand edits win). If missing,
    insert it — with the value, or blank when no value. Block values untouched.
    Blank insertions carry no trailing space."""
    if is_block_value(fm, key):
        return fm
    m = re.search(r"^(%s):[ \t]*(.*)$" % re.escape(key), fm, re.M)
    if m:
        if value and not m.group(2).strip():
            return set_field(fm, key, value, before)
        return fm
    val = emit_val(value)
    line = ("%s: %s\n" % (key, val)) if val else ("%s:\n" % key)
    anchor = re.search(r"^%s:" % re.escape(before), fm, re.M)
    return (fm[:anchor.start()] + line + fm[anchor.start():]) if anchor else (fm + line)


# ---------------------------------------------------------------- io
def read_text(path):
    """Read a file preserving its exact bytes (no newline translation), or
    None if it does not exist."""
    p = Path(path)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write_if_changed(path, text):
    """Write `text` to `path` only if it differs from what's there. Atomic
    (temp file + os.replace) and newline-exact. Returns True if it wrote."""
    p = Path(path)
    if p.exists():
        with open(p, "r", encoding="utf-8", newline="") as f:
            if f.read() == text:
                return False
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, p)
    return True
