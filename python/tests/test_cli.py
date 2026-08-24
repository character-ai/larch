"""Tests for the temporary empty Python dispatcher."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from larch import cli


PYTHON_DIR = Path(__file__).resolve().parents[1]
CLI_PATH = PYTHON_DIR / "cli.py"
DISPATCHER_PATH = PYTHON_DIR / "larch" / "cli.py"


def test_runtime_tree_contains_only_dispatcher() -> None:
    files = sorted(
        path.relative_to(PYTHON_DIR).as_posix()
        for path in (PYTHON_DIR / "larch").rglob("*.py")
    )
    assert files == ["larch/cli.py"]


def test_dispatcher_registry_is_empty() -> None:
    namespace = vars(cli)
    assert namespace["_REGISTRY"] == {}
    assert not namespace["_MACHINE_STDOUT_KEYS"]


@pytest.mark.parametrize("argv", [[], ["-h"], ["--help"]])
def test_help_exits_zero(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(argv) == 0
    captured = capsys.readouterr()
    assert "Available subcommands:" in captured.out
    assert captured.err == ""


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["unknown", "verb"], "unknown subcommand"),
        (["unknown"], "missing verb"),
    ],
)
def test_invalid_command_exits_two(
    argv: list[str], message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert message in captured.err


def test_entrypoint_shim_imports_only_the_dispatcher() -> None:
    source = CLI_PATH.read_text(encoding="utf-8")
    imports = {
        line.strip()
        for line in source.splitlines()
        if line.startswith(("import ", "from "))
        and not line.startswith("from __future__")
    }
    assert imports == {"import sys", "import larch.cli as _cli"}


def test_dispatcher_imports_only_stdlib_modules() -> None:
    source = DISPATCHER_PATH.read_text(encoding="utf-8")
    imports = {
        line.strip()
        for line in source.splitlines()
        if line.startswith(("import ", "from "))
        and not line.startswith("from __future__")
    }
    assert imports == {"import argparse", "import importlib", "import os", "import sys"}


def test_subprocess_help() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Available subcommands:" in result.stdout
    assert result.stderr == ""


def test_subprocess_unknown_command_exits_two() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "unknown", "verb"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "unknown subcommand" in result.stderr
