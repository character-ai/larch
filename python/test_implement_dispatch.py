# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from cli import _REGISTRY

import agents
import implement_dispatch
import logging_util


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)


@pytest.fixture(autouse=True)
def quiet_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    logging_util.reset_quiet_state()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "feature"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
    (root / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    monkeypatch.chdir(root)
    return root


def _session(tmp_path: Path) -> Path:
    tmp = tmp_path / "impl"
    tmp.mkdir()
    (tmp / "plan.txt").write_text("## Plan\n", encoding="utf-8")
    (tmp / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    (tmp / "session-env.sh").write_text("CURSOR_PRESENT=false\nLARCH_CLAUDE_PLUGIN_ROOT=.\n", encoding="utf-8")
    return tmp


def test_cli_registry_has_implement_and_launcher_verbs() -> None:
    assert _REGISTRY[("implement", "step2-dispatch")] == ("implement_dispatch", "step2_dispatch_main")
    assert _REGISTRY[("implement", "run-dispatch")] == ("implement_dispatch", "run_dispatch_main")
    assert _REGISTRY[("implement", "recovery-paths")] == ("implement_dispatch", "recovery_paths_main")
    assert _REGISTRY[("implement", "commit")] == ("implement_dispatch", "commit_main")
    assert _REGISTRY[("agent", "launch-codex-implement")] == ("agents", "launch_codex_implement_main")
    assert _REGISTRY[("agent", "launch-cursor-implement")] == ("agents", "launch_cursor_implement_main")


def test_recovery_paths_filters_tmpdir_and_detects_changed_predirty(repo: Path) -> None:
    tmp = repo / ".tmp-impl"
    tmp.mkdir()
    predirty = repo / "README.md"
    predirty.write_text("dirty-before\n", encoding="utf-8")
    pre = tmp / "pre.nul"
    post = tmp / "post.nul"
    digests = tmp / "digests.txt"
    out = tmp / "out.nul"
    pre.write_bytes(_git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.encode())
    digest = implement_dispatch.hashlib.sha256(predirty.read_bytes()).hexdigest()
    digests.write_text(f"{digest}\tREADME.md\n", encoding="utf-8")
    predirty.write_text("changed-after\n", encoding="utf-8")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    (tmp / "scratch.txt").write_text("scratch\n", encoding="utf-8")
    post.write_bytes(_git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.encode())

    ok = implement_dispatch.compute_recovery_paths(
        repo_root=repo,
        tmpdir=tmp,
        prelaunch_porcelain=pre,
        postlaunch_porcelain=post,
        prelaunch_digests=digests,
        out_file=out,
    )

    assert ok is True
    paths = set(out.read_bytes().rstrip(b"\0").split(b"\0"))
    assert b"README.md" in paths
    assert b"new.txt" in paths
    assert all(not p.startswith(b".tmp-impl/") for p in paths)


def test_step2_dispatch_claude_fallback(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "claude",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=claude_fallback" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=allowed" in out


def test_run_dispatch_fails_closed_on_cursor_drift(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    rc = implement_dispatch.run_dispatch_main(["--implement-tmpdir", str(tmp), "--coder", "cursor"])
    assert rc == 2
    assert "CURSOR_PRESENT=false" in capsys.readouterr().err


def test_step2_dispatch_complete_commits_manifest_message(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "implemented.txt").write_text("done\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps({
            "schema_version": "1",
            "status": "complete",
            "files_touched": [{"path": "implemented.txt", "lines_added": 1, "lines_removed": 0}],
            "tests_added_or_modified": [],
            "summary_bullets": ["Implement the feature"],
            "commit_message": "Implement via fake launcher",
            "todos_left": [],
            "oos_observations": [],
        }), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda _st: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    assert _git(repo, "log", "-1", "--pretty=%s").stdout.strip() == "Implement via fake launcher"


def test_step2_dispatch_malformed_manifest_recovery(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "recovered.txt").write_text("done\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text('{"status":"complete","summary":"x","checks":"y"}\n', encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "cursor",
        "--cursor-present", "true",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=claude_fallback" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=allowed" in out
    assert "RECOVERY_FROM=manifest-schema-invalid" in out
    assert (tmp / "step2-recovery-paths.nul").read_bytes() == b"recovered.txt\0"


def test_commit_main_commits_named_file(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "commit-me.txt").write_text("x\n", encoding="utf-8")
    rc = implement_dispatch.commit_main(["--message", "Commit helper", "commit-me.txt"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "COMMITTED=true" in out
    assert _git(repo, "log", "-1", "--pretty=%s").stdout.strip() == "Commit helper"


def test_commit_main_passes_named_files_once(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        stdout = "abc123\n" if argv[:2] == ["git", "rev-parse"] else ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(implement_dispatch, "_run", fake_run)

    rc = implement_dispatch.commit_main(["--message", "Commit helper", "one.txt", "two.txt"])

    assert rc == 0
    assert calls[0][-2:] == ["one.txt", "two.txt"]
    assert calls[0].count("one.txt") == 1
    assert calls[0].count("two.txt") == 1
    assert "SHA=abc123" in capsys.readouterr().out


def _launcher_args(tmp: Path) -> list[str]:
    for name in ("out", "plan.txt", "feature.txt", "agent.md"):
        path = tmp / name
        if "." in name:
            path.write_text("---\ndescription: x\n---\nbody\n", encoding="utf-8")
    outdir = tmp / "out"
    outdir.mkdir(exist_ok=True)
    return [
        "--transcript-path", str(outdir / "transcript.txt"),
        "--sidecar-log", str(tmp / "sidecar.log"),
        "--manifest-path", str(outdir / "manifest.json"),
        "--qa-pending-path", str(outdir / "qa-pending.json"),
        "--scout-manifest-path", str(outdir / "scout-coder-manifest.json"),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature.txt"),
        "--agent-prompt", str(tmp / "agent.md"),
        "--timeout", "1",
    ]


def test_codex_launcher_missing_binary_emits_kv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(agents.shutil, "which", lambda name: None if name == "codex" else "/bin/true")
    rc = agents.launch_codex_implement_main(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "LAUNCHER_EXIT=127" in out
    assert "MANIFEST_WRITTEN=false" in out


@pytest.mark.parametrize(
    ("launcher", "tool"),
    [
        (agents.launch_codex_implement_main, "codex"),
        (agents.launch_cursor_implement_main, "cursor"),
    ],
)
def test_implement_launchers_reject_bad_timeout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    launcher: Callable[[list[str]], int],
    tool: str,
) -> None:
    args = _launcher_args(tmp_path)
    args[args.index("--timeout") + 1] = "0"

    rc = launcher(args)

    assert rc == 2
    assert f"agent launch-{tool}-implement: --timeout must be a positive integer" in capsys.readouterr().err


def test_codex_launcher_rejects_session_tmpdir_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    args = _launcher_args(tmp_path)
    outdir = tmp_path / "out"
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(outdir))

    rc = agents.launch_codex_implement_main(args)

    assert rc == 2
    assert "--manifest-path parent must not be the implement session tmpdir root" in capsys.readouterr().err


def test_codex_launcher_builds_exec_argv_and_dynamic_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/codex" if name == "codex" else "/bin/true")
    monkeypatch.setattr(agents, "_record_implement_timing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_record_usage_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_mirror_codex_quota_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_promote_inner_done", lambda *_args, **_kwargs: None)
    captured: dict[str, object] = {}

    def fake_run_external_agent_with_auth_retries(**kwargs):  # type: ignore[no-untyped-def]
        cmd = list(kwargs["cmd"])
        output = kwargs["output"]
        stdout_path = kwargs["stdout_path"]
        captured["cmd"] = cmd
        captured["cwd"] = kwargs["cwd"]
        captured["config"] = (Path(agents.os.environ["CODEX_HOME"]) / "config.toml").read_text(encoding="utf-8")
        output.write_text("codex transcript\n", encoding="utf-8")
        stdout_path.write_text('{"type":"turn_completed","usage":{"input_tokens":1}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)

    rc = agents.launch_codex_implement_main(args)

    cmd = captured["cmd"]
    assert rc == 0
    assert isinstance(cmd, list)
    assert cmd[:4] == ["codex", "exec", "--full-auto", "-C"]
    assert cmd.count("--add-dir") == 2
    assert str(tmp_path / "out") in cmd
    assert str(Path.cwd()) in cmd
    assert "--output-last-message" in cmd
    assert cmd[-2] == "--"
    assert "body" not in Path(str(tmp_path / "out" / "transcript.txt.prompt")).read_text(encoding="utf-8")
    assert "instructions = '''" in str(captured["config"])
    assert "body" in str(captured["config"])


def test_cursor_launcher_missing_binary_emits_kv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setattr(agents.shutil, "which", lambda name: None if name == "cursor" else "/bin/true")
    rc = agents.launch_cursor_implement_main(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "LAUNCHER_EXIT=127" in out
    assert "MANIFEST_WRITTEN=false" in out


def test_cursor_launcher_builds_agent_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/cursor" if name == "cursor" else "/bin/true")
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(agents, "cursor_preread_service_token", lambda: None)
    monkeypatch.setattr(agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(agents, "_record_implement_timing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_record_cursor_implement_usage", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_promote_inner_done", lambda *_args, **_kwargs: None)
    captured: dict[str, object] = {}

    def fake_run_external_agent_with_auth_retries(**kwargs):  # type: ignore[no-untyped-def]
        cmd = list(kwargs["cmd"])
        output = kwargs["output"]
        captured["cmd"] = cmd
        captured["capture_stdout_only"] = kwargs["capture_stdout_only"]
        output.write_text('{"usage":{"inputTokens":1}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)

    rc = agents.launch_cursor_implement_main(args)

    cmd = captured["cmd"]
    assert rc == 0
    assert isinstance(cmd, list)
    assert cmd[:7] == ["cursor", "agent", "-p", "--force", "--trust", "--output-format", "json"]
    assert "--workspace" in cmd
    assert "--" not in cmd
    assert captured["capture_stdout_only"] is True
