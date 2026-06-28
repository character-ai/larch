# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportPrivateUsage=false
"""Cursor auth, probe helpers, reviewer check, and degraded tools."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from larch.core import config
from larch.core.ctx import Ctx
from larch.core import logging_util

from larch.agents._types import (
    _AUTH_RETRY_RC,
    _PROBE_NO_RETRY_RC,
    _CURSOR_PREFLIGHT_AUTH_RC,
    _CURSOR_AUTH_MAX_ATTEMPTS,
    CURSOR_PREREAD_FAIL_MSG,
    AuthVerdict,
    CheckReviewersResult,
    DegradedToolsResult,
    _err,
    _emit,
    _emit_kv,
    _write,
    _append,
    _plugin_root,
    _env_int,
)
from larch.agents._launch_failure import (
    resolve_model_args,
)
from larch.agents._run_external import (
    external_startup_lock_acquire,
    external_startup_lock_release_after,
    external_auth_verdict,
    _codex_auth_args,
    _codex_env_key_enabled,
    _trust_config_arg,
    _resolve_review_codex_workdir,
    _prepare_codex_home,
)

def cursor_auth_preflight(*, caller: str = "agent cursor-auth-preflight") -> AuthVerdict:
    raw_key = os.environ.get("CURSOR_API_KEY", "")
    key = raw_key.strip()
    if not key or "\n" in raw_key or "\r" in raw_key:
        os.environ.pop("CURSOR_API_KEY", None)
    if "\n" in raw_key or "\r" in raw_key:
        key = ""
    if key:
        os.environ["CURSOR_API_KEY"] = key
        return AuthVerdict(ok=True, rc=0)
    uname_out = os.environ.get("LIB_CURSOR_AUTH_TEST_UNAME", "") if os.environ.get("LARCH_LIB_CURSOR_AUTH_TEST_MODE") == "1" else ""
    if not uname_out:
        uname_out = platform.system() or "unknown"
    if uname_out != "Darwin":
        return AuthVerdict(ok=True, rc=0)

    seq = os.environ.get("LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ", "") if os.environ.get("LARCH_LIB_CURSOR_AUTH_TEST_MODE") == "1" else ""
    seq_values = seq.split(",") if seq else []
    test_rc = os.environ.get("LIB_CURSOR_AUTH_TEST_SECURITY_RC", "") if os.environ.get("LARCH_LIB_CURSOR_AUTH_TEST_MODE") == "1" else ""
    last_rc = seq_values[-1] if seq_values else test_rc
    state = external_startup_lock_acquire(tool="cursor")
    try:
        for attempt in range(_CURSOR_AUTH_MAX_ATTEMPTS):
            token = ""
            if seq_values:
                rc_text = seq_values[attempt] if attempt < len(seq_values) else last_rc
                rc = int(rc_text or "1")
                if rc == 0:
                    token = os.environ.get("LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN", "").strip()
            elif test_rc:
                rc = int(test_rc)
                if rc == 0:
                    token = os.environ.get("LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN", "").strip()
            else:
                # Probe readability with -w, not just existence (#5518): on macOS an
                # access-controlled keychain entry can pass an existence check yet deny
                # the -w read without UI interaction, so an existence-only preflight
                # reports green while Cursor's own in-process read fails (exit 1, 0 bytes).
                # Reading here makes the preflight fail closed when the token is present
                # but unreadable. Require a non-empty stripped token, not just exit 0.
                result = subprocess.run(
                    [shutil.which("security") or "/usr/bin/security", "find-generic-password", "-a", "cursor-user", "-s", "cursor-access-token", "-w"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                rc = result.returncode
                token = result.stdout.strip() if rc == 0 else ""
            if rc == 0 and token:
                return AuthVerdict(ok=True, rc=0)
            if attempt < _CURSOR_AUTH_MAX_ATTEMPTS - 1:
                time.sleep(0.2)
    finally:
        external_startup_lock_release_after(state=state, delay=0)
    msg = (
        f"{caller}: cursor-auth-preflight failed.\n"
        "  CURSOR_API_KEY is unset/empty AND the `cursor-user` / `cursor-access-token`\n"
        "  keychain entry is missing or unreadable (-w denied) on this Darwin host.\n"
        "  Cursor would otherwise emit the cryptic `Security process exited with code: 45`.\n\n"
        "  See docs/installation-and-setup.md (Cursor section) for setup.\n\n"
        "  To fix, choose one:\n"
        "    (a) export CURSOR_API_KEY=<your-cursor-api-key>\n"
        "    (b) security delete-generic-password -a cursor-user 2>/dev/null; cursor login"
    )
    return AuthVerdict(ok=False, rc=2, message=msg)


def cursor_preread_service_token() -> bool:
    raw_key = os.environ.get("CURSOR_API_KEY", "")
    key = raw_key.strip()
    if key and "\n" not in raw_key and "\r" not in raw_key:
        return True
    uname_out = os.environ.get("LIB_CURSOR_AUTH_TEST_UNAME", "") if os.environ.get("LARCH_LIB_CURSOR_AUTH_TEST_MODE") == "1" else ""
    if not uname_out:
        uname_out = platform.system() or "unknown"
    if uname_out != "Darwin":
        return True
    state = external_startup_lock_acquire(tool="cursor")
    read_failed = False
    token = ""
    try:
        if os.environ.get("LARCH_LIB_CURSOR_AUTH_TEST_MODE") == "1":
            token = os.environ.get("LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN", "").strip()
            read_failed = not token
        else:
            result = subprocess.run(
                [shutil.which("security") or "/usr/bin/security", "find-generic-password", "-a", "cursor-user", "-s", "cursor-access-token", "-w"],
                capture_output=True,
                text=True,
                check=False,
            )
            token = result.stdout.strip() if result.returncode == 0 else ""
            read_failed = result.returncode != 0 or not token
    finally:
        external_startup_lock_release_after(state=state, delay=0)
    if token:
        os.environ["CURSOR_API_KEY"] = token
        return True
    if read_failed:
        # Surface the silent token-read drop (#5518) instead of proceeding with an empty
        # CURSOR_API_KEY: the entry may exist (so the old existence-only preflight passed)
        # while the -w read is denied, which lets the Cursor slot auth-fail in-process and
        # return a canned, un-reviewed response that the panel scores as clean.
        _err(CURSOR_PREREAD_FAIL_MSG)
    return False


def cursor_auth_export_env() -> None:
    # Suppress cursor-agent's deeplink/browser opener (`open <cursor://…>`) so it
    # never launches the Cursor.app "Composer" GUI window in headless larch lanes
    # (issue #5797). All cursor lanes call this pre-spawn and the child inherits
    # os.environ, so this single assignment covers every cursor subprocess.
    os.environ["NO_OPEN_BROWSER"] = "1"
    raw_key = os.environ.get("CURSOR_API_KEY", "")
    key = raw_key.strip()
    if "\n" in key or "\r" in key:
        os.environ.pop("CURSOR_API_KEY", None)
    elif key:
        os.environ["CURSOR_API_KEY"] = key
    else:
        os.environ.pop("CURSOR_API_KEY", None)


def cursor_auth_preflight_main(argv: list[str] | None = None) -> int:
    _ = argv
    logging_util.quiet_init(argv0="cli.py")
    verdict = cursor_auth_preflight()
    if not verdict.ok:
        _err(verdict.message)
    return verdict.rc


def cursor_wrap_prompt_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        _err("agent cursor-wrap-prompt: a single prompt argument is required")
        return 1
    stream = logging_util.contract_stream()
    _ = stream.write(f" /max-mode on. Prompt: {args[0]}")
    stream.flush()
    return 0




def _max_transient_probe_retries(max_auth_retries: int) -> int:
    if "LARCH_PROBE_RETRIES" in os.environ:
        return _env_int(name="LARCH_PROBE_RETRIES", default=2)
    if max_auth_retries == 1:
        return 0
    return 2


def _max_timeout_probe_retries() -> int:
    return _env_int(name="LARCH_PROBE_TIMEOUT_RETRIES", default=0)


def _probe_tmpdir() -> Path:
    return Path(os.environ.get("TMPDIR") or "/tmp")  # noqa: S108 - parity with Bash TMPDIR fallback.


def _probe_user() -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "", os.environ.get("USER", ""))
    return sanitized or "larch"


def _probe_stamp_path(kind: str) -> Path:
    return _probe_tmpdir() / f"larch-{kind}-present-{_probe_user()}.stamp"


def _codex_probe_stamp_kind() -> str:
    return "codex-env-key" if _codex_env_key_enabled() else "codex-login"


def _read_fresh_probe_stamp(*, stamp: Path, ttl: int, negative_ttl: int) -> bool | None:
    if ttl <= 0:
        return None
    try:
        stat = stamp.stat()
    except OSError:
        return None
    now = time.time()
    age = now - stat.st_mtime
    if age < 0 or age > ttl:
        return None
    try:
        line = stamp.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return None
    value = line.replace("\r", "")
    if value == "true":
        return True
    if value == "false" and negative_ttl > 0 and age <= negative_ttl:
        return False
    return None


def _write_probe_stamp(*, stamp: Path, value: bool) -> None:
    try:
        stamp.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=str(stamp.parent),
            prefix="larch-probe-stamp.",
        ) as handle:
            handle.write(f"{str(value).lower()}\n")
            tmp = Path(handle.name)
        tmp.replace(stamp)
    except OSError:
        with contextlib.suppress(NameError, OSError):
            tmp.unlink()  # type: ignore[name-defined]


@contextlib.contextmanager
def _temporary_environ(updates: dict[str, str] | None = None):
    old = os.environ.copy()
    if updates:
        os.environ.clear()
        os.environ.update(updates)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old)


def _run_probe_command(cmd: Sequence[str], *, timeout: int, env: dict[str, str], stdout: Path | None = None, stderr: Path | None = None, input_text: str | None = None) -> int:
    try:
        with contextlib.ExitStack() as stack:
            stdout_target: object = subprocess.DEVNULL
            stderr_target: object = subprocess.DEVNULL
            if stdout is not None:
                stdout_target = stack.enter_context(stdout.open("wb"))
            if stderr is not None:
                if stdout is not None and stderr == stdout:
                    stderr_target = subprocess.STDOUT
                else:
                    stderr_target = stack.enter_context(stderr.open("wb"))
            result = subprocess.run(
                list(cmd),
                input=input_text,
                stdout=stdout_target,
                stderr=stderr_target,
                timeout=timeout,
                env=env,
                text=input_text is not None,
                check=False,
            )
        return result.returncode
    except FileNotFoundError:
        return 127
    except subprocess.TimeoutExpired:
        return config.EXIT_TIMEOUT


@dataclass(frozen=True)
class _CursorProbeSetup:
    cfg_tmp: Path
    old_cfg: str | None


def _cursor_probe_setup_chain() -> _CursorProbeSetup | None:
    try:
        if not cursor_preread_service_token():
            return None
        cursor_auth_export_env()
        cfg_tmp = Path(tempfile.mkdtemp(prefix="larch-cursor-cfg-", dir=str(_probe_tmpdir())))
    except OSError:
        return None
    old_cfg = os.environ.get("CURSOR_CONFIG_DIR")
    os.environ["CURSOR_CONFIG_DIR"] = str(cfg_tmp)
    user_cfg = Path.home() / ".cursor" / "cli-config.json"
    if user_cfg.is_file():
        with contextlib.suppress(OSError):
            shutil.copyfile(user_cfg, cfg_tmp / "cli-config.json")
    return _CursorProbeSetup(cfg_tmp=cfg_tmp, old_cfg=old_cfg)


def _cursor_probe_cleanup_private_config_dir(setup: _CursorProbeSetup | None) -> None:
    if setup is None:
        return
    shutil.rmtree(setup.cfg_tmp, ignore_errors=True)
    if setup.old_cfg is None:
        os.environ.pop("CURSOR_CONFIG_DIR", None)
    else:
        os.environ["CURSOR_CONFIG_DIR"] = setup.old_cfg


def _run_one_cursor_probe(timeout: int) -> int:
    probe_out: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=str(_probe_tmpdir()), prefix="larch-cursor-probe.") as handle:
            probe_out = Path(handle.name)
        try:
            model_args = list(resolve_model_args("cursor").argv)
        except ValueError:
            model_args = []
        prompt = " /max-mode on. Prompt: Respond with OK"
        state = external_startup_lock_acquire(tool="cursor")
        external_startup_lock_release_after(state=state)
        probe_workdir = _resolve_review_codex_workdir(str(Path.cwd()))
        rc = _run_probe_command(
            ["cursor", "agent", "-p", prompt, "--trust", "--workspace", probe_workdir, *model_args],
            timeout=timeout,
            env=dict(os.environ),
            stdout=probe_out,
            stderr=probe_out,
        )
        if rc == config.EXIT_TIMEOUT:
            return config.EXIT_TIMEOUT
        if rc == 0:
            return 0
        if external_auth_verdict("cursor", probe_out) == "auth":
            return _AUTH_RETRY_RC
        return 1
    finally:
        if probe_out is not None:
            with contextlib.suppress(OSError):
                probe_out.unlink()


def _run_one_codex_probe(timeout: int) -> int:
    probe_out: Path | None = None
    probe_side: Path | None = None
    codex_home: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=str(_probe_tmpdir()), prefix="larch-codex-probe.") as handle:
            probe_out = Path(handle.name)
        probe_side = Path(str(probe_out) + ".sidecar")
        _write(path=probe_side, text="")
        codex_home = Path(tempfile.mkdtemp(prefix="larch-codex-probe-home-", dir=str(_probe_tmpdir())))
        prep_rc, prep_msg = _prepare_codex_home(codex_home)
        if prep_rc != 0:
            if prep_msg:
                _append(path=probe_side, text=prep_msg + "\n")
            if _codex_env_key_enabled():
                _err("agent check-reviewers: Codex OPENAI_API_KEY auth setup failed")
            return _PROBE_NO_RETRY_RC
        try:
            model_args = list(resolve_model_args("codex", with_effort=True, codex_role="review").argv)
        except ValueError as exc:
            _append(path=probe_side, text=f"model args failed: {exc}\n")
            return _PROBE_NO_RETRY_RC
        probe_workdir = _resolve_review_codex_workdir(str(Path.cwd()))
        cmd = [
            "codex",
            "exec",
            "--sandbox",
            "read-only",
            "-C",
            probe_workdir,
            *model_args,
            "-c",
            _trust_config_arg(probe_workdir),
            *_codex_auth_args(),
            "--output-last-message",
            str(probe_out),
            "--",
            "Respond with OK",
        ]
        env: dict[str, str] = dict(os.environ)
        env["CODEX_HOME"] = str(codex_home)
        state = external_startup_lock_acquire(tool="codex")
        external_startup_lock_release_after(state=state)
        rc = _run_probe_command(cmd, timeout=timeout, env=env, stderr=probe_side)
        if rc == config.EXIT_TIMEOUT:
            return config.EXIT_TIMEOUT
        if rc == 0:
            return 0
        if external_auth_verdict("codex", probe_out, probe_side) == "auth":
            return _AUTH_RETRY_RC
        return 1
    finally:
        if codex_home is not None:
            shutil.rmtree(codex_home, ignore_errors=True)
        for path in (probe_out, probe_side):
            if path is not None:
                with contextlib.suppress(OSError):
                    path.unlink()


def _run_codex_probes(*, max_auth_retries: int, max_transient_retries: int, max_timeout_retries: int, timeout: int) -> tuple[bool, bool]:
    auth_failures = 0
    transient_retries_used = 0
    timeout_retries_used = 0
    while True:
        rc = _run_one_codex_probe(timeout)
        if rc == config.EXIT_TIMEOUT:
            if timeout_retries_used < max_timeout_retries:
                timeout_retries_used += 1
                continue
            return False, True
        if rc == 0:
            return True, False
        if rc == _PROBE_NO_RETRY_RC:
            return False, False
        if rc == _AUTH_RETRY_RC:
            auth_failures += 1
            if auth_failures >= max(max_auth_retries, 1):
                return False, False
            continue
        if rc == 1:
            if transient_retries_used >= max_transient_retries:
                return False, False
            transient_retries_used += 1
            continue
        return False, False


def _run_cursor_probes(*, max_auth_retries: int, max_transient_retries: int, max_timeout_retries: int, timeout: int) -> tuple[bool, bool]:
    setup = _cursor_probe_setup_chain()
    if setup is None:
        return False, False
    try:
        auth_failures = 0
        transient_retries_used = 0
        timeout_retries_used = 0
        while True:
            rc = _run_one_cursor_probe(timeout)
            if rc == config.EXIT_TIMEOUT:
                if timeout_retries_used < max_timeout_retries:
                    timeout_retries_used += 1
                    continue
                return False, True
            if rc == 0:
                return True, False
            if rc == _PROBE_NO_RETRY_RC:
                return False, False
            if rc == _AUTH_RETRY_RC:
                auth_failures += 1
                if auth_failures >= max(max_auth_retries, 1):
                    return False, False
                continue
            if rc == 1:
                if transient_retries_used >= max_transient_retries:
                    return False, False
                transient_retries_used += 1
                continue
            return False, False
    finally:
        _cursor_probe_cleanup_private_config_dir(setup)


def check_reviewers(
    *,
    skip_codex_probe: bool = False,
    skip_cursor_probe: bool = False,
    probe_timeout_seconds: int | None = None,
    env: dict[str, str] | None = None,
) -> CheckReviewersResult:
    with _temporary_environ(env):
        ttl = _env_int(name="LARCH_PROBE_TTL_SECONDS", default=60)
        negative_ttl = _env_int(name="LARCH_PROBE_NEGATIVE_TTL_SECONDS", default=0)
        # The 60s probe timeout is intentional to avoid degraded-tools false
        # negatives from slow probes; timeout retries default to 0.
        timeout = probe_timeout_seconds or _env_int(name="LARCH_PROBE_TIMEOUT_SECONDS", default=60, zero_allowed=False)
        max_auth_retries = _env_int(name="LARCH_EXTERNAL_AUTH_RETRIES", default=5, zero_allowed=False)
        max_transient_retries = _max_transient_probe_retries(max_auth_retries)
        max_timeout_retries = _max_timeout_probe_retries()

        codex_binary_found = shutil.which("codex") is not None
        cursor_binary_found = shutil.which("cursor") is not None
        codex_present = False
        cursor_present = False
        codex_probe_timed_out = False
        cursor_probe_timed_out = False

        if cursor_binary_found and not skip_cursor_probe:
            cached = _read_fresh_probe_stamp(stamp=_probe_stamp_path("cursor"), ttl=ttl, negative_ttl=negative_ttl)
            if cached is not None:
                cursor_present = cached
            else:
                preflight = cursor_auth_preflight(caller="agent check-reviewers")
                cursor_auth_retries = 1 if preflight.rc == _CURSOR_PREFLIGHT_AUTH_RC else max_auth_retries
                cursor_transient_retries = 0 if preflight.rc == _CURSOR_PREFLIGHT_AUTH_RC else max_transient_retries
                cursor_present, cursor_probe_timed_out = _run_cursor_probes(
                    max_auth_retries=cursor_auth_retries,
                    max_transient_retries=cursor_transient_retries,
                    max_timeout_retries=max_timeout_retries,
                    timeout=timeout,
                )
                _write_probe_stamp(stamp=_probe_stamp_path("cursor"), value=cursor_present)

        if codex_binary_found and not skip_codex_probe:
            stamp = _probe_stamp_path(_codex_probe_stamp_kind())
            cached = _read_fresh_probe_stamp(stamp=stamp, ttl=ttl, negative_ttl=negative_ttl)
            if cached is not None:
                codex_present = cached
            else:
                codex_present, codex_probe_timed_out = _run_codex_probes(
                    max_auth_retries=max_auth_retries,
                    max_transient_retries=max_transient_retries,
                    max_timeout_retries=max_timeout_retries,
                    timeout=timeout,
                )
                _write_probe_stamp(stamp=stamp, value=codex_present)

        return CheckReviewersResult(
            codex_binary_found=codex_binary_found,
            cursor_binary_found=cursor_binary_found,
            codex_present=codex_present,
            cursor_present=cursor_present,
            codex_probe_timed_out=codex_probe_timed_out,
            cursor_probe_timed_out=cursor_probe_timed_out,
        )


def check_reviewers_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py agent check-reviewers")
    parser.add_argument("--skip-codex-probe", action="store_true")
    parser.add_argument("--skip-cursor-probe", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 1
    result = check_reviewers(
        skip_codex_probe=args.skip_codex_probe,
        skip_cursor_probe=args.skip_cursor_probe,
    )
    for line in result.kv_lines():
        _emit(line)
    return 0


EXTERNAL_TOOL_NAMES: tuple[str, ...] = ("codex", "cursor")


def external_tool_names() -> tuple[str, ...]:
    return EXTERNAL_TOOL_NAMES


def external_tool_registry_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py agent external-tool-registry")
    parser.add_argument("--kind", choices=("external-tools", "implementer-coders", "kv"), default="kv")
    args = parser.parse_args(argv)
    if args.kind == "external-tools":
        for tool in EXTERNAL_TOOL_NAMES:
            _emit(tool)
    elif args.kind == "implementer-coders":
        _emit("claude")
        for tool in EXTERNAL_TOOL_NAMES:
            _emit(tool)
    else:
        _emit_kv(key="EXTERNAL_TOOLS", value=",".join(EXTERNAL_TOOL_NAMES))
        _emit_kv(key="IMPLEMENTER_CODERS", value="claude,codex,cursor")
    return 0


def _norm_bool(value: str) -> str:
    return "true" if value == "true" else "false"


def _norm_tristate(value: str) -> str:
    return value if value in {"true", "false"} else "unknown"


def _tool_state(*, binary_found: str, present: str) -> str:
    if binary_found == "false":
        return "binary-missing"
    if present == "true":
        return "ok"
    if binary_found == "true":
        return "probe-failed"
    return "unavailable"


def _state_phrase(state: str) -> str:
    return {
        "ok": "available",
        "binary-missing": "UNAVAILABLE — CLI binary not found on PATH",
        "probe-failed": "UNAVAILABLE — runtime health probe failed (binary present but the auth/quota check did not pass)",
        "unavailable": "UNAVAILABLE — session health probe did not pass",
    }.get(state, "unknown")


def degraded_tools_result(
    *,
    codex_binary_found: str,
    codex_present: str,
    cursor_binary_found: str,
    cursor_present: str,
    skill: str,
) -> DegradedToolsResult:
    presence_empty = not codex_present or not cursor_present
    c_b = _norm_tristate(codex_binary_found)
    c_p = _norm_bool(codex_present)
    u_b = _norm_tristate(cursor_binary_found)
    u_p = _norm_bool(cursor_present)
    codex_state = _tool_state(binary_found=c_b, present=c_p)
    cursor_state = _tool_state(binary_found=u_b, present=u_p)
    degraded = codex_state != "ok" or cursor_state != "ok"
    both_down = codex_state != "ok" and cursor_state != "ok"
    explanation: list[str] = []
    if degraded:
        explanation.extend(
            [
                f"⚠ Degraded external-tool availability for this /{skill} run:",
                "",
                f"  • Codex:  {_state_phrase(codex_state)}",
                f"  • Cursor: {_state_phrase(cursor_state)}",
                "",
            ]
        )
        explanation.extend(
            [
                "Step 0 uses this health probe only as an operator-safety gate.",
                "Later vendor calls do not route from this probe result; they use binary",
                "presence, launcher-owned retries, and existing fallback/degradation paths.",
                "",
            ]
        )
        if both_down:
            explanation.extend([
                "Both external vendors are unavailable. This run cannot continue.",
                "Fix at least one vendor or retry after the outage clears.",
            ])
        else:
            explanation.extend([
                "Exactly one external vendor is unavailable. Explicit operator confirmation",
                "is required before continuing with reduced model-family diversity.",
            ])
    return DegradedToolsResult(degraded, codex_state, cursor_state, both_down, presence_empty, tuple(explanation))


def degraded_tools_gate_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py agent degraded-tools-gate")
    parser.add_argument("--codex-binary-found", default=os.environ.get(config.ENV_CODEX_BINARY_FOUND, "unknown"))
    parser.add_argument("--codex-present", default=os.environ.get(config.ENV_CODEX_PRESENT, ""))
    parser.add_argument("--cursor-binary-found", default=os.environ.get(config.ENV_CURSOR_BINARY_FOUND, "unknown"))
    parser.add_argument("--cursor-present", default=os.environ.get(config.ENV_CURSOR_PRESENT, ""))
    parser.add_argument("--skill", default="this")
    args = parser.parse_args(argv)
    ctx = Ctx.from_mapping({
        **os.environ,
        config.ENV_CODEX_BINARY_FOUND: args.codex_binary_found,
        config.ENV_CODEX_PRESENT: args.codex_present,
        config.ENV_CURSOR_BINARY_FOUND: args.cursor_binary_found,
        config.ENV_CURSOR_PRESENT: args.cursor_present,
        "skill": args.skill,
    })
    if not ctx.codex_present:
        _err("agent degraded-tools-gate: ERROR: --codex-present resolved empty (caller rehydration bug — read presence keys from the durable session-env file, not ambient shell state); treating as down (fail-safe)")
    if not ctx.cursor_present:
        _err("agent degraded-tools-gate: ERROR: --cursor-present resolved empty (caller rehydration bug — read presence keys from the durable session-env file, not ambient shell state); treating as down (fail-safe)")
    result = degraded_tools_result(
        codex_binary_found=ctx.codex_binary_found,
        codex_present=ctx.codex_present,
        cursor_binary_found=ctx.cursor_binary_found,
        cursor_present=ctx.cursor_present,
        skill=ctx.str_value(key="skill", default="this"),
    )
    _emit_kv(key="DEGRADED", value=str(result.degraded).lower())
    _emit_kv(key="CODEX_STATE", value=result.codex_state)
    _emit_kv(key="CURSOR_STATE", value=result.cursor_state)
    _emit_kv(key="BOTH_DOWN", value=str(result.both_down).lower())
    if result.both_down:
        _emit_kv(key="DEGRADED_HARD_FAIL", value="true")
    if result.presence_input_empty:
        _emit_kv(key="PRESENCE_INPUT_EMPTY", value="true")
    if result.degraded:
        _emit("DEGRADED_EXPLANATION_BEGIN")
        for line in result.explanation:
            _emit(line)
        _emit("DEGRADED_EXPLANATION_END")
    return 0


def _read_plugin_version_best_effort() -> str:
    root = _plugin_root()
    try:
        parsed: object = json.loads((root / config.PLUGIN_JSON_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    if isinstance(parsed, dict):
        value = parsed.get("version")
        if value is not None:
            version = str(value).splitlines()[0].strip("\r")
            if version and version != "null":
                return version
    return "unknown"


def status_check_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py status check")
    try:
        parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    version = _read_plugin_version_best_effort()
    try:
        reviewer_result = check_reviewers()
    except Exception:  # pylint: disable=broad-except
        reviewer_result = CheckReviewersResult(
            codex_binary_found=False,
            cursor_binary_found=False,
            codex_present=False,
            cursor_present=False,
        )
    codex_binary_found = str(reviewer_result.codex_binary_found).lower()
    cursor_binary_found = str(reviewer_result.cursor_binary_found).lower()
    codex_present = str(reviewer_result.codex_present).lower()
    cursor_present = str(reviewer_result.cursor_present).lower()
    degraded = degraded_tools_result(
        codex_binary_found=codex_binary_found,
        codex_present=codex_present,
        cursor_binary_found=cursor_binary_found,
        cursor_present=cursor_present,
        skill="status",
    )
    _emit_kv(key="LARCH_PLUGIN_VERSION", value=version)
    _emit_kv(key="CODEX_BINARY_FOUND", value=codex_binary_found)
    _emit_kv(key="CURSOR_BINARY_FOUND", value=cursor_binary_found)
    _emit_kv(key="CODEX_PRESENT", value=codex_present)
    _emit_kv(key="CURSOR_PRESENT", value=cursor_present)
    _emit_kv(key="CODEX_STATE", value=degraded.codex_state)
    _emit_kv(key="CURSOR_STATE", value=degraded.cursor_state)
    _emit_kv(key="DEGRADED", value=str(degraded.degraded).lower())
    return 0
