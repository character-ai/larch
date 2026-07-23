# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnusedCallResult=false
from __future__ import annotations

import json
import subprocess
import sys
import os
from pathlib import Path

import pytest

from larch.core.proc import CommandResult
from larch.implement import dispatch_bootstrap
from larch.state import bootstrap

from test_support import ROOT as _REPO_ROOT, seed_feature_description, seed_plan


def test_filtered_envelope_allowlist_and_resume_empty_coder() -> None:
    text = "IMPLEMENT_TMPDIR=/tmp/x\nBAD=x\ncoder=\ncoder_fallback=true\nBRANCH_ACTION=create\n"
    out = bootstrap._filtered_envelope(text, resume=True)  # pyright: ignore[reportPrivateUsage]
    assert "IMPLEMENT_TMPDIR=/tmp/x" in out
    assert "BRANCH_ACTION=create" in out
    assert "BAD=" not in out
    assert "coder=\n" not in out


def test_parse_routing_file_first_stdout_fills_missing(tmp_path, capsys) -> None:
    tmpdir = tmp_path / "impl"
    tmpdir.mkdir()
    (tmpdir / "bootstrap-routing.env").write_text("IMPLEMENT_TMPDIR=/file\nBRANCH_NAME=file-branch\n", encoding="utf-8")
    stdout = tmp_path / "stdout.txt"
    stdout.write_text(f"IMPLEMENT_TMPDIR={tmpdir}\nBRANCH_NAME=stdout-branch\nRUN_ID=R1\n", encoding="utf-8")
    rc = bootstrap.parse_routing_main(["--stdout-file", str(stdout), "--tmpdir", str(tmpdir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "BRANCH_NAME=file-branch" in out
    assert "RUN_ID=R1" in out


def test_parse_routing_output_atomic(tmp_path) -> None:
    stdout = tmp_path / "stdout.txt"
    output = tmp_path / "out.env"
    stdout.write_text("IMPLEMENT_TMPDIR=/tmp/impl\nRUN_ID=abc\n", encoding="utf-8")
    assert bootstrap.parse_routing_main(["--stdout-file", str(stdout), "--output", str(output)]) == 0
    assert "RUN_ID=abc" in output.read_text(encoding="utf-8")


def test_write_base_session_env_preserves_claude_source_and_dynamic_keys(tmp_path, monkeypatch) -> None:
    session_env = tmp_path / "session-env.sh"
    session_env.write_text(
        "LARCH_CLAUDE_SOURCE_FILE=/tmp/source.env\n"
        "LARCH_DYNAMIC_ARCHETYPES_MAX=1\n"
        "LARCH_AUTO_MODE=true\n",
        encoding="utf-8",
    )
    calls: list[bootstrap.session_env.WriteEnvParams] = []

    def fake_write_env(params: bootstrap.session_env.WriteEnvParams) -> bootstrap.session_env.WriteEnvResult:
        calls.append(params)
        return bootstrap.session_env.WriteEnvResult(output=Path(params.output), wrote=True)

    monkeypatch.setattr(bootstrap.session_env, "write_env", fake_write_env)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="infra"),
        implement_tmpdir=str(tmp_path),
        repo="owner/repo",
        repo_unavailable="false",
        session_id="sid",
        claude_binary_found="true",
    )
    bootstrap._write_base_session_env(st)  # pyright: ignore[reportPrivateUsage]
    write_env = next(call for call in calls if not call.plugin_root_only)
    assert write_env.claude_source_file == "/tmp/source.env"
    assert write_env.dynamic_archetypes == "1"
    assert write_env.auto_mode == "true"
    assert write_env.claude_binary_found == "true"


def test_write_claude_source_snapshot_does_not_inject_larch_session_id(tmp_path, monkeypatch) -> None:
    source = bootstrap.tokens.ClaudeSourceResult(
        transcript_path=Path("/tmp/transcript.jsonl"), session_dir=Path("/tmp/session"),
        session_uuid="claude-session",
    )
    monkeypatch.setattr(bootstrap.tokens, "token_claude_source", lambda: source)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="infra"),
        implement_tmpdir=str(tmp_path),
        session_id="larch-run-id",
    )

    bootstrap._write_claude_source_snapshot(st)  # pyright: ignore[reportPrivateUsage]

    assert (tmp_path / "claude-source.env").is_file()


def test_write_larch_run_sh_dispatches_shell_and_python_targets(tmp_path) -> None:
    assert bootstrap._write_larch_run_sh(str(tmp_path))  # pyright: ignore[reportPrivateUsage]
    launcher = tmp_path / "larch-run.sh"
    text = launcher.read_text(encoding="utf-8")
    assert launcher.stat().st_mode & 0o111
    assert "_larch_cleanup_active_leg()" in text
    assert "_larch_active_leg_owner_token=" in text
    assert 'export LARCH_ACTIVE_LEG_OWNER_TOKEN="$_larch_active_leg_owner_token"' in text
    assert "trap _larch_cleanup_active_leg EXIT INT TERM" in text
    assert 'python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@"' in text
    assert 'implement kill-active-leg --owner-token "$_larch_active_leg_owner_token" --implement-tmpdir' in text
    assert 'kill-active-leg --implement-tmpdir "$IMPLEMENT_TMPDIR" 2>/dev/null' not in text
    assert "*.py) exec python3" not in text
    assert '*.sh) exec "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;' in text
    assert "/*|*..*)" in text


def test_install_statusline_best_effort_relays_notice(monkeypatch, capsys) -> None:
    calls: list[tuple[Path, Path, bool]] = []

    def fake_install(*, plugin_root: Path, repo_root: Path, notice: bool) -> bootstrap.statusline_install.StatuslineInstallResult:
        calls.append((plugin_root, repo_root, notice))
        print("larch: installed progress statusline (set LARCH_STATUSLINE_DISABLE=1 to opt out)")
        return bootstrap.statusline_install.StatuslineInstallResult(installed=True)

    monkeypatch.setattr(bootstrap.statusline_install, "install_statusline", fake_install)

    bootstrap._install_statusline_best_effort()  # pyright: ignore[reportPrivateUsage]

    out = capsys.readouterr().out
    assert "installed progress statusline" in out
    assert calls[0][2] is True


def test_invoke_main_resume_recovers_implement_tmpdir_from_pointer(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    pointer = home / ".cache" / "larch" / "sessions" / "current-implement-env-123.sh"
    pointer.parent.mkdir(parents=True)
    pointer.write_text("IMPLEMENT_TMPDIR=/tmp/impl\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LARCH_CLAUDE_PID", "123")
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    seen: dict[str, object] = {}

    def fake_run_bootstrap(opts):
        seen["resume_plan_tail"] = opts.resume_plan_tail
        print("IMPLEMENT_TMPDIR=/tmp/impl\n")
        return 0

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)

    rc = bootstrap.invoke_main(["--mode", "resume"])

    assert rc == 0
    assert seen["resume_plan_tail"] is True
    assert os.environ["IMPLEMENT_TMPDIR"] == "/tmp/impl"


def test_tracking_adoption_empty_run_id_stalls_without_side_effects(tmp_path, monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(
        bootstrap.issue_query, "issue_state",
        lambda *_args, **_kwargs: bootstrap.issue_query.IssueState(state="OPEN", url="", is_pr=False),
    )
    monkeypatch.setattr(bootstrap.run_logs, "log_init", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(bootstrap.dirty_tree, "checkpoint", lambda: ["STATUS=clean", "MODE=checkpoint"])
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="tracking", issue_number="7"),
        implement_tmpdir=str(tmp_path),
        repo="owner/repo",
        repo_unavailable="false",
    )
    bootstrap._phase_tracking(st)  # pyright: ignore[reportPrivateUsage]
    assert st.implement_bail_reason == "tracking-init-failed"
    assert st.stall_tracking == "true"
    assert not calls


def test_tracking_bails_with_dirty_tree_before_rename(tmp_path, monkeypatch) -> None:
    rename_called = [False]

    def fake_rename(*_args: object, **_kwargs: object) -> None:
        rename_called[0] = True
    monkeypatch.setattr(
        bootstrap.issue_query, "issue_state",
        lambda *_args, **_kwargs: bootstrap.issue_query.IssueState(state="OPEN", url="", is_pr=False),
    )
    monkeypatch.setattr(bootstrap.tracking_issue, "rename_with_details", fake_rename)
    monkeypatch.setattr(bootstrap.dirty_tree, "checkpoint", lambda: ["STATUS=dirty", "MODE=checkpoint"])
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="tracking", issue_number="7"),
        implement_tmpdir=str(tmp_path),
        repo="owner/repo",
        repo_unavailable="false",
    )
    bootstrap._phase_tracking(st)  # pyright: ignore[reportPrivateUsage]
    assert st.implement_bail_reason == "dirty-tree"
    assert not rename_called[0]


def test_tracking_helper_failure_stalls_before_sentinel(tmp_path, monkeypatch) -> None:
    post_called = [False]

    def fake_post(*_args: object, **_kwargs: object) -> None:
        post_called[0] = True

    def fail_init(**_kwargs: object) -> object:
        raise OSError("boom")

    monkeypatch.setattr(bootstrap.run_logs, "log_init", fail_init)
    monkeypatch.setattr(bootstrap.pr_body, "post_tracking_issue", fake_post)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="tracking", issue_number="7"),
        implement_tmpdir=str(tmp_path),
        repo="owner/repo",
        repo_unavailable="false",
        issue_number_resolved="7",
        run_id="RUN1",
    )
    assert not bootstrap._perform_tracking_side_effects(st, write_sentinel=True)  # pyright: ignore[reportPrivateUsage]
    assert st.implement_bail_reason == "tracking-init-failed"
    assert st.stall_tracking == "true"
    assert not post_called[0]
    assert not (tmp_path / "parent-issue.md").exists()


def test_tracking_parent_sentinel_requires_explicit_issue_number(tmp_path, capsys) -> None:
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=7\nRUN_ID=R1\nADOPTED=true\n", encoding="utf-8")
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="tracking"),
        implement_tmpdir=str(tmp_path),
        repo="owner/repo",
        repo_unavailable="false",
    )
    with pytest.raises(bootstrap.BootstrapExit) as exc_info:
        bootstrap._phase_tracking(st)  # pyright: ignore[reportPrivateUsage]
    assert exc_info.value.code == 2
    assert "STEP_FAILED=issue-number-required-for-resume" in capsys.readouterr().out


def test_resume_plan_tail_matching_sentinel_skips_tracking_side_effects(tmp_path) -> None:
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=7\nRUN_ID=R1\nADOPTED=true\n", encoding="utf-8")
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", resume_plan_tail=True),
        implement_tmpdir=str(tmp_path),
        repo="owner/repo",
        repo_unavailable="false",
    )
    bootstrap._phase_tracking(st)  # pyright: ignore[reportPrivateUsage]
    assert st.branch_selected == "branch-1-resume"
    assert st.issue_number_resolved == "7"
    assert st.run_id == "R1"


def test_force_bypass_validates_issue_and_consumes_invalid_log(tmp_path, monkeypatch) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    (preflight / "force-bypass.log").write_text("BYPASS kind=missing-plan issue=99\n", encoding="utf-8")
    calls: list[dict[str, object]] = []

    def fake_append_failure(**kwargs: object) -> Path:
        calls.append(kwargs)
        return impl / "failure.md"

    monkeypatch.setattr(bootstrap.run_logs, "log_append_failure", fake_append_failure)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", force_requested="true", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(impl),
    )
    assert bootstrap._append_force_bypass(st)  # pyright: ignore[reportPrivateUsage]
    assert (impl / ".force-bypass-log-consumed").exists()
    assert calls[0]["exit_code"] == "99"
    assert calls[0]["status_label"] == "invalid-format"


def test_force_bypass_valid_bypass_makes_no_run_log_write(tmp_path, monkeypatch) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    (preflight / "force-bypass.log").write_text("BYPASS kind=missing-designed-prefix issue=7\n", encoding="utf-8")
    def unexpected_append_failure(**_kwargs: object) -> Path:
        raise AssertionError("valid bypasses are intentional; no warning is logged")

    monkeypatch.setattr(bootstrap.run_logs, "log_append_failure", unexpected_append_failure)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", force_requested="true", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(impl),
    )
    assert bootstrap._append_force_bypass(st)  # pyright: ignore[reportPrivateUsage]
    assert (impl / ".force-bypass-log-consumed").exists()


def test_resume_plan_tail_appends_force_bypass_before_flags(tmp_path, monkeypatch) -> None:
    order: list[str] = []
    monkeypatch.setattr(bootstrap, "_append_force_bypass", lambda _st: order.append("bypass") or True)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_persist_run_flags", lambda _st: order.append("flags") or True)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap.dirty_tree, "checkpoint", lambda: ["STATUS=clean", "MODE=checkpoint"])
    monkeypatch.setattr(bootstrap, "_publish_plan_review_tally", lambda _st: None)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_upsert_plan_summary", lambda _st: None)  # pyright: ignore[reportPrivateUsage]
    _ = seed_feature_description(tmp_path, "Title\n")
    _ = seed_plan(tmp_path, "Plan\n")
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", resume_plan_tail=True),
        implement_tmpdir=str(tmp_path),
        branch_name="feature",
        plan_file=str(tmp_path / "plan.txt"),
    )
    bootstrap._phase_plan(st)  # pyright: ignore[reportPrivateUsage]
    assert order[:2] == ["bypass", "flags"]


def test_main_health_env_copied_from_preflight(tmp_path: Path) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    _ = (preflight / "main-health.env").write_text(
        "MAIN_CI_STATUS=fail\nMAIN_FAILED_RUN_ID=7\nMAIN_HEALTH_HEAD_SHA=abc\nMAIN_HEALTH_DETAIL=red main\n",
        encoding="utf-8",
    )
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(impl),
    )

    bootstrap._materialize_main_health_env(st)  # pyright: ignore[reportPrivateUsage]

    assert (impl / "main-health.env").read_text(encoding="utf-8") == (
        "MAIN_CI_STATUS=fail\nMAIN_FAILED_RUN_ID=7\nMAIN_HEALTH_HEAD_SHA=abc\nMAIN_HEALTH_DETAIL=red main\n"
    )


def test_main_health_env_preserved_on_resume_without_preflight_refresh(tmp_path: Path) -> None:
    impl = tmp_path / "impl"
    impl.mkdir()
    _ = (impl / "main-health.env").write_text("MAIN_CI_STATUS=fail\n", encoding="utf-8")
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", resume_plan_tail=True),
        implement_tmpdir=str(impl),
    )

    bootstrap._materialize_main_health_env(st)  # pyright: ignore[reportPrivateUsage]

    assert (impl / "main-health.env").read_text(encoding="utf-8") == "MAIN_CI_STATUS=fail\n"


def test_resume_plan_tail_stops_after_run_flags_failure(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(bootstrap, "_append_force_bypass", lambda _st: True)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_persist_run_flags", lambda st: setattr(st, "implement_bail_reason", "run-flags-persist-failed") or False)  # pyright: ignore[reportPrivateUsage]

    def dirty_checkpoint() -> list[str]:
        raise AssertionError("dirty checkpoint should not run after run flag persistence failure")

    monkeypatch.setattr(bootstrap.dirty_tree, "checkpoint", dirty_checkpoint)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", resume_plan_tail=True),
        implement_tmpdir=str(tmp_path),
    )
    bootstrap._phase_plan(st)  # pyright: ignore[reportPrivateUsage]
    assert st.implement_bail_reason == "run-flags-persist-failed"


def test_publish_plan_review_tally_emits_stub_when_no_candidate(tmp_path, monkeypatch) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    calls: list[dict[str, object]] = []

    def fake_log_write(**kwargs: object) -> Path:
        calls.append(kwargs)
        return impl / "larch-logs" / "manifest.json"

    monkeypatch.setattr(bootstrap.run_logs, "log_write", fake_log_write)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(impl),
        run_id="RUNID0001",
    )
    bootstrap._publish_plan_review_tally(st)  # pyright: ignore[reportPrivateUsage]

    assert len(calls) == 1
    source = Path(str(calls[0]["input_file"]))
    assert source.is_file()
    record = json.loads(source.read_text(encoding="utf-8"))
    assert record["phase"] == "plan-review"
    assert record["batch"] == "plan-review-tally"
    assert record["accepted_count"] == 0
    assert record["rejected_count"] == 0
    assert "/design" in record["body"]


def test_publish_plan_review_tally_prefers_existing_candidate(tmp_path, monkeypatch) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    tally = preflight / "plan-review-tally.json"
    tally.write_text('{"schema_version":2,"phase":"plan-review"}', encoding="utf-8")
    calls: list[dict[str, object]] = []

    def fake_log_write(**kwargs: object) -> Path:
        calls.append(kwargs)
        return impl / "larch-logs" / "manifest.json"

    monkeypatch.setattr(bootstrap.run_logs, "log_write", fake_log_write)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(impl),
        run_id="RUNID0002",
    )
    bootstrap._publish_plan_review_tally(st)  # pyright: ignore[reportPrivateUsage]

    assert len(calls) == 1
    source = Path(str(calls[0]["input_file"]))
    assert source == tally
    assert not (impl / "plan-review-tally-stub.json").exists()


def test_plan_stops_after_run_flags_failure(tmp_path, monkeypatch) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    (preflight / "plan-from-issue.txt").write_text("plan", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "_append_force_bypass", lambda _st: True)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_persist_run_flags", lambda st: setattr(st, "implement_bail_reason", "run-flags-persist-failed") or False)  # pyright: ignore[reportPrivateUsage]

    def fake_view(_runner, issue, fields, template, *, repo=None, cwd=None):
        _ = issue, fields, template, repo, cwd
        return CommandResult(("gh",), 0, "Title\n\nBody\n", "", 0.01)

    monkeypatch.setattr(bootstrap.gh, "issue_view_template_read", fake_view)

    def dirty_checkpoint() -> list[str]:
        raise AssertionError("dirty checkpoint should not run after run flag persistence failure")

    monkeypatch.setattr(bootstrap.dirty_tree, "checkpoint", dirty_checkpoint)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(impl),
        issue_number_resolved="7",
    )
    bootstrap._phase_plan(st)  # pyright: ignore[reportPrivateUsage]
    assert st.implement_bail_reason == "run-flags-persist-failed"


def test_plan_materialization_strips_only_terminal_design_provenance(tmp_path, monkeypatch) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    source_text = (
        "## Plan\n\n"
        "review_status: prose survives\n"
        "rounds_completed: prose survives\n\n"
        "```text\n"
        "review_status: fenced survives\n"
        "rounds_completed: fenced survives\n"
        "```\n\n"
        "review_status: complete\n"
        "rounds_completed: 5\n"
        "diff_added: 10\n"
        "diff_deleted: 2\n"
        "mechanical_churn: false\n"
        "diff_lines: 10\n"
    )
    plan_src = preflight / "plan-from-issue.txt"
    plan_src.write_text(source_text, encoding="utf-8")
    monkeypatch.setattr(bootstrap.dirty_tree, "checkpoint", lambda: ["STATUS=clean", "MODE=checkpoint"])
    monkeypatch.setattr(bootstrap, "_append_force_bypass", lambda _st: True)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_persist_run_flags", lambda _st: True)  # pyright: ignore[reportPrivateUsage]

    def fake_view(_runner, issue, fields, template, *, repo=None, cwd=None):
        _ = issue, fields, template, repo, cwd
        return CommandResult(("gh",), 0, "Title\n\nBody\n", "", 0.01)

    monkeypatch.setattr(bootstrap.gh, "issue_view_template_read", fake_view)

    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(impl),
        issue_number_resolved="7",
        is_user_branch="true",
    )
    bootstrap._phase_plan(st)  # pyright: ignore[reportPrivateUsage]

    materialized = (impl / "plan.txt").read_text(encoding="utf-8")
    assert "review_status: prose survives" in materialized
    assert "rounds_completed: prose survives" in materialized
    assert "review_status: fenced survives" in materialized
    assert "rounds_completed: fenced survives" in materialized
    assert "review_status: complete" not in materialized
    assert "rounds_completed: 5" not in materialized
    assert "diff_added: 10" in materialized
    assert "diff_deleted: 2" in materialized
    assert "mechanical_churn: false" in materialized
    assert "diff_lines: 10" in materialized
    assert plan_src.read_text(encoding="utf-8") == source_text


def test_strip_plan_provenance_headers_skips_prose_above_size_trailers() -> None:
    source = (
        "## Plan\n\n"
        "review_status: prose survives\n"
        "rounds_completed: prose survives\n"
        "diff_added: 10\n"
        "diff_deleted: 2\n"
        "mechanical_churn: false\n"
        "review_status: complete\n"
        "rounds_completed: 5\n"
        "diff_lines: 10\n"
    )
    result = bootstrap._strip_plan_provenance_headers(source)  # pyright: ignore[reportPrivateUsage]
    assert "review_status: prose survives" in result
    assert "rounds_completed: prose survives" in result
    assert "review_status: complete" not in result
    assert "rounds_completed: 5" not in result


def test_strip_plan_provenance_headers_requires_terminal_trailers() -> None:
    source = "review_status: complete\nrounds_completed: 2\ndiff_lines: 1\ntrailing prose\n"
    assert bootstrap._strip_plan_provenance_headers(source) == source  # pyright: ignore[reportPrivateUsage]


def test_forked_plan_requires_upstream_repo_before_gh(tmp_path, monkeypatch) -> None:
    preflight = tmp_path / "preflight"
    preflight.mkdir()
    (preflight / "plan-from-issue.txt").write_text("plan", encoding="utf-8")
    monkeypatch.setattr(bootstrap.dirty_tree, "checkpoint", lambda: ["STATUS=clean", "MODE=checkpoint"])
    monkeypatch.setattr(bootstrap, "_append_force_bypass", lambda _st: True)  # pyright: ignore[reportPrivateUsage]

    def unexpected_issue_view(*_args: object, **_kwargs: object) -> CommandResult:
        raise AssertionError("forked-plan validation must fail before reading the issue")

    monkeypatch.setattr(bootstrap.gh, "issue_view_template_read", unexpected_issue_view)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", forked_target="true", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(tmp_path),
        issue_number_resolved="7",
    )
    with pytest.raises(bootstrap.BootstrapExit) as exc_info:
        bootstrap._phase_plan(st)  # pyright: ignore[reportPrivateUsage]
    assert exc_info.value.code == 2
    assert st.implement_bail_reason == ""


def test_phase_plan_materializes_feature_description_via_template_wrapper(tmp_path, monkeypatch) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    (preflight / "plan-from-issue.txt").write_text("plan body\ndiff_lines: 1\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_view(_runner, issue, fields, template, *, repo=None, cwd=None):
        captured["issue"] = issue
        captured["fields"] = fields
        captured["template"] = template
        captured["repo"] = repo
        _ = cwd
        return CommandResult(("gh",), 0, "Feature Title\n\nFeature body\n", "", 0.01)

    monkeypatch.setattr(bootstrap.gh, "issue_view_template_read", fake_view)
    monkeypatch.setattr(bootstrap, "_append_force_bypass", lambda _st: True)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_persist_run_flags", lambda _st: True)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap.dirty_tree, "checkpoint", lambda: ["STATUS=clean", "MODE=checkpoint"])

    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(
            up_to_phase="plan",
            issue_number="42",
            forked_target="true",
            upstream_repo="upstream/repo",
            preflight_tmpdir=str(preflight),
        ),
        implement_tmpdir=str(impl),
        issue_number_resolved="42",
        is_user_branch="true",
    )
    bootstrap._phase_plan(st)  # pyright: ignore[reportPrivateUsage]

    assert captured["issue"] == "42"
    assert captured["fields"] == "title,body"
    assert captured["template"] == "{{.title}}\n\n{{.body}}"
    assert captured["repo"] == "upstream/repo"
    assert (impl / "feature-description.txt").read_text(encoding="utf-8") == "Feature Title\n\nFeature body\n"


def test_phase_plan_issue_view_failure_preserves_stderr_artifact(tmp_path, monkeypatch, capsys) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    (preflight / "plan-from-issue.txt").write_text("plan\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "_append_force_bypass", lambda _st: True)  # pyright: ignore[reportPrivateUsage]

    def failed_view(_runner, _issue, _fields, _template, *, repo=None, cwd=None):
        _ = repo, cwd
        return CommandResult(("gh",), 1, "", "wrapper stderr\n", 0.01)

    monkeypatch.setattr(bootstrap.gh, "issue_view_template_read", failed_view)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="42", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(impl),
        issue_number_resolved="42",
    )

    with pytest.raises(bootstrap.BootstrapExit) as exc_info:
        bootstrap._phase_plan(st)  # pyright: ignore[reportPrivateUsage]

    assert exc_info.value.code == 2
    assert (impl / "gh-issue-view.stderr.log").read_text(encoding="utf-8") == "wrapper stderr\n"
    assert "STEP_FAILED=gh-issue-view" in capsys.readouterr().out


def test_run_bootstrap_unexpected_exception_emits_structured_failure(monkeypatch, capsys) -> None:
    def boom(_st):
        raise OSError("boom")

    monkeypatch.setattr(bootstrap, "_phase_infra", boom)  # pyright: ignore[reportPrivateUsage]
    rc = bootstrap.run_bootstrap(bootstrap.BootstrapOptions(up_to_phase="infra"))
    assert rc == 2
    assert "STEP_FAILED=internal-error" in capsys.readouterr().out


def test_invoke_rejects_invalid_boolean_cli_value(capsys) -> None:
    rc = bootstrap.invoke_main(["--mode", "initial", "--forked-target", "tru"])
    assert rc == 1
    assert "invalid choice" in capsys.readouterr().err


def test_cli_bootstrap_invoke_rejects_invalid_boolean_value() -> None:
    result = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "python" / "cli.py"), "bootstrap", "invoke", "--mode", "initial", "--forked-target", "tru"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        check=False,
    )
    assert result.returncode == 1
    assert "invalid choice" in result.stderr


def test_step0_wrapper_rejects_invalid_boolean_value() -> None:
    result = subprocess.run(
        ["bash", str(_REPO_ROOT / "skills" / "implement" / "scripts" / "step-0-bootstrap.sh"), "--mode", "initial", "--forked-target", "tru"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        check=False,
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(_REPO_ROOT)},
    )
    assert result.returncode == 2
    assert "--forked-target must be true or false" in result.stderr or "invalid" in result.stderr.lower() or "true or false" in result.stderr


def test_step0_wrapper_runs_without_non_interactive_flag() -> None:
    script_src = (_REPO_ROOT / "python" / "larch" / "implement" / "dispatch_bootstrap.py").read_text(encoding="utf-8")
    assert "non_interactive" in script_src
    assert "resolve-non-interactive" in script_src


@pytest.mark.parametrize(("no_logs", "expected_calls"), [("false", 2), ("true", 1)])
def test_step0_bootstrap_adopts_lifecycle_unless_logs_are_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_logs: str, expected_calls: int) -> None:
    calls: list[list[str]] = []

    def fake_invoke(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] == ["bootstrap", "invoke"]:
            return subprocess.CompletedProcess(args, 0, f"IMPLEMENT_TMPDIR={tmp_path}\nRUN_ID=run-7887\nISSUE_NUMBER=7887\n", "")
        return subprocess.CompletedProcess(args, 0, "LIFECYCLE_STARTED=true\n", "")

    monkeypatch.setitem(dispatch_bootstrap.__dict__, "_invoke_cli", fake_invoke)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(_REPO_ROOT))
    parent_context = tmp_path / "parent-context.json"
    argv = ["--mode", "initial", "--non-interactive", "true", "--no-logs-commit", no_logs, "--lifecycle-parent-context", str(parent_context)]
    rc = dispatch_bootstrap.step0_bootstrap_main(argv)
    assert rc == 0
    assert len(calls) == expected_calls
    if no_logs == "true":
        return
    lifecycle = calls[1]
    values = tuple(lifecycle[lifecycle.index(flag) + 1] for flag in ("--run-id", "--log-root", "--lifecycle-parent-context"))
    assert (values, "--adopt-existing" in lifecycle) == (("run-7887", str(tmp_path / "larch-logs"), str(parent_context)), True)


def test_invoke_persists_ship_seed_input_flags(tmp_path, monkeypatch) -> None:
    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        print("DEFERRED=true")
        print("PLAN_FILE=/tmp/plan.txt")
        print("STALL_TRACKING=false")
        print("coder=codex")
        return 0

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    monkeypatch.setattr(
        bootstrap,
        "_run_absorbed_continue_tail",
        lambda data, **_kwargs: bootstrap.ContinueTailResult(routing=data, advisory_lines=[]),  # pyright: ignore[reportPrivateUsage]
    )
    rc = bootstrap.invoke_main([
        "--mode", "initial",
        "--merge-requested", "true",
        "--draft-requested", "true",
        "--forked-target", "true",
        "--no-admin-fallback", "true",
        "--no-logs-commit", "true",
    ])
    assert rc == 0
    data = dict(
        line.split("=", 1)
        for line in (tmp_path / "ship-seed-input.env").read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    assert data == {
        "MERGE": "true",
        "DRAFT": "true",
        "FORKED_TARGET": "true",
        "NO_ADMIN_FALLBACK": "true",
        "NO_LOGS_COMMIT": "true",
        "DEFERRED": "true",
        "DIFFICULTY_OVERRIDE": "",
    }


def test_invoke_resume_preserves_existing_ship_seed_context(tmp_path, monkeypatch) -> None:
    (tmp_path / "ship-seed-input.env").write_text("MERGE=true\nMANIFEST_PATH=/tmp/manifest.json\nTOOL_LABEL=Codex\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        print("DEFERRED=false")
        print("PLAN_FILE=/tmp/plan.txt")
        print("STALL_TRACKING=false")
        print("coder=codex")
        return 0

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    monkeypatch.setattr(
        bootstrap,
        "_run_absorbed_continue_tail",
        lambda data, **_kwargs: bootstrap.ContinueTailResult(routing=data, advisory_lines=[]),  # pyright: ignore[reportPrivateUsage]
    )
    assert bootstrap.invoke_main(["--mode", "resume"]) == 0
    data = dict(
        line.split("=", 1)
        for line in (tmp_path / "ship-seed-input.env").read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    assert data["MERGE"] == "true"
    assert data["MANIFEST_PATH"] == "/tmp/manifest.json"
    assert data["TOOL_LABEL"] == "Codex"
    assert data["DRAFT"] == "false"
    assert data["NO_ADMIN_FALLBACK"] == "false"
    assert data["NO_LOGS_COMMIT"] == "false"


def test_invoke_initial_fails_when_ship_seed_input_write_fails(tmp_path, monkeypatch) -> None:
    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        print("DEFERRED=true")
        print("PLAN_FILE=/tmp/plan.txt")
        print("STALL_TRACKING=false")
        print("coder=codex")
        return 0

    def fail_seed_write(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    monkeypatch.setattr(
        bootstrap,
        "_run_absorbed_continue_tail",
        lambda data, **_kwargs: bootstrap.ContinueTailResult(routing=data, advisory_lines=[]),  # pyright: ignore[reportPrivateUsage]
    )
    monkeypatch.setattr(bootstrap, "_merge_write_ship_seed_input", fail_seed_write)
    rc = bootstrap.invoke_main([
        "--mode", "initial",
        "--merge-requested", "true",
        "--draft-requested", "true",
    ])
    assert rc == 2
    assert not (tmp_path / "ship-seed-input.env").exists()


def test_invoke_env_fallback_and_flag_precedence(tmp_path, monkeypatch) -> None:
    captured: list[bootstrap.BootstrapOptions] = []
    monkeypatch.setenv("TARGET_ISSUE_NUMBER", "41")
    monkeypatch.setenv("CALLER_ENV_PATH", "/env/caller")
    monkeypatch.setenv("PREFLIGHT_TMPDIR", "/env/preflight")
    monkeypatch.setenv("forked_target", "true")
    monkeypatch.setenv("UPSTREAM_REPO", "env/upstream")
    monkeypatch.setenv("RUN_ID", "ENV")
    monkeypatch.setenv("force_requested", "true")
    monkeypatch.setenv("self_review", "true")
    monkeypatch.setenv("self_implement", "true")
    monkeypatch.setenv("coder", "cursor")

    def fake_run_bootstrap(opts: bootstrap.BootstrapOptions) -> int:
        captured.append(opts)
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        print("RUN_ID=ARG")
        return 0

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    rc = bootstrap.invoke_main(
        [
            "--mode",
            "initial",
            "--issue-number",
            "7",
            "--caller-env",
            "/arg/caller",
            "--preflight-tmpdir",
            "/arg/preflight",
            "--forked-target",
            "false",
            "--upstream-repo",
            "arg/upstream",
            "--run-id",
            "ARG",
            "--force-requested",
            "false",
            "--self-review-requested",
            "false",
            "--self-implement-requested",
            "false",
            "--coder",
            "codex",
        ],
    )
    assert rc == 0
    opts = captured[0]
    assert opts.issue_number == "7"
    assert opts.caller_env == "/arg/caller"
    assert opts.preflight_tmpdir == "/arg/preflight"
    assert opts.forked_target == "false"
    assert opts.upstream_repo == "arg/upstream"
    assert opts.run_id == "ARG"
    assert opts.force_requested == "false"
    assert opts.self_review_requested == "false"
    assert opts.self_implement_requested == "false"
    assert opts.coder_opt == "codex"


def test_invoke_env_fallback_used_when_flags_omitted(tmp_path, monkeypatch) -> None:
    captured: list[bootstrap.BootstrapOptions] = []
    monkeypatch.setenv("TARGET_ISSUE_NUMBER", "41")
    monkeypatch.setenv("CALLER_ENV_PATH", "/env/caller")
    monkeypatch.setenv("PREFLIGHT_TMPDIR", "/env/preflight")
    monkeypatch.setenv("forked_target", "true")
    monkeypatch.setenv("UPSTREAM_REPO", "env/upstream")
    monkeypatch.setenv("RUN_ID", "ENV")
    monkeypatch.setenv("force_requested", "true")
    monkeypatch.setenv("self_review", "true")
    monkeypatch.setenv("self_implement", "true")
    monkeypatch.setenv("coder", "cursor")

    def fake_run_bootstrap(opts: bootstrap.BootstrapOptions) -> int:
        captured.append(opts)
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        return 0

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    assert bootstrap.invoke_main(["--mode", "initial"]) == 0
    opts = captured[0]
    assert opts.issue_number == "41"
    assert opts.caller_env == "/env/caller"
    assert opts.preflight_tmpdir == "/env/preflight"
    assert opts.forked_target == "true"
    assert opts.upstream_repo == "env/upstream"
    assert opts.run_id == "ENV"
    assert opts.force_requested == "true"
    assert opts.self_review_requested == "true"
    assert opts.self_implement_requested == "true"
    assert opts.coder_opt == "cursor"


def test_invoke_contract_failure_maps_to_exit_2(monkeypatch) -> None:
    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print("STEP_FAILED=copy-plan")
        print("IMPLEMENT_TMPDIR=")
        return bootstrap.BOOTSTRAP_CONTRACT_FAILURE

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    assert bootstrap.invoke_main(["--mode", "initial"]) == 2


def test_invoke_contract_failure_leaves_stdout_empty(monkeypatch, capsys) -> None:
    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print("STEP_FAILED=session-setup")
        return bootstrap.BOOTSTRAP_CONTRACT_FAILURE

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    assert bootstrap.invoke_main(["--mode", "initial"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "STEP_FAILED=session-setup" in captured.err


def test_invoke_error_session_setup_mentions_stash_recovery(capsys) -> None:
    bootstrap._invoke_error(  # pyright: ignore[reportPrivateUsage]
        step_failed="session-setup",
        out="STEP_FAILED=session-setup\nPREFLIGHT_ERROR=Git stash is not empty\n",
        implement_tmpdir="",
    )
    err = capsys.readouterr().err
    assert "PREFLIGHT_ERROR=Git stash is not empty" in err
    assert "git stash pop" in err
    assert "git stash drop" in err
    assert "stash cleanliness still applies on feature branches" in err


def test_invoke_routing_write_failure_preserves_stdout_envelope(tmp_path, monkeypatch, capsys) -> None:
    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        print("RUN_ID=R1")
        print("coder=codex")
        return 0

    real_atomic = bootstrap._atomic_text  # pyright: ignore[reportPrivateUsage]

    def fail_routing_only(path: Path, text: str) -> None:
        if path.name == "bootstrap-routing.env":
            raise OSError("permission denied")
        real_atomic(path=path, text=text)

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    monkeypatch.setattr(bootstrap, "_atomic_text", fail_routing_only)  # pyright: ignore[reportPrivateUsage]
    assert bootstrap.invoke_main(["--mode", "initial"]) == 0
    captured = capsys.readouterr()
    assert f"IMPLEMENT_TMPDIR={tmp_path}" in captured.out
    assert "BOOTSTRAP_NEXT=cleanup" in captured.out
    assert "RUN_ID=R1" in captured.out
    assert "could not write bootstrap-routing.env" in captured.err


def test_invoke_disables_inherited_quiet_routing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_ACTIVE", "1")
    monkeypatch.setenv("LARCH_QUIET_PID", "999999")
    monkeypatch.delenv("LARCH_QUIET_DISABLE", raising=False)

    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        return 0

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    assert bootstrap.invoke_main(["--mode", "initial"]) == 0
    assert os.environ["LARCH_QUIET_DISABLE"] == "1"


def test_invoke_refuses_symlinked_bootstrap_routing_env(tmp_path, monkeypatch, capsys) -> None:
    target = tmp_path / "target.env"
    target.write_text("prior\n", encoding="utf-8")
    (tmp_path / "bootstrap-routing.env").symlink_to(target)

    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        print("RUN_ID=R1")
        return 0

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    assert bootstrap.invoke_main(["--mode", "initial"]) == 0
    captured = capsys.readouterr()
    assert f"IMPLEMENT_TMPDIR={tmp_path}" in captured.out
    assert "BOOTSTRAP_NEXT=cleanup" in captured.out
    assert "refusing to overwrite symlinked bootstrap-routing.env" in captured.err
    assert target.read_text(encoding="utf-8") == "prior\n"


def test_invoke_refuses_non_regular_bootstrap_routing_env(tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / "bootstrap-routing.env").mkdir()

    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        print("RUN_ID=R1")
        return 0

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    assert bootstrap.invoke_main(["--mode", "initial"]) == 0
    captured = capsys.readouterr()
    assert f"IMPLEMENT_TMPDIR={tmp_path}" in captured.out
    assert "BOOTSTRAP_NEXT=cleanup" in captured.out
    assert "refusing to overwrite non-regular bootstrap-routing.env" in captured.err
    assert (tmp_path / "bootstrap-routing.env").is_dir()


def test_invoke_resume_preserves_prior_coder_in_routing_file(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    plan = seed_plan(tmp_path, "plan\n")
    _ = seed_feature_description(tmp_path)
    (tmp_path / "bootstrap-routing.env").write_text(
        f"IMPLEMENT_TMPDIR={tmp_path}\nRUN_ID=R1\ncoder=codex\ncoder_fallback=true\n",
        encoding="utf-8",
    )

    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        print("RUN_ID=R1")
        print(f"PLAN_FILE={plan}")
        print("STALL_TRACKING=false")
        return 0

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    _install_tail_fakes(monkeypatch)
    assert bootstrap.invoke_main(["--mode", "resume"]) == 0
    out = capsys.readouterr().out
    stored = (tmp_path / "bootstrap-routing.env").read_text(encoding="utf-8")
    assert "coder=codex" in out
    assert "coder_fallback=true" in out
    assert "coder=codex" in stored
    assert "coder_fallback=true" in stored


def test_invoke_resume_restored_coder_tail_absent_route_rebase_routes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    plan = seed_plan(tmp_path, "plan\n")
    _ = seed_feature_description(tmp_path)
    _ = (tmp_path / "bootstrap-routing.env").write_text(
        f"IMPLEMENT_TMPDIR={tmp_path}\nRUN_ID=R1\ncoder=codex\n",
        encoding="utf-8",
    )
    tail_inputs: list[dict[str, str]] = []

    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        print("RUN_ID=R1")
        print(f"PLAN_FILE={plan}")
        print("STALL_TRACKING=false")
        return 0

    def fake_tail(data: dict[str, str], **_kwargs: object) -> bootstrap.ContinueTailResult:
        tail_inputs.append(dict(data))
        return bootstrap.ContinueTailResult()

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    monkeypatch.setattr(bootstrap, "_run_absorbed_continue_tail", fake_tail)  # pyright: ignore[reportPrivateUsage]
    assert bootstrap.invoke_main(["--mode", "resume"]) == 0
    out = capsys.readouterr().out
    assert tail_inputs[0]["coder"] == "codex"
    assert "ROUTE=" not in out
    assert "BOOTSTRAP_NEXT=rebase-routing" in out


def test_routing_parser_preserve_coder_on_resume(tmp_path, capsys) -> None:
    tmpdir = tmp_path / "impl"
    tmpdir.mkdir()
    (tmpdir / "bootstrap-routing.env").write_text("IMPLEMENT_TMPDIR=/file\ncoder=codex\nRUN_ID=R1\n", encoding="utf-8")
    stdout = tmp_path / "stdout.txt"
    stdout.write_text(f"IMPLEMENT_TMPDIR={tmpdir}\ncoder=cursor\nBRANCH_NAME=resume-branch\n", encoding="utf-8")
    assert bootstrap.parse_routing_main(["--stdout-file", str(stdout), "--tmpdir", str(tmpdir), "--resume", "true"]) == 0
    out = capsys.readouterr().out
    assert "coder=" not in out
    assert "unset coder" not in out
    assert "RUN_ID=R1" in out
    assert "BRANCH_NAME=resume-branch" in out


@pytest.mark.parametrize(
    ("requested", "codex_available", "cursor_available", "expected_coder", "expected_fallback", "expected_explicit_warning"),
    [
        ("cursor", "true", "false", "codex", "", True),
        ("codex", "false", "true", "cursor", "", True),
        ("cursor", "false", "false", "claude", "true", True),
        ("", "true", "true", "codex", "", False),
        ("", "false", "true", "cursor", "", False),
        ("", "false", "false", "claude", "true", False),
    ],
)
def test_phase_coder_selection_matrix(
    tmp_path,
    monkeypatch,
    requested: str,
    codex_available: str,
    cursor_available: str,
    expected_coder: str,
    expected_fallback: str,
    expected_explicit_warning: bool,
) -> None:
    _ = seed_plan(tmp_path, "plan\n")
    _ = seed_feature_description(tmp_path)
    explicit_warnings: list[tuple[str, str]] = []
    fallback_reasons: list[str] = []
    monkeypatch.setattr(
        bootstrap,
        "_record_explicit_coder_unavailable",
        lambda requested, selected, **_: explicit_warnings.append((requested, selected)),
    )  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_record_coder_fallback", lambda reason, **_: fallback_reasons.append(reason))  # pyright: ignore[reportPrivateUsage]
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="coder", coder_opt=requested),
        implement_tmpdir=str(tmp_path),
        repo_unavailable="false",
        plan_file=str(tmp_path / "plan.txt"),
        codex_available=codex_available,
        cursor_available=cursor_available,
    )
    bootstrap._phase_coder(st)  # pyright: ignore[reportPrivateUsage]
    assert st.coder == expected_coder
    assert st.coder_fallback == expected_fallback
    assert bool(explicit_warnings) is expected_explicit_warning
    assert bool(fallback_reasons) is (expected_fallback == "true")


def test_phase_coder_moderate_prefers_cursor(tmp_path: Path) -> None:
    _ = seed_plan(tmp_path, "plan\n")
    _ = seed_feature_description(tmp_path)
    _ = (tmp_path / "difficulty-prior.env").write_text("DESIGN_DIFFICULTY=MODERATE\n", encoding="utf-8")
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="coder"),
        implement_tmpdir=str(tmp_path),
        repo_unavailable="false",
        plan_file=str(tmp_path / "plan.txt"),
        codex_available="true",
        cursor_available="true",
    )

    bootstrap._phase_coder(st)  # pyright: ignore[reportPrivateUsage]

    assert st.coder == "cursor"


def test_phase_coder_override_precedes_prior(tmp_path: Path) -> None:
    _ = seed_plan(tmp_path, "plan\n")
    _ = seed_feature_description(tmp_path)
    _ = (tmp_path / "run-flags.sh").write_text("DIFFICULTY_OVERRIDE=HARD\n", encoding="utf-8")
    _ = (tmp_path / "difficulty-prior.env").write_text("DESIGN_DIFFICULTY=MODERATE\n", encoding="utf-8")
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="coder"),
        implement_tmpdir=str(tmp_path),
        repo_unavailable="false",
        plan_file=str(tmp_path / "plan.txt"),
        codex_available="true",
        cursor_available="true",
    )

    bootstrap._phase_coder(st)  # pyright: ignore[reportPrivateUsage]

    assert st.coder == "codex"


@pytest.mark.parametrize(
    ("difficulty_value", "cursor_available", "expected_coder"),
    [
        ("TRIVIAL", "true", "cursor"),
        ("MODERATE", "false", "codex"),
        ("HARD", "true", "codex"),
        ("", "true", "codex"),
        ("INVALID", "true", "codex"),
    ],
)
def test_phase_coder_routes_difficulty_matrix(
    tmp_path: Path,
    difficulty_value: str,
    cursor_available: str,
    expected_coder: str,
) -> None:
    _ = seed_plan(tmp_path, "plan\n")
    _ = seed_feature_description(tmp_path)
    if difficulty_value:
        _ = (tmp_path / "difficulty-prior.env").write_text(
            f"DESIGN_DIFFICULTY={difficulty_value}\n",
            encoding="utf-8",
        )
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="coder"),
        implement_tmpdir=str(tmp_path),
        repo_unavailable="false",
        plan_file=str(tmp_path / "plan.txt"),
        codex_available="true",
        cursor_available=cursor_available,
    )

    bootstrap._phase_coder(st)  # pyright: ignore[reportPrivateUsage]

    assert st.coder == expected_coder


def test_phase_coder_self_implement_forces_claude_without_fallback(tmp_path, monkeypatch) -> None:
    _ = seed_plan(tmp_path, "plan\n")
    _ = seed_feature_description(tmp_path)
    explicit_warnings: list[tuple[str, str]] = []
    fallback_reasons: list[str] = []
    monkeypatch.setattr(
        bootstrap,
        "_record_explicit_coder_unavailable",
        lambda requested, selected, **_: explicit_warnings.append((requested, selected)),
    )  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_record_coder_fallback", lambda reason, **_: fallback_reasons.append(reason))  # pyright: ignore[reportPrivateUsage]
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="coder", coder_opt="cursor", self_implement_requested="true"),
        implement_tmpdir=str(tmp_path),
        repo_unavailable="false",
        plan_file=str(tmp_path / "plan.txt"),
        codex_available="true",
        cursor_available="true",
    )
    bootstrap._phase_coder(st)  # pyright: ignore[reportPrivateUsage]
    assert st.coder == "claude"
    assert st.coder_fallback == ""
    assert not explicit_warnings
    assert not fallback_reasons


def test_phase_coder_force_alone_does_not_force_claude(tmp_path) -> None:
    _ = seed_plan(tmp_path, "plan\n")
    _ = seed_feature_description(tmp_path)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="coder", coder_opt="cursor", force_requested="true"),
        implement_tmpdir=str(tmp_path),
        repo_unavailable="false",
        plan_file=str(tmp_path / "plan.txt"),
        codex_available="true",
        cursor_available="true",
    )
    bootstrap._phase_coder(st)  # pyright: ignore[reportPrivateUsage]
    assert st.coder == "cursor"
    assert st.coder_fallback == ""


@pytest.mark.parametrize(
    ("step_failed", "log_name"),
    [
        ("copy-plan", "copy-plan.stderr.log"),
        ("gh-issue-view", "gh-issue-view.stderr.log"),
    ],
)
def test_invoke_error_redacts_step_logs(tmp_path, capsys, step_failed: str, log_name: str) -> None:
    impl = tmp_path / "claude-implement-larch8-AbC123"
    impl.mkdir()
    token = "ghp_" + ("A" * 24)
    (impl / log_name).write_text(f"{impl}/secret.txt token {token}\n", encoding="utf-8")
    bootstrap._invoke_error(step_failed=step_failed, out=f"IMPLEMENT_TMPDIR={impl}\nSTEP_FAILED={step_failed}\n", implement_tmpdir=str(impl))  # pyright: ignore[reportPrivateUsage]
    err = capsys.readouterr().err
    assert token not in err
    assert str(impl) not in err
    assert "<TMPDIR>" in err


def test_invoke_error_redaction_failure_uses_fixed_diagnostic(tmp_path, monkeypatch, capsys) -> None:
    impl = tmp_path / "claude-implement-larch8-AbC123"
    impl.mkdir()
    token = "ghp_" + ("A" * 24)
    (impl / "copy-plan.stderr.log").write_text(f"{impl}/secret.txt token {token}\n", encoding="utf-8")

    def fail_redact(_text: str) -> str:
        raise RuntimeError("redaction unavailable")

    monkeypatch.setattr(bootstrap.redact, "redact", fail_redact)
    bootstrap._invoke_error(step_failed="copy-plan", out=f"IMPLEMENT_TMPDIR={impl}\nSTEP_FAILED=copy-plan\n", implement_tmpdir=str(impl))  # pyright: ignore[reportPrivateUsage]
    err = capsys.readouterr().err
    assert "diagnostic redaction failed" in err
    assert token not in err
    assert str(impl) not in err


def test_tracking_side_effects_defer_rename_until_lease_activation(tmp_path, monkeypatch) -> None:
    calls: list[str] = []

    def fail_rename(*_args: object, **_kwargs: object) -> bootstrap.tracking_issue.RenameOutput:
        calls.append("rename")
        raise OSError("rename failed")

    def fake_log_init(**_kwargs: object) -> Path:
        calls.append("init")
        return tmp_path / "larch-logs" / "implement" / "RUN1"

    def fake_post(*_args: object, **_kwargs: object) -> bootstrap.pr_body.TrackingIssuePostResult:
        calls.append("post")
        return bootstrap.pr_body.TrackingIssuePostResult(
            exit_code=0, posted=True, comment_url="", error=""
        )

    def fake_title(*_args: object, **_kwargs: object) -> CommandResult:
        return CommandResult(("gh",), 0, "Title", "", 0.01)

    monkeypatch.setattr(bootstrap.gh, "issue_view_template_read", fake_title)
    monkeypatch.setattr(bootstrap.tracking_issue, "rename_with_details", fail_rename)
    monkeypatch.setattr(bootstrap.run_logs, "log_init", fake_log_init)
    monkeypatch.setattr(bootstrap.pr_body, "post_tracking_issue", fake_post)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="tracking", issue_number="7"),
        implement_tmpdir=str(tmp_path),
        repo="owner/repo",
        repo_unavailable="false",
        issue_number_resolved="7",
        run_id="RUN1",
    )
    assert bootstrap._perform_tracking_side_effects(st, write_sentinel=True)  # pyright: ignore[reportPrivateUsage]
    assert st.stall_tracking == "false"
    assert st.implement_bail_reason == ""
    assert calls == ["init", "post"]
    assert not (tmp_path / "tracking-rename-warning.stderr.log").exists()


def test_tracking_lease_verifies_before_implementing_title(tmp_path, monkeypatch) -> None:
    calls: list[str] = []

    def initialize(*_args: object, **_kwargs: object) -> object:
        calls.append("lease")
        return object()

    def title(*_args: object, **_kwargs: object) -> CommandResult:
        calls.append("title-read")
        return CommandResult(("gh",), 0, "[DESIGNED] Title", "", 0.01)

    def rename(*_args: object, **_kwargs: object) -> bootstrap.tracking_issue.RenameOutput:
        calls.append("rename")
        return bootstrap.tracking_issue.RenameOutput(
            renamed=True, new_title="[IMPLEMENTING] Title"
        )

    monkeypatch.setattr(bootstrap.tracking_issue, "initialize_implementation_lease", initialize)
    monkeypatch.setattr(bootstrap.gh, "issue_view_template_read", title)
    monkeypatch.setattr(bootstrap.tracking_issue, "rename_with_details", rename)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7"),
        implement_tmpdir=str(tmp_path),
        repo="owner/repo",
        issue_number_resolved="7",
        run_id="run-7",
        branch_name="feature/owner",
    )
    assert bootstrap._activate_tracking_lease(st)  # pyright: ignore[reportPrivateUsage]
    assert calls == ["lease", "title-read", "rename"]


def test_tracking_activation_failure_terminalizes_created_lease(tmp_path, monkeypatch) -> None:
    calls: list[str] = []

    def initialize(*_args: object, **_kwargs: object) -> object:
        calls.append("lease")
        return object()

    def title(*_args: object, **_kwargs: object) -> CommandResult:
        calls.append("title-read")
        return CommandResult(("gh",), 1, "", "unavailable", 0.01)

    def terminal(*_args: object, **_kwargs: object) -> bootstrap.tracking_issue.RenameOutput:
        calls.append("terminal")
        return bootstrap.tracking_issue.RenameOutput(
            renamed=True, new_title="[STALLED] Title"
        )

    monkeypatch.setattr(bootstrap.tracking_issue, "initialize_implementation_lease", initialize)
    monkeypatch.setattr(bootstrap.gh, "issue_view_template_read", title)
    monkeypatch.setattr(bootstrap.tracking_issue, "rename_terminal_with_lease", terminal)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7"),
        implement_tmpdir=str(tmp_path),
        repo="owner/repo",
        issue_number_resolved="7",
        run_id="run-7",
        branch_name="feature/owner",
    )
    assert not bootstrap._activate_tracking_lease(st)  # pyright: ignore[reportPrivateUsage]
    assert calls == ["lease", "title-read", "terminal"]
    assert st.stall_tracking == "true"


def _run_phase_infra_for_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    opts_run_id: str = "",
    setup_session_id: str = "setup-run-id",
    activate_returncode: int = 0,
    self_review_requested: str = "false",
    self_implement_requested: str = "false",
    write_implement_env_error: str = "",
    claude_pid: bool = True,
) -> tuple[bootstrap.BootstrapState, list[tuple[str, ...]]]:
    calls: list[tuple[str, ...]] = []
    if claude_pid:
        monkeypatch.setenv("LARCH_CLAUDE_PID", "12345")
    else:
        monkeypatch.delenv("LARCH_CLAUDE_PID", raising=False)

    def fake_branch(*_args: object, **_kwargs: object) -> bootstrap.pr.CreateBranchResult:
        calls.append(("branch",))
        return bootstrap.pr.CreateBranchResult("checked", current_branch="feature", is_user_branch=True, user_prefix="user")

    def fake_gate(**_kwargs: object) -> bootstrap.session_env.GateResult:
        calls.append(("entry-gate",))
        return bootstrap.session_env.GateResult("user-branch", "true")

    def fake_setup(**kwargs: object) -> bootstrap.session_env.SessionSetupResult:
        calls.append(("setup", str(kwargs["skip_codex_probe"]), str(kwargs["skip_cursor_probe"])))
        return bootstrap.session_env.SessionSetupResult(
            session_tmpdir=tmp_path, session_id=setup_session_id, render_cache_dir=tmp_path,
            claude_binary_found="true", repo="owner/repo", repo_unavailable="false",
            codex_present="false", cursor_present="false", codex_binary_found="false", cursor_binary_found="false",
        )

    def fake_activate(repo_root: str | Path, run_id: str) -> None:
        _ = repo_root, activate_returncode
        calls.append(("activate", run_id))

    def fake_timing(*, label: str, env: dict[str, str] | None = None) -> None:
        _ = env
        calls.append(("timing", label))

    def fake_write_implement_env(**_kwargs: object) -> bootstrap.session_env.WriteImplementEnvResult:
        calls.append(("write-implement-env",))
        if write_implement_env_error:
            raise OSError(write_implement_env_error)
        return bootstrap.session_env.WriteImplementEnvResult(tmp_path / "pointer", tmp_path / "run", tmp_path, str(Path.cwd()))

    monkeypatch.setattr(bootstrap.pr, "check_branch_state", fake_branch)
    monkeypatch.setattr(bootstrap.session_env, "entry_gate", fake_gate)
    monkeypatch.setattr(bootstrap.session_env, "setup", fake_setup)
    monkeypatch.setattr(bootstrap.progress_file, "activate_run", fake_activate)
    monkeypatch.setattr(bootstrap.timing, "mark", fake_timing)
    monkeypatch.setattr(bootstrap.session_env, "write_implement_env", fake_write_implement_env)
    monkeypatch.setattr(bootstrap, "_write_claude_source_snapshot", lambda _st: None)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_write_base_session_env", lambda _st: None)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_refresh_reviewer_state", lambda _st: None)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_install_statusline_best_effort", lambda: None)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_write_larch_run_sh", lambda _tmpdir: True)  # pyright: ignore[reportPrivateUsage]
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(
            up_to_phase="infra",
            run_id=opts_run_id,
            self_review_requested=self_review_requested,
            self_implement_requested=self_implement_requested,
        )
    )
    bootstrap._phase_infra(st)  # pyright: ignore[reportPrivateUsage]
    return st, calls


def test_phase_infra_progress_activate_uses_explicit_run_id_before_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st, calls = _run_phase_infra_for_progress(
        tmp_path,
        monkeypatch,
        opts_run_id="explicit-run-id",
        setup_session_id="setup-run-id",
    )

    activate_call = next(call for call in calls if call[0] == "activate")
    timing_call = next(call for call in calls if call[0] == "timing")

    assert st.run_id == "explicit-run-id"
    assert activate_call == ("activate", "explicit-run-id")
    assert calls.index(activate_call) < calls.index(timing_call)
    assert timing_call == ("timing", "Step 0 — preflight")


def test_phase_infra_progress_activate_uses_setup_session_id_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st, calls = _run_phase_infra_for_progress(
        tmp_path,
        monkeypatch,
        setup_session_id="setup-session-run-id",
    )

    activate_call = next(call for call in calls if call[0] == "activate")

    assert st.run_id == "setup-session-run-id"
    assert activate_call == ("activate", "setup-session-run-id")


def test_phase_infra_progress_activate_failure_is_best_effort(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    st, calls = _run_phase_infra_for_progress(
        tmp_path,
        monkeypatch,
        setup_session_id="setup-run-id",
        activate_returncode=1,
    )

    captured = capsys.readouterr()

    assert st.run_id == "setup-run-id"
    assert any(call[0] == "activate" for call in calls)
    assert any(call[0] == "write-implement-env" for call in calls)
    assert "STEP_FAILED=" not in captured.out


def test_phase_infra_self_subagents_skip_external_tool_health_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _st, calls = _run_phase_infra_for_progress(
        tmp_path,
        monkeypatch,
        opts_run_id="self-subagent-run",
        setup_session_id="setup-run-id",
        self_review_requested="true",
        self_implement_requested="true",
    )

    setup_call = next(call for call in calls if call[0] == "setup")
    assert setup_call[1:] == ("True", "True")


@pytest.mark.parametrize("reserved_run_id", ["current", ".", ".."])
def test_phase_infra_reserved_run_id_skips_progress_activate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reserved_run_id: str,
) -> None:
    st, calls = _run_phase_infra_for_progress(
        tmp_path,
        monkeypatch,
        opts_run_id=reserved_run_id,
        setup_session_id="setup-run-id",
    )

    assert st.run_id == reserved_run_id
    assert not any(call[0] == "activate" for call in calls)


def test_write_implement_env_failure_is_fatal(tmp_path, monkeypatch) -> None:
    with pytest.raises(bootstrap.BootstrapExit) as exc_info:
        _run_phase_infra_for_progress(
            tmp_path, monkeypatch, write_implement_env_error="pointer failed",
        )
    assert exc_info.value.code == 2
    assert "pointer failed" in (tmp_path / "write-implement-env-warning.log").read_text(encoding="utf-8")
    fallback = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "- **Step implement-bootstrap write-implement-env: session write-implement-env failed" in fallback


def test_write_implement_env_missing_pid_is_fatal_without_write_attempt(tmp_path, monkeypatch) -> None:
    with pytest.raises(bootstrap.BootstrapExit) as exc_info:
        _run_phase_infra_for_progress(tmp_path, monkeypatch, claude_pid=False)

    assert exc_info.value.code == 2


def _continue_data(tmp_path: Path, **overrides: str) -> dict[str, str]:
    plan = seed_plan(tmp_path, "plan\n")
    _ = seed_feature_description(tmp_path)
    data = {
        "IMPLEMENT_TMPDIR": str(tmp_path),
        "IMPLEMENT_BAIL_REASON": "",
        "STALL_TRACKING": "false",
        "PLAN_FILE": str(plan),
        "coder": "codex",
        "CODEX_PRESENT": "true",
        "CURSOR_PRESENT": "true",
        "CODEX_BINARY_FOUND": "true",
        "CURSOR_BINARY_FOUND": "true",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    ("overrides", "continue_tail_attempted", "expected"),
    [
        ({"ROUTE": "continue"}, True, "step2"),
        ({"DEGRADED_PROMPT_REQUIRED": "true", "ROUTE": "continue"}, True, "degraded-prompt"),
        ({"ROUTE": "conflict"}, True, "rebase-routing"),
        ({"ROUTE": "bail"}, True, "rebase-routing"),
        ({}, True, "rebase-routing"),
        ({"ROUTE": "nonsense"}, True, "rebase-routing"),
        ({"IMPLEMENT_BAIL_REASON": "dirty-tree"}, False, "dirty-recovery"),
        ({"REPO_UNAVAILABLE": "true", "ROUTE": "continue"}, True, "cleanup"),
        ({"REPO_UNAVAILABLE": "true", "ROUTE": "conflict"}, False, "cleanup"),
        ({"STALL_TRACKING": "true", "ROUTE": "continue"}, True, "cleanup"),
    ],
)
def test_bootstrap_next_routing_matrix(
    tmp_path: Path,
    overrides: dict[str, str],
    continue_tail_attempted: bool,
    expected: str,
) -> None:
    data = _continue_data(tmp_path, **overrides)
    assert bootstrap._bootstrap_next(data, continue_tail_attempted=continue_tail_attempted) == expected  # pyright: ignore[reportPrivateUsage]


def test_bootstrap_next_absent_route_without_tail_and_blockers_cleans_up(tmp_path: Path) -> None:
    data = _continue_data(tmp_path)
    (tmp_path / "feature-description.txt").unlink()
    assert bootstrap._bootstrap_next(data, continue_tail_attempted=False) == "cleanup"  # pyright: ignore[reportPrivateUsage]


def test_bootstrap_next_absent_route_without_tail_cleans_up(tmp_path: Path) -> None:
    data = _continue_data(tmp_path)
    assert bootstrap._bootstrap_next(data, continue_tail_attempted=False) == "cleanup"  # pyright: ignore[reportPrivateUsage]


def test_bootstrap_next_tail_popped_route_but_blockers_cleans_up(tmp_path: Path) -> None:
    data = _continue_data(tmp_path)
    (tmp_path / "feature-description.txt").unlink()
    assert bootstrap._bootstrap_next(data, continue_tail_attempted=True) == "cleanup"  # pyright: ignore[reportPrivateUsage]


def _reviewers(*, codex_present: bool = True, cursor_present: bool = True) -> bootstrap.agents.CheckReviewersResult:
    return bootstrap.agents.CheckReviewersResult(codex_binary_found=True, cursor_binary_found=True, codex_present=codex_present, cursor_present=cursor_present)


def _gate(*, both_down: bool = False) -> bootstrap.agents.DegradedToolsResult:
    degraded = both_down
    return bootstrap.agents.DegradedToolsResult(
        degraded=degraded,
        codex_state="binary-missing" if degraded else "ok",
        cursor_state="binary-missing" if degraded else "ok",
        both_down=both_down,
        presence_input_empty=False,
        explanation=("Degraded external-tool availability",) if degraded else (),
    )


def _probe(
    *,
    exit_code: int = 0,
    route: str = "continue",
    conflict_files: str = "",
) -> bootstrap.rust_runtime.CheckpointProbeOutput:
    routing = {"REBASE_OUTCOME": "ok", "ROUTE": route, "CHECKPOINT_NEXT": "continue"}
    if conflict_files:
        routing["CONFLICT_FILES"] = conflict_files
    return bootstrap.rust_runtime.CheckpointProbeOutput(
        exit_code=exit_code,
        stdout="",
        stderr="",
        routing=routing,
        advisory_lines=(),
    )


def _install_tail_fakes(monkeypatch: pytest.MonkeyPatch, *, gate: bootstrap.agents.DegradedToolsResult | None = None, probe: bootstrap.rust_runtime.CheckpointProbeOutput | None = None) -> None:
    def healthy_reviewers() -> bootstrap.agents.CheckReviewersResult:
        return _reviewers()

    monkeypatch.setattr(bootstrap.agents, "check_reviewers", healthy_reviewers)
    monkeypatch.setattr(bootstrap.agents, "degraded_tools_result", lambda **_kwargs: gate or _gate())
    monkeypatch.setattr(bootstrap.rust_runtime, "checkpoint_probe", lambda *_args, **_kwargs: probe or _probe())


def test_bootstrap_has_no_cli_self_reentry() -> None:
    source = Path(bootstrap.__file__).read_text(encoding="utf-8")
    assert "_PY_CLI" not in source
    assert "_cli(" not in source
    assert not hasattr(bootstrap, "_cli")


def test_absorbed_tail_uses_typed_healthy_gate_and_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_tail_fakes(monkeypatch)
    tail = bootstrap._run_absorbed_continue_tail(_continue_data(tmp_path), opts=bootstrap.BootstrapOptions(up_to_phase="coder"), non_interactive=False)  # pyright: ignore[reportPrivateUsage]
    assert tail.routing["DEGRADED"] == "false"
    assert tail.routing["ROUTE"] == "continue"
    assert tail.routing["REBASE_RC"] == "0"


def test_absorbed_tail_both_down_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_tail_fakes(monkeypatch, gate=_gate(both_down=True))
    tail = bootstrap._run_absorbed_continue_tail(_continue_data(tmp_path), opts=bootstrap.BootstrapOptions(up_to_phase="coder"), non_interactive=True)  # pyright: ignore[reportPrivateUsage]
    assert tail.contract_failure
    assert tail.step_failed == "degraded-both-down-hard-fail"
    assert tail.routing["DEGRADED_HARD_FAIL"] == "true"


def test_absorbed_tail_one_down_prompts_interactively(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    one_down = bootstrap.agents.DegradedToolsResult(
        degraded=True,
        codex_state="binary-missing",
        cursor_state="ok",
        both_down=False,
        presence_input_empty=False,
        explanation=("one tool unavailable",),
    )
    _install_tail_fakes(monkeypatch, gate=one_down)
    tail = bootstrap._run_absorbed_continue_tail(_continue_data(tmp_path), opts=bootstrap.BootstrapOptions(up_to_phase="coder"), non_interactive=False)  # pyright: ignore[reportPrivateUsage]
    assert tail.routing["DEGRADED_PROMPT_REQUIRED"] == "true"
    assert "ROUTE" not in tail.routing


def test_absorbed_tail_self_subagents_skip_tool_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap.agents, "check_reviewers", lambda: (_ for _ in ()).throw(AssertionError("unexpected gate")))
    monkeypatch.setattr(bootstrap.agents, "degraded_tools_result", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected gate")))
    monkeypatch.setattr(bootstrap.rust_runtime, "checkpoint_probe", lambda *_args, **_kwargs: _probe())
    tail = bootstrap._run_absorbed_continue_tail(_continue_data(tmp_path), opts=bootstrap.BootstrapOptions(up_to_phase="coder", self_review_requested="true", self_implement_requested="true"), non_interactive=True)  # pyright: ignore[reportPrivateUsage]
    assert tail.routing["DEGRADED"] == "false"
    assert tail.routing["ROUTE"] == "continue"


def test_absorbed_tail_relays_typed_conflict_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_tail_fakes(monkeypatch, probe=_probe(exit_code=1, route="conflict", conflict_files="a.py,b.py"))
    tail = bootstrap._run_absorbed_continue_tail(_continue_data(tmp_path), opts=bootstrap.BootstrapOptions(up_to_phase="coder"), non_interactive=False)  # pyright: ignore[reportPrivateUsage]
    assert tail.routing["ROUTE"] == "conflict"
    assert tail.routing["CONFLICT_FILES"] == "a.py,b.py"
    assert tail.routing["REBASE_RC"] == "1"


def test_refresh_gate_probe_retries_typed_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    def unavailable() -> bootstrap.agents.CheckReviewersResult:
        nonlocal calls
        calls += 1
        raise OSError("probe unavailable")
    monkeypatch.setattr(bootstrap.agents, "check_reviewers", unavailable)
    st = bootstrap.BootstrapState(bootstrap.BootstrapOptions(up_to_phase="coder"), implement_tmpdir=str(tmp_path))
    assert bootstrap._refresh_gate_probe(st) == "absorbed-gate-probe-refresh-failed"  # pyright: ignore[reportPrivateUsage]
    assert calls == 2


def test_refresh_gate_probe_updates_typed_reviewer_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap.agents, "check_reviewers", lambda: _reviewers(codex_present=False, cursor_present=False))
    st = bootstrap.BootstrapState(bootstrap.BootstrapOptions(up_to_phase="coder"), implement_tmpdir=str(tmp_path))
    assert bootstrap._refresh_gate_probe(st) is None  # pyright: ignore[reportPrivateUsage]
    assert st.codex_present == "false"
    assert st.cursor_binary_found == "true"


def test_emit_final_repo_root_prefers_session_value(tmp_path, capsys) -> None:
    (tmp_path / "session-env.sh").write_text("REPO_ROOT=/persisted/root\n", encoding="utf-8")
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="infra"),
        implement_tmpdir=str(tmp_path),
    )
    bootstrap._emit_final(st)  # pyright: ignore[reportPrivateUsage]
    assert "REPO_ROOT=/persisted/root" in capsys.readouterr().out


def test_emit_final_repo_root_falls_back_to_trust_boundary(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude/project")
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="infra"),
        implement_tmpdir=str(tmp_path),
    )
    bootstrap._emit_final(st)  # pyright: ignore[reportPrivateUsage]
    assert "REPO_ROOT=/claude/project" in capsys.readouterr().out


def test_filtered_envelope_passes_repo_root() -> None:
    out = bootstrap._filtered_envelope("REPO_ROOT=/some/root\n", resume=False)  # pyright: ignore[reportPrivateUsage]
    assert "REPO_ROOT=/some/root" in out
