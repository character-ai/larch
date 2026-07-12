"""Start-or-reattach protocol for bgjob-backed step adapters."""

from __future__ import annotations

import contextlib
import fcntl
import os
import stat
from collections.abc import Generator
from dataclasses import dataclass, replace
from pathlib import Path

from larch import io as larch_io
from larch.bgjob import daemon, model, registry
from larch.core import config
from larch.report.progress_file import validate_run_id

_DEAD_IDENTITY_REASONS = frozenset(
    {
        "missing-pid",
        "pgid-mismatch",
        "start-time-mismatch",
        "command-mismatch",
        "expected-command-mismatch",
    }
)
_FORK_CLOSE_FDS: set[int] = set()


class AdaptError(RuntimeError):
    """A fail-closed adapter outcome with a stable machine token."""

    def __init__(self, token: str) -> None:
        super().__init__(token)
        self.token = token


@dataclass(frozen=True)
class RegistrySnapshot:
    path: Path
    entry: model.RegistryEntry | None
    fingerprint: tuple[int, int, int, int] | None
    invalid: bool = False


@dataclass(frozen=True)
class ProcessState:
    live: bool
    proven_dead: bool


def _close_adapter_locks_after_fork() -> None:
    for fd in tuple(_FORK_CLOSE_FDS):
        with contextlib.suppress(OSError):
            os.close(fd)
    _FORK_CLOSE_FDS.clear()


os.register_at_fork(after_in_child=_close_adapter_locks_after_fork)


def _stat_fingerprint(path: Path) -> tuple[int, int, int, int] | None:
    try:
        file_stat = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(file_stat.st_mode):
        raise AdaptError("unsafe-path")
    return (file_stat.st_dev, file_stat.st_ino, file_stat.st_mtime_ns, file_stat.st_size)


def _lock_path(*, run_id: str, step: str) -> Path:
    root = model.registry_root()
    run_slug = validate_run_id(run_id)
    step_slug = model.validate_slug(step, label="step")
    return root / f"{run_slug}-{step_slug}.lock"


@contextlib.contextmanager
def _decision_lock(*, run_id: str, step: str) -> Generator[None, None, None]:
    try:
        path = _lock_path(run_id=run_id, step=step)
    except (OSError, ValueError) as exc:
        raise AdaptError("lock-failed") from exc
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = -1
    try:
        fd = os.open(path, flags, 0o600)
        opened_stat = os.fstat(fd)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise AdaptError("unsafe-path")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        path_stat = path.lstat()
        if (path_stat.st_dev, path_stat.st_ino) != (opened_stat.st_dev, opened_stat.st_ino):
            raise AdaptError("lock-failed")
        _FORK_CLOSE_FDS.add(fd)
        yield
    except OSError as exc:
        raise AdaptError("lock-failed") from exc
    finally:
        _FORK_CLOSE_FDS.discard(fd)
        if fd >= 0:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
            with contextlib.suppress(OSError):
                os.close(fd)


def _read_completed_result(*, spec: model.JobSpec) -> model.ResultEnvRows | None:
    try:
        root = model.bgjob_dir(spec.tmpdir)
        step = model.validate_slug(spec.step, label="step")
        path = root / f"{step}{config.BGJOB_RESULT_ENV_SUFFIX}"
    except (OSError, ValueError) as exc:
        raise AdaptError("unsafe-path") from exc
    result: model.ResultEnvRows | None = None
    try:
        before = _stat_fingerprint(path)
    except AdaptError:
        before = None
    if before is not None and not path.is_symlink():
        try:
            text = larch_io.read_trusted_text(
                path,
                root=root,
                errors="strict",
                reject_cr=True,
            )
            after = _stat_fingerprint(path)
        except (AdaptError, OSError, UnicodeError, ValueError):
            text = ""
            after = None
        if before == after and text:
            result = _parse_completed_rows(text=text, step=spec.step)
    return result


def _parse_completed_rows(*, text: str, step: str) -> model.ResultEnvRows | None:
    rows: list[tuple[str, str]] = []
    valid = True
    for line in text.splitlines():
        if not line or "=" not in line:
            valid = False
            break
        key, value = line.split("=", 1)
        if not key:
            valid = False
            break
        rows.append((key, value))
    parsed = dict(rows)
    if not parsed.get(config.BGJOB_RC_KEY) or parsed.get("STEP") != step:
        valid = False
    return model.ResultEnvRows(rows=tuple(rows)) if valid else None


def _emit_done(result: model.ResultEnvRows) -> None:
    rows = [(config.BGJOB_STATUS_KEY, config.BGJOB_STATUS_DONE), *result.rows]
    print(larch_io.format_kvs(rows), end="")


def _emit_started(*, step: str, pgid: int) -> None:
    print(f"{config.BGJOB_STATUS_KEY}={config.BGJOB_STATUS_STARTED} STEP={step} PGID={pgid}")


def _snapshot_registry(*, spec: model.JobSpec) -> RegistrySnapshot:
    try:
        root = model.registry_root()
        path = root / f"{validate_run_id(spec.run_id)}-{model.validate_slug(spec.step, label='step')}.env"
    except (OSError, ValueError) as exc:
        raise AdaptError("registry-failed") from exc
    try:
        before = _stat_fingerprint(path)
    except AdaptError:
        return RegistrySnapshot(path=path, entry=None, fingerprint=None, invalid=True)
    if before is None:
        return RegistrySnapshot(path=path, entry=None, fingerprint=None)
    try:
        entry = registry.read_entry(path)
        after = _stat_fingerprint(path)
    except AdaptError:
        return RegistrySnapshot(path=path, entry=None, fingerprint=None, invalid=True)
    except (OSError, ValueError) as exc:
        raise AdaptError("registry-failed") from exc
    if entry is None or before != after:
        return RegistrySnapshot(path=path, entry=None, fingerprint=after, invalid=True)
    return RegistrySnapshot(path=path, entry=entry, fingerprint=after)


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def _validate_entry(*, spec: model.JobSpec, entry: model.RegistryEntry) -> None:
    expected_result = model.result_env_path(tmpdir=spec.tmpdir, step=spec.step)
    expected_clone = Path.cwd().resolve()
    matches = (
        entry.step == spec.step,
        entry.run_id == spec.run_id,
        _same_path(entry.tmpdir, spec.tmpdir),
        _same_path(entry.clone_path, expected_clone),
        _same_path(entry.result_env, expected_result),
    )
    if not all(matches):
        raise AdaptError("registry-identity-mismatch")
    if entry.start_epoch <= 0 or entry.budget_s <= 0:
        raise AdaptError("registry-invalid")
    identities = (entry.daemon, entry.child)
    if not all(
        identity.pid > 0
        and identity.pgid > 0
        and bool(identity.start_time)
        and bool(identity.command_signature)
        for identity in identities
    ):
        raise AdaptError("registry-invalid")


def _process_state(verdict: model.LivenessVerdict) -> ProcessState:
    if verdict.live:
        return ProcessState(live=True, proven_dead=False)
    return ProcessState(
        live=False,
        proven_dead=verdict.reason in _DEAD_IDENTITY_REASONS,
    )


def _result_or_none(*, spec: model.JobSpec) -> bool:
    result = _read_completed_result(spec=spec)
    if result is None:
        return False
    _emit_done(result)
    return True


def _verify_same_snapshot(*, spec: model.JobSpec, previous: RegistrySnapshot) -> RegistrySnapshot:
    current = _snapshot_registry(spec=spec)
    if current.invalid or current.fingerprint != previous.fingerprint or current.entry != previous.entry:
        if _result_or_none(spec=spec):
            raise AdaptError("result-emitted")
        raise AdaptError("registry-replaced")
    return current


def _clear_expired(*, spec: model.JobSpec, snapshot: RegistrySnapshot) -> None:
    if _result_or_none(spec=spec):
        raise AdaptError("result-emitted")
    current = _verify_same_snapshot(spec=spec, previous=snapshot)
    if _result_or_none(spec=spec):
        raise AdaptError("result-emitted")
    current = _verify_same_snapshot(spec=spec, previous=current)
    registry.unlink_entry(current.path)
    if current.path.exists() or current.path.is_symlink():
        raise AdaptError("registry-clear-failed")


def _merge_env_path(*, spec: model.JobSpec) -> Path:
    root = model.bgjob_dir(spec.tmpdir)
    return root / f"{model.validate_slug(spec.step, label='step')}.merge.env"


def _prepare_launch_spec(spec: model.JobSpec) -> model.JobSpec:
    try:
        root = model.bgjob_dir(spec.tmpdir)
        root.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as exc:
        raise AdaptError("unsafe-path") from exc
    if root.is_symlink() or not root.is_dir():
        raise AdaptError("unsafe-path")
    try:
        merge_env = _merge_env_path(spec=spec)
    except (OSError, ValueError) as exc:
        raise AdaptError("unsafe-path") from exc
    if merge_env.is_symlink() or (merge_env.exists() and not merge_env.is_file()):
        raise AdaptError("unsafe-path")
    try:
        larch_io.atomic_write(path=merge_env, text="", nofollow=True, mode=0o600)
    except (OSError, ValueError) as exc:
        raise AdaptError("unsafe-path") from exc
    command = (*spec.command, "--bgjob-child", "--merge-result-env", str(merge_env))
    return replace(spec, command=command, merge_result_env=merge_env)


def _plugin_root_from_file(*, path: Path, key: str) -> str:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise AdaptError("plugin-root-invalid")
    if not path.is_file():
        return ""
    try:
        rows = larch_io.read_kvs(
            path,
            first_wins=True,
            reject_cr=True,
            reject_symlink=True,
            on_error_default=False,
        )
        return rows.get(key, "")
    except (OSError, UnicodeError, ValueError) as exc:
        raise AdaptError("plugin-root-invalid") from exc


def _rehydrate_plugin_root(tmpdir: Path) -> Path:
    raw_root = os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, "")
    if not raw_root:
        raw_root = _plugin_root_from_file(
            path=tmpdir / "plugin-root.env",
            key=config.ENV_CLAUDE_PLUGIN_ROOT,
        )
    if not raw_root:
        raw_root = _plugin_root_from_file(
            path=tmpdir / "session-env.sh",
            key="LARCH_CLAUDE_PLUGIN_ROOT",
        )
    if not raw_root or raw_root == "${CLAUDE_PLUGIN_ROOT}" or "\n" in raw_root or "\r" in raw_root:
        raise AdaptError("plugin-root-missing")
    root = Path(raw_root).expanduser()
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise AdaptError("plugin-root-invalid")
    resolved = root.resolve()
    if not (resolved / "python" / "cli.py").is_file():
        raise AdaptError("plugin-root-invalid")
    os.environ[config.ENV_CLAUDE_PLUGIN_ROOT] = str(resolved)
    return resolved


def _start_fresh(spec: model.JobSpec) -> int:
    _ = _rehydrate_plugin_root(spec.tmpdir)
    if _result_or_none(spec=spec):
        return 0
    final_registry = _snapshot_registry(spec=spec)
    if final_registry.invalid or final_registry.entry is not None:
        raise AdaptError("registry-replaced")
    if _result_or_none(spec=spec):
        raise AdaptError("result-emitted")
    launch_spec = _prepare_launch_spec(spec)
    if _result_or_none(spec=spec):
        raise AdaptError("result-emitted")
    final_registry = _snapshot_registry(spec=spec)
    if final_registry.invalid or final_registry.entry is not None:
        raise AdaptError("registry-replaced")
    if _result_or_none(spec=spec):
        raise AdaptError("result-emitted")
    try:
        rc = daemon.start_daemon(launch_spec)
    except (OSError, RuntimeError, ValueError) as exc:
        raise AdaptError("daemon-start-exception") from exc
    if rc != 0:
        raise AdaptError("daemon-start-failed")
    return 0


def _handle_expired(
    *,
    spec: model.JobSpec,
    snapshot: RegistrySnapshot,
    daemon_state: ProcessState,
    child_state: ProcessState,
) -> int:
    if daemon_state.live:
        raise AdaptError("expired-live")
    if child_state.live:
        raise AdaptError("expired-live")
    if not daemon_state.proven_dead:
        raise AdaptError("registry-identity-unverifiable")
    if not child_state.proven_dead:
        raise AdaptError("registry-identity-unverifiable")
    _clear_expired(spec=spec, snapshot=snapshot)
    if _result_or_none(spec=spec):
        return 0
    return _start_fresh(spec)


def _handle_active(
    *,
    spec: model.JobSpec,
    snapshot: RegistrySnapshot,
    entry: model.RegistryEntry,
    daemon_state: ProcessState,
    child_state: ProcessState,
) -> int:
    # The daemon owns child monitoring and final publication. Without a live,
    # identity-validated daemon, re-attachment cannot preserve the wait contract.
    if not daemon_state.live:
        if child_state.live:
            raise AdaptError("registry-ownership-lost")
        if not daemon_state.proven_dead:
            raise AdaptError("registry-identity-unverifiable")
        if not child_state.proven_dead:
            raise AdaptError("registry-identity-unverifiable")
        raise AdaptError("registry-dead")
    if _result_or_none(spec=spec):
        return 0
    _ = _verify_same_snapshot(spec=spec, previous=snapshot)
    _emit_started(step=spec.step, pgid=entry.child.pgid)
    return 0


def _decide_locked(spec: model.JobSpec) -> int:
    if _result_or_none(spec=spec):
        return 0
    snapshot = _snapshot_registry(spec=spec)
    if snapshot.invalid:
        raise AdaptError("registry-invalid")
    entry = snapshot.entry
    if entry is None:
        if _result_or_none(spec=spec):
            raise AdaptError("result-emitted")
        return _start_fresh(spec)
    _validate_entry(spec=spec, entry=entry)
    daemon_state = _process_state(registry.daemon_liveness(entry))
    child_state = _process_state(registry.child_liveness(entry))
    if registry.entry_expired(entry):
        return _handle_expired(
            spec=spec,
            snapshot=snapshot,
            daemon_state=daemon_state,
            child_state=child_state,
        )
    return _handle_active(
        spec=spec,
        snapshot=snapshot,
        entry=entry,
        daemon_state=daemon_state,
        child_state=child_state,
    )


def start_or_reattach(spec: model.JobSpec) -> int:
    """Start a step daemon or emit the matching existing job/result contract."""
    try:
        with _decision_lock(run_id=spec.run_id, step=spec.step):
            return _decide_locked(spec)
    except AdaptError as exc:
        if exc.token == "result-emitted":
            return 0
        raise
