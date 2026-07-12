# pyright: reportPrivateUsage=false
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from larch import cli as root_cli
from larch import io as larch_io
from larch.bgjob import adapt, cli, daemon, model, registry
from larch.core import config, process_identity


def _identity(*, pid: int, pgid: int | None = None) -> process_identity.RecordedProcessIdentity:
    return process_identity.RecordedProcessIdentity(
        pid=pid,
        pgid=pid if pgid is None else pgid,
        start_time=f"start-{pid}",
        command_signature=f"command-{pid}",
        expected_signature="",
    )


def _spec(tmp_path: Path, *, step: str = "demo-step", budget_s: int = 300) -> model.JobSpec:
    log_dir = tmp_path / "bgjob"
    log_dir.mkdir(exist_ok=True)
    return model.JobSpec(
        step=step,
        tmpdir=tmp_path,
        log_dir=log_dir,
        budget_s=budget_s,
        command=(sys.executable, "-c", "print('child')"),
        run_id="run-1",
        owner=model.OwnerIdentity(recorded=None),
    )


def _entry(
    spec: model.JobSpec,
    *,
    daemon_pid: int = 101,
    child_pid: int = 202,
    start_epoch: int | None = None,
) -> model.RegistryEntry:
    return model.RegistryEntry(
        step=spec.step,
        run_id=spec.run_id,
        tmpdir=spec.tmpdir,
        log_dir=spec.log_dir,
        clone_path=Path.cwd().resolve(),
        daemon=_identity(pid=daemon_pid),
        child=_identity(pid=child_pid, pgid=303),
        owner=None,
        start_epoch=int(time.time()) if start_epoch is None else start_epoch,
        budget_s=spec.budget_s,
        stdout_log=spec.log_dir / f"{spec.step}.stdout.log",
        stderr_log=spec.log_dir / f"{spec.step}.stderr.log",
        result_env=model.result_env_path(tmpdir=spec.tmpdir, step=spec.step),
    )


@pytest.fixture(autouse=True)
def adapter_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.ENV_BGJOB_REGISTRY_ROOT, str(tmp_path / "registry"))
    monkeypatch.setenv(config.ENV_CLAUDE_PLUGIN_ROOT, str(Path(__file__).resolve().parents[3]))


def _verdict(*, live: bool, reason: str = "ok") -> model.LivenessVerdict:
    return model.LivenessVerdict(live=live, reason=reason)


def _owner_none(_raw: str | None) -> model.OwnerIdentity:
    return model.OwnerIdentity(recorded=None)


def _return_verdict(
    verdict: model.LivenessVerdict,
) -> Callable[[model.RegistryEntry], model.LivenessVerdict]:
    def fake_liveness(_entry: model.RegistryEntry) -> model.LivenessVerdict:
        return verdict

    return fake_liveness


def _record_start(
    launches: list[model.JobSpec],
) -> Callable[[model.JobSpec], int]:
    def fake_start(spec: model.JobSpec) -> int:
        launches.append(spec)
        return 0

    return fake_start


def _start_ok(_spec: model.JobSpec) -> int:
    return 0


def _start_exception(_spec: model.JobSpec) -> int:
    raise RuntimeError("startup pipe")


def _read_entry_as(
    entry: model.RegistryEntry,
) -> Callable[[Path], model.RegistryEntry]:
    def fake_read(_path: Path) -> model.RegistryEntry:
        return entry

    return fake_read


def _read_result_sequence(
    results: Iterator[model.ResultEnvRows | None],
) -> Callable[[model.JobSpec], model.ResultEnvRows | None]:
    def fake_read_result(spec: model.JobSpec) -> model.ResultEnvRows | None:
        _ = spec
        return next(results)

    return fake_read_result


def test_fresh_start_builds_adapter_daemon_spec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path)
    captured: list[model.JobSpec] = []

    def fake_start(launch_spec: model.JobSpec) -> int:
        captured.append(launch_spec)
        return 0

    monkeypatch.setattr(adapt.daemon, "start_daemon", fake_start)

    assert adapt.start_or_reattach(spec) == 0

    assert len(captured) == 1
    launch_spec = captured[0]
    expected_merge = tmp_path / "bgjob" / "demo-step.merge.env"
    assert launch_spec.merge_result_env == expected_merge
    assert launch_spec.command == (
        *spec.command,
        "--bgjob-child",
        "--merge-result-env",
        str(expected_merge),
    )
    assert expected_merge.read_text(encoding="utf-8") == ""
    assert expected_merge.stat().st_mode & 0o777 == 0o600


def test_adapt_main_strips_leading_delimiter_and_uses_tmpdir_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[model.JobSpec] = []

    def fake_adapt(spec: model.JobSpec) -> int:
        captured.append(spec)
        return 0

    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    monkeypatch.setattr(
        cli.daemon,
        "owner_identity_from_env",
        _owner_none,
    )
    monkeypatch.setattr(cli.adapt, "start_or_reattach", fake_adapt)

    rc = cli.adapt_main(
        [
            "--step",
            "demo-step",
            "--budget-s",
            "10",
            "--",
            sys.executable,
            "-c",
            "print('ok')",
        ]
    )

    assert rc == 0
    assert captured[0].tmpdir == tmp_path
    assert captured[0].command[0] == sys.executable
    assert captured[0].command[0] != "--"


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--step", "demo", "--budget-s", "0", "--", "true"], "invalid-budget"),
        (["--step", "demo", "--budget-s", "1", "--"], "missing-command"),
        (["--step", "demo", "--budget-s", "1", "--", "true"], "missing-tmpdir"),
        (["--step", "demo", "--", "true"], "invalid-input"),
    ],
)
def test_adapt_main_contract_errors(
    argv: list[str],
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(config.ENV_IMPLEMENT_TMPDIR, raising=False)

    assert cli.adapt_main(argv) == 2
    assert capsys.readouterr().out == f"BGJOB_ERROR={expected}\n"


def test_adapt_main_bad_step_is_machine_readable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.adapt_main(
        [
            "--step",
            "bad/step",
            "--tmpdir",
            str(tmp_path),
            "--budget-s",
            "1",
            "--",
            "true",
        ]
    ) == 2
    assert capsys.readouterr().out == "BGJOB_ERROR=invalid-input\n"


def test_completed_result_emits_wait_compatible_rows_without_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = _spec(tmp_path)
    result = model.result_env_path(tmpdir=tmp_path, step=spec.step)
    larch_io.write_kvs(
        path=result,
        values=[("BGJOB_RC", "0"), ("STEP", spec.step), ("CUSTOM", "merged")],
    )

    def fail_start(_spec: model.JobSpec) -> int:
        pytest.fail("completed results must not launch")

    monkeypatch.setattr(adapt.daemon, "start_daemon", fail_start)

    assert adapt.start_or_reattach(spec) == 0
    assert capsys.readouterr().out == (
        "BGJOB_STATUS=DONE\nBGJOB_RC=0\nSTEP=demo-step\nCUSTOM=merged\n"
    )


def test_completed_result_accepts_blank_lines_like_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = _spec(tmp_path)
    result = model.result_env_path(tmpdir=tmp_path, step=spec.step)
    larch_io.write_kvs(
        path=result,
        values=[("BGJOB_RC", "0"), ("STEP", spec.step)],
    )
    _ = result.write_text(f"\n{result.read_text(encoding='utf-8')}\n", encoding="utf-8")

    def fail_start(_spec: model.JobSpec) -> int:
        pytest.fail("completed results must not launch")

    monkeypatch.setattr(adapt.daemon, "start_daemon", fail_start)

    assert adapt.start_or_reattach(spec) == 0
    assert capsys.readouterr().out.startswith("BGJOB_STATUS=DONE\n")


@pytest.mark.parametrize(
    "text",
    [
        "",
        "BGJOB_RC=0\n",
        "STEP=demo-step\n",
        "BGJOB_RC=0\nSTEP=other-step\n",
        "BGJOB_RC=0\nmalformed\nSTEP=demo-step\n",
    ],
)
def test_incomplete_or_malformed_result_does_not_suppress_launch(
    text: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path)
    result = model.result_env_path(tmpdir=tmp_path, step=spec.step)
    result.parent.mkdir(parents=True, exist_ok=True)
    _ = result.write_text(text, encoding="utf-8")
    launches: list[model.JobSpec] = []
    monkeypatch.setattr(adapt.daemon, "start_daemon", _record_start(launches))

    assert adapt.start_or_reattach(spec) == 0
    assert len(launches) == 1


@pytest.mark.parametrize("unsafe_kind", ["symlink", "directory"])
def test_unsafe_result_fails_closed_without_launch(
    unsafe_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = _spec(tmp_path)
    result = model.result_env_path(tmpdir=tmp_path, step=spec.step)
    result.parent.mkdir(parents=True, exist_ok=True)
    if unsafe_kind == "symlink":
        target = tmp_path / "outside-result"
        _ = target.write_text("BGJOB_RC=0\nSTEP=demo-step\n", encoding="utf-8")
        _ = result.symlink_to(target)
    else:
        result.mkdir()
    launches: list[model.JobSpec] = []
    monkeypatch.setattr(adapt.daemon, "start_daemon", _record_start(launches))

    with pytest.raises(adapt.AdaptError, match="unsafe-path"):
        _ = adapt.start_or_reattach(spec)
    assert "BGJOB_STATUS=DONE" not in capsys.readouterr().out
    assert not launches


def test_live_daemon_and_child_reattach_with_validated_child_pgid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = _spec(tmp_path)
    _ = registry.write_entry(_entry(spec))
    monkeypatch.setattr(adapt.registry, "daemon_liveness", _return_verdict(_verdict(live=True)))
    monkeypatch.setattr(adapt.registry, "child_liveness", _return_verdict(_verdict(live=True)))

    assert adapt.start_or_reattach(spec) == 0
    assert capsys.readouterr().out == "BGJOB_STATUS=STARTED STEP=demo-step PGID=303\n"


@pytest.mark.parametrize(
    ("daemon_verdict", "child_verdict", "token"),
    [
        (_verdict(live=False, reason="missing-pid"), _verdict(live=True), "registry-ownership-lost"),
        (
            _verdict(live=False, reason="missing-pid"),
            _verdict(live=False, reason="missing-pid"),
            "registry-dead",
        ),
        (
            _verdict(live=False, reason="identity-probe-timeout"),
            _verdict(live=False, reason="missing-pid"),
            "registry-identity-unverifiable",
        ),
    ],
)
def test_in_budget_unusable_registry_fails_closed_without_stale_pgid(
    daemon_verdict: model.LivenessVerdict,
    child_verdict: model.LivenessVerdict,
    token: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = _spec(tmp_path)
    path = registry.write_entry(_entry(spec))
    monkeypatch.setattr(adapt.registry, "daemon_liveness", _return_verdict(daemon_verdict))
    monkeypatch.setattr(adapt.registry, "child_liveness", _return_verdict(child_verdict))
    launches: list[model.JobSpec] = []
    monkeypatch.setattr(adapt.daemon, "start_daemon", _record_start(launches))

    with pytest.raises(adapt.AdaptError, match=token):
        _ = adapt.start_or_reattach(spec)

    assert path.is_file()
    assert not launches
    assert "PGID=" not in capsys.readouterr().out


@pytest.mark.parametrize("reason", ["missing-pid", "identity-probe-timeout"])
def test_live_daemon_reattaches_while_it_finalizes_child(
    reason: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = _spec(tmp_path)
    _ = registry.write_entry(_entry(spec))
    monkeypatch.setattr(adapt.registry, "daemon_liveness", _return_verdict(_verdict(live=True)))
    monkeypatch.setattr(
        adapt.registry,
        "child_liveness",
        _return_verdict(_verdict(live=False, reason=reason)),
    )

    assert adapt.start_or_reattach(spec) == 0
    assert capsys.readouterr().out == "BGJOB_STATUS=STARTED STEP=demo-step PGID=303\n"


def test_live_daemon_reattaches_with_external_log_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    external_log_dir = tmp_path.parent / f"{tmp_path.name}-external-logs"
    external_log_dir.mkdir()
    spec = replace(_spec(tmp_path), log_dir=external_log_dir)
    _ = registry.write_entry(_entry(spec))
    monkeypatch.setattr(adapt.registry, "daemon_liveness", _return_verdict(_verdict(live=True)))
    monkeypatch.setattr(adapt.registry, "child_liveness", _return_verdict(_verdict(live=True)))

    assert adapt.start_or_reattach(spec) == 0
    assert capsys.readouterr().out == "BGJOB_STATUS=STARTED STEP=demo-step PGID=303\n"


def test_live_daemon_rejects_child_identity_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = _spec(tmp_path)
    _ = registry.write_entry(_entry(spec))
    monkeypatch.setattr(adapt.registry, "daemon_liveness", _return_verdict(_verdict(live=True)))
    monkeypatch.setattr(
        adapt.registry,
        "child_liveness",
        _return_verdict(_verdict(live=False, reason="pgid-mismatch")),
    )

    with pytest.raises(adapt.AdaptError, match="registry-identity-unverifiable"):
        _ = adapt.start_or_reattach(spec)

    assert "PGID=" not in capsys.readouterr().out


@pytest.mark.parametrize("live_part", ["daemon", "child"])
def test_expired_live_registry_fails_closed(
    live_part: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path, budget_s=1)
    path = registry.write_entry(_entry(spec, start_epoch=1))
    daemon_live = live_part == "daemon"
    child_live = live_part == "child"
    monkeypatch.setattr(
        adapt.registry,
        "daemon_liveness",
        _return_verdict(_verdict(live=daemon_live, reason="ok" if daemon_live else "missing-pid")),
    )
    monkeypatch.setattr(
        adapt.registry,
        "child_liveness",
        _return_verdict(_verdict(live=child_live, reason="ok" if child_live else "missing-pid")),
    )

    with pytest.raises(adapt.AdaptError, match="expired-live"):
        _ = adapt.start_or_reattach(spec)
    assert path.is_file()


def test_expired_registry_with_unverifiable_liveness_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path, budget_s=1)
    old_path = registry.write_entry(_entry(spec, start_epoch=1))
    dead = _verdict(live=False, reason="identity-probe-timeout")
    monkeypatch.setattr(adapt.registry, "daemon_liveness", _return_verdict(dead))
    monkeypatch.setattr(adapt.registry, "child_liveness", _return_verdict(dead))
    launches: list[model.JobSpec] = []
    monkeypatch.setattr(adapt.daemon, "start_daemon", _record_start(launches))

    with pytest.raises(adapt.AdaptError, match="registry-identity-unverifiable"):
        _ = adapt.start_or_reattach(spec)
    assert old_path.is_file()
    assert not launches


def test_expired_verified_dead_registry_is_removed_and_relaunched_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path, budget_s=1)
    old_path = registry.write_entry(_entry(spec, start_epoch=1))
    dead = _verdict(live=False, reason="missing-pid")
    launches: list[model.JobSpec] = []
    monkeypatch.setattr(adapt.registry, "daemon_liveness", _return_verdict(dead))
    monkeypatch.setattr(adapt.registry, "child_liveness", _return_verdict(dead))
    monkeypatch.setattr(adapt.daemon, "start_daemon", _record_start(launches))

    assert adapt.start_or_reattach(spec) == 0

    assert not old_path.exists()
    assert len(launches) == 1


def test_expired_registry_with_identity_mismatch_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path, budget_s=1)
    old_path = registry.write_entry(_entry(spec, start_epoch=1))
    mismatched = _verdict(live=False, reason="start-time-mismatch")
    launches: list[model.JobSpec] = []
    monkeypatch.setattr(adapt.registry, "daemon_liveness", _return_verdict(mismatched))
    monkeypatch.setattr(adapt.registry, "child_liveness", _return_verdict(mismatched))
    monkeypatch.setattr(adapt.daemon, "start_daemon", _record_start(launches))

    with pytest.raises(adapt.AdaptError, match="registry-identity-unverifiable"):
        _ = adapt.start_or_reattach(spec)

    assert old_path.is_file()
    assert not launches


@pytest.mark.parametrize("field", ["step", "run_id", "tmpdir", "clone_path"])
def test_registry_identity_mismatch_fails_closed(
    field: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path)
    entry = _entry(spec)
    changed: object
    if field == "step":
        changed = "other-step"
    elif field == "run_id":
        changed = "other-run"
    else:
        changed = tmp_path.parent
    mismatched = replace(entry, **{field: changed})
    path = model.registry_path(run_id=spec.run_id, step=spec.step)
    _ = path.write_text("placeholder\n", encoding="utf-8")
    monkeypatch.setattr(adapt.registry, "read_entry", _read_entry_as(mismatched))

    with pytest.raises(adapt.AdaptError, match="registry-identity-mismatch"):
        _ = adapt.start_or_reattach(spec)


def test_registry_child_pgid_must_be_structurally_valid(
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path)
    entry = replace(_entry(spec), child=_identity(pid=202, pgid=0))
    _ = registry.write_entry(entry)

    with pytest.raises(adapt.AdaptError, match="registry-invalid"):
        _ = adapt.start_or_reattach(spec)


@pytest.mark.parametrize("unsafe_kind", ["malformed", "symlink", "directory"])
def test_unsafe_registry_fails_closed_without_launch(
    unsafe_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path)
    path = model.registry_path(run_id=spec.run_id, step=spec.step)
    if unsafe_kind == "malformed":
        _ = path.write_text("STEP=demo-step\n", encoding="utf-8")
    elif unsafe_kind == "symlink":
        target = tmp_path / "outside-registry"
        _ = target.write_text("STEP=demo-step\n", encoding="utf-8")
        _ = path.symlink_to(target)
    else:
        path.mkdir()
    launches: list[model.JobSpec] = []
    monkeypatch.setattr(adapt.daemon, "start_daemon", _record_start(launches))

    with pytest.raises(adapt.AdaptError, match="registry-invalid"):
        _ = adapt.start_or_reattach(spec)
    assert not launches


def test_replaced_registry_fails_closed_without_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path)
    entry = _entry(spec)
    path = registry.write_entry(entry)
    launches: list[model.JobSpec] = []

    def replace_during_read(read_path: Path) -> model.RegistryEntry:
        text = read_path.read_text(encoding="utf-8")
        _ = read_path.write_text(f"{text}REPLACED=yes\n", encoding="utf-8")
        return entry

    monkeypatch.setattr(adapt.registry, "read_entry", replace_during_read)
    monkeypatch.setattr(adapt.daemon, "start_daemon", _record_start(launches))

    with pytest.raises(adapt.AdaptError, match="registry-invalid"):
        _ = adapt.start_or_reattach(spec)
    assert path.is_file()
    assert not launches


def test_result_appearing_at_final_launch_check_wins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = _spec(tmp_path)
    complete = model.ResultEnvRows(
        rows=(("BGJOB_RC", "0"), ("STEP", spec.step), ("LATE", "yes"))
    )
    reads = iter([None, None, complete])
    monkeypatch.setattr(adapt, "_read_completed_result", _read_result_sequence(reads))

    def fail_start(_spec: model.JobSpec) -> int:
        pytest.fail("late completed result must suppress launch")

    monkeypatch.setattr(adapt.daemon, "start_daemon", fail_start)

    assert adapt.start_or_reattach(spec) == 0
    assert capsys.readouterr().out.endswith("LATE=yes\n")


@pytest.mark.parametrize("unsafe_kind", ["symlink", "directory"])
def test_merge_env_rejects_unsafe_existing_path(
    unsafe_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path)
    merge_env = tmp_path / "bgjob" / "demo-step.merge.env"
    if unsafe_kind == "symlink":
        target = tmp_path / "outside-merge"
        _ = target.write_text("CUSTOM=bad\n", encoding="utf-8")
        _ = merge_env.symlink_to(target)
    else:
        merge_env.mkdir()
    monkeypatch.setattr(adapt.daemon, "start_daemon", _start_ok)

    with pytest.raises(adapt.AdaptError, match="unsafe-path"):
        _ = adapt.start_or_reattach(spec)


def test_merge_env_publication_uses_pinned_bgjob_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path)
    observed: dict[str, Path] = {}
    original = adapt.larch_io.trusted_atomic_write

    def capture(*, path: Path, text: str, root: Path, mode: int) -> None:
        observed.update(path=path, root=root)
        original(path=path, text=text, root=root, mode=mode)

    monkeypatch.setattr(adapt.larch_io, "trusted_atomic_write", capture)
    monkeypatch.setattr(adapt.daemon, "start_daemon", _start_ok)

    assert adapt.start_or_reattach(spec) == 0
    assert observed == {
        "path": tmp_path / "bgjob" / "demo-step.merge.env",
        "root": tmp_path / "bgjob",
    }


def test_persisted_plugin_root_is_rehydrated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    spec = _spec(tmp_path)
    _ = (tmp_path / "session-env.sh").write_text(
        f"LARCH_CLAUDE_PLUGIN_ROOT={repo_root}\n",
        encoding="utf-8",
    )
    monkeypatch.delenv(config.ENV_CLAUDE_PLUGIN_ROOT, raising=False)
    monkeypatch.setattr(adapt.daemon, "start_daemon", _start_ok)

    assert adapt.start_or_reattach(spec) == 0
    assert os.environ[config.ENV_CLAUDE_PLUGIN_ROOT] == str(repo_root)


@pytest.mark.parametrize("state", ["missing", "malformed"])
def test_missing_or_malformed_plugin_root_fails_before_launch(
    state: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path)
    monkeypatch.delenv(config.ENV_CLAUDE_PLUGIN_ROOT, raising=False)
    if state == "malformed":
        _ = (tmp_path / "plugin-root.env").write_text(
            "CLAUDE_PLUGIN_ROOT=/does/not/exist\n",
            encoding="utf-8",
        )
    launches: list[model.JobSpec] = []
    monkeypatch.setattr(adapt.daemon, "start_daemon", _record_start(launches))

    with pytest.raises(adapt.AdaptError, match="plugin-root"):
        _ = adapt.start_or_reattach(spec)
    assert not launches


@pytest.mark.parametrize("pipe_payload", [b"", b"not-a-startup-record\n"])
def test_daemon_start_failures_are_machine_readable(
    pipe_payload: bytes,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    read_fd, write_fd = os.pipe()
    original_close = daemon.os.close

    def fake_pipe() -> tuple[int, int]:
        return read_fd, write_fd

    def fake_fork() -> int:
        if pipe_payload:
            _ = os.write(write_fd, pipe_payload)
        return 1

    def close_except_startup_writer(fd: int) -> None:
        if fd != write_fd or not pipe_payload:
            original_close(fd)

    monkeypatch.setattr(
        cli.daemon,
        "owner_identity_from_env",
        _owner_none,
    )
    monkeypatch.setattr(daemon.os, "pipe", fake_pipe)
    monkeypatch.setattr(daemon.os, "fork", fake_fork)
    monkeypatch.setattr(daemon.os, "close", close_except_startup_writer)

    try:
        rc = cli.adapt_main(
            [
                "--step",
                "demo-step",
                "--tmpdir",
                str(tmp_path),
                "--budget-s",
                "10",
                "--",
                "true",
            ]
        )
    finally:
        if pipe_payload:
            original_close(write_fd)

    assert rc == 2
    assert capsys.readouterr().out == "BGJOB_ERROR=daemon-start-failed\n"


def test_daemon_start_exception_is_machine_readable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli.daemon, "owner_identity_from_env", _owner_none)
    monkeypatch.setattr(adapt.daemon, "start_daemon", _start_exception)

    rc = cli.adapt_main(
        [
            "--step",
            "demo-step",
            "--tmpdir",
            str(tmp_path),
            "--budget-s",
            "10",
            "--",
            "true",
        ]
    )

    assert rc == 2
    assert capsys.readouterr().out == "BGJOB_ERROR=daemon-start-exception\n"


def test_dispatcher_registers_adapt_as_machine_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[tuple[str, str, list[str]]] = []

    def fake_run(module_name: str, func_name: str, argv: list[str]) -> int:
        called.append((module_name, func_name, argv))
        return 0

    monkeypatch.delenv("LARCH_QUIET_DISABLE", raising=False)
    monkeypatch.setattr(root_cli, "_run_subcommand", fake_run)

    assert root_cli.main(["bgjob", "adapt", "--help"]) == 0
    assert called == [("larch.bgjob.cli", "adapt_main", ["--help"])]
    assert os.environ["LARCH_QUIET_DISABLE"] == "1"
    assert ("bgjob", "adapt") in root_cli._REGISTRY
    assert ("bgjob", "adapt") in root_cli._MACHINE_STDOUT_KEYS


def test_forked_daemon_does_not_retain_adapter_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path, budget_s=10)
    child_pid = 0

    def fork_and_return(_spec: model.JobSpec) -> int:
        nonlocal child_pid
        pid = os.fork()
        if pid == 0:
            time.sleep(1)
            os._exit(0)
        child_pid = pid
        _ = registry.write_entry(_entry(spec))
        return 0

    monkeypatch.setattr(adapt.daemon, "start_daemon", fork_and_return)
    monkeypatch.setattr(adapt.registry, "daemon_liveness", _return_verdict(_verdict(live=True)))
    monkeypatch.setattr(adapt.registry, "child_liveness", _return_verdict(_verdict(live=True)))

    assert adapt.start_or_reattach(spec) == 0
    started = time.monotonic()
    try:
        assert adapt.start_or_reattach(spec) == 0
        assert time.monotonic() - started < 0.5
    finally:
        if child_pid > 0:
            _ = os.waitpid(child_pid, 0)


def test_decision_lock_rejects_swapped_registry_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _spec(tmp_path)
    registry_root = tmp_path / "registry"
    registry_root.mkdir()
    moved_root = tmp_path / "moved-registry"
    outside = tmp_path / "outside"
    outside.mkdir()
    original_open = os.open

    def swap_after_open(path: str | bytes | os.PathLike[str] | os.PathLike[bytes], flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        fd = original_open(path, flags, mode, dir_fd=dir_fd)
        if Path(os.fsdecode(path)) == registry_root and dir_fd is None:
            _ = registry_root.rename(moved_root)
            registry_root.symlink_to(outside, target_is_directory=True)
        return fd

    monkeypatch.setattr(adapt.model, "registry_root", lambda: registry_root)
    monkeypatch.setattr(adapt.os, "open", swap_after_open)

    with pytest.raises(adapt.AdaptError, match="lock-failed"):
        _ = adapt.start_or_reattach(spec)

    assert not tuple(outside.iterdir())


def test_concurrent_adapter_decisions_launch_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = _spec(tmp_path)
    launch_count = 0
    launch_started = threading.Event()
    release_launch = threading.Event()

    def fake_start(_spec: model.JobSpec) -> int:
        nonlocal launch_count
        launch_count += 1
        launch_started.set()
        assert release_launch.wait(timeout=2)
        _ = registry.write_entry(_entry(spec))
        return 0

    monkeypatch.setattr(adapt.daemon, "start_daemon", fake_start)
    monkeypatch.setattr(adapt.registry, "daemon_liveness", _return_verdict(_verdict(live=True)))
    monkeypatch.setattr(adapt.registry, "child_liveness", _return_verdict(_verdict(live=True)))
    errors: list[BaseException] = []

    def invoke() -> None:
        try:
            _ = adapt.start_or_reattach(spec)
        except BaseException as exc:  # test thread must report failures to the parent
            errors.append(exc)

    first = threading.Thread(target=invoke)
    second = threading.Thread(target=invoke)
    first.start()
    assert launch_started.wait(timeout=2)
    second.start()
    release_launch.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not errors
    assert not first.is_alive()
    assert not second.is_alive()
    assert launch_count == 1
    assert "BGJOB_STATUS=STARTED STEP=demo-step PGID=303" in capsys.readouterr().out


def test_merge_env_rows_are_published_after_child_writes(tmp_path: Path) -> None:
    spec = replace(
        _spec(tmp_path),
        command=(
            sys.executable,
            "-c",
            "import pathlib, sys; path = pathlib.Path(sys.argv[sys.argv.index('--merge-result-env') + 1]); path.write_text(path.read_text(encoding='utf-8') + 'CHILD_WRITTEN=ok\\n', encoding='utf-8')",
        ),
    )
    launch_spec = adapt._prepare_launch_spec(spec)
    assert launch_spec.merge_result_env is not None
    _ = launch_spec.merge_result_env.write_text("PRESEEDED=yes\n", encoding="utf-8")
    _ = subprocess.run(launch_spec.command, check=True)

    daemon.write_result(spec=launch_spec, rc="0", elapsed_s=1)

    rows = larch_io.read_kvs(model.result_env_path(tmpdir=tmp_path, step=spec.step))
    assert rows["PRESEEDED"] == "yes"
    assert rows["CHILD_WRITTEN"] == "ok"
