"""Tests for run_logs.py."""

from __future__ import annotations

import contextlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from larch.core import architectural_guidelines
from larch.core import config
from larch import io as larch_io
from larch.report import final_report
from larch.report import run_log_batch, run_log_commit, run_log_flush, run_log_manifest, run_logs
from larch.report.run_log_batch import _rebase_under_tmpdir, _write_batch, _append_batch  # pyright: ignore[reportPrivateUsage]
from larch.report import timing
from larch.report import tokens
from larch.errors import ShipError
from larch.core.proc import CommandResult

from test_support import RecordingRunner as _RecordingRunner, RunCall, make_run_context

if TYPE_CHECKING:
    from larch.core.run_context import RunContext


@dataclass
class RecordingRunner(_RecordingRunner):
    """Shared queue runner that also tallies ``git commit -m`` calls."""

    git_commits: int = 0

    def __post_init__(self) -> None:
        self.on_call = self._count_git_commits

    def _count_git_commits(self, call: RunCall) -> None:
        if call.argv[:3] == ("git", "commit", "-m"):
            self.git_commits += 1


def _ctx(tmp_path: Path, state_file: str | None = None) -> RunContext:
    return make_run_context(
        run_id="run-abc",
        tmpdir=str(tmp_path),
        manifest_path=str(tmp_path / "manifest.json"),
        state_file=state_file,
    )


def _stub_rust_manifest_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep Python-only checkpoint tests isolated from the Rust bootstrap."""
    original_run = final_report.subprocess.run

    def run_manifest_in_process(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "run-log" not in argv or "manifest" not in argv:
            return original_run(argv, **kwargs)  # type: ignore[arg-type]
        root = Path(argv[argv.index("--log-root") + 1])
        skill = argv[argv.index("--skill") + 1]
        run_id = argv[argv.index("--run-id") + 1]
        updates: dict[str, object] = {}
        for index, value in enumerate(argv):
            if value != "--field":
                continue
            key, raw = argv[index + 1].split("=", 1)
            if raw == "true":
                updates[key] = True
            elif raw == "false":
                updates[key] = False
            elif raw == "null":
                updates[key] = None
            elif raw.lstrip("-").isdigit():
                updates[key] = int(raw)
            else:
                updates[key] = raw
        run_log_manifest._update_manifest_v2(  # pyright: ignore[reportPrivateUsage]  # checkpoint unit-test boundary double; Rust CLI parity is covered separately.
            path=root / skill / run_id / "manifest.json",
            updates=updates,
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(final_report.subprocess, "run", run_manifest_in_process)


def test_validate_run_id_slug() -> None:
    assert run_log_batch.validate_run_id_slug("run-1")
    assert run_log_batch.validate_run_id_slug("-abc123")
    assert not run_log_batch.validate_run_id_slug("../evil")
    assert not run_log_batch.validate_run_id_slug("a..b")
    assert not run_log_batch.validate_run_id_slug("bad/slash")
    assert not run_log_batch.validate_run_id_slug(r"bad\slash")


def test_run_dir_rejects_invalid_run_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid run-id"):
        run_log_batch._run_dir(log_root=tmp_path / "larch-logs", skill="implement", run_id="../evil")  # pyright: ignore[reportPrivateUsage, reportUnusedCallResult]


def _guideline_outcome_payload(
    *,
    outcome: str = "pinned",
    reason: str = "note-pinned",
    assessment_kind: str | None = None,
) -> dict[str, str]:
    if assessment_kind is None:
        if outcome == "clean":
            assessment_kind = "clean" if reason == "clean-note" else ""
        elif outcome == "pinned":
            assessment_kind = "deviation"
        else:
            assessment_kind = ""
    return {
        "schema_version": "1",
        "phase": "implement",
        "step": "8",
        "outcome": outcome,
        "reason": reason,
        "detail": "",
        "guidelines_status": "present",
        "head_sha": "abc123",
        "base_ref": "origin/main",
        "assessment_kind": assessment_kind,
    }


def test_write_batch_uses_cache_scratch_when_log_root_is_under_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    cache = tmp_path / "cache"
    payload = tmp_path / "architectural-guideline-outcome.json"
    _ = payload.write_text(json.dumps(_guideline_outcome_payload()), encoding="utf-8")

    def fake_cache_scratch() -> Path:
        cache.mkdir(parents=True, exist_ok=True)
        return cache

    monkeypatch.setattr(run_log_batch, "_REPO_ROOT", repo)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(run_log_batch, "_larch_sessions_scratch_dir", fake_cache_scratch)  # pyright: ignore[reportPrivateUsage]

    assert run_log_batch._scratch_dir_for_log_root(repo / "nested" / "larch-logs") == cache  # pyright: ignore[reportPrivateUsage]

    path, written, unchanged = run_log_batch._write_batch(  # pyright: ignore[reportPrivateUsage]
        log_root=repo / "nested" / "larch-logs",
        skill="implement",
        run_id="run-abc",
        batch=config.RUN_LOG_BATCH_GUIDELINE_SHIP_OUTCOME,
        input_file=str(payload),
    )

    assert written is True
    assert unchanged is False
    assert path.is_file()
    assert cache.is_dir()


def test_capture_transcript_scratch_dir_uses_cache_when_log_root_is_under_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    cache = tmp_path / "cache"
    repo.mkdir()

    def fake_cache_scratch() -> Path:
        cache.mkdir(parents=True, exist_ok=True)
        return cache

    monkeypatch.setattr(run_log_batch, "_REPO_ROOT", repo)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(run_log_flush, "_larch_sessions_scratch_dir", fake_cache_scratch)  # pyright: ignore[reportPrivateUsage]

    assert (
        run_log_flush._capture_transcript_scratch_dir(  # pyright: ignore[reportPrivateUsage]
            tmpdir="",
            log_root=repo / "nested" / "larch-logs",
        )
        == cache
    )


def test_capture_transcript_scratch_dir_uses_active_checkout_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "consumer-repo"
    repo.mkdir()
    cache = tmp_path / "cache"

    def fake_cache_scratch() -> Path:
        cache.mkdir(parents=True, exist_ok=True)
        return cache

    def fake_git_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout=f"{repo}\n", stderr="")

    monkeypatch.setattr(run_log_batch.proc, "run", fake_git_run)  # type: ignore[attr-defined]
    monkeypatch.setattr(run_log_batch, "_REPO_ROOT", tmp_path / "plugin-root")  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(run_log_batch, "_larch_sessions_scratch_dir", fake_cache_scratch)  # pyright: ignore[reportPrivateUsage]

    assert run_log_batch._path_is_repo_related(repo / "nested")  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._scratch_dir_for_log_root(repo / "nested" / "larch-logs") == cache  # pyright: ignore[reportPrivateUsage]


def test_guideline_outcome_batch_registry_and_sanitizer(tmp_path: Path) -> None:
    payload = tmp_path / "architectural-guideline-outcome.json"
    _ = payload.write_text(json.dumps(_guideline_outcome_payload()), encoding="utf-8")

    path, written, unchanged = _write_batch(
        log_root=tmp_path / "larch-logs",
        skill="implement",
        run_id="run-abc",
        batch=config.RUN_LOG_BATCH_GUIDELINE_SHIP_OUTCOME,
        input_file=str(payload),
    )

    assert written is True
    assert unchanged is False
    assert path.name == "architectural-guideline-outcome.json"
    assert json.loads(path.read_text(encoding="utf-8"))["outcome"] == "pinned"

    bad = tmp_path / "bad.json"
    _ = bad.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="requires a JSON object"):
        _ = _write_batch(
            log_root=tmp_path / "larch-logs",
            skill="implement",
            run_id="run-abc",
            batch=config.RUN_LOG_BATCH_GUIDELINE_SHIP_OUTCOME,
            input_file=str(bad),
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({**_guideline_outcome_payload(), "phase": "design"}, "phase must be implement"),
        ({**_guideline_outcome_payload(), "step": "7"}, "step must be 8"),
        ({**_guideline_outcome_payload(), "base_ref": ""}, "base_ref is empty"),
        (
            {**_guideline_outcome_payload(), "outcome": "dropped", "reason": "note-pinned"},
            "fields are inconsistent for dropped guidelines",
        ),
    ],
)
def test_guideline_outcome_batch_rejects_schema_mismatches(
    tmp_path: Path,
    payload: dict[str, str],
    message: str,
) -> None:
    path = tmp_path / "architectural-guideline-outcome.json"
    _ = path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        _ = _write_batch(
            log_root=tmp_path / "larch-logs",
            skill="implement",
            run_id="run-abc",
            batch=config.RUN_LOG_BATCH_GUIDELINE_SHIP_OUTCOME,
            input_file=str(path),
        )


def test_guideline_outcome_sidecar_stages_pre_commit(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    sidecar = architectural_guidelines.guideline_ship_outcome_path(tmp_path)
    _ = sidecar.write_text(json.dumps(_guideline_outcome_payload()), encoding="utf-8")

    run_log_flush._stage_guideline_ship_outcome(  # pyright: ignore[reportPrivateUsage]
        ctx=ctx,
        log_root=tmp_path / "larch-logs",
    )

    staged = tmp_path / "larch-logs" / "implement" / "run-abc" / "architectural-guideline-outcome.json"
    assert json.loads(staged.read_text(encoding="utf-8"))["reason"] == "note-pinned"


def test_atomic_write_uses_nofollow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: dict[str, Any] = {}

    def fake_atomic_write(_path: Path, _content: str, **kwargs: Any) -> None:
        calls.update(kwargs)

    monkeypatch.setattr(larch_io, "atomic_write", fake_atomic_write)
    run_log_batch._atomic_write(path=tmp_path / "manifest.json", content="{}")  # pyright: ignore[reportPrivateUsage]
    assert calls["prefix"] == ".manifest-"
    assert calls["nofollow"] is True


def test_refresh_logs_checkpoint_state_file_less_does_not_require_repo_cwd(tmp_path: Path) -> None:
    runner = RecordingRunner()
    skip = run_log_flush.refresh_logs_checkpoint(runner=runner, ctx=_ctx(tmp_path), cwd=None)
    assert not skip.skipped


def test_refresh_logs_checkpoint_state_file_less_stages_without_git_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner = RecordingRunner()

    def fake_commit(
        *,
        log_root: Path,
        skill: str = "implement",
        run_id: str = "",
        cwd: str | None = None,
        pre_scrub_violations: int = 0,
    ) -> CommandResult:
        _ = log_root, skill, run_id, pre_scrub_violations
        assert cwd == str(tmp_path)
        runner.git_commits += 1
        return CommandResult(("git", "commit"), 0, "", "", 0.01)

    monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit, raising=False)  # type: ignore[arg-type]
    skip = run_log_flush.refresh_logs_checkpoint(runner=runner, ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert not skip.skipped
    assert runner.git_commits == 0


def test_refresh_logs_checkpoint_skips_post_merge(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("MERGE_RESULT=merged\nRUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner()
    skip = run_log_flush.refresh_logs_checkpoint(runner=runner, ctx=_ctx(tmp_path, str(state)))
    assert skip.reason == config.REFRESH_SKIP_POST_MERGE


def test_refresh_postmerge_snapshot_no_git_commit(tmp_path: Path) -> None:
    runner = RecordingRunner()
    ctx = _ctx(tmp_path).with_(pr_number=17)
    _ = run_log_manifest.init_run(ctx)
    _ = run_log_flush.refresh_postmerge_snapshot(ctx, merge_result=config.MERGE_RESULT_MERGED)
    assert runner.git_commits == 0
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == config.MANIFEST_STATUS_DONE
    assert manifest["pr_number"] == 17
    assert "pr_number" not in manifest["steps_ran"]


def test_refresh_postmerge_snapshot_does_not_write_done_manifest_before_reports(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ctx = _ctx(tmp_path).with_(pr_number=17)
    _ = run_log_manifest.init_run(ctx)

    def fail_report(*_a: object, **_k: object) -> None:
        raise ShipError("write-final-report failed")

    monkeypatch.setattr(run_log_flush, "_write_final_report", fail_report)
    monkeypatch.setattr(run_log_flush, "_write_final_report", fail_report)  # type: ignore[arg-type]
    skip = run_log_flush.refresh_postmerge_snapshot(
        ctx, merge_result=config.MERGE_RESULT_MERGED, runner=RecordingRunner()
    )
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert skip.skipped is True
    assert manifest["status"] == config.MANIFEST_STATUS_PARTIAL
    assert "pr_number" not in manifest


def test_refresh_postmerge_snapshot_manifest_write_oserror_returns_recovery_skip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ctx = _ctx(tmp_path)
    _ = run_log_manifest.init_run(ctx)

    def boom(*_a: object, **_k: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(run_log_manifest, "_write_manifest", boom)
    monkeypatch.setattr(run_log_flush, "_write_manifest", boom)  # type: ignore[arg-type]
    skip = run_log_flush.refresh_postmerge_snapshot(ctx, merge_result=config.MERGE_RESULT_MERGED)
    assert skip.skipped is True
    assert skip.reason == run_log_manifest.REFRESH_SKIP_RECOVERY_FAILED


def test_refresh_postmerge_snapshot_leaves_partial_on_failed_merge(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _ = run_log_manifest.init_run(ctx)
    _ = run_log_flush.refresh_postmerge_snapshot(ctx, merge_result=config.MERGE_RESULT_ERROR)
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == config.MANIFEST_STATUS_PARTIAL


def test_load_or_recover_manifest_from_log_dir(tmp_path: Path) -> None:
    log_dir = tmp_path / "larch-logs" / "implement" / "recovered-run"
    log_dir.mkdir(parents=True)
    ctx = _ctx(tmp_path).with_(run_id="../invalid")
    manifest = run_log_manifest.load_or_recover_manifest(ctx)
    assert manifest.run_id == ""


def test_load_or_recover_manifest_absent_run_dir_tags_partial(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=lost-run\nISSUE_NUMBER=123\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    recovered = run_log_manifest.load_or_recover_manifest_checked(ctx)
    assert recovered.recovery_ok
    assert recovered.manifest.status == config.MANIFEST_STATUS_PARTIAL
    assert recovered.manifest.extra == {"recovery_reason": "manifest_lost_mid_run"}
    assert recovered.manifest.reserved["issue_number"] == 123
    manifest_path = tmp_path / "larch-logs" / "implement" / "lost-run" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    assert manifest["run_id"] == "lost-run"
    assert manifest["issue_number"] == 123
    assert manifest["steps_ran"] == {}
    assert manifest["issue_number"] == 123


def test_effective_run_id_prefers_state_file(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=state-run\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    assert run_log_manifest.effective_run_id(ctx) == "state-run"


def test_effective_run_id_rejects_unvalidated_ctx_run_id(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path).with_(run_id="../../../outside")
    assert run_log_manifest.effective_run_id(ctx) == ""


def test_read_resume_counters_absent_and_corrupt_values(tmp_path: Path) -> None:
    assert run_log_manifest.read_resume_counters(None) == run_log_manifest.ResumeCounters(0, 0, 0, 0)
    state = tmp_path / "state.env"
    _ = state.write_text(
        "ITERATION=10\nREBASE_COUNT=bad\nFIX_ATTEMPTS=\nTRANSIENT_RETRIES=3\n",
        encoding="utf-8",
    )

    assert run_log_manifest.read_resume_counters(str(state)) == run_log_manifest.ResumeCounters(10, 0, 0, 3)


def test_read_durable_flags_state_first_and_forked_target_implies_forked(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path).with_(repo_unavailable=False, forked=False, forked_target=False, merge=True, draft=False)
    assert run_log_manifest.read_durable_flags(state_file=None, ctx=ctx) == run_log_manifest.DurableFlags(
        repo_unavailable=False,
        forked_target=False,
        forked=False,
        merge=True,
        draft=False,
    )
    state = tmp_path / "state.env"
    _ = state.write_text(
        "REPO_UNAVAILABLE=true\nFORKED_TARGET=true\nMERGE=false\nDRAFT=maybe\n",
        encoding="utf-8",
    )

    assert run_log_manifest.read_durable_flags(state_file=str(state), ctx=ctx) == run_log_manifest.DurableFlags(
        repo_unavailable=True,
        forked_target=True,
        forked=True,
        merge=False,
        draft=False,
    )


def test_read_durable_flags_persisted_false_overrides_stale_ctx_forked(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path).with_(forked=True, forked_target=True)
    state = tmp_path / "state.env"
    _ = state.write_text("FORKED_TARGET=false\n", encoding="utf-8")

    assert run_log_manifest.read_durable_flags(state_file=str(state), ctx=ctx).forked is False


def test_parse_pr_number_state_first_and_ctx_fallback(tmp_path: Path) -> None:
    assert run_log_manifest.parse_pr_number(state_file=None, ctx_pr_number=7) is None
    state = tmp_path / "state.env"
    _ = state.write_text("PR_NUMBER=\n", encoding="utf-8")
    assert run_log_manifest.parse_pr_number(state_file=str(state), ctx_pr_number="8") is None
    _ = state.write_text("PR_NUMBER=0\n", encoding="utf-8")
    assert run_log_manifest.parse_pr_number(state_file=str(state), ctx_pr_number="8") is None
    _ = state.write_text("PR_NUMBER=9\n", encoding="utf-8")
    assert run_log_manifest.parse_pr_number(state_file=str(state), ctx_pr_number=None) == 9


def test_manifest_status_read_only_uses_effective_run_id_path(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=state-run\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state)).with_(run_id="ctx-run")
    assert run_log_manifest.manifest_status(ctx) == ""
    manifest = tmp_path / "larch-logs" / "implement" / "state-run" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text('{"status":"done"}', encoding="utf-8")
    assert run_log_manifest.manifest_status(ctx) == "done"
    manifest = tmp_path / "larch-logs" / "implement" / "ctx-run" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text('{"status":"done"}', encoding="utf-8")
    assert run_log_manifest.manifest_status(ctx) == "done"
    _ = (tmp_path / "larch-logs" / "implement" / "state-run" / "manifest.json").write_text("{", encoding="utf-8")
    assert run_log_manifest.manifest_status(ctx) == ""


def test_execution_issues_batch_from_markdown(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Tool Failures\nline one\n",
        encoding="utf-8",
    )
    _ = (tmp_path / ".execution-issues-step7a-reached").write_text("", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    batch_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    batch_dir.mkdir(parents=True)
    run_log_flush._render_execution_issues_batch(  # pyright: ignore[reportPrivateUsage]
        ctx=ctx,
        batch_dir=batch_dir,
        step_label="pre-push",
        source_label="test",
    )
    batch = batch_dir / "execution-issues.ndjson"
    assert batch.is_file()
    text = batch.read_text(encoding="utf-8")
    assert "Tool Failures" in text
    assert "-----BEGIN" not in text


def test_execution_issues_batch_redacts_pem(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    secret = "ghp_" + "abcdefghijklmnopqrstuvwxyz1234567890ABCD"
    _ = (tmp_path / "execution-issues.md").write_text(
        f"### Tool Failures\n{secret}\n",
        encoding="utf-8",
    )
    _ = (tmp_path / ".execution-issues-step7a-reached").write_text("", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    batch_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    batch_dir.mkdir(parents=True)
    run_log_flush._render_execution_issues_batch(  # pyright: ignore[reportPrivateUsage]
        ctx=ctx,
        batch_dir=batch_dir,
        step_label="pre-push",
        source_label="test",
    )
    batch = batch_dir / "execution-issues.ndjson"
    assert batch.is_file()
    assert secret not in batch.read_text(encoding="utf-8")


def test_execution_issues_batch_dedupes_repeated_warning_events(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    issue_log = tmp_path / "execution-issues.md"
    _ = issue_log.write_text("### Warnings\n- **Step 7a**: transient warning\n", encoding="utf-8")
    _ = (tmp_path / ".execution-issues-step7a-reached").write_text("", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    batch_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    batch_dir.mkdir(parents=True)

    for _index in range(2):
        run_log_flush._render_execution_issues_batch(  # pyright: ignore[reportPrivateUsage]
            ctx=ctx,
            batch_dir=batch_dir,
            step_label="pre-push",
            source_label="test",
        )
    _ = issue_log.write_text(
        "### Warnings\n- **Step 7a**: transient warning\n- **Step 8**: new warning\n",
        encoding="utf-8",
    )
    run_log_flush._render_execution_issues_batch(  # pyright: ignore[reportPrivateUsage]
        ctx=ctx,
        batch_dir=batch_dir,
        step_label="pre-push",
        source_label="test",
    )

    rows = [
        json.loads(line)
        for line in (batch_dir / "execution-issues.ndjson").read_text(encoding="utf-8").splitlines()
    ]
    assert [row["body"].strip() for row in rows] == [
        "- **Step 7a**: transient warning",
        "- **Step 8**: new warning",
    ]


def test_load_or_recover_manifest_invalid_json(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "execution-issues.ndjson").write_text("{}\n", encoding="utf-8")
    _ = (run_dir / "manifest.json").write_text("{not-json", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    manifest = run_log_manifest.load_or_recover_manifest(ctx)
    assert manifest.run_id == "run-abc"
    assert manifest.steps_ran.get("recovered") is True


def test_token_batch_refresh_json_not_written_to_batch_dir(tmp_path: Path) -> None:
    # Refresh JSON files are volatile in-loop snapshots and must NOT be copied
    # into the committed run tree (issue #3708 Phase 1).  This test verifies
    # the PEM-containing edge case: even with bad content in the refresh file,
    # nothing is written to batch_dir under the refresh basename.
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    pem = "-----BEGIN RSA " + "PRIVATE KEY-----\nMIIB\n"
    _ = (tmp_path / "token-report-refresh.json").write_text(pem, encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    run_log_flush._render_token_timing_batches(  # pyright: ignore[reportPrivateUsage]
        ctx=ctx,
        log_root=tmp_path / "larch-logs",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    assert not (run_dir / "token-report-refresh.json").exists()


def test_path_under_repo_rejects_traversal(tmp_path: Path) -> None:
    assert not run_logs.path_under_repo(repo_root=tmp_path, rel_path="../outside")
    assert run_logs.path_under_repo(repo_root=tmp_path, rel_path="docs/plan.md")


@pytest.mark.parametrize("merge_result", ["merged", "admin_merged", "already_merged"])
def test_refresh_logs_checkpoint_skips_post_merge_matrix(tmp_path: Path, merge_result: str) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text(f"MERGE_RESULT={merge_result}\nRUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner()
    skip = run_log_flush.refresh_logs_checkpoint(runner=runner, ctx=_ctx(tmp_path, str(state)))
    assert skip.reason == config.REFRESH_SKIP_POST_MERGE


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        ("RUN_ID=run-abc\nNO_LOGS_COMMIT=true\n", config.REFRESH_SKIP_NO_LOGS_COMMIT),
        ("", config.REFRESH_SKIP_NO_RUN_ID),
        ("RUN_ID=../bad\n", config.REFRESH_SKIP_INVALID_RUN_ID),
    ],
)
def test_refresh_logs_checkpoint_skip_reason_tokens(tmp_path: Path, line: str, reason: str) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text(line, encoding="utf-8")
    runner = RecordingRunner()
    skip = run_log_flush.refresh_logs_checkpoint(runner=runner, ctx=_ctx(tmp_path, str(state)))
    assert skip.skipped
    assert skip.reason == reason


def test_is_placeholder_run_id_matches_non_unique_labels() -> None:
    assert run_log_batch.is_placeholder_run_id("run-1")
    assert run_log_batch.is_placeholder_run_id("run-2")
    assert run_log_batch.is_placeholder_run_id("run-10")
    # Unique run-ids (UUIDs, tmpdir basenames, the "run-abc" test label) are kept.
    assert not run_log_batch.is_placeholder_run_id("run-abc")
    assert not run_log_batch.is_placeholder_run_id("9F1C2D3E-1234-5678-9ABC-DEF012345678")
    assert not run_log_batch.is_placeholder_run_id("larch-implement-AbC123")
    assert not run_log_batch.is_placeholder_run_id("run")
    assert not run_log_batch.is_placeholder_run_id("")


def test_refresh_only_sidecars_not_written_to_batch_dir(tmp_path: Path) -> None:
    # Refresh JSON files must NOT be written to batch_dir (issue #3708 Phase 1).
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "token-report-refresh.json").write_text("{}", encoding="utf-8")
    _ = (tmp_path / "timing-report-refresh.json").write_text("{}", encoding="utf-8")
    run_log_flush._render_token_timing_batches(  # pyright: ignore[reportPrivateUsage]
        ctx=_ctx(tmp_path, str(state)),
        log_root=tmp_path / "larch-logs",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    assert not (run_dir / "token-report-refresh.json").exists()
    assert not (run_dir / "timing-report-refresh.json").exists()


def test_refresh_logs_checkpoint_happy_path_stages_without_git_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_log_manifest.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _ = (run_dir / "token-report-refresh.json").write_text("{}", encoding="utf-8")
    commits: list[bool] = []

    def fake_commit(
        *,
        log_root: object,
        skill: object = None,
        run_id: object = None,
        cwd: str | None = None,
        pre_scrub_violations: int = 0,
    ) -> CommandResult:
        _ = log_root, skill, run_id, pre_scrub_violations, cwd
        commits.append(True)
        return CommandResult(
            ("git", "commit"),
            0,
            "a" * 40 + "\n",
            "",
            0.0,
        )

    def noop_write_final_report(**_kw: object) -> None:
        pass

    def noop_capture(**_kw: object) -> None:
        pass

    monkeypatch.setattr(run_log_flush, "_write_final_report", noop_write_final_report)
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop_capture)
    monkeypatch.setattr(run_log_flush, "_write_final_report", noop_write_final_report)
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop_capture)
    monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit, raising=False)  # type: ignore[arg-type]
    runner = RecordingRunner()
    skip = run_log_flush.refresh_logs_checkpoint(runner=runner, ctx=ctx, cwd=str(tmp_path / "repo"))
    assert not skip.skipped
    assert not commits
    manifest = json.loads(
        (tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json").read_text(
            encoding="utf-8",
        ),
    )
    assert "step9a1" not in manifest["steps_ran"]


def test_refresh_logs_checkpoint_update_manifest_failure_returns_recovery_skip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_log_manifest.init_run(ctx)

    def fail_update(*_a: object, **_k: object) -> run_log_manifest.Manifest:
        raise ShipError("manifest recovery failed")

    monkeypatch.setattr(run_log_manifest, "update_manifest", fail_update)
    monkeypatch.setattr(run_log_flush, "update_manifest", fail_update)  # type: ignore[arg-type]
    skip = run_log_flush.refresh_logs_checkpoint(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))
    assert skip.skipped is True
    assert skip.reason == run_log_manifest.REFRESH_SKIP_RECOVERY_FAILED


def test_refresh_logs_checkpoint_does_not_call_git_commit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_log_manifest.init_run(ctx)

    def fail_commit(*_a: object, **_k: object) -> CommandResult:
        raise ShipError("commit failed")

    def noop(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(run_log_flush, "_commit_run", fail_commit, raising=False)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_write_final_report", noop)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)  # type: ignore[arg-type]
    skip = run_log_flush.refresh_logs_checkpoint(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))
    assert skip.skipped is False


@pytest.mark.parametrize(
    ("forked", "state_text", "finalize_text", "flags_text", "files", "expected"),
    [
        (True, "RUN_ID=run-abc\n", "", "", ("run-statistics.md",), True),
        (False, "RUN_ID=run-abc\nFORKED_TARGET=true\n", "", "", ("run-statistics.md",), True),
        (
            False,
            "RUN_ID=run-abc\n",
            "DESIGN_ONLY_DONE=true\n",
            "NO_ISSUES=true\n",
            (),
            False,
        ),
        (False, "RUN_ID=run-abc\n", "", "", ("oos-issues.ndjson",), False),
        (False, "RUN_ID=run-abc\n", "", "", ("run-statistics.md",), True),
        (False, "RUN_ID=run-abc\n", "", "", ("oos-issues.ndjson", "run-statistics.md"), True),
        (False, "RUN_ID=run-abc\n", "", "", (), None),
    ],
)
def test_step9a1_heuristic_matrix(
    tmp_path: Path,
    forked: bool,
    state_text: str,
    finalize_text: str,
    flags_text: str,
    files: tuple[str, ...],
    expected: bool | None,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text(state_text, encoding="utf-8")
    if finalize_text:
        _ = (tmp_path / "finalize-state.sh").write_text(finalize_text, encoding="utf-8")
    if flags_text:
        _ = (tmp_path / "run-flags.sh").write_text(flags_text, encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    for filename in files:
        if filename == "run-statistics.md":
            _ = (run_dir / filename).write_text("Run run-abc: 0 OOS issue(s) filed.\n", encoding="utf-8")
        elif filename == "oos-issues.ndjson":
            _ = (run_dir / filename).write_text('{"phase":"implement"}\n', encoding="utf-8")
        else:
            _ = (run_dir / filename).write_text("x\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state)).with_(forked=forked)
    assert run_log_flush._step9a1_heuristic(ctx) is expected  # pyright: ignore[reportPrivateUsage]


def test_step9a1_heuristic_manifest_explicit_values(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "oos-issues.ndjson").write_text('{"phase":"implement"}\n', encoding="utf-8")
    _ = (run_dir / "manifest.json").write_text('{"steps_ran":{"step9a1":false}}\n', encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    assert run_log_flush._step9a1_heuristic(ctx) is False  # pyright: ignore[reportPrivateUsage]
    _ = (run_dir / "manifest.json").write_text('{"steps_ran":{"step9a1":true}}\n', encoding="utf-8")
    assert run_log_flush._step9a1_heuristic(ctx) is False  # pyright: ignore[reportPrivateUsage]


def test_refresh_logs_checkpoint_downgrades_stale_step9a1_true_with_ndjson_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_log_manifest.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _ = (run_dir / "oos-issues.ndjson").write_text('{"phase":"implement"}\n', encoding="utf-8")
    manifest_path = run_dir / "manifest.json"
    _ = manifest_path.write_text(
        json.dumps({"status": "partial", "version": "1", "run_id": "run-abc", "steps_ran": {"step9a1": True}}),
        encoding="utf-8",
    )

    def noop(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(run_log_flush, "_write_final_report", noop)
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)

    def noop_commit(*_args: object, **_kwargs: object) -> CommandResult:
        return CommandResult(("",), 0, "", "", 0.0)

    monkeypatch.setattr(run_log_flush, "_write_final_report", noop)
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)
    monkeypatch.setattr(run_log_flush, "_commit_run", noop_commit, raising=False)  # type: ignore[arg-type]
    skip = run_log_flush.refresh_logs_checkpoint(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))
    assert not skip.skipped
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["steps_ran"]["step9a1"] is False


def test_refresh_logs_checkpoint_multi_flush_shipping_then_pr_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")
    _ = (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text(
        "RUN_ID=run-abc\nSTALL_TRACKING=false\nMERGE=true\nPR_NUMBER=\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, str(state))
    _ = run_log_manifest.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _stub_rust_manifest_command(monkeypatch)

    monkeypatch.setattr(final_report, "_final_report_token_fields", lambda **_k: {"cost_unavailable": True})  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", lambda *_a, **_k: None)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", lambda *_a, **_k: None)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", lambda *_a, **_k: None)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", lambda *_a, **_k: None)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(run_log_flush, "_commit_run", lambda *_a, **_k: CommandResult(("git", "commit"), 0, "a" * 40 + "\n", "", 0.0), raising=False)  # type: ignore[arg-type]

    skip1 = run_log_flush.refresh_logs_checkpoint(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))
    assert not skip1.skipped
    final1 = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    heading1 = final1.split(":", 1)[-1].split("\n", 1)[0].strip()
    assert heading1 == "shipping"

    _ = state.write_text(
        "RUN_ID=run-abc\nSTALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nPR_URL=https://example.test/pr/12\n"
        "PHASE=ci-initial\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )

    skip2 = run_log_flush.refresh_logs_checkpoint(
        runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path), strict_final_report=True
    )
    assert not skip2.skipped
    final2 = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    heading2 = final2.split(":", 1)[-1].split("\n", 1)[0].strip()
    assert heading2 == "pr-created"
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == config.MANIFEST_STATUS_IN_PROGRESS
    assert manifest["steps_ran"].get("step8") is True


def test_refresh_logs_checkpoint_rewrites_stalled_summary_after_clean_pr_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    _ = (tmp_path / "run-flags.sh").write_text("FORCE_REQUESTED=false\n", encoding="utf-8")
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text(
        "RUN_ID=run-abc\nSTALL_TRACKING=true\nMERGE=true\nPR_NUMBER=\nPHASE=stalled\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "finalize-state.sh").write_text(
        "STALL_TRACKING=true\nSTALL_STEP=5\nPHASE=stalled\nEXIT_CODE=4\n",
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, str(state))
    _ = run_log_manifest.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _stub_rust_manifest_command(monkeypatch)

    def fake_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = implement_tmpdir, run_id
        return {"cost_unavailable": True}

    def fake_commit(*_args: object, **_kwargs: object) -> CommandResult:
        return CommandResult(("git", "commit"), 0, "a" * 40 + "\n", "", 0.0)

    monkeypatch.setattr(final_report, "_final_report_token_fields", fake_token_fields)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit, raising=False)  # type: ignore[arg-type]

    skip1 = run_log_flush.refresh_logs_checkpoint(
        runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path), strict_final_report=True
    )
    assert not skip1.skipped
    stalled_summary = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    assert ": stalled" in stalled_summary
    assert "- **Outcome**: ❌ STALLED" in stalled_summary

    _ = state.write_text(
        "RUN_ID=run-abc\nSTALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nPR_URL=https://example.test/pr/12\n"
        "PHASE=ci-initial\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )

    skip2 = run_log_flush.refresh_logs_checkpoint(
        runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path), strict_final_report=True
    )

    assert not skip2.skipped
    recovered_summary = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    assert ": pr-created" in recovered_summary
    assert "- **Outcome**: ✅ DONE" in recovered_summary
    assert "- **Outcome**: stalled" not in recovered_summary
    assert "- **Outcome**: STALLED" not in recovered_summary
    assert "- **Outcome**: ❌ STALLED" not in recovered_summary


@pytest.mark.parametrize("heading_separator", [": ", " — "])
def test_manifest_only_stalled_summary_reconciliation_updates_heading_and_outcome(
    tmp_path: Path,
    heading_separator: str,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-abc",
        "steps_ran": {},
        "status": config.MANIFEST_STATUS_DONE,
        "pr_number": 12,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text(
        f"## /implement run run-abc{heading_separator}stalled\n\n- **Outcome**: stalled\n- **PR**: #12\n",
        encoding="utf-8",
    )

    assert final_report.reconcile_stalled_summary_from_manifest(run_dir)

    text = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    assert "## /implement run run-abc: merged" in text
    assert "- **Outcome**: ✅ DONE" in text
    assert "- **Outcome**: stalled" not in text
    assert "- **Outcome**: STALLED" not in text
    assert "- **Outcome**: ❌ STALLED" not in text


def test_manifest_only_stalled_summary_reconciliation_rewrites_uppercase_outcome(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-abc",
        "steps_ran": {},
        "status": config.MANIFEST_STATUS_DONE,
        "pr_number": 12,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text(
        "## /implement run run-abc: stalled\n\n- **Outcome**: STALLED\n- **PR**: #12\n",
        encoding="utf-8",
    )

    assert final_report.reconcile_stalled_summary_from_manifest(run_dir)

    text = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    assert "## /implement run run-abc: merged" in text
    assert "- **Outcome**: ✅ DONE" in text
    assert "- **Outcome**: stalled" not in text
    assert "- **Outcome**: STALLED" not in text
    assert "- **Outcome**: ❌ STALLED" not in text


def test_manifest_only_stalled_summary_reconciliation_rewrites_emoji_outcome(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-abc",
        "steps_ran": {},
        "status": config.MANIFEST_STATUS_DONE,
        "pr_number": 12,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text(
        "## /implement run run-abc: stalled\n\n- **Outcome**: ❌ STALLED\n- **PR**: #12\n",
        encoding="utf-8",
    )

    assert final_report.reconcile_stalled_summary_from_manifest(run_dir)

    text = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    assert "## /implement run run-abc: merged" in text
    assert "- **Outcome**: ✅ DONE" in text
    assert "- **Outcome**: stalled" not in text
    assert "- **Outcome**: STALLED" not in text
    assert "- **Outcome**: ❌ STALLED" not in text


def test_manifest_only_stalled_summary_reconciliation_rewrites_legacy_done_outcome(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-abc",
        "steps_ran": {},
        "status": config.MANIFEST_STATUS_DONE,
        "pr_number": 12,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text(
        "## /implement run run-abc: stalled\n\n- **Outcome**: DONE\n- **PR**: #12\n",
        encoding="utf-8",
    )

    assert final_report.reconcile_stalled_summary_from_manifest(run_dir)

    text = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    assert "## /implement run run-abc: merged" in text
    assert "- **Outcome**: ✅ DONE" in text
    assert "- **Outcome**: DONE" not in text


def test_manifest_only_stalled_summary_reconciliation_scans_prelude(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-abc",
        "steps_ran": {},
        "status": config.MANIFEST_STATUS_DONE,
        "pr_number": 12,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text(
        "Preface line\n\n## /implement run run-abc: stalled\n\n- **Outcome**: stalled\n- **PR**: #12\n",
        encoding="utf-8",
    )

    assert final_report.stalled_summary_manifest_reconciliation_needed(run_dir)
    assert final_report.reconcile_stalled_summary_from_manifest(run_dir)

    text = (run_dir / "final-summary.md").read_text(encoding="utf-8")
    assert text.startswith("Preface line\n\n")
    assert "## /implement run run-abc: merged" in text
    assert "- **Outcome**: ✅ DONE" in text
    assert "- **Outcome**: stalled" not in text
    assert "- **Outcome**: STALLED" not in text
    assert "- **Outcome**: ❌ STALLED" not in text


def test_manifest_only_stalled_summary_outcome_bullet_without_heading_does_not_reconcile(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-abc",
        "steps_ran": {},
        "status": config.MANIFEST_STATUS_DONE,
        "pr_number": 12,
    }
    body = "Prelude\n\n- **Outcome**: stalled\n- **PR**: #12\n"
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text(body, encoding="utf-8")

    assert not final_report.summary_heading_is_stalled(body)
    heading_index = final_report._summary_stalled_heading_index(  # pyright: ignore[reportPrivateUsage]
        body.splitlines(keepends=True),
    )
    assert heading_index is None
    assert not final_report.stalled_summary_manifest_reconciliation_needed(run_dir)
    assert not final_report.reconcile_stalled_summary_from_manifest(run_dir)
    assert (run_dir / "final-summary.md").read_text(encoding="utf-8") == body


def test_manifest_only_pr_number_without_done_status_keeps_stalled_summary(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-abc",
        "steps_ran": {},
        "status": config.MANIFEST_STATUS_IN_PROGRESS,
        "pr_number": 12,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text(
        "## /implement run run-abc: stalled\n\n- **Outcome**: stalled\n- **PR**: #12\n",
        encoding="utf-8",
    )

    assert not final_report.reconcile_stalled_summary_from_manifest(run_dir)
    assert "- **Outcome**: stalled" in (run_dir / "final-summary.md").read_text(encoding="utf-8")


def test_manifest_only_stalled_summary_skips_rewrite_with_active_bail_reason(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    run_dir.mkdir(parents=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-abc",
        "steps_ran": {},
        "status": config.MANIFEST_STATUS_DONE,
        "pr_number": 12,
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _ = (run_dir / "final-summary.md").write_text(
        "## /implement run run-abc: stalled\n\n- **Outcome**: stalled\n- **PR**: #12\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "ship-pr-state.sh").write_text("BAIL_REASON=ci-failed\n", encoding="utf-8")

    assert not final_report.reconcile_stalled_summary_from_manifest(run_dir)
    assert "- **Outcome**: stalled" in (run_dir / "final-summary.md").read_text(encoding="utf-8")


def test_refresh_logs_checkpoint_retains_reloaded_step8_after_final_report_reconcile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_log_manifest.init_run(ctx)
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["steps_ran"] = {"step8": False}
    _ = manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def fake_write_final_report(**_kw: object) -> None:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        loaded["steps_ran"]["step8"] = True
        _ = manifest_path.write_text(json.dumps(loaded), encoding="utf-8")

    def noop(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(run_log_flush, "_write_final_report", fake_write_final_report)
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)
    monkeypatch.setattr(run_log_flush, "_write_final_report", fake_write_final_report)
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)
    monkeypatch.setattr(run_log_flush, "_commit_run", lambda *_a, **_k: CommandResult(("git", "commit"), 0, "", "", 0.0), raising=False)  # type: ignore[arg-type]

    skip = run_log_flush.refresh_logs_checkpoint(runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path))

    assert not skip.skipped
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["steps_ran"]["step8"] is True


def test_refresh_logs_checkpoint_strict_final_report_error_returns_recovery_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_log_manifest.init_run(ctx)

    def fail_report(*_a: object, **_k: object) -> None:
        raise ShipError("reconcile failed")

    monkeypatch.setattr(run_log_flush, "_write_final_report", fail_report)  # type: ignore[arg-type]

    skip = run_log_flush.refresh_logs_checkpoint(
        runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path), strict_final_report=True
    )

    assert skip.skipped
    assert skip.reason == run_log_manifest.REFRESH_SKIP_RECOVERY_FAILED


def test_refresh_logs_checkpoint_strict_final_report_skips_tracking_upsert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_log_manifest.init_run(ctx)
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    _stub_rust_manifest_command(monkeypatch)
    seen: list[bool] = []

    def fake_write_final_report(
        *,
        skip_tracking_upsert: bool = False,
        **_kw: object,
    ) -> None:
        seen.append(skip_tracking_upsert)
        _ = (run_dir / "final-summary.md").write_text("summary\n", encoding="utf-8")

    def noop(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(run_log_flush, "_write_final_report", fake_write_final_report)
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)
    monkeypatch.setattr(run_log_flush, "_write_final_report", fake_write_final_report)
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)
    monkeypatch.setattr(run_log_flush, "_commit_run", lambda *_a, **_k: CommandResult(("git", "commit"), 0, "", "", 0.0), raising=False)  # type: ignore[arg-type]

    skip = run_log_flush.refresh_logs_checkpoint(
        runner=RecordingRunner(), ctx=ctx, cwd=str(tmp_path), strict_final_report=True
    )

    assert not skip.skipped
    assert seen == [True, True]


def test_render_token_timing_batches_skips_missing_refresh_json(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    run_log_flush._render_token_timing_batches(  # pyright: ignore[reportPrivateUsage]
        ctx=ctx,
        log_root=tmp_path / "larch-logs",
    )
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    assert not (tmp_path / "token-report-refresh.json").exists()
    assert not (run_dir / "token-report-refresh.json").exists()


def test_stage_ship_route_handoff_copies_when_present(tmp_path: Path) -> None:
    handoff = tmp_path / ".ship-route-exit-handoff.env"
    _ = handoff.write_text("NEXT_ACTION=ci-fix\nFAILED_RUN_ID=abc123\n", encoding="utf-8")
    ctx = _ctx(tmp_path)
    log_root = tmp_path / "larch-logs"
    run_log_flush._stage_ship_route_handoff(ctx=ctx, log_root=log_root)  # pyright: ignore[reportPrivateUsage]
    dest = log_root / "implement" / "run-abc" / "ship-route-exit-handoff.env"
    assert dest.is_file()
    assert "NEXT_ACTION=ci-fix" in dest.read_text(encoding="utf-8")


def test_stage_ship_route_handoff_skips_when_absent(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    log_root = tmp_path / "larch-logs"
    run_log_flush._stage_ship_route_handoff(ctx=ctx, log_root=log_root)  # pyright: ignore[reportPrivateUsage]
    dest = log_root / "implement" / "run-abc" / "ship-route-exit-handoff.env"
    assert not dest.exists()


def test_update_manifest_ignores_unknown_keys(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _ = run_log_manifest.init_run(ctx)
    manifest = run_log_manifest.update_manifest(ctx, version="9", updated_at="now")
    assert manifest.version == "9"
    assert manifest.updated_at == "now"
    assert "version" not in manifest.steps_ran


def test_read_state_kv_unreadable_file_returns_empty(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_bytes(b"\xff\xfe")
    assert run_log_manifest.read_state_kv(state_file=str(state), key="RUN_ID") == ""


def test_refresh_logs_checkpoint_stages_without_repo_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    ctx = _ctx(tmp_path, str(state))
    _ = run_log_manifest.init_run(ctx)

    def noop(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(run_log_flush, "_write_final_report", noop)
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)
    runner = RecordingRunner()
    skip = run_log_flush.refresh_logs_checkpoint(runner=runner, ctx=ctx, cwd=None)
    assert not skip.skipped


def test_load_or_recover_manifest_prefers_ctx_run_id(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs" / "implement"
    old = log_root / "run-old"
    new = log_root / "run-abc"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    _ = (old / "manifest.json").write_text(
        json.dumps({"status": "partial", "version": "1", "run_id": "run-old", "steps_ran": {}}),
        encoding="utf-8",
    )
    _ = (new / "manifest.json").write_text(
        json.dumps({"status": "partial", "version": "1", "run_id": "run-abc", "steps_ran": {}}),
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, state_file=None)
    manifest = run_log_manifest.load_or_recover_manifest(ctx)
    assert manifest.run_id == "run-abc"


def test_load_or_recover_manifest_fails_closed_without_valid_run_id(
    tmp_path: Path,
) -> None:
    newest = tmp_path / "larch-logs" / "implement" / "run-new"
    newest.mkdir(parents=True)
    _ = (newest / "manifest.json").write_text(
        json.dumps(
            {"status": "partial", "version": "1", "run_id": "run-new", "steps_ran": {}},
        ),
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path).with_(run_id="../bad")
    manifest = run_log_manifest.load_or_recover_manifest(ctx)
    assert manifest.run_id == ""
    assert not manifest.steps_ran


def test_scrub_run_tree_redacts_cursor_key(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
    sub = run_dir / "round-1"
    sub.mkdir(parents=True)
    secret = (
        "cursor --api-key crsr_1620abcdefghijklmnopqrstuvwxyz0123456789 --workspace /x\n"
    )
    _ = (sub / "findings.md").write_text(secret, encoding="utf-8")
    _ = (run_dir / "clean.md").write_text("clean prose\n", encoding="utf-8")
    violations, files_scrubbed = run_log_commit._scrub_run_tree(  # pyright: ignore[reportPrivateUsage]
        run_dir,
    )
    assert violations == 1
    assert files_scrubbed == 1
    assert "crsr_1620" not in (sub / "findings.md").read_text(encoding="utf-8")
    assert (run_dir / "clean.md").read_text(encoding="utf-8") == "clean prose\n"


def test_scrub_run_tree_redacts_tmpdir_paths(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    artifact = run_dir / "artifact.txt"
    _ = artifact.write_text(
        "failure at /private/tmp/larch-design-run.123/result.env\n",
        encoding="utf-8",
    )

    violations, files_scrubbed = run_log_commit._scrub_run_tree(  # pyright: ignore[reportPrivateUsage]
        run_dir
    )

    assert violations == 0
    assert files_scrubbed == 1
    assert "/private/tmp/" not in artifact.read_text(encoding="utf-8")


def test_rebase_under_tmpdir_handles_session_local_absolute_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "record.json"
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    assert _rebase_under_tmpdir(str(source)) == source


def test_rebase_under_tmpdir_keeps_external_absolute_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = Path("/var/folders/example/T/record.json")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    assert _rebase_under_tmpdir(str(source)) == source


def test_rebase_under_tmpdir_prepends_relative_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    assert _rebase_under_tmpdir("record.json") == tmp_path / "record.json"


def test_rebase_under_tmpdir_uses_default_leaf_for_empty_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    assert _rebase_under_tmpdir("", default_leaf="default.json") == tmp_path / "default.json"


def test_rebase_under_tmpdir_returns_path_without_implement_tmpdir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)

    assert _rebase_under_tmpdir("record.json") == Path("record.json")


_DEBATE_SESSION_POINTER = "/tmp/claude-implement-AbC123/plan.txt"
_DEBATE_OPERATOR_PATH = "/Users/example/larch3/skills/debate/SKILL.md"


def test_debate_batch_registry_contracts() -> None:
    assert run_log_batch._batch_extension("debate-round-ledger") == ".ndjson"  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._batch_mode("debate-round-ledger") == "append"  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._batch_sanitizer("debate-round-ledger") == "json-lines"  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._batch_extension("debate-proposal") == ".md"  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._batch_mode("debate-proposal") == "replace"  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._batch_sanitizer("debate-proposal") == "none"  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._batch_extension("debate-stalemate-tally") == ".json"  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._batch_mode("debate-stalemate-tally") == "replace"  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._batch_sanitizer("debate-stalemate-tally") == "json-object"  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._batch_extension("debate-participants") == ".tsv"  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._batch_mode("debate-participants") == "replace"  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._batch_sanitizer("debate-participants") == "none"  # pyright: ignore[reportPrivateUsage]


def test_debate_batches_round_trip_append_and_replace(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    ledger_one = tmp_path / "ledger-1.ndjson"
    ledger_two = tmp_path / "ledger-2.ndjson"
    _ = ledger_one.write_text('{"round":1,"point":"p1","stance":"HOLD"}\n', encoding="utf-8")
    _ = ledger_two.write_text('{"round":2,"point":"p1","stance":"AGREE"}\n', encoding="utf-8")
    path, written, unchanged = _append_batch(
        log_root=log_root,
        skill="debate",
        run_id="run-abc",
        batch="debate-round-ledger",
        record_file=str(ledger_one),
    )
    assert written is True
    assert unchanged is False
    _, written2, _ = _append_batch(
        log_root=log_root,
        skill="debate",
        run_id="run-abc",
        batch="debate-round-ledger",
        record_file=str(ledger_two),
    )
    assert written2 is True
    assert path.read_text(encoding="utf-8") == (
        '{"round":1,"point":"p1","stance":"HOLD"}\n'
        '{"round":2,"point":"p1","stance":"AGREE"}\n'
    )

    proposal = tmp_path / "proposal.md"
    _ = proposal.write_text("# Proposal\nShip the narrow carrier.\n", encoding="utf-8")
    proposal_path, _, _ = _write_batch(
        log_root=log_root,
        skill="debate",
        run_id="run-abc",
        batch="debate-proposal",
        input_file=str(proposal),
    )
    _ = proposal.write_text("# Proposal\nRevised body.\n", encoding="utf-8")
    _, written_prop, _ = _write_batch(
        log_root=log_root,
        skill="debate",
        run_id="run-abc",
        batch="debate-proposal",
        input_file=str(proposal),
    )
    assert written_prop is True
    assert proposal_path.read_text(encoding="utf-8") == "# Proposal\nRevised body.\n"

    tally = tmp_path / "tally.json"
    _ = tally.write_text('{"outcome":"BOTH_VIABLE","points":["p1"]}\n', encoding="utf-8")
    tally_path, _, _ = _write_batch(
        log_root=log_root,
        skill="debate",
        run_id="run-abc",
        batch="debate-stalemate-tally",
        input_file=str(tally),
    )
    assert json.loads(tally_path.read_text(encoding="utf-8"))["outcome"] == "BOTH_VIABLE"

    participants = tmp_path / "participants.tsv"
    _ = participants.write_text("vendor\tslot\tstatus\ncodex\t1\tlive\n", encoding="utf-8")
    participants_path, _, _ = _write_batch(
        log_root=log_root,
        skill="debate",
        run_id="run-abc",
        batch="debate-participants",
        input_file=str(participants),
    )
    assert "codex\t1\tlive" in participants_path.read_text(encoding="utf-8")


def test_debate_batches_validate_malformed_json(tmp_path: Path) -> None:
    log_root = tmp_path / "larch-logs"
    bad_ledger = tmp_path / "bad-ledger.ndjson"
    _ = bad_ledger.write_text("{not-json\n", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        _ = _append_batch(
            log_root=log_root,
            skill="debate",
            run_id="run-abc",
            batch="debate-round-ledger",
            record_file=str(bad_ledger),
        )

    bad_tally = tmp_path / "bad-tally.json"
    _ = bad_tally.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="requires a JSON object"):
        _ = _write_batch(
            log_root=log_root,
            skill="debate",
            run_id="run-abc",
            batch="debate-stalemate-tally",
            input_file=str(bad_tally),
        )


def test_debate_proposal_redacts_operator_repo_and_secrets(tmp_path: Path) -> None:
    proposal = tmp_path / "proposal.md"
    secret = "ghp_" + "abcdefghijklmnopqrstuvwxyz1234567890ABCD"
    _ = proposal.write_text(
        f"See {_DEBATE_OPERATOR_PATH} and token {secret}\n",
        encoding="utf-8",
    )
    path, _, _ = _write_batch(
        log_root=tmp_path / "larch-logs",
        skill="debate",
        run_id="run-abc",
        batch="debate-proposal",
        input_file=str(proposal),
    )
    text = path.read_text(encoding="utf-8")
    assert _DEBATE_OPERATOR_PATH not in text
    assert config.REDACTED_OPERATOR_REPO in text
    assert secret not in text
    assert config.REDACTED_TOKEN in text


@pytest.mark.parametrize(
    ("batch", "mode", "payload"),
    [
        ("debate-proposal", "replace", f"pointer {_DEBATE_SESSION_POINTER}\n"),
        ("debate-participants", "replace", f"vendor\tslot\ncodex\t{_DEBATE_SESSION_POINTER}\n"),
        (
            "debate-round-ledger",
            "append",
            json.dumps({"note": _DEBATE_SESSION_POINTER}) + "\n",
        ),
        (
            "debate-stalemate-tally",
            "replace",
            json.dumps({"path": _DEBATE_SESSION_POINTER}) + "\n",
        ),
    ],
)
def test_debate_batches_reject_raw_session_tmpdir_before_redaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    batch: str,
    mode: str,
    payload: str,
) -> None:
    calls: list[Path] = []
    original_redact = run_log_batch._redact_to_temp  # pyright: ignore[reportPrivateUsage]

    def spy_redact_to_temp(
        input_file: Path,
        *,
        scratch_dir: Path,
        cap_bytes: int | None = None,
    ) -> Path:
        calls.append(input_file)
        return original_redact(
            input_file,
            scratch_dir=scratch_dir,
            cap_bytes=cap_bytes,
        )

    monkeypatch.setattr(run_log_batch, "_redact_to_temp", spy_redact_to_temp)
    source = tmp_path / "payload.txt"
    _ = source.write_text(payload, encoding="utf-8")
    log_root = tmp_path / "larch-logs"
    if mode == "append":
        with pytest.raises(ValueError, match="rejects recognized session-tmpdir pointers"):
            _ = _append_batch(
                log_root=log_root,
                skill="debate",
                run_id="run-abc",
                batch=batch,
                record_file=str(source),
            )
    else:
        with pytest.raises(ValueError, match="rejects recognized session-tmpdir pointers"):
            _ = _write_batch(
                log_root=log_root,
                skill="debate",
                run_id="run-abc",
                batch=batch,
                input_file=str(source),
            )
    assert not calls
    out = log_root / "debate" / "run-abc" / f"{batch}{run_log_batch._batch_extension(batch)}"  # pyright: ignore[reportPrivateUsage]
    assert not out.exists()


def test_debate_json_batches_reject_escaped_session_tmpdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Path] = []
    original_redact = run_log_batch._redact_to_temp  # pyright: ignore[reportPrivateUsage]

    def spy_redact_to_temp(
        input_file: Path,
        *,
        scratch_dir: Path,
        cap_bytes: int | None = None,
    ) -> Path:
        calls.append(input_file)
        return original_redact(
            input_file,
            scratch_dir=scratch_dir,
            cap_bytes=cap_bytes,
        )

    monkeypatch.setattr(run_log_batch, "_redact_to_temp", spy_redact_to_temp)
    log_root = tmp_path / "larch-logs"

    # Escaped slashes still contain /tmp/… after the backslash boundary; reject
    # before redaction (raw or decoded).
    escaped_slash = '{"note":"\\/tmp\\/claude-implement-AbC123\\/plan.txt"}\n'
    ledger = tmp_path / "escaped-ledger.ndjson"
    _ = ledger.write_text(escaped_slash, encoding="utf-8")
    with pytest.raises(ValueError, match="rejects recognized session-tmpdir pointers"):
        _ = _append_batch(
            log_root=log_root,
            skill="debate",
            run_id="run-abc",
            batch="debate-round-ledger",
            record_file=str(ledger),
        )

    # Unicode escapes omit literal /tmp/ in the raw file; decoded values reject.
    unicode_escaped = '{"path":"\\u002ftmp\\u002fclaude-implement-AbC123\\u002fplan.txt"}\n'
    assert "/tmp/claude-implement-AbC123" not in unicode_escaped
    tally = tmp_path / "escaped-tally.json"
    _ = tally.write_text(unicode_escaped, encoding="utf-8")
    with pytest.raises(ValueError, match="rejects recognized session-tmpdir pointers"):
        _ = _write_batch(
            log_root=log_root,
            skill="debate",
            run_id="run-abc",
            batch="debate-stalemate-tally",
            input_file=str(tally),
        )

    # A pointer hidden in a JSON object key rejects the same way.
    escaped_key = '{"\\u002ftmp\\u002fclaude-implement-AbC123\\u002fplan.txt":1}\n'
    assert "/tmp/claude-implement-AbC123" not in escaped_key
    key_tally = tmp_path / "escaped-key-tally.json"
    _ = key_tally.write_text(escaped_key, encoding="utf-8")
    with pytest.raises(ValueError, match="rejects recognized session-tmpdir pointers"):
        _ = _write_batch(
            log_root=log_root,
            skill="debate",
            run_id="run-abc",
            batch="debate-stalemate-tally",
            input_file=str(key_tally),
        )
    key_ledger = tmp_path / "escaped-key-ledger.ndjson"
    _ = key_ledger.write_text(
        '{"row":{"\\u002ftmp\\u002fclaude-implement-AbC123\\u002fplan.txt":1}}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="rejects recognized session-tmpdir pointers"):
        _ = _append_batch(
            log_root=log_root,
            skill="debate",
            run_id="run-abc",
            batch="debate-round-ledger",
            record_file=str(key_ledger),
        )
    assert not calls


def test_debate_append_rejection_preserves_prior_content(
    tmp_path: Path,
) -> None:
    log_root = tmp_path / "larch-logs"
    good = tmp_path / "good.ndjson"
    _ = good.write_text('{"round":1,"ok":true}\n', encoding="utf-8")
    path, _, _ = _append_batch(
        log_root=log_root,
        skill="debate",
        run_id="run-abc",
        batch="debate-round-ledger",
        record_file=str(good),
    )
    before = path.read_text(encoding="utf-8")
    bad = tmp_path / "bad.ndjson"
    _ = bad.write_text(json.dumps({"note": _DEBATE_SESSION_POINTER}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="rejects recognized session-tmpdir pointers"):
        _ = _append_batch(
            log_root=log_root,
            skill="debate",
            run_id="run-abc",
            batch="debate-round-ledger",
            record_file=str(bad),
        )
    assert path.read_text(encoding="utf-8") == before


def test_run_log_checkpoint_warns_when_stage_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.delenv("LARCH_NO_LOGS_COMMIT", raising=False)
    _ = (tmp_path / "session-id").write_text("run-abc\n", encoding="utf-8")

    def fail_stage(*_args: object, **_kwargs: object) -> None:
        raise OSError("stage unavailable")

    monkeypatch.setattr(run_log_flush, "_stage_local_checkpoint", fail_stage)
    monkeypatch.setattr(run_log_flush, "_stage_local_checkpoint", fail_stage)  # type: ignore[arg-type]

    rc = run_log_flush.run_log_checkpoint_main([])

    assert rc == config.EXIT_INTERNAL_ERROR
    assert "WARN: run-log checkpoint failed: stage unavailable" in capsys.readouterr().err


def test_larch_log_flush_does_not_call_git_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.delenv("LARCH_NO_LOGS_COMMIT", raising=False)
    _ = (tmp_path / "session-id").write_text("run-abc\n", encoding="utf-8")

    def fail_commit(*_args: object, **_kwargs: object) -> CommandResult:
        return CommandResult(
            ("run-log", "commit"),
            1,
            "",
            "refusing to replace symlink destination: /some/path\n",
            0.0,
        )

    monkeypatch.setattr(run_log_flush, "_stage_local_checkpoint", lambda *_a, **_k: None)  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    monkeypatch.setattr(run_log_flush, "_stage_local_checkpoint", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(run_log_flush, "_commit_run", fail_commit, raising=False)

    rc = run_log_flush.run_log_checkpoint_main([])

    assert rc == 0
    assert capsys.readouterr().err == ""


def test_round_artifact_allowlist_includes_degraded_attempt_tallies() -> None:
    assert run_log_batch._round_artifact_included("voting-tally-degraded-attempt-1.md")  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._round_artifact_included("voting-tally-degraded-attempt-2.md")  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._round_artifact_included("oos.md")  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._round_artifact_included("panel-manifest.ndjson.output-files.dropped-slots")  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._round_artifact_included("panel-prompt-sizes.tsv")  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._round_artifact_included("dropped-dyn-lint-cursor-straggler-dropped.txt")  # pyright: ignore[reportPrivateUsage]
    assert run_log_batch._round_artifact_included("oos-dropped-before-vote.md")  # pyright: ignore[reportPrivateUsage]
    assert not run_log_batch._round_artifact_included("dyn-lint-output.txt")  # pyright: ignore[reportPrivateUsage]


def test_warn_secret_scrub_remains_warning_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_log_commit._warn_secret_scrub(violations=2, files_scrubbed=1, directory=tmp_path)  # pyright: ignore[reportPrivateUsage]

    assert "SECRETS DETECTED AND SCRUBBED" in capsys.readouterr().err


def test_publish_breadcrumbs_consumer_invokes_rust_owner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recorded: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> CommandResult:
        recorded.append(argv)
        return CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(run_log_commit.proc, "run", fake_run)
    dest = tmp_path / "larch-logs" / "implement" / "run-abc"

    run_log_commit._publish_breadcrumbs_with_warning(log_root=tmp_path / "larch-logs", dest=dest)  # pyright: ignore[reportPrivateUsage]

    assert len(recorded) == 1
    assert recorded[0][0].endswith("/scripts/larch.sh")
    assert recorded[0][1:] == [
        "run-log",
        "publish-breadcrumbs",
        "--source-dir",
        str(tmp_path / "breadcrumbs"),
        "--dest-dir",
        str(dest / "breadcrumbs"),
    ]


def test_publish_breadcrumbs_consumer_warns_on_owner_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def failing_run(argv: list[str], **_kwargs: object) -> CommandResult:
        return CommandResult(tuple(argv), 1, "", "publish-breadcrumbs: refusing symlink\n", 0.0)

    monkeypatch.setattr(run_log_commit.proc, "run", failing_run)

    run_log_commit._publish_breadcrumbs_with_warning(  # pyright: ignore[reportPrivateUsage]
        log_root=tmp_path / "larch-logs",
        dest=tmp_path / "larch-logs" / "implement" / "run-abc",
    )

    assert (
        "WARN: run-log breadcrumb publish failed: publish-breadcrumbs: refusing symlink"
        in capsys.readouterr().err
    )


def test_publish_breadcrumbs_consumer_skips_non_larch_logs_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_run(argv: list[str], **_kwargs: object) -> CommandResult:
        raise AssertionError(f"unexpected breadcrumb spawn: {argv}")

    monkeypatch.setattr(run_log_commit.proc, "run", fail_run)

    run_log_commit._publish_breadcrumbs_with_warning(  # pyright: ignore[reportPrivateUsage]
        log_root=tmp_path / "review-logs",
        dest=tmp_path / "review-logs" / "review" / "run-abc",
    )


def test_refresh_logs_checkpoint_does_not_probe_git_volatile_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_commit(*_a: object, **_k: object) -> CommandResult:
        return CommandResult(("larch-log-volatile-only",), 0, "", "", 0.01)

    monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit, raising=False)
    skip = run_log_flush.refresh_logs_checkpoint(runner=RecordingRunner(), ctx=_ctx(tmp_path), cwd=str(tmp_path))
    assert not skip.skipped


def test_render_ledger_reports_uses_direct_renderers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "timing-ledger.tsv").write_text(
        "v1\tmark\t1\timplement\tStep 0\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )
    captured: dict[str, str] = {}

    def capture_env(env: object) -> None:
        if isinstance(env, Mapping):
            env_map = cast("Mapping[object, object]", env)
            captured.update(
                {key: value for key, value in env_map.items() if isinstance(key, str) and isinstance(value, str)}
            )

    def fake_token_report(**kwargs: object) -> dict[str, object]:
        capture_env(kwargs.get("env"))
        return {"claude": {}}

    def fake_render_json(_self: timing.TimingReport, *, env: object = None, **_: object) -> dict[str, object]:
        capture_env(env)
        return {"per_step": []}

    def fake_resolve_timing_ledger_path(**_: object) -> Path:
        return tmp_path / "timing-ledger.tsv"

    monkeypatch.setattr(tokens, "token_report", fake_token_report)
    monkeypatch.setattr(timing.TimingReport, "render_json", fake_render_json)
    monkeypatch.setattr(timing, "resolve_timing_ledger_path", fake_resolve_timing_ledger_path)
    write_batches: list[str] = []

    def fake_write_batch(
        *, batch: str, input_file: Path, **_kw: object
    ) -> tuple[Path, bool, bool]:
        write_batches.append(batch)
        return (input_file, True, False)

    monkeypatch.setattr(run_log_batch, "_write_batch", fake_write_batch)
    monkeypatch.setattr(run_log_flush, "_write_batch", fake_write_batch)
    ctx = _ctx(tmp_path, str(state))
    runner = RecordingRunner()
    run_log_flush._render_ledger_reports(runner=runner, ctx=ctx, log_root=tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

    assert (tmp_path / "token-report-refresh.json").is_file()
    assert (tmp_path / "timing-report-refresh.json").is_file()
    assert captured.get("LARCH_TIMING_SKILL") == "implement"
    assert "DESIGN_TMPDIR" not in captured
    assert "token-report" in write_batches
    assert "timing-report" in write_batches


def _ledger_report_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[RecordingRunner, RunContext, list[str]]:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    _ = (tmp_path / "timing-ledger.tsv").write_text(
        "v1\tmark\t1\timplement\tStep 0\t-\t-\t-\t-\t-\t-\t-\t-\n",
        encoding="utf-8",
    )
    _ledger_path = tmp_path / "timing-ledger.tsv"
    monkeypatch.setattr(timing, "resolve_timing_ledger_path", lambda **_kw: _ledger_path)  # type: ignore[arg-type]
    write_batches: list[str] = []

    def fake_write_batch(
        *, batch: str, input_file: Path, **_kw: object
    ) -> tuple[Path, bool, bool]:
        write_batches.append(batch)
        return (input_file, True, False)

    monkeypatch.setattr(run_log_batch, "_write_batch", fake_write_batch)
    monkeypatch.setattr(run_log_flush, "_write_batch", fake_write_batch)
    return RecordingRunner(), _ctx(tmp_path, str(state)), write_batches


def test_render_ledger_reports_timing_succeeds_when_token_report_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, ctx, write_batches = _ledger_report_fixture(monkeypatch, tmp_path)

    def raise_token_report(**_kwargs: object) -> dict[str, object]:
        msg = "token renderer failed"
        raise RuntimeError(msg)

    monkeypatch.setattr(tokens, "token_report", raise_token_report)
    run_log_flush._render_ledger_reports(runner=runner, ctx=ctx, log_root=tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

    assert not (tmp_path / "token-report-refresh.json").exists()
    assert (tmp_path / "timing-report-refresh.json").is_file()
    assert "token-report" not in write_batches
    assert "timing-report" in write_batches


def test_render_ledger_reports_token_succeeds_when_timing_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, ctx, write_batches = _ledger_report_fixture(monkeypatch, tmp_path)

    def fake_token_report(**_kwargs: object) -> dict[str, object]:
        return {"claude": {}}

    def raise_render_json(_self: timing.TimingReport, **_: object) -> dict[str, object]:  # type: ignore[misc]
        raise RuntimeError("timing renderer failed")

    monkeypatch.setattr(tokens, "token_report", fake_token_report)
    monkeypatch.setattr(timing.TimingReport, "render_json", raise_render_json)
    run_log_flush._render_ledger_reports(runner=runner, ctx=ctx, log_root=tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

    assert (tmp_path / "token-report-refresh.json").is_file()
    assert not (tmp_path / "timing-report-refresh.json").exists()
    assert "token-report" in write_batches
    assert "timing-report" not in write_batches


def test_render_ledger_reports_writes_empty_timing_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner, ctx, _write_batches = _ledger_report_fixture(monkeypatch, tmp_path)

    def fake_token_report(**_kwargs: object) -> dict[str, object]:
        return {"claude": {}}

    def empty_render_json(_self: timing.TimingReport, **_: object) -> dict[str, object]:  # type: ignore[misc]
        return {}

    monkeypatch.setattr(tokens, "token_report", fake_token_report)
    monkeypatch.setattr(timing.TimingReport, "render_json", empty_render_json)
    run_log_flush._render_ledger_reports(runner=runner, ctx=ctx, log_root=tmp_path / "logs")  # pyright: ignore[reportPrivateUsage]

    timing_path = tmp_path / "timing-report-refresh.json"
    assert timing_path.is_file()
    assert json.loads(timing_path.read_text(encoding="utf-8")) == {}


def test_report_subprocess_env_pins_implement_and_clears_design_tmpdir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    design_tmp = tmp_path / "design"
    design_tmp.mkdir()
    _ = (design_tmp / "run-params.json").write_text(json.dumps({}), encoding="utf-8")
    monkeypatch.setenv("LARCH_TIMING_SKILL", "design")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design_tmp))
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    env = run_log_flush._report_subprocess_env(_ctx(tmp_path, str(state)))  # pyright: ignore[reportPrivateUsage]
    assert env["LARCH_TIMING_SKILL"] == "implement"
    assert "DESIGN_TMPDIR" not in env


def _write_run_manifest(run_dir: Path, *, skill: str, steps_ran: dict[str, object] | None = None) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "schema_version": 2,
        "skill": skill,
        "run_id": run_dir.name,
        "steps_ran": steps_ran or {},
        "status": "partial",
    }
    _ = (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_artifact_present_or_waived_matches_implement_capture_warning(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN1"
    _write_run_manifest(run_dir, skill="implement")
    body = "- **Step 18: session-transcript status=write-failed:** source file disappeared"
    _ = (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Warnings", "body": body}) + "\n",
        encoding="utf-8",
    )
    artifact = run_log_manifest.RequiredArtifact(
        slug="session-transcript", relative_path="session-transcript.jsonl", skill="implement", condition="step18"
    )

    assert run_log_manifest.artifact_present_or_waived(
        run_dir=run_dir,
        artifact=artifact,
        execution_issues_path=run_dir / "execution-issues.ndjson",
    )


def test_artifact_present_or_waived_matches_design_capture_warning(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "design" / "RUN1"
    _write_run_manifest(run_dir, skill="design")
    _ = (run_dir / "execution-issues.md").write_text(
        "### Warnings\n- design Step 5c session-transcript write-failed: source file disappeared\n",
        encoding="utf-8",
    )
    artifact = run_log_manifest.RequiredArtifact(
        slug="session-transcript",
        relative_path="session-transcript.jsonl",
        skill="design",
        condition="design-transcript",
    )

    assert run_log_manifest.artifact_present_or_waived(
        run_dir=run_dir,
        artifact=artifact,
        execution_issues_path=run_dir / "execution-issues.md",
    )


def test_artifact_present_or_waived_ignores_live_tmpdir_warning(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN1"
    _write_run_manifest(run_dir, skill="implement")
    live_issue_log = tmp_path / "execution-issues.md"
    _ = live_issue_log.write_text(
        "### Warnings\n- **Step 18: session-transcript status=write-failed:** source file disappeared\n",
        encoding="utf-8",
    )
    artifact = run_log_manifest.RequiredArtifact(
        slug="session-transcript", relative_path="session-transcript.jsonl", skill="implement", condition="step18"
    )

    assert not run_log_manifest.artifact_present_or_waived(
        run_dir=run_dir,
        artifact=artifact,
        execution_issues_path=live_issue_log,
    )


def test_design_plan_review_round_requires_classification_without_full_review_file(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "design" / "RUN1"
    _write_run_manifest(run_dir, skill="design")
    round_dir = run_dir / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "findings-classification.tsv").write_text("id\tstatus\n", encoding="utf-8")

    ok, missing = run_log_manifest.verify_run_log_completeness(run_dir=run_dir, skill="design")
    rows = run_log_manifest.required_artifacts_for_run(
        run_dir=run_dir,
        skill="design",
        manifest=run_log_manifest.Manifest.from_json(json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))),
    )

    assert ok is True
    assert missing == []
    assert "review-findings-full.jsonl" not in {row.relative_path for row in rows}
    assert "plan-review/round-1/findings-classification.tsv" in {row.relative_path for row in rows}


def test_design_plan_review_multi_round_requires_each_classification(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "design" / "RUN1"
    _write_run_manifest(run_dir, skill="design")
    round1 = run_dir / "plan-review" / "round-1"
    round2 = run_dir / "plan-review" / "round-2"
    round1.mkdir(parents=True)
    round2.mkdir(parents=True)
    _ = (round1 / "findings-classification.tsv").write_text("id\tstatus\n", encoding="utf-8")

    ok, missing = run_log_manifest.verify_run_log_completeness(run_dir=run_dir, skill="design")

    assert ok is False
    assert missing == ["plan-review-round-2:plan-review/round-2/findings-classification.tsv"]


def test_design_final_summary_requires_session_transcript(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "design" / "RUN1"
    _write_run_manifest(run_dir, skill="design")
    _ = (run_dir / "final-summary.md").write_text("summary\n", encoding="utf-8")

    ok, missing = run_log_manifest.verify_run_log_completeness(run_dir=run_dir, skill="design")

    assert ok is False
    assert missing == ["session-transcript:session-transcript.jsonl"]


def test_design_publish_transcript_waived_by_committed_execution_issue(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "design" / "RUN1"
    _write_run_manifest(run_dir, skill="design")
    _ = (run_dir / "final-summary.md").write_text("summary\n", encoding="utf-8")
    _ = (run_dir / "execution-issues.md").write_text(
        "### Warnings\n- design Step 5c session-transcript write-failed: source file disappeared\n",
        encoding="utf-8",
    )

    ok, missing = run_log_manifest.verify_run_log_completeness(run_dir=run_dir, skill="design")

    assert ok is True
    assert missing == []


def _design_run_with_final_summary(tmp_path: Path, *, outcome: str = "approved") -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    run_dir = repo / "larch-logs" / "design" / "RUN1"
    repo.mkdir(parents=True)
    _write_run_manifest(run_dir, skill="design")
    (run_dir / "final-summary.md").write_text(f"## /design run RUN1: {outcome}\n\n", encoding="utf-8")
    (run_dir / "session-transcript.jsonl").write_text('{"type":"message"}\n', encoding="utf-8")
    return repo, run_dir


def test_design_invariant_assessment_required_for_approved_present_invariants(tmp_path: Path) -> None:
    repo, run_dir = _design_run_with_final_summary(tmp_path)
    (repo / "ARCHITECTURAL_INVARIANTS.md").write_text("### I-Test-1: Test\nInvariant text.\n", encoding="utf-8")

    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )

    assert ok is False
    assert missing == ["invariant-assessment:architectural-invariant-assessment.md"]


def test_design_invariant_assessment_required_for_approved_partition(tmp_path: Path) -> None:
    repo, run_dir = _design_run_with_final_summary(tmp_path, outcome="approved-partition")
    (repo / "ARCHITECTURAL_INVARIANTS.md").write_text("### I-Test-1: Test\nInvariant text.\n", encoding="utf-8")

    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )

    assert ok is False
    assert missing == ["invariant-assessment:architectural-invariant-assessment.md"]


def test_design_invariant_assessment_present_passes(tmp_path: Path) -> None:
    repo, run_dir = _design_run_with_final_summary(tmp_path)
    (repo / "ARCHITECTURAL_INVARIANTS.md").write_text("### I-Test-1: Test\nInvariant text.\n", encoding="utf-8")
    (run_dir / "architectural-invariant-assessment.md").write_text("clean\n", encoding="utf-8")

    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )

    assert ok is True
    assert missing == []


def test_design_invariant_assessment_warning_waives_missing_artifact(tmp_path: Path) -> None:
    repo, run_dir = _design_run_with_final_summary(tmp_path)
    (repo / "ARCHITECTURAL_INVARIANTS.md").write_text("### I-Test-1: Test\nInvariant text.\n", encoding="utf-8")
    (run_dir / "execution-issues.md").write_text(
        "### Warnings\n- invariant-assessment: missing architectural-invariant-assessment.md\n",
        encoding="utf-8",
    )

    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )

    assert ok is True
    assert missing == []


def test_design_invariant_assessment_not_required_for_nonapproved_absent_invalid_or_empty(
    tmp_path: Path,
) -> None:
    repo, run_dir = _design_run_with_final_summary(tmp_path, outcome="failed-plan-write")
    (repo / "ARCHITECTURAL_INVARIANTS.md").write_text("### I-Test-1: Test\nInvariant text.\n", encoding="utf-8")

    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )
    assert ok is True
    assert missing == []

    (run_dir / "final-summary.md").write_text("## /design run RUN1: approved\n\n", encoding="utf-8")
    (repo / "ARCHITECTURAL_INVARIANTS.md").unlink()
    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )
    assert ok is True
    assert missing == []

    (repo / "ARCHITECTURAL_INVARIANTS.md").mkdir()
    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )
    assert ok is True
    assert missing == []

    (repo / "ARCHITECTURAL_INVARIANTS.md").rmdir()
    (repo / "ARCHITECTURAL_INVARIANTS.md").write_text("# No invariant entries\n", encoding="utf-8")
    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )
    assert ok is True
    assert missing == []


def test_archive_prep_completeness_refuses_missing_invariant_assessment(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ARCHITECTURAL_INVARIANTS.md").write_text("### I-Test-1: Test\nInvariant text.\n", encoding="utf-8")
    log_root = tmp_path / "session" / "larch-logs"
    run_dir = log_root / "design" / "RUN1"
    _write_run_manifest(run_dir, skill="design")
    (run_dir / "final-summary.md").write_text("## /design run RUN1: approved\n\n", encoding="utf-8")
    (run_dir / "session-transcript.jsonl").write_text('{"type":"message"}\n', encoding="utf-8")

    with pytest.raises(ShipError) as excinfo:
        _ = run_log_commit.prepare_run_for_archive(
            log_root=log_root,
            repo_root=repo,
            skill="design",
            run_id="RUN1",
        )

    assert str(excinfo.value) == "run-log incomplete: invariant-assessment:architectural-invariant-assessment.md"


def test_design_guideline_assessment_required_for_approved_present_guidelines(tmp_path: Path) -> None:
    repo, run_dir = _design_run_with_final_summary(tmp_path)
    (repo / "ARCHITECTURAL_GUIDELINES.md").write_text("### G-Test-1: Test\n- Why: test.\n", encoding="utf-8")

    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )

    assert ok is False
    assert missing == ["guideline-assessment:architectural-guideline-assessment.md"]


def test_design_guideline_assessment_present_passes(tmp_path: Path) -> None:
    repo, run_dir = _design_run_with_final_summary(tmp_path)
    (repo / "ARCHITECTURAL_GUIDELINES.md").write_text("### G-Test-1: Test\n- Why: test.\n", encoding="utf-8")
    (run_dir / "architectural-guideline-assessment.md").write_text("clean\n", encoding="utf-8")

    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )

    assert ok is True
    assert missing == []


def test_design_guideline_assessment_warning_waives_missing_artifact(tmp_path: Path) -> None:
    repo, run_dir = _design_run_with_final_summary(tmp_path)
    (repo / "ARCHITECTURAL_GUIDELINES.md").write_text("### G-Test-1: Test\n- Why: test.\n", encoding="utf-8")
    (run_dir / "execution-issues.md").write_text(
        "### Warnings\n- guideline-assessment: missing architectural-guideline-assessment.md\n",
        encoding="utf-8",
    )

    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )

    assert ok is True
    assert missing == []


def test_design_guideline_assessment_not_required_for_nonapproved_or_absent_invalid(
    tmp_path: Path,
) -> None:
    repo, run_dir = _design_run_with_final_summary(tmp_path, outcome="failed-plan-write")
    (repo / "ARCHITECTURAL_GUIDELINES.md").write_text("### G-Test-1: Test\n- Why: test.\n", encoding="utf-8")

    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )
    assert ok is True
    assert missing == []

    (run_dir / "final-summary.md").write_text("## /design run RUN1: approved\n\n", encoding="utf-8")
    (repo / "ARCHITECTURAL_GUIDELINES.md").unlink()
    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )
    assert ok is True
    assert missing == []

    (repo / "ARCHITECTURAL_GUIDELINES.md").mkdir()
    ok, missing = run_log_manifest.verify_run_log_completeness(
        run_dir=run_dir,
        skill="design",
        repo_root=repo,
    )
    assert ok is True
    assert missing == []


def test_archive_prep_completeness_uses_consumer_repo_root_for_guidelines(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ARCHITECTURAL_GUIDELINES.md").write_text("### G-Test-1: Test\n- Why: test.\n", encoding="utf-8")
    log_root = tmp_path / "session" / "larch-logs"
    run_dir = log_root / "design" / "RUN1"
    _write_run_manifest(run_dir, skill="design")
    (run_dir / "final-summary.md").write_text("## /design run RUN1: approved\n\n", encoding="utf-8")
    (run_dir / "session-transcript.jsonl").write_text('{"type":"message"}\n', encoding="utf-8")

    with pytest.raises(ShipError) as excinfo:
        _ = run_log_commit.prepare_run_for_archive(
            log_root=log_root,
            repo_root=repo,
            skill="design",
            run_id="RUN1",
        )

    assert str(excinfo.value) == "run-log incomplete: guideline-assessment:architectural-guideline-assessment.md"


def test_design_completed_step3_without_plan_review_does_not_reach_round_requirements(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "design" / "RUN1"
    _write_run_manifest(run_dir, skill="design")
    completed = run_dir / ".completed"
    completed.mkdir()
    _ = (completed / "step-3").write_text("", encoding="utf-8")

    ok, missing = run_log_manifest.verify_run_log_completeness(run_dir=run_dir, skill="design")

    assert not run_log_manifest._design_plan_review_reached(run_dir)  # pyright: ignore[reportPrivateUsage]
    assert ok is True
    assert missing == []


def test_refresh_run_logs_main_skips_without_state_file(tmp_path: Path) -> None:
    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_log_flush.refresh_run_logs_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    assert f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_STATE_FILE_MISSING}" in buf.getvalue()


def test_capture_transcript_main_missing_source(tmp_path: Path) -> None:
    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_log_flush.capture_transcript_main(
            [
                "--source-file",
                str(tmp_path / "missing.txt"),
                "--log-root",
                str(tmp_path / "larch-logs"),
                "--skill",
                "implement",
                "--run-id",
                "RUN1",
                "--no-logs-commit",
                "true",
            ],
        )
    assert rc == 0
    assert "SESSION_TRANSCRIPT_STATUS=source-file-missing" in buf.getvalue()


def test_capture_transcript_main_rejects_invalid_run_id_before_path_lookup(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside" / "session-transcript.jsonl"
    outside.parent.mkdir(parents=True)
    _ = outside.write_text('{"type":"message"}\n', encoding="utf-8")
    issues_log = tmp_path / "execution-issues.md"
    _ = issues_log.write_text("", encoding="utf-8")

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_log_flush.capture_transcript_main(
            [
                "--source-file",
                str(tmp_path / "missing.txt"),
                "--log-root",
                str(tmp_path / "larch-logs"),
                "--tmpdir",
                str(tmp_path),
                "--skill",
                "implement",
                "--run-id",
                "../../../outside",
                "--no-logs-commit",
                "true",
                "--refresh-mode",
                "true",
                "--execution-issues-log",
                str(issues_log),
            ],
        )
    assert rc == 0
    captured = buf.getvalue()
    assert "SESSION_TRANSCRIPT_STATUS=invalid-run-id" in captured
    assert "source-file-missing" not in captured
    assert outside.read_text(encoding="utf-8") == '{"type":"message"}\n'


def test_capture_transcript_main_defer_commit_no_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """defer_commit=true success path must not append a Warnings entry."""
    transcript = tmp_path / "transcript.jsonl"
    _ = transcript.write_text('{"type":"message"}\n', encoding="utf-8")
    source = tmp_path / "source.txt"
    _ = source.write_text(f"TRANSCRIPT_PATH={transcript}\n", encoding="utf-8")
    log_root = tmp_path / "larch-logs"
    issues_log = tmp_path / "execution-issues.md"
    _ = issues_log.write_text("", encoding="utf-8")

    def _fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        for i, arg in enumerate(args):
            if arg == "--output" and i + 1 < len(args):
                _ = Path(args[i + 1]).write_text('{"type":"stub"}\n', encoding="utf-8")
                break
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(run_log_batch.proc, "run", _fake_run)  # type: ignore[attr-defined]

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_log_flush.capture_transcript_main(
            [
                "--source-file",
                str(source),
                "--log-root",
                str(log_root),
                "--tmpdir",
                str(tmp_path),
                "--skill",
                "implement",
                "--run-id",
                "RUN1",
                "--no-logs-commit",
                "false",
                "--execution-issues-log",
                str(issues_log),
                "--defer-commit",
                "true",
            ]
        )
    assert rc == 0
    assert "SESSION_TRANSCRIPT_STATUS=captured" in buf.getvalue()
    assert "session transcript was written; commit deferred" not in issues_log.read_text(encoding="utf-8")


def test_capture_transcript_main_stages_preterminal_stalled_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transcript = tmp_path / "transcript.jsonl"
    _ = transcript.write_text('{"type":"message"}\n', encoding="utf-8")
    source = tmp_path / "source.txt"
    _ = source.write_text(f"TRANSCRIPT_PATH={transcript}\n", encoding="utf-8")
    log_root = tmp_path / "larch-logs"
    issues_log = tmp_path / "execution-issues.md"
    _ = issues_log.write_text("", encoding="utf-8")
    run_dir = log_root / "implement" / "run-1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "final-summary.md").write_text("## /implement final summary: stalled\n", encoding="utf-8")

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        output = Path(args[args.index("--output") + 1])
        _ = output.write_text('{"type":"stub"}\n', encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    def fake_write_batch(
        *,
        log_root: Path,
        skill: str,
        run_id: str,
        batch: str,
        input_file: str,
    ) -> tuple[Path, bool, bool]:
        target = log_root / skill / run_id / f"{batch}.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(Path(input_file).read_text(encoding="utf-8"), encoding="utf-8")
        return target, True, False

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.setattr(run_log_flush, "_write_batch", fake_write_batch)

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_log_flush.capture_transcript_main(
            [
                "--source-file",
                str(source),
                "--log-root",
                str(log_root),
                "--tmpdir",
                str(tmp_path),
                "--skill",
                "implement",
                "--run-id",
                "run-1",
                "--no-logs-commit",
                "false",
                "--execution-issues-log",
                str(issues_log),
            ]
        )

    assert rc == 0
    captured = buf.getvalue()
    assert "SESSION_TRANSCRIPT_STATUS=captured" in captured
    assert "pre-terminal" not in issues_log.read_text(encoding="utf-8")


def test_capture_transcript_main_uses_explicit_tmpdir_for_render_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system_tmp = tmp_path / "system-tmp"
    scratch_tmp = tmp_path / "scratch-tmp"
    system_tmp.mkdir()
    scratch_tmp.mkdir()
    monkeypatch.setattr(run_log_flush.tempfile, "tempdir", str(system_tmp))
    transcript = tmp_path / "transcript.jsonl"
    _ = transcript.write_text('{"type":"message"}\n', encoding="utf-8")
    source = tmp_path / "source.txt"
    _ = source.write_text(f"TRANSCRIPT_PATH={transcript}\n", encoding="utf-8")
    log_root = tmp_path / "larch-logs"
    rendered_payload = '{"type":"stub"}\n'

    def _fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args and args[0] == "git" and "rev-parse" in args and "--show-toplevel" in args:
            return subprocess.CompletedProcess(args, 0, stdout=f"{tmp_path.parent / 'repo-root'}\n", stderr="")
        if "--output" not in args:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        output = Path(args[args.index("--output") + 1])
        assert output.is_relative_to(scratch_tmp)
        assert not output.is_relative_to(system_tmp)
        _ = output.write_text(rendered_payload, encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_log_flush.capture_transcript_main(
            [
                "--source-file",
                str(source),
                "--log-root",
                str(log_root),
                "--tmpdir",
                str(scratch_tmp),
                "--skill",
                "implement",
                "--run-id",
                "RUN1",
                "--defer-commit",
                "true",
            ]
        )

    captured = buf.getvalue()
    committed = log_root / "implement" / "RUN1" / "session-transcript.jsonl"
    assert rc == 0
    assert "SESSION_TRANSCRIPT_STATUS=captured" in captured
    assert "write-failed" not in captured
    assert committed.read_text(encoding="utf-8") == rendered_payload


def test_init_run_writes_manifest_v2(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _ = run_log_manifest.init_run(ctx, run_id="run-abc")
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 2
    assert data["skill"] == "implement"


def test_manifest_v2_round_trip_preserves_reserved_and_extension_bytes() -> None:
    original = {
        "schema_version": 2,
        "skill": "implement",
        "run_id": "run-1",
        "operator_cwd": "<OPERATOR_CWD>",
        "operator_repo_root": "<REPO_ROOT>",
        "parent_skill": None,
        "issue_number": 42,
        "larch_version": "1.2.3",
        "model_roster": {"main": "model"},
        "effort": "unknown",
        "started_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "attempt": 1,
        "superseded_by": None,
        "stalled_at_step": "5",
        "steps_ran": {"step5": True},
        "flags": {"merge": True},
        "status": "partial",
        "pr_number": 9,
        "extension_key": "kept",
    }

    manifest = run_log_manifest.Manifest.from_json(original)
    rendered = manifest.to_json(existing=original)

    assert rendered == original
    text = json.dumps(rendered, indent=2, sort_keys=True) + "\n"
    assert '"created_at"' not in text
    assert '"version"' not in text
    assert manifest.reserved["stalled_at_step"] == "5"
    assert manifest.extra == {"extension_key": "kept"}


def test_update_manifest_routes_reserved_keys_to_top_level(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _ = run_log_manifest.init_run(ctx, run_id="run-abc")

    updated = run_log_manifest.update_manifest(ctx, stalled_at_step="7", pr_number=123, custom_extension="yes")

    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["stalled_at_step"] == "7"
    assert data["pr_number"] == 123
    assert data["custom_extension"] == "yes"
    assert updated.reserved["stalled_at_step"] == "7"
    assert updated.reserved["pr_number"] == 123
    assert updated.extra == {"custom_extension": "yes"}


def test_manifest_v2_registry_keeps_parse_and_emit_filters_distinct() -> None:
    original: dict[str, Any] = {
        "schema_version": 2,
        "status": "partial",
        "skill": "implement",
        "run_id": "run-1",
        "steps_ran": {},
        "started_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "stalled_at_step": "old",
    }

    manifest = run_log_manifest.Manifest.from_json(original)
    assert manifest.extra is None
    promoted = run_log_manifest.Manifest(
        status=manifest.status,
        version=manifest.version,
        run_id=manifest.run_id,
        steps_ran=manifest.steps_ran,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
        extra={"stalled_at_step": "new"},
        reserved={},
    ).to_json(existing=original)

    assert promoted["stalled_at_step"] == "new"


def test_synthesize_v2_main_model_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE_MODEL", raising=False)
    monkeypatch.setenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    data = run_log_manifest.Manifest.synthesize_v2(skill="implement", run_id="r").to_json(existing=None)
    assert data["model_roster"]["main"] == "claude-sonnet-4-6"


def test_synthesize_v2_main_model_from_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE_MODEL", raising=False)
    monkeypatch.delenv("CLAUDE_MODEL", raising=False)
    monkeypatch.setattr(tokens, "read_main_model", lambda: "claude-opus-4-8")
    data = run_log_manifest.Manifest.synthesize_v2(skill="design", run_id="r").to_json(existing=None)
    assert data["model_roster"]["main"] == "claude-opus-4-8"


def test_synthesize_v2_main_model_unknown_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE_MODEL", raising=False)
    monkeypatch.delenv("CLAUDE_MODEL", raising=False)
    monkeypatch.setattr(tokens, "read_main_model", lambda: "")
    data = run_log_manifest.Manifest.synthesize_v2(skill="implement", run_id="r").to_json(existing=None)
    assert data["model_roster"]["main"] == "unknown"


# pyright: reportUnusedCallResult=false
