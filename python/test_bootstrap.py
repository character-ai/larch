# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import bootstrap


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
