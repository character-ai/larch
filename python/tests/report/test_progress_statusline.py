"""Read-only Python compatibility tests for Rust-owned progress state."""

from __future__ import annotations

import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from larch.report import progress_file


def test_resolve_persisted_run_returns_frozen_named_fields(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = (tmp_path / "session-env.sh").write_text(
        "LARCH_RUN_ID=design-20260714.1\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "source-env.sh").write_text(
        f"REPO_ROOT={repo}\n",
        encoding="utf-8",
    )

    result = progress_file.resolve_persisted_run(tmpdir=tmp_path, env={})

    assert result.run_id == "design-20260714.1"
    assert result.repo_root == repo.resolve()
    with pytest.raises(FrozenInstanceError):
        result.run_id = "other"  # type: ignore[misc]


def test_resolve_owned_run_id_prefers_valid_explicit_environment_and_persisted_values(
    tmp_path: Path,
) -> None:
    _ = (tmp_path / "session-env.sh").write_text(
        "LARCH_RUN_ID=from-session\n",
        encoding="utf-8",
    )

    assert progress_file.resolve_owned_run_id(
        explicit="from-explicit",
        tmpdir=tmp_path,
        env={"LARCH_RUN_ID": "from-environment"},
    ) == "from-explicit"
    assert progress_file.resolve_owned_run_id(
        explicit="bad/id",
        tmpdir=tmp_path,
        env={"LARCH_RUN_ID": "from-environment"},
    ) == "from-environment"
    assert progress_file.resolve_owned_run_id(
        explicit="bad/id",
        tmpdir=tmp_path,
        env={"LARCH_RUN_ID": "bad id"},
    ) == "from-session"


def test_resolve_persisted_repo_root_requires_an_existing_absolute_directory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = (tmp_path / "source-env.sh").write_text(
        "REPO_ROOT=relative\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "session-env.sh").write_text(
        f"export REPO_ROOT='{repo}'\n",
        encoding="utf-8",
    )

    assert progress_file.resolve_persisted_repo_root(tmpdir=tmp_path) == repo.resolve()


@pytest.mark.parametrize(
    "run_id",
    ["", ".", "..", "current", "bad/id", "bad\\id", "bad\nid", "bad id", "bad\tid"],
)
def test_validate_run_id_rejects_unsafe_values(run_id: str) -> None:
    with pytest.raises(ValueError, match=r"run ID|reserved"):
        _ = progress_file.validate_run_id(run_id)


@pytest.mark.parametrize("run_id", ["design-20260708.1", "run_42", "a.b-c"])
def test_validate_run_id_retains_safe_values(run_id: str) -> None:
    assert progress_file.validate_run_id(run_id) == run_id


def test_sessionstart_statusline_harness() -> None:
    result = subprocess.run(
        ["bash", "scripts/test-sessionstart-statusline.sh"],
        cwd=Path(__file__).resolve().parents[3],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
