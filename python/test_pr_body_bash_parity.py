"""Bash parity for mermaid sanitizer and compose-pr-summary."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import config
import pr_body
from proc import CommandResult

REPO_ROOT = Path(__file__).resolve().parents[1]
SANITIZE = REPO_ROOT / "scripts" / "sanitize-mermaid-fragment.sh"
COMPOSE = REPO_ROOT / "scripts" / "compose-pr-summary.sh"


def _bash_sanitize(fragment: str) -> set[str]:
    completed = subprocess.run(
        ["bash", str(SANITIZE), "--input", "/dev/stdin"],
        input=fragment,
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    tokens: set[str] = set()
    for line in completed.stdout.splitlines():
        if line.startswith("REASON_TOKEN="):
            tokens.add(line.split("=", 1)[1].split()[0])
    return tokens


@pytest.mark.skipif(not SANITIZE.is_file(), reason="sanitize script missing")
def test_quoted_pipe_in_node_label_ok() -> None:
    fragment = 'flowchart TD\n  A["foo|bar"]\n'
    py = pr_body.sanitize_fragment(fragment)
    bash_tokens = _bash_sanitize(fragment)
    assert py.status == "ok"
    assert not bash_tokens


@pytest.mark.skipif(not SANITIZE.is_file(), reason="sanitize script missing")
def test_mermaid_reason_tokens_match_bash() -> None:
    fragment = "flowchart LR\n  N[bad|pipe] --> M\n"
    py = pr_body.sanitize_fragment(fragment)
    bash_tokens = _bash_sanitize(fragment)
    if py.status == "rejected":
        assert config.MERMAID_REASON_PIPE_IN_NODE in bash_tokens


@pytest.mark.skipif(not COMPOSE.is_file(), reason="compose script missing")
def test_compose_summary_semantic_parity(tmp_path: Path) -> None:
    goals = tmp_path / "goals.md"
    _ = goals.write_text("## Goal\n\nParity goal line.\n", encoding="utf-8")
    completed = subprocess.run(
        ["bash", str(COMPOSE), "--plan-goals-file", str(goals)],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert completed.returncode == 0
    class _NoopRunner:
        def run(self, *args: object, **kwargs: object) -> CommandResult:  # pylint: disable=unused-argument
            return CommandResult((), 1, "", "", 0.0)

    py_summary = pr_body.compose_summary_bullets(
        _NoopRunner(),  # type: ignore[arg-type]
        plan_goals_file="goals.md",
        cwd=str(tmp_path),
    )
    assert "Parity goal line" in completed.stdout
    assert "Parity goal line" in py_summary


@pytest.mark.skipif(not SANITIZE.is_file(), reason="sanitize script missing")
@pytest.mark.parametrize(
    ("fragment", "reason"),
    [
        (
            "sequenceDiagram\n  participant A as alias<br/>note\n",
            config.MERMAID_REASON_BR_IN_ALIAS,
        ),
        (
            "sequenceDiagram\n  participant A as $alias\n",
            config.MERMAID_REASON_DOLLAR_IN_ALIAS,
        ),
    ],
)
def test_mermaid_rejection_tokens_match_bash(fragment: str, reason: str) -> None:
    py = pr_body.sanitize_fragment(fragment)
    bash_tokens = _bash_sanitize(fragment)
    if py.status == "rejected":
        assert reason in py.reason_tokens
        assert reason in bash_tokens
