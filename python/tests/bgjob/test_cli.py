from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from larch.bgjob import cli, model


def _ns(*, tmpdir: str, step: str, run_id: str | None) -> argparse.Namespace:
    return argparse.Namespace(
        tmpdir=tmpdir,
        step=step,
        run_id=run_id or "",
        log_dir="",
        budget_s=300,
        foreground=False,
        sentinel=[],
        owner_pid="",
        merge_result_env="",
        command=["true"],
    )


def test_build_spec_uses_persisted_larch_run_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """bgjob start resolves run_id from LARCH_RUN_ID in session-env.sh."""
    import os
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    monkeypatch.setenv("LARCH_CLAUDE_PID", str(os.getpid()))
    (tmp_path / "session-env.sh").write_text(
        "LARCH_RUN_ID=custom-run-999\n", encoding="utf-8"
    )

    spec = cli._build_spec(_ns(tmpdir=str(tmp_path), step="test-step", run_id=None))

    assert spec.run_id == "custom-run-999"


def test_build_spec_explicit_run_id_wins_over_session_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit --run-id overrides any persisted LARCH_RUN_ID."""
    import os
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    monkeypatch.setenv("LARCH_CLAUDE_PID", str(os.getpid()))
    (tmp_path / "session-env.sh").write_text(
        "LARCH_RUN_ID=persisted-run\n", encoding="utf-8"
    )

    spec = cli._build_spec(
        _ns(tmpdir=str(tmp_path), step="test-step", run_id="explicit-run")
    )

    assert spec.run_id == "explicit-run"


def test_build_spec_falls_back_to_tmpdir_hash_without_session_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without LARCH_RUN_ID in session env, the tmpdir-hash fallback is used."""
    import os
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    monkeypatch.setenv("LARCH_CLAUDE_PID", str(os.getpid()))

    spec = cli._build_spec(_ns(tmpdir=str(tmp_path), step="test-step", run_id=None))

    assert spec.run_id == model.default_run_id(
        tmpdir=tmp_path, clone_path=Path.cwd().resolve()
    )
