# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pytest

from larch import io as larch_io

from larch.agents import agents
from larch.agents import _run_external
from larch.implement import implement_dispatch
from larch.implement import (
    dispatch_commit_route,
    dispatch_helpers,
    dispatch_leg_runner,
    dispatch_manifest,
    dispatch_recovery,
    self_edit_log,
    ship_state,
)
from larch.implement.dispatch_helpers import resolve_tmpdir_path
from larch.core import config
from larch.core.proc import CommandResult
from larch.core import logging_util
from test_support import make_implement_tmpdir

@pytest.fixture(autouse=True)
def _answer_resolve_repo_root(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    """Answer the out-of-process `checks-result-identity resolve-repo-root` verb.

    That verb is Rust-owned now, and the verified bootstrap needs an installed
    larch binary a unit test does not have. This reads the same persisted
    session key the command reads and leaves every other verb untouched.
    """
    real_invoke = dispatch_commit_route._invoke_larch

    def fake_invoke(args: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        argv = [str(item) for item in args]
        if argv[:3] != ["implement", "checks-result-identity", "resolve-repo-root"]:
            return real_invoke(args, **cast("Any", kwargs))
        tmpdir = Path(argv[argv.index("--implement-tmpdir") + 1])
        root = (
            larch_io.read_kv(path=tmpdir / "session-env.sh", key="REPO_ROOT", default="", first_match=True)
            .strip()
            .strip("'\"")
        )
        if not root:
            return subprocess.CompletedProcess(argv, 2, "", "ERROR=REPO_ROOT missing from session-env.sh\n")
        return subprocess.CompletedProcess(argv, 0, f"REPO_ROOT={root}\n", "")

    monkeypatch.setattr(dispatch_commit_route, "_invoke_larch", fake_invoke)


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


def test_checks_commit_route_step3_does_not_touch_legacy_sidecars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp))

    def fake_impl(args: Any, implement_tmpdir: Path) -> int:
        assert args.checks_site == "step3"
        assert args.commit_site == "step4"
        assert implement_tmpdir == tmp
        return 0

    monkeypatch.setattr(dispatch_commit_route, "_checks_commit_route_main_impl", fake_impl)

    rc = dispatch_commit_route.checks_commit_route_main(["--checks-site", "step3", "--commit-site", "step4"])

    assert rc == 0


def test_checks_step_for_site_preserves_budgets() -> None:
    assert dispatch_commit_route._checks_step_for_site("step3") == ("implement-step3-checks", 15600)  # pyright: ignore[reportPrivateUsage]
    assert dispatch_commit_route._checks_step_for_site("step5-self-review") == (  # pyright: ignore[reportPrivateUsage]
        "implement-checks-step5-self-review",
        14700,
    )


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
        / "crates/larch-cli/src/implement_ship_commands.rs"
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


def test_commit_main_passes_named_files_once(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        stdout = "abc123\n" if argv[:2] == ["git", "rev-parse"] else ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(dispatch_recovery, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(implement_dispatch, "_run", fake_run)
    monkeypatch.setattr(dispatch_recovery, "_run", fake_run)

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
        if list(argv[1:3]) == ["git", "commit"]:
            return subprocess.CompletedProcess(argv, 7, "", "hook rejected commit")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(dispatch_recovery, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(implement_dispatch, "_run", fake_run)
    monkeypatch.setattr(dispatch_recovery, "_run", fake_run)
    rc = implement_dispatch.commit_main(["--message", "Implement thing", "file.txt"])
    assert rc == 7
    captured = capsys.readouterr()
    assert "COMMITTED=false" in captured.out
    assert "ERROR=hook rejected commit" in captured.out


_STEP5_COMMIT_OK = "COMMITTED=true\nSHA=abc123\nERROR=\nCOMMIT_OUTCOME=ok\n"
_STEP5_COMMIT_NOOP = "COMMITTED=false\nSHA=\nERROR=\nCOMMIT_OUTCOME=noop\n"
_STEP5_COMMIT_FAILED = "COMMITTED=false\nSHA=\nERROR=no review delta paths\nCOMMIT_OUTCOME=failed\n"
_STEP5_ROUTE_OK = _STEP5_COMMIT_OK + "NEXT_ACTION=continue\n"
_STEP5_ROUTE_NOOP = _STEP5_COMMIT_NOOP + "NEXT_ACTION=continue\n"
_STEP5_ROUTE_STALL = _STEP5_COMMIT_FAILED + "NEXT_ACTION=stall\n"


def _setup_commit_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    commit_stdout: str,
    commit_rc: int = 0,
    commit_stderr: str = "",
    porcelain_stdout: str = "",
    porcelain_rc: int = 0,
    seed_rc: int = 0,
) -> tuple[Path, list[list[str]], list[list[str]]]:
    impl = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    invoke_calls: list[list[str]] = []
    seed_calls: list[list[str]] = []

    def fake_invoke(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        call = list(args)
        invoke_calls.append(call)
        if call == ["review-and-fix", "commit-fixes", "--stage-all"]:
            return subprocess.CompletedProcess(call, commit_rc, commit_stdout, commit_stderr)
        if call[:2] == ["run-log", "append-failure"]:
            return subprocess.CompletedProcess(call, 0, "", "")
        if call[:2] == ["implement", "step-8-seed-initial"]:
            return fake_seed(call)
        return subprocess.CompletedProcess(call, 0, "", "")

    def fake_seed(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        call = list(args)
        seed_calls.append(call)
        if seed_rc == 0:
            (impl / "ship-pr-state.sh").write_text(
                "STALL_TRACKING=true\nSTALL_STEP=seeded\nBAIL_REASON=seeded\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(call, seed_rc, "", "seed failed\n" if seed_rc else "")

    def fake_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(argv), porcelain_rc, porcelain_stdout, "")

    monkeypatch.setattr(implement_dispatch, "_invoke_cli", fake_invoke)
    monkeypatch.setattr(dispatch_commit_route, "_invoke_cli", fake_invoke)
    # Rust-owned run-log verbs route through the bootstrap runner.
    monkeypatch.setattr(implement_dispatch, "_invoke_larch", fake_invoke, raising=False)
    monkeypatch.setattr(dispatch_commit_route, "_invoke_larch", fake_invoke, raising=False)
    monkeypatch.setattr(implement_dispatch, "_run", fake_run)
    monkeypatch.setattr(dispatch_commit_route, "_run", fake_run)
    return impl, invoke_calls, seed_calls


@pytest.mark.parametrize("site", ["step5-self-review", "step5-resume-handoff", "step7"])
@pytest.mark.parametrize("commit_stdout", [_STEP5_COMMIT_OK, _STEP5_COMMIT_NOOP])
def test_commit_route_success_relays_continue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    site: str,
    commit_stdout: str,
) -> None:
    _impl, invoke_calls, seed_calls = _setup_commit_route(tmp_path, monkeypatch, commit_stdout=commit_stdout)

    rc = implement_dispatch.commit_route_main(["--site", site])

    assert rc == 0
    out = capsys.readouterr().out
    assert "COMMIT_OUTCOME=" in out
    assert "NEXT_ACTION=continue\n" in out
    assert out.count("NEXT_ACTION=") == 1
    assert ["review-and-fix", "commit-fixes", "--stage-all"] in invoke_calls
    assert not [call for call in invoke_calls if call[:2] == ["run-log", "append-failure"]]
    assert not seed_calls


@pytest.mark.parametrize(
    ("site", "stall_step", "bail_reason", "display_site"),
    [
        ("step5-self-review", "5", "review-fix-commit-failed", "5-self-review"),
        ("step5-resume-handoff", "5", "resume-handoff-commit-failed", "5-resume-handoff"),
        ("step7", "7", "review-fix-commit-failed", "7"),
    ],
)
@pytest.mark.parametrize(
    "commit_stdout",
    [
        "COMMITTED=false\nERROR=missing outcome with COMMIT_OUTCOME=ok in prose\n",
        "COMMITTED=false\nCOMMIT_OUTCOME=bogus\n",
        _STEP5_COMMIT_FAILED,
    ],
)
def test_commit_route_failure_seeds_stall_and_logs_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    site: str,
    stall_step: str,
    bail_reason: str,
    display_site: str,
    commit_stdout: str,
) -> None:
    impl, invoke_calls, _seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=commit_stdout,
        commit_rc=1 if "COMMIT_OUTCOME=failed" in commit_stdout else 0,
    )
    (impl / "ship-pr-state.sh").write_text("RUN_ID=run\nOOS_PENDING=false\n", encoding="utf-8")

    rc = implement_dispatch.commit_route_main(["--site", site])

    assert rc == 0
    out = capsys.readouterr().out
    assert "NEXT_ACTION=stall\n" in out
    assert out.count("NEXT_ACTION=") == 1
    state = (impl / "ship-pr-state.sh").read_text(encoding="utf-8")
    assert "STALL_TRACKING=true\n" in state
    assert f"STALL_STEP={stall_step}\n" in state
    assert f"BAIL_REASON={bail_reason}\n" in state
    log_calls = [call for call in invoke_calls if call[:2] == ["run-log", "append-failure"]]
    assert len(log_calls) == 1
    assert "--redact" in log_calls[0]
    # #7074: the machine site key ("step7") must be de-prefixed for the emitter so
    # the rendered bullet reads "Step 7:", not the doubled "Step step7:".
    site_arg = log_calls[0][log_calls[0].index("--site") + 1]
    assert site_arg == display_site
    assert not site_arg.startswith("step")


@pytest.mark.parametrize(("porcelain_stdout", "porcelain_rc"), [(" M leftover.txt\n", 0), ("", 1)])
def test_commit_route_resume_porcelain_failure_seeds_and_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    porcelain_stdout: str,
    porcelain_rc: int,
) -> None:
    impl, invoke_calls, _seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_OK,
        porcelain_stdout=porcelain_stdout,
        porcelain_rc=porcelain_rc,
    )
    (impl / "ship-pr-state.sh").write_text("RUN_ID=run\nOOS_PENDING=false\n", encoding="utf-8")

    rc = implement_dispatch.commit_route_main(["--site", "step5-resume-handoff"])

    assert rc == 0
    assert "NEXT_ACTION=stall\n" in capsys.readouterr().out
    state = (impl / "ship-pr-state.sh").read_text(encoding="utf-8")
    assert "STALL_STEP=5\n" in state
    assert "BAIL_REASON=resume-handoff-commit-failed\n" in state
    log_calls = [call for call in invoke_calls if call[:2] == ["run-log", "append-failure"]]
    assert len(log_calls) == 1
    assert "--redact" in log_calls[0]


def test_commit_route_self_review_skips_porcelain_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _impl, _invoke_calls, _seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_OK,
        porcelain_stdout=" M ignored.txt\n",
    )

    rc = implement_dispatch.commit_route_main(["--site", "step5-self-review"])

    assert rc == 0
    assert "NEXT_ACTION=continue\n" in capsys.readouterr().out


def test_commit_route_absent_state_uses_initial_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl, _invoke_calls, seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_FAILED,
        commit_rc=1,
    )

    rc = implement_dispatch.commit_route_main(["--site", "step7"])

    assert rc == 0
    assert "NEXT_ACTION=stall\n" in capsys.readouterr().out
    assert seed_calls
    assert "--stall-tracking" in seed_calls[0]
    assert (impl / "ship-pr-state.sh").is_file()


def test_commit_route_empty_state_uses_initial_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl, _invoke_calls, seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_FAILED,
        commit_rc=1,
    )
    (impl / "ship-pr-state.sh").write_text("", encoding="utf-8")

    rc = implement_dispatch.commit_route_main(["--site", "step7"])

    assert rc == 0
    assert "NEXT_ACTION=stall\n" in capsys.readouterr().out
    assert seed_calls


def test_commit_route_seed_failure_omits_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _impl, _invoke_calls, _seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_FAILED,
        commit_rc=1,
        seed_rc=1,
    )

    rc = implement_dispatch.commit_route_main(["--site", "step7"])

    assert rc != 0
    assert "NEXT_ACTION=" not in capsys.readouterr().out


def test_commit_route_malformed_state_omits_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl, _invoke_calls, seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_FAILED,
        commit_rc=1,
    )
    (impl / "ship-pr-state.sh").write_text("# not a shell kv\nmalformed\n", encoding="utf-8")

    rc = implement_dispatch.commit_route_main(["--site", "step7"])

    assert rc != 0
    assert not seed_calls
    assert "NEXT_ACTION=" not in capsys.readouterr().out


def test_commit_route_relay_helper_includes_next_action(capsys: pytest.CaptureFixture[str]) -> None:
    implement_dispatch._relay_commit_kvs("NEXT_ACTION=stall\nCOMMIT_OUTCOME=failed\nIGNORED=1\n")
    assert capsys.readouterr().out == "NEXT_ACTION=stall\nCOMMIT_OUTCOME=failed\n"


def test_checks_relay_whitespace_parser_uses_shared_codec_not_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_helper(_text: str) -> dict[str, str]:
        raise AssertionError("line-oriented implement_dispatch._parse_kv must not parse checks relay")

    real_parse_kv = dispatch_commit_route.larch_io.parse_kv
    seen: list[str] = []

    def track_parse_kv(text: str, **kwargs: Any) -> object:
        seen.append(text)
        return real_parse_kv(text, **kwargs)

    monkeypatch.setattr(implement_dispatch, "_parse_kv", fail_helper)
    monkeypatch.setattr(dispatch_commit_route.larch_io, "parse_kv", track_parse_kv)
    line = "STATUS=fail FAILURE_REASON=relevant-checks-failed EXIT_CODE=2 PHASE=checks DIGEST_FILE=/tmp/digest.txt REDACTED_LOG_FILE=/tmp/redacted.log trailing prose"

    values = implement_dispatch._parse_whitespace_kv_line(line)

    assert seen == [
        "STATUS=fail\nFAILURE_REASON=relevant-checks-failed\nEXIT_CODE=2\n"
        "PHASE=checks\nDIGEST_FILE=/tmp/digest.txt\nREDACTED_LOG_FILE=/tmp/redacted.log\n"
        "trailing\nprose"
    ]
    assert values == {
        "STATUS": "fail",
        "FAILURE_REASON": "relevant-checks-failed",
        "EXIT_CODE": "2",
        "PHASE": "checks",
        "DIGEST_FILE": "/tmp/digest.txt",
        "REDACTED_LOG_FILE": "/tmp/redacted.log",
    }
    assert implement_dispatch._checks_relay_line(values) == (
        "STATUS=fail FAILURE_REASON=relevant-checks-failed EXIT_CODE=2 "
        "PHASE=checks DIGEST_FILE=/tmp/digest.txt REDACTED_LOG_FILE=/tmp/redacted.log"
    )


def test_checks_relay_formats_pass_and_skipped() -> None:
    assert implement_dispatch._checks_relay_line(
        {"RELEVANT_CHECKS_OK": "true", "SITE": "step6", "COVERAGE": "changed", "PHASE": "checks"}
    ) == "RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=changed PHASE=checks"
    assert implement_dispatch._checks_relay_line(
        {"RELEVANT_CHECKS_SKIPPED": "true", "SITE": "step5-self-review"}
    ) == "RELEVANT_CHECKS_SKIPPED=true SITE=step5-self-review"


def test_commit_route_child_envelope_omits_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _impl, _invoke_calls, _seed_calls = _setup_commit_route(tmp_path, monkeypatch, commit_stdout=_STEP5_COMMIT_OK)

    rc = implement_dispatch.commit_route_main(["--site", "step5-self-review", "--emit-next-action", "false"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "COMMIT_ROUTE_OUTCOME=continue\n" in out
    assert "COMMIT_OUTCOME=ok\n" in out
    assert "NEXT_ACTION=" not in out


def test_commit_route_child_envelope_distinguishes_seed_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _impl, _invoke_calls, _seed_calls = _setup_commit_route(
        tmp_path,
        monkeypatch,
        commit_stdout=_STEP5_COMMIT_FAILED,
        commit_rc=1,
        seed_rc=1,
    )

    rc = implement_dispatch.commit_route_main(["--site", "step7", "--emit-next-action", "false"])

    assert rc == 1
    out = capsys.readouterr().out
    assert "COMMIT_ROUTE_OUTCOME=seed-failed\n" in out
    assert "NEXT_ACTION=" not in out


def _mock_composite_continue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, commit_stdout: str = "COMMIT_ROUTE_OUTCOME=continue\nCOMMITTED=true\nCOMMIT_OUTCOME=ok\n") -> Path:
    impl = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step6", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step6", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_commit_route_leg",
        lambda **_kwargs: ("continue", commit_stdout),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", lambda **_kwargs: ("continue", commit_stdout))
    return impl


def test_run_relevant_checks_for_site_does_not_allow_skip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    calls: list[tuple[list[str], int, str]] = []

    def fake_run_leg(*, argv: Sequence[str], deadline_ms: int, label: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((list(argv), deadline_ms, label))
        return subprocess.CompletedProcess(
            list(argv),
            0,
            "RELEVANT_CHECKS_OK=true SITE=step6\n",
            "",
        )

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)

    captured, timed_out = implement_dispatch._run_relevant_checks_for_site(
        implement_tmpdir=impl,
        checks_site="step6",
        deadline_ms=1234,
    )

    assert not timed_out
    assert implement_dispatch._checks_pass(captured)
    assert captured == {"RELEVANT_CHECKS_OK": "true", "SITE": "step6"}
    assert calls == [
        (
            [
                "checks",
                "run-relevant",
                "--site",
                "step6",
                "--tmpdir",
                str(impl),
                "--repo-root",
                str(Path(__file__).resolve().parents[3]),
            ],
            1234,
            "checks_run_relevant:step6",
        )
    ]


def test_run_relevant_checks_binds_persisted_root_over_claude_project_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(foreign))
    captured_env: dict[str, str] = {}
    captured_cwd: list[Path | None] = []

    def fake_run_leg(
        *,
        argv: Sequence[str],
        deadline_ms: int,
        label: str,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _ = (deadline_ms, label)
        captured_cwd.append(cwd)
        if env is not None:
            captured_env.update(env)
        assert "--repo-root" in argv
        root_idx = list(argv).index("--repo-root") + 1
        assert Path(argv[root_idx]) == Path(__file__).resolve().parents[3]
        return subprocess.CompletedProcess(list(argv), 0, "RELEVANT_CHECKS_OK=true SITE=step3\n", "")

    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)
    captured, timed_out = dispatch_commit_route._run_relevant_checks_for_site(
        implement_tmpdir=impl,
        checks_site="step3",
        deadline_ms=1000,
    )
    assert not timed_out
    assert captured.get("RELEVANT_CHECKS_OK") == "true"
    assert captured_cwd == [Path(__file__).resolve().parents[3]]
    assert captured_env.get("CLAUDE_PROJECT_DIR") == str(Path(__file__).resolve().parents[3])
    assert captured_env.get("REPO_ROOT") == str(Path(__file__).resolve().parents[3])


def test_checks_commit_route_ok_envelope_continues_through_real_helper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    checks_calls: list[list[str]] = []
    commit_calls: list[str] = []

    def fake_run_leg(*, argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        checks_calls.append(list(argv))
        return subprocess.CompletedProcess(
            list(argv),
            0,
            "RELEVANT_CHECKS_OK=true SITE=step5-self-review\n",
            "",
        )

    def fake_commit(*, site_name: str, **_kwargs: object) -> tuple[implement_dispatch.CommitRouteOutcome, str]:
        commit_calls.append(site_name)
        return "continue", "COMMIT_ROUTE_OUTCOME=continue\nCOMMITTED=true\nCOMMIT_OUTCOME=ok\n"

    def fail_checkpoint(_forked_target: str) -> int:
        raise AssertionError("7.r checkpoint must not run without the explicit Step 6 flag")

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(implement_dispatch, "_run_commit_route_leg", fake_commit)
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", fake_commit)
    monkeypatch.setattr(implement_dispatch, "_run_7r_rebase_checkpoint", fail_checkpoint)
    monkeypatch.setattr(dispatch_commit_route, "_run_7r_rebase_checkpoint", fail_checkpoint)

    rc = implement_dispatch.checks_commit_route_main(
        ["--checks-site", "step5-self-review", "--commit-site", "step5-self-review"]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert checks_calls == [
        [
            "checks",
            "run-relevant",
            "--site",
            "step5-self-review",
            "--tmpdir",
            str(impl),
            "--repo-root",
            str(Path(__file__).resolve().parents[3]),
        ]
    ]
    assert commit_calls == ["step5-self-review"]
    assert "RELEVANT_CHECKS_OK=true SITE=step5-self-review" in out
    assert "NEXT_ACTION=checks-failed" not in out
    assert [line for line in out.splitlines() if line == "NEXT_ACTION=continue"] == ["NEXT_ACTION=continue"]


def test_checks_commit_route_emit_step7_breadcrumb_goes_to_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """emit_step7_breadcrumb=True must print the step-7 breadcrumb to stderr, not stdout."""
    impl = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))

    def fake_run_leg(*, argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(argv), 0, "RELEVANT_CHECKS_OK=true SITE=step6\n", "")

    def fake_commit(**_kwargs: object) -> tuple[implement_dispatch.CommitRouteOutcome, str]:
        return "continue", "COMMIT_ROUTE_OUTCOME=continue\nCOMMITTED=true\nCOMMIT_OUTCOME=ok\n"

    def fake_7r(_forked_target: str) -> int:
        return 0

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)  # lint-monkeypatch-binding: ok mirrors existing test pattern; both facades patched for coverage
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)  # lint-monkeypatch-binding: ok mirrors existing test pattern; both facades patched for coverage
    monkeypatch.setattr(implement_dispatch, "_run_commit_route_leg", fake_commit)  # lint-monkeypatch-binding: ok mirrors existing test pattern; both facades patched for coverage
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", fake_commit)  # lint-monkeypatch-binding: ok mirrors existing test pattern; both facades patched for coverage
    monkeypatch.setattr(implement_dispatch, "_run_7r_rebase_checkpoint", fake_7r)  # lint-monkeypatch-binding: ok mirrors existing test pattern; both facades patched for coverage
    monkeypatch.setattr(dispatch_commit_route, "_run_7r_rebase_checkpoint", fake_7r)  # lint-monkeypatch-binding: ok mirrors existing test pattern; both facades patched for coverage

    rc = implement_dispatch.checks_commit_route_main(
        ["--checks-site", "step6", "--commit-site", "step7", "--emit-step7-breadcrumb", "--rebase-checkpoint-7r"]
    )

    captured = capsys.readouterr()
    assert rc == 0
    breadcrumb = "> **🔶 /implement 7: commit (review)**"
    assert breadcrumb not in captured.out, "step-7 breadcrumb must not appear on stdout"
    assert breadcrumb in captured.err, "step-7 breadcrumb must appear on stderr"


def test_composite_outer_timeout_budgets_match_leg_sums_and_fences() -> None:
    assert implement_dispatch.CHECKS_DEADLINE_MS == implement_dispatch._CHECKS_DEADLINE_MS
    assert implement_dispatch.CHECKS_STEP3_BG_WAIT_TIMEOUT_S == implement_dispatch.CHECKS_DEADLINE_MS // 1000
    assert implement_dispatch.CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS == (
        implement_dispatch.CHECKS_DEADLINE_MS
        + implement_dispatch._COMMIT_ROUTE_DEADLINE_MS
        + implement_dispatch._REBASE_CHECKPOINT_DEADLINE_MS
        + implement_dispatch._COMPOSITE_OUTER_SLACK_MS
    )
    assert implement_dispatch.CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS == 15_600_000
    assert implement_dispatch.CHECKS_STEP5_RESUME_OUTER_TIMEOUT_MS == (
        implement_dispatch._CHECKS_DEADLINE_MS
        + implement_dispatch._STEP5_RESUME_DEADLINE_MS
        + implement_dispatch._COMPOSITE_OUTER_SLACK_MS
    )
    assert implement_dispatch.CHECKS_STEP5_RESUME_OUTER_TIMEOUT_MS == 32_700_000

    root = Path(__file__).resolve().parents[3]
    skill = (root / "skills" / "implement" / "SKILL.md").read_text(encoding="utf-8")
    run_step_checks = (root / "skills" / "implement" / "scripts" / "run-step-checks.sh").read_text(
        encoding="utf-8"
    )
    step6_entry_sh = (root / "skills" / "implement" / "scripts" / "step-6-entry.sh").read_text(
        encoding="utf-8"
    )
    self_review_ref = (root / "skills" / "implement" / "references" / "self-review.md").read_text(
        encoding="utf-8"
    )
    dispatch_commit = (root / "python" / "larch" / "implement" / "dispatch_commit_route.py").read_text(
        encoding="utf-8"
    )
    step6_launcher = "skills/implement/scripts/step-6-entry.sh"
    assert step6_launcher in skill
    assert "implement-step6-checks" in skill
    assert "skills/implement/references/self-review.md" in skill
    assert 'implement run-step-checks "$@"' in run_step_checks
    assert "bgjob start" not in run_step_checks
    assert '"implement-checks-step5-self-review", 14700' in dispatch_commit
    assert "checks-result-identity" in dispatch_commit
    assert "step_checks_result_env_state" not in dispatch_commit
    assert 'implement step-6-entry "$@"' in step6_entry_sh
    assert "bgjob start" not in step6_entry_sh
    assert "step6_result_env_state" not in dispatch_commit
    assert "_session_validated_repo_root" in dispatch_commit
    assert '"--repo-root"' in dispatch_commit or "'--repo-root'" in dispatch_commit
    assert "CLAUDE_PROJECT_DIR" in dispatch_commit
    identity_mod = (root / "crates" / "larch-core" / "src" / "implement" / "identity.rs").read_text(
        encoding="utf-8"
    )
    assert "CHECKS_IDENTITY_INTEGRITY_FAILED_ACTION" in identity_mod
    assert "BGJOB_STATUS=STARTED STEP=implement-step6-checks PGID=<n>" in skill
    assert "scripts/larch.sh bgjob wait --step implement-step6-checks" in skill
    assert "checks-commit-route --checks-site step5-self-review" not in skill
    assert "timeout: 14700000" not in skill
    assert "run-step-checks.sh --site step5-self-review --commit-site step5-self-review" in self_review_ref
    assert "BGJOB_STATUS=STARTED STEP=implement-checks-step5-self-review PGID=<n>" in self_review_ref
    assert "BUDGET_S=14700" in self_review_ref


def test_7r_rebase_checkpoint_invokes_cli_and_relays_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[dict[str, str]] = []

    def fake_checkpoint(_runner: object, *, step_prefix: str, short_name: str, forked_target: str = "false", base_remote: str | None = None, base_ref: str | None = None, cwd: str | None = None) -> dispatch_commit_route.rust_runtime.CheckpointProbeOutput:
        _ = (base_remote, base_ref, cwd)
        calls.append({"step_prefix": step_prefix, "short_name": short_name, "forked_target": forked_target})
        return dispatch_commit_route.rust_runtime.CheckpointProbeOutput(
            exit_code=1,
            stdout="\nCHECKPOINT_NEXT=load-routing\n\nREBASE_OUTCOME=conflict\nCONFLICT_FILES=a.py,b.py\n",
            stderr="probe warning\n",
            routing={},
            advisory_lines=(),
        )

    monkeypatch.setattr(dispatch_commit_route.rust_runtime, "checkpoint_probe", fake_checkpoint)

    rc = implement_dispatch._run_7r_rebase_checkpoint("true")

    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == "CHECKPOINT_NEXT=load-routing\nREBASE_OUTCOME=conflict\nCONFLICT_FILES=a.py,b.py\n"
    assert captured.err == "probe warning\n"
    assert calls == [{"step_prefix": "7.r", "short_name": "commit (review)", "forked_target": "true"}]


@pytest.mark.parametrize(
    ("probe_rc", "forked_target", "probe_outcome"),
    [(0, "false", "ok"), (1, "true", "conflict")],
)
def test_composite_rebase_checkpoint_relays_probe_and_returns_probe_rc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    probe_rc: int,
    forked_target: str,
    probe_outcome: str,
) -> None:
    _mock_composite_continue(tmp_path, monkeypatch)
    checkpoint_calls: list[str] = []

    def fake_checkpoint(value: str) -> int:
        checkpoint_calls.append(value)
        print(f"CHECKPOINT_NEXT={'continue' if probe_rc == 0 else 'load-routing'}")
        print(f"REBASE_OUTCOME={probe_outcome}")
        if probe_rc == 1:
            print("CONFLICT_FILES=changed.py")
        return probe_rc

    monkeypatch.setattr(implement_dispatch, "_run_7r_rebase_checkpoint", fake_checkpoint)
    monkeypatch.setattr(dispatch_commit_route, "_run_7r_rebase_checkpoint", fake_checkpoint)

    rc = implement_dispatch.checks_commit_route_main(
        [
            "--checks-site",
            "step6",
            "--commit-site",
            "step7",
            "--rebase-checkpoint-7r",
            "--forked-target",
            forked_target,
        ]
    )

    out = capsys.readouterr().out
    assert rc == probe_rc
    assert checkpoint_calls == [forked_target]
    assert "RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=changed PHASE=checks\n" in out
    assert f"REBASE_OUTCOME={probe_outcome}\n" in out
    assert "NEXT_ACTION=continue\n" in out
    assert out.count("NEXT_ACTION=") == 1
    assert out.index(f"REBASE_OUTCOME={probe_outcome}") < out.index("NEXT_ACTION=continue")


def test_composite_without_rebase_flag_preserves_step5_self_review_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_composite_continue(tmp_path, monkeypatch)

    def fail_checkpoint(_forked_target: str) -> int:
        raise AssertionError("7.r checkpoint must not run without the explicit Step 6 flag")

    monkeypatch.setattr(implement_dispatch, "_run_7r_rebase_checkpoint", fail_checkpoint)
    monkeypatch.setattr(dispatch_commit_route, "_run_7r_rebase_checkpoint", fail_checkpoint)

    rc = implement_dispatch.checks_commit_route_main(
        ["--checks-site", "step5-self-review", "--commit-site", "step5-self-review"]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "NEXT_ACTION=continue\n" in out
    assert "CHECKPOINT_NEXT=" not in out


def test_composite_rebase_checkpoint_skips_checks_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: ({"STATUS": "fail", "FAILURE_REASON": "relevant-checks-failed"}, False),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: ({"STATUS": "fail", "FAILURE_REASON": "relevant-checks-failed"}, False))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_commit_route_leg",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("commit must not run after checks failure")),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("commit must not run after checks failure")))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_7r_rebase_checkpoint",
        lambda _forked_target: (_ for _ in ()).throw(AssertionError("7.r checkpoint must not run after checks failure")),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_7r_rebase_checkpoint", lambda _forked_target: (_ for _ in ()).throw(AssertionError("7.r checkpoint must not run after checks failure")))

    rc = implement_dispatch.checks_commit_route_main(
        ["--checks-site", "step6", "--commit-site", "step7", "--rebase-checkpoint-7r"]
    )

    assert rc == 0
    assert capsys.readouterr().out == "STATUS=fail FAILURE_REASON=relevant-checks-failed\nNEXT_ACTION=checks-failed\n"


def test_composite_rebase_checkpoint_skips_seeded_stall(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_composite_continue(tmp_path, monkeypatch, commit_stdout="COMMIT_ROUTE_OUTCOME=seeded-stall\nCOMMIT_OUTCOME=failed\n")
    monkeypatch.setattr(
        implement_dispatch,
        "_run_commit_route_leg",
        lambda **_kwargs: ("seeded-stall", "COMMIT_ROUTE_OUTCOME=seeded-stall\nCOMMIT_OUTCOME=failed\n"),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", lambda **_kwargs: ("seeded-stall", "COMMIT_ROUTE_OUTCOME=seeded-stall\nCOMMIT_OUTCOME=failed\n"))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_7r_rebase_checkpoint",
        lambda _forked_target: (_ for _ in ()).throw(AssertionError("7.r checkpoint must not run after seeded stall")),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_7r_rebase_checkpoint", lambda _forked_target: (_ for _ in ()).throw(AssertionError("7.r checkpoint must not run after seeded stall")))

    rc = implement_dispatch.checks_commit_route_main(
        ["--checks-site", "step6", "--commit-site", "step7", "--rebase-checkpoint-7r"]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "NEXT_ACTION=stall\n" in out
    assert "CHECKPOINT_NEXT=" not in out


def test_step4_composite_noop_runs_4r_and_does_not_double_emit_continue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step3", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step3", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ))
    monkeypatch.setattr(implement_dispatch, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(dispatch_commit_route, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(implement_dispatch, "_run_step4_recovery_recompute", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(dispatch_commit_route, "_run_step4_recovery_recompute", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        implement_dispatch,
        "_run_step4_commit_leg",
        lambda *_args, **_kwargs: ("noop", "COMMIT_ROUTE_OUTCOME=noop\n"),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_step4_commit_leg", lambda *_args, **_kwargs: ("noop", "COMMIT_ROUTE_OUTCOME=noop\n"))

    def fake_4r(forked_target: str) -> int:
        assert forked_target == "true"
        print("CHECKPOINT_NEXT=continue")
        print("REBASE_OUTCOME=ok")
        print("NEXT_ACTION=continue")
        return 0

    monkeypatch.setattr(implement_dispatch, "_run_4r_rebase_checkpoint", fake_4r)
    monkeypatch.setattr(dispatch_commit_route, "_run_4r_rebase_checkpoint", fake_4r)

    rc = implement_dispatch.checks_commit_route_main([
        "--checks-site",
        "step3",
        "--commit-site",
        "step4",
        "--rebase-checkpoint-4r",
        "--forked-target",
        "true",
    ])

    out = capsys.readouterr().out
    assert rc == 0
    assert "RELEVANT_CHECKS_OK=true SITE=step3 COVERAGE=changed PHASE=checks\n" in out
    assert "COMMIT_ROUTE_OUTCOME=noop\n" in out
    assert out.count("NEXT_ACTION=continue") == 1


def test_step4_composite_seeded_stall_skips_4r(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: ({"RELEVANT_CHECKS_OK": "true", "SITE": "step3"}, False),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: ({"RELEVANT_CHECKS_OK": "true", "SITE": "step3"}, False))
    monkeypatch.setattr(implement_dispatch, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(dispatch_commit_route, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(implement_dispatch, "_run_step4_recovery_recompute", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(dispatch_commit_route, "_run_step4_recovery_recompute", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        implement_dispatch,
        "_run_step4_commit_leg",
        lambda *_args, **_kwargs: ("seeded-stall", "COMMIT_ROUTE_OUTCOME=seeded-stall\n"),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_step4_commit_leg", lambda *_args, **_kwargs: ("seeded-stall", "COMMIT_ROUTE_OUTCOME=seeded-stall\n"))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_4r_rebase_checkpoint",
        lambda _forked_target: (_ for _ in ()).throw(AssertionError("4.r must not run after seeded stall")),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_4r_rebase_checkpoint", lambda _forked_target: (_ for _ in ()).throw(AssertionError("4.r must not run after seeded stall")))

    rc = implement_dispatch.checks_commit_route_main([
        "--checks-site",
        "step3",
        "--commit-site",
        "step4",
        "--rebase-checkpoint-4r",
    ])

    assert rc == 0
    assert "NEXT_ACTION=stall\n" in capsys.readouterr().out


def test_run_step4_commit_leg_commits_ordinary_pathspec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    (impl / "implementation-commit-message.txt").write_text("Implement thing\n", encoding="utf-8")
    (impl / "implementation-commit-paths.nul").write_bytes(b"file.txt\0")
    calls: list[list[str]] = []

    def fake_run_leg(*, argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, "COMMITTED=true\nSHA=abc\n", "")

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(implement_dispatch, "_pathspec_clean_relative_to_head", lambda _pathspec: False)
    monkeypatch.setattr(dispatch_commit_route, "_pathspec_clean_relative_to_head", lambda _pathspec: False)

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    assert outcome == "continue"
    assert "COMMIT_ROUTE_OUTCOME=continue\n" in stdout
    assert calls == [[
        "implement",
        "commit",
        "--message",
        "Implement thing",
        "--pathspec-from-file",
        str(impl / "implementation-commit-paths.nul"),
        "--pathspec-file-nul",
    ]]


def test_run_step4_commit_leg_absorbs_attributed_step3_lint_fix_path(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    baseline = repo / "python" / "ruff.toml"
    baseline.parent.mkdir()
    baseline.write_text('{"reasons": []}\n', encoding="utf-8")
    unrelated = repo / "unrelated.txt"
    unrelated.write_text("base\n", encoding="utf-8")
    _git(repo, "add", str(baseline.relative_to(repo)), "unrelated.txt")
    _git(repo, "commit", "-m", "add lint config")
    baseline.write_text('{"reasons": ["lint-fix"]}\n', encoding="utf-8")
    unrelated.write_text("external change\n", encoding="utf-8")
    _ = self_edit_log.record_self_edits(
        tmpdir=impl,
        source="lint-fix:step3",
        paths=[str(baseline.relative_to(repo))],
        repo_root=repo,
    )
    (impl / "implementation-commit-message.txt").write_text("Implement thing\n", encoding="utf-8")
    (impl / "implementation-commit-paths.nul").write_bytes(b"README.md\0")
    calls: list[list[str]] = []

    def fake_run_leg(*, argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, "COMMITTED=true\nSHA=abc\n", "")

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)  # lint-monkeypatch-binding: ok both re-export facades are patched for this regression
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)  # lint-monkeypatch-binding: ok both re-export facades are patched for this regression

    outcome, stdout = dispatch_commit_route._run_step4_commit_leg(impl, deadline_ms=123)

    assert outcome == "continue"
    assert "COMMIT_ROUTE_OUTCOME=continue\n" in stdout
    assert calls[0][-2] == str(impl / "step4-commit-paths.nul")
    assert (impl / "step4-commit-paths.nul").read_bytes() == (
        b"README.md\0python/ruff.toml\0"
    )


def test_step4_pathspec_excludes_stale_unallowlisted_self_edit(
    repo: Path,
    tmp_path: Path,
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    path = repo / "python" / "ruff.toml"
    path.parent.mkdir()
    path.write_text('{"revision": 0}\n', encoding="utf-8")
    _git(repo, "add", str(path.relative_to(repo)))
    _git(repo, "commit", "-m", "add ordinary lint config")
    path.write_text('{"revision": 1}\n', encoding="utf-8")
    _ = self_edit_log.record_self_edits(
        tmpdir=impl,
        source="lint-fix:step3",
        paths=[str(path.relative_to(repo))],
        repo_root=repo,
    )
    path.write_text('{"revision": 2}\n', encoding="utf-8")
    pathspec = impl / "implementation-commit-paths.nul"
    pathspec.write_bytes(b"README.md\0")

    refreshed, refresh_ok = dispatch_commit_route._step4_pathspec_with_step3_self_edits(
        implement_tmpdir=impl,
        pathspec=pathspec,
        repo_root=repo,
    )

    assert refresh_ok is True
    assert refreshed == pathspec


def test_run_step4_commit_leg_failure_seeds_step4_stall(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    (impl / "implementation-commit-message.txt").write_text("Implement thing\n", encoding="utf-8")
    (impl / "implementation-commit-paths.nul").write_bytes(b"file.txt\0")
    seed_calls: list[tuple[str, str]] = []

    monkeypatch.setattr(implement_dispatch, "_pathspec_clean_relative_to_head", lambda _pathspec: False)
    monkeypatch.setattr(dispatch_commit_route, "_pathspec_clean_relative_to_head", lambda _pathspec: False)
    monkeypatch.setattr(
        implement_dispatch,
        "_run_leg_with_timeout",
        lambda **_kwargs: subprocess.CompletedProcess([], 1, "COMMITTED=false\nERROR=failed\n", ""),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", lambda **_kwargs: subprocess.CompletedProcess([], 1, "COMMITTED=false\nERROR=failed\n", ""))
    monkeypatch.setattr(
        implement_dispatch,
        "_invoke_cli",
        lambda args, **_kwargs: subprocess.CompletedProcess(list(args), 0, "", ""),
    )
    monkeypatch.setattr(dispatch_commit_route, "_invoke_cli", lambda args, **_kwargs: subprocess.CompletedProcess(list(args), 0, "", ""))

    def fake_seed(_tmpdir: Path, *, stall_step: str, bail_reason: str) -> bool:
        seed_calls.append((stall_step, bail_reason))
        return True

    monkeypatch.setattr(implement_dispatch, "_seed_durable_stall_state", fake_seed)
    monkeypatch.setattr(dispatch_commit_route, "_seed_durable_stall_state", fake_seed)

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    assert outcome == "seeded-stall"
    assert "COMMIT_ROUTE_OUTCOME=seeded-stall\n" in stdout
    assert seed_calls == [("4", "implementation-commit-failed")]


def test_seed_durable_stall_state_uses_verified_rust_seeder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    calls: list[list[str]] = []

    def fake_larch(args: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return subprocess.CompletedProcess(list(args), 0, "", "")

    monkeypatch.setattr(dispatch_commit_route, "_invoke_larch", fake_larch)

    assert dispatch_commit_route._seed_durable_stall_state(  # pyright: ignore[reportPrivateUsage]
        impl,
        stall_step="4",
        bail_reason="implementation-commit-failed",
    )
    assert calls == [[
        "implement",
        "step-8-seed-initial",
        "--stall-tracking",
        "true",
        "--stall-step",
        "4",
        "--bail-reason",
        "implementation-commit-failed",
    ]]


def test_persist_ship_seed_context_refreshes_blank_manifest_path(tmp_path: Path) -> None:
    impl = make_implement_tmpdir(tmp_path)
    (impl / "ship-seed-input.env").write_text("MANIFEST_PATH=\nTOOL_LABEL=\n", encoding="utf-8")
    (impl / "manifest.json").write_text('{"schema_version":"1"}\n', encoding="utf-8")
    (impl / "bootstrap-routing.env").write_text("coder=codex\n", encoding="utf-8")

    implement_dispatch._persist_ship_seed_context(impl)

    seed = (impl / "ship-seed-input.env").read_text(encoding="utf-8")
    assert f"MANIFEST_PATH={impl / 'manifest.json'}" in seed
    assert "TOOL_LABEL=Codex" in seed


def test_run_step4_commit_leg_noop_emits_dispatcher_committed_breadcrumb(
    repo: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = repo
    impl = make_implement_tmpdir(tmp_path)
    manifest = impl / "manifest.json"
    manifest.write_text('{"schema_version":"1"}\n', encoding="utf-8")
    (impl / "ship-seed-input.env").write_text(
        f"MANIFEST_PATH={manifest}\nDISPATCHER_COMMITTED=true\n",
        encoding="utf-8",
    )

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    captured = capsys.readouterr()
    assert outcome == "noop"
    assert "COMMIT_ROUTE_OUTCOME=noop\n" in stdout
    assert "dispatcher-committed" in captured.err


def test_run_step4_commit_leg_dispatcher_committed_commits_later_dirty_paths(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    manifest = impl / "manifest.json"
    manifest.write_text('{"schema_version":"1"}\n', encoding="utf-8")
    (impl / "ship-seed-input.env").write_text(
        f"MANIFEST_PATH={manifest}\nDISPATCHER_COMMITTED=true\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("base\nlint fix\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run_leg(*, argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, "COMMITTED=true\nSHA=def\n", "")

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    assert outcome == "continue"
    assert "COMMIT_ROUTE_OUTCOME=continue\n" in stdout
    assert calls == [[
        "implement",
        "commit",
        "--message",
        "Apply post-dispatch checks fixes",
        "--pathspec-from-file",
        str(impl / "dispatcher-committed-dirty-paths.nul"),
        "--pathspec-file-nul",
    ]]
    assert (impl / "dispatcher-committed-dirty-paths.nul").read_bytes() == b"README.md\0"


def test_pathspec_clean_relative_to_head_detects_dirty_and_clean(repo: Path) -> None:
    (repo / "changed.txt").write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "changed.txt")
    _git(repo, "commit", "-m", "add changed.txt")
    pathspec = repo / "pathspec.nul"
    pathspec.write_bytes(b"changed.txt\0")

    assert dispatch_commit_route._pathspec_clean_relative_to_head(pathspec) is True

    (repo / "changed.txt").write_text("v2\n", encoding="utf-8")

    assert dispatch_commit_route._pathspec_clean_relative_to_head(pathspec) is False


def test_pathspec_clean_relative_to_head_empty_pathspec_is_not_clean(tmp_path: Path) -> None:
    pathspec = tmp_path / "empty.nul"
    pathspec.write_bytes(b"")

    assert dispatch_commit_route._pathspec_clean_relative_to_head(pathspec) is False


def test_run_step4_commit_leg_already_committed_by_main_agent_short_circuits_noop(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    (impl / "implementation-commit-message.txt").write_text("Implement thing\n", encoding="utf-8")
    (impl / "implementation-commit-paths.nul").write_bytes(b"already-committed.txt\0")
    (repo / "already-committed.txt").write_text("done\n", encoding="utf-8")
    _git(repo, "add", "already-committed.txt")
    _git(repo, "commit", "-m", "ad hoc lint fix commit covering the implementation path")
    calls: list[list[str]] = []

    def fake_run_leg(*, argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 1, "COMMITTED=false\nERROR=nothing to commit, working tree clean\n", "")

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    captured = capsys.readouterr()
    assert outcome == "noop"
    assert "COMMIT_ROUTE_OUTCOME=noop\n" in stdout
    assert "already-committed" in captured.err
    assert not calls


def test_run_step4_commit_leg_recovery_branch_uses_recovery_pathspec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    (impl / "recovery-metadata.json").write_text("{}\n", encoding="utf-8")
    (impl / "recovery-commit-message.txt").write_text("Recover implementation\n", encoding="utf-8")
    (impl / "step2-recovery-paths-final.nul").write_bytes(b"recovered.txt\0")
    calls: list[list[str]] = []

    def fake_run_leg(*, argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, "COMMITTED=true\nSHA=abc\n", "")

    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(implement_dispatch, "_pathspec_clean_relative_to_head", lambda _pathspec: False)
    monkeypatch.setattr(dispatch_commit_route, "_pathspec_clean_relative_to_head", lambda _pathspec: False)

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    assert outcome == "continue"
    assert "COMMIT_ROUTE_OUTCOME=continue\n" in stdout
    assert calls == [[
        "implement",
        "commit",
        "--message",
        "Recover implementation",
        "--pathspec-from-file",
        str(impl / "step2-recovery-paths-final.nul"),
        "--pathspec-file-nul",
    ]]


def test_run_step4_commit_leg_recovery_metadata_missing_message_seed_fails(
    tmp_path: Path,
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    (impl / "recovery-metadata.json").write_text("{}\n", encoding="utf-8")
    (impl / "implementation-commit-message.txt").write_text("Ordinary\n", encoding="utf-8")
    (impl / "implementation-commit-paths.nul").write_bytes(b"file.txt\0")

    outcome, stdout = implement_dispatch._run_step4_commit_leg(impl, deadline_ms=123)

    assert outcome == "seed-failed"
    assert stdout == "COMMIT_ROUTE_OUTCOME=seed-failed\n"


def test_run_step4_recovery_recompute_scope_check_failure_emits_bail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    (impl / "recovery-metadata.json").write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(implement_dispatch, "_derive_pathspec_via_recovery_paths", lambda **_kwargs: 0)
    monkeypatch.setattr(dispatch_commit_route, "_derive_pathspec_via_recovery_paths", lambda **_kwargs: 0)
    command: list[str] = []

    def fake_scope_check(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        command.extend(args)
        return subprocess.CompletedProcess(args, 1, "", "scope fail")

    monkeypatch.setattr(dispatch_commit_route.proc, "run", fake_scope_check)

    rc = implement_dispatch._run_step4_recovery_recompute(impl, repo_root=Path("/repo"))

    out = capsys.readouterr()
    assert rc == 1
    assert "BAIL_REASON=recovery-out-of-scope\n" in out.out
    assert "NEXT_ACTION=" not in out.out
    assert command[0].endswith("/scripts/larch.sh")
    assert command[1:3] == ["dirty-tree", "scope-check"]


def test_step4_composite_recovery_out_of_scope_emits_bail_without_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    (impl / "recovery-metadata.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: ({"RELEVANT_CHECKS_OK": "true", "SITE": "step3"}, False),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: ({"RELEVANT_CHECKS_OK": "true", "SITE": "step3"}, False))
    monkeypatch.setattr(implement_dispatch, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(dispatch_commit_route, "_resolve_repo_root", lambda: Path("/repo"))
    monkeypatch.setattr(implement_dispatch, "_derive_pathspec_via_recovery_paths", lambda **_kwargs: 0)
    monkeypatch.setattr(dispatch_commit_route, "_derive_pathspec_via_recovery_paths", lambda **_kwargs: 0)
    monkeypatch.setattr(
        implement_dispatch,
        "_invoke_cli",
        lambda args, **_kwargs: subprocess.CompletedProcess(list(args), 1, "", "scope fail"),
    )
    monkeypatch.setattr(dispatch_commit_route, "_invoke_cli", lambda args, **_kwargs: subprocess.CompletedProcess(list(args), 1, "", "scope fail"))
    # Rust-owned run-log verbs route through the bootstrap runner; the recorded
    # append succeeds so the scope refusal is the only non-zero result.
    monkeypatch.setattr(dispatch_commit_route, "_invoke_larch", lambda args, **_kwargs: subprocess.CompletedProcess(list(args), 0, "", ""))

    # This case asserts the recovery scope refusal, so bind the session repo
    # root it needs first and stub `dirty-tree scope-check` (Rust-owned, and
    # dispatched through the bootstrap) to refuse explicitly, rather than
    # letting an unrelated bootstrap failure code stand in for a refusal.
    monkeypatch.setattr(dispatch_commit_route, "_session_validated_repo_root", lambda _tmpdir: Path("/repo"))

    def fake_scope_check(argv: Sequence[str], **_kwargs: object) -> CommandResult:
        command = [str(arg) for arg in argv]
        refused = command[1:3] == ["dirty-tree", "scope-check"]
        return CommandResult(tuple(command), 1 if refused else 0, "", "scope fail" if refused else "", 0.0)

    monkeypatch.setattr(dispatch_commit_route.proc, "run", fake_scope_check)

    rc = implement_dispatch.checks_commit_route_main([
        "--checks-site",
        "step3",
        "--commit-site",
        "step4",
    ])

    out = capsys.readouterr().out
    assert rc == 1
    assert "BAIL_REASON=recovery-out-of-scope\n" in out
    assert "NEXT_ACTION=" not in out


def test_composite_commit_route_spawns_child_with_emit_next_action_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    calls: list[list[str]] = []

    def fake_run_leg(*, argv: Sequence[str], deadline_ms: int, label: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        assert deadline_ms == 1234
        assert label == "commit-route:step7"
        return subprocess.CompletedProcess(
            list(argv),
            0,
            "COMMIT_ROUTE_OUTCOME=continue\nCOMMITTED=true\nCOMMIT_OUTCOME=ok\n",
            "",
        )

    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step6", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: (
            {"RELEVANT_CHECKS_OK": "true", "SITE": "step6", "COVERAGE": "changed", "PHASE": "checks"},
            False,
        ))
    monkeypatch.setattr(implement_dispatch, "_run_leg_with_timeout", fake_run_leg)
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", fake_run_leg)

    rc = implement_dispatch.checks_commit_route_main(
        ["--checks-site", "step6", "--commit-site", "step7", "--commit-deadline-ms", "1234"]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=changed PHASE=checks\n" in out
    assert "NEXT_ACTION=continue\n" in out
    assert calls == [
        [
            "implement",
            "commit-route",
            "--site",
            "step7",
            "--implement-tmpdir",
            str(impl),
            "--emit-next-action",
            "false",
        ]
    ]


def test_composite_checks_timeout_with_partial_pass_skips_commit_leg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_leg_with_timeout",
        lambda **_kwargs: subprocess.TimeoutExpired(
            cmd=["checks", "run-relevant"],
            timeout=1,
            output="RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=changed PHASE=checks\n",
            stderr="timeout",
        ),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", lambda **_kwargs: subprocess.TimeoutExpired(
            cmd=["checks", "run-relevant"],
            timeout=1,
            output="RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=changed PHASE=checks\n",
            stderr="timeout",
        ))

    def fail_commit(**_kwargs: object) -> tuple[implement_dispatch.CommitRouteOutcome, str]:
        raise AssertionError("commit leg must not start after checks-leg timeout")

    monkeypatch.setattr(implement_dispatch, "_run_commit_route_leg", fail_commit)
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", fail_commit)

    rc = implement_dispatch.checks_commit_route_main(["--checks-site", "step6", "--commit-site", "step7"])

    assert rc == 0
    assert capsys.readouterr().out == "STATUS=fail FAILURE_REASON=checks-leg-timeout\nNEXT_ACTION=checks-failed\n"


def test_composite_checks_failure_skips_commit_leg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setattr(
        implement_dispatch,
        "_run_relevant_checks_for_site",
        lambda **_kwargs: ({"STATUS": "fail", "FAILURE_REASON": "checks-leg-timeout"}, True),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_relevant_checks_for_site", lambda **_kwargs: ({"STATUS": "fail", "FAILURE_REASON": "checks-leg-timeout"}, True))

    def fail_commit(**_kwargs: object) -> tuple[implement_dispatch.CommitRouteOutcome, str]:
        raise AssertionError("commit leg must not start after checks failure")

    monkeypatch.setattr(implement_dispatch, "_run_commit_route_leg", fail_commit)
    monkeypatch.setattr(dispatch_commit_route, "_run_commit_route_leg", fail_commit)

    rc = implement_dispatch.checks_commit_route_main(["--checks-site", "step6", "--commit-site", "step7"])

    assert rc == 0
    assert capsys.readouterr().out == "STATUS=fail FAILURE_REASON=checks-leg-timeout\nNEXT_ACTION=checks-failed\n"


def test_commit_leg_timeout_seeds_stall_in_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    impl = make_implement_tmpdir(tmp_path)
    seed_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        implement_dispatch,
        "_run_leg_with_timeout",
        lambda **_kwargs: subprocess.TimeoutExpired(cmd=["child"], timeout=1, output="COMMITTED=false\n", stderr="timeout"),
    )
    monkeypatch.setattr(dispatch_commit_route, "_run_leg_with_timeout", lambda **_kwargs: subprocess.TimeoutExpired(cmd=["child"], timeout=1, output="COMMITTED=false\n", stderr="timeout"))
    monkeypatch.setattr(implement_dispatch, "_commit_route_log_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dispatch_commit_route, "_commit_route_log_failure", lambda *_args, **_kwargs: None)

    def fake_seed(_tmp: Path, *, stall_step: str, bail_reason: str) -> bool:
        seed_calls.append((stall_step, bail_reason))
        return True

    monkeypatch.setattr(implement_dispatch, "_seed_durable_stall_state", fake_seed)
    monkeypatch.setattr(dispatch_commit_route, "_seed_durable_stall_state", fake_seed)

    outcome, stdout = implement_dispatch._run_commit_route_leg(
        site_name="step7",
        implement_tmpdir=impl,
        deadline_ms=1,
    )

    assert outcome == "seeded-stall"
    assert stdout == "COMMITTED=false\n"
    assert seed_calls == [("7", "review-fix-commit-failed")]


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
    monkeypatch.setattr(dispatch_recovery, "_invoke_cli", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(implement_dispatch, "_run", fake_run)
    monkeypatch.setattr(dispatch_recovery, "_run", fake_run)

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
