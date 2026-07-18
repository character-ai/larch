from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from larch.lint.lint_codex_exec_auth import main
from tests.lint.conftest import lint_runner

if TYPE_CHECKING:
    import pytest


def write(path: Path, *lines: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text("\n".join(lines) + "\n", encoding="utf-8")


run = lint_runner(main)


def test_clean_and_allowlisted_launcher(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "python/larch/agents/agents.py", 'child = ["codex", "exec", "--full-auto"]')
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_non_python_surfaces_are_owned_by_rust(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "scripts/bad.sh", "#!/bin/bash", "codex exec --full-auto -C . hi")
    write(tmp_path / ".claude/skills/dev/SKILL.md", "```bash", "codex exec --full-auto -C . hi", "```")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_python_raw_exec_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "python/new_launcher.py", 'subprocess.run(["codex", "exec", "--full-auto"])')
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "python/new_launcher.py:1:" in err


def test_out_of_scope_ignored_and_invalid_root(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "docs/out.md", "```bash", "codex exec hi", "```")
    write(tmp_path / "hooks/out.sh", "codex exec hi")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err
    assert main(["--root", "/no/such/path/for/codex-lint"]) == 2
    assert "not a directory" in capsys.readouterr().err
