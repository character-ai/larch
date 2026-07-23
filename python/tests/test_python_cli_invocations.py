"""Regression coverage for non-executable Python CLI command instructions."""
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATHS = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "docs",
    "skills",
    "agents",
    "hooks",
    "scripts",
    ".claude-plugin",
    ".claude",
    ".github",
    "plugin",
)
EXCLUDED_PATH_PARTS = frozenset({"attic", "test_fixtures", "__pycache__"})
DIRECT_PYTHON_CLI = re.compile(
    r'(?<!python3 )(?<!=)"\$\{CLAUDE_PLUGIN_ROOT\}/python/cli\.py"'
)


def _runtime_files() -> list[Path]:
    files: list[Path] = []
    for relative in RUNTIME_PATHS:
        path = REPO_ROOT / relative
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(child for child in path.rglob("*") if child.is_file())
    return sorted(
        (path for path in files if not EXCLUDED_PATH_PARTS.intersection(path.parts)),
        key=lambda path: path.relative_to(REPO_ROOT).as_posix(),
    )


def test_live_python_cli_invocations_use_python3() -> None:
    """Reject every direct instruction, listing all source locations at once."""
    violations: list[str] = []
    for path in _runtime_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if DIRECT_PYTHON_CLI.search(line):
                relative = path.relative_to(REPO_ROOT).as_posix()
                violations.append(f"{relative}:{line_number}: {line.strip()}")

    assert not violations, (
        "Direct execution of non-executable python/cli.py is forbidden; "
        "invoke it with python3:\n" + "\n".join(violations)
    )
