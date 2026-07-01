"""Tests for sanitized session transcript rendering."""

from __future__ import annotations

import json
from pathlib import Path

from larch.rendering import render_session_transcript


def _render_one(tmp_path: Path, block: dict[str, object]) -> list[dict[str, object]]:
    src = tmp_path / "raw.jsonl"
    _ = src.write_text(
        json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [block]}}) + "\n",
        encoding="utf-8",
    )
    lines = render_session_transcript.render(src).splitlines()
    assert json.loads(lines[0])["policy"] == "prose-errors-and-reference-reads"
    if len(lines) == 1:
        return []
    return json.loads(lines[1])["blocks"]


def test_render_preserves_reference_read(tmp_path: Path) -> None:
    blocks = _render_one(
        tmp_path,
        {
            "type": "tool_use",
            "id": "toolu_1",
            "name": "Read",
            "input": {"file_path": "skills/design/references/approval-gates.md", "offset": 10},
        },
    )
    assert blocks == [
        {"type": "tool_use", "name": "Read", "input": {"file_path": "skills/design/references/approval-gates.md"}}
    ]


def test_render_drops_non_reference_markdown_read(tmp_path: Path) -> None:
    blocks = _render_one(
        tmp_path,
        {"type": "tool_use", "id": "toolu_1", "name": "Read", "input": {"file_path": "docs/guide.md"}},
    )
    assert blocks == []


def test_render_drops_non_read_tool(tmp_path: Path) -> None:
    blocks = _render_one(
        tmp_path,
        {"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": {"command": "pwd"}},
    )
    assert blocks == []


def test_render_preserves_shared_reference_read(tmp_path: Path) -> None:
    blocks = _render_one(
        tmp_path,
        {"type": "tool_use", "id": "toolu_1", "name": "Read", "input": {"file_path": "skills/shared/topology.md"}},
    )
    assert blocks == [{"type": "tool_use", "name": "Read", "input": {"file_path": "skills/shared/topology.md"}}]
