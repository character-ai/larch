"""Tests for pr_body.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import config
import pr_body
from errors import ShipError
from proc import CommandResult


class _NoopRunner:
    def run(self, *args: object, **kwargs: object) -> CommandResult:  # pylint: disable=unused-argument
        return CommandResult((), 0, "", "", 0.0)


def test_sanitize_rejects_pipe_in_node() -> None:
    fragment = "flowchart LR\n  A[foo|bar] --> B\n"
    result = pr_body.sanitize_fragment(fragment)
    assert result.status == "rejected"
    assert config.MERMAID_REASON_PIPE_IN_NODE in result.reason_tokens


def test_sanitize_rejects_unclosed_frontmatter() -> None:
    fragment = "---\ntitle: x\nflowchart LR\n  A --> B\n"
    result = pr_body.sanitize_fragment(fragment)
    assert result.status == "rejected"
    assert config.MERMAID_REASON_UNCLOSED_FRONTMATTER in result.reason_tokens


def test_compose_summary_rejects_absolute_path_without_cwd() -> None:
    with pytest.raises(ShipError, match="escapes repo root"):
        _ = pr_body.compose_summary_bullets(
            _NoopRunner(),  # type: ignore[arg-type]
            plan_goals_file="/etc/passwd",
            cwd=None,
        )


def test_compose_summary_rejects_relative_path_without_cwd() -> None:
    with pytest.raises(ShipError, match="escapes repo root"):
        _ = pr_body.compose_summary_bullets(
            _NoopRunner(),  # type: ignore[arg-type]
            plan_goals_file="docs/plan.md",
            cwd=None,
        )


def test_compose_summary_from_plan(tmp_path: Path) -> None:
    goals = tmp_path / "goals.md"
    _ = goals.write_text("## Goal\n\nShip Phase 5 modules.\n", encoding="utf-8")
    summary = pr_body.compose_summary_bullets(
        _NoopRunner(),  # type: ignore[arg-type]
        plan_goals_file=str(goals),
        cwd=str(tmp_path),
    )
    assert "Ship Phase 5" in summary


def test_sanitize_fenced_mermaid_auto_extracts() -> None:
    fenced = "```mermaid\nflowchart LR\n  A --> B\n```\n"
    result = pr_body.sanitize_fragment(fenced)
    assert result.status == "ok"


def test_compose_pr_body_rejects_bad_mermaid() -> None:
    with pytest.raises(ShipError, match="mermaid fragment rejected"):
        _ = pr_body.compose_pr_body(
            summary="- x",
            mermaid="flowchart LR\n  A[bad|pipe] --> B\n",
        )


def test_compose_pr_body_rejects_bad_mermaid_in_summary() -> None:
    bad_summary = "- x\n\n```mermaid\nflowchart LR\n  A[bad|pipe] --> B\n```\n"
    with pytest.raises(ShipError, match="mermaid in PR body rejected"):
        _ = pr_body.compose_pr_body(summary=bad_summary)


def test_compose_pr_body_fail_closed_on_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_redact(_text: str) -> str:
        return "body [content truncated — safety]"

    monkeypatch.setattr(pr_body.redact, "redact", fake_redact)
    with pytest.raises(ShipError, match="redaction failed"):
        _ = pr_body.compose_pr_body(summary="- x")


def test_update_pr_body_rejects_unsafe_mermaid() -> None:
    bad = "```mermaid\nflowchart LR\n  A[x|y] --> B\n```\n"
    with pytest.raises(ShipError, match="mermaid in PR body rejected"):
        pr_body.update_pr_body(_NoopRunner(), 3, bad, repo="o/r")


def test_update_pr_body_invokes_gh() -> None:
    def new_calls() -> list[list[str]]:
        return []

    @dataclass
    class Runner:
        calls: list[list[str]] = field(default_factory=new_calls)

        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,  # pylint: disable=unused-argument
            cwd: str | None = None,  # pylint: disable=unused-argument
            env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
            check: bool = False,  # pylint: disable=unused-argument
            stdout: int | None = None,  # pylint: disable=unused-argument
            stderr: int | None = None,  # pylint: disable=unused-argument
        ) -> CommandResult:
            self.calls.append(list(argv))
            return CommandResult(tuple(argv), 0, "", "", 0.0)

    runner = Runner()
    pr_body.update_pr_body(runner, 3, "body", repo="o/r")  # type: ignore[arg-type]
    assert runner.calls
    assert runner.calls[0][1] == "pr"
