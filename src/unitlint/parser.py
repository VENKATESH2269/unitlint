"""A small parser for systemd unit files.

systemd unit files look like INI files but differ in a few ways that matter
for linting: keys may repeat, lines ending in a backslash continue on the next
line, and both ``#`` and ``;`` start comments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Directive:
    section: str
    key: str
    value: str
    line: int


@dataclass
class UnitFile:
    path: str
    directives: List[Directive] = field(default_factory=list)
    section_lines: Dict[str, int] = field(default_factory=dict)
    syntax_errors: List[Tuple[int, str]] = field(default_factory=list)

    def has_section(self, name: str) -> bool:
        return name in self.section_lines

    def section_line(self, name: str) -> int:
        return self.section_lines.get(name, 1)

    def all(self, section: str, key: str) -> List[Directive]:
        return [d for d in self.directives if d.section == section and d.key == key]

    def get(self, section: str, key: str) -> Optional[Directive]:
        """Return the effective directive (systemd uses the last assignment)."""
        found = self.all(section, key)
        return found[-1] if found else None

    def value(self, section: str, key: str, default: str = "") -> str:
        directive = self.get(section, key)
        return directive.value.strip() if directive else default

    def tokens(self, section: str, key: str) -> List[str]:
        """All whitespace-separated words from every assignment of a key."""
        words: List[str] = []
        for directive in self.all(section, key):
            words.extend(directive.value.split())
        return words


def _logical_lines(text: str) -> List[Tuple[int, str]]:
    """Join backslash-continued lines. Returns (first_line_number, text)."""
    logical: List[Tuple[int, str]] = []
    buffer = ""
    start = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        if not buffer:
            start = number
        if line.endswith("\\"):
            buffer += line[:-1] + " "
            continue
        logical.append((start, buffer + line))
        buffer = ""
    if buffer:
        logical.append((start, buffer))
    return logical


def parse(text: str, path: str = "<unit>") -> UnitFile:
    unit = UnitFile(path=path)
    section: Optional[str] = None
    for number, line in _logical_lines(text):
        stripped = line.strip()
        if not stripped or stripped[0] in "#;":
            continue
        if stripped.startswith("["):
            if not stripped.endswith("]") or len(stripped) < 3:
                unit.syntax_errors.append((number, "malformed section header"))
                continue
            section = stripped[1:-1]
            unit.section_lines.setdefault(section, number)
            continue
        if "=" not in stripped:
            unit.syntax_errors.append(
                (number, f"line is not a 'Key=Value' assignment: {stripped[:40]!r}")
            )
            continue
        if section is None:
            unit.syntax_errors.append((number, "assignment appears before any [Section]"))
            continue
        key, value = stripped.split("=", 1)
        unit.directives.append(Directive(section, key.strip(), value.strip(), number))
    return unit
