"""Tests for the root-resolution adoption lint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from larch.lint import lint_root_resolution as lint
from larch.lint.engine import Finding, LintRule, SourceFile


def _rule(tmp_path: Path, rows: list[dict[str, object]] | None = None) -> LintRule:
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir()
    _ = baseline.write_text(json.dumps(rows or []), encoding="utf-8")
    return lint.build_rule(tmp_path)


def _source(path: str, text: str) -> SourceFile:
    return SourceFile(path=path, text=text, lines=tuple(text.splitlines()))


def test_detect_rejects_private_plugin_root(tmp_path: Path) -> None:
    rule = _rule(tmp_path)

    findings = cast("list[Finding]", rule.detect(_source("python/larch/demo.py", "def _plugin_root():\n    return None\n")))

    assert len(findings) == 1
    assert isinstance(findings[0], Finding)
    assert findings[0].message.startswith("private-plugin-root")


def test_detect_rejects_new_inline_git_toplevel_after_baseline_count(tmp_path: Path) -> None:
    rule = _rule(tmp_path, [{
        "path": "python/larch/demo.py",
        "kind": "inline-git-toplevel",
        "count": 1,
        "reason": "one legacy command-result caller",
    }])
    source = _source(
        "python/larch/demo.py",
        "one = ['git', 'rev-parse', '--show-toplevel']\ntwo = ['git', 'rev-parse', '--show-toplevel']\n",
    )

    findings = cast("list[Finding]", rule.detect(source))

    assert len(findings) == 1
    assert findings[0].message.endswith("occurrence 2)")


def test_detect_exempts_the_canonical_owner(tmp_path: Path) -> None:
    rule = _rule(tmp_path)

    assert rule.detect(_source("python/larch/core/repo_roots.py", "cmd = ['git', 'rev-parse', '--show-toplevel']\n")) == []
