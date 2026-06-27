"""Tests for bounded diagram failure logging helpers."""

from __future__ import annotations

from pathlib import Path

import design_diagram_log
from larch.design import design_log_publish_flow


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


def test_strip_diagram_sections_removes_unfenced_graph_syntax() -> None:
    text = "before\ngraph TD\nA-->B\nafter\n"
    stripped = design_diagram_log.strip_diagram_sections(text)
    assert "before" in stripped
    assert "after" in stripped
    assert "graph TD" not in stripped
    assert "A-->B" not in stripped


def test_strip_diagram_sections_removes_participant_subgraph_and_sequence_arrows() -> None:
    text = (
        "before\n"
        "participant A as Alice\n"
        "A->>B: hi\n"
        "subgraph group\n"
        "classDef foo fill:#fff\n"
        "style A fill:#000\n"
        "after\n"
    )
    stripped = design_diagram_log.strip_diagram_sections(text)
    assert "before" in stripped
    assert "after" in stripped
    assert "participant" not in stripped
    assert "->>" not in stripped
    assert "subgraph" not in stripped
    assert "classDef" not in stripped
    assert "style A" not in stripped


def test_strip_diagram_sections_preserves_edge_like_operator_text_outside_diagram() -> None:
    text = "module A --> module B failed\nkeep this\n"
    stripped = design_diagram_log.strip_diagram_sections(text)
    assert "module A --> module B failed" in stripped
    assert "keep this" in stripped


def test_sanitize_diagram_capture_fails_closed_on_mermaid_remainder() -> None:
    assert design_diagram_log.sanitize_diagram_capture("```mermaid\ngraph TD\n```") == "diagram-content-redacted"
    assert design_diagram_log.sanitize_diagram_capture("participant A\nA->>B: hi") == "diagram-content-redacted"


def test_strip_diagram_sections_removes_generic_fenced_blocks() -> None:
    text = "keep\n```python\nprint('x')\n```\ntail\n"
    stripped = design_diagram_log.strip_diagram_sections(text)
    assert "keep" in stripped
    assert "tail" in stripped
    assert "print" not in stripped
    assert "```" not in stripped


def test_bounded_sidecar_redacts_reason_and_excludes_bounded_log_from_publish(tmp_path: Path) -> None:
    sidecar = design_diagram_log.write_bounded_diagram_failure_log(
        tmp_path,
        site="design Step 5b.5",
        reason="graph TD\nA-->B\nkey=sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890ABCDEF",
        exit_code=1,
    )
    text = sidecar.read_text(encoding="utf-8")
    assert "graph TD" not in text
    assert "A-->B" not in text
    assert "sk-ant-" not in text
    assert design_log_publish_flow._publish_excluded(  # pyright: ignore[reportPrivateUsage]
        "design-step-5b.5-diagram-failure.bounded.log",
        is_dir=False,
        top_level=True,
    )
