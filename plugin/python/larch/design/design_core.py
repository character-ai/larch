"""Core utilities and low-level helpers for /design lifecycle phases."""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnusedFunction=false, reportUnusedCallResult=false
from __future__ import annotations

import argparse
import contextlib
import fcntl
import io
import os
import re
import shutil
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Iterable, Mapping, Sequence

from larch import io as larch_io
from larch.core import config, logging_util, proc, rust_runtime
from larch.core import redact
from larch.core.ctx import Ctx
from larch.core.repo_roots import larch_entrypoint
from larch.design import design_pause
from larch.state import session_env
from larch.state.session_env import validate_design_tmpdir

_SUBPROCESS_RUN = subprocess.run


DESIGN_BGJOB_STEP3_REVIEW = "design-step3-review"
DESIGN_BGJOB_STEP4_TAIL = "design-step4-tail"
DESIGN_BGJOB_STEP5C = "design-step5c"
DESIGN_BGJOB_STEP_FINAL_SUMMARY = "design-step-final-summary"


def design_bgjob_result_env_path(*, design_tmpdir: Path, step: str) -> Path:
    return design_tmpdir / config.BGJOB_TMP_SUBDIR / f"{step}{config.BGJOB_RESULT_ENV_SUFFIX}"


def design_recreate_merge_env(*, path: Path, design_tmpdir: Path) -> None:
    root = design_tmpdir.resolve()
    target = path.resolve(strict=False)
    try:
        _ = target.relative_to(root)
    except ValueError as exc:
        msg = f"merge env escapes DESIGN_TMPDIR: {path}"
        raise OSError(msg) from exc
    if path.is_symlink():
        msg = f"refusing to replace symlink merge env: {path}"
        raise OSError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or not path.parent.is_dir():
        msg = f"merge env parent is not a regular directory: {path.parent}"
        raise OSError(msg)
    larch_io.atomic_write(path=path, text="", nofollow=True, mode=0o600)


def design_write_merge_env(*, path: Path, design_tmpdir: Path, rows: Iterable[tuple[str, object]]) -> None:
    root = design_tmpdir.resolve()
    target = path.resolve(strict=False)
    try:
        _ = target.relative_to(root)
    except ValueError as exc:
        msg = f"merge env escapes DESIGN_TMPDIR: {path}"
        raise OSError(msg) from exc
    safe_rows: list[tuple[str, str]] = []
    for key, value in rows:
        if not key or "\n" in key or "\r" in key:
            msg = f"invalid merge env key: {key!r}"
            raise ValueError(msg)
        text = str(value)
        if "\n" in text or "\r" in text:
            msg = f"merge env value contains newline: {key}"
            raise ValueError(msg)
        safe_rows.append((key, text))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or not path.parent.is_dir():
        msg = f"merge env parent is not a regular directory: {path.parent}"
        raise OSError(msg)
    larch_io.atomic_write(path=path, text=larch_io.format_kvs(safe_rows), nofollow=True, mode=0o600)


class _CoreUsageError(Exception):
    """User-facing argument or validation error for ported design helpers."""


def _validate_design_tmpdir_arg(candidate: str) -> Path:
    ok, message = validate_design_tmpdir(candidate)
    if not ok:
        raise _CoreUsageError(message)
    path = Path(candidate).resolve()
    if not path.is_dir():
        raise _CoreUsageError("design-tmpdir: path must name a directory")
    return path


def _capture_contract_stream_to_paths(
    callable_obj: Callable[..., int | tuple[int, list[str]]],
    stdout_path: str | Path,
    stderr_path: str | Path,
    *args: object,
    **kwargs: object,
) -> int:
    """Run ``callable_obj`` while capturing fd 1, fd 2, and fd 3 contracts.

    ``quiet_init`` routes machine stdout through fd 3. In-process callers use
    this helper so a core function can emit through ``logging_util.emit_kv``
    without inheriting the caller's stdout/stderr routing after return.
    """
    out_path = Path(stdout_path)
    err_path = Path(stderr_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    err_path.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout.flush()
    sys.stderr.flush()
    os.write(1, b"")
    os.write(2, b"")
    had_contract_fd = False
    try:
        saved_contract = fcntl.fcntl(3, fcntl.F_DUPFD, 10)
        had_contract_fd = True
    except OSError:
        saved_contract = None
    had_quiet_fd = False
    try:
        saved_quiet = fcntl.fcntl(4, fcntl.F_DUPFD, 10)
        had_quiet_fd = True
    except OSError:
        saved_quiet = None
    saved_stdout = fcntl.fcntl(1, fcntl.F_DUPFD, 10)
    saved_stderr = fcntl.fcntl(2, fcntl.F_DUPFD, 10)
    out_fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    err_fd = os.open(err_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.dup2(out_fd, 1)
        os.dup2(err_fd, 2)
        os.dup2(out_fd, 3)
        try:
            with out_path.open("a", encoding="utf-8") as py_out, err_path.open("a", encoding="utf-8") as py_err, contextlib.redirect_stdout(py_out), contextlib.redirect_stderr(py_err):
                try:
                    rc = callable_obj(*args, **kwargs)
                except SystemExit as exc:
                    return int(exc.code) if isinstance(exc.code, int) else 1
                except BaseException:
                    traceback.print_exc()
                    return 1
            if isinstance(rc, tuple):
                rc = rc[0]
            return int(rc)
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(saved_stdout, 1)
            os.dup2(saved_stderr, 2)
            if had_contract_fd and saved_contract is not None:
                os.dup2(saved_contract, 3)
            else:
                with contextlib.suppress(OSError):
                    os.close(3)
            if had_quiet_fd and saved_quiet is not None:
                os.dup2(saved_quiet, 4)
            os.write(1, b"")
            os.write(2, b"")
    finally:
        with contextlib.suppress(OSError):
            os.close(out_fd)
        with contextlib.suppress(OSError):
            os.close(err_fd)
        with contextlib.suppress(OSError):
            os.close(saved_stdout)
        with contextlib.suppress(OSError):
            os.close(saved_stderr)
        if saved_contract is not None:
            with contextlib.suppress(OSError):
                os.close(saved_contract)
        if saved_quiet is not None:
            with contextlib.suppress(OSError):
                os.close(saved_quiet)


capture_contract_stream_to_paths = _capture_contract_stream_to_paths


def _append_execution_issue(*, design_tmpdir: Path, message: str) -> None:
    path = design_tmpdir / "execution-issues.md"
    outcome = rust_runtime.execution_issues_append(
        proc.ProcRunner(),
        log=str(path),
        category="Warnings",
        entry=message,
    )
    if outcome.failed:
        raise OSError(outcome.error)


def _emit_core_kvs(rows: Iterable[tuple[str, str]]) -> None:
    for key, value in rows:
        logging_util.emit_kv(key=key, value=value)


def _core_quiet_mirrors_to_fd4() -> bool:
    pid = os.environ.get("LARCH_QUIET_PID", "")
    active = os.environ.get("LARCH_QUIET_ACTIVE", "").lower() in {"1", "true", "yes", "on"}
    return active and pid == str(os.getpid())


def _core_diagnostic(message: str) -> None:
    """Mirror bash larch_err for post-quiet_init *_core validation errors."""
    line = redact.redact_outbound(logging_util.sanitize_diagnostic_line(message)).rstrip("\n") + "\n"
    _ = sys.stderr.write(line)
    _ = sys.stderr.flush()
    if _core_quiet_mirrors_to_fd4():
        with contextlib.suppress(OSError):
            _ = os.write(4, line.encode("utf-8"))


def _core_print_exc() -> None:
    buf = io.StringIO()
    traceback.print_exc(file=buf)
    for line in buf.getvalue().splitlines():
        _core_diagnostic(line)


def _read_env_value(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path=path, key=key, default=default, first_match=True, empty_value_means_default=True, reject_symlink=True, on_error_default=True, errors="replace")


def _read_env_value_last(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(
        path=path,
        key=key,
        default=default,
        duplicate_policy="last-non-empty",
        reject_symlink=True,
        on_error_default=True,
        errors="replace",
    )


def _read_env_values(*, path: Path, defaults: Mapping[str, str]) -> dict[str, str]:
    return larch_io.read_kvs(
        path,
        default=defaults,
        duplicate_policy="last-non-empty",
        allowed_keys=defaults,
        reject_symlink=True,
        on_error_default=True,
        errors="replace",
    )



def _cli_cmd(plugin_root: Path, *args: str) -> list[str]:
    return [sys.executable, str(plugin_root / "python" / "cli.py"), *args]


# Shared private helpers absorbed from the retired design_router.py (#8577);
# the route/init-runparams verbs themselves are Rust-owned in
# crates/larch-cli/src/design_commands.rs.


def _usage() -> None:
    print(
        "usage: read-result-env.sh --input PATH [--fallback-input PATH] --allow KEY ... --output PATH",
        file=sys.stderr,
    )


def _write_kv_file(*, path: Path, rows: list[tuple[str, str]]) -> bool:
    try:
        larch_io.write_kvs(path=path, values=rows, atomic=False, create_parent=False)
    except OSError:
        return False
    return True


def _parse_stdout_kv(text: str) -> dict[str, list[str]]:
    return larch_io.parse_kv(
        text,
        duplicate_policy="all",
        skip_empty_key=True,
    )


def _normalize_step(value: str) -> str:
    lowered = value.lower()
    return "".join(ch if (ch.isalnum() or ch in "._-") else "-" for ch in lowered)


def _extract_args(line: str) -> str:
    marker = " ARGS="
    if marker not in line:
        return ""
    return line.split(marker, 1)[1]


@dataclass(frozen=True)
class FailureLogRequest:
    """One structured request to record a design execution failure."""

    plugin_root: Path
    design_tmpdir: Path
    site: str
    tool: str
    exit_code: int | str
    category: str
    output_file: Path


def append_failure(
    *,
    request: FailureLogRequest,
    env: Mapping[str, str] | None = None,
    runner: Callable[..., proc.CommandResult] = proc.run,
) -> bool:
    """Append one failure record through the canonical run-log command."""
    result = runner(
        [str(larch_entrypoint(request.plugin_root)), "run-log", "append-failure", "--log", str(request.design_tmpdir / "execution-issues.md"), "--site", request.site, "--tool", request.tool, "--exit-code", str(request.exit_code), "--category", request.category, "--output-file", str(request.output_file), "--redact"],
        env={**os.environ, **env} if env is not None else None,
    )
    return result.returncode == 0


def _append_failure(*, plugin_root: Path, design_tmpdir: Path, site: str, tool: str, exit_code: int | str, category: str, output_file: Path) -> bool:
    """Compatibility wrapper for established design failure-log call sites."""
    return append_failure(
        request=FailureLogRequest(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            site=site,
            tool=tool,
            exit_code=exit_code,
            category=category,
            output_file=output_file,
        )
    )


def _design_verb_plugin_root(plugin_root: Path | None) -> Path:
    if plugin_root is not None:
        return plugin_root
    return Path(os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, Path(__file__).resolve().parents[3]))


def _design_verb_command(plugin_root: Path | None, verb: str, args: Sequence[str]) -> list[str]:
    """Literal per-verb argv for the Rust-owned ``design`` seam (#8580).

    Each Rust-owned verb has its own literal ``[entrypoint, "design", "<verb>", ...]``
    list so the command-registry caller discovery records the exact verbs this
    module dispatches rather than a ``design *`` wildcard over every design verb.
    """
    entrypoint = str(larch_entrypoint(_design_verb_plugin_root(plugin_root)))
    if verb == "read-result-env":
        return [entrypoint, "design", "read-result-env", *args]
    if verb == "stage-terminal-state":
        return [entrypoint, "design", "stage-terminal-state", *args]
    if verb == "failure-report":
        return [entrypoint, "design", "failure-report", *args]
    raise ValueError(f"unsupported Rust-owned design verb: {verb!r}")


def run_design_verb_captured(
    *, verb: str, args: Sequence[str], stdout_path: Path, stderr_path: Path, plugin_root: Path | None = None
) -> int:
    """Invoke a Rust-owned ``design <verb>`` and capture its streams to files.

    Replaces the in-process ``capture_contract_stream_to_paths(<core>, ...)``
    call sites for the verbs migrated to Rust in #8580: the Rust owner emits its
    machine ``KEY=value`` rows to stdout and diagnostics to stderr, so capturing
    them to the two log paths preserves the callers' ``STAGED=`` reads.
    """
    cmd = _design_verb_command(plugin_root, verb, args)
    try:
        with Path(stdout_path).open("w", encoding="utf-8") as out, Path(stderr_path).open("w", encoding="utf-8") as err:
            result = subprocess.run(cmd, stdout=out, stderr=err, check=False)  # lint-subprocess-via-runner: ok invokes the Rust-owned design verb entrypoint, capturing its streams to the caller's log files
    except OSError:
        return 1
    return result.returncode


def run_design_verb(*, verb: str, args: Sequence[str], plugin_root: Path | None = None) -> int:
    """Invoke a Rust-owned ``design <verb>`` inheriting stdout/stderr.

    Used where the verb writes its payload to an ``--output`` file and the
    caller only needs the exit code (e.g. ``read-result-env`` in step5c).
    """
    cmd = _design_verb_command(plugin_root, verb, args)
    try:
        result = subprocess.run(cmd, check=False)  # lint-subprocess-via-runner: ok invokes the Rust-owned design verb entrypoint for its exit code and file side effects
    except OSError:
        return 1
    return result.returncode


# --- Relocated Step 0 wrapper-env constants, wrapper-arg parser, bash-quoting
# codec, and env loaders (retired design_step0_env.py, #8578); the Step 0 verbs
# themselves are Rust-owned in crates/larch-cli/src/design_commands.rs. ---

COMMON_ENV_DEFAULTS: dict[str, str] = {
    **session_env.COMMON_DESIGN_ENV_DEFAULTS,
    **session_env.DESIGN_REQUEST_ENV_DEFAULTS,
    "difficulty": "",
    "SUMMARY_OUTCOME": "",
    "CLARIFY_FAILURE_LOG": "",
    "CLARIFY_HARD_HALT_RC": "1",
}
SOURCE_ENV_ALLOW = frozenset({
    "DESIGN_TMPDIR",
    "SESSION_TMPDIR",
    "SESSION_ID",
    "ISSUE_NUMBER",
    "ISSUE_TITLE",
    "HAS_CLARIFY_LABEL",
    "REPO",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "CLAUDE_PLUGIN_ROOT",
})
ROUTE_STATE_PATH = ".design-step0-route-state.env"
_TEMPLATE_PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}"
CONFIGURATION_ERROR_RC = 2


class Step0WrapperNs(argparse.Namespace):
    session_env_path: str
    claude_pid: str
    plugin_root: str
    mode: str
    outcome: str
    skip_validate: bool
    issue_number: str
    exit_code: str
    failure_detail_log: str
    reason: str
    tool: str
    public_argv: list[str]


def _parse_wrapper_args(argv: Sequence[str]) -> Step0WrapperNs:
    ns = Step0WrapperNs()
    ns.session_env_path = ""
    ns.claude_pid = ""
    ns.plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    ns.mode = ""
    ns.outcome = os.environ.get("SUMMARY_OUTCOME", "")
    ns.skip_validate = False
    ns.issue_number = ""
    ns.exit_code = os.environ.get("CLARIFY_HARD_HALT_RC", "1") or "1"
    ns.failure_detail_log = os.environ.get("CLARIFY_FAILURE_LOG", "")
    ns.reason = "external tool unhealthy; re-run once it recovers."
    ns.tool = "degraded-tools-gate"
    ns.public_argv = []
    i = 0
    args = list(argv)
    value_flags = {
        "--session-env-path": "session_env_path",
        "--claude-pid": "claude_pid",
        "--plugin-root": "plugin_root",
        "--mode": "mode",
        "--outcome": "outcome",
        "--issue-number": "issue_number",
        "--exit-code": "exit_code",
        "--failure-detail-log": "failure_detail_log",
        "--reason": "reason",
        "--tool": "tool",
        "--site": "site",
        "--step3-review-loop-status": "step3_review_loop_status",
        "--loop-status": "loop_status",
    }
    while i < len(args):
        token = args[i]
        if token == "--":
            ns.public_argv = args[i + 1 :]
            return ns
        if token in {"--skip-validate", "--snapshot-original"}:
            if token == "--skip-validate":
                ns.skip_validate = True
            i += 1
            continue
        if token in value_flags:
            if i + 1 >= len(args):
                print(f"design wrapper: {token} requires a value", file=sys.stderr)
                raise SystemExit(2)
            setattr(ns, value_flags[token], args[i + 1])
            i += 2
            continue
        print(f"design wrapper: unknown argument: {token}", file=sys.stderr)
        raise SystemExit(2)
    return ns


def require_plugin_root(value: str) -> Path:
    if not value:
        print("/design wrapper: CLAUDE_PLUGIN_ROOT is empty; abort", file=sys.stderr)
        raise SystemExit(1)
    if value == _TEMPLATE_PLUGIN_ROOT:
        print(f"/design wrapper: CLAUDE_PLUGIN_ROOT is the unexpanded template literal {_TEMPLATE_PLUGIN_ROOT}; abort", file=sys.stderr)
        raise SystemExit(1)
    os.environ["CLAUDE_PLUGIN_ROOT"] = value
    return Path(value)


def _decode_ansi_c_quoted(inner: str) -> str:
    max_oct_digits = 3
    short_hex_digits = 2
    unicode_hex_digits = 4
    long_unicode_hex_digits = 8
    out: list[str] = []
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch != "\\" or i + 1 >= len(inner):
            out.append(ch)
            i += 1
            continue
        nxt = inner[i + 1]
        escapes = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v", "\\": "\\", "'": "'", '"': '"'}
        if nxt in escapes:
            out.append(escapes[nxt])
            i += 2
            continue
        if nxt in "01234567":
            j = i + 1
            oct_digits = ""
            while j < len(inner) and len(oct_digits) < max_oct_digits and inner[j] in "01234567":
                oct_digits += inner[j]
                j += 1
            out.append(chr(int(oct_digits, 8)))
            i = j
            continue
        if nxt == "x":
            j = i + 2
            hex_digits = ""
            while j < len(inner) and len(hex_digits) < short_hex_digits and inner[j] in "0123456789abcdefABCDEF":
                hex_digits += inner[j]
                j += 1
            if hex_digits:
                out.append(chr(int(hex_digits, 16)))
                i = j
                continue
        if nxt == "u" and i + 5 <= len(inner):
            hex_digits = inner[i + 2 : i + 6]
            if len(hex_digits) == unicode_hex_digits and all(c in "0123456789abcdefABCDEF" for c in hex_digits):
                out.append(chr(int(hex_digits, 16)))
                i += 6
                continue
        if nxt == "U" and i + 9 <= len(inner):
            hex_digits = inner[i + 2 : i + 10]
            if len(hex_digits) == long_unicode_hex_digits and all(c in "0123456789abcdefABCDEF" for c in hex_digits):
                out.append(chr(int(hex_digits, 16)))
                i += 10
                continue
        out.append(nxt)
        i += 2
    return "".join(out)


def _decode_utf8_byte_escapes(value: str) -> str:
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _decode_bash_percent_q(value: str) -> str:
    if value == "''":
        return ""
    if not value:
        return ""
    if value.startswith("$'") and value.endswith("'"):
        return _decode_utf8_byte_escapes(_decode_ansi_c_quoted(value[2:-1]))
    if value.startswith("'"):
        out = []
        i = 1
        while i < len(value):
            if value[i] != "'":
                out.append(value[i])
                i += 1
                continue
            if value.startswith("'\"'\"'", i):
                out.append("'")
                i += 5
                continue
            break
        return "".join(out)
    out = []
    i = 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            out.append(value[i + 1])
            i += 2
        else:
            out.append(value[i])
            i += 1
    return "".join(out)


def _decode_shell_assignment_value(value: str) -> str:
    if value == "":
        return ""
    return _decode_bash_percent_q(value)


def load_bash_quoted_env(*, path: Path, allow_keys: Iterable[str]) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        return {}
    data = larch_io.parse_kv(
        "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()),
        allowed_keys=set(allow_keys),
        skip_comments=True,
        duplicate_policy="last",
    )
    return {key: _decode_shell_assignment_value(value) for key, value in data.items()}


def _load_source_env(*, path: str | Path, allow_keys: Iterable[str] = SOURCE_ENV_ALLOW, claude_pid: str = "") -> dict[str, str]:
    source = Path(path)
    if not str(path):
        return {}
    read_path: Path | None
    if source.is_symlink():
        if not claude_pid:
            return {}
        resolved = session_env.resolve_trusted_design_session_env_source(path=source, claude_pid=claude_pid)
        if resolved is None:
            return {}
        read_path = resolved
    elif source.is_file():
        read_path = source
    else:
        return {}
    normalized = "\n".join(
        line.removeprefix("export ")
        for raw in read_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if (line := raw.strip()) and not line.startswith("#")
    )
    data = larch_io.parse_kv(normalized, allowed_keys=set(allow_keys), duplicate_policy="last")
    return {key: _decode_shell_assignment_value(value) for key, value in data.items()}


def _base_env() -> dict[str, str]:
    return {key: os.environ.get(key, default) for key, default in COMMON_ENV_DEFAULTS.items()}


def _load_wrapper_env(ns: Step0WrapperNs) -> dict[str, str]:
    data = _base_env()
    data.update(_load_source_env(path=ns.session_env_path, claude_pid=ns.claude_pid))
    if ns.plugin_root:
        data["CLAUDE_PLUGIN_ROOT"] = ns.plugin_root
    if ns.outcome:
        data["SUMMARY_OUTCOME"] = ns.outcome
    return data


# --- Relocated Step 0 main-entry support helpers (retired design_step0.py,
# #8578); the Step 0 main entries are Rust-owned. ---


def _derive_binary_found(env: dict[str, str]) -> None:
    if not env.get("CODEX_BINARY_FOUND"):
        env["CODEX_BINARY_FOUND"] = "true" if shutil.which("codex") else "false"
    if not env.get("CURSOR_BINARY_FOUND"):
        env["CURSOR_BINARY_FOUND"] = "true" if shutil.which("cursor") else "false"


def _run_best_effort(*, command: Sequence[str], env: Mapping[str, str] | None = None) -> None:
    with contextlib.suppress(OSError):
        subprocess.run(list(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=dict(env) if env is not None else None, check=False)


def _pause_args(
    *, design_tmpdir: str | Path,
    env: Mapping[str, str] | None = None,
    ctx: Ctx | None = None,
) -> list[str]:
    if ctx is not None:
        issue = ctx.issue_number
        repo = ctx.repo
    elif env is not None:
        issue = env.get("ISSUE_NUMBER", "")
        repo = env.get("REPO", "")
    else:
        issue = os.environ.get("ISSUE_NUMBER", "")
        repo = os.environ.get("REPO", "")
    args = ["--design-tmpdir", str(design_tmpdir), "--issue", issue]
    if repo:
        args.extend(["--repo", repo])
    return args


def _require_design_tmpdir(*, env: Mapping[str, str], design_tmpdir: str | Path | None = None) -> Path:
    raw = str(design_tmpdir or env.get("DESIGN_TMPDIR", ""))
    if not raw:
        print("/design wrapper: DESIGN_TMPDIR required", file=sys.stderr)
        raise SystemExit(1)
    path = Path(raw)
    if not path.is_absolute():
        print("/design wrapper: DESIGN_TMPDIR must be an absolute path", file=sys.stderr)
        raise SystemExit(1)
    if not path.is_dir():
        print(f"/design wrapper: DESIGN_TMPDIR is not an existing directory: {path}", file=sys.stderr)
        raise SystemExit(1)
    return path.resolve()


def _require_design_tmpdir_nonempty(*, env: Mapping[str, str], site: str) -> Path:
    raw = env.get("DESIGN_TMPDIR", "")
    if not raw:
        print(f"/design Step 5b {site}: DESIGN_TMPDIR required", file=sys.stderr)
        raise SystemExit(1)
    return Path(raw)


def check_pause_and_exit(*, env: Mapping[str, str], design_tmpdir: str | Path | None = None) -> None:
    raw = str(design_tmpdir or env.get("DESIGN_TMPDIR", ""))
    if not raw:
        return
    tmpdir = _require_design_tmpdir(env=env, design_tmpdir=design_tmpdir)
    if (tmpdir / ".pause-requested").is_file():
        rc = design_pause.pause_save_main(_pause_args(design_tmpdir=tmpdir, env=env))
        raise SystemExit(rc)


def _step2b5_self_log(*, plugin_root: Path, design_tmpdir: Path, rc: int, stdout: str, stderr_tmp: Path) -> None:
    if rc == 0:
        return
    stderr = ""
    with contextlib.suppress(OSError):
        stderr = stderr_tmp.read_text(encoding="utf-8", errors="replace")
    combined = stdout
    if stderr:
        if combined and not combined.endswith("\n"):
            combined += "\n"
        combined += stderr
    output_file = design_tmpdir / "check-plan-size.validation.log"
    try:
        output_file.write_text(combined, encoding="utf-8")
    except OSError:
        return
    _append_failure(plugin_root=plugin_root, design_tmpdir=design_tmpdir, site="design Step 2b.5", tool="scripts/larch.sh plan check-size", exit_code=rc, category="Warnings", output_file=output_file)


# --- Relocated wrapper-env, session helpers, pause/capture, and phase-driver
# result-env writers (retired design_session.py, #8578). The settle-next-action
# dispatch is Rust-owned; Python keeps no in-process copy. ---

PHASE_RESULT_ENV_ALLOW_KEYS = {
    "ACCEPTED_COUNT",
    "AGGREGATOR_STATUS",
    "BASELINE_DIFF_LINES",
    "BASELINE_PLAN_LINES",
    "DEDUP_RC",
    "DEGRADED_PANEL",
    "DEGRADED_PANEL_WARNING",
    "INVALID_SLOT_PANEL_WARNING",
    "DIFF_ADDED",
    "DIFF_DELETED",
    "DIFF_LINES",
    "DRIFT_DIFF_RATIO",
    "DRIFT_MULTIPLE",
    "DRIFT_PLAN_RATIO",
    "DRIFT_TRIGGER_FIRED",
    "EMIT_PLAN_STATUS",
    "ERROR",
    "FINAL_ROUND_NUM",
    "IMPORTANT_ACCEPTED_COUNT",
    "LOOP_STATUS",
    "MECHANICAL_CHURN",
    "NEXT_ACTION",
    "OOS_SKIP_BREADCRUMB",
    "PANEL_PRUNED_EMPTY",
    "PARTITION_REQUESTED",
    "PLAN_LINES",
    "PLAN_REVIEW_CONTINUE_REASON",
    "PLAN_SIZE_STATUS",
    "POSTPLAN_EMIT_STATUS",
    "POSTPLAN_RC",
    "REASON",
    "REVIEW_ROUND_COUNT",
    "ROUND_NUM",
    "ROUNDS_COMPLETED",
    "SCOPE_ANCHOR_FILE",
    "SIZE_TRIGGER_FIRED",
    "SNAPSHOT_STATUS",
    "SETTLE_NEXT_ACTION",
    "SETTLE_EXIT_RC",
    "SETTLE_STATUS",
    "SOFT_ADVISORY",
    "STEP3_REVIEW_LOOP_STATUS",
    "STEP3_REVIEW_CAP_REACHED",
    "STEP3_REVIEW_ROUND_NUM",
    "STEP2B5_EXIT_RC",
    "STEP2B5_NEXT_ACTION",
    "STEP2B5_STATUS",
    "TALLY_PLAN_REVIEW_STATUS",
    "TRIGGER_REASONS",
    "VALIDATE_DEFECT_COUNT",
    "VALIDATE_LOG_FILE",
    "VALIDATE_MISSING_SCRIPT_COUNT",
    "VALIDATE_SKIPPED_COUNT",
    "VALIDATE_STATUS",
    "VALIDATE_UNSAFE_TOKEN_COUNT",
    "VOTING_TALLY_FILE",
    "WARN",
}

CHECK_SIZE_WARNING_RC = 2


_WRAPPER_ENV_DEFAULTS: dict[str, str] = {
    "CLAUDE_PLUGIN_ROOT": "",
    "MODE": "",
    "SITE": "",
    "SUMMARY_OUTCOME": "",
    "SKIP_VALIDATE": "",
    **session_env.COMMON_DESIGN_ENV_DEFAULTS,
    **session_env.DESIGN_REQUEST_ENV_DEFAULTS,
    **session_env.VALIDATOR_STATUS_ENV_DEFAULTS,
    "PUBLISH_OK": "",
    "PLAN_WRITE_OK": "",
    "STANDALONE_HEAVY_FAILED": "",
    "CLEANUP_ELIGIBLE": "",
}

_SESSION_ENV_ALLOWLIST = frozenset(_WRAPPER_ENV_DEFAULTS) | {
    "LARCH_AUTO_MODE",
    "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT",
    "LARCH_TIMING_LEDGER",
    "LARCH_TOKEN_SESSION_ID",
    "LARCH_CLAUDE_SOURCE_FILE",
    "PREV_IMPLEMENT_TMPDIR",
    "LARCH_DYNAMIC_ARCHETYPES_MAX",
    "LARCH_RUN_ID",
    "LARCH_CLAUDE_PLUGIN_ROOT",
    "LARCH_DESIGN_DRAFTER",
    "LARCH_DESIGN_PLAN_MODEL",
    "LARCH_DESIGN_DRIFT_MULTIPLE",
}


# Mutable builder: the argv parser sets fields on the instance as it scans.
@dataclass
class WrapperArgs:
    session_env_path: str = ""
    claude_pid: str = ""
    plugin_root: str = ""
    mode: str = ""
    site: str = ""
    snapshot_original: bool = False
    outcome: str = ""
    skip_validate: bool = False
    write_completion_only: bool = False
    include_step2b: bool = False
    write_step2b_completion_only: bool = False
    step3_review_loop_status: str = ""
    loop_status: str = ""
    validator_target_file: str = ""
    validate_log_file: str = ""
    validate_defect_count: str = ""
    validate_unsafe_token_count: str = ""
    validate_skipped_count: str = ""
    operator_cancel: bool = False
    public_argv_words: list[str] | None = None


@dataclass(frozen=True)
class DesignSessionRequest:
    """Rehydrated request shared by the small /design entry points."""

    claude_plugin_root: str
    design_tmpdir: str
    issue_number: str
    repo: str
    claude_pid: str


class DesignSessionRequestError(ValueError):
    """A session-env path cannot safely provide a generated-wrapper request."""


@dataclass(frozen=True)
class PostplanResult:
    postplan_rc: int
    stdout_lines: str
    status: str
    inline_retry_scheduled: bool = False


@dataclass(frozen=True)
class SettleDispatchResult:
    action: str
    exit_rc: int
    status: str


@dataclass(frozen=True)
class Step2b5DispatchResult:
    action: str
    exit_rc: int
    status: str


@dataclass(frozen=True)
class PostplanPaths:
    design_tmpdir: Path
    completed_dir: Path
    step2b5_done: Path
    step2b_done: Path
    inline_retry_done: Path
    inline_retry_pending: Path
    fallback_used: Path
    plan_source: Path
    plan_summary: Path

    @classmethod
    def from_design_tmpdir(cls, design_tmpdir: Path) -> PostplanPaths:
        root = design_tmpdir.resolve()
        completed = root / ".completed"
        return cls(
            design_tmpdir=root,
            completed_dir=completed,
            step2b5_done=completed / "step-2b.5",
            step2b_done=completed / "step-2b",
            inline_retry_done=root / ".step2b-postplan-inline-retry-done",
            inline_retry_pending=root / ".step2b-postplan-inline-retry-pending",
            fallback_used=root / ".step2b-postplan-fallback-used",
            plan_source=root / ".step2b-plan-source",
            plan_summary=root / "plan-summary.md",
        )


@dataclass(frozen=True)
class PostplanDecision:
    postplan_rc: int
    status: str
    rows: tuple[str, ...]
    touches: tuple[Path, ...]
    writes: tuple[tuple[Path, str], ...]
    unlinks: tuple[Path, ...]
    clear_scout_manifests: bool = False
    pause_save: bool = False
    fatal_stderr: str = ""
    print_captured_before_return: bool = False
    print_stdout_before_system_exit: bool = False
    inline_retry_scheduled: bool = False


def _valid_var_name(value: str) -> bool:
    if not value or value[0].isdigit():
        return False
    return all(ch.isalnum() or ch == "_" for ch in value)


def step2b5_next_action_for(*, check_size_rc: int, check_size_kvs: dict[str, str], partition_requested: bool) -> Step2b5DispatchResult:
    """Choose the Step 2b.5 action.

    Priority is non-zero check-size rc, hard size trigger, explicit partition,
    drift advisory, then under-threshold.
    """
    if check_size_rc != 0:
        if check_size_rc == CHECK_SIZE_WARNING_RC:
            return Step2b5DispatchResult(action="rc2-warning", exit_rc=CHECK_SIZE_WARNING_RC, status="rc2-warning")
        return Step2b5DispatchResult(action="internal-error", exit_rc=check_size_rc, status="internal-error")
    if check_size_kvs.get("SIZE_TRIGGER_FIRED", "false") == "true":
        return Step2b5DispatchResult(action="hard-trigger", exit_rc=0, status="plan-size-trigger")
    if partition_requested:
        return Step2b5DispatchResult(action="partition-split", exit_rc=0, status="partition-requested")
    if check_size_kvs.get("DRIFT_TRIGGER_FIRED", "false") == "true":
        return Step2b5DispatchResult(action="drift-advisory", exit_rc=0, status="drift-advisory")
    return Step2b5DispatchResult(action="under-threshold", exit_rc=0, status="under-threshold")


def _quote_single(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _parse_common_wrapper_args(argv: Sequence[str]) -> WrapperArgs:
    args = list(argv)
    out = WrapperArgs(public_argv_words=[])
    value_flags = session_env.WRAPPER_VALUE_FLAGS
    bool_flags: dict[str, str] = {
        "--snapshot-original": "snapshot_original",
        "--skip-validate": "skip_validate",
        "--write-completion-only": "write_completion_only",
        "--include-step2b": "include_step2b",
        "--write-step2b-completion-only": "write_step2b_completion_only",
        "--operator-cancel": "operator_cancel",
    }
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--":
            out.public_argv_words = args[i + 1 :]
            break
        if token in value_flags:
            if i + 1 >= len(args):
                raise ValueError(f"{token} requires a value")
            setattr(out, value_flags[token], args[i + 1])
            i += 2
            continue
        if token in bool_flags:
            setattr(out, bool_flags[token], True)
            i += 1
            continue
        # Forward-compatible no-op parsing for retired generated wrapper args.
        # Unknown flags with a following value consume that value; bare flags are
        # ignored. Behavior-bearing flags above are bound explicitly.
        if token.startswith("--") and i + 1 < len(args) and not args[i + 1].startswith("--"):
            i += 2
        else:
            i += 1
    return out


def _parse_session_env_line(raw: str) -> tuple[str, str] | None:
    return session_env.parse_allowlisted_env_line(
        raw=raw,
        allowlist=_SESSION_ENV_ALLOWLIST,
        name_validator=_valid_var_name,
        reject_newline_rhs=True,
    )


def _load_session_env(path: str) -> dict[str, str]:
    if not path:
        return {}
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        return {}
    env: dict[str, str] = {}
    try:
        text = source.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return env
    for raw in text.splitlines():
        pair = _parse_session_env_line(raw)
        if pair is not None:
            env[pair[0]] = pair[1]
    return env


def _rehydrate_wrapper_env(parsed: WrapperArgs) -> dict[str, str]:
    merged: dict[str, str] = {key: os.environ.get(key, default) for key, default in _WRAPPER_ENV_DEFAULTS.items()}
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        merged["CLAUDE_PLUGIN_ROOT"] = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    merged.update(_load_source_env(path=parsed.session_env_path, allow_keys=_SESSION_ENV_ALLOWLIST, claude_pid=parsed.claude_pid))
    if parsed.plugin_root:
        merged["CLAUDE_PLUGIN_ROOT"] = parsed.plugin_root
    if parsed.mode:
        merged["MODE"] = parsed.mode
    if parsed.site:
        merged["SITE"] = parsed.site
    if parsed.outcome:
        merged["SUMMARY_OUTCOME"] = parsed.outcome
    if parsed.skip_validate:
        merged["SKIP_VALIDATE"] = "1"
    if parsed.step3_review_loop_status:
        merged["STEP3_REVIEW_LOOP_STATUS"] = parsed.step3_review_loop_status
    if parsed.loop_status:
        merged["LOOP_STATUS"] = parsed.loop_status
    if parsed.validator_target_file:
        merged["_validator_target_file"] = parsed.validator_target_file
    if parsed.validate_log_file:
        merged["VALIDATE_LOG_FILE"] = parsed.validate_log_file
    if parsed.validate_defect_count:
        merged["VALIDATE_DEFECT_COUNT"] = parsed.validate_defect_count
    if parsed.validate_unsafe_token_count:
        merged["VALIDATE_UNSAFE_TOKEN_COUNT"] = parsed.validate_unsafe_token_count
    if parsed.validate_skipped_count:
        merged["VALIDATE_SKIPPED_COUNT"] = parsed.validate_skipped_count
    return session_env.finalize_wrapper_env(merged)


def load_design_session_request(argv: Sequence[str]) -> DesignSessionRequest:
    """Load the generated-wrapper request shape without sourcing shell code."""
    parsed = _parse_common_wrapper_args(argv)
    source = Path(parsed.session_env_path) if parsed.session_env_path else None
    if source is not None and source.is_symlink():
        trusted = session_env.resolve_trusted_design_session_env_source(
            path=source, claude_pid=parsed.claude_pid
        )
        if trusted is None:
            raise DesignSessionRequestError(
                f"/design wrapper: refusing untrusted session-env symlink: {parsed.session_env_path}"
            )
    merged = _rehydrate_wrapper_env(parsed)
    os.environ.update(merged)
    return DesignSessionRequest(
        claude_plugin_root=merged["CLAUDE_PLUGIN_ROOT"],
        design_tmpdir=merged["DESIGN_TMPDIR"],
        issue_number=merged["ISSUE_NUMBER"],
        repo=merged["REPO"],
        claude_pid=parsed.claude_pid,
    )


def _design_require_plugin_root() -> int:
    rc = session_env.require_plugin_root()
    if rc != 0:
        return rc
    os.environ["CLAUDE_PLUGIN_ROOT"] = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    return 0


def _design_tmpdir(ctx: Ctx | None = None) -> Path:
    return Path(ctx.design_tmpdir if ctx is not None else os.environ.get("DESIGN_TMPDIR", ""))


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _write_text(*, path: Path, text: str) -> None:
    larch_io.write_text(path=path, text=text)


def _exact_line_file(*, path: Path, expected: str) -> bool:
    try:
        return path.read_text(encoding="utf-8", errors="replace").rstrip("\n") == expected
    except OSError:
        return False


def _call_pause_save(*, design_tmpdir: Path, ctx: Ctx | None = None) -> int:
    args = ["--design-tmpdir", str(design_tmpdir), "--issue", ctx.issue_number if ctx is not None else os.environ.get("ISSUE_NUMBER", "")]
    repo = ctx.repo if ctx is not None else os.environ.get("REPO", "")
    if repo:
        args.extend(["--repo", repo])
    return design_pause.pause_save_main(args)


def _call_pause_save_captured(*, design_tmpdir: Path, ctx: Ctx | None = None) -> tuple[int, str, str]:
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        rc = _call_pause_save(design_tmpdir=design_tmpdir, ctx=ctx)
    return int(rc), stdout_buf.getvalue(), stderr_buf.getvalue()


def _pause_save_stdout_ok(stdout: str) -> bool:
    return any(line == "PAUSE_OK=true" for line in stdout.splitlines())


def _print_pause_save_capture(stdout: str, stderr: str) -> None:
    _print_text(stdout)
    if stderr:
        print(stderr, end="", file=sys.stderr)


def _run_pause_save_terminal(*, design_tmpdir: Path, ctx: Ctx | None = None) -> int:
    rc, stdout, stderr = _call_pause_save_captured(design_tmpdir=design_tmpdir, ctx=ctx)
    _print_pause_save_capture(stdout, stderr)
    if not _pause_save_stdout_ok(stdout):
        return 1
    return rc


def pause_save_for_request(*, design_tmpdir: Path) -> int:
    """Run the existing pause owner for a rehydrated small-entry request."""
    return _call_pause_save(design_tmpdir=design_tmpdir)


def _maybe_timing_mark(*, label: str, ctx: Ctx | None = None) -> None:
    plugin_root = ctx.claude_plugin_root if ctx is not None else os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not plugin_root or plugin_root == "${CLAUDE_PLUGIN_ROOT}":
        return
    env = ctx.subprocess_env(overrides={"LARCH_TIMING_SKILL": "design"}) if ctx is not None else os.environ.copy()
    env["LARCH_TIMING_SKILL"] = "design"
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    with contextlib.suppress(OSError):
        subprocess.run(
            [str(larch_entrypoint(plugin_root)), "timing", "mark", label],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def mark_design_timing(*, label: str) -> None:
    """Best-effort design timing mark for a rehydrated small-entry request."""
    _maybe_timing_mark(label=label)


def _capture_stdout(*, callable_obj: Callable[..., int], argv: Sequence[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = callable_obj(list(argv))
    return int(rc), buf.getvalue()


def _capture_stdout_stderr(*, callable_obj: Callable[..., int], argv: Sequence[str], stderr_path: Path) -> tuple[int, str]:
    buf = io.StringIO()
    try:
        with stderr_path.open("w", encoding="utf-8") as err, contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            try:
                rc = callable_obj(list(argv))
                return int(rc), buf.getvalue()
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
                return code, buf.getvalue()
            except BaseException:
                err.write(traceback.format_exc())
                return 1, buf.getvalue()
    except OSError:
        return 1, buf.getvalue()


def _print_text(text: str) -> None:
    if text:
        print(text, end="" if text.endswith("\n") else "\n")


def prelude_main(argv: Sequence[str]) -> int:
    try:
        request = load_design_session_request(argv)
    except DesignSessionRequestError as exc:
        print(exc, file=sys.stderr)
        return 1
    if not request.design_tmpdir:
        return 0
    pause_requested = Path(request.design_tmpdir) / ".pause-requested"
    if not pause_requested.is_file():
        return 0
    return _call_pause_save(design_tmpdir=Path(request.design_tmpdir))


def step3_continuation_entry_main(argv: Sequence[str]) -> int:
    try:
        request = load_design_session_request(argv)
    except DesignSessionRequestError as exc:
        print(exc, file=sys.stderr)
        return 1
    if _design_require_plugin_root() != 0:
        return 1
    if not request.design_tmpdir:
        print("/design Step 3 continuation-entry: DESIGN_TMPDIR required", file=sys.stderr)
        return 1
    ok, _message = session_env.validate_design_tmpdir(request.design_tmpdir)
    if not ok:
        return 2
    design_tmpdir = Path(request.design_tmpdir).resolve()
    with contextlib.suppress(FileNotFoundError):
        (design_tmpdir / ".step3-entry-plan-printed").unlink()
    if (design_tmpdir / ".pause-requested").is_file():
        return _call_pause_save(design_tmpdir=design_tmpdir)
    completed = subprocess.run(
        [
            str(larch_entrypoint(request.claude_plugin_root)),
            "plan-review",
            "step3-state",
            "--design-tmpdir",
            str(design_tmpdir),
            "--auto-continuation-entry",
        ],
        check=False,
    )
    rc = completed.returncode
    if rc == 0:
        _maybe_timing_mark(label="design Step 3 — auto-continuation entry")
    return rc


# --- Relocated surviving library helpers from the retired design_terminal.py
# (#8580). The four terminal/failure/summary verbs are Rust-owned in
# crates/larch-cli/src/design_terminal_commands.rs. These pure helpers and the
# three step-final-summary internals stay in Python because still-Python design
# siblings import them in-process (clarify.py, decompose.py, design_postplan.py,
# design_publish.py, design_step5c.py). The step5c-shared internals are a
# ledgered temporary Python survival reconciled at #8586/#8593. ---


def phase_driver_read_result_env(*, path: str | Path, allow_keys: Iterable[str]) -> list[tuple[str, str]]:
    """Read allowlisted KEY=VALUE records from a result-env file.

    Blank and malformed lines are skipped. Values containing CR or LF are
    refused, matching the shell phase-driver trust boundary.
    """
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise OSError(f"result env is not a regular file: {source}")
    allow = set(allow_keys)
    text = source.read_bytes().decode("utf-8", errors="replace")
    clean_lines = [line for line in text.split("\n") if "\r" not in line]
    text = "\n".join(clean_lines)
    rows = larch_io.parse_kv(
        text,
        duplicate_policy="all",
        allowed_keys=allow,
    )
    return [(key, value) for key, values in rows.items() for value in values]


def phase_driver_write_result_env(
    *,
    path: str | Path,
    kvs: Iterable[tuple[str, str] | str],
    allow_keys: Iterable[str] | None = None,
) -> None:
    """Atomically write allowlisted KEY=VALUE records to a result-env file.

    The trust boundary mirrors the shell phase driver: symlink targets are
    refused, keys must be allowlisted shell variable names, and values may not
    contain CR/LF bytes.
    """
    allowed = set(PHASE_RESULT_ENV_ALLOW_KEYS if allow_keys is None else allow_keys)
    dest = Path(path)
    if dest.is_symlink():
        raise OSError(f"refusing to write symlink result env: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, str]] = []
    for item in kvs:
        if isinstance(item, str):
            if "=" not in item:
                raise ValueError(f"result env row is missing '=': {item}")
            key, _, value = item.partition("=")
        else:
            key, value = item
        if key not in allowed or not _valid_var_name(key):
            raise ValueError(f"result env key is not allowlisted: {key}")
        if "\n" in value or "\r" in value:
            raise ValueError(f"result env value contains newline: {key}")
        rows.append((key, value))
    larch_io.atomic_write(
        path=dest,
        text=larch_io.format_kvs(rows),
        create_parent=True,
        nofollow=True,
        mode=0o600,
    )


def clarify_failure_stage_args(
    *, design_tmpdir: Path, exit_code: str, detail_log: Path
) -> list[str]:
    """Return the shared terminal-state argv for a failed clarify loop."""
    return [
        "--design-tmpdir", str(design_tmpdir),
        "--outcome", "failed-clarify",
        "--step", "clarify",
        "--phase", "clarify-loop",
        "--site", "clarify-loop",
        "--trigger", "failed",
        "--bail-reason", "clarify-hard-halt",
        "--exit-code", exit_code,
        "--source-script", "clarify-loop",
        "--summary-outcome", "failed-clarify",
        "--failure-detail-log", str(detail_log),
    ]


def phase_driver_recreate_result_env(*, path: str | Path, design_tmpdir: str | Path) -> None:
    """Recreate a result-env file under a validated design tmpdir.

    This is the safe replacement for shell truncation when a wrapper needs an
    empty merge-input env: the destination must stay under DESIGN_TMPDIR, must
    not be a symlink, and is recreated through the atomic nofollow writer.
    """
    dest = Path(path)
    root = Path(design_tmpdir)
    if root.is_symlink() or not root.is_dir():
        raise OSError(f"design tmpdir is not a regular directory: {root}")
    resolved_root = root.resolve()
    if dest.is_symlink():
        raise OSError(f"refusing to replace symlink result env: {dest}")
    try:
        resolved_dest = dest.resolve(strict=False)
    except OSError as exc:
        raise OSError(f"result env cannot be resolved: {dest}") from exc
    if resolved_dest != resolved_root and resolved_root not in resolved_dest.parents:
        raise OSError(f"result env escapes DESIGN_TMPDIR: {dest}")
    phase_driver_write_result_env(path=dest, kvs=[])


def extend_publish_failure_stage_args(stage_args: list[str], values: Mapping[str, str]) -> None:
    """Append optional publish state to a terminal-stage command."""
    for flag, key in (
        ("--publish-attempt-id", "PUBLISH_ATTEMPT_ID"),
        ("--publish-rc-source", "PUBLISH_RC_SOURCE"),
        ("--latest-phase", "LATEST_PHASE"),
        ("--plan-write-ok", "PLAN_WRITE_OK"),
        ("--publish-ok", "PUBLISH_OK"),
        ("--renamed", "RENAMED"),
        ("--log-publish-attempted", "LOG_PUBLISH_ATTEMPTED"),
        ("--log-publish-completed", "LOG_PUBLISH_COMPLETED"),
        ("--designed-admission-ready", "DESIGNED_ADMISSION_READY"),
        ("--pr-url", "PR_URL"),
        ("--recovery-branch", "RECOVERY_BRANCH"),
    ):
        value = values.get(key, "")
        if value:
            stage_args.extend((flag, value))


def _final_summary_stream():
    return logging_util.contract_stream()


def _final_summary_ready_rows(*, final_summary_path: Path) -> list[tuple[str, str]]:
    return [
        (config.ENV_FINAL_SUMMARY_PATH, str(final_summary_path)),
        (config.ENV_FINAL_SUMMARY_READY, "true"),
    ]


def _has_nonempty_final_summary(path: Path) -> bool:
    return not path.is_symlink() and path.is_file() and path.stat().st_size > 0


def _parse_contract_value(text: str, key: str) -> str:
    return larch_io.kv_value(text=text, key=key, duplicate_policy="last")


def _upsert_final_summary_ready_into_merge_env(
    *,
    design_tmpdir: Path,
    merge_env: Path,
    final_summary_path: Path,
) -> None:
    """Merge FINAL_SUMMARY_PATH/READY into a caller-owned merge env for bgjob DONE."""
    if merge_env.is_symlink() or not merge_env.is_file():
        return
    existing = larch_io.read_kvs(merge_env, duplicate_policy="last", reject_symlink=True)
    merged: list[tuple[str, str]] = []
    for key, value in existing.items():
        if key in {config.ENV_FINAL_SUMMARY_PATH, config.ENV_FINAL_SUMMARY_READY}:
            continue
        merged.append((key, value))
    merged.extend(_final_summary_ready_rows(final_summary_path=final_summary_path))
    design_write_merge_env(path=merge_env, design_tmpdir=design_tmpdir, rows=merged)


def _persist_final_summary_readiness(
    *,
    design_tmpdir: Path,
    final_summary_path: str,
    merge_env: Path | None = None,
) -> None:
    """Write readiness KVs into merge envs that bgjob wait promotes into DONE/result.env."""
    summary_path = Path(final_summary_path)
    if not _has_nonempty_final_summary(summary_path):
        return
    design_write_merge_env(
        path=design_tmpdir / ".design-step-final-summary-result.env",
        design_tmpdir=design_tmpdir,
        rows=_final_summary_ready_rows(final_summary_path=summary_path),
    )
    if merge_env is not None:
        _upsert_final_summary_ready_into_merge_env(
            design_tmpdir=design_tmpdir,
            merge_env=merge_env,
            final_summary_path=summary_path,
        )


def _emit_final_summary_marked_from_disk(
    *,
    design_tmpdir: Path,
    final_summary_path: str,
    merge_env: Path | None = None,
) -> None:
    summary_path = Path(final_summary_path)
    if not summary_path.is_file() or summary_path.stat().st_size == 0:
        return
    stream = _final_summary_stream()
    logging_util.emit_kv(key=config.ENV_FINAL_SUMMARY_PATH, value=str(summary_path))
    stream.write(f"{config.LARCH_FINAL_SUMMARY_BEGIN_MARKER}\n")
    stream.write(f"{config.LARCH_FINAL_SUMMARY_END_MARKER}\n")
    stream.flush()
    # Contract-stream markers are not merged into bgjob DONE/result.env (#8462).
    # Persist an equivalent readiness KV into the step merge envs that are.
    _persist_final_summary_readiness(
        design_tmpdir=design_tmpdir,
        final_summary_path=str(summary_path),
        merge_env=merge_env,
    )


def _emit_report_gate_sidecars_from_disk(design_tmpdir: Path) -> None:
    handoff = design_tmpdir / "design-report-gate-sidecars.md"
    sidecars = (design_tmpdir / "design-failure-chat-print.md", design_tmpdir / "design-failure-operator-action-chat.md")
    chunks = [sidecar.read_text(encoding="utf-8", errors="replace") for sidecar in sidecars if sidecar.is_file() and sidecar.stat().st_size > 0]
    handoff.write_text(("\n".join(chunks).rstrip("\n") + "\n") if chunks else "", encoding="utf-8")
    if handoff.stat().st_size > 0:
        logging_util.emit_kv(key="REPORT_GATE_SIDECARS_FILE", value=str(handoff))


def _publish_terminal_final_summary(
    *,
    design_tmpdir: Path,
    run_id: str,
    issue: str,
    outcome: str,
    repo: str = "",
) -> tuple[int, bool]:
    plugin_root = Path(os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, Path(__file__).resolve().parents[3]))
    args = [
        str(larch_entrypoint(plugin_root)),
        "design",
        "log-publish",
        "--design-tmpdir",
        str(design_tmpdir),
        "--run-id",
        run_id,
        "--issue",
        issue,
        "--outcome",
        outcome,
    ]
    if repo:
        args.extend(["--repo", repo])
    stdout_log = design_tmpdir / "design-log-publish.terminal.stdout.log"
    stderr_log = design_tmpdir / "design-log-publish.terminal.stderr.log"
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    _ = stdout_log.write_text(completed.stdout, encoding="utf-8")
    _ = stderr_log.write_text(completed.stderr, encoding="utf-8")
    rc = int(completed.returncode)
    publish_ok = _parse_contract_value(completed.stdout, "PUBLISH_OK")
    recovery_branch = _parse_contract_value(completed.stdout, "RECOVERY_BRANCH")
    return rc, rc == 0 and publish_ok == "true" and not recovery_branch

def _read_review_round_count(design_tmpdir: Path) -> int:
    """Return the launched-round count from review-round-count.txt (0 if absent/invalid).

    Mirrors plan_review._read_count. Used as a defense-in-depth fallback by
    review_provenance when a result-env writer omits the round-count keys (#5210).
    """
    path = design_tmpdir / "review-round-count.txt"
    if not path.is_file() or path.is_symlink():
        return 0
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return 0
    return int(raw, 10) if re.fullmatch(r"[0-9]+", raw) else 0


def review_provenance(design_tmpdir: Path) -> tuple[str, int, bool]:
    """Return (review_status, rounds_completed, provenance_present) from .step3-review-result.env."""
    result_env = design_tmpdir / ".step3-review-result.env"
    if not result_env.is_file() or result_env.is_symlink():
        return "", 0, False
    kv = larch_io.read_kvs(
        result_env,
        duplicate_policy="last",
        errors="replace",
    )
    status = kv.get("STEP3_REVIEW_LOOP_STATUS", "")
    if not status:
        loop = kv.get("LOOP_STATUS", "")
        tally = kv.get("TALLY_PLAN_REVIEW_STATUS", "")
        if loop == "complete":
            status = "complete"
        elif loop in {"cap-reached", "cap-hit"}:
            status = "cap-hit"
        elif loop in {
            "panel-failed", "panel-init-failed", "panel-skipped",
            "tally-error", "degraded-empty-collector",
            "main-agent-vote-required", "postplan-failed",
        }:
            status = loop
        elif tally:
            status = tally
    rounds_raw = kv.get("ROUNDS_COMPLETED", "") or kv.get("REVIEW_ROUND_COUNT", "")
    try:
        rounds = int(rounds_raw) if rounds_raw.strip().isdigit() else 0
    except (ValueError, AttributeError):
        rounds = 0
    if not rounds_raw.strip():
        # #5210 defense-in-depth: when a result-env writer omits both ROUNDS_COMPLETED
        # and REVIEW_ROUND_COUNT, recover the launched-round count from the durable
        # review-round-count.txt so a cleanly-reviewed plan is not refused as rounds=0.
        rounds = _read_review_round_count(design_tmpdir)
    provenance_present = bool(status or rounds_raw.strip())
    return status, rounds, provenance_present
