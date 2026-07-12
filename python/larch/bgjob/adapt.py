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

_DEAD_IDENTITY_REASONS = frozenset({"missing-pid"})
_IDENTITY_MISMATCH_REASONS = frozenset(
    {"pgid-mismatch", "start-time-mismatch", "command-mismatch", "expected-command-mismatch"}
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
    identity_mismatch: bool


@dataclass(frozen=True)
class AdaptOptions:
    """Workflow-neutral controls applied under the adapter decision lock."""

    clear_on_fresh: Path | None = None
    replace_completed_result: bool = False


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


def _lock_name(*, run_id: str, step: str) -> str:
    run_slug = validate_run_id(run_id)
    step_slug = model.validate_slug(step, label="step")
    return f"{run_slug}-{step_slug}.lock"


def _directory_open_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _lock_open_flags() -> int:
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _open_pinned_lock(*, run_id: str, step: str) -> tuple[int, int]:
    root = model.registry_root()
    name = _lock_name(run_id=run_id, step=step)
    root_fd = os.open(root, _directory_open_flags())
    fd = -1
    try:
        opened_root = os.fstat(root_fd)
        current_root = root.stat(follow_symlinks=False)
        if (opened_root.st_dev, opened_root.st_ino) != (current_root.st_dev, current_root.st_ino):
            raise AdaptError("lock-failed")
        fd = os.open(name, _lock_open_flags(), 0o600, dir_fd=root_fd)
        opened_lock = os.fstat(fd)
        path_lock = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISREG(opened_lock.st_mode):
            raise AdaptError("unsafe-path")
        if (opened_lock.st_dev, opened_lock.st_ino) != (path_lock.st_dev, path_lock.st_ino):
            raise AdaptError("lock-failed")
        os.fchmod(fd, 0o600)
    except Exception:
        with contextlib.suppress(OSError):
            os.close(fd)
        with contextlib.suppress(OSError):
            os.close(root_fd)
        raise
    return root_fd, fd


@contextlib.contextmanager
def _decision_lock(*, run_id: str, step: str) -> Generator[None, None, None]:
    root_fd = -1
    fd = -1
    try:
        root_fd, fd = _open_pinned_lock(run_id=run_id, step=step)
        fcntl.flock(fd, fcntl.LOCK_EX)
        _FORK_CLOSE_FDS.add(fd)
        yield
    except (OSError, ValueError) as exc:
        raise AdaptError("lock-failed") from exc
    finally:
        _FORK_CLOSE_FDS.discard(fd)
        if fd >= 0:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
            with contextlib.suppress(OSError):
                os.close(fd)
        if root_fd >= 0:
            with contextlib.suppress(OSError):
                os.close(root_fd)


def _read_completed_result(*, spec: model.JobSpec) -> model.ResultEnvRows | None:
    try:
        root = model.bgjob_dir(spec.tmpdir)
        step = model.validate_slug(spec.step, label="step")
        path = root / f"{step}{config.BGJOB_RESULT_ENV_SUFFIX}"
    except (OSError, ValueError) as exc:
        raise AdaptError("unsafe-path") from exc
    try:
        present = larch_io.trusted_file_present(path, root=root)
    except OSError as exc:
        raise AdaptError("unsafe-path") from exc
    if not present:
        return None
    try:
        text = larch_io.read_trusted_text(
            path,
            root=root,
            errors="strict",
            reject_cr=True,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise AdaptError("unsafe-path") from exc
    return _parse_completed_rows(text=text, step=spec.step) if text else None


def _parse_completed_rows(*, text: str, step: str) -> model.ResultEnvRows | None:
    rows: list[tuple[str, str]] = []
    valid = True
    for line in text.splitlines():
        if not line:
            continue
        if "=" not in line:
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
        return ProcessState(live=True, proven_dead=False, identity_mismatch=False)
    return ProcessState(
        live=False,
        proven_dead=verdict.reason in _DEAD_IDENTITY_REASONS,
        identity_mismatch=verdict.reason in _IDENTITY_MISMATCH_REASONS,
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


def _clear_verified_dead_registry(*, spec: model.JobSpec, snapshot: RegistrySnapshot) -> None:
    """Remove the exact dead row selected for an explicit replacement."""
    current = _verify_same_snapshot(spec=spec, previous=snapshot)
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
    try:
        larch_io.trusted_atomic_write(path=merge_env, text="", root=root, mode=0o600)
    except (OSError, ValueError) as exc:
        raise AdaptError("unsafe-path") from exc
    command = (*spec.command, "--bgjob-child", "--merge-result-env", str(merge_env))
    return replace(spec, command=command, merge_result_env=merge_env)


def _validated_clear_path(*, spec: model.JobSpec, candidate: Path) -> Path:
    try:
        path = model.ensure_under(candidate, spec.tmpdir, label="clear-on-fresh")
    except (OSError, ValueError) as exc:
        raise AdaptError("unsafe-path") from exc
    if candidate.is_symlink() or path.is_symlink():
        raise AdaptError("unsafe-path")
    if path.exists() and not path.is_file():
        raise AdaptError("unsafe-path")
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise AdaptError("unsafe-path")
    return path


def _unlink_regular_under(*, path: Path, root: Path, failure_reason: str) -> None:
    try:
        parent = larch_io.validate_trusted_directory(path.parent, root=root)
        parent_fd = os.open(parent, _directory_open_flags())
    except (OSError, ValueError) as exc:
        raise AdaptError("unsafe-path") from exc
    try:
        opened_parent = os.fstat(parent_fd)
        current_parent = parent.stat(follow_symlinks=False)
        if (opened_parent.st_dev, opened_parent.st_ino) != (
            current_parent.st_dev,
            current_parent.st_ino,
        ):
            raise AdaptError("unsafe-path")
        try:
            current = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        if not stat.S_ISREG(current.st_mode):
            raise AdaptError("unsafe-path")
        os.unlink(path.name, dir_fd=parent_fd)
        try:
            _ = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise AdaptError(failure_reason)
    except OSError as exc:
        raise AdaptError(failure_reason) from exc
    finally:
        os.close(parent_fd)


def _clear_before_fresh(*, spec: model.JobSpec, candidate: Path | None) -> Path | None:
    if candidate is None:
        return None
    path = _validated_clear_path(spec=spec, candidate=candidate)
    try:
        existed = larch_io.trusted_file_present(path, root=spec.tmpdir)
    except OSError as exc:
        raise AdaptError("unsafe-path") from exc
    _unlink_regular_under(
        path=path,
        root=spec.tmpdir,
        failure_reason="clear-on-fresh-failed",
    )
    return path if existed else None


def _restore_cleared_path(*, spec: model.JobSpec, path: Path | None) -> None:
    """Restore an empty completion sentinel when daemon startup never succeeds."""
    if path is None:
        return
    try:
        if larch_io.trusted_file_present(path, root=spec.tmpdir):
            return
        larch_io.trusted_atomic_write(path=path, text="", root=spec.tmpdir, mode=0o600)
    except (OSError, ValueError) as exc:
        raise AdaptError("clear-on-fresh-restore-failed") from exc


def _invalidate_completed_result(*, spec: model.JobSpec) -> None:
    try:
        root = model.bgjob_dir(spec.tmpdir)
        result = model.result_env_path(tmpdir=spec.tmpdir, step=spec.step)
        if not larch_io.trusted_file_present(result, root=root):
            return
        _unlink_regular_under(
            path=result,
            root=spec.tmpdir,
            failure_reason="result-clear-failed",
        )
    except (OSError, ValueError) as exc:
        raise AdaptError("unsafe-path") from exc


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


def _start_fresh(spec: model.JobSpec, *, options: AdaptOptions) -> int:
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
    cleared_path = _clear_before_fresh(spec=spec, candidate=options.clear_on_fresh)
    try:
        rc = daemon.start_daemon(launch_spec)
    except (OSError, RuntimeError, ValueError) as exc:
        _restore_cleared_path(spec=spec, path=cleared_path)
        raise AdaptError("daemon-start-exception") from exc
    if rc != 0:
        _restore_cleared_path(spec=spec, path=cleared_path)
        raise AdaptError("daemon-start-failed")
    return 0


def _handle_expired(
    *,
    spec: model.JobSpec,
    snapshot: RegistrySnapshot,
    daemon_state: ProcessState,
    child_state: ProcessState,
    options: AdaptOptions,
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
    return _start_fresh(spec, options=options)


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
    if not child_state.live and child_state.identity_mismatch:
        raise AdaptError("registry-identity-unverifiable")
    if _result_or_none(spec=spec):
        return 0
    _ = _verify_same_snapshot(spec=spec, previous=snapshot)
    _emit_started(step=spec.step, pgid=entry.child.pgid)
    return 0


def _replacement_registry_check(*, spec: model.JobSpec, snapshot: RegistrySnapshot) -> None:
    if snapshot.invalid:
        raise AdaptError("registry-invalid")
    entry = snapshot.entry
    if entry is None:
        return
    _validate_entry(spec=spec, entry=entry)
    daemon_state = _process_state(registry.daemon_liveness(entry))
    child_state = _process_state(registry.child_liveness(entry))
    if daemon_state.live or child_state.live:
        raise AdaptError("replace-active")
    if not daemon_state.proven_dead or not child_state.proven_dead:
        raise AdaptError("registry-identity-unverifiable")
    _clear_verified_dead_registry(spec=spec, snapshot=snapshot)


def _decide_locked(spec: model.JobSpec, *, options: AdaptOptions) -> int:
    completed = _read_completed_result(spec=spec)
    if completed is not None and not options.replace_completed_result:
        _emit_done(completed)
        return 0
    snapshot = _snapshot_registry(spec=spec)
    if options.replace_completed_result:
        _replacement_registry_check(spec=spec, snapshot=snapshot)
    if completed is not None:
        _invalidate_completed_result(spec=spec)
        snapshot = _snapshot_registry(spec=spec)
    if snapshot.invalid:
        raise AdaptError("registry-invalid")
    entry = snapshot.entry
    if entry is None:
        if _result_or_none(spec=spec):
            raise AdaptError("result-emitted")
        return _start_fresh(spec, options=options)
    _validate_entry(spec=spec, entry=entry)
    daemon_state = _process_state(registry.daemon_liveness(entry))
    child_state = _process_state(registry.child_liveness(entry))
    if registry.entry_expired(entry):
        return _handle_expired(
            spec=spec,
            snapshot=snapshot,
            daemon_state=daemon_state,
            child_state=child_state,
            options=options,
        )
    return _handle_active(
        spec=spec,
        snapshot=snapshot,
        entry=entry,
        daemon_state=daemon_state,
        child_state=child_state,
    )


def start_or_reattach(spec: model.JobSpec, *, options: AdaptOptions | None = None) -> int:
    """Start a step daemon or emit the matching existing job/result contract."""
    try:
        with _decision_lock(run_id=spec.run_id, step=spec.step):
            return _decide_locked(spec, options=options or AdaptOptions())
    except AdaptError as exc:
        if exc.token == "result-emitted":
            return 0
        raise
