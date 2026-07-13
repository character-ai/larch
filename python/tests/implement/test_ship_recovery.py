"""Tests for operator-approved ship recovery verbs."""

# pyright: reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from larch.errors import ShipError
from larch.git.gh import PullRequest
from larch.implement import ship_recovery
from larch.report import final_report
from larch.state import stall_recovery


def _session(
    tmp_path: Path, *, run_id: str = "RUN-123", repo: str = "owner/repo"
) -> None:
    (tmp_path / "session-env.sh").write_text(
        f"LARCH_RUN_ID={run_id}\nREPO={repo}\nSTALL_TRACKING=true\nSTALL_STEP=8\n"
        "BAIL_REASON=architectural-assessment-unavailable\nIMPLEMENT_BAIL_REASON=operator-bail\n"
        "BAIL_NEEDS_USER_INPUT=true\nBAIL_FAILURE_DETAIL_LOG=failure.log\nFAILED_RUN_ID=77\nEXIT_CODE=4\n",
        encoding="utf-8",
    )


def _manifest(tmp_path: Path, *, run_id: str = "RUN-123") -> Path:
    path = tmp_path / "larch-logs" / "implement" / run_id / "manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"status":"in-progress","keep":"yes"}\n', encoding="utf-8")
    return path


def _merged_pr(number: int = 7049) -> PullRequest:
    return PullRequest(
        number,
        f"https://github.com/owner/repo/pull/{number}",
        "MERGED",
        "feat",
        "2026-07-12T00:00:00Z",
    )


def test_reconcile_manual_merge_clears_every_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _session(tmp_path)
    stale = (
        "REPO=owner/repo\nKEEP=value\nPHASE=stalled\nSTALL_TRACKING=true\nSTALL_STEP=8\n"
        "REPO_UNAVAILABLE=true\n"
        "BAIL_REASON=architectural-assessment-unavailable\nIMPLEMENT_BAIL_REASON=operator-bail\n"
        "BAIL_NEEDS_USER_INPUT=true\nBAIL_FAILURE_DETAIL_LOG=failure.log\nFAILED_RUN_ID=77\nEXIT_CODE=4\n"
    )
    (tmp_path / "ship-pr-state.sh").write_text(stale, encoding="utf-8")
    (tmp_path / "finalize-state.sh").write_text(stale, encoding="utf-8")
    manifest = _manifest(tmp_path)
    monkeypatch.setattr(
        ship_recovery.gh,
        "pr_view",
        lambda *_args, **_kwargs: _merged_pr(),
    )

    rc = ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7049"],
    )

    assert rc == 0
    assert (
        capsys.readouterr().out
        == "RECONCILE_STATUS=ok\nPR_NUMBER=7049\nMERGE_RESULT=merged\n"
    )
    for name in ("ship-pr-state.sh", "finalize-state.sh", "session-env.sh"):
        layer = ship_recovery._read_layer(tmpdir=tmp_path, name=name)  # pyright: ignore[reportPrivateUsage]
        assert layer["PHASE"] == "done"
        assert layer["REPO_UNAVAILABLE"] == "false"
        assert layer["STALL_TRACKING"] == "false"
        assert layer["BAIL_NEEDS_USER_INPUT"] == "false"
        assert layer["BAIL_REASON"] == ""
        assert layer.get("IMPLEMENT_BAIL_REASON", "") == ""
        assert layer["BAIL_FAILURE_DETAIL_LOG"] == layer["FAILED_RUN_ID"] == ""
        assert layer["EXIT_CODE"] == "0"
    assert (
        ship_recovery._read_layer(tmpdir=tmp_path, name="finalize-state.sh")["KEEP"]  # pyright: ignore[reportPrivateUsage]
        == "value"
    )
    assert (tmp_path / "post-merge-sentinel").read_text(
        encoding="utf-8"
    ) == "MERGE_RESULT=merged\n"
    assert json.loads(manifest.read_text(encoding="utf-8")) == {
        "status": "done",
        "keep": "yes",
        "pr_number": 7049,
    }


def test_reconcile_unmerged_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _session(tmp_path)
    before = (tmp_path / "session-env.sh").read_bytes()
    monkeypatch.setattr(
        ship_recovery.gh,
        "pr_view",
        lambda *_args, **_kwargs: PullRequest(
            7, "https://github.com/owner/repo/pull/7", "OPEN", "feat"
        ),
    )

    rc = ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7"],
    )

    assert rc == 1
    assert capsys.readouterr().out == "RECONCILE_STATUS=failed\nERROR=pr-not-merged\n"
    assert (tmp_path / "session-env.sh").read_bytes() == before
    assert not (tmp_path / "post-merge-sentinel").exists()


@pytest.mark.parametrize("state", ["OPEN", "CLOSED"])
def test_reconcile_open_or_closed_unmerged_pr_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    state: str,
) -> None:
    _session(tmp_path)
    before = (tmp_path / "session-env.sh").read_bytes()
    monkeypatch.setattr(
        ship_recovery.gh,
        "pr_view",
        lambda *_args, **_kwargs: PullRequest(
            7, "https://github.com/owner/repo/pull/7", state, "feat"
        ),
    )

    rc = ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7"],
    )

    assert rc == 1
    assert capsys.readouterr().out == "RECONCILE_STATUS=failed\nERROR=pr-not-merged\n"
    assert (tmp_path / "session-env.sh").read_bytes() == before


def test_reconcile_missing_pr_reports_probe_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _session(tmp_path)

    def missing(*_args: object, **_kwargs: object) -> PullRequest:
        raise ShipError("not found")

    monkeypatch.setattr(ship_recovery.gh, "pr_view", missing)

    rc = ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7"],
    )

    assert rc == 1
    assert capsys.readouterr().out == "RECONCILE_STATUS=failed\nERROR=pr-probe-failed\n"
    assert not (tmp_path / "post-merge-sentinel").exists()


def test_reconcile_repository_mismatch_refuses_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _session(tmp_path)
    called = False

    def unexpected_probe(*_args: object, **_kwargs: object) -> PullRequest:
        nonlocal called
        called = True
        return _merged_pr()

    monkeypatch.setattr(ship_recovery.gh, "pr_view", unexpected_probe)

    rc = ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7049", "--repo", "other/repo"],
    )

    assert rc == 1
    assert (
        capsys.readouterr().out
        == "RECONCILE_STATUS=failed\nERROR=repository-mismatch\n"
    )
    assert called is False


def test_reconcile_rejects_merged_payload_for_different_requested_pr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _session(tmp_path)
    _manifest(tmp_path)
    monkeypatch.setattr(
        ship_recovery.gh, "pr_view", lambda *_args, **_kwargs: _merged_pr(number=7050)
    )

    rc = ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7049"],
    )

    assert rc == 1
    assert capsys.readouterr().out == "RECONCILE_STATUS=failed\nERROR=pr-identity-mismatch\n"
    assert not (tmp_path / "post-merge-sentinel").exists()


def test_reconcile_rejects_merged_payload_for_different_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _session(tmp_path)
    _manifest(tmp_path)
    monkeypatch.setattr(
        ship_recovery.gh,
        "pr_view",
        lambda *_args, **_kwargs: PullRequest(
            7049,
            "https://github.com/other/repo/pull/7049",
            "MERGED",
            "feat",
            "2026-07-12T00:00:00Z",
        ),
    )

    rc = ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7049"],
    )

    assert rc == 1
    assert capsys.readouterr().out == "RECONCILE_STATUS=failed\nERROR=pr-identity-mismatch\n"


def test_reconcile_rejects_mismatched_persisted_run_identity_before_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _session(tmp_path)
    (tmp_path / "ship-pr-state.sh").write_text("RUN_ID=OTHER\nREPO=owner/repo\n", encoding="utf-8")
    called = False

    def unexpected_probe(*_args: object, **_kwargs: object) -> PullRequest:
        nonlocal called
        called = True
        return _merged_pr()

    monkeypatch.setattr(ship_recovery.gh, "pr_view", unexpected_probe)

    rc = ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7049"],
    )

    assert rc == 1
    assert capsys.readouterr().out == "RECONCILE_STATUS=failed\nERROR=run-id-mismatch\n"
    assert called is False


def test_reconcile_rejects_mismatched_manifest_run_identity_before_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _session(tmp_path)
    _manifest(tmp_path).write_text('{"run_id":"OTHER"}\n', encoding="utf-8")
    monkeypatch.setattr(
        ship_recovery.gh,
        "pr_view",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("probe must not run")),
    )

    rc = ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7049"],
    )

    assert rc == 1
    assert capsys.readouterr().out == "RECONCILE_STATUS=failed\nERROR=manifest-run-mismatch\n"


def test_reconcile_refuses_symlinked_ship_state_before_writing(tmp_path: Path) -> None:
    _session(tmp_path)
    target = tmp_path / "outside-state.sh"
    target.write_text("KEEP=outside\n", encoding="utf-8")
    (tmp_path / "ship-pr-state.sh").symlink_to(target)

    rc = ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7049"],
    )

    assert rc == 1
    assert target.read_text(encoding="utf-8") == "KEEP=outside\n"


def test_reconcile_rerun_converges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _session(tmp_path)
    _manifest(tmp_path)
    monkeypatch.setattr(
        ship_recovery.gh, "pr_view", lambda *_args, **_kwargs: _merged_pr()
    )

    for _ in range(2):
        assert (
            ship_recovery.reconcile_manual_merge_main(
                ["--implement-tmpdir", str(tmp_path), "--pr", "7049"],
            )
            == 0
        )

    assert capsys.readouterr().out.count("RECONCILE_STATUS=ok\n") == 2


def test_reconcile_fails_post_read_when_partial_clear_leaves_overlay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _session(tmp_path)
    _manifest(tmp_path)
    monkeypatch.setattr(
        ship_recovery.gh, "pr_view", lambda *_args, **_kwargs: _merged_pr()
    )
    original = ship_recovery._write_terminal_layer  # pyright: ignore[reportPrivateUsage]

    def leave_overlay(*, tmpdir: Path, name: str, updates: dict[str, str]) -> None:
        original(tmpdir=tmpdir, name=name, updates=updates)
        if name == "session-env.sh":
            values = ship_recovery._read_layer(tmpdir=tmpdir, name=name)  # pyright: ignore[reportPrivateUsage]
            values["BAIL_REASON"] = "still-bailed"
            (tmpdir / name).write_text(
                ship_recovery.larch_io.format_kvs(values, sort_keys=True),
                encoding="utf-8",
            )

    monkeypatch.setattr(ship_recovery, "_write_terminal_layer", leave_overlay)

    rc = ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7049"],
    )

    assert rc == 1
    assert (
        capsys.readouterr().out
        == "RECONCILE_STATUS=failed\nERROR=bail-overlay-remains\n"
    )


def test_bd267d84_operator_waiver_manual_merge_replay_writes_merged_final_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _session(tmp_path)
    manifest = _manifest(tmp_path)
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=RUN-123\n", encoding="utf-8")
    (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")
    monkeypatch.setattr(
        ship_recovery.gh, "pr_view", lambda *_args, **_kwargs: _merged_pr()
    )

    assert ship_recovery.reconcile_manual_merge_main(
        ["--implement-tmpdir", str(tmp_path), "--pr", "7049"]
    ) == 0
    values = stall_recovery.normalized_outcome_values(
        argparse.Namespace(
            implement_tmpdir=str(tmp_path), in_memory_stall_tracking="false"
        )
    )
    rc, _url, err = final_report.write_final_report(tmp_path, comment_only=True)

    assert values["IMPLEMENT_NORMALIZED_OUTCOME"] == "merged"
    assert json.loads(manifest.read_text(encoding="utf-8"))["status"] == "done"
    assert json.loads(manifest.read_text(encoding="utf-8"))["pr_number"] == 7049
    assert rc == 0
    assert err == ""
    assert "merged" in (tmp_path / "summary-final.md").read_text(encoding="utf-8")
