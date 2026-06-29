from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from larch.lint.lint_run_log_run_id import find_violations, main


def _init_repo(root: Path) -> None:
    for argv in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@example.com"],
        ["git", "config", "user.name", "t"],
    ):
        _ = subprocess.run(argv, cwd=root, check=True, capture_output=True)


def _add(root: Path, rel: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text("{}", encoding="utf-8")
    _ = subprocess.run(["git", "add", "--", rel], cwd=root, check=True, capture_output=True)


def test_clean_tree_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init_repo(tmp_path)
    _add(tmp_path, "larch-logs/implement/0199F1E2-2238-403D-89F3-F37CA6989999/manifest.json")
    _add(tmp_path, "larch-logs/design/ABCDEF01-2345-6789-ABCD-EF0123456789/manifest.json")
    _add(tmp_path, "larch-logs/shared/state.json")
    assert main(["--root", str(tmp_path)]) == 0, capsys.readouterr().err


@pytest.mark.parametrize("skill", ["implement", "design", "review"])
def test_placeholder_run_dir_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    skill: str,
) -> None:
    _init_repo(tmp_path)
    _add(tmp_path, f"larch-logs/{skill}/run-1/manifest.json")
    assert main(["--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert f"larch-logs/{skill}/run-1/manifest.json" in err
    assert "#4397" in err


def test_find_violations_only_flags_run_n(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _add(tmp_path, "larch-logs/implement/run-12/manifest.json")
    _add(tmp_path, "larch-logs/implement/run-abc/manifest.json")
    _add(tmp_path, "larch-logs/implement/9F1C2D3E-1111-2222-3333-444455556666/manifest.json")
    assert find_violations(tmp_path.resolve()) == ["larch-logs/implement/run-12/manifest.json"]


def test_missing_root_returns_2(tmp_path: Path) -> None:
    assert main(["--root", str(tmp_path / "nope")]) == 2
