"""Tests for bounded diagram failure logging helpers."""

from __future__ import annotations

from pathlib import Path

import design_diagram_log


def test_strip_diagram_sections_removes_diagram_bodies_and_mermaid_fences() -> None:
    text = """before
## Architecture Diagram

```mermaid
graph TD
A-->B
```
## Kept
keep this
```mermaid
sequenceDiagram
A->>B: hi
```
## Code Flow Diagram
```mermaid
graph LR
C-->D
```
## After
after
"""

    stripped = design_diagram_log.strip_diagram_sections(text)

    assert "before" in stripped
    assert "## Kept" in stripped
    assert "keep this" in stripped
    assert "after" in stripped
    assert "Architecture Diagram" not in stripped
    assert "Code Flow Diagram" not in stripped
    assert "```mermaid" not in stripped
    assert "A-->B" not in stripped
    assert "C-->D" not in stripped


def test_bounded_sidecar_contains_no_fence_tokens(tmp_path: Path) -> None:
    raw = tmp_path / "raw.log"
    _ = raw.write_text(
        "stderr before\n## Code Flow Diagram\n```mermaid\ngraph TD\nA-->B\n```\nstderr after\n",
        encoding="utf-8",
    )

    sidecar = design_diagram_log.write_bounded_diagram_failure_log(
        tmp_path,
        site="design Step 5b.5",
        reason="sanitizer-rejected",
        exit_code=7,
        raw_capture_path=raw,
    )

    text = sidecar.read_text(encoding="utf-8")
    assert "site=design Step 5b.5" in text
    assert "reason=sanitizer-rejected" in text
    assert "exit-code=7" in text
    assert "```" not in text
    assert "mermaid" not in text.lower()
    assert "A-->B" not in text
