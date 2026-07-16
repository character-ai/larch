"""Cycle-free leaf helpers shared by rendering.py and _rendering_generators.py.

Must not import rendering.py, _rendering_generators.py, CLI modules, or package
facades. Callers import these helpers; this module stays below both in the
import graph.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from pathlib import Path

from larch import io as larch_io

FRONTMATTER_FENCE_COUNT = 2


class RenderError(RuntimeError):
    """Rendering drift or runtime error."""


def write_text_atomic(*, path: Path, text: str) -> None:
    larch_io.atomic_write(path=path, text=text, prefix=f".{path.name}.")


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def frontmatter_body(path: Path) -> str:
    lines = larch_io.read_text(path).splitlines()
    count = 0
    for i, line in enumerate(lines):
        if re.fullmatch(r"---\s*", line):
            count += 1
            if count == FRONTMATTER_FENCE_COUNT:
                return "\n".join(lines[i + 1 :])
    return ""


def extract_generated_body(template: Path, *, heading: str | None = None) -> str:
    lines = larch_io.read_text(template).splitlines()
    in_section = heading is None
    in_body = False
    found = False
    buf: list[str] = []
    skipped_open = False
    for line in lines:
        if heading is not None and line == heading:
            in_section = True
            continue
        if found:
            continue
        if in_section and "<!-- BEGIN GENERATED_BODY -->" in line:
            in_body = True
            skipped_open = False
            continue
        if in_body and "<!-- END GENERATED_BODY -->" in line:
            in_body = False
            in_section = False
            found = True
            continue
        if in_body:
            if not skipped_open:
                skipped_open = True
                continue
            buf.append(line)
    if not found or not buf:
        label = heading or "GENERATED_BODY"
        raise RenderError(f"ERROR: no content found for {label} between BEGIN/END GENERATED_BODY markers")
    if buf[-1] != "```":
        raise RenderError(f"ERROR: expected outer close fence ``` as last line inside GENERATED_BODY markers; got: {buf[-1]}")
    return "\n".join(buf[:-1])


def replace_output_instruction(body: str, *, inscope: Iterable[str], oos: Iterable[str]) -> str:
    out: list[str] = []
    section = ""
    for line in body.splitlines():
        if line == "### In-Scope Findings":
            section = "in_scope"
            out.append(line)
            continue
        if line == "### Out-of-Scope Observations":
            section = "oos"
            out.append(line)
            continue
        if line == "- {OUTPUT_INSTRUCTION}":
            if section == "in_scope":
                out.extend(f"- {item}" for item in inscope if item)
            elif section == "oos":
                out.extend(f"- {item}" for item in oos if item)
            else:
                raise RenderError("{OUTPUT_INSTRUCTION} encountered outside a known section")
            continue
        out.append(line)
    return "\n".join(out)


def extract_template_fragment(template: Path, *, name: str) -> str:
    """Read a named canonical fragment delimited by stable HTML comments."""
    text = larch_io.read_text(template)
    match = re.search(
        rf"<!-- BEGIN {re.escape(name)} -->\n(.*?)\n<!-- END {re.escape(name)} -->",
        text,
        flags=re.DOTALL,
    )
    if match is None or not match.group(1).strip():
        raise RenderError(f"ERROR: no content found for canonical fragment {name}")
    return match.group(1).strip()
