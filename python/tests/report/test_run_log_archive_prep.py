"""Completeness checks before a staged implement run is archived."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from larch.errors import ShipError
from larch.report import run_log_commit

if TYPE_CHECKING:
    import pytest


def _write_manifest(
    run_dir: Path,
    *,
    steps_ran: dict[str, object] | None = None,
) -> None:
    payload: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": run_dir.name,
        "steps_ran": steps_ran or {},
        "status": "partial",
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    _ = (run_dir / "manifest.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _write_terminal_artifacts(run_dir: Path) -> None:
    _ = (run_dir / "final-summary.md").write_text("# Final\n", encoding="utf-8")
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
    _ = (run_dir / "timing-report.json").write_text("{}", encoding="utf-8")
    _ = (run_dir / "execution-issues.ndjson").write_text("", encoding="utf-8")


def _prepare_tmp_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    run_id: str = "run-abc",
) -> str:
    def ignore_breadcrumbs(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        run_log_commit,
        "_publish_breadcrumbs_with_warning",
        ignore_breadcrumbs,
    )
    try:
        prepared = run_log_commit.prepare_run_for_archive(
            log_root=tmp_path / "larch-logs",
            skill="implement",
            run_id=run_id,
            repo_root=tmp_path / "repo",
        )
    except ShipError as exc:
        return str(exc)
    assert prepared.run_dir == tmp_path / "larch-logs" / "implement" / run_id
    return ""


def test_all_required_artifacts_are_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir, steps_ran={"step18": True})
    _write_terminal_artifacts(run_dir)
    _ = (run_dir / "session-transcript.jsonl").write_text("{}\n", encoding="utf-8")

    assert _prepare_tmp_run(tmp_path, monkeypatch) == ""


def test_recorded_transcript_omission_is_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir, steps_ran={"step18": True})
    _write_terminal_artifacts(run_dir)
    body = "- **Step 7a: session-transcript status=write-failed:** source file disappeared"
    _ = (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Warnings", "body": body}) + "\n",
        encoding="utf-8",
    )

    assert _prepare_tmp_run(tmp_path, monkeypatch) == ""


def test_silent_transcript_omission_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir, steps_ran={"step18": True})
    _write_terminal_artifacts(run_dir)

    assert "session-transcript.jsonl" in _prepare_tmp_run(tmp_path, monkeypatch)


def test_session_local_status_does_not_waive_a_durable_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir, steps_ran={"step18": True})
    _write_terminal_artifacts(run_dir)
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Warnings\n- **Step 7a: session-transcript status=write-failed:** source file disappeared\n",
        encoding="utf-8",
    )

    assert "session-transcript.jsonl" in _prepare_tmp_run(tmp_path, monkeypatch)


def test_code_review_tally_requires_full_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "code-review-tally.json").write_text("{}", encoding="utf-8")

    assert "review-findings-full.jsonl" in _prepare_tmp_run(tmp_path, monkeypatch)


def test_step7a_without_code_review_does_not_require_full_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _write_manifest(run_dir)
    _ = (run_dir / "token-report.json").write_text("{}", encoding="utf-8")
    _ = (run_dir / "session-transcript.jsonl").write_text("{}\n", encoding="utf-8")

    assert _prepare_tmp_run(tmp_path, monkeypatch) == ""


def test_missing_run_directory_fails_loudly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert "run-log staging directory is missing or unsafe" in _prepare_tmp_run(
        tmp_path,
        monkeypatch,
    )
