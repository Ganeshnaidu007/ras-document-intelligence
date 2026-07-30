"""parsers/structure_parser.py — Detect document structure (headings, sections, lists)."""
import re
from typing import List, Dict, Any


HEADING_PATTERNS = [
    re.compile(r"^#{1,6}\s+(.+)"),               # Markdown headings
    re.compile(r"^([A-Z][A-Z\s]{3,})$"),          # ALL CAPS headings
    re.compile(r"^(\d+\.\d*\s+.+)"),           # Numbered sections 1.2 Title
]


def detect_headings(text: str) -> List[Dict[str, Any]]:
    headings = []
    for i, line in enumerate(text.splitlines(), 1):
        for pat in HEADING_PATTERNS:
            m = pat.match(line.strip())
            if m:
                headings.append({"line": i, "text": m.group(1).strip(), "raw": line})
                break
    return headings


def split_by_sections(text: str) -> List[Dict[str, Any]]:
    lines    = text.splitlines()
    sections = []
    cur_title, cur_lines = "Preamble", []
    for line in lines:
        is_heading = any(p.match(line.strip()) for p in HEADING_PATTERNS)
        if is_heading and cur_lines:
            sections.append({"title": cur_title, "text": "\n".join(cur_lines).strip()})
            cur_title  = line.strip(); cur_lines = []
        else:
            cur_lines.append(line)
    if cur_lines:
        sections.append({"title": cur_title, "text": "\n".join(cur_lines).strip()})
    return sections
