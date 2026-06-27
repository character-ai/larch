from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from larch.lint.lint_gh_body_inline import main


BODY = "--" + "body"
NOTES = "--" + "notes"
GH = "g" + "h"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_clean_tree(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "scripts/good.sh", f"{GH} issue comment 1 {BODY}-file body.md\n{GH} release create v1 {NOTES}-file notes.md\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


@pytest.mark.parametrize(("name", "opt", "replacement"), [("bad_body.sh", BODY, BODY + "-file"), ("bad_notes.sh", NOTES, NOTES + "-file")])
def test_inline_payloads_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str], name: str, opt: str, replacement: str) -> None:
    write(tmp_path / "scripts" / name, f'{GH} issue comment 1 {opt} "hi"\n')
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert f"scripts/{name}:1:" in err
    assert replacement in err


def test_pragma_and_comments(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "scripts/allowed.sh", f'{GH} issue comment 1 {BODY} "hi" # lint-gh-body-inline: ok fixture\n')
    write(tmp_path / "scripts/comment.sh", f'# {GH} issue comment 1 {BODY} "hi"\n')
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_python_argv_and_equals_form(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "scripts/bad.py", f'import subprocess\nsubprocess.run(["{GH}", "issue", "create", "{BODY}", "x"])\n')
    write(tmp_path / "scripts/equals.sh", f'{GH} issue comment 1 {BODY}="hi"\n')
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "scripts/bad.py:2:" in err
    assert "scripts/equals.sh:1:" in err


def test_git_untracked_and_larch_logs_exclusion(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    write(tmp_path / "scripts/untracked.sh", f'{GH} issue comment 1 {BODY} "hi"\n')
    write(tmp_path / "larch-logs/run/script.sh", f'{GH} issue comment 1 {BODY} "hi"\n')
    _ = subprocess.run(["git", "add", "larch-logs/run/script.sh"], cwd=tmp_path, check=True)
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "scripts/untracked.sh:1:" in err
    assert "larch-logs" not in err


def test_invalid_root(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--root", "/no/such/path/for/gh-lint"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "not a directory" in err
