# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportPrivateUsage=false, reportUnusedFunction=false
"""External agent runner and shared launcher helpers."""

from __future__ import annotations

import contextlib
import json
import os
import platform
import re
import shutil
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from threading import Timer

from larch.core import config
from larch.core.ctx import Ctx
from larch.core import logging_util
from larch.core import proc
from larch.core import redact
from larch.core.proc import CommandResult

from larch.agents._types import (
    _QUOTA_RE,
    _AUTH_RE,
    _TOML_CLOSED_STRING_DELIMITER_COUNT,
    _PY_CLI,
    LauncherPaths,
    RunExternalAgentResult,
    RunExternalAgentFilePrep,
    TailReadResult,
    StartupLockState,
    _err,
    _emit_kv,
    _read_text,
    _write,
    _append,
    _parse_positive_or_zero_int,
    _is_positive_int,
    _validate_meta_path,
    _sanitize_tool_label,
    _json_array,
)
from larch.agents._launch_failure import (
    classify_launch_failure,
)
from larch.agents._failure_diag import (
    select_failed_agent_stderr_source,
    _write_stderr_tail,
    _tail_redacted,
    _compose_failure_diag,
    _truncate_utf8_bytes,
    _vendor_failure_diag_cap,
    resolve_failure_diagnostic_source,
    parse_codex_usage_file,
    _num,
    _first_not_none,
)

def _positive_int_env(*, name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    parsed = _parse_positive_or_zero_int(raw)
    return parsed if parsed is not None and parsed > 0 else default


def _nonnegative_float_env(*, name: str, default: float) -> float:
    raw = os.environ.get(name, str(default))
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value >= 0 else default

def _cursor_ci_stall_sidecar_dir(output_file: Path) -> Path | None:
    for parent in [output_file.parent, *output_file.parents]:
        if re.fullmatch(r"round-[0-9]+", parent.name):
            return parent
    impl = os.environ.get("IMPLEMENT_TMPDIR", "")
    if impl:
        candidate = Path(impl) / "round-1"
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            return None
    return None


def _git_status_excerpt(root: Path) -> str:
    result = proc.run(["git", "-C", str(root), "status", "--porcelain"], timeout=3, check=False)
    text = result.stdout if result.returncode == 0 else ""
    return redact.redact_tmpdir_paths(redact.redact_secrets_only(text[:32000]))


def _tree_latest_mtime(root: Path) -> float:
    latest = 0.0
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            if ".git" in dirnames:
                dirnames.remove(".git")
            for name in filenames:
                try:
                    latest = max(latest, (Path(dirpath) / name).stat().st_mtime)
                except OSError:
                    continue
    except OSError:
        return latest
    return latest


def _stall_channel_progress(*, channel: str, output_file: Path, last_marker: float) -> tuple[bool, float]:
    if channel == "stdout":
        size = float(output_file.stat().st_size) if output_file.is_file() else 0.0
        return size != last_marker, size
    if channel.startswith("tree:"):
        marker = _tree_latest_mtime(Path(channel.split(":", 1)[1]))
        return marker != last_marker, marker
    if channel.startswith("file:"):
        path = Path(channel.split(":", 1)[1])
        if path.is_file():
            stat = path.stat()
            marker = float(stat.st_size) + stat.st_mtime
        else:
            marker = 0.0
        return marker != last_marker, marker
    return False, last_marker


def _emit_elapsed_minute_if_needed(*, tool: str, elapsed: float, last_progress_minute: int) -> int:
    elapsed_minute = int(elapsed // 60)
    if elapsed_minute >= 1 and elapsed_minute != last_progress_minute:
        _err(f"⏳ {tool} agent: still running ({elapsed_minute}m elapsed)")
        return elapsed_minute
    return last_progress_minute


def _terminate_child_processes_first(pid: int) -> None:
    try:
        children = proc.run(["pgrep", "-P", str(pid)], check=False)
    except OSError:
        children = CommandResult(("pgrep", "-P", str(pid)), 1, "", "", 0.0)
    child_pids = [line.strip() for line in children.stdout.splitlines() if line.strip().isdigit()]
    for child_pid in child_pids:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(int(child_pid), 15)
    with contextlib.suppress(OSError, ProcessLookupError):
        os.kill(pid, 15)
    time.sleep(2)
    for child_pid in child_pids:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(int(child_pid), 9)
    with contextlib.suppress(OSError, ProcessLookupError):
        os.kill(pid, 9)


def _write_cursor_ci_stall_artifacts(
    *,
    output_file: Path,
    diag: Path,
    channel: str,
    pid: int,
    elapsed: int,
) -> None:
    try:
        ps = proc.run(["ps", "-p", str(pid), "-o", "pid,pcpu,etime,stat"], check=False).stdout
    except OSError:
        ps = ""
    ps_text = ps or "(target not found)\n"
    _append(
        path=diag,
        text=f"Stall detected: channel={channel} time_since_last_progress={elapsed}s\n"
        "--- stall ps snapshot (target pid="
        f"{pid}) ---\n{ps_text}"
    )
    root = Path.cwd()
    if channel.startswith("tree:"):
        root = Path(channel.split(":", 1)[1])
    payload = {
        "tool": "cursor",
        "channel": channel,
        "pid": pid,
        "time_since_last_progress": elapsed,
        "capture_phase": "pre_sigterm",
        "git_state": {"status_porcelain": _git_status_excerpt(root)},
        "last_transcript_lines": (
            _tail_redacted(output_file, lines=50, cap=8000)
            + "\n"
            + _tail_redacted(diag, lines=50, cap=8000)
        ).splitlines()[-110:],
    }
    text = json.dumps(payload, ensure_ascii=False) + "\n"
    _write(path=output_file.with_suffix(output_file.suffix + ".stall.json"), text=text)
    sidecar_dir = _cursor_ci_stall_sidecar_dir(output_file)
    if sidecar_dir is not None:
        name = f"cursor-ci-stall-{int(time.time())}-{pid}.json"
        with contextlib.suppress(OSError):
            _write(path=sidecar_dir / name, text=text)


def _prepare_run_external_agent_files(prep: RunExternalAgentFilePrep) -> tuple[Path, LauncherPaths, Path, Path]:
    output_path = Path(prep.output)
    paths = LauncherPaths.from_output(output_path)
    stale_paths = {
        paths.output,
        paths.done,
        paths.inner_done,
        paths.meta,
        paths.diag,
        paths.stderr_tail,
        paths.failure_diag,
    }
    if prep.stdout_path is not None:
        stale_paths.add(Path(prep.stdout_path))
    if prep.stderr_path is not None:
        stale_paths.add(Path(prep.stderr_path))
    for stale in stale_paths:
        with contextlib.suppress(FileNotFoundError):
            stale.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    meta_lines = [
        f"TOOL={_sanitize_tool_label(prep.tool)}",
        f"TIMEOUT={prep.timeout_seconds}",
        f"CAPTURE_STDOUT={str(prep.capture_stdout).lower()}",
        f"CAPTURE_STDOUT_ONLY={str(prep.capture_stdout_only).lower()}",
        f"OUTPUT_FILE={prep.output}",
    ]
    if prep.stderr_sink:
        meta_lines.append(f"STDERR_SINK={prep.stderr_sink}")
    meta_lines.append(f"CMD_JSON={_json_array(prep.cmd)}")
    _write(path=paths.meta, text="\n".join(meta_lines) + "\n")
    return output_path, paths, paths.diag, paths.sentinel_done(prep.sentinel_suffix)


def run_external_agent(
    *,
    tool: str,
    output: str,
    timeout_seconds: int,
    cmd: Sequence[str],
    env: Mapping[str, str] | None = None,
    capture_stdout: bool = False,
    capture_stdout_only: bool = False,
    stderr_sink: str = "",
    cwd: str | None = None,
    stdout_path: str | Path | None = None,
    stderr_path: str | Path | None = None,
    stall_channel: str = "",
    stall_threshold_seconds: int = 0,
    ctx: Ctx | None = None,
    inner_sentinel_suffix: str | None = None,
    poll_interval: float | None = None,
) -> RunExternalAgentResult:
    suffix = inner_sentinel_suffix
    if suffix is None:
        suffix = ctx.str_value(key=config.ENV_RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX, default=".done") if ctx is not None else os.environ.get(config.ENV_RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX, ".done")
    output_path, paths, diag, done = _prepare_run_external_agent_files(
        RunExternalAgentFilePrep(
            tool=tool,
            output=output,
            timeout_seconds=timeout_seconds,
            capture_stdout=capture_stdout,
            capture_stdout_only=capture_stdout_only,
            stderr_sink=stderr_sink,
            cmd=cmd,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            sentinel_suffix=suffix,
        )
    )

    exit_code = 99
    proc_obj: subprocess.Popen[bytes] | None = None
    _old_sigterm: object = None
    try:
        stdin = subprocess.DEVNULL if tool == "codex" else None
        stdout_target = None
        stderr_target = None
        handles = []
        try:
            if capture_stdout:
                stdout_target = output_path.open("wb")
                handles.append(stdout_target)
                stderr_target = subprocess.STDOUT
            elif capture_stdout_only:
                stdout_target = output_path.open("wb")
                handles.append(stdout_target)
                stderr_target = diag.open("wb")
                handles.append(stderr_target)
            else:
                if stdout_path is not None:
                    stdout_target = Path(stdout_path).open("wb")  # noqa: SIM115 - child owns descriptor after Popen starts  # pylint: disable=consider-using-with
                    handles.append(stdout_target)
                elif os.environ.get(config.ENV_LARCH_QUIET_ACTIVE, "").lower() in {"1", "true", "yes", "on"}:
                    with contextlib.suppress(OSError):
                        stdout_target = os.fdopen(os.dup(3), "wb", closefd=True)
                        handles.append(stdout_target)
                if stderr_path is not None:
                    stderr_target = Path(stderr_path).open("wb")  # noqa: SIM115 - child owns descriptor after Popen starts  # pylint: disable=consider-using-with
                    handles.append(stderr_target)
                elif os.environ.get(config.ENV_LARCH_QUIET_ACTIVE, "").lower() in {"1", "true", "yes", "on"}:
                    with contextlib.suppress(OSError):
                        stderr_target = os.fdopen(os.dup(4), "wb", closefd=True)
                        handles.append(stderr_target)
            proc_obj = subprocess.Popen(  # pylint: disable=consider-using-with
                list(cmd),
                cwd=cwd,
                env=env,
                stdin=stdin,
                stdout=stdout_target,
                stderr=stderr_target,
            )
        except FileNotFoundError as exc:
            _write(path=output_path, text="")
            _append(path=diag, text=f"Failed to launch child: {exc}\n")
            exit_code = 127
            return RunExternalAgentResult(exit_code, output_path)
        except PermissionError as exc:
            _write(path=output_path, text="")
            _append(path=diag, text=f"Failed to launch child: {exc}\n")
            exit_code = 126
            return RunExternalAgentResult(exit_code, output_path)
        finally:
            for handle in handles:
                handle.close()

        def _on_sigterm(signum: int, _frame: object) -> None:  # lint-keyword-only: ok signal handler callback
            _terminate_child_processes_first(proc_obj.pid)
            raise SystemExit(128 + signum)

        _old_sigterm = signal.signal(signal.SIGTERM, _on_sigterm)
        if poll_interval is None:
            poll_raw = ctx.str_value(key=config.ENV_RUN_EXTERNAL_AGENT_POLL_INTERVAL, default="10") if ctx is not None else os.environ.get(config.ENV_RUN_EXTERNAL_AGENT_POLL_INTERVAL, "10")
            poll_interval = float(poll_raw or "10")
        start = time.monotonic()
        last_progress_time = start
        _, stall_marker = _stall_channel_progress(channel=stall_channel, output_file=output_path, last_marker=-1.0) if stall_channel else (False, 0.0)
        last_progress_minute = 0
        policy_watch = _codex_policy_watch_path(tool=tool, stdout_path=stdout_path)
        policy_watch_offset = 0
        policy_watch_tail = ""
        while True:
            try:
                exit_code = proc_obj.wait(timeout=poll_interval)
                break
            except subprocess.TimeoutExpired:
                elapsed = time.monotonic() - start
                policy_rejected, policy_watch_offset, policy_watch_tail = _codex_policy_rejection_fast_fail(
                    watch=policy_watch,
                    offset=policy_watch_offset,
                    tail=policy_watch_tail,
                    diag=diag,
                    proc_obj=proc_obj,
                )
                if policy_rejected:
                    exit_code = 1
                    break
                if stall_channel and stall_threshold_seconds > 0:
                    progressed, new_marker = _stall_channel_progress(channel=stall_channel, output_file=output_path, last_marker=stall_marker)
                    if progressed:
                        stall_marker = new_marker
                        last_progress_time = time.monotonic()
                    stall_elapsed = int(time.monotonic() - last_progress_time)
                    if stall_elapsed >= stall_threshold_seconds:
                        _write_cursor_ci_stall_artifacts(
                            output_file=output_path,
                            diag=diag,
                            channel=stall_channel,
                            pid=proc_obj.pid,
                            elapsed=stall_elapsed,
                        )
                        _err(f"⚠ {tool} agent: STALLED after {stall_elapsed}s without progress, killing")
                        _terminate_child_processes_first(proc_obj.pid)
                        with contextlib.suppress(Exception):
                            proc_obj.wait(timeout=1)
                        exit_code = config.EXIT_TIMEOUT
                        break
                if elapsed >= timeout_seconds:
                    _err(f"⚠ {tool} agent: TIMED OUT after {timeout_seconds // 60} minutes, killing")
                    proc_obj.terminate()
                    try:
                        proc_obj.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc_obj.kill()
                        proc_obj.wait()
                    exit_code = config.EXIT_TIMEOUT
                    size = output_path.stat().st_size if output_path.is_file() else 0
                    _append(path=diag, text=f"Timed out after {int(elapsed)}s (limit: {timeout_seconds}s). Process was killed after exceeding the timeout. Output size: {size} bytes.\n")
                    break
                last_progress_minute = _emit_elapsed_minute_if_needed(
                    tool=tool,
                    elapsed=elapsed,
                    last_progress_minute=last_progress_minute,
                )

        if (
            exit_code != 0
            and policy_watch is not None
            and not _policy_rejection_marker_present(output_path)
        ):
            policy_detected, policy_watch_offset, policy_watch_tail = _codex_policy_rejection_fast_fail(
                watch=policy_watch,
                offset=policy_watch_offset,
                tail=policy_watch_tail,
                diag=diag,
                proc_obj=proc_obj,
            )
            if policy_detected:
                exit_code = 1

        size = output_path.stat().st_size if output_path.is_file() else 0
        if exit_code != 0:
            _err(f"❌ {tool} agent: FAILED (exit code {exit_code}, output {size} bytes)")
            _append(path=diag, text=f"Failed with exit code {exit_code}. Output size: {size} bytes.\n")
            source = select_failed_agent_stderr_source(
                output_path,
                capture_stdout=capture_stdout,
                capture_stdout_only=capture_stdout_only,
                stderr_sink=stderr_sink,
            )
            if source:
                _write_stderr_tail(source=source, output=output_path)
        elif size == 0:
            _err(f"⚠ {tool} agent: completed but OUTPUT IS EMPTY (exit code 0)")
            _append(path=diag, text="Process exited successfully (code 0) but produced no output.\n")
        else:
            _err(f"✓ {tool} agent: completed (exit code 0, output {size} bytes)")
        return RunExternalAgentResult(exit_code, output_path)
    finally:
        if _old_sigterm is not None:
            with contextlib.suppress(OSError, ValueError):
                signal.signal(signal.SIGTERM, _old_sigterm)
        if proc_obj is not None and proc_obj.poll() is None:
            proc_obj.terminate()
            with contextlib.suppress(Exception):
                proc_obj.wait(timeout=5)
        if exit_code != 0:
            _compose_failure_diag(output_path, sink=stderr_sink)
        else:
            with contextlib.suppress(FileNotFoundError):
                paths.failure_diag.unlink()
        _write(path=done, text=f"{exit_code}\n")


def run_external_agent_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    args = argv if argv is not None else sys.argv[1:]
    tool = ""
    output = ""
    timeout_raw = ""
    stderr_sink = ""
    capture_stdout = False
    capture_stdout_only = False
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--":
            idx += 1
            break
        if arg == "--tool" and idx + 1 < len(args):
            tool = args[idx + 1]
            idx += 2
        elif arg == "--output" and idx + 1 < len(args):
            output = args[idx + 1]
            idx += 2
        elif arg == "--timeout" and idx + 1 < len(args):
            timeout_raw = args[idx + 1]
            idx += 2
        elif arg == "--stderr-sink" and idx + 1 < len(args):
            stderr_sink = args[idx + 1]
            idx += 2
        elif arg == "--capture-stdout":
            capture_stdout = True
            idx += 1
        elif arg == "--capture-stdout-only":
            capture_stdout_only = True
            idx += 1
        elif arg == "--help":
            _err("Usage: cli.py agent run-external-agent --tool NAME --output FILE --timeout SECS [--capture-stdout|--capture-stdout-only] [--stderr-sink PATH] -- CMD...")
            return 0
        else:
            _err(f"Unknown option: {arg}")
            return 1
    cmd = args[idx:]
    if not tool or not output or not timeout_raw:
        _err("ERROR: --tool, --output, and --timeout are required")
        return 1
    if capture_stdout and capture_stdout_only:
        _err("ERROR: --capture-stdout and --capture-stdout-only are mutually exclusive")
        return 1
    if not _validate_meta_path(label="--output", value=output):
        return 1
    if stderr_sink and not _validate_meta_path(label="--stderr-sink", value=stderr_sink):
        return 1
    if not _is_positive_int(timeout_raw):
        _err(f"ERROR: --timeout must be a positive integer, got '{timeout_raw}'")
        return 1
    ctx = Ctx.from_env()
    suffix = ctx.str_value(key=config.ENV_RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX, default="")
    if suffix and suffix != ".inner.done":
        _err(f"ERROR: invalid RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX value '{suffix}'; expected '.inner.done'")
        return 1
    poll = ctx.str_value(key=config.ENV_RUN_EXTERNAL_AGENT_POLL_INTERVAL, default="10") or "10"
    try:
        poll_interval = float(poll)
        if poll_interval <= 0:
            raise ValueError
    except ValueError:
        _err(f"ERROR: RUN_EXTERNAL_AGENT_POLL_INTERVAL must be a positive number, got '{poll}'")
        return 1
    if not cmd:
        _err("ERROR: no command specified after --")
        return 1
    result = run_external_agent(
        tool=tool,
        output=output,
        timeout_seconds=int(timeout_raw, 10),
        cmd=cmd,
        capture_stdout=capture_stdout,
        capture_stdout_only=capture_stdout_only,
        stderr_sink=stderr_sink,
        env=ctx.subprocess_env(),
        ctx=ctx,
        inner_sentinel_suffix=suffix or ".done",
        poll_interval=poll_interval,
    )
    return result.exit_code


def _positive_int_ctx(*, ctx: Ctx | None, name: str, default: int) -> int:
    if ctx is None:
        return _positive_int_env(name=name, default=default)
    parsed = _parse_positive_or_zero_int(ctx.str_value(key=name, default=str(default)))
    return parsed if parsed is not None and parsed > 0 else default


def external_startup_lock_acquire(*, tool: str, ctx: Ctx | None = None) -> StartupLockState:
    forced = ctx.str_value(key=config.ENV_LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME) if ctx is not None else os.environ.get(config.ENV_LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME)
    if (forced or platform.system()) != "Darwin" or tool not in {"codex", "cursor"}:
        return StartupLockState(None)
    user = (ctx.user if ctx is not None else os.environ.get(config.ENV_USER)) or "larch"
    lock_path = Path(f"/tmp/larch-external-startup-{user}.lock")  # noqa: S108 - Bash Darwin startup-lock path parity
    ttl = _positive_int_ctx(ctx=ctx, name=config.ENV_LARCH_EXTERNAL_STARTUP_LOCK_TTL, default=30)
    tries = _positive_int_ctx(ctx=ctx, name=config.ENV_LARCH_EXTERNAL_STARTUP_LOCK_TRIES, default=300)
    for _ in range(max(tries, 1)):
        try:
            lock_path.mkdir()
            return StartupLockState(lock_path)
        except FileExistsError:
            if ttl > 0:
                try:
                    age = time.time() - lock_path.stat().st_mtime
                    if age >= ttl:
                        lock_path.rmdir()
                        continue
                except OSError:
                    pass
            time.sleep(0.1)
    return StartupLockState(None)


def external_startup_lock_release_after(*, state: StartupLockState, delay: float | None = None) -> None:
    if state.lock_path is None:
        return
    release_delay = delay if delay is not None else _nonnegative_float_env(name="LARCH_EXTERNAL_STARTUP_LOCK_DELAY", default=0.5)

    def release() -> None:
        with contextlib.suppress(OSError):
            state.lock_path.rmdir()

    timer = Timer(release_delay, release)
    timer.daemon = False
    timer.start()


def external_auth_verdict(tool: str, *sidecars: str | Path) -> str:
    readable = False
    pattern = _AUTH_RE.get(tool)
    if pattern is None:
        return "unclassified"
    for sidecar in sidecars:
        text = _read_text(sidecar)
        if not text:
            continue
        readable = True
        if pattern.search(text):
            return "auth"
    return "non-auth" if readable else "unclassified"


def _emit_claude_subprocess_failure_fields(*, output: Path, launcher_exit: int) -> None:
    auth_paths = [
        output.with_suffix(output.suffix + ".stderr"),
        output.with_suffix(output.suffix + ".stderr-tail"),
        output.with_suffix(output.suffix + ".failure-diag"),
        output,
    ]
    sidecar = next((path for path in auth_paths if path.is_file() and path.stat().st_size > 0), auth_paths[0])
    failure = classify_launch_failure(
        launcher_exit=launcher_exit,
        sidecar=sidecar,
        auth_verdict=external_auth_verdict("claude", *auth_paths),
        binary_present=shutil.which("claude") is not None,
        tool="claude",
        output_file=output,
    )
    _emit_kv(key="LAUNCHER_FAILURE_CLASS", value=failure.failure_class)
    _emit_kv(key="LAUNCHER_FAILURE_REASON", value=failure.reason)


def _record_usage_from_events(*, events: Path, sidecar: Path, label: str, token_record: Path | None = None, model: str = "") -> None:
    try:
        totals = parse_codex_usage_file(events)
    except (FileNotFoundError, ValueError) as exc:
        _append(path=sidecar, text=f"agent parse-codex-usage: {exc}\n")
        return
    if token_record is not None:
        model_line = f"MODEL={model}\n" if model else ""
        _write(
            path=token_record,
            text=f"TOOL=codex\n{model_line}INPUT={totals.uncached_input_tokens}\nOUTPUT={totals.output_tokens}\nCACHE_READ={totals.cached_input_tokens}\nTOTAL={totals.total_tokens}\nRAW={label}\n"
        )
        return
    proc.run(
        [
            sys.executable,
            str(_PY_CLI),
            "token",
            "record-vendor",
            "codex",
            f"input={totals.uncached_input_tokens}",
            f"cache_read={totals.cached_input_tokens}",
            f"output={totals.output_tokens}",
            f"total={totals.total_tokens}",
            f"raw={label}",
        ],
    )


def _mirror_codex_quota_from_events(*, events: Path, sidecar: Path) -> None:
    text = _read_text(events)
    if text and _QUOTA_RE.search(text):
        _append(path=sidecar, text="codex-quota: usage limit / quota reported on the codex exec --json events stream\n")


_CODEX_POLICY_REJECTION_TAIL_BYTES = 32768
_CODEX_POLICY_REJECTION_EXCERPT_BYTES = 2048
_CODEX_EXEC_COMMAND_FAILED_RE = re.compile(r"\bexec_command\s+failed\b", re.IGNORECASE)
_CODEX_POLICY_BLOCKED_RE = re.compile(r"blocked by policy|Rejected\(", re.IGNORECASE)


def _should_strip_aggregated_output(exit_code: object, aggregated_output: object) -> bool:
    return exit_code == 0 or (exit_code is None and not aggregated_output)


def _strip_gated_aggregated_output(node: object) -> None:
    if isinstance(node, dict):
        if (
            "aggregated_output" in node
            and "exit_code" in node
            and _should_strip_aggregated_output(node["exit_code"], node["aggregated_output"])
        ):
            node.pop("aggregated_output", None)
        for value in node.values():
            _strip_gated_aggregated_output(value)
    elif isinstance(node, list):
        for item in node:
            _strip_gated_aggregated_output(item)


def _sanitize_codex_events_for_policy_scan(text: str) -> str:
    sanitized: list[str] = []
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        terminator = line[len(content):]
        if not content.strip():
            sanitized.append(line)
            continue
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            sanitized.append(line)
            continue
        _strip_gated_aggregated_output(parsed)
        sanitized.append(json.dumps(parsed, ensure_ascii=False) + terminator)
    return "".join(sanitized)


def _codex_policy_rejection_excerpt(text: str) -> str:
    bounded = text[-_CODEX_POLICY_REJECTION_TAIL_BYTES:]
    if not bounded:
        return ""
    scanned = _sanitize_codex_events_for_policy_scan(bounded)
    if _CODEX_EXEC_COMMAND_FAILED_RE.search(scanned) is None:
        return ""
    if _CODEX_POLICY_BLOCKED_RE.search(scanned) is None:
        return ""
    lines = [
        line
        for line in scanned.splitlines()
        if _CODEX_EXEC_COMMAND_FAILED_RE.search(line)
        or _CODEX_POLICY_BLOCKED_RE.search(line)
        or "CreateProcess" in line
    ]
    excerpt = "\n".join(lines[-8:]) or scanned[-_CODEX_POLICY_REJECTION_EXCERPT_BYTES:]
    redacted = redact.redact_secrets_only(redact.redact_tmpdir_paths(excerpt))
    return _truncate_utf8_bytes(text=redacted, cap=_CODEX_POLICY_REJECTION_EXCERPT_BYTES)


def _read_tail_update(*, path: Path, offset: int) -> TailReadResult:
    if not path.is_file():
        return TailReadResult(offset=offset, text="")
    try:
        size = path.stat().st_size
        start = 0 if size < offset else offset
        with path.open("rb") as handle:
            handle.seek(start)
            data = handle.read()
    except OSError:
        return TailReadResult(offset=offset, text="")
    return TailReadResult(offset=start + len(data), text=data.decode("utf-8", errors="replace"))


def _codex_policy_watch_path(*, tool: str, stdout_path: str | Path | None) -> Path | None:
    if tool != "codex" or stdout_path is None:
        return None
    return Path(stdout_path)


def _stop_policy_rejected_process(proc_obj: subprocess.Popen[bytes]) -> None:
    proc_obj.terminate()
    try:
        proc_obj.wait(timeout=1)
    except subprocess.TimeoutExpired:
        proc_obj.kill()
        proc_obj.wait()


def _codex_policy_rejection_fast_fail(
    *,
    watch: Path | None,
    offset: int,
    tail: str,
    diag: Path,
    proc_obj: subprocess.Popen[bytes],
) -> tuple[bool, int, str]:
    if watch is None:
        return False, offset, tail
    update = _read_tail_update(path=watch, offset=offset)
    if not update.text:
        return False, update.offset, tail
    new_tail = (tail + update.text)[-_CODEX_POLICY_REJECTION_TAIL_BYTES:]
    excerpt = _codex_policy_rejection_excerpt(new_tail)
    if not excerpt:
        return False, update.offset, new_tail
    _err("❌ codex agent: exec_command policy rejection detected, killing")
    _stop_policy_rejected_process(proc_obj)
    _append(
        path=diag,
        text=(
            "FAILURE_CLASS=policy-rejection\n"
            "POLICY_REJECTION=true\n"
            "Codex exec_command policy rejection detected in events stream.\n"
            "Matched excerpt:\n"
            f"{excerpt.rstrip()}\n"
        ),
    )
    return True, update.offset, new_tail


def _policy_rejection_marker_present(output: Path) -> bool:
    diag = output.with_suffix(output.suffix + ".diag")
    text = _read_text(diag)
    return "POLICY_REJECTION=true" in text or "FAILURE_CLASS=policy-rejection" in text


def _codex_env_key_enabled() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def _codex_auth_args() -> list[str]:
    if not _codex_env_key_enabled():
        return []
    return [
        "-c",
        'model_provider="openai-larch-env"',
        "-c",
        'model_providers.openai-larch-env.name="OpenAI API (larch env key)"',
        "-c",
        'model_providers.openai-larch-env.base_url="https://api.openai.com/v1"',
        "-c",
        'model_providers.openai-larch-env.env_key="OPENAI_API_KEY"',
        "-c",
        'model_providers.openai-larch-env.wire_api="responses"',
    ]


def _strip_codex_config(text: str, *, strip_instructions: bool = False) -> str:
    out: list[str] = []
    skip_block_delim = ""
    skip_provider = False
    for line in text.splitlines():
        stripped = line.strip()
        if skip_block_delim:
            if skip_block_delim in line:
                skip_block_delim = ""
            continue
        if skip_provider:
            if stripped.startswith("["):
                skip_provider = False
            else:
                continue
        if re.match(r"\[\[?\s*model_providers\.openai-larch-env\s*\]?\]", stripped):
            skip_provider = True
            continue
        if re.match(r"model_provider\s*=\s*['\"]?openai-larch-env", stripped):
            continue
        if re.match(r"env_key\s*=\s*['\"]?OPENAI_API_KEY", stripped):
            continue
        if re.match(r"([A-Za-z0-9_-]+\.)*(api_key|openai_api_key)\s*=", stripped):
            if "'''" in stripped and stripped.count("'''") < _TOML_CLOSED_STRING_DELIMITER_COUNT:
                skip_block_delim = "'''"
            elif '"""' in stripped and stripped.count('"""') < _TOML_CLOSED_STRING_DELIMITER_COUNT:
                skip_block_delim = '"""'
            continue
        if strip_instructions and re.match(r"instructions\s*=", stripped):
            if "'''" in stripped and stripped.count("'''") < _TOML_CLOSED_STRING_DELIMITER_COUNT:
                skip_block_delim = "'''"
            elif '"""' in stripped and stripped.count('"""') < _TOML_CLOSED_STRING_DELIMITER_COUNT:
                skip_block_delim = '"""'
            continue
        out.append(line)
    return "\n".join(out) + ("\n" if out else "")


def _prepare_codex_home(home_dir: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
    try:
        home_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return 1, f"codex auth setup failed: {exc}"
    user_config = Path.home() / ".codex" / "config.toml"
    try:
        config_text = user_config.read_text(encoding="utf-8", errors="replace") if user_config.is_file() else ""
    except OSError as exc:
        return 1, f"codex auth setup failed: {exc}"
    if trusted_instructions_file:
        trusted = Path(trusted_instructions_file)
        if not trusted.is_file():
            return 2, f"--trusted-instructions-file not found: {trusted_instructions_file}"
        if trusted.is_symlink():
            return 2, "--trusted-instructions-file must not be a symlink"
        body = trusted.read_text(encoding="utf-8", errors="replace")
        if "'''" in body:
            return 2, "trusted instructions file contains TOML triple-single-quote delimiter"
        config_text = f"instructions = '''\n{body}\n'''\n\n" + _strip_codex_config(config_text, strip_instructions=True)
    else:
        config_text = _strip_codex_config(config_text)
    if config_text:
        _write(path=home_dir / "config.toml", text=config_text)
    if not _codex_env_key_enabled():
        auth = Path.home() / ".codex" / "auth.json"
        if auth.is_file():
            try:
                (home_dir / "auth.json").symlink_to(auth.resolve())
            except OSError as exc:
                return 1, f"codex auth setup failed: {exc}"
    return 0, ""


def _ci_failure_source(output: Path) -> Path:
    return resolve_failure_diagnostic_source(output) or output.with_suffix(output.suffix + ".diag")


def _resolve_execution_issues_log() -> Path | None:
    if os.environ.get("LARCH_EXECUTION_ISSUES_LOG"):
        return Path(os.environ["LARCH_EXECUTION_ISSUES_LOG"])
    if os.environ.get("SESSION_ENV_PATH"):
        return Path(os.environ["SESSION_ENV_PATH"]).parent / "execution-issues.md"
    for name in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "REVIEW_TMPDIR"):
        if os.environ.get(name):
            return Path(os.environ[name]) / "execution-issues.md"
    return None


def _append_vendor_failure_diagnostics(source: Path, *, site: str, exit_code: int) -> None:
    tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not tmpdir:
        return
    root = Path(tmpdir)
    if not root.is_dir():
        return
    parts_dir = root / "vendor-failure-diagnostics.parts"
    try:
        parts_dir.mkdir(parents=True, exist_ok=True)
        cap = _vendor_failure_diag_cap()
        if source.is_file() and source.stat().st_size > 0:
            body = source.read_text(encoding="utf-8", errors="replace")
        else:
            body = f"no diagnostics captured (exit {exit_code})\n"
        text = f"===== {site} =====\nexit-code: {exit_code}\n{body.rstrip()}\n"
        redacted = redact.redact_secrets_only(redact.redact_tmpdir_paths(text))
        capped = _truncate_utf8_bytes(text=redacted, cap=cap)
        fd, _part = tempfile.mkstemp(prefix="part.", dir=str(parts_dir))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(capped)
    except OSError:
        return


def _append_ci_failure(output: Path, *, tool: str, launcher_exit: int, site: str, binary_present: bool = True) -> None:
    if launcher_exit == 0:
        return
    source = _ci_failure_source(output)
    log = _resolve_execution_issues_log()
    if log is not None:
        failure = classify_launch_failure(
            launcher_exit=launcher_exit,
            sidecar=source,
            auth_verdict=external_auth_verdict(tool, source, output),
            binary_present=binary_present,
            tool=tool,
            output_file=output,
        )
        proc.run(
            [
                sys.executable,
                str(_PY_CLI),
                "run-log",
                "append-failure",
                "--log",
                str(log),
                "--site",
                site,
                "--tool",
                f"{tool}-ci",
                "--exit-code",
                str(launcher_exit),
                "--category",
                "CI Issues",
                "--output-file",
                str(source),
                "--verdict",
                failure.reason or failure.failure_class,
                "--redact",
            ],
            check=False,
        )
    _append_vendor_failure_diagnostics(source, site=f"{site} {tool}-ci", exit_code=launcher_exit)


def _write_preflight_bundle(
    *,
    output: Path,
    timeout: str,
    launcher_exit: int,
    failure_reason: str,
    tool: str = "codex",
    binary_present: bool = True,
) -> None:
    _write(path=output, text="")
    _write(path=output.with_suffix(output.suffix + ".diag"), text=f"STATUS=FAILED\nFAILURE_REASON={failure_reason}\n")
    _write(
        path=output.with_suffix(output.suffix + ".meta"),
        text=f"TOOL={tool}\nTIMEOUT={timeout}\nCAPTURE_STDOUT=false\nOUTPUT_FILE={output}\nCMD_JSON=[]\n"
    )
    _write(path=output.with_suffix(output.suffix + ".done"), text=f"{launcher_exit}\n")
    _emit_kv(key="LAUNCHER_EXIT", value=launcher_exit)
    failure = classify_launch_failure(
        launcher_exit=launcher_exit,
        sidecar=output.with_suffix(output.suffix + ".diag"),
        binary_present=binary_present,
        tool=tool,
        output_file=output,
    )
    _emit_kv(key="LAUNCHER_FAILURE_CLASS", value=failure.failure_class)
    _emit_kv(key="LAUNCHER_FAILURE_REASON", value=failure.reason or failure_reason)
    _emit_kv(key="OUTPUT", value=str(output))


def _trust_config_arg(workdir: str) -> str:
    key = workdir.replace("\\", "\\\\").replace('"', '\\"')
    return f'projects."{key}".trust_level="trusted"'


def _git_toplevel(path: str) -> str | None:
    try:
        result = proc.run(
            ["git", "-C", path, "rev-parse", "--show-toplevel"],
            timeout=2,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        value = line.strip()
        if value:
            return value
    return None


def _read_keepalive_clone_path(keepalive: Path) -> str | None:
    try:
        text = keepalive.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        key, value = stripped.split("=", 1)
        if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
            continue
        if key != "CLONE_PATH":
            continue
        try:
            parsed = shlex.split(value, posix=True)
        except ValueError:
            parsed = [value]
        clone_path = parsed[0] if len(parsed) == 1 else value
        if clone_path.strip():
            return clone_path.strip()
    return None


def _clone_path_from_session_tmpdir() -> str | None:
    for name in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR", "SESSION_TMPDIR"):
        tmpdir = os.environ.get(name)
        if not tmpdir:
            continue
        clone = _read_keepalive_clone_path(Path(tmpdir) / ".larch-keepalive")
        if clone:
            return clone
    return None


def _clone_path_from_parent_walk(start: Path) -> str | None:
    current = start
    while True:
        clone = _read_keepalive_clone_path(current / ".larch-keepalive")
        if clone:
            return clone
        if current.parent == current:
            return None
        current = current.parent


def _resolve_review_codex_workdir(cwd: str) -> str:
    start = Path(cwd)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        toplevel = _git_toplevel(project_dir)
        if toplevel:
            return toplevel
    toplevel = _git_toplevel(str(start))
    if toplevel:
        return toplevel
    clone = _clone_path_from_session_tmpdir() or _clone_path_from_parent_walk(start)
    if clone:
        toplevel = _git_toplevel(clone)
        if toplevel:
            return toplevel
    return cwd


def _auth_retry_limit() -> int:
    raw = os.environ.get("LARCH_EXTERNAL_AUTH_RETRIES", "5")
    return int(raw) if raw.isdigit() and int(raw) > 0 else 5


def _is_unclassified_empty_startup_failure(*, exit_code: int, verdict: str) -> bool:
    return exit_code == 1 and verdict == "unclassified"


@contextlib.contextmanager
def _temporary_env(*, name: str, value: str):
    old = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old


def _record_launch_timing(*, tool: str, task_kind: str, start_s: float, output: Path, exit_code: int) -> None:
    proc.run(
        [
            sys.executable,
            str(_PY_CLI),
            "timing",
            "record-vendor-task",
            "--vendor",
            tool,
            "--task-kind",
            task_kind,
            "--start-s",
            str(int(start_s)),
            "--end-s",
            str(int(time.time())),
            "--output",
            str(output),
            "--exit-code",
            str(exit_code),
            "--status",
            "complete" if exit_code == 0 else "signal",
        ],
        check=False,
    )


def _finalize_launch(*, hooks: Sequence[Callable[[], None]] = ()) -> None:
    """Run hooks in caller order."""
    for hook in hooks:
        hook()


def _post_codex_events(*, events: Path, sidecar: Path) -> None:
    if not events.is_file() or events.stat().st_size == 0:
        _write(path=events, text="{}\n")
    _mirror_codex_quota_from_events(events=events, sidecar=sidecar)


def _emit_token_record_if_present(token_record: Path) -> None:
    if token_record.is_file():
        _emit_kv(key="TOKEN_RECORD", value=str(token_record))


def _record_usage_from_events_and_emit_token(*, events: Path, sidecar: Path, label: str, token_record: Path) -> None:
    _record_usage_from_events(events=events, sidecar=sidecar, label=label, token_record=token_record)
    _emit_token_record_if_present(token_record)


def _write_timeout_stall_json(
    stall_json: Path,
    *,
    tool: str,
    exit_code: int,
    timeout_seconds: int,
    overwrite: bool,
) -> None:
    if exit_code == config.EXIT_TIMEOUT and (overwrite or not stall_json.is_file()):
        _write(path=stall_json, text=json.dumps({"tool": tool, "exit_code": exit_code, "timeout": timeout_seconds}) + "\n")




def _run_external_agent_with_auth_retries(
    *,
    tool: str,
    output: Path,
    timeout_seconds: int,
    cmd: Sequence[str],
    env: Mapping[str, str] | None = None,
    cwd: str | None = None,
    capture_stdout_only: bool = False,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    stall_channel: str = "",
    stall_threshold_seconds: int = 0,
) -> RunExternalAgentResult:
    result: RunExternalAgentResult | None = None
    max_auth = _auth_retry_limit()
    auth_attempt = 1
    unclassified_empty_retried = False
    while True:
        with _temporary_env(name="RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX", value=".inner.done"):
            state = external_startup_lock_acquire(tool=tool)
            external_startup_lock_release_after(state=state)
            result = run_external_agent(
                tool=tool,
                output=str(output),
                timeout_seconds=timeout_seconds,
                cmd=cmd,
                env=env,
                cwd=cwd,
                capture_stdout_only=capture_stdout_only,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                stall_channel=stall_channel,
                stall_threshold_seconds=stall_threshold_seconds,
            )
        if result.exit_code == 0:
            return result
        if _policy_rejection_marker_present(output):
            return result
        auth_paths: list[Path] = []
        if stderr_path is not None:
            auth_paths.append(Path(stderr_path))
        if stdout_path is not None:
            auth_paths.append(Path(stdout_path))
        auth_paths.extend([
            output.with_suffix(output.suffix + ".sidecar"),
            output.with_suffix(output.suffix + ".events.jsonl"),
            output,
        ])
        empty_verdict = external_auth_verdict(tool, *auth_paths)
        auth_paths.append(output.with_suffix(output.suffix + ".diag"))
        verdict = external_auth_verdict(tool, *auth_paths)
        if (
            not unclassified_empty_retried
            and _is_unclassified_empty_startup_failure(exit_code=result.exit_code, verdict=empty_verdict)
            and verdict != "auth"
        ):
            unclassified_empty_retried = True
            continue
        if verdict == "auth" and auth_attempt < max_auth:
            auth_attempt += 1
            continue
        return result


def _record_cursor_usage_from_output(*, output: Path, label: str, model: str = "") -> None:
    try:
        obj = json.loads(_read_text(output))
    except json.JSONDecodeError:
        return
    usage = obj.get("usage") if isinstance(obj, dict) else None
    if not isinstance(usage, dict):
        return
    try:
        input_tokens = _num(_first_not_none(usage.get("inputTokens"), usage.get("input_tokens"), 0))
        output_tokens = _num(_first_not_none(usage.get("outputTokens"), usage.get("output_tokens"), 0))
        cache_read = _num(_first_not_none(usage.get("cacheReadTokens"), usage.get("cache_read_input_tokens"), 0))
        cache_create = _num(_first_not_none(usage.get("cacheWriteTokens"), usage.get("cache_creation_input_tokens"), 0))
    except ValueError as exc:
        _append(path=output.with_suffix(output.suffix + ".sidecar"), text=f"agent parse-cursor-usage: {exc}\n")
        return
    total = input_tokens + output_tokens + cache_read + cache_create
    token_record = output.with_suffix(output.suffix + ".token-record")
    text = f"TOOL=cursor\nINPUT={input_tokens}\nOUTPUT={output_tokens}\nCACHE_READ={cache_read}\nCACHE_CREATE={cache_create}\nTOTAL={total}\nRAW={label}\n"
    if model:
        text += f"MODEL={model}\n"
    _write(path=token_record, text=text)
    proc.run(
        [sys.executable, str(_PY_CLI), "token", "record-vendor-sidecar", "--input", str(token_record)],
        check=False,
    )


def _under(*, path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _promote_inner_done(output: Path) -> None:
    paths = LauncherPaths.from_output(output)
    if paths.inner_done.is_file():
        paths.inner_done.replace(paths.done)


# Review preamble constants shared by _review_launcher and _ci_launcher.
_CODEX_REVIEW_STRICT_PREAMBLE = (
    "STRICT CONSTRAINTS — your role is read-only review. Do not create, edit, "
    "delete, or overwrite files, and do not run mutating shell or git commands. "
    "The launcher enforces this with --sandbox read-only (CLI rejects writes)."
)
_CURSOR_SANDBOX_ENFORCEMENT_LINE = (
    "The launcher passes --mode ask to the cursor CLI. Any post-run mutation will "
    "be detected by the dirty-tree sidecar."
)
_CURSOR_REVIEW_STRICT_PREAMBLE = (
    "STRICT CONSTRAINTS — your role is read-only review. Do not create, edit, "
    "delete, or overwrite files, and do not run mutating shell or git commands.\n"
    f"{_CURSOR_SANDBOX_ENFORCEMENT_LINE}"
)
_REVIEW_MAX_TRANSIENT_RETRIES = 4
_COLLECTOR_NS_STRONG_HEADER = (
    "IMPORTANT: Your previous response was not structured correctly. "
    "You MUST output findings in the exact format your original prompt requires, "
    "or the literal NO_ISSUES_FOUND if no issues exist. "
    "Do NOT write narrative, process descriptions, or reading logs. "
    "Begin your response directly with the format your prompt demands.\n\n"
)
