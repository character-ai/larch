# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pytest

from larch.agents import agents
from larch.agents import _run_external
from larch.implement import implement_dispatch
from larch.implement import (
    dispatch_helpers,
    dispatch_leg_runner,
    dispatch_manifest,
    ship_state,
)
from larch.implement.dispatch_helpers import resolve_tmpdir_path
from larch.core import config
from larch.core.proc import CommandResult
from larch.core import logging_util
from test_support import make_implement_tmpdir


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False)


def test_tracking_sentinel_values_use_verified_rust_entrypoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel = tmp_path / "parent-issue.md"
    sentinel.write_text("ISSUE_NUMBER=7\nRUN_ID=run-1\nADOPTED=true\n", encoding="utf-8")
    calls: list[str] = []

    def fake_read(
        _runner: object, *, sentinel: str, cwd: str | None = None
    ) -> dispatch_helpers.rust_runtime.TrackingIssueSentinelOutput:
        assert cwd is None
        calls.append(sentinel)
        return dispatch_helpers.rust_runtime.TrackingIssueSentinelOutput(
            failed=False,
            issue_number="7",
            run_id="run-1",
            adopted="true",
        )

    def fail_python_cli(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("tracking sentinel bypassed scripts/larch.sh")

    monkeypatch.setattr(
        dispatch_helpers.rust_runtime, "tracking_issue_read_sentinel", fake_read
    )
    monkeypatch.setattr(dispatch_helpers, "_invoke_cli", fail_python_cli)

    assert dispatch_helpers._tracking_sentinel_values(sentinel) == {
        "ISSUE_NUMBER": "7",
        "RUN_ID": "run-1",
        "ADOPTED": "true",
    }
    assert calls == [str(sentinel)]


@pytest.fixture(autouse=True)
def quiet_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.delenv("LARCH_CLAUDE_PID", raising=False)
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
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True
    ).stdout.strip()
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", base_sha], cwd=root, check=True)
    subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
        cwd=root, check=True,
    )
    monkeypatch.chdir(root)
    return root


@pytest.mark.parametrize(
    ("script_name", "verb"),
    [
        ("run-step-checks.sh", "run-step-checks"),
        ("step-5-review.sh", "step-5-review"),
        ("step-5-resume.sh", "step-5-resume"),
        ("step-6-entry.sh", "step-6-entry"),
        ("step-8-ship.sh", "step-8-ship"),
    ],
)
def test_converted_bgjob_launchers_are_thin_wrappers(script_name: str, verb: str) -> None:
    root = Path(__file__).resolve().parents[3]
    source = (root / "skills" / "implement" / "scripts" / script_name).read_text(encoding="utf-8")
    assert f'implement {verb} "$@"' in source
    assert "bgjob start" not in source
    assert "registry" not in source


def test_step8_rust_patch_allowlist_matches_python_ship_state() -> None:
    source = (
        Path(__file__).resolve().parents[3]
        / "crates/larch-core/src/implement/ship_state.rs"
    ).read_text(encoding="utf-8")
    block = source.split("const SHIP_STATE_ALLOWED_KEYS", 1)[1].split("];", 1)[0]
    rust_keys = frozenset(re.findall(r'"([A-Z][A-Z0-9_]*)"', block))
    assert rust_keys == ship_state._ALLOWED_SHIP_STATE_KEYS  # pyright: ignore[reportPrivateUsage]


def test_resolve_tmpdir_path_empty_uses_default(tmp_path: Path) -> None:
    tmp = make_implement_tmpdir(tmp_path)

    assert resolve_tmpdir_path(tmpdir=tmp, raw="", default_relpath="paths.nul") == tmp / "paths.nul"


def test_resolve_tmpdir_path_root_relative_argv_rebases_to_tmpdir(tmp_path: Path) -> None:
    tmp = make_implement_tmpdir(tmp_path)

    assert resolve_tmpdir_path(
        tmpdir=tmp,
        raw="/step2-recovery-paths.nul",
        default_relpath="default.nul",
    ) == tmp / "step2-recovery-paths.nul"


def test_clone_tag_derivation_truncates_sanitized_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/" + ("é" * 20))

    assert implement_dispatch._derive_clone_tag_full() == "_" * 32


def test_clone_tag_derivation_keeps_one_underscore_per_invalid_byte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/!!!")

    assert implement_dispatch._derive_clone_tag_full() == "___"


def test_clone_tag_derivation_empty_basename_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/")

    assert implement_dispatch._derive_clone_tag_full() == "_"


def test_clone_tag_derivation_strips_trailing_slash_from_pwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/logical/larch4/")

    assert implement_dispatch._derive_clone_tag_full() == "larch4"


def test_clone_tag_derivation_uses_pwd_not_physical_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    physical = tmp_path / "physical"
    physical.mkdir()
    monkeypatch.chdir(physical)
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/logical/logical clone")

    assert physical.name != "logical clone"
    assert implement_dispatch._derive_clone_tag_full() == "logical_clone"


def test_clone_expected_tmpdir_prefix_reuses_clone_tag_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLONE_TAG", raising=False)
    monkeypatch.setenv("PWD", "/logical/repo.name")

    assert implement_dispatch._clone_expected_tmpdir_prefix() == f"claude-implement-{implement_dispatch._derive_clone_tag_full()}-"


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
        porcelain=implement_dispatch.RecoveryPorcelainInputs(
            prelaunch_porcelain=pre,
            postlaunch_porcelain=post,
            prelaunch_digests=digests,
        ),
        out_file=out,
    )

    assert ok is True
    paths = set(out.read_bytes().rstrip(b"\0").split(b"\0"))
    assert b"README.md" in paths
    assert b"new.txt" in paths
    assert all(not p.startswith(b".tmp-impl/") for p in paths)


def _recovery_paths_from_file(path: Path) -> list[str]:
    return [p.decode() for p in path.read_bytes().split(b"\0") if p]


def test_step2_dispatch_adapter_uses_durable_rejoin_contract() -> None:
    root = Path(__file__).resolve().parents[3]
    source = (root / "skills" / "implement" / "scripts" / "step-2-dispatch.sh").read_text(encoding="utf-8")

    assert "bgjob adapt" in source
    assert "--step implement-step2-dispatch" in source
    assert "--budget-s 7200" in source
    assert "--bgjob-child" in source
    assert "--merge-result-env" in source
    assert "REPLACE_COMPLETED_RESULT=true" in source
    assert "--replace-completed-result" in source


def test_recovery_paths_git_mv_includes_source_path_and_commit_is_clean(repo: Path) -> None:
    tmp = repo / ".tmp-impl"
    tmp.mkdir()
    pre = tmp / "pre.nul"
    post = tmp / "post.nul"
    digests = tmp / "digests.txt"
    out = tmp / "out.nul"
    pre.write_bytes(_git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.encode())
    digests.write_text("", encoding="utf-8")
    _git(repo, "mv", "README.md", "RENAMED.md")
    post.write_bytes(_git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.encode())
    ok = implement_dispatch.compute_recovery_paths(
        repo_root=repo,
        tmpdir=tmp,
        porcelain=implement_dispatch.RecoveryPorcelainInputs(
            prelaunch_porcelain=pre,
            postlaunch_porcelain=post,
            prelaunch_digests=digests,
        ),
        out_file=out,
    )
    assert ok is True
    paths = _recovery_paths_from_file(out)
    assert "README.md" in paths
    assert "RENAMED.md" in paths
    result = subprocess.run(
        ["git", "-C", str(repo), "commit", "--only", "--pathspec-from-file", str(out), "--pathspec-file-nul", "-m", "mv"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert _git(repo, "diff", "--cached", "--name-only").stdout == ""


_STEP5_COMMIT_OK = "COMMITTED=true\nSHA=abc123\nERROR=\nCOMMIT_OUTCOME=ok\n"
_STEP5_COMMIT_NOOP = "COMMITTED=false\nSHA=\nERROR=\nCOMMIT_OUTCOME=noop\n"
_STEP5_COMMIT_FAILED = "COMMITTED=false\nSHA=\nERROR=no review delta paths\nCOMMIT_OUTCOME=failed\n"
_STEP5_ROUTE_OK = _STEP5_COMMIT_OK + "NEXT_ACTION=continue\n"
_STEP5_ROUTE_NOOP = _STEP5_COMMIT_NOOP + "NEXT_ACTION=continue\n"
_STEP5_ROUTE_STALL = _STEP5_COMMIT_FAILED + "NEXT_ACTION=stall\n"


def test_persist_ship_seed_context_refreshes_blank_manifest_path(tmp_path: Path) -> None:
    impl = make_implement_tmpdir(tmp_path)
    (impl / "ship-seed-input.env").write_text("MANIFEST_PATH=\nTOOL_LABEL=\n", encoding="utf-8")
    (impl / "manifest.json").write_text('{"schema_version":"1"}\n', encoding="utf-8")
    (impl / "bootstrap-routing.env").write_text("coder=codex\n", encoding="utf-8")

    implement_dispatch._persist_ship_seed_context(impl)

    seed = (impl / "ship-seed-input.env").read_text(encoding="utf-8")
    assert f"MANIFEST_PATH={impl / 'manifest.json'}" in seed
    assert "TOOL_LABEL=Codex" in seed


def test_kill_active_leg_clears_tracked_process(monkeypatch: pytest.MonkeyPatch) -> None:
    killed: list[int] = []

    class FakeProcess:
        pid = 5150
        returncode = None

        def poll(self) -> int | None:
            return self.returncode

        def wait(self, timeout: float | None = None) -> int:  # pylint: disable=unused-argument
            self.returncode = -15
            return -15

    process = FakeProcess()
    implement_dispatch._LEG_STATE.active = cast("subprocess.Popen[str]", process)
    monkeypatch.setattr(implement_dispatch, "_descendants", lambda _pid: [])
    monkeypatch.setattr(dispatch_leg_runner, "_descendants", lambda _pid: [])
    monkeypatch.setattr(implement_dispatch.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(implement_dispatch.os, "killpg", lambda _pgid, _sig: killed.append(1))

    implement_dispatch._kill_active_leg()

    assert killed == [1, 1]
    assert implement_dispatch._LEG_STATE.active is None


def test_run_leg_with_timeout_fails_closed_when_active_leg_publish_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    killed: list[int] = []

    class FakeProcess:
        pid = 4242
        returncode = None
        stdout = None
        stderr = None

        def poll(self) -> int | None:
            return self.returncode

        def wait(self, timeout: float | None = None) -> int:  # pylint: disable=unused-argument
            self.returncode = -9
            return -9

    def fake_popen(*_args: object, **_kwargs: object) -> FakeProcess:
        return FakeProcess()

    monkeypatch.setattr(implement_dispatch.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(dispatch_leg_runner, "_publish_active_leg_record", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dispatch_leg_runner, "_kill_leg_process_group", lambda process: killed.append(process.pid))
    monkeypatch.setattr(dispatch_leg_runner, "_drain_leg_pipes", lambda _process, **_kwargs: ("", ""))

    result = implement_dispatch._run_leg_with_timeout(argv=["checks", "run-relevant"], deadline_ms=1, label="checks")

    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 1
    assert result.stderr == "checks active-leg publication failed"
    assert killed == [4242]


def test_run_leg_with_timeout_returns_child_result_when_publication_fails_after_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    killed: list[int] = []

    class FakeProcess:
        pid = 4242
        returncode = 0
        stdout = None
        stderr = None

        def poll(self) -> int | None:
            return self.returncode

        def wait(self, timeout: float | None = None) -> int:  # pylint: disable=unused-argument
            return 0

    def fake_popen(*_args: object, **_kwargs: object) -> FakeProcess:
        return FakeProcess()

    monkeypatch.setattr(implement_dispatch.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(dispatch_leg_runner, "_publish_active_leg_record", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dispatch_leg_runner, "_kill_leg_process_group", lambda process: killed.append(process.pid))
    monkeypatch.setattr(dispatch_leg_runner, "_drain_leg_pipes", lambda _process, **_kwargs: ("child stdout\n", "child stderr\n"))

    result = implement_dispatch._run_leg_with_timeout(argv=["checks", "run-relevant"], deadline_ms=1, label="checks")

    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 0
    assert result.stdout == "child stdout\n"
    assert result.stderr == "child stderr\n"
    assert not killed


def test_dispatcher_finally_does_not_clear_foreign_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    own: dict[str, object] = {"pid": 123, "pgid": 123, "start_time": "one", "command_signature": "cmd", "owner_token": "owner-1", "writer_pid": 1}
    foreign: dict[str, object] = {"pid": 124, "pgid": 124, "start_time": "two", "command_signature": "cmd", "owner_token": "owner-2", "writer_pid": 2}
    path = tmp_path / config.ACTIVE_LEG_IDENTITY_FILE
    path.write_text(json.dumps(foreign), encoding="utf-8")

    implement_dispatch._clear_active_leg_record(own)

    assert json.loads(path.read_text(encoding="utf-8"))["owner_token"] == "owner-2"


def _dynamic_archetype(name: str) -> dict[str, object]:
    return {
        "name": name,
        "focus_area": "architecture",
        "weight": 1,
        "rationale": "Architecture changed.",
        "prompt_body": "Check architecture risks in the changed code.",
    }


# Mirrors REVIEW_RESERVED in crates/larch-core/src/design/plan_scout.rs so unit
# tests can stub the Rust-owned scout filter without a CI binary.
_REVIEW_RESERVED_SLUGS = {
    "generic",
    "structure",
    "correctness",
    "testing",
    "security",
    "edge-cases",
    "plan-fidelity",
    "code-reviewer",
    "reviewer-structure",
    "reviewer-correctness",
    "reviewer-testing",
    "reviewer-security",
    "reviewer-edge-cases",
    "reviewer-plan-fidelity",
}


def _stub_scout_filter_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace `_invoke_larch` scout filter-manifest with a review-mode stub.

    `python-tests` CI shards have no Rust binary. Production still reaches the
    verified bootstrap; these unit tests only need the filter contract.
    """

    def fake_larch(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert list(args[:2]) == ["scout", "filter-manifest"], args
        input_path = Path(str(args[2]))
        output_path = Path(str(args[3]))
        max_archetypes = 1
        mode = "review"
        argv = [str(item) for item in args[4:]]
        while argv:
            flag = argv.pop(0)
            if flag == "--max-archetypes":
                max_archetypes = int(argv.pop(0))
            elif flag == "--mode":
                mode = argv.pop(0)
            else:
                raise AssertionError(f"unexpected filter-manifest flag: {flag}")
        assert mode == "review"
        data = json.loads(input_path.read_text(encoding="utf-8"))
        kept: list[object] = []
        for item in data.get("archetypes", []):
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str) or name in _REVIEW_RESERVED_SLUGS:
                continue
            if len(kept) < max_archetypes:
                kept.append(item)
        output_path.write_text(json.dumps({"archetypes": kept}, separators=(",", ":")) + "\n", encoding="utf-8")
        status = "empty" if not kept else "ok"
        stdout = (
            f"SCOUT_STATUS={status}\n"
            f"SCOUT_MANIFEST={output_path}\n"
            f"SCOUT_ARCHETYPE_COUNT={len(kept)}\n"
        )
        return subprocess.CompletedProcess(list(args), 0, stdout, "")

    monkeypatch.setattr(dispatch_manifest, "_invoke_larch", fake_larch)


def test_normalize_coder_scout_producer_subagent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_scout_filter_manifest(monkeypatch)
    raw = tmp_path / "scout-coder-manifest.raw.json"
    raw.write_text('{"archetypes":[]}\n', encoding="utf-8")
    status = implement_dispatch.normalize_coder_scout(tmpdir=tmp_path, input_path=raw, producer="subagent")
    assert status == "ok"
    status_env = (tmp_path / "step2-scout-coder-status.env").read_text(encoding="utf-8")
    assert "SCOUT_CODER_PRODUCER=subagent" in status_env


def test_normalize_coder_scout_intentional_empty_is_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_scout_filter_manifest(monkeypatch)
    raw = tmp_path / "raw.json"
    raw.write_text('{"archetypes":[]}\n', encoding="utf-8")
    status = implement_dispatch.normalize_coder_scout(tmpdir=tmp_path, input_path=raw, producer="main-agent")
    assert status == "ok"
    assert (tmp_path / "step2-external-scout-eligible.txt").is_file()
    assert "SCOUT_CODER_STATUS=ok" in (tmp_path / "step2-scout-coder-status.env").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "scout-coder-manifest.json").read_text(encoding="utf-8")) == {"archetypes": []}


def test_normalize_coder_scout_filtered_to_zero_is_invalid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _stub_scout_filter_manifest(monkeypatch)
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"archetypes": [_dynamic_archetype("correctness"), _dynamic_archetype("testing")]}) + "\n", encoding="utf-8")
    status = implement_dispatch.normalize_coder_scout(tmpdir=tmp_path, input_path=raw, producer="main-agent")
    captured = capsys.readouterr()
    assert status == "missing-or-invalid"
    assert "dynamic-archetype manifest missing or invalid" in captured.err
    assert not (tmp_path / "step2-external-scout-eligible.txt").exists()
    assert "SCOUT_CODER_STATUS=missing-or-invalid" in (tmp_path / "step2-scout-coder-status.env").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "scout-coder-manifest.json").read_text(encoding="utf-8")) == {"archetypes": []}


def test_normalize_coder_scout_uses_review_mode_so_arch_survives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_scout_filter_manifest(monkeypatch)
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"archetypes": [_dynamic_archetype("arch")]}) + "\n", encoding="utf-8")
    status = implement_dispatch.normalize_coder_scout(tmpdir=tmp_path, input_path=raw, producer="external")
    assert status == "ok"
    manifest = json.loads((tmp_path / "scout-coder-manifest.json").read_text(encoding="utf-8"))
    assert [item["name"] for item in manifest["archetypes"]] == ["arch"]


def test_normalize_coder_scout_caps_to_one_archetype(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_scout_filter_manifest(monkeypatch)
    raw = tmp_path / "raw.json"
    raw.write_text(
        json.dumps({"archetypes": [_dynamic_archetype("arch"), _dynamic_archetype("api-contract")]}) + "\n",
        encoding="utf-8",
    )
    status = implement_dispatch.normalize_coder_scout(tmpdir=tmp_path, input_path=raw, producer="external")
    assert status == "ok"
    manifest = json.loads((tmp_path / "scout-coder-manifest.json").read_text(encoding="utf-8"))
    assert [item["name"] for item in manifest["archetypes"]] == ["arch"]


def _materialize_dispatch_state(tmp_path: Path, observations: object) -> implement_dispatch.DispatchState:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    tmp = tmp_path / "impl"
    tmp.mkdir()
    manifest = tmp / "manifest.json"
    manifest.write_text(json.dumps({"oos_observations": observations}), encoding="utf-8")
    return implement_dispatch.DispatchState(
        repo_root=tmp_path,
        tmpdir=tmp,
        plan_file=tmp / "plan.txt",
        feature_file=tmp / "feature.txt",
        coder="codex",
        cursor_present="false",
        cursor_binary_found="true",
        codex_binary_found="true",
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
        completion_retry_state_file=tmp / "completion-retry-state.env",
        completion_retry_feedback_file=tmp / "completion-retry.md",
        spawn_branch_file=tmp / "branch.txt",
        spawn_coder_file=tmp / "coder.txt",
        runtime_failure_token="codex-runtime-failure",  # noqa: S106
        bailed_no_reason_token="codex-bailed-no-reason",  # noqa: S106
        requires_head_unchanged=False,
        nonzero_exit_warn_token="",
    )


def test_materialize_oos_full_failure_with_observations_bails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    st = _materialize_dispatch_state(tmp_path, [{"title": "t"}])
    calls: list[bool] = []

    def fake_larch(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "materialize-manifest" not in args:
            return subprocess.CompletedProcess(list(args), 0, "", "")
        count_only = "--count-only" in args
        calls.append(count_only)
        if count_only:
            return subprocess.CompletedProcess(list(args), 0, "1\n", "")
        return subprocess.CompletedProcess(list(args), 1, "", "forced materialize failure\n")

    monkeypatch.setattr(dispatch_manifest, "_invoke_larch", fake_larch)
    reason = implement_dispatch._materialize_oos(st, oos_observations_nonempty=True)

    assert reason == "manifest-oos-materialization-failed"
    assert calls == [True, False]
    assert (st.tmpdir / "materialize-manifest-oos.log").is_file()
    assert "forced materialize failure" in (st.tmpdir / "materialize-manifest-oos.log").read_text(encoding="utf-8")


def test_oos_materialize_should_bail_gates_positive_count_on_failure() -> None:
    assert (
        implement_dispatch._oos_materialize_should_bail(
            count_rc=0,
            count_str="1",
            oos_nonempty=True,
            materialize_failed=False,
        )
        is False
    )
    assert (
        implement_dispatch._oos_materialize_should_bail(
            count_rc=0,
            count_str="1",
            oos_nonempty=False,
            materialize_failed=True,
        )
        is True
    )
    assert (
        implement_dispatch._oos_materialize_should_bail(
            count_rc=1,
            count_str="0",
            oos_nonempty=False,
            materialize_failed=False,
        )
        is True
    )


def test_materialize_oos_successful_dual_pass_positive_count_does_not_bail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = _materialize_dispatch_state(tmp_path, [{"title": "t"}])
    calls: list[bool] = []

    def fake_larch(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append("--count-only" in args)
        return subprocess.CompletedProcess(list(args), 0, "1\n", "")

    monkeypatch.setattr(dispatch_manifest, "_invoke_larch", fake_larch)

    assert implement_dispatch._materialize_oos(st, oos_observations_nonempty=True) == ""
    assert calls == [True, False]


def test_materialize_oos_count_type_error_runs_full_pass_and_bails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = _materialize_dispatch_state(tmp_path, [{"title": "t"}])
    calls: list[bool] = []

    def fake_larch(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        count_only = "--count-only" in args
        calls.append(count_only)
        if count_only:
            return subprocess.CompletedProcess(list(args), 1, "", "bad count\n")
        return subprocess.CompletedProcess(list(args), 0, "", "")

    monkeypatch.setattr(dispatch_manifest, "_invoke_larch", fake_larch)

    assert implement_dispatch._materialize_oos(st, oos_observations_nonempty=True) == "manifest-oos-materialization-failed"
    assert calls == [True, False]
    assert "bad count" in (st.tmpdir / "materialize-manifest-oos.log").read_text(encoding="utf-8")


def test_materialize_oos_preassignment_failure_and_full_failure_logs_both(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = _materialize_dispatch_state(tmp_path, [{"title": "t"}])
    calls: list[bool] = []

    def fake_larch(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "materialize-manifest" not in args:
            return subprocess.CompletedProcess(list(args), 0, "", "")
        count_only = "--count-only" in args
        calls.append(count_only)
        detail = "count boom\n" if count_only else "full boom\n"
        return subprocess.CompletedProcess(list(args), 1, "", detail)

    monkeypatch.setattr(dispatch_manifest, "_invoke_larch", fake_larch)

    assert implement_dispatch._materialize_oos(st, oos_observations_nonempty=True) == "manifest-oos-materialization-failed"
    assert calls == [True, False]
    log_text = (st.tmpdir / "materialize-manifest-oos.log").read_text(encoding="utf-8")
    assert "count boom" in log_text
    assert "full boom" in log_text


def test_materialize_oos_count_result_is_bound_as_string(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = _materialize_dispatch_state(tmp_path, [{"title": "t"}])

    def fake_larch(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        stdout = "1\n" if "--count-only" in args else ""
        return subprocess.CompletedProcess(list(args), 0, stdout, "")

    monkeypatch.setattr(dispatch_manifest, "_invoke_larch", fake_larch)

    assert implement_dispatch._materialize_oos(st, oos_observations_nonempty=True) == ""


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

    monkeypatch.setattr(_run_external, "external_auth_verdict", fake_verdict)
    monkeypatch.setattr(_run_external, "run_external_agent", fake_run_external_agent)
    monkeypatch.setattr(_run_external, "_auth_retry_limit", lambda: 2)
    monkeypatch.setattr(_run_external, "external_startup_lock_acquire", lambda **_kwargs: object())
    monkeypatch.setattr(_run_external, "external_startup_lock_release_after", lambda **_kwargs: None)
    result = _run_external._run_external_agent_with_auth_retries(
        tool="codex",
        output=output,
        timeout_seconds=1,
        cmd=["codex", "exec", "hi"],
        stderr_path=stderr_path,
    )
    assert result.exit_code == 2
    assert stderr_path in seen


def test_parse_kv_keeps_first_duplicate_stdout_value() -> None:
    assert implement_dispatch._parse_kv("STATUS=first\nSTATUS=second\nBAD-key=no\n") == {"STATUS": "first"}
