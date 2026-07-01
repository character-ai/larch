from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from larch.lint.lint_flat_tests import main


def write(root: Path, rel: str, text: str = "x\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_clean_tree_without_root_tests_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "python/tests/lint/test_example.py")

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_support_helper_is_the_only_root_exemption(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "python/test_support.py")

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_flat_root_test_fails_with_path_diagnostic(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "python/test_example.py")

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "lint-flat-tests: python/test_example.py" in err
    assert "move test modules under python/tests/" in err


def test_nested_mirrored_tests_do_not_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "python/tests/lint/test_example.py")

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_invalid_root_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--root", str(tmp_path / "missing")])
    err = capsys.readouterr().err

    assert rc == 2
    assert "--root is not a directory" in err


def test_git_worktree_untracked_root_tests_are_included(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if shutil.which("git") is None:
        pytest.skip("git is required for worktree enumeration")
    _ = subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    write(tmp_path, "python/test_untracked.py")

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "python/test_untracked.py" in err
