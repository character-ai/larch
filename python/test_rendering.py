"""Tests for rendering.py ports."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import logging_util
import rendering

if TYPE_CHECKING:
    import pytest

def _reset_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    logging_util.reset_quiet_state()
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")


def test_mermaid_from_md_rejection_reports_heading(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    doc = tmp_path / "doc.md"
    _ = doc.write_text(
        "## Architecture Diagram\n\n```mermaid\nflowchart LR\n  A[bad|pipe] --> B\n```\n",
        encoding="utf-8",
    )
    rc = rendering.mermaid_sanitize_main(["--input", str(doc), "--from-md"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "STATUS=rejected" in out
    assert "REASON_TOKEN=pipe-in-node-label fence=1 line=2" in out
    assert "FENCE_1_HEADING=architecture" in out


def test_render_lane_status_sanitizes_reason(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    kv = tmp_path / "lanes.env"
    _ = kv.write_text(
        "RESEARCH_ARCH_STATUS=fallback_probe_failed\nRESEARCH_ARCH_REASON=a=b | c\nVALIDATION_CODE_STATUS=ok\n",
        encoding="utf-8",
    )
    rc = rendering.render_lane_status_main(["--input", str(kv)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "RESEARCH_ARCH_HEADER=Architecture: Claude-fallback (probe failed: ab c)" in out
    assert "VALIDATION_CODE_HEADER=Code: ✅" in out


def test_reviewer_renderer_preserves_ampersand_target(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    q = tmp_path / "q.txt"
    c = tmp_path / "c.txt"
    ins = tmp_path / "ins.txt"
    _ = q.write_text("question", encoding="utf-8")
    _ = c.write_text("context with {REVIEW_TARGET}", encoding="utf-8")
    _ = ins.write_text("Find issues", encoding="utf-8")
    rc = rendering.render_reviewer_main(
        [
            "--target",
            "R&D findings",
            "--research-question-file",
            str(q),
            "--context-file",
            str(c),
            "--in-scope-instruction-file",
            str(ins),
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "R&D findings" in out
    assert "context with {REVIEW_TARGET}" in out


def test_generate_check_accepts_verb_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    assert rendering.generate_check_main([]) == 0


def test_topology_header_uses_python_invocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    target = tmp_path / "topology.md"
    monkeypatch.setenv("LARCH_TOPOLOGY_DOC", str(target))
    assert rendering.generate_topology_docs_main([]) == 0
    text = target.read_text(encoding="utf-8")
    assert "Regenerate via: python3 python/cli.py generate topology-docs" in text


def test_diagrams_upsert_dry_run_merges_sections(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_quiet(monkeypatch)
    section = tmp_path / "code.md"
    _ = section.write_text("## Code Flow Diagram\n\n```mermaid\nflowchart LR\n  A[Start] --> B[Done]\n```\n", encoding="utf-8")
    rc = rendering.diagrams_upsert_main(
        [
            "--issue",
            "42",
            "--code-flow-file",
            str(section),
            "--allow-external-paths",
            "--dry-run",
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "<!-- larch:diagrams v1 -->" in out
    assert "## Code Flow Diagram" in out
    assert "UPSERT_STATUS=ok" in out
