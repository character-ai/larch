"""Shared throwaway-git-repository fixture for lint baseline tests."""

from __future__ import annotations

import contextlib
import io
import subprocess
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

from larch.lint.engine import LintRule, run_rule

_GIT_INIT_STEPS = (
    ("init", "-q"),
    ("config", "user.email", "test@example.com"),
    ("config", "user.name", "test"),
    ("add", "-A"),
    ("commit", "-q", "-m", "fixture", "--allow-empty"),
)


def init_repo(root: Path) -> None:
    """Initialize a disposable git repository fixture under ``root``."""
    for step in _GIT_INIT_STEPS:
        _ = subprocess.run(  # lint-subprocess-via-runner: ok test fixture bootstraps a throwaway git repo
            ["git", *step], cwd=root, check=True  # noqa: S607 - git is a required test fixture dependency
        )


def write_python_files(root: Path, files: dict[str, str]) -> Path:
    """Write Python fixture files and return their project directory."""
    python_dir = root / "python"
    for relpath, source in files.items():
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    return python_dir


def invoke_lint_main(
    main: Callable[[list[str]], int], root: Path, argv: list[str]
) -> tuple[int, str, str]:
    """Run a lint CLI main and capture its public output streams."""
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(["--root", str(root), *argv])
    return code, stdout.getvalue(), stderr.getvalue()


def invoke_engine_rule(  # noqa: PLR0913 - mirrors the engine rule API for tests.
    rule: LintRule,
    root: Path,
    runner: Any,
    *,
    paths: list[str] | None = None,
    baseline_path: str | Path | None = None,
    write_baseline: bool = False,
    initial_reason: str | None = None,
    strict_stale: bool = False,
) -> tuple[int, str, str]:
    """Run one engine rule and capture its public output streams."""
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = run_rule(
            rule,
            root,
            runner,
            paths=paths,
            baseline_path=baseline_path,
            write_baseline=write_baseline,
            initial_reason=initial_reason,
            strict_stale=strict_stale,
        )
    return code, stdout.getvalue(), stderr.getvalue()


def make_engine_rule_invoker(rule: LintRule) -> Callable[..., tuple[int, str, str]]:
    """Bind one lint rule for test modules that vary only its arguments."""
    return partial(invoke_engine_rule, rule)


def make_lint_main_invoker(
    main: Callable[[list[str]], int],
) -> Callable[[Path, list[str]], tuple[int, str, str]]:
    """Bind one lint CLI main for test modules."""
    return partial(invoke_lint_main, main)


def make_python_baseline_rule_invoker(
    rule: LintRule,
    baseline_name: str,
    *,
    non_strict_when_writing: bool = False,
) -> Callable[..., tuple[int, str, str]]:
    """Bind a rule whose baseline is stored below the fixture's Python root."""
    def invoke(  # noqa: PLR0913 - preserves each lint test's established helper surface.
        root: Path,
        runner: Any,
        *,
        write_baseline: bool = False,
        initial_reason: str | None = None,
        strict_stale: bool = True,
        baseline_name: str = baseline_name,
    ) -> tuple[int, str, str]:
        effective_strict_stale = (
            False if non_strict_when_writing and write_baseline else strict_stale
        )
        return invoke_engine_rule(
            rule,
            root,
            runner,
            baseline_path=root / "python" / baseline_name,
            write_baseline=write_baseline,
            initial_reason=initial_reason,
            strict_stale=effective_strict_stale,
        )

    return invoke
