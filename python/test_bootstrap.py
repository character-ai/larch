# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path

import pytest

import bootstrap

_REPO_ROOT = Path(__file__).resolve().parents[1]


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
        "LARCH_DYNAMIC_ARCHETYPES_MAX=2\n"
        "LARCH_AUTO_MODE=true\n",
        encoding="utf-8",
    )
    calls: list[tuple[str, ...]] = []

    def fake_cli(*args: str, env=None):
        _ = env
        calls.append(args)
        if args[:2] == ("session", "read-key"):
            file_path = args[args.index("--file") + 1]
            key = args[args.index("--key") + 1]
            default = args[args.index("--default") + 1] if "--default" in args else ""
            for line in Path(file_path).read_text(encoding="utf-8").splitlines():
                if line.startswith(f"{key}="):
                    return subprocess.CompletedProcess(["cli", *args], 0, line.split("=", 1)[1] + "\n", "")
            return subprocess.CompletedProcess(["cli", *args], 0, default + "\n", "")
        return subprocess.CompletedProcess(["cli", *args], 0, "", "")

    monkeypatch.setattr(bootstrap, "_cli", fake_cli)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="infra"),
        implement_tmpdir=str(tmp_path),
        repo="owner/repo",
        repo_unavailable="false",
        session_id="sid",
    )
    bootstrap._write_base_session_env(st)  # pyright: ignore[reportPrivateUsage]
    write_env = next(call for call in calls if call[:2] == ("session", "write-env") and "--plugin-root-only" not in call)
    assert "--claude-source-file" in write_env
    assert "/tmp/source.env" in write_env
    assert "--dynamic-archetypes" in write_env
    assert "2" in write_env
    assert "--auto-mode" in write_env


def test_write_larch_run_sh_dispatches_shell_and_python_targets(tmp_path) -> None:
    assert bootstrap._write_larch_run_sh(str(tmp_path))  # pyright: ignore[reportPrivateUsage]
    launcher = tmp_path / "larch-run.sh"
    text = launcher.read_text(encoding="utf-8")
    assert launcher.stat().st_mode & 0o111
    assert '*.py) exec python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;' in text
    assert '*.sh) exec "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;' in text
    assert '/*|*..*)' in text


def test_tracking_adoption_empty_run_id_stalls_without_side_effects(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_cli(*args: str, env=None):
        _ = env
        calls.append(args)
        if args[:2] == ("issue", "state"):
            return subprocess.CompletedProcess(["cli", *args], 0, "STATE=OPEN\nIS_PR=false\n", "")
        return subprocess.CompletedProcess(["cli", *args], 0, "", "")

    monkeypatch.setattr(bootstrap, "_cli", fake_cli)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="tracking", issue_number="7"),
        implement_tmpdir=str(tmp_path),
        repo="owner/repo",
        repo_unavailable="false",
    )
    bootstrap._phase_tracking(st)  # pyright: ignore[reportPrivateUsage]
    assert st.implement_bail_reason == "tracking-init-failed"
    assert st.stall_tracking == "true"
    assert not any(call[:2] == ("run-log", "init") for call in calls)


def test_tracking_helper_failure_stalls_before_sentinel(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(argv, *, env=None, cwd=None):
        _ = env, cwd
        if "tracking-issue-write.sh" in str(argv[0]):
            return subprocess.CompletedProcess(argv, 0, "RENAMED=true\n", "")
        if "post-tracking-issue.sh" in str(argv[0]):
            calls.append(("post",))
            return subprocess.CompletedProcess(argv, 0, "POSTED=true\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def fake_cli(*args: str, env=None):
        _ = env
        calls.append(args)
        if args[:2] == ("run-log", "init"):
            return subprocess.CompletedProcess(["cli", *args], 1, "", "boom\n")
        return subprocess.CompletedProcess(["cli", *args], 0, "", "")

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(bootstrap, "_cli", fake_cli)
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
    assert ("post",) not in calls
    assert not (tmp_path / "parent-issue.md").exists()


def test_tracking_parent_sentinel_requires_explicit_issue_number(tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=7\nRUN_ID=R1\n", encoding="utf-8")

    def fake_run(argv, *, env=None, cwd=None):
        _ = env, cwd
        if "tracking-issue-read.sh" in str(argv[0]):
            return subprocess.CompletedProcess(argv, 0, "ADOPTED=true\nISSUE_NUMBER=7\nRUN_ID=R1\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(bootstrap, "_run", fake_run)
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


def test_resume_plan_tail_matching_sentinel_skips_tracking_side_effects(tmp_path, monkeypatch) -> None:
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=7\nRUN_ID=R1\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def fake_run(argv, *, env=None, cwd=None):
        _ = env, cwd
        if "tracking-issue-read.sh" in str(argv[0]):
            return subprocess.CompletedProcess(argv, 0, "ADOPTED=true\nISSUE_NUMBER=7\nRUN_ID=R1\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def fake_cli(*args: str, env=None):
        _ = env
        calls.append(args)
        return subprocess.CompletedProcess(["cli", *args], 0, "", "")

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(bootstrap, "_cli", fake_cli)
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
    assert not any(call[:2] == ("run-log", "init") for call in calls)


def test_emergency_bypass_validates_issue_and_consumes_invalid_log(tmp_path, monkeypatch) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    (preflight / "emergency-bypass.log").write_text("BYPASS kind=missing-plan issue=99\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def fake_cli(*args: str, env=None):
        _ = env
        calls.append(args)
        return subprocess.CompletedProcess(["cli", *args], 0, "", "")

    monkeypatch.setattr(bootstrap, "_cli", fake_cli)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", emergency_requested="true", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(impl),
    )
    assert bootstrap._append_emergency_bypass(st)  # pyright: ignore[reportPrivateUsage]
    assert (impl / ".emergency-bypass-log-consumed").exists()
    assert "--exit-code" in calls[0]
    assert "99" in calls[0]
    assert "invalid-format" in calls[0]


def test_emergency_bypass_append_failure_falls_back_to_append_entry(tmp_path, monkeypatch) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    (preflight / "emergency-bypass.log").write_text("BYPASS kind=missing-plan issue=7\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def fake_cli(*args: str, env=None):
        _ = env
        calls.append(args)
        if args[:2] == ("run-log", "append-failure"):
            return subprocess.CompletedProcess(["cli", *args], 2, "", "append failed\n")
        return subprocess.CompletedProcess(["cli", *args], 0, "APPENDED=true\n", "")

    monkeypatch.setattr(bootstrap, "_cli", fake_cli)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", emergency_requested="true", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(impl),
    )
    assert bootstrap._append_emergency_bypass(st)  # pyright: ignore[reportPrivateUsage]
    assert (impl / ".emergency-bypass-log-consumed").exists()
    assert any(call[:2] == ("run-log", "append-entry") for call in calls)


def test_resume_plan_tail_appends_emergency_bypass_before_flags(tmp_path, monkeypatch) -> None:
    order: list[str] = []
    monkeypatch.setattr(bootstrap, "_append_emergency_bypass", lambda _st: order.append("bypass") or True)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_persist_run_flags", lambda _st: order.append("flags") or True)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap.dirty_tree, "checkpoint", lambda: ["STATUS=clean", "MODE=checkpoint"])
    monkeypatch.setattr(bootstrap, "_run", lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, "BRANCH=feature\n", ""))  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_publish_plan_review_tally", lambda _st: None)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_upsert_plan_summary", lambda _st: None)  # pyright: ignore[reportPrivateUsage]
    (tmp_path / "feature-description.txt").write_text("Title\n", encoding="utf-8")
    (tmp_path / "plan.txt").write_text("Plan\n", encoding="utf-8")
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", resume_plan_tail=True),
        implement_tmpdir=str(tmp_path),
        branch_name="feature",
        plan_file=str(tmp_path / "plan.txt"),
    )
    bootstrap._phase_plan(st)  # pyright: ignore[reportPrivateUsage]
    assert order[:2] == ["bypass", "flags"]


def test_resume_plan_tail_stops_after_run_flags_failure(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(bootstrap, "_append_emergency_bypass", lambda _st: True)  # pyright: ignore[reportPrivateUsage]
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


def test_plan_stops_after_run_flags_failure(tmp_path, monkeypatch) -> None:
    preflight = tmp_path / "preflight"
    impl = tmp_path / "impl"
    preflight.mkdir()
    impl.mkdir()
    (preflight / "plan-from-issue.txt").write_text("plan", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "_append_emergency_bypass", lambda _st: True)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_persist_run_flags", lambda st: setattr(st, "implement_bail_reason", "run-flags-persist-failed") or False)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_run", lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, "Title\n\nBody\n", ""))  # pyright: ignore[reportPrivateUsage]

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


def test_forked_plan_requires_upstream_repo_before_gh(tmp_path, monkeypatch) -> None:
    calls: list[list[str]] = []
    preflight = tmp_path / "preflight"
    preflight.mkdir()
    (preflight / "plan-from-issue.txt").write_text("plan", encoding="utf-8")
    monkeypatch.setattr(bootstrap.dirty_tree, "checkpoint", lambda: ["STATUS=clean", "MODE=checkpoint"])
    monkeypatch.setattr(bootstrap, "_append_emergency_bypass", lambda _st: True)  # pyright: ignore[reportPrivateUsage]

    def fake_run(argv, *, env=None, cwd=None):
        _ = env, cwd
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="plan", issue_number="7", forked_target="true", preflight_tmpdir=str(preflight)),
        implement_tmpdir=str(tmp_path),
        issue_number_resolved="7",
    )
    with pytest.raises(bootstrap.BootstrapExit) as exc_info:
        bootstrap._phase_plan(st)  # pyright: ignore[reportPrivateUsage]
    assert exc_info.value.code == 2
    assert st.implement_bail_reason == ""
    assert not any(call[:3] == ["gh", "issue", "view"] for call in calls)


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
    )
    assert result.returncode == 2
    assert "--forked-target must be true or false" in result.stderr


def test_invoke_env_fallback_and_flag_precedence(tmp_path, monkeypatch) -> None:
    captured: list[bootstrap.BootstrapOptions] = []
    monkeypatch.setenv("TARGET_ISSUE_NUMBER", "41")
    monkeypatch.setenv("CALLER_ENV_PATH", "/env/caller")
    monkeypatch.setenv("PREFLIGHT_TMPDIR", "/env/preflight")
    monkeypatch.setenv("forked_target", "true")
    monkeypatch.setenv("UPSTREAM_REPO", "env/upstream")
    monkeypatch.setenv("RUN_ID", "ENV")
    monkeypatch.setenv("emergency_requested", "true")
    monkeypatch.setenv("self_review", "true")
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
            "--emergency-requested",
            "false",
            "--self-review-requested",
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
    assert opts.emergency_requested == "false"
    assert opts.self_review_requested == "false"
    assert opts.coder_opt == "codex"


def test_invoke_env_fallback_used_when_flags_omitted(tmp_path, monkeypatch) -> None:
    captured: list[bootstrap.BootstrapOptions] = []
    monkeypatch.setenv("TARGET_ISSUE_NUMBER", "41")
    monkeypatch.setenv("CALLER_ENV_PATH", "/env/caller")
    monkeypatch.setenv("PREFLIGHT_TMPDIR", "/env/preflight")
    monkeypatch.setenv("forked_target", "true")
    monkeypatch.setenv("UPSTREAM_REPO", "env/upstream")
    monkeypatch.setenv("RUN_ID", "ENV")
    monkeypatch.setenv("emergency_requested", "true")
    monkeypatch.setenv("self_review", "true")
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
    assert opts.emergency_requested == "true"
    assert opts.self_review_requested == "true"
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


def test_invoke_routing_write_failure_preserves_stdout_envelope(tmp_path, monkeypatch, capsys) -> None:
    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        print("RUN_ID=R1")
        print("coder=codex")
        return 0

    def fail_atomic(_path: Path, _text: str) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    monkeypatch.setattr(bootstrap, "_atomic_text", fail_atomic)  # pyright: ignore[reportPrivateUsage]
    assert bootstrap.invoke_main(["--mode", "initial"]) == 0
    captured = capsys.readouterr()
    assert f"IMPLEMENT_TMPDIR={tmp_path}" in captured.out
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
    assert "refusing to overwrite non-regular bootstrap-routing.env" in captured.err
    assert (tmp_path / "bootstrap-routing.env").is_dir()


def test_invoke_resume_preserves_prior_coder_in_routing_file(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    (tmp_path / "bootstrap-routing.env").write_text(
        f"IMPLEMENT_TMPDIR={tmp_path}\nRUN_ID=R1\ncoder=codex\ncoder_fallback=true\n",
        encoding="utf-8",
    )

    def fake_run_bootstrap(_opts: bootstrap.BootstrapOptions) -> int:
        print(f"IMPLEMENT_TMPDIR={tmp_path}")
        print("RUN_ID=R1")
        print(f"PLAN_FILE={tmp_path / 'plan.txt'}")
        return 0

    monkeypatch.setattr(bootstrap, "run_bootstrap", fake_run_bootstrap)
    assert bootstrap.invoke_main(["--mode", "resume"]) == 0
    out = capsys.readouterr().out
    stored = (tmp_path / "bootstrap-routing.env").read_text(encoding="utf-8")
    assert "coder=codex" in out
    assert "coder_fallback=true" in out
    assert "coder=codex" in stored
    assert "coder_fallback=true" in stored


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
    (tmp_path / "plan.txt").write_text("plan\n", encoding="utf-8")
    (tmp_path / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    explicit_warnings: list[tuple[str, str]] = []
    fallback_reasons: list[str] = []
    monkeypatch.setattr(
        bootstrap,
        "_record_explicit_coder_unavailable",
        lambda _st, req, selected: explicit_warnings.append((req, selected)),
    )  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_record_coder_fallback", lambda _st, reason: fallback_reasons.append(reason))  # pyright: ignore[reportPrivateUsage]
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


def test_phase_coder_emergency_forces_claude_without_fallback(tmp_path, monkeypatch) -> None:
    (tmp_path / "plan.txt").write_text("plan\n", encoding="utf-8")
    (tmp_path / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    explicit_warnings: list[tuple[str, str]] = []
    fallback_reasons: list[str] = []
    monkeypatch.setattr(
        bootstrap,
        "_record_explicit_coder_unavailable",
        lambda _st, req, selected: explicit_warnings.append((req, selected)),
    )  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(bootstrap, "_record_coder_fallback", lambda _st, reason: fallback_reasons.append(reason))  # pyright: ignore[reportPrivateUsage]
    st = bootstrap.BootstrapState(
        bootstrap.BootstrapOptions(up_to_phase="coder", coder_opt="cursor", emergency_requested="true"),
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
    bootstrap._invoke_error(step_failed, f"IMPLEMENT_TMPDIR={impl}\nSTEP_FAILED={step_failed}\n", str(impl))  # pyright: ignore[reportPrivateUsage]
    err = capsys.readouterr().err
    assert token not in err
    assert str(impl) not in err
    assert "<TMPDIR>" in err


def test_invoke_error_redaction_failure_uses_fixed_diagnostic(tmp_path, monkeypatch, capsys) -> None:
    impl = tmp_path / "claude-implement-larch8-AbC123"
    impl.mkdir()
    token = "ghp_" + ("A" * 24)
    (impl / "copy-plan.stderr.log").write_text(f"{impl}/secret.txt token {token}\n", encoding="utf-8")

    def fail_run(*args, **_kwargs):
        return subprocess.CompletedProcess(args[0], 1, "", "failed\n")

    monkeypatch.setattr(bootstrap.subprocess, "run", fail_run)
    bootstrap._invoke_error("copy-plan", f"IMPLEMENT_TMPDIR={impl}\nSTEP_FAILED=copy-plan\n", str(impl))  # pyright: ignore[reportPrivateUsage]
    err = capsys.readouterr().err
    assert "diagnostic redaction failed" in err
    assert token not in err
    assert str(impl) not in err


def test_tracking_rename_failure_warns_and_continues(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(argv, *, env=None, cwd=None):
        _ = env, cwd
        if "tracking-issue-write.sh" in str(argv[0]):
            calls.append(("rename",))
            return subprocess.CompletedProcess(argv, 1, "FAILED=true\n", "rename failed\n")
        if "post-tracking-issue.sh" in str(argv[0]):
            calls.append(("post",))
            return subprocess.CompletedProcess(argv, 0, "POSTED=true\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def fake_cli(*args: str, env=None):
        _ = env
        calls.append(args)
        return subprocess.CompletedProcess(["cli", *args], 0, "", "")

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(bootstrap, "_cli", fake_cli)
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
    assert ("run-log", "init", "--log-root", str(tmp_path / "larch-logs"), "--skill", "implement", "--run-id", "RUN1", "--issue", "7") in calls
    assert ("post",) in calls
    assert "rename failed" in (tmp_path / "tracking-rename-warning.stderr.log").read_text(encoding="utf-8")


def test_write_implement_env_failure_logs_warning_and_continues(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setenv("LARCH_CLAUDE_PID", "12345")

    def fake_run(argv, *, env=None, cwd=None):
        _ = env, cwd
        if "create-branch.sh" in str(argv[0]):
            return subprocess.CompletedProcess(argv, 0, "CURRENT_BRANCH=feature\nIS_MAIN=false\nIS_USER_BRANCH=true\nUSER_PREFIX=user\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def fake_cli(*args: str, env=None):
        _ = env
        calls.append(args)
        if args[:2] == ("session", "entry-gate"):
            return subprocess.CompletedProcess(["cli", *args], 0, "ENTRY_GATE=user-branch\nSKIP_BRANCH_CHECK=true\n", "")
        if args[:2] == ("session", "setup"):
            return subprocess.CompletedProcess(
                ["cli", *args],
                0,
                f"SESSION_TMPDIR={tmp_path}\nSESSION_ID=R1\nREPO=owner/repo\nREPO_UNAVAILABLE=false\nCODEX_PRESENT=false\nCURSOR_PRESENT=false\nCODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\n",
                "",
            )
        if args[:2] == ("session", "write-implement-env"):
            return subprocess.CompletedProcess(["cli", *args], 2, "", "pointer failed\n")
        return subprocess.CompletedProcess(["cli", *args], 0, "", "")

    monkeypatch.setattr(bootstrap, "_run", fake_run)
    monkeypatch.setattr(bootstrap, "_cli", fake_cli)
    st = bootstrap.BootstrapState(bootstrap.BootstrapOptions(up_to_phase="infra"))
    bootstrap._phase_infra(st)  # pyright: ignore[reportPrivateUsage]
    assert st.implement_tmpdir == str(tmp_path)
    assert "pointer failed" in (tmp_path / "write-implement-env-warning.log").read_text(encoding="utf-8")
    assert any(call[:2] == ("run-log", "append-failure") for call in calls)
