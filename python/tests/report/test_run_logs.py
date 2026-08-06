"""Tests for run_logs.py."""

# pyright: reportUnusedFunction=false

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from larch.core import rust_runtime
from larch.core import config
from larch import io as larch_io
from larch.report import final_report
from larch.report import run_log_batch, run_log_commit, run_log_manifest, run_logs
from larch.report.run_log_batch import _rebase_under_tmpdir, _write_batch, _append_batch  # pyright: ignore[reportPrivateUsage]
from larch.report import tokens
from larch.errors import ShipError
from larch.core.proc import CommandResult

from test_support import RecordingRunner as _RecordingRunner, RunCall, make_run_context
from tests.support.stall_recovery import frozen_normalized_outcome

if TYPE_CHECKING:
    from larch.core.run_context import RunContext


@pytest.fixture(autouse=True)
def _stub_rust_outcome_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep Python unit tests independent of an installed Rust binary."""
    monkeypatch.setattr(rust_runtime, "normalized_stall_outcome_values", frozen_normalized_outcome)


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




def test_atomic_write_uses_nofollow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: dict[str, Any] = {}

    def fake_atomic_write(_path: Path, _content: str, **kwargs: Any) -> None:
        calls.update(kwargs)

    monkeypatch.setattr(larch_io, "atomic_write", fake_atomic_write)
    run_log_batch._atomic_write(path=tmp_path / "manifest.json", content="{}")  # pyright: ignore[reportPrivateUsage]
    assert calls["prefix"] == ".manifest-"
    assert calls["nofollow"] is True
















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




def test_path_under_repo_rejects_traversal(tmp_path: Path) -> None:
    assert not run_logs.path_under_repo(repo_root=tmp_path, rel_path="../outside")
    assert run_logs.path_under_repo(repo_root=tmp_path, rel_path="docs/plan.md")






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
