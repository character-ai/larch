from __future__ import annotations

from pathlib import Path

import pytest

from lint_codex_exec_auth import main


def write(path: Path, *lines: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_clean_and_allowlisted_launcher(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "python/larch/agents/agents.py", 'child = ["codex", "exec", "--full-auto"]')
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


@pytest.mark.parametrize(
    "line",
    [
        "codex exec --full-auto -C . hi",
        '"codex" exec --full-auto -C . hi',
        "'codex' exec --full-auto -C . hi",
        "\\codex exec --full-auto -C . hi",
        "CODEX_HOME=/tmp/codex OTHER=1 codex exec --full-auto -C . hi",
        "A=1 B=codex exec --full-auto -C . hi",
    ],
)
def test_shell_raw_exec_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str], line: str) -> None:
    write(tmp_path / "scripts/bad.sh", "#!/bin/bash", line)
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "scripts/bad.sh:2:" in err


@pytest.mark.parametrize("rel", ["scripts/" + "check-reviewers" + ".sh", "scripts/" + "run-negotiation-round" + ".sh"])
def test_retired_script_names_are_not_allowlisted(tmp_path: Path, capsys: pytest.CaptureFixture[str], rel: str) -> None:
    write(tmp_path / rel, "#!/bin/bash", "codex exec --full-auto -C . hi")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert f"{rel}:2:" in err


def test_pragma_comments_and_continuation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "scripts/pragma.sh", "codex exec hi # lint-codex-exec-auth: ok fixture")
    write(tmp_path / "scripts/comment.sh", "# codex exec hi")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err
    write(tmp_path / "scripts/continued.sh", "codex \\", "  exec --full-auto -C . hi")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "scripts/continued.sh:1:" in err


def test_markdown_fences(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "skills/foo/SKILL.md", "```Bash", "codex exec --full-auto -C . hi", "```")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/foo/SKILL.md:2:" in err


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
