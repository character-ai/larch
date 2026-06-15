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


def _legacy_malformed_manifest() -> str:
    return '{"status":"complete","summary":"done","checks":"ok"}\n'


def _assert_bailed_no_recovery(out: str, *, reason: str = "manifest-schema-invalid") -> None:
    assert "STATUS=bailed" in out
    assert f"REASON={reason}" in out
    assert "RECOVERY_FROM=" not in out


def _assert_recovery_envelope(out: str, tool: str) -> None:
    assert "STATUS=claude_fallback" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=allowed" in out
    assert "RECOVERY_FROM=manifest-schema-invalid" in out
    assert f"RECOVERY_PRIOR_TOOL={tool}" in out
    assert "RECOVERY_PATHS_FILE=" in out
    assert _auth_lines(out) == 1


def _recovery_paths_from_file(path: Path) -> list[str]:
    return [p.decode() for p in path.read_bytes().split(b"\0") if p]


def _kv_value(out: str, key: str) -> str:
    prefix = f"{key}="
    for line in out.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
    raise AssertionError(f"missing {key}= in output")


def _malformed_launcher(edit: Callable[[Path, implement_dispatch.DispatchState], None]):
    def fake_launcher(st: implement_dispatch.DispatchState):
        edit(st.repo_root, st)
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(_legacy_malformed_manifest(), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    return fake_launcher


def test_run_dispatch_fails_closed_on_cursor_drift(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    rc = implement_dispatch.run_dispatch_main(["--implement-tmpdir", str(tmp), "--coder", "cursor"])
    assert rc == 2
    assert "CURSOR_PRESENT=false" in capsys.readouterr().err


def test_run_dispatch_missing_tmpdir_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        implement_dispatch.run_dispatch_main(["--coder", "codex"])
    assert exc.value.code == 2
    assert "--implement-tmpdir" in capsys.readouterr().err


def test_run_dispatch_missing_answers_path_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    rc = implement_dispatch.run_dispatch_main([
        "--implement-tmpdir", str(tmp),
        "--coder", "codex",
        "--answers", str(tmp / "missing.json"),
    ])
    assert rc == 2
    assert "--answers path does not exist" in capsys.readouterr().err


def test_run_dispatch_invalid_cursor_present_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    (tmp / "session-env.sh").write_text("CURSOR_PRESENT=maybe\n", encoding="utf-8")
    rc = implement_dispatch.run_dispatch_main(["--implement-tmpdir", str(tmp), "--coder", "codex"])
    assert rc == 2
    assert "CURSOR_PRESENT must be true or false" in capsys.readouterr().err


def test_run_dispatch_forwards_answers_to_step2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tmp = _session(tmp_path)
    answers = tmp / "answers.json"
    answers.write_text('{"answers":[]}\n', encoding="utf-8")
    captured: dict[str, list[str]] = {}

    def fake_run(argv, **_kwargs):  # type: ignore[no-untyped-def]
        if len(argv) >= 4 and argv[2:4] == ["implement", "step2-dispatch"]:
            captured["argv"] = list(argv)
            return subprocess.CompletedProcess(argv, 0, "STATUS=claude_fallback\nORCHESTRATOR_EDIT_AUTHORITY=allowed\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(implement_dispatch.subprocess, "run", fake_run)
    rc = implement_dispatch.run_dispatch_main([
        "--implement-tmpdir", str(tmp),
        "--coder", "codex",
        "--answers", str(answers),
    ])
    assert rc == 0
    argv = captured["argv"]
    assert "--answers" in argv
    assert str(answers) in argv


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
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
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


def test_step2_dispatch_malformed_manifest_empty_delta_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
    monkeypatch.setattr(implement_dispatch, "_run_launcher", _malformed_launcher(lambda _repo, _st: None))
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    _assert_bailed_no_recovery(capsys.readouterr().out)


def test_step2_dispatch_prelaunch_staged_index_blocks_recovery(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    (repo / "staged.txt").write_text("prelaunch staged\n", encoding="utf-8")
    _git(repo, "add", "staged.txt")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def edit_readme(repo_root: Path, _st: implement_dispatch.DispatchState) -> None:
        (repo_root / "README.md").write_text("recovered edit\n", encoding="utf-8")

    monkeypatch.setattr(
        implement_dispatch,
        "_run_launcher",
        _malformed_launcher(edit_readme),
    )
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    _assert_bailed_no_recovery(capsys.readouterr().out)
    assert "PRELAUNCH_INDEX_NONEMPTY=true" in (tmp / "step2-prelaunch-index.env").read_text(encoding="utf-8")


def test_step2_dispatch_rename_recovery_uses_destination_path(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def edit(repo_root: Path, _st: implement_dispatch.DispatchState) -> None:
        _git(repo_root, "mv", "README.md", "RENAMED.md")

    monkeypatch.setattr(implement_dispatch, "_run_launcher", _malformed_launcher(edit))
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    _assert_recovery_envelope(out, "codex")
    recovery_file = Path(_kv_value(out, "RECOVERY_PATHS_FILE"))
    assert _recovery_paths_from_file(recovery_file) == ["RENAMED.md"]


def test_step2_dispatch_baseline_persists_across_answers_resume(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
    state = {"round": 0}

    def fake_launcher(st: implement_dispatch.DispatchState):
        state["round"] += 1
        if state["round"] == 1:
            (repo / "A.txt").write_text("round1\n", encoding="utf-8")
            st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            st.manifest_path.write_text(json.dumps({
                "schema_version": "1",
                "status": "needs_qa",
                "needs_qa": {"questions": [{"id": "q1", "text": "continue?"}]},
            }), encoding="utf-8")
            st.qa_pending_path.write_text(json.dumps({
                "questions": [{"id": "q1", "text": "continue?"}],
            }), encoding="utf-8")
            return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""
        (repo / "B.txt").write_text("round2\n", encoding="utf-8")
        st.manifest_path.write_text(_legacy_malformed_manifest(), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    rc_qa = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc_qa == 0
    assert "STATUS=needs_qa" in capsys.readouterr().out
    answers = tmp / "answers.json"
    answers.write_text('{"answers":[{"id":"q1","text":"yes"}]}\n', encoding="utf-8")
    rc_recovery = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
        "--answers", str(answers),
    ])
    assert rc_recovery == 0
    out = capsys.readouterr().out
    _assert_recovery_envelope(out, "codex")
    recovery_file = Path(_kv_value(out, "RECOVERY_PATHS_FILE"))
    assert _recovery_paths_from_file(recovery_file) == ["A.txt", "B.txt"]


def test_step2_dispatch_non_v1_schema_version_hard_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        readme = repo / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "edit\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            '{"schema_version":2,"status":"complete","summary":"done","checks":"ok"}\n',
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    _assert_bailed_no_recovery(capsys.readouterr().out)


def test_step2_dispatch_launcher_retries_on_clean_post_failure(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
    launcher_calls = 0

    def fake_launcher(st: implement_dispatch.DispatchState):
        nonlocal launcher_calls
        launcher_calls += 1
        if launcher_calls == 1:
            return 1, {"LAUNCHER_EXIT": "1", "MANIFEST_WRITTEN": "false"}, ""
        (repo / "implemented.txt").write_text("done\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps(_complete_manifest_payload()), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    assert launcher_calls == 2
    out = capsys.readouterr().out
    assert "STATUS=complete" in out


def test_step2_dispatch_oos_materialize_failure_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    plugin_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    monkeypatch.setenv("LARCH_TEST_MATERIALIZE_FORCE_FAIL", "true")

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("edited by stub\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps({
            "schema_version": "1",
            "status": "complete",
            "files_touched": [{"path": "README.md"}],
            "commit_message": "stub: edit README",
            "summary_bullets": ["edited README"],
            "tests_added_or_modified": [],
            "todos_left": [],
            "oos_observations": [{"title": "OOS", "description": "manifest OOS", "phase": "implement"}],
        }), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=bailed" in out
    assert "REASON=manifest-oos-materialization-failed" in out


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


def test_commit_main_missing_message_emits_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    rc = implement_dispatch.commit_main(["file.txt"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "COMMITTED=false" in captured.out
    assert "ERROR=--message is required" in captured.out
    assert "review-and-fix commit-fixes" in captured.err


def test_commit_main_stage_all_unknown_option_emits_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    rc = implement_dispatch.commit_main(["--stage-all"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "COMMITTED=false" in captured.out
    assert "ERROR=unknown option: --stage-all" in captured.out
    assert "review-and-fix commit-fixes" in captured.err


def test_commit_main_git_commit_failure_preserves_exit_code(repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "file.txt").write_text("x\n", encoding="utf-8")

    def fake_run(argv, **_kwargs):  # type: ignore[no-untyped-def]
        if str(argv[0]).endswith("git-commit.sh"):
            return subprocess.CompletedProcess(argv, 7, "", "hook rejected commit")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(implement_dispatch, "_run", fake_run)
    rc = implement_dispatch.commit_main(["--message", "Implement thing", "file.txt"])
    assert rc == 7
    captured = capsys.readouterr()
    assert "COMMITTED=false" in captured.out
    assert "ERROR=hook rejected commit" in captured.out


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
    resolved = tmp_path / "resolved-repo"
    resolved.mkdir()
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", lambda _cwd: str(resolved))  # type: ignore[arg-type]
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
    assert cmd[4] == str(resolved)
    add_dir_values = [cmd[index + 1] for index, value in enumerate(cmd) if value == "--add-dir"]
    assert str(resolved) in add_dir_values
    assert f'projects."{resolved}".trust_level="trusted"' in cmd
    assert captured["cwd"] == str(resolved)
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
    resolved = tmp_path / "resolved-repo"
    resolved.mkdir()
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", lambda _cwd: str(resolved))  # type: ignore[arg-type]
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
    assert cmd[cmd.index("--workspace") + 1] == str(resolved)
    assert "--" not in cmd
def _auth_lines(out: str) -> int:
    return sum(1 for line in out.splitlines() if line.startswith("ORCHESTRATOR_EDIT_AUTHORITY="))


def test_step2_dispatch_auth_pair_claude_fallback(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "claude",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=claude_fallback" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=allowed" in out


def test_step2_dispatch_auth_pair_external_bailed(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    (tmp / "step2-baseline.txt").write_text(_git(repo, "rev-parse", "HEAD").stdout, encoding="utf-8")
    (tmp / "step2-spawn-branch.txt").write_text(_git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout, encoding="utf-8")
    (tmp / "step2-plugin-json-baseline.txt").write_text("", encoding="utf-8")
    (tmp / "codex-resume-count.txt").write_text("5\n", encoding="utf-8")
    answers = tmp / "answers.json"
    answers.write_text("{}\n", encoding="utf-8")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
        "--answers", str(answers),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=allowed" not in out


def test_commit_main_pathspec_with_spaced_paths(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    spaced = repo / "path with spaces.txt"
    spaced.write_text("x\n", encoding="utf-8")
    pathspec = tmp_path / "paths.nul"
    pathspec.write_bytes(b"path with spaces.txt\0")
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        stdout = "abc123\n" if argv[:2] == ["git", "rev-parse"] else ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(implement_dispatch, "_run", fake_run)

    rc = implement_dispatch.commit_main([
        "--message", "Recover spaced path",
        "--pathspec-from-file", str(pathspec),
        "--pathspec-file-nul",
        "ignored.txt",
    ])

    assert rc == 0
    assert calls[0][-4:] == ["--only", "--pathspec-from-file", str(pathspec), "--pathspec-file-nul"]
    assert "ignored.txt" not in calls[0]
    out = capsys.readouterr().out
    assert "COMMITTED=true" in out
    assert "SHA=abc123" in out


def test_step2_dispatch_git_add_failure_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
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

    real_run = implement_dispatch.subprocess.run

    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        if len(argv) >= 4 and argv[0:3] == [implement_dispatch.GIT_BIN, "-C", str(repo)] and argv[3] == "add":
            return subprocess.CompletedProcess(argv, 1, "", "index.lock")
        return real_run(argv, check=kwargs.pop("check", False), **kwargs)

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    monkeypatch.setattr(implement_dispatch.subprocess, "run", fake_run)

    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=bailed" in out
    assert "REASON=commit-failed" in out


def test_step2_dispatch_main_branch_prohibited(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    subprocess.run(["git", "-C", str(repo), "checkout", "-B", "main"], check=True, stdout=subprocess.DEVNULL)
    tmp = _session(tmp_path)
    (tmp / "session-env.sh").write_text("ISSUE_NUMBER=123\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "cursor",
        "--cursor-present", "true",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=bailed" in out
    assert "REASON=main-branch-prohibited" in out


def test_step2_dispatch_needs_qa_repair_from_pending(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps({
            "schema_version": "1",
            "status": "needs_qa",
            "needs_qa": {"questions": []},
            "files_touched": [{"path": "implemented.txt"}],
            "summary_bullets": ["q"],
            "commit_message": "x",
            "tests_added_or_modified": [],
            "todos_left": [],
            "oos_observations": [],
        }), encoding="utf-8")
        st.qa_pending_path.write_text(json.dumps({
            "items": [{"area": "auth", "risk": "high", "suggested_check": "verify login"}],
        }), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=needs_qa" in out
    qa_path = tmp / "codex-step2-out" / "qa-pending.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    assert qa["questions"][0]["text"].startswith("Area: auth")


def _seed_external_dispatch_state(
    repo: Path,
    tmp: Path,
    *,
    resume_count: str | None = None,
    spawn_coder: str | None = None,
) -> None:
    (tmp / "step2-baseline.txt").write_text(_git(repo, "rev-parse", "HEAD").stdout, encoding="utf-8")
    (tmp / "step2-spawn-branch.txt").write_text(_git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout, encoding="utf-8")
    plugin_json = repo / ".claude-plugin" / "plugin.json"
    baseline = _git(repo, "hash-object", str(plugin_json)).stdout if plugin_json.is_file() else ""
    (tmp / "step2-plugin-json-baseline.txt").write_text(baseline + ("\n" if baseline else ""), encoding="utf-8")
    if resume_count is not None:
        (tmp / "codex-resume-count.txt").write_text(resume_count + "\n", encoding="utf-8")
    if spawn_coder is not None:
        (tmp / "step2-spawn-coder.txt").write_text(spawn_coder + "\n", encoding="utf-8")


def _complete_manifest_payload(*, path: str = "implemented.txt", commit_message: str = "Implement via fake launcher") -> dict[str, object]:
    return {
        "schema_version": "1",
        "status": "complete",
        "files_touched": [{"path": path, "lines_added": 1, "lines_removed": 0}],
        "tests_added_or_modified": [],
        "summary_bullets": ["Implement the feature"],
        "commit_message": commit_message,
        "todos_left": [],
        "oos_observations": [],
    }


def test_step2_dispatch_qa_loop_exceeded(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    _seed_external_dispatch_state(repo, tmp, resume_count="5")
    answers = tmp_path / "answers.json"
    answers.write_text('{"answers":[{"id":"q1","text":"x"}]}\n', encoding="utf-8")
    launcher_calls = 0

    def fake_launcher(_st: implement_dispatch.DispatchState):
        nonlocal launcher_calls
        launcher_calls += 1
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
        "--answers", str(answers),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert launcher_calls == 0
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=qa-loop-exceeded" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    assert (tmp / "codex-resume-count.txt").is_file()


def test_step2_dispatch_corrupt_resume_counter_bails(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    _seed_external_dispatch_state(repo, tmp, resume_count="garbage")
    answers = tmp_path / "answers.json"
    answers.write_text('{"answers":[{"id":"q1","text":"x"}]}\n', encoding="utf-8")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
        "--answers", str(answers),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=manifest-schema-invalid" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out


def test_step2_dispatch_coder_mismatch_tmpdir_reuse(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    _seed_external_dispatch_state(repo, tmp, spawn_coder="codex")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "cursor",
        "--cursor-present", "true",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=coder-mismatch-tmpdir-reuse" in out
    assert "TOOL=cursor" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    assert (tmp / "step2-spawn-coder.txt").read_text(encoding="utf-8").strip() == "codex"
    assert not (tmp / "cursor-resume-count.txt").exists()


def test_step2_dispatch_detached_head_prohibited(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    subprocess.run(["git", "-C", str(repo), "checkout", "--detach"], check=True, stdout=subprocess.DEVNULL)
    tmp = _session(tmp_path)
    (tmp / "session-env.sh").write_text("ISSUE_NUMBER=2486\nFORKED_TARGET=false\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
    launcher_calls = 0

    def fake_launcher(_st: implement_dispatch.DispatchState):
        nonlocal launcher_calls
        launcher_calls += 1
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
    assert launcher_calls == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=detached-head-prohibited" in out
    assert "TOOL=cursor" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out


def test_step2_dispatch_cap_hit_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(_st: implement_dispatch.DispatchState):
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "false", "STATUS": "cap_hit"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=cap_hit" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out


def test_step2_dispatch_wrapper_validation_failure_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(_st: implement_dispatch.DispatchState):
        return implement_dispatch.WRAPPER_VALIDATION_RC, dict[str, str](), ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=wrapper-validation-failure" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out


def test_step2_dispatch_dirty_state_after_timeout_bails(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(_st: implement_dispatch.DispatchState):
        (repo / "dirty-after-timeout.txt").write_text("x\n", encoding="utf-8")
        return 1, {"LAUNCHER_EXIT": "1", "MANIFEST_WRITTEN": "false"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=dirty-state-after-timeout" in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out


def test_step2_dispatch_codex_nonzero_exit_salvages_complete(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("edited by stub\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path="README.md", commit_message="stub: edit README after self-verify failure")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "1", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=complete" in out
    assert "WARN_CODEX_NONZERO_EXIT=true" in out
    assert "REASON=codex-runtime-failure" not in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    assert _git(repo, "log", "-1", "--pretty=%s").stdout.strip() == "stub: edit README after self-verify failure"
    issues = (tmp / "execution-issues.md").read_text(encoding="utf-8")
    assert "WARN_CODEX_NONZERO_EXIT=true" in issues


@pytest.mark.parametrize(
    "manifest_payload",
    [
        pytest.param(
            {
                "schema_version": "1",
                "status": "needs_qa",
                "needs_qa": {"questions": [{"id": "q1", "text": "stub question?"}]},
            },
            id="needs_qa",
        ),
        pytest.param(
            {
                "schema_version": "1",
                "status": "bailed",
                "bail_reason": "stub-self-bail",
            },
            id="bailed",
        ),
    ],
)
def test_step2_dispatch_codex_nonzero_exit_does_not_salvage_non_complete(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    manifest_payload: dict[str, object],
) -> None:
    _ = repo
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "1", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert _auth_lines(out) == 1
    assert "STATUS=bailed" in out
    assert "REASON=codex-runtime-failure" in out
    assert "WARN_CODEX_NONZERO_EXIT=true" not in out
    assert "STATUS=complete" not in out
    assert "ORCHESTRATOR_EDIT_AUTHORITY=forbidden" in out
    if manifest_payload.get("status") == "bailed":
        assert "REASON=stub-self-bail" not in out


def test_step2_dispatch_complete_emits_scout_kv(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "implemented.txt").write_text("done\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(json.dumps(_complete_manifest_payload()), encoding="utf-8")
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    def fake_normalize_scout(st: implement_dispatch.DispatchState) -> None:
        st.scout_status = "ok"
        st.scout_coder_manifest.parent.mkdir(parents=True, exist_ok=True)
        st.scout_coder_manifest.write_text('{"archetypes":[{"name":"api-contract"}]}\n', encoding="utf-8")
        st.external_scout_marker.write_text("eligible\n", encoding="utf-8")

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", fake_normalize_scout)
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    assert f"SCOUT_CODER_MANIFEST={tmp / 'scout-coder-manifest.json'}" in out
    assert "SCOUT_CODER_STATUS=ok" in out


def test_step2_dispatch_undeclared_path_warning(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tmp = _session(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))

    def fake_launcher(st: implement_dispatch.DispatchState):
        (repo / "README.md").write_text("declared edit\n", encoding="utf-8")
        (repo / "undeclared.txt").write_text("undeclared edit\n", encoding="utf-8")
        st.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        st.manifest_path.write_text(
            json.dumps(_complete_manifest_payload(path="README.md", commit_message="stub: edit README with undeclared side file")),
            encoding="utf-8",
        )
        return 0, {"LAUNCHER_EXIT": "0", "MANIFEST_WRITTEN": "true"}, ""

    monkeypatch.setattr(implement_dispatch, "_run_launcher", fake_launcher)
    monkeypatch.setattr(implement_dispatch, "_normalize_scout", lambda st: setattr(st, "scout_status", "ok"))
    monkeypatch.setattr(implement_dispatch, "_materialize_oos", lambda *_a, **_k: "")
    rc = implement_dispatch.step2_dispatch_main([
        "--tmpdir", str(tmp),
        "--plan-file", str(tmp / "plan.txt"),
        "--feature-file", str(tmp / "feature-description.txt"),
        "--coder", "codex",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=complete" in out
    issues = (tmp / "execution-issues.md").read_text(encoding="utf-8")
    assert "not declared in manifest files_touched/tests_added_or_modified" in issues
    assert "- undeclared.txt" in issues
    assert "- README.md" not in issues


def test_materialize_oos_missing_helper_with_observations_bails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    tmp = tmp_path / "impl"
    tmp.mkdir()
    manifest = tmp / "manifest.json"
    manifest.write_text(json.dumps({"oos_observations": [{"title": "t"}]}), encoding="utf-8")
    st = implement_dispatch.DispatchState(
        repo_root=tmp_path,
        tmpdir=tmp,
        plan_file=tmp / "plan.txt",
        feature_file=tmp / "feature.txt",
        coder="codex",
        cursor_present="false",
        answers_file=None,
        plugin_root=plugin,
        tool_tag="codex",
        manifest_path=manifest,
        manifest_raw_path=tmp / "manifest-raw.json",
        qa_pending_path=tmp / "qa-pending.json",
        transcript_path=tmp / "transcript.txt",
        sidecar_log=tmp / "sidecar.log",
        scout_coder_manifest=tmp / "scout.json",
        launch_scout_manifest=tmp / "launch-scout.json",
        external_scout_marker=tmp / "marker.txt",
        baseline_file=tmp / "baseline.txt",
        prelaunch_porcelain=tmp / "pre.nul",
        postlaunch_porcelain=tmp / "post.nul",
        prelaunch_digests=tmp / "digests.txt",
        prelaunch_index_flag=tmp / "index.env",
        recovery_paths_file=tmp / "recovery.nul",
        resume_count_file=tmp / "resume.txt",
        spawn_branch_file=tmp / "branch.txt",
        plugin_json_baseline_file=tmp / "plugin.txt",
        spawn_coder_file=tmp / "coder.txt",
        runtime_failure_token="codex-runtime-failure",  # noqa: S106
        bailed_no_reason_token="codex-bailed-no-reason",  # noqa: S106
        requires_head_unchanged=False,
        nonzero_exit_warn_token="",
    )
    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_a, **_k: subprocess.CompletedProcess([], 0, "", ""))
    reason = implement_dispatch._materialize_oos(st, oos_observations_nonempty=True)
    assert reason == "manifest-oos-materialization-failed"
    assert (tmp / "materialize-manifest-oos.log").is_file()


def test_codex_launcher_rejects_control_char_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad\nparent"
    bad.mkdir()
    outdir = bad / "out"
    outdir.mkdir()
    for name in ("plan.txt", "feature.txt", "agent.md"):
        (tmp_path / name).write_text("---\ndescription: x\n---\nbody\n", encoding="utf-8")
    args = [
        "--transcript-path", str(outdir / "transcript.txt"),
        "--sidecar-log", str(tmp_path / "sidecar.log"),
        "--manifest-path", str(outdir / "manifest.json"),
        "--qa-pending-path", str(outdir / "qa-pending.json"),
        "--scout-manifest-path", str(outdir / "scout-coder-manifest.json"),
        "--plan-file", str(tmp_path / "plan.txt"),
        "--feature-file", str(tmp_path / "feature.txt"),
        "--agent-prompt", str(tmp_path / "agent.md"),
        "--timeout", "1",
    ]
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    rc = agents.launch_codex_implement_main(args)
    assert rc == 2
    assert "parent is not a directory" in capsys.readouterr().err


def test_codex_launcher_rejects_symlink_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    real = tmp_path / "real-out"
    real.mkdir()
    symlink = tmp_path / "symlink-out"
    symlink.symlink_to(real)
    for name in ("plan.txt", "feature.txt", "agent.md"):
        (tmp_path / name).write_text("---\ndescription: x\n---\nbody\n", encoding="utf-8")
    args = [
        "--transcript-path", str(symlink / "transcript.txt"),
        "--sidecar-log", str(tmp_path / "sidecar.log"),
        "--manifest-path", str(symlink / "manifest.json"),
        "--qa-pending-path", str(symlink / "qa-pending.json"),
        "--scout-manifest-path", str(symlink / "scout-coder-manifest.json"),
        "--plan-file", str(tmp_path / "plan.txt"),
        "--feature-file", str(tmp_path / "feature.txt"),
        "--agent-prompt", str(tmp_path / "agent.md"),
        "--timeout", "1",
    ]
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    rc = agents.launch_codex_implement_main(args)
    assert rc == 2
    assert "parent is not a directory" in capsys.readouterr().err


def test_codex_launcher_rejects_transcript_parent_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    outdir = tmp_path / "out"
    outdir.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    for name in ("plan.txt", "feature.txt", "agent.md"):
        (tmp_path / name).write_text("---\ndescription: x\n---\nbody\n", encoding="utf-8")
    args = [
        "--transcript-path", str(other / "transcript.txt"),
        "--sidecar-log", str(tmp_path / "sidecar.log"),
        "--manifest-path", str(outdir / "manifest.json"),
        "--qa-pending-path", str(outdir / "qa-pending.json"),
        "--scout-manifest-path", str(outdir / "scout-coder-manifest.json"),
        "--plan-file", str(tmp_path / "plan.txt"),
        "--feature-file", str(tmp_path / "feature.txt"),
        "--agent-prompt", str(tmp_path / "agent.md"),
        "--timeout", "1",
    ]
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    rc = agents.launch_codex_implement_main(args)
    assert rc == 2
    assert "must share the parent directory" in capsys.readouterr().err


def test_codex_launcher_codex_home_outside_implement_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/codex" if name == "codex" else "/bin/true")
    monkeypatch.setattr(agents, "_record_implement_timing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_record_usage_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_mirror_codex_quota_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_promote_inner_done", lambda *_args, **_kwargs: None)
    captured: dict[str, str] = {}

    def fake_run_external_agent_with_auth_retries(**kwargs):  # type: ignore[no-untyped-def]
        captured["home"] = agents.os.environ["CODEX_HOME"]
        output = kwargs["output"]
        stdout_path = kwargs["stdout_path"]
        output.write_text("codex transcript\n", encoding="utf-8")
        stdout_path.write_text('{"type":"turn_completed"}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    rc = agents.launch_codex_implement_main(args)
    assert rc == 0
    home = Path(captured["home"]).resolve()
    assert not str(home).startswith(str(tmp_path.resolve()))


def test_codex_launcher_env_key_auth_argv_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/codex" if name == "codex" else "/bin/true")
    monkeypatch.setattr(agents, "_record_implement_timing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_record_usage_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_mirror_codex_quota_from_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_promote_inner_done", lambda *_args, **_kwargs: None)
    captured: dict[str, object] = {}

    def fake_run_external_agent_with_auth_retries(**kwargs):  # type: ignore[no-untyped-def]
        cmd = list(kwargs["cmd"])
        captured["cmd"] = cmd
        captured["config"] = (Path(agents.os.environ["CODEX_HOME"]) / "config.toml").read_text(encoding="utf-8")
        output = kwargs["output"]
        stdout_path = kwargs["stdout_path"]
        output.write_text("ok\n", encoding="utf-8")
        stdout_path.write_text('{"type":"turn_completed"}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    rc = agents.launch_codex_implement_main(args)
    assert rc == 0
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert 'model_provider="openai-larch-env"' in cmd
    config = str(captured["config"])
    assert "api_key" not in config
    assert "OPENAI_API_KEY" not in config


def test_cursor_launcher_continues_when_config_copy_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    args = _launcher_args(tmp_path)
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/cursor" if name == "cursor" else "/bin/true")
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(agents, "cursor_preread_service_token", lambda: None)
    monkeypatch.setattr(agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(agents, "_record_implement_timing", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_record_cursor_implement_usage", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_promote_inner_done", lambda *_args, **_kwargs: None)

    def boom_copy(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise OSError("permission denied")

    real_is_file = Path.is_file

    def selective_is_file(self: Path) -> bool:
        if str(self).endswith(".cursor/cli-config.json"):
            return True
        return real_is_file(self)

    monkeypatch.setattr(agents.shutil, "copyfile", boom_copy)
    monkeypatch.setattr(Path, "is_file", selective_is_file)

    def fake_run_external_agent_with_auth_retries(**kwargs):  # type: ignore[no-untyped-def]
        output = kwargs["output"]
        output.write_text('{"usage":{"inputTokens":1}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    rc = agents.launch_cursor_implement_main(args)
    assert rc == 0
    assert "LAUNCHER_EXIT=0" in capsys.readouterr().out


def test_auth_retry_includes_stderr_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    stderr_path = tmp_path / "sidecar.log"
    stderr_path.write_text("auth error\n", encoding="utf-8")
    seen: list[Path] = []

    def fake_verdict(_tool: str, *paths: Path) -> str:
        seen.extend(paths)
        return "auth" if stderr_path in paths else ""

    def fake_run_external_agent(**_kwargs):  # type: ignore[no-untyped-def]
        return agents.RunExternalAgentResult(2, output)

    monkeypatch.setattr(agents, "external_auth_verdict", fake_verdict)
    monkeypatch.setattr(agents, "run_external_agent", fake_run_external_agent)
    monkeypatch.setattr(agents, "_auth_retry_limit", lambda: 2)
    monkeypatch.setattr(agents, "external_serial_lock_acquire", lambda _tool: object())
    monkeypatch.setattr(agents, "external_serial_lock_release_after", lambda _state: None)
    result = agents._run_external_agent_with_auth_retries(
        tool="codex",
        output=output,
        timeout_seconds=1,
        cmd=["codex", "exec", "hi"],
        stderr_path=stderr_path,
    )
    assert result.exit_code == 2
    assert stderr_path in seen
