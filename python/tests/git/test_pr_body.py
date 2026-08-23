"""Tests for pr_body.py."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

from larch.core import config
from larch.git import pr_body


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


def test_sanitize_fenced_mermaid_auto_extracts() -> None:
    fenced = "```mermaid\nflowchart LR\n  A --> B\n```\n"
    result = pr_body.sanitize_fragment(fenced)
    assert result.status == "ok"
