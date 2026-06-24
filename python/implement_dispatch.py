# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""/implement Step 2 dispatch, recovery paths, and Step 4 commit helpers."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import file_oos
import issue_wire
import larch_io
import logging_util
import oos_filer
import phantom
import proc
import redact
import ship

_PLUGIN_ROOT = Path(__file__).resolve().parents[1]
_SAFE_CODERS = {"claude", "codex", "cursor"}
WRAPPER_VALIDATION_RC = 2
RESUME_CAP = 5
SUMMARY_BULLETS_MAX = 5
PORCELAIN_MIN_PARTS = 2
GIT_BIN = shutil.which("git") or "git"
TIMING_LEDGER_MIN_COLUMNS = 7
SHIP_ROUTE_EXIT_NEEDS_USER = 3
SHIP_ROUTE_EXIT_STALLED = 4
SHIP_ROUTE_EXIT_TRANSIENT = 6
SHIP_ROUTE_TRANSIENT_STALL_RETRY = 4
SHIP_ROUTE_DETAIL_FILE_MAX = 300


def _err(message: str) -> None:
    logging_util.diagnostic(message)


def _emit_kv(key: str, value: str | int) -> None:
    logging_util.emit_kv(key, str(value))


def _run(argv: Sequence[str], *, cwd: str | Path | None = None, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        cwd=str(cwd) if cwd is not None else None,
        text=True,
        capture_output=True,
        check=False,
        **kwargs,
    )


def _git(repo: Path, *args: str, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        [GIT_BIN, "-C", str(repo), *args],
        capture_output=True,
        text=not binary,
        check=False,
    )


def _git_stdout(repo: Path, *args: str) -> str:
    result = _git(repo, *args)
    if result.returncode != 0:
        return ""
    return result.stdout.rstrip("\n")


def _write_text_atomic(path: Path, text: str) -> None:
    larch_io.atomic_write(path, text, temp_name=f"{path.name}.tmp")


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def _parse_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, first_wins=True, key_pattern=r"^[A-Z0-9_]+$")


def _session_get(file: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(file, key, default=default, first_match=True, cr_strip="none")



def _binary_available(session_env: Path, key: str, binary: str) -> str:
    value = _session_get(file=session_env, key=key, default="")
    if value in {"true", "false"}:
        return value
    return "true" if shutil.which(binary) is not None else "false"

def _current_cli_path() -> Path:
    root = Path(os.environ.get("LARCH_CLAUDE_PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT") or _PLUGIN_ROOT)
    return root / "python" / "cli.py"


def _invoke_cli(args: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return _run([sys.executable, str(_current_cli_path()), *args], cwd=cwd)



def _forward_result(result: subprocess.CompletedProcess[str]) -> int:
    if result.stdout:
        sys.stdout.write(result.stdout)
        sys.stdout.flush()
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()
    return result.returncode


def _tmpdir_from_env() -> Path:
    raw = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not raw:
        print("IMPLEMENT_TMPDIR required", file=sys.stderr)
        raise SystemExit(2)
    return Path(raw)


def _rehydrate_plugin_root(implement_tmpdir: Path | None = None) -> Path:
    root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not root and implement_tmpdir:
        plugin_env = implement_tmpdir / "plugin-root.env"
        if plugin_env.is_file():
            value = _session_get(file=plugin_env, key="CLAUDE_PLUGIN_ROOT", default="")
            if value:
                root = value
        if not root:
            value = _session_get(file=implement_tmpdir / "session-env.sh", key="LARCH_CLAUDE_PLUGIN_ROOT", default="")
            if value:
                root = value
    if not root:
        root = str(_PLUGIN_ROOT)
    os.environ["CLAUDE_PLUGIN_ROOT"] = root
    return Path(root)


def _read_session_key_default(implement_tmpdir: Path, key: str, default: str = "") -> str:
    return _session_get(file=implement_tmpdir / "session-env.sh", key=key, default=default)


def _rehydrate_larch_triplet(implement_tmpdir: Path) -> None:
    for key in ("LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE", "LARCH_TIMING_LEDGER"):
        if not os.environ.get(key):
            value = _read_session_key_default(implement_tmpdir, key, "")
            if value:
                os.environ[key] = value


def _read_kv_file(path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path, key, default=default, first_match=True)


def _tracking_sentinel_values(sentinel: Path) -> dict[str, str]:
    if not sentinel.is_file():
        return {}
    result = _invoke_cli(["tracking-issue", "read", "--sentinel", str(sentinel)])
    return _parse_kv(result.stdout if result.returncode == 0 else "")


def _first_nonempty(*values: str) -> str:
    return next((value for value in values if value), "")


_CLONE_TAG_ALLOWED_BYTES = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")


def _pwd_basename(pwd: str) -> str:
    r"""Match bash ``basename \"$PWD\"`` byte behavior on the logical PWD string."""
    path_bytes = os.fsencode(pwd)
    if path_bytes in (b"", b"/"):
        return "/"
    trimmed = path_bytes.rstrip(b"/")
    if not trimmed:
        return "/"
    return os.fsdecode(trimmed.rsplit(b"/", 1)[-1])


def _derive_clone_tag_full(env: Mapping[str, str] | None = None) -> str:
    source_env = os.environ if env is None else env
    clone_tag = source_env.get("CLONE_TAG", "")
    if clone_tag:
        return clone_tag
    basename = _pwd_basename(source_env["PWD"])
    translated = bytes(byte if byte in _CLONE_TAG_ALLOWED_BYTES else ord("_") for byte in os.fsencode(basename))[:32]
    if not translated:
        return "_"
    return translated.decode("ascii")


def _clone_expected_tmpdir_prefix() -> str:
    return f"claude-implement-{_derive_clone_tag_full()}-"


def clone_tag_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement clone-tag")
    parser.parse_args(argv)
    clone_tag_full = _derive_clone_tag_full()
    expected_prefix = f"claude-implement-{clone_tag_full}-"
    print(f"CLONE_TAG_FULL={shlex.quote(clone_tag_full)}")
    print(f"EXPECTED_TMPDIR_BASENAME_PREFIX={shlex.quote(expected_prefix)}")
    return 0


def _run_cli_forward(args: Sequence[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    result = subprocess.run(
        [sys.executable, str(_current_cli_path()), *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return _forward_result(result)


def _run_cli_capture(args: Sequence[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_current_cli_path()), *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _env_value(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def step0_bootstrap_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-0-bootstrap")
    parser.add_argument("--mode", choices=("initial", "resume"), required=True)
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--preflight-tmpdir", default="")
    parser.add_argument("--coder", default="")
    parser.add_argument("--emergency-requested", choices=("", "true", "false"), default="")
    parser.add_argument("--self-review-requested", choices=("", "true", "false"), default="")
    parser.add_argument("--forked-target", choices=("", "true", "false"), default="")
    parser.add_argument("--merge-requested", choices=("", "true", "false"), default="")
    parser.add_argument("--draft-requested", choices=("", "true", "false"), default="")
    parser.add_argument("--no-admin-fallback", choices=("", "true", "false"), default="")
    parser.add_argument("--no-logs-commit", choices=("", "true", "false"), default="")
    parser.add_argument("--upstream-repo", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--caller-env", default="")
    parser.add_argument("--session-env", default="")
    parser.add_argument("--non-interactive", choices=("true", "false"), default="")
    args = parser.parse_args(argv)
    implement_tmpdir_raw = os.environ.get("IMPLEMENT_TMPDIR", "")
    implement_tmpdir = Path(implement_tmpdir_raw) if implement_tmpdir_raw else None
    _rehydrate_plugin_root(implement_tmpdir)
    issue = args.issue_number or os.environ.get("TARGET_ISSUE_NUMBER", os.environ.get("ISSUE_NUMBER", ""))
    preflight = args.preflight_tmpdir or os.environ.get("PREFLIGHT_TMPDIR", "")
    coder = args.coder or _env_value("coder")
    emergency = args.emergency_requested
    self_review = args.self_review_requested
    forked = args.forked_target
    merge = args.merge_requested
    draft = args.draft_requested
    no_admin = args.no_admin_fallback
    no_logs = args.no_logs_commit
    upstream = args.upstream_repo or os.environ.get("UPSTREAM_REPO", "")
    run_id = args.run_id or os.environ.get("RUN_ID", "")
    caller_env = args.caller_env or args.session_env or os.environ.get("CALLER_ENV_PATH", os.environ.get("SESSION_ENV_PATH", ""))
    if args.mode == "resume" and implement_tmpdir:
        if not preflight and (implement_tmpdir / "preflight-tmpdir.env").is_file():
            preflight = _session_get(file=implement_tmpdir / "preflight-tmpdir.env", key="PREFLIGHT_TMPDIR", default="")
        if not forked:
            forked = _read_session_key_default(implement_tmpdir, "FORKED_TARGET", "false")
        emergency = _env_value("emergency_requested") if _env_value("emergency_requested") in {"true", "false"} else _session_get(file=implement_tmpdir / "run-flags.sh", key="EMERGENCY_REQUESTED", default=emergency)
        self_review = _env_value("self_review") if _env_value("self_review") in {"true", "false"} else _session_get(file=implement_tmpdir / "run-flags.sh", key="SELF_REVIEW_REQUESTED", default=self_review)
        seed = implement_tmpdir / "ship-seed-input.env"
        merge = _env_value("merge") or _session_get(file=seed, key="MERGE", default=merge)
        draft = _env_value("draft") or _session_get(file=seed, key="DRAFT", default=draft)
        no_admin = _env_value("no_admin_fallback") or _session_get(file=seed, key="NO_ADMIN_FALLBACK", default=no_admin)
        no_logs = _env_value("no_logs_commit") or _session_get(file=seed, key="NO_LOGS_COMMIT", default=no_logs)
        if not issue:
            sentinel_values = _tracking_sentinel_values(implement_tmpdir / "parent-issue.md")
            issue = sentinel_values.get("ISSUE_NUMBER", "") or _read_session_key_default(implement_tmpdir, "ISSUE_NUMBER", "")
            run_id = run_id or sentinel_values.get("RUN_ID", "")
        run_id = run_id or _read_session_key_default(implement_tmpdir, "RUN_ID", "")
    if forked == "true" and not upstream:
        fork = _invoke_cli(["admission", "fork-env"])
        if fork.stdout:
            sys.stdout.write(fork.stdout)
        if fork.returncode != 0:
            return fork.returncode
        values = _parse_kv(fork.stdout)
        caller_env = values.get("CALLER_ENV_PATH", caller_env)
        upstream = values.get("UPSTREAM_REPO", upstream)
        os.environ["FORK_REPO"] = values.get("FORK_REPO", os.environ.get("FORK_REPO", ""))
        os.environ["FORK_OWNER"] = values.get("FORK_OWNER", os.environ.get("FORK_OWNER", ""))
        forked = values.get("FORKED_TARGET", forked)
    if implement_tmpdir:
        _rehydrate_larch_triplet(implement_tmpdir)
        if preflight:
            _write_text_atomic(implement_tmpdir / "preflight-tmpdir.env", f"PREFLIGHT_TMPDIR={preflight}\n")
    non_interactive = args.non_interactive
    if not non_interactive:
        resolved = _invoke_cli(["bootstrap", "resolve-non-interactive"])
        non_interactive = "true" if resolved.stdout.strip() == "true" else "false"
    os.environ["LARCH_CLAUDE_PID"] = os.environ.get("LARCH_CLAUDE_PID", str(os.getppid()))
    invoke_args = [
        "bootstrap", "invoke", "--mode", args.mode,
        "--issue-number", issue,
        "--preflight-tmpdir", preflight,
        "--coder", coder,
        "--emergency-requested", emergency or "false",
        "--self-review-requested", self_review or "false",
        "--forked-target", forked or "false",
        "--merge-requested", merge or "false",
        "--draft-requested", draft or "false",
        "--no-admin-fallback", no_admin or "false",
        "--no-logs-commit", no_logs or "false",
        "--upstream-repo", upstream,
        "--run-id", run_id,
        "--caller-env", caller_env,
        "--non-interactive", non_interactive,
    ]
    result = _invoke_cli(invoke_args)
    if result.returncode != 0:
        return result.returncode
    if args.mode != "resume":
        print("progress: type p (or progress) at any time")
    if result.stdout:
        sys.stdout.write(result.stdout)
    return 0


def step0_degraded_gate_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-0-degraded-gate").parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    codex_binary_found = _read_session_key_default(implement_tmpdir, "CODEX_BINARY_FOUND", "")
    cursor_binary_found = _read_session_key_default(implement_tmpdir, "CURSOR_BINARY_FOUND", "")
    check_args = ["agent", "check-reviewers"]
    if shutil.which("codex") is None:
        check_args.append("--skip-codex-probe")
    if shutil.which("cursor") is None:
        check_args.append("--skip-cursor-probe")
    probe = _invoke_cli(check_args)
    if probe.returncode != 0:
        probe = _invoke_cli(check_args)
    values = _parse_kv(probe.stdout)
    return _run_cli_forward([
        "agent", "degraded-tools-gate", "--skill", "implement",
        "--codex-present", values.get("CODEX_PRESENT", ""),
        "--cursor-present", values.get("CURSOR_PRESENT", ""),
        "--codex-binary-found", codex_binary_found,
        "--cursor-binary-found", cursor_binary_found,
    ])


def step2_entry_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-2-entry")
    parser.add_argument("--coder", choices=("claude", "codex", "cursor"), required=True)
    args = parser.parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    codex_found = _read_session_key_default(implement_tmpdir, "CODEX_BINARY_FOUND", "false")
    cursor_found = _read_session_key_default(implement_tmpdir, "CURSOR_BINARY_FOUND", "false")
    if args.coder == "claude" or (args.coder == "codex" and codex_found != "true") or (args.coder == "cursor" and cursor_found != "true"):
        _invoke_cli(["token", "mark", "Step 2 — implementation"])
    subprocess.run([sys.executable, str(_current_cli_path()), "timing", "mark", "Step 2 — implementation"], env={**os.environ, "DESIGN_TMPDIR": "", "LARCH_TIMING_SKILL": "implement"}, check=False)
    return 0


def _persist_ship_seed_context(implement_tmpdir: Path) -> None:
    seed_file = implement_tmpdir / "ship-seed-input.env"
    lines = seed_file.read_text(encoding="utf-8", errors="replace").splitlines() if seed_file.is_file() and not seed_file.is_symlink() else []
    keys = {line.split("=", 1)[0] for line in lines if "=" in line}
    if "MANIFEST_PATH" not in keys:
        manifest = ""
        if (implement_tmpdir / "codex-step2-out" / "manifest.json").is_file():
            manifest = str(implement_tmpdir / "codex-step2-out" / "manifest.json")
        elif (implement_tmpdir / "manifest.json").is_file():
            manifest = str(implement_tmpdir / "manifest.json")
        lines.append(f"MANIFEST_PATH={manifest}")
    if "TOOL_LABEL" not in keys:
        coder_value = _read_kv_file(implement_tmpdir / "bootstrap-routing.env", "coder", "")
        tool_label = "Codex" if coder_value == "codex" else "Cursor" if coder_value == "cursor" else "claude"
        lines.append(f"TOOL_LABEL={tool_label}")
    _write_text_atomic(seed_file, "\n".join(lines) + "\n")


def _emit_phantom_probe_with_warn(step: str) -> None:
    result = phantom.probe_with_warn(proc, step=step)
    _emit_kv(key="PHANTOM_STATUS", value=result.dirty.status)
    if result.dirty.reason:
        _emit_kv(key="PHANTOM_REASON", value=result.dirty.reason)
    if result.dirty.status == "phantom":
        _emit_kv(key="PHANTOM_COUNT", value=result.dirty.count)
        _emit_kv(key="PHANTOM_PATHS_FILE", value=result.dirty.paths_file)
    if result.append_warn_error:
        _emit_kv(key="PHANTOM_APPEND_WARN_ERROR", value=result.append_warn_error)


def step2_post_dispatch_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-2-post-dispatch").parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _emit_phantom_probe_with_warn("2-post-dispatch")
    branch = _run([GIT_BIN, "symbolic-ref", "--short", "HEAD"])
    if branch.returncode != 0 or not branch.stdout.strip():
        _err("step-2-post-dispatch: not on a named branch (detached HEAD or not a git repo)")
        return 1
    _emit_kv(key="BRANCH", value=branch.stdout.strip())
    commit = _run([GIT_BIN, "rev-parse", "--short", "HEAD"])
    if commit.returncode == 0 and commit.stdout.strip():
        _emit_kv(key="COMMIT_SHA", value=commit.stdout.strip())
    _persist_ship_seed_context(implement_tmpdir)
    return 0


def step5_review_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-5-review").parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _invoke_cli(["timing", "telemetry-mark", "--implement-tmpdir", str(implement_tmpdir), "--label", "Step 5 — code review"])
    dynamic_cap = _read_session_key_default(implement_tmpdir, "LARCH_DYNAMIC_ARCHETYPES_MAX", "") or os.environ.get("LARCH_DYNAMIC_ARCHETYPES_MAX", "") or "3"
    if dynamic_cap not in {"0", "1", "2", "3"}:
        print(f"ERROR: Step 5 banner dynamic_archetypes_cap is non-integer or out of range: {dynamic_cap}", file=sys.stderr)
        return 2
    os.environ["LARCH_DYNAMIC_ARCHETYPES_MAX"] = dynamic_cap
    round_cap = "5"
    print(f"> **🔶 /implement 5: code review — review-and-fix step5 --mode loop, up to {round_cap} rounds; 3-judge panel on every round (three Cursor archetype voters; single-Claude fallback when Cursor is unavailable); review panel: specialists per vendor (mechanically pruned in rounds 3-4 when prior yield is zero; an all-pruned round converges the loop); dynamic-archetypes cap={dynamic_cap}**")
    return _run_cli_forward(["review-and-fix", "step5", "--implement-tmpdir", str(implement_tmpdir), "--mode", "loop", "--starting-round", "1"])


def _step5_round_timing_row_exists(cols: list[str], *, round_decimal: str, start_s: str) -> bool:
    return (
        len(cols) >= TIMING_LEDGER_MIN_COLUMNS
        and cols[1] == "round"
        and cols[3] == "implement"
        and cols[4] == "Step 5 — code review"
        and cols[5] == round_decimal
        and cols[6] == start_s
    )


_STEP5_RESUME_COMMIT_RELAY_KEYS = ("COMMITTED", "ERROR", "SHA", "COMMIT_OUTCOME", "NEXT_ACTION")
_COMMIT_ROUTE_SUCCESS_OUTCOMES = frozenset({"ok", "noop"})
_COMMIT_ROUTE_FAILURE_LOG_MAX = 12000


@dataclass(frozen=True)
class CommitRouteSite:
    stall_step: str
    bail_reason: str
    failure_log_label: str
    porcelain_probe: bool


@dataclass(frozen=True)
class CommitRouteFailure:
    site_name: str
    site: CommitRouteSite
    exit_code: int
    reason: str
    stdout: str
    stderr: str = ""


_COMMIT_ROUTE_SITES: dict[str, CommitRouteSite] = {
    "step5-self-review": CommitRouteSite(
        stall_step="5",
        bail_reason="review-fix-commit-failed",
        failure_log_label="Step 5 — self-review commit failed",
        porcelain_probe=False,
    ),
    "step5-resume-handoff": CommitRouteSite(
        stall_step="5",
        bail_reason="resume-handoff-commit-failed",
        failure_log_label="Step 5 — resume handoff commit failed",
        porcelain_probe=True,
    ),
    "step7": CommitRouteSite(
        stall_step="7",
        bail_reason="review-fix-commit-failed",
        failure_log_label="Step 7 — review-fix commit failed",
        porcelain_probe=False,
    ),
}


def _parse_line_anchored_commit_kv(stdout: str, *, key: str) -> list[str]:
    prefix = f"{key}="
    return [line.removeprefix(prefix) for line in stdout.splitlines() if line.startswith(prefix)]


def _relay_commit_kvs(commit_output: str, *, include_next_action: bool = True) -> None:
    allowed = set(_STEP5_RESUME_COMMIT_RELAY_KEYS)
    if not include_next_action:
        allowed.discard("NEXT_ACTION")
    for line in commit_output.splitlines():
        if line.split("=", 1)[0] in allowed:
            print(line)


def _step5_resume_relay_commit_kvs(commit_output: str) -> None:
    _relay_commit_kvs(commit_output)


def _commit_route_failure_log_path(implement_tmpdir: Path, *, site: str) -> Path:
    safe_site = re.sub(r"[^A-Za-z0-9_.-]+", "-", site).strip("-") or "unknown"
    return implement_tmpdir / f"commit-route-{safe_site}.failure.log"


def _write_commit_route_failure_log(
    implement_tmpdir: Path,
    *,
    failure: CommitRouteFailure,
) -> Path:
    path = _commit_route_failure_log_path(implement_tmpdir, site=failure.site_name)
    text = (
        f"{failure.site.failure_log_label}\n"
        f"site={failure.site_name}\n"
        f"exit_code={failure.exit_code}\n"
        f"reason={failure.reason}\n"
        "\n"
        "stdout:\n"
        f"{failure.stdout}\n"
        "\n"
        "stderr:\n"
        f"{failure.stderr}\n"
    )
    if len(text) > _COMMIT_ROUTE_FAILURE_LOG_MAX:
        text = text[:_COMMIT_ROUTE_FAILURE_LOG_MAX] + "\n[truncated]\n"
    _write_text_atomic(path, text)
    return path


def _commit_route_log_failure(
    implement_tmpdir: Path,
    *,
    site_name: str,
    site: CommitRouteSite,
    exit_code: int,
    output_file: Path,
) -> None:
    result = _invoke_cli(
        [
            "run-log",
            "append-failure",
            "--log",
            str(implement_tmpdir / "execution-issues.md"),
            "--site",
            site_name,
            "--tool",
            "python/cli.py review-and-fix commit-fixes --stage-all",
            "--exit-code",
            str(exit_code),
            "--category",
            "Tool Failures",
            "--output-file",
            str(output_file),
            "--redact",
        ]
    )
    if result.returncode != 0:
        print(
            f"commit-route: failed to append redacted failure log for {site.failure_log_label}",
            file=sys.stderr,
        )
        _forward_child_output_to_stderr(result)


def _seed_durable_stall_state(
    implement_tmpdir: Path,
    *,
    stall_step: str,
    bail_reason: str,
) -> bool:
    state_file = implement_tmpdir / "ship-pr-state.sh"
    try:
        if state_file.is_symlink():
            print(f"commit-route: refusing symlinked ship state: {state_file}", file=sys.stderr)
            return False
        if state_file.is_file():
            text = state_file.read_text(encoding="utf-8", errors="replace")
            has_kv = re.search(r"^[A-Za-z_][A-Za-z0-9_]*=", text, re.MULTILINE) is not None
            if has_kv:
                ship._patch_ship_state_keys(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                    state_file=state_file,
                    patch={
                        "STALL_TRACKING": "true",
                        "STALL_STEP": stall_step,
                        "BAIL_REASON": bail_reason,
                    },
                )
                return True
            if text.strip():
                print(f"commit-route: refusing malformed ship state: {state_file}", file=sys.stderr)
                return False
        result = _run_cli_capture(
            [
                "implement",
                "step-8-seed-initial",
                "--stall-tracking",
                "true",
                "--stall-step",
                stall_step,
                "--bail-reason",
                bail_reason,
            ]
        )
        _forward_child_output_to_stderr(result)
        return result.returncode == 0
    except Exception as exc:
        print(f"commit-route: durable stall seed failed: {exc}", file=sys.stderr)
        return False


def _commit_route_porcelain_gate() -> tuple[bool, str, str]:
    result = _run([GIT_BIN, "status", "--porcelain"])
    if result.returncode != 0:
        detail = result.stderr or result.stdout or "git status probe failed"
        return False, "git status probe failed", detail
    if result.stdout.strip():
        return False, "dirty tree after review fix commit", result.stdout
    return True, "", ""


def _commit_route_stall(
    implement_tmpdir: Path,
    *,
    failure: CommitRouteFailure,
) -> int:
    failure_log = _write_commit_route_failure_log(
        implement_tmpdir,
        failure=failure,
    )
    _commit_route_log_failure(
        implement_tmpdir,
        site_name=failure.site_name,
        site=failure.site,
        exit_code=failure.exit_code,
        output_file=failure_log,
    )
    seeded = _seed_durable_stall_state(
        implement_tmpdir,
        stall_step=failure.site.stall_step,
        bail_reason=failure.site.bail_reason,
    )
    if not seeded:
        return 1
    _relay_commit_kvs(failure.stdout, include_next_action=False)
    _emit_kv("NEXT_ACTION", "stall")
    return 0


def _commit_route_run(*, site_name: str, implement_tmpdir: Path) -> int:
    site = _COMMIT_ROUTE_SITES[site_name]
    commit_result = _invoke_cli(["review-and-fix", "commit-fixes", "--stage-all"])
    commit_output = commit_result.stdout
    outcomes = _parse_line_anchored_commit_kv(commit_output, key="COMMIT_OUTCOME")
    if len(outcomes) != 1:
        return _commit_route_stall(
            implement_tmpdir,
            failure=CommitRouteFailure(
                site_name=site_name,
                site=site,
                exit_code=commit_result.returncode or 1,
                reason="missing or malformed COMMIT_OUTCOME",
                stdout=commit_output,
                stderr=commit_result.stderr,
            ),
        )
    outcome = outcomes[0]
    if outcome not in _COMMIT_ROUTE_SUCCESS_OUTCOMES:
        return _commit_route_stall(
            implement_tmpdir,
            failure=CommitRouteFailure(
                site_name=site_name,
                site=site,
                exit_code=commit_result.returncode or 1,
                reason=f"COMMIT_OUTCOME={outcome}",
                stdout=commit_output,
                stderr=commit_result.stderr,
            ),
        )
    if site.porcelain_probe:
        ok, reason, detail = _commit_route_porcelain_gate()
        if not ok:
            return _commit_route_stall(
                implement_tmpdir,
                failure=CommitRouteFailure(
                    site_name=site_name,
                    site=site,
                    exit_code=1,
                    reason=reason,
                    stdout=commit_output,
                    stderr=detail,
                ),
            )
    _relay_commit_kvs(commit_output, include_next_action=False)
    _emit_kv("NEXT_ACTION", "continue")
    return 0


def commit_route_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement commit-route")
    parser.add_argument("--site", choices=sorted(_COMMIT_ROUTE_SITES), required=True)
    parser.add_argument("--implement-tmpdir", default="")
    args = parser.parse_args(argv)
    raw_tmpdir = args.implement_tmpdir or os.environ.get("IMPLEMENT_TMPDIR", "")
    if not raw_tmpdir:
        print("IMPLEMENT_TMPDIR required", file=sys.stderr)
        return 2
    implement_tmpdir = Path(raw_tmpdir)
    if not implement_tmpdir.is_dir():
        print(f"commit-route: implement tmpdir not found: {implement_tmpdir}", file=sys.stderr)
        return 2
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    return _commit_route_run(site_name=args.site, implement_tmpdir=implement_tmpdir)


def _step5_resume_commit_phase() -> int | None:
    """Run shared commit-route and relay its routing envelope."""
    commit_result = _invoke_cli(["implement", "commit-route", "--site", "step5-resume-handoff"])
    commit_output = commit_result.stdout
    next_actions = _parse_line_anchored_commit_kv(commit_output, key="NEXT_ACTION")
    if len(next_actions) == 1 and next_actions[0] in ("continue", "stall"):
        _emit_kv("NEXT_ACTION", next_actions[0])
        _relay_commit_kvs(commit_output, include_next_action=False)
        if next_actions[0] == "stall":
            return commit_result.returncode if commit_result.returncode != 0 else 1
        if commit_result.returncode != 0:
            return commit_result.returncode
        return None
    _step5_resume_relay_commit_kvs(commit_output)
    return commit_result.returncode if commit_result.returncode != 0 else 1


def step5_resume_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-5-resume")
    parser.add_argument("--final-round-num", required=True)
    parser.add_argument("--ready-to-commit", action="store_true")
    parser.add_argument("--record-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.final_round_num.isdigit():
        print("step-5-resume: --final-round-num must be numeric", file=sys.stderr)
        return 2
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    subprocess.run([sys.executable, str(_current_cli_path()), "timing", "mark", "Step 5 — review handoff"], env={**os.environ, "DESIGN_TMPDIR": "", "LARCH_TIMING_SKILL": "implement"}, check=False)
    round_start_file = implement_tmpdir / f"round-{args.final_round_num}" / "round-start-s"
    if round_start_file.is_file():
        start_s = round_start_file.read_text(encoding="utf-8", errors="replace").strip()
        ledger = implement_tmpdir / "timing-ledger.tsv"
        needs_record = start_s.isdigit()
        if needs_record and ledger.is_file():
            round_decimal = str(int(args.final_round_num))
            for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
                cols = line.split("\t")
                if _step5_round_timing_row_exists(cols, round_decimal=round_decimal, start_s=start_s):
                    needs_record = False
                    break
        if needs_record and start_s.isdigit():
            _invoke_cli(["review-and-fix", "record-round-timing", "--implement-tmpdir", str(implement_tmpdir), "--round", args.final_round_num, "--start-s", start_s, "--end-s", str(int(time.time()))])
    if args.record_only:
        return 0
    if args.ready_to_commit or os.environ.get("STEP5_HANDOFF_READY_TO_COMMIT") == "true":
        commit_rc = _step5_resume_commit_phase()
        if commit_rc is not None:
            return commit_rc
    print("progress: type p (or progress) at any time")
    return _run_cli_forward(["review-and-fix", "step5", "--implement-tmpdir", str(implement_tmpdir), "--mode", "loop", "--starting-round", str(int(args.final_round_num) + 1)])


def step6_entry_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-6-entry").parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    (implement_tmpdir / ".review-boundary-passed").touch(exist_ok=True)
    return _run_cli_forward(["review-and-fix", "check-changes", "--baseline", str(implement_tmpdir / "pre-review-untracked.txt"), "--head-baseline", str(implement_tmpdir / "pre-review-head.txt")])


def run_step_checks_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement run-step-checks")
    parser.add_argument("--site", required=True)
    args = parser.parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    return _run_cli_forward(["checks", "run-relevant", "--site", args.site, "--tmpdir", str(implement_tmpdir)])


def step8_python_guard_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-8-python-guard").parse_args(argv)
    if sys.version_info >= (3, 11):  # noqa: UP036 - intentional runtime guard; this module may execute under pre-3.11 interpreters.
        return 0
    print("ERROR: Python ship driver requires Python 3.11 or newer", file=sys.stderr)
    print('{"detail":"Python ship driver requires Python 3.11 or newer","failed_run_id":"","ledger_dispatcher":"","ledger_exit_code":null,"ledger_failure_detail_log":"","ledger_phase":"","ledger_ready":false,"ledger_site":"","ledger_step":"","ledger_trigger":"","merge_result":"","needs_user_reason":"","outcome":"STALLED","pr_number":null,"pr_url":""}')
    return 4


def step8_seed_initial_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-8-seed-initial")
    for flag in ("merge", "draft", "no-admin-fallback", "no-logs-commit", "manifest-path", "tool-label", "stall-tracking", "stall-step", "bail-reason", "bail-failure-detail-log"):
        parser.add_argument(f"--{flag}", default="")
    args = parser.parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    state_file = implement_tmpdir / "ship-pr-state.sh"
    if state_file.is_file() and state_file.stat().st_size > 0 and re.search(r"^[A-Za-z_][A-Za-z0-9_]*=", state_file.read_text(encoding="utf-8", errors="replace"), re.MULTILINE):
        print("step-8-seed-initial: initial ship state is create-if-absent only; refusing to re-seed non-empty ship-pr-state.sh", file=sys.stderr)
        return 2
    bootstrap_file = implement_tmpdir / "bootstrap-routing.env"
    seed_file = implement_tmpdir / "ship-seed-input.env"
    parent_issue = implement_tmpdir / "parent-issue.md"
    sentinel = _tracking_sentinel_values(parent_issue)
    bootstrap_coder = _read_kv_file(bootstrap_file, "coder", "")
    mapped_tool = "Codex" if bootstrap_coder == "codex" else "Cursor" if bootstrap_coder == "cursor" else "" if not bootstrap_coder else "claude"
    branch = _first_nonempty(_read_kv_file(bootstrap_file, "BRANCH_NAME", ""), _read_kv_file(parent_issue, "BRANCH_NAME", ""), sentinel.get("BRANCH_NAME", ""))
    issue = _first_nonempty(_read_kv_file(bootstrap_file, "ISSUE_NUMBER", ""), _read_kv_file(parent_issue, "ISSUE_NUMBER", ""), sentinel.get("ISSUE_NUMBER", ""))
    run_id = _first_nonempty(_read_kv_file(bootstrap_file, "RUN_ID", ""), _read_session_key_default(implement_tmpdir, "LARCH_RUN_ID", ""), _read_kv_file(parent_issue, "RUN_ID", ""), sentinel.get("RUN_ID", ""))
    repo = _first_nonempty(_read_kv_file(bootstrap_file, "REPO", ""), _read_session_key_default(implement_tmpdir, "REPO", ""))
    if not branch:
        print("step-8-seed-initial: BRANCH_NAME is required but missing from durable inputs", file=sys.stderr)
        return 2
    if not issue.isdigit():
        print("step-8-seed-initial: ISSUE_NUMBER must be a non-empty digit value", file=sys.stderr)
        return 2
    if not run_id:
        print("step-8-seed-initial: RUN_ID is required but missing from durable inputs", file=sys.stderr)
        return 2
    if not repo:
        print("step-8-seed-initial: REPO is required but missing from durable inputs", file=sys.stderr)
        return 2
    expected_session_id = (implement_tmpdir / "session-id").read_text(encoding="utf-8", errors="replace").strip() if (implement_tmpdir / "session-id").is_file() else ""
    return _run_cli_forward([
        "ship", "seed-initial-state", "--tmpdir", str(implement_tmpdir), "--state-file", str(state_file),
        "--branch", branch, "--issue", issue, "--repo", repo, "--run-id", run_id,
        "--manifest-path", _first_nonempty(args.manifest_path, _read_kv_file(seed_file, "MANIFEST_PATH", "")),
        "--tool-label", _first_nonempty(args.tool_label, _read_kv_file(seed_file, "TOOL_LABEL", ""), mapped_tool, "claude"),
        "--merge", _first_nonempty(args.merge, _read_kv_file(seed_file, "MERGE", ""), "false"),
        "--draft", _first_nonempty(args.draft, _read_kv_file(seed_file, "DRAFT", ""), "false"),
        "--forked", _first_nonempty(_read_kv_file(seed_file, "FORKED_TARGET", ""), _read_session_key_default(implement_tmpdir, "FORKED_TARGET", ""), "false"),
        "--repo-unavailable", _first_nonempty(_read_kv_file(bootstrap_file, "REPO_UNAVAILABLE", ""), _read_session_key_default(implement_tmpdir, "REPO_UNAVAILABLE", ""), "false"),
        "--deferred", _first_nonempty(_read_kv_file(bootstrap_file, "DEFERRED", ""), _read_kv_file(seed_file, "DEFERRED", ""), "false"),
        "--no-admin-fallback", _first_nonempty(args.no_admin_fallback, _read_kv_file(seed_file, "NO_ADMIN_FALLBACK", ""), "false"),
        "--no-logs-commit", _first_nonempty(args.no_logs_commit, _read_kv_file(seed_file, "NO_LOGS_COMMIT", ""), "false"),
        "--expected-session-id", expected_session_id,
        "--expected-tmpdir-basename-prefix", _clone_expected_tmpdir_prefix(),
        "--stall-tracking", args.stall_tracking or "false",
        "--stall-step", args.stall_step,
        "--bail-reason", args.bail_reason,
        "--bail-failure-detail-log", args.bail_failure_detail_log,
    ])


def _ship_state_has_shell_kv_entries(state_file: Path) -> bool:
    if not state_file.is_file():
        return False
    text = state_file.read_text(encoding="utf-8", errors="replace")
    return re.search(r"^[A-Za-z_][A-Za-z0-9_]*=", text, re.MULTILINE) is not None


def _forward_child_output_to_stderr(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        sys.stderr.write(result.stdout)
        sys.stderr.flush()
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()


_SHIP_ROUTE_EXIT_AUTONOMOUS_REASONS = {
    "first-fixer-non-health",
    "ship-pr-internal-lint-fix",
    "local-unfixable",
}
_SHIP_ROUTE_EXIT_LEDGER_KEYS = (
    "ledger_ready",
    "ledger_site",
    "ledger_trigger",
    "ledger_step",
    "ledger_phase",
    "ledger_dispatcher",
    "ledger_exit_code",
    "ledger_failure_detail_log",
)


@dataclass(frozen=True)
class ShipRouteResult:
    exit_code: int
    payload: dict[str, object]
    action: str


def _ship_route_exit_fail(*, message: str, handoff: Path) -> int:
    with contextlib.suppress(FileNotFoundError):
        handoff.unlink()
    print(f"ship route-exit: {message}", file=sys.stderr)
    return 2


def _read_ship_route_exit_code(*, args: argparse.Namespace, default_file: Path) -> tuple[int | None, str]:
    file_path = Path(args.exit_code_file) if args.exit_code_file else default_file
    if file_path.is_file():
        raw = file_path.read_text(encoding="utf-8", errors="replace").strip()
        try:
            return int(raw), ""
        except ValueError:
            return None, f"invalid exit-code sidecar: {file_path}"
    if args.exit_code is not None:
        return int(args.exit_code), ""
    return None, f"missing exit-code sidecar: {file_path}"


def _read_ship_route_json(path: Path) -> tuple[dict[str, object] | None, str]:
    if not path.is_file():
        return None, f"missing json sidecar: {path}"
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"malformed json sidecar: {exc}"
    if not isinstance(raw, dict):
        return None, "json sidecar is not an object"
    return cast("dict[str, object]", raw), ""


def _ship_route_required_str(*, payload: Mapping[str, object], key: str) -> tuple[str, str]:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        return "", f"missing required JSON field: {key}"
    return value, ""


def _classify_ship_needs_user_reason(reason: str) -> str:
    if reason == "oos-filing":
        return "oos-pipeline"
    if reason in _SHIP_ROUTE_EXIT_AUTONOMOUS_REASONS or reason.startswith("ci-local-unfixable:"):
        return "ci-fix"
    return "operator-bail"


def _classify_ship_route_exit(*, exit_code: int, payload: dict[str, object]) -> tuple[str, str]:
    outcome, error = _ship_route_required_str(payload=payload, key="outcome")
    if error:
        return "", error
    if exit_code == SHIP_ROUTE_EXIT_NEEDS_USER:
        reason, error = _ship_route_required_str(payload=payload, key="needs_user_reason")
        return ("", error) if error else (_classify_ship_needs_user_reason(reason), "")
    actions = {
        0: "complete" if outcome == "OK" else "reship",
        1: "tool-failure" if outcome == "INTERNAL_ERROR" else "",
        SHIP_ROUTE_EXIT_STALLED: "stall",
        SHIP_ROUTE_EXIT_TRANSIENT: "transient",
    }
    action = actions.get(exit_code)
    if action:
        return action, ""
    if exit_code == 1:
        return "", "exit 1 requires outcome=INTERNAL_ERROR"
    return "", f"unsupported driver exit code: {exit_code}"


def _ship_route_safe_line(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def _ship_route_detail_needs_file(detail: str) -> bool:
    return "\n" in detail or "\r" in detail or len(detail) > SHIP_ROUTE_DETAIL_FILE_MAX


def _write_ship_route_handoff(
    *,
    implement_tmpdir: Path,
    payload: Mapping[str, object],
    action: str,
    delay_seconds: int = 0,
) -> None:
    handoff = implement_tmpdir / ".ship-route-exit-handoff.env"
    detail_file = implement_tmpdir / ".ship-route-exit-detail.txt"
    lines: list[str] = []
    key_map = {
        "failed_run_id": "FAILED_RUN_ID",
        "needs_user_reason": "NEEDS_USER_REASON",
    }
    for source_key, out_key in key_map.items():
        value = _ship_route_safe_line(payload.get(source_key, ""))
        if value:
            lines.append(f"{out_key}={value}")
    detail_raw = payload.get("detail", "")
    detail = detail_raw if isinstance(detail_raw, str) else str(detail_raw or "")
    if detail:
        if _ship_route_detail_needs_file(detail):
            _write_text_atomic(detail_file, detail if detail.endswith("\n") else f"{detail}\n")
            lines.append(f"DETAIL_FILE={detail_file}")
        else:
            lines.append(f"DETAIL={_ship_route_safe_line(detail)}")
    lines.extend(f"{key}={_ship_route_safe_line(payload[key])}" for key in _SHIP_ROUTE_EXIT_LEDGER_KEYS if key in payload)
    lines.append(f"NEXT_ACTION={action}")
    if delay_seconds:
        lines.append(f"RESHIP_DELAY_SECONDS={delay_seconds}")
    _write_text_atomic(handoff, "\n".join(lines) + "\n")


def _ship_route_read_retry_count(path: Path) -> int:
    if not path.is_file():
        return 0
    with contextlib.suppress(ValueError, OSError, UnicodeDecodeError):
        return int(path.read_text(encoding="utf-8").strip() or "0")
    return 0


def _ship_route_write_retry_count(*, path: Path, value: int) -> None:
    _write_text_atomic(path, f"{value}\n")


def _ship_route_seed_transient_stall(implement_tmpdir: Path) -> None:
    result = _run_cli_capture([
        "stall-recovery",
        "seed-terminal-state",
        "--implement-tmpdir",
        str(implement_tmpdir),
        "--stall-step",
        "transient-retry-cap",
        "--phase",
        "ci-initial",
    ])
    if result.returncode != 0:
        print(
            "ship route-exit: transient retry-cap stall seed failed; continuing with NEXT_ACTION=stall",
            file=sys.stderr,
        )
        _forward_child_output_to_stderr(result)


def ship_route_exit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ship route-exit")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--json-file", default="")
    parser.add_argument("--exit-code-file", default="")
    parser.add_argument("--exit-code", type=int)
    args = parser.parse_args(argv)
    implement_tmpdir = Path(args.implement_tmpdir)
    handoff = implement_tmpdir / ".ship-route-exit-handoff.env"
    json_file = Path(args.json_file) if args.json_file else implement_tmpdir / ".step-8-ship-handoff.json"
    exit_code_file = implement_tmpdir / ".step-8-ship-handoff.rc"
    exit_code, error = _read_ship_route_exit_code(args=args, default_file=exit_code_file)
    if error or exit_code is None:
        return _ship_route_exit_fail(message=error or "missing exit code", handoff=handoff)
    payload, error = _read_ship_route_json(json_file)
    if error or payload is None:
        return _ship_route_exit_fail(message=error or "missing json", handoff=handoff)
    action, error = _classify_ship_route_exit(exit_code=exit_code, payload=payload)
    if error:
        return _ship_route_exit_fail(message=error, handoff=handoff)
    delay_seconds = 0
    if action == "transient":
        count_file = implement_tmpdir / "ship-pr-net-retries-python.count"
        retry = _ship_route_read_retry_count(count_file) + 1
        try:
            _ship_route_write_retry_count(path=count_file, value=retry)
        except OSError as exc:
            return _ship_route_exit_fail(message=f"cannot persist transient retry counter: {exc}", handoff=handoff)
        if retry >= SHIP_ROUTE_TRANSIENT_STALL_RETRY:
            _ship_route_seed_transient_stall(implement_tmpdir)
            action = "stall"
        else:
            delay_seconds = 30
            time.sleep(delay_seconds)
            action = "reship"
    try:
        _write_ship_route_handoff(
            implement_tmpdir=implement_tmpdir,
            payload=payload,
            action=action,
            delay_seconds=delay_seconds,
        )
    except OSError as exc:
        return _ship_route_exit_fail(message=f"cannot write route-exit handoff: {exc}", handoff=handoff)
    _emit_kv(key="NEXT_ACTION", value=action)
    return 0


def ship_pre_driver_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py ship pre-driver").parse_args(argv)
    raw_tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not raw_tmpdir:
        print("IMPLEMENT_TMPDIR required", file=sys.stderr)
        _emit_kv(key="NEXT_ACTION", value="halt-seed")
        return 2
    implement_tmpdir = Path(raw_tmpdir)
    _rehydrate_plugin_root(implement_tmpdir)
    state_file = implement_tmpdir / "ship-pr-state.sh"

    guard = _run_cli_capture(["implement", "step-8-python-guard"])
    _forward_child_output_to_stderr(guard)
    if guard.returncode != 0:
        _emit_kv(key="NEXT_ACTION", value="stall")
        return 4

    if not _ship_state_has_shell_kv_entries(state_file):
        seed = _run_cli_capture(["implement", "step-8-seed-initial"])
        _forward_child_output_to_stderr(seed)
        if seed.returncode != 0:
            _emit_kv(key="NEXT_ACTION", value="halt-seed")
            return seed.returncode

    oos = _run_cli_capture(["oos", "file", "--implement-tmpdir", str(implement_tmpdir)])
    _forward_child_output_to_stderr(oos)
    if oos.returncode != 0:
        _emit_kv(key="NEXT_ACTION", value="halt-oos")
        return oos.returncode

    _emit_kv(key="NEXT_ACTION", value="ship")
    return 0


def step8_ship_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-8-ship").parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    state_file = implement_tmpdir / "ship-pr-state.sh"
    def state(key: str, default: str = "") -> str:
        return _read_kv_file(state_file, key, default)
    branch = os.environ.get("BRANCH_NAME", "") or state("BRANCH_NAME")
    issue = os.environ.get("ISSUE_NUMBER", "") or state("ISSUE_NUMBER")
    run_id = os.environ.get("RUN_ID", "") or state("RUN_ID")
    repo = os.environ.get("REPO", "") or state("REPO")
    merge = _env_value("merge") or state("MERGE", "false") or "false"
    draft = _env_value("draft") or state("DRAFT", "false") or "false"
    forked = _env_value("forked_target") or state("FORKED_TARGET", "false") or "false"
    repo_unavailable = os.environ.get("REPO_UNAVAILABLE", "") or state("REPO_UNAVAILABLE", "false") or "false"
    manifest = os.environ.get("MANIFEST_PATH", "") or state("MANIFEST_PATH")
    tool = _env_value("coder") or state("TOOL_LABEL", "claude") or "claude"
    no_admin = _env_value("no_admin_fallback") or state("NO_ADMIN_FALLBACK", "false") or "false"
    no_logs = _env_value("no_logs_commit") or state("NO_LOGS_COMMIT", "false") or "false"
    for name, value in (("BRANCH_NAME", branch), ("RUN_ID", run_id), ("REPO", repo)):
        if not value:
            print(f"step-8-ship: missing {name} (not exported and absent from ship-pr-state.sh)", file=sys.stderr)
            return 2
    guard_rc = step8_python_guard_main([])
    if guard_rc != 0:
        return guard_rc
    print("→ phantom-probe: 8-pre-ship", file=sys.stderr)
    with contextlib.redirect_stdout(sys.stderr):
        _emit_phantom_probe_with_warn("8-pre-ship")
    expected_session_id = (implement_tmpdir / "session-id").read_text(encoding="utf-8", errors="replace").strip() if (implement_tmpdir / "session-id").is_file() else ""
    return _run_cli_forward([
        "ship", "pr", "--branch", branch, "--issue", issue, "--repo", repo, "--run-id", run_id,
        "--tmpdir", str(implement_tmpdir), "--manifest-path", manifest, "--state-file", str(state_file),
        "--tool-label", tool, "--merge", merge, "--draft", draft, "--forked", forked,
        "--repo-unavailable", repo_unavailable, "--no-admin-fallback", no_admin or "false", "--no-logs-commit", no_logs or "false",
        "--expected-session-id", expected_session_id, "--expected-tmpdir-basename-prefix", _clone_expected_tmpdir_prefix(),
    ])


def _step8_oos_checkpoint_log_failure(*, implement_tmpdir: Path, rc: int, err: Path) -> None:
    log_file = implement_tmpdir / "execution-issues.md"
    log_text = log_file.read_text(encoding="utf-8", errors="replace") if log_file.is_file() else ""
    if rc == 1:
        already = "Step step-8-oos-checkpoint —" in log_text or (
            "step-8-oos-checkpoint" in log_text and "step-8-oos-checkpoint-validation" not in log_text
        )
    else:
        already = "step-8-oos-checkpoint-validation" in log_text
    if rc != 0 and not already:
        site = "step-8-oos-checkpoint" if rc == 1 else "step-8-oos-checkpoint-validation"
        _invoke_cli([
            "run-log",
            "append-failure",
            "--log",
            str(log_file),
            "--site",
            site,
            "--tool",
            "python/cli.py oos disposition-checkpoint",
            "--exit-code",
            str(rc),
            "--category",
            "Tool Failures",
            "--output-file",
            str(err),
            "--redact",
        ])


def _step8_oos_checkpoint_filed_count(*, implement_tmpdir: Path, run_id: str) -> int:
    ndjson = implement_tmpdir / "larch-logs" / "implement" / run_id / "oos-issues.ndjson"
    if ndjson.is_file():
        return len(oos_filer._ndjson_filed_evidence(implement_tmpdir, run_id))  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    return 0


def _step8_oos_checkpoint_bookkeeping(implement_tmpdir: Path) -> tuple[bool, str]:
    run_id = file_oos.resolve_implement_run_id_for_disposition(implement_tmpdir)
    if not run_id:
        print("step-8-oos-checkpoint: bookkeeping failed: cannot resolve canonical run id", file=sys.stderr)
        return False, ""
    stats_path = implement_tmpdir / "larch-logs" / "implement" / run_id / "run-statistics.md"
    try:
        filed_count = _step8_oos_checkpoint_filed_count(implement_tmpdir=implement_tmpdir, run_id=run_id)
        stamped = oos_filer._stamp_manifest(implement_tmpdir, run_id, value=True)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        if not stamped:
            raise RuntimeError("manifest stamp returned false")
        _ = oos_filer._write_run_statistics(implement_tmpdir, run_id, filed_count)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        ship._patch_ship_state_keys(state_file=implement_tmpdir / "ship-pr-state.sh", patch={"OOS_PENDING": "false"})  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    except Exception as exc:
        print(f"step-8-oos-checkpoint: bookkeeping failed: {exc}", file=sys.stderr)
        with contextlib.suppress(Exception):
            _ = oos_filer._stamp_manifest(implement_tmpdir, run_id, value=False)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        with contextlib.suppress(OSError):
            if stats_path.is_file():
                stats_path.unlink()
        return False, run_id
    return True, run_id


def step8_oos_checkpoint_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-8-oos-checkpoint").parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    err = implement_tmpdir / "oos-disposition-checkpoint.stderr.log"
    args = ["oos", "disposition-checkpoint", "--implement-tmpdir", str(implement_tmpdir)]
    if os.environ.get("DESIGN_TMPDIR"):
        args.extend(["--design-tmpdir", os.environ["DESIGN_TMPDIR"]])
    result = subprocess.run([sys.executable, str(_current_cli_path()), *args], capture_output=True, text=True, check=False)
    if result.stderr:
        existing = err.read_text(encoding="utf-8", errors="replace") if err.is_file() else ""
        err.write_text(existing + result.stderr, encoding="utf-8")
    _step8_oos_checkpoint_log_failure(implement_tmpdir=implement_tmpdir, rc=result.returncode, err=err)
    if result.returncode != 0:
        _emit_kv(key="OOS_CHECKPOINT_RC", value=result.returncode)
        _emit_kv(key="NEXT_ACTION", value="stall")
        return 0
    ok, _run_id = _step8_oos_checkpoint_bookkeeping(implement_tmpdir)
    if ok:
        _emit_kv(key="OOS_CHECKPOINT_RC", value=0)
        _emit_kv(key="NEXT_ACTION", value="reship")
    else:
        _emit_kv(key="OOS_CHECKPOINT_RC", value=2)
        _emit_kv(key="NEXT_ACTION", value="stall")
    return 0


@dataclass(frozen=True)
class RecoveryParse:
    tuples: set[tuple[str, str]]
    paths: set[str]


def _parse_porcelain_z(path: Path) -> RecoveryParse:
    raw = path.read_bytes() if path.exists() else b""
    items = raw.split(b"\0")
    tuples: set[tuple[str, str]] = set()
    paths: set[str] = set()
    idx = 0
    while idx < len(items):
        rec = items[idx]
        idx += 1
        if not rec:
            continue
        status = rec[:2].decode("ascii", "replace")
        rel = rec[3:].decode("utf-8", "surrogateescape")
        if ("R" in status or "C" in status) and idx < len(items):
            idx += 1
        tuples.add((status, rel))
        paths.add(rel)
    return RecoveryParse(tuples, paths)


def compute_recovery_paths(
    *,
    repo_root: Path,
    tmpdir: Path,
    prelaunch_porcelain: Path,
    postlaunch_porcelain: Path,
    prelaunch_digests: Path,
    out_file: Path,
) -> bool:
    pre = _parse_porcelain_z(prelaunch_porcelain)
    post = _parse_porcelain_z(postlaunch_porcelain)
    digests: dict[str, str] = {}
    if prelaunch_digests.exists():
        for line in prelaunch_digests.read_text(encoding="utf-8", errors="surrogateescape").splitlines():
            if "\t" in line:
                digest, rel = line.split("\t", 1)
                digests[rel] = digest
    tmp_rel: str | None = None
    try:
        repo_real = repo_root.resolve()
        tmp_real = tmpdir.resolve()
        if tmp_real == repo_real:
            tmp_rel = "."
        else:
            tmp_real.relative_to(repo_real)
            tmp_rel = os.path.relpath(tmp_real, repo_real)
    except (OSError, ValueError):
        tmp_rel = None

    def under_tmp(rel: str) -> bool:
        if tmp_rel is None:
            return False
        return rel == tmp_rel or rel.startswith(tmp_rel.rstrip("/") + "/")

    def current_digest(rel: str) -> str:
        try:
            return hashlib.sha256((repo_root / rel).read_bytes()).hexdigest()
        except OSError:
            return "missing"

    candidates: list[str] = []
    for status, rel in sorted(post.tuples, key=lambda item: item[1]):
        if under_tmp(rel):
            continue
        include = False
        if (status, rel) not in pre.tuples:
            include = True
        elif rel in pre.paths:
            include = current_digest(rel) != digests.get(rel, "")
        if include and rel not in candidates:
            candidates.append(rel)
    _write_bytes_atomic(out_file, b"".join(p.encode("utf-8", "surrogateescape") + b"\0" for p in candidates))
    return bool(candidates)


def recovery_paths_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py implement recovery-paths")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--tmpdir", required=True)
    parser.add_argument("--prelaunch-porcelain", required=True)
    parser.add_argument("--postlaunch-porcelain", required=True)
    parser.add_argument("--prelaunch-digests", required=True)
    parser.add_argument("--out-file", required=True)
    args = parser.parse_args(argv)
    ok = compute_recovery_paths(
        repo_root=Path(args.repo_root),
        tmpdir=Path(args.tmpdir),
        prelaunch_porcelain=Path(args.prelaunch_porcelain),
        postlaunch_porcelain=Path(args.postlaunch_porcelain),
        prelaunch_digests=Path(args.prelaunch_digests),
        out_file=Path(args.out_file),
    )
    return 0 if ok else 1


def _commit_usage_fail(error: str) -> int:
    _err("Usage: implement commit --message MSG [--pathspec-from-file PATH [--pathspec-file-nul]] [files...]")
    _err("HINT: --stage-all belongs to review-and-fix commit-fixes (Step 5 review fixes); implementation commits name specific files or use --pathspec-from-file.")
    _emit_kv(key="COMMITTED", value="false")
    _emit_kv(key="SHA", value="")
    _emit_kv(key="ERROR", value=error)
    return 2


def commit_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    argv_list = list(argv if argv is not None else sys.argv[1:])
    known_flags = {"--message", "-m", "--pathspec-from-file", "--pathspec-file-nul", "--help", "-h"}
    idx = 0
    while idx < len(argv_list):
        arg = argv_list[idx]
        if arg in ("--help", "-h"):
            argparse.ArgumentParser(prog="cli.py implement commit").print_help()
            return 0
        if arg.startswith("-") and arg not in known_flags:
            return _commit_usage_fail(f"unknown option: {arg}")
        if arg in ("--message", "-m", "--pathspec-from-file"):
            if idx + 1 >= len(argv_list) or argv_list[idx + 1].startswith("-"):
                return _commit_usage_fail(f"{arg} requires a value")
            idx += 2
            continue
        if arg == "--pathspec-file-nul":
            idx += 1
            continue
        idx += 1
    parser = argparse.ArgumentParser(prog="cli.py implement commit", add_help=True)
    parser.add_argument("--message", "-m", default="")
    parser.add_argument("--pathspec-from-file", default="")
    parser.add_argument("--pathspec-file-nul", action="store_true")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args(argv_list)
    if not args.message.strip():
        return _commit_usage_fail("--message is required")

    env_file = Path(os.environ.get("IMPLEMENT_TMPDIR", "")) / "session-env.sh" if os.environ.get("IMPLEMENT_TMPDIR") else None
    if env_file and env_file.is_file():
        for key in ("LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE", "LARCH_TIMING_LEDGER"):
            if not os.environ.get(key):
                value = _session_get(file=env_file, key=key, default="")
                if value:
                    os.environ[key] = value
    _invoke_cli(["token", "mark", "Step 4 — commit implementation"])
    env = os.environ.copy()
    env["LARCH_TIMING_SKILL"] = "implement"
    subprocess.run([sys.executable, str(_current_cli_path()), "timing", "mark", "Step 4 — commit implementation"], env=env, check=False)

    commit_args = [sys.executable, str(_current_cli_path()), "git", "commit", "-m", args.message]
    if args.pathspec_from_file:
        commit_args.extend(["--only", "--pathspec-from-file", args.pathspec_from_file])
        if args.pathspec_file_nul:
            commit_args.append("--pathspec-file-nul")
    else:
        commit_args.extend(args.files)
    result = _run(commit_args)
    if result.returncode == 0:
        sha = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
        _emit_kv(key="COMMITTED", value="true")
        _emit_kv(key="SHA", value=sha)
        return 0
    error = (result.stderr or result.stdout).replace("\n", " ")[:500]
    _emit_kv(key="COMMITTED", value="false")
    _emit_kv(key="SHA", value="")
    _emit_kv(key="ERROR", value=error)
    return result.returncode


def run_dispatch_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py implement run-dispatch")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--coder", required=True)
    parser.add_argument("--answers", default="")
    args = parser.parse_args(argv)
    tmp_arg = Path(args.implement_tmpdir)
    if not tmp_arg.is_dir():
        _err(f"implement run-dispatch: --implement-tmpdir not a directory: {tmp_arg}")
        return 2
    tmpdir = tmp_arg.resolve()
    session_env = tmpdir / "session-env.sh"
    feature_file = tmpdir / "feature-description.txt"
    plan_file = tmpdir / "plan.txt"
    if not session_env.is_file():
        _err(f"implement run-dispatch: session-env not readable: {session_env}")
        return 2
    if not feature_file.is_file():
        _err(f"implement run-dispatch: feature file not found: {feature_file}")
        return 2
    if not plan_file.is_file():
        _err(f"implement run-dispatch: plan file not found at conventional path: {plan_file}")
        return 2
    if args.answers and not Path(args.answers).is_file():
        _err(f"implement run-dispatch: --answers path does not exist: {args.answers}")
        return 2
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or _session_get(file=session_env, key="LARCH_CLAUDE_PLUGIN_ROOT", default="") or str(_PLUGIN_ROOT)
    if not Path(plugin_root).is_dir():
        _err(f"implement run-dispatch: plugin root not a directory: {plugin_root}")
        return 2
    cursor_binary_found = _binary_available(session_env, "CURSOR_BINARY_FOUND", "cursor")
    codex_binary_found = _binary_available(session_env, "CODEX_BINARY_FOUND", "codex")
    if args.coder == "cursor" and cursor_binary_found != "true":
        _err("implement run-dispatch: cursor coder selected at Step 0 but cursor binary is missing; refusing Step 2 dispatch")
        return 2
    if args.coder == "codex" and codex_binary_found != "true":
        _err("implement run-dispatch: codex coder selected at Step 0 but codex binary is missing; refusing Step 2 dispatch")
        return 2
    child = [
        sys.executable,
        str(Path(plugin_root) / "python" / "cli.py"),
        "implement",
        "step2-dispatch",
        "--tmpdir",
        str(tmpdir),
        "--plan-file",
        str(plan_file),
        "--feature-file",
        str(feature_file),
        "--coder",
        args.coder,
        "--cursor-binary-found",
        cursor_binary_found,
        "--codex-binary-found",
        codex_binary_found,
    ]
    if args.answers:
        child.extend(["--answers", args.answers])
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = plugin_root
    env["IMPLEMENT_TMPDIR"] = str(tmpdir)
    result = subprocess.run(child, text=True, capture_output=True, env=env, check=False)
    if result.stdout:
        stream = logging_util.contract_stream()
        stream.write(result.stdout)
        stream.flush()
    if result.stderr:
        _err(result.stderr.rstrip("\n"))
    return result.returncode


# Mutable state: scout_status / baseline_sha / spawn_branch are filled in as dispatch proceeds.
@dataclass
class DispatchState:
    repo_root: Path
    tmpdir: Path
    plan_file: Path
    feature_file: Path
    coder: str
    cursor_present: str
    cursor_binary_found: str
    codex_binary_found: str
    answers_file: Path | None
    plugin_root: Path
    tool_tag: str
    manifest_path: Path
    manifest_raw_path: Path
    qa_pending_path: Path
    transcript_path: Path
    sidecar_log: Path
    scout_coder_manifest: Path
    launch_scout_manifest: Path
    external_scout_marker: Path
    baseline_file: Path
    prelaunch_porcelain: Path
    postlaunch_porcelain: Path
    prelaunch_digests: Path
    prelaunch_index_flag: Path
    recovery_paths_file: Path
    resume_count_file: Path
    spawn_branch_file: Path
    spawn_coder_file: Path
    runtime_failure_token: str
    bailed_no_reason_token: str
    requires_head_unchanged: bool
    nonzero_exit_warn_token: str = ""
    baseline_sha: str = ""
    spawn_branch: str = ""
    scout_status: str = ""

    def emit_bailed(self, reason: str, *, manifest: bool = False) -> int:
        _emit_kv(key="STATUS", value="bailed")
        _emit_kv(key="REASON", value=reason)
        _emit_kv(key="TOOL", value=self.tool_tag)
        if manifest:
            _emit_kv(key="MANIFEST", value=str(self.manifest_path))
        if self.transcript_path.exists() and self.transcript_path.stat().st_size > 0:
            _emit_kv(key="TRANSCRIPT", value=str(self.transcript_path))
        if self.sidecar_log.exists() and self.sidecar_log.stat().st_size > 0:
            _emit_kv(key="SIDECAR_LOG", value=str(self.sidecar_log))
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="forbidden")
        return 0


def _clear_external_scout_state(tmpdir: Path) -> None:
    for path in (
        tmpdir / "scout-coder-manifest.json",
        tmpdir / "step2-external-scout-eligible.txt",
        tmpdir / "step2-scout-coder-status.env",
        tmpdir / "scout-coder-manifest.raw.json",
        tmpdir / ".producer-scout-warning-logged",
        tmpdir / "codex-step2-out" / "scout-coder-manifest.json",
        tmpdir / "cursor-step2-out" / "scout-coder-manifest.json",
    ):
        with contextlib.suppress(OSError):
            path.unlink()


def _submodule_roots(repo: Path) -> list[str]:
    out = _git_stdout(repo, "submodule", "status", "--recursive")
    roots: list[str] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= PORCELAIN_MIN_PARTS:
            roots.append(parts[1].rstrip("/"))
    return roots


def _path_under_submodule(rel: str, roots: Iterable[str]) -> bool:
    return any(rel == root or rel.startswith(root + "/") for root in roots if root)


def _post_implementer_safety_reason(st: DispatchState) -> str:
    current_branch = _git_stdout(st.repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    if current_branch != st.spawn_branch:
        return "branch-changed"
    sub_status = _git_stdout(st.repo_root, "submodule", "status", "--recursive")
    if sub_status and re.search(r"^[+\-U]", sub_status, re.MULTILINE):
        return "submodule-dirty"
    roots = _submodule_roots(st.repo_root)
    if roots:
        raw = _git(st.repo_root, "status", "--porcelain=v1", "-z", "--ignore-submodules=none", binary=True)
        if raw.returncode != 0:
            return "submodule-dirty"
        for rec in raw.stdout.split(b"\0"):
            if not rec:
                continue
            rel = rec[3:].decode("utf-8", "surrogateescape")
            if _path_under_submodule(rel, roots):
                return "submodule-dirty"
    if st.requires_head_unchanged:
        current_head = _git_stdout(st.repo_root, "rev-parse", "HEAD")
        if current_head != st.baseline_sha:
            return f"{st.tool_tag}-modified-history"
    return ""


def _write_prelaunch_baseline(st: DispatchState) -> None:
    if st.answers_file is not None or st.prelaunch_porcelain.exists():
        return
    raw = _git(st.repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=all", binary=True).stdout
    _write_bytes_atomic(st.prelaunch_porcelain, raw)
    index_nonempty = _git(st.repo_root, "diff", "--cached", "--quiet", "--no-ext-diff").returncode != 0
    _write_text_atomic(st.prelaunch_index_flag, f"PRELAUNCH_INDEX_NONEMPTY={str(index_nonempty).lower()}\n")
    parsed = _parse_porcelain_z(st.prelaunch_porcelain)
    lines: list[str] = []
    for rel in sorted(parsed.paths):
        full = st.repo_root / rel
        try:
            digest = hashlib.sha256(full.read_bytes()).hexdigest()
        except OSError:
            digest = "missing"
        lines.append(f"{digest}\t{rel}")
    _write_text_atomic(st.prelaunch_digests, "\n".join(lines) + ("\n" if lines else ""))


def _manifest_legacy_fingerprint(obj: object) -> bool:
    return isinstance(obj, dict) and "schema_version" not in obj and set(obj.keys()) <= {"status", "summary", "checks"}


def _json_load(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _coder_scout_archetype_count(path: Path) -> int | None:
    obj = _json_load(path)
    if not isinstance(obj, dict) or not isinstance(obj.get("archetypes"), list):
        return None
    return len(obj["archetypes"])


def _write_coder_scout_status(tmpdir: Path, status: str, manifest: Path, producer: str) -> None:
    _write_text_atomic(
        tmpdir / "step2-scout-coder-status.env",
        f"SCOUT_CODER_STATUS={status}\n"
        f"SCOUT_CODER_MANIFEST={manifest}\n"
        f"SCOUT_CODER_PRODUCER={producer}\n",
    )


def _warn_invalid_coder_scout(producer: str) -> None:
    producer_label = "main agent" if producer == "main-agent" else "external coder"
    print(
        f"**⚠ implement Step 2: {producer_label} dynamic-archetype manifest missing or invalid; Step 5 will use static reviewers only.**",
        file=sys.stderr,
    )


def normalize_coder_scout(
    *,
    tmpdir: Path,
    input_path: Path,
    producer: str = "external",
) -> str:
    """Normalize a coder-produced scout manifest for /implement Step 5."""
    scout_manifest = tmpdir / "scout-coder-manifest.json"
    marker = tmpdir / "step2-external-scout-eligible.txt"
    filtered_tmp = tmpdir / f"scout-coder-manifest.filtered.{os.getpid()}.json"
    raw_count = _coder_scout_archetype_count(input_path)
    status = "missing-or-invalid"
    try:
        if raw_count is not None:
            result = _invoke_cli(
                [
                    "scout",
                    "filter-manifest",
                    str(input_path),
                    str(filtered_tmp),
                    "--max-archetypes",
                    "3",
                    "--mode",
                    "review",
                ]
            )
            kv = _parse_kv(result.stdout)
            filtered_count = _coder_scout_archetype_count(filtered_tmp)
            filter_status = kv.get("SCOUT_STATUS", "")
            filter_ok = result.returncode == 0 and filter_status in {"ok", "empty"} and filtered_count is not None
            if filter_ok and (raw_count == 0 or (filtered_count or 0) > 0):
                status = "ok"
                filtered_tmp.replace(scout_manifest)
            else:
                _write_text_atomic(scout_manifest, '{"archetypes":[]}\n')
        else:
            _write_text_atomic(scout_manifest, '{"archetypes":[]}\n')
    finally:
        with contextlib.suppress(OSError):
            filtered_tmp.unlink()
    if status == "ok":
        _write_text_atomic(marker, "eligible\n")
    else:
        with contextlib.suppress(OSError):
            marker.unlink()
        _warn_invalid_coder_scout(producer)
    _write_coder_scout_status(tmpdir, status, scout_manifest, producer)
    return status


def normalize_coder_scout_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement normalize-coder-scout")
    parser.add_argument("--tmpdir", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--producer", choices=("external", "main-agent"), default="external")
    args = parser.parse_args(argv)
    tmpdir = Path(args.tmpdir)
    if not tmpdir.is_dir():
        print(f"implement normalize-coder-scout: --tmpdir not a directory: {tmpdir}", file=sys.stderr)
        return 2
    _rehydrate_plugin_root(tmpdir)
    status = normalize_coder_scout(tmpdir=tmpdir, input_path=Path(args.input), producer=args.producer)
    _emit_kv(key="SCOUT_CODER_STATUS", value=status)
    _emit_kv(key="SCOUT_CODER_MANIFEST", value=str(tmpdir / "scout-coder-manifest.json"))
    return 0


def _emit_manifest_invalid_or_recover(st: DispatchState, status: str, raw_obj: object | None) -> int:
    if not isinstance(raw_obj, dict):
        return st.emit_bailed("manifest-schema-invalid")
    if status != "complete" and not (status == "" and _manifest_legacy_fingerprint(raw_obj)):
        return st.emit_bailed("manifest-schema-invalid")
    prelaunch_index_nonempty = "false"
    if st.prelaunch_index_flag.is_file():
        for line in st.prelaunch_index_flag.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("PRELAUNCH_INDEX_NONEMPTY="):
                prelaunch_index_nonempty = line.split("=", 1)[1]
                break
    if prelaunch_index_nonempty == "true":
        return st.emit_bailed("manifest-schema-invalid")
    post = _git(st.repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=all", binary=True).stdout
    _write_bytes_atomic(st.postlaunch_porcelain, post)
    ok = compute_recovery_paths(
        repo_root=st.repo_root,
        tmpdir=st.tmpdir,
        prelaunch_porcelain=st.prelaunch_porcelain,
        postlaunch_porcelain=st.postlaunch_porcelain,
        prelaunch_digests=st.prelaunch_digests,
        out_file=st.recovery_paths_file,
    )
    if not ok:
        return st.emit_bailed("manifest-schema-invalid")
    roots = _submodule_roots(st.repo_root)
    for rel in st.recovery_paths_file.read_bytes().split(b"\0"):
        if not rel:
            continue
        path = rel.decode("utf-8", "surrogateescape")
        if _path_under_submodule(path, roots):
            return st.emit_bailed("submodule-dirty")
    reason = _post_implementer_safety_reason(st)
    if reason:
        return st.emit_bailed(reason)
    invalid = st.tmpdir / "manifest-raw.invalid.json"
    if st.manifest_raw_path.exists():
        st.manifest_raw_path.replace(invalid)
    _write_text_atomic(
        st.tmpdir / "recovery-metadata.json",
        json.dumps(
            {
                "schema_version": 1,
                "recovery_from": "manifest-schema-invalid",
                "prior_tool": st.tool_tag,
                "recovery_paths_file": st.recovery_paths_file.name,
            },
            separators=(",", ":"),
        )
        + "\n",
    )
    _emit_kv(key="STATUS", value="claude_fallback")
    _emit_kv(key="TOOL", value=st.tool_tag)
    if st.transcript_path.exists() and st.transcript_path.stat().st_size > 0:
        _emit_kv(key="TRANSCRIPT", value=str(st.transcript_path))
    if st.sidecar_log.exists() and st.sidecar_log.stat().st_size > 0:
        _emit_kv(key="SIDECAR_LOG", value=str(st.sidecar_log))
    _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
    _emit_kv(key="RECOVERY_FROM", value="manifest-schema-invalid")
    _emit_kv(key="RECOVERY_PRIOR_TOOL", value=st.tool_tag)
    _emit_kv(key="RECOVERY_PATHS_FILE", value=str(st.recovery_paths_file))
    _clear_external_scout_state(st.tmpdir)
    return 0


def _manifest_complete_salvageable(path: Path) -> bool:
    obj = _json_load(path)
    return isinstance(obj, dict) and str(obj.get("schema_version", "")) == "1" and obj.get("status") == "complete"


def _normalize_scout(st: DispatchState) -> None:
    st.scout_status = normalize_coder_scout(
        tmpdir=st.tmpdir,
        input_path=st.launch_scout_manifest,
        producer="external",
    )


def _validate_manifest_paths(st: DispatchState, obj: dict[str, Any]) -> str:
    roots = _submodule_roots(st.repo_root)
    paths = [
        item["path"]
        for item in obj.get("files_touched", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    paths.extend(item for item in obj.get("tests_added_or_modified", []) if isinstance(item, str))
    for p in paths:
        if "\x00" in p or p.startswith("/") or ".." in p or _path_under_submodule(p, roots):
            return "protected-path-modified"
    return ""


def _complete_schema_valid(obj: dict[str, Any]) -> bool:
    return (
        isinstance(obj.get("files_touched"), list)
        and len(obj["files_touched"]) > 0
        and all(isinstance(item, dict) and isinstance(item.get("path"), str) for item in obj["files_touched"])
        and isinstance(obj.get("commit_message"), str)
        and len(obj["commit_message"]) > 0
        and isinstance(obj.get("summary_bullets"), list)
        and 1 <= len(obj["summary_bullets"]) <= SUMMARY_BULLETS_MAX
        and isinstance(obj.get("tests_added_or_modified"), list)
        and isinstance(obj.get("todos_left"), list)
        and isinstance(obj.get("oos_observations"), list)
    )


def _sanitize_manifest_obj(obj: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(obj)
    for key in ("commit_message",):
        if isinstance(sanitized.get(key), str):
            sanitized[key] = redact.redact_secrets_only(sanitized[key])
    for key in ("summary_bullets", "todos_left"):
        if isinstance(sanitized.get(key), list):
            sanitized[key] = [redact.redact_secrets_only(v) if isinstance(v, str) else v for v in sanitized[key]]
    if isinstance(sanitized.get("oos_observations"), list):
        out: list[Any] = []
        for item in sanitized["oos_observations"]:
            if not isinstance(item, dict):
                out.append(item)
                continue
            new = dict(item)
            for key in ("title", "description", "focus-area", "focus_area"):
                if isinstance(new.get(key), str):
                    new[key] = redact.redact_secrets_only(new[key])
            out.append(new)
        sanitized["oos_observations"] = out
    return sanitized


def _append_materialize_oos_failure(st: DispatchState, log: Path, exit_code: int) -> None:
    _invoke_cli([
        "run-log",
        "append-failure",
        "--log",
        str(st.tmpdir / "execution-issues.md"),
        "--site",
        "step2-materialize-manifest-oos",
        "--tool",
        "cli.py oos materialize-manifest",
        "--exit-code",
        str(exit_code),
        "--category",
        "Tool Failures",
        "--output-file",
        str(log),
        "--redact",
    ], cwd=st.repo_root)


def _oos_materialize_should_bail(*, count_rc: int, count_str: str, oos_nonempty: bool, materialize_failed: bool) -> bool:
    if count_rc != 0:
        return True
    if materialize_failed and count_str.isdigit() and int(count_str) > 0:
        return True
    return materialize_failed and oos_nonempty


def _materialize_oos(st: DispatchState, *, oos_observations_nonempty: bool = False) -> str:
    log = st.tmpdir / "materialize-manifest-oos.log"
    log.write_text("", encoding="utf-8")
    count_rc = 0
    count_str = ""
    materialize_failed = False

    try:
        count_result = file_oos.materialize_manifest_oos(st.manifest_path, st.tmpdir, count_only=True)
        count_str = str(count_result)
        count_rc = 0
    except (TypeError, ValueError, RuntimeError, OSError) as exc:
        log.write_text(str(exc) + "\n", encoding="utf-8")
        count_rc = 1

    try:
        _ = file_oos.materialize_manifest_oos(st.manifest_path, st.tmpdir, count_only=False)
    except (TypeError, ValueError, RuntimeError, OSError) as exc:
        with log.open("a", encoding="utf-8") as handle:
            handle.write(str(exc) + "\n")
        materialize_failed = True

    if materialize_failed:
        _append_materialize_oos_failure(st, log, 1)
    if _oos_materialize_should_bail(
        count_rc=count_rc,
        count_str=count_str,
        oos_nonempty=oos_observations_nonempty,
        materialize_failed=materialize_failed,
    ):
        return "manifest-oos-materialization-failed"
    return ""


def _dispatch_state(args: argparse.Namespace, repo_root: Path, tmpdir: Path, plugin_root: Path) -> DispatchState:
    tool = args.coder
    manifest_path = tmpdir / "manifest.json"
    qa_pending_path = tmpdir / "qa-pending.json"
    transcript = tmpdir / f"{tool}-impl-transcript.txt"
    launch_scout = tmpdir / "scout-coder-manifest.json"
    if tool == "codex":
        out_dir = tmpdir / "codex-step2-out"
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = out_dir / "manifest.json"
        qa_pending_path = out_dir / "qa-pending.json"
        transcript = out_dir / f"{tool}-impl-transcript.txt"
        launch_scout = out_dir / "scout-coder-manifest.json"
    return DispatchState(
        repo_root=repo_root,
        tmpdir=tmpdir,
        plan_file=Path(args.plan_file),
        feature_file=Path(args.feature_file),
        coder=tool,
        cursor_present=args.cursor_present or "false",
        cursor_binary_found=args.cursor_binary_found or "",
        codex_binary_found=args.codex_binary_found or "",
        answers_file=Path(args.answers) if args.answers else None,
        plugin_root=plugin_root,
        tool_tag=tool,
        manifest_path=manifest_path,
        manifest_raw_path=tmpdir / "manifest-raw.json",
        qa_pending_path=qa_pending_path,
        transcript_path=transcript,
        sidecar_log=tmpdir / f"{tool}-impl.log",
        scout_coder_manifest=tmpdir / "scout-coder-manifest.json",
        launch_scout_manifest=launch_scout,
        external_scout_marker=tmpdir / "step2-external-scout-eligible.txt",
        baseline_file=tmpdir / "step2-baseline.txt",
        prelaunch_porcelain=tmpdir / "step2-prelaunch-porcelain.nul",
        postlaunch_porcelain=tmpdir / "step2-postlaunch-porcelain.nul",
        prelaunch_digests=tmpdir / "step2-prelaunch-content-digests.txt",
        prelaunch_index_flag=tmpdir / "step2-prelaunch-index.env",
        recovery_paths_file=tmpdir / "step2-recovery-paths.nul",
        resume_count_file=tmpdir / f"{tool}-resume-count.txt",
        spawn_branch_file=tmpdir / "step2-spawn-branch.txt",
        spawn_coder_file=tmpdir / "step2-spawn-coder.txt",
        runtime_failure_token=f"{tool}-runtime-failure",
        bailed_no_reason_token=f"{tool}-bailed-no-reason",
        requires_head_unchanged=(tool == "cursor"),
        nonzero_exit_warn_token="WARN_CODEX_NONZERO_EXIT" if tool == "codex" else "",
    )


def _launcher_args(st: DispatchState) -> list[str]:
    args = [
        "agent",
        f"launch-{st.tool_tag}-implement",
        "--transcript-path",
        str(st.transcript_path),
        "--sidecar-log",
        str(st.sidecar_log),
        "--manifest-path",
        str(st.manifest_path),
        "--qa-pending-path",
        str(st.qa_pending_path),
        "--scout-manifest-path",
        str(st.launch_scout_manifest),
        "--plan-file",
        str(st.plan_file),
        "--feature-file",
        str(st.feature_file),
        "--agent-prompt",
        str(st.plugin_root / "agents" / f"{st.tool_tag}-implementer.md"),
        "--timeout",
        "7200",
    ]
    cap = os.environ.get("LARCH_TOKEN_BUDGET_CAP_IMPLEMENT", "")
    if cap:
        args.extend(["--token-budget-cap", cap])
    if st.answers_file is not None:
        args.extend(["--answers-file", str(st.answers_file)])
    return args


def _run_launcher(st: DispatchState) -> tuple[int, dict[str, str], str]:
    result = _invoke_cli(_launcher_args(st), cwd=st.repo_root)
    out = (result.stdout or "")[:65536]
    return result.returncode, _parse_kv(out), out + (result.stderr or "")


def _append_warning(st: DispatchState, text: str) -> None:
    # exec_issue_detail counts/renders only lines that start with "- "; normalize
    # plain warning text to a bullet so it is not dropped from the final summary.
    entry = text if text.startswith("- ") else f"- {text}"
    _invoke_cli(["run-log", "append-entry", "--log", str(st.tmpdir / "execution-issues.md"), "--category", "Warnings", "--entry", entry])


def _working_tree_touched_paths_and_failures(repo_root: Path) -> tuple[set[str] | None, list[str]]:
    probes = [
        ("git diff --name-only HEAD", ("diff", "--name-only", "HEAD")),
        ("git ls-files --others --exclude-standard", ("ls-files", "--others", "--exclude-standard")),
    ]
    touched: set[str] = set()
    failures: list[str] = []
    for label, args in probes:
        result = _git(repo_root, *args)
        if result.returncode != 0:
            failures.append(label)
            continue
        touched.update(line for line in str(result.stdout).splitlines() if line)
    if failures:
        return None, failures
    return touched, []


def _working_tree_touched_paths(repo_root: Path) -> set[str] | None:
    touched, _failures = _working_tree_touched_paths_and_failures(repo_root)
    return touched


def _explicit_plan_scope_paths(plan_text: str) -> list[str]:
    return issue_wire.extract_scope_paths(plan_text=plan_text, use_fallback=False, include_optional=False)


def _plan_coverage_uncovered_paths(st: DispatchState, touched: set[str] | None) -> list[str] | None:
    if touched is None:
        return None
    try:
        plan_text = st.plan_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _append_warning(st=st, text=f"Step 7a.1 — could not read plan file for plan-file coverage: {st.plan_file}: {exc}")
        return None
    explicit = _explicit_plan_scope_paths(plan_text)
    if not explicit:
        return []
    return sorted(path for path in explicit if path not in touched)


def step2_dispatch_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py implement step2-dispatch")
    parser.add_argument("--tmpdir", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--feature-file", required=True)
    parser.add_argument("--coder", default="")
    parser.add_argument("--codex-available", default="")
    parser.add_argument("--cursor-present", default="")
    parser.add_argument("--codex-present", default="")
    parser.add_argument("--cursor-available", default="")
    parser.add_argument("--codex-binary-found", default="")
    parser.add_argument("--cursor-binary-found", default="")
    parser.add_argument("--answers", default="")
    args = parser.parse_args(argv)

    if args.coder and args.codex_available:
        _err("implement step2-dispatch: --coder and --codex-available are mutually exclusive")
        return 2
    if args.codex_available:
        if args.codex_available == "true":
            _err("implement step2-dispatch: WARNING: --codex-available is deprecated; pass --coder codex instead")
            args.coder = "codex"
        elif args.codex_available == "false":
            _err("implement step2-dispatch: WARNING: --codex-available is deprecated; pass --coder claude instead")
            args.coder = "claude"
        else:
            _err(f"implement step2-dispatch: --codex-available must be 'true' or 'false', got: {args.codex_available}")
            return 2
    if not args.coder:
        _err("implement step2-dispatch: --coder is required")
        return 2
    if args.coder not in _SAFE_CODERS:
        _err(f"implement step2-dispatch: --coder must be one of {{claude,codex,cursor}}, got: {args.coder}")
        return 2
    for flag_name in ("codex_present", "cursor_present", "cursor_available", "codex_binary_found", "cursor_binary_found"):
        value = getattr(args, flag_name)
        if value and value not in {"true", "false"}:
            _err(f"implement step2-dispatch: --{flag_name.replace('_', '-')} must be 'true', 'false', or empty, got: {value}")
            return 2
    tmpdir_raw = Path(args.tmpdir)
    if not tmpdir_raw.is_dir():
        _err(f"implement step2-dispatch: --tmpdir not a directory: {tmpdir_raw}")
        return 2
    tmpdir = tmpdir_raw.resolve()
    os.environ["IMPLEMENT_TMPDIR"] = str(tmpdir)
    if (tmpdir / "session-id").is_file():
        session_id = (tmpdir / "session-id").read_text(encoding="utf-8", errors="replace").strip()
        if session_id:
            os.environ["LARCH_TOKEN_SESSION_ID"] = session_id
    if (tmpdir / "claude-source.env").is_file():
        os.environ["LARCH_CLAUDE_SOURCE_FILE"] = str(tmpdir / "claude-source.env")
    if not Path(args.plan_file).is_file():
        _err(f"implement step2-dispatch: --plan-file not found: {args.plan_file}")
        return 2
    if not Path(args.feature_file).is_file():
        _err(f"implement step2-dispatch: --feature-file not found: {args.feature_file}")
        return 2
    if args.coder == "claude":
        _clear_external_scout_state(tmpdir)
        _emit_kv(key="STATUS", value="claude_fallback")
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
        return 0
    session_env = tmpdir / "session-env.sh"
    if not args.cursor_binary_found:
        args.cursor_binary_found = _binary_available(session_env, "CURSOR_BINARY_FOUND", "cursor")
    if not args.codex_binary_found:
        args.codex_binary_found = _binary_available(session_env, "CODEX_BINARY_FOUND", "codex")
    if args.coder == "cursor" and args.cursor_binary_found != "true":
        _clear_external_scout_state(tmpdir)
        _emit_kv(key="STATUS", value="claude_fallback")
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
        return 0
    if args.coder == "codex" and args.codex_binary_found != "true":
        _clear_external_scout_state(tmpdir)
        _emit_kv(key="STATUS", value="claude_fallback")
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
        return 0

    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("LARCH_CLAUDE_PLUGIN_ROOT") or _PLUGIN_ROOT).resolve()
    repo_result = _run(["git", "rev-parse", "--show-toplevel"])
    if repo_result.returncode != 0 or not repo_result.stdout.strip():
        _err("implement step2-dispatch: must be invoked from within a git working tree (git rev-parse --show-toplevel failed)")
        return 2
    repo_root = Path(repo_result.stdout.strip()).resolve()
    _invoke_cli(["timing", "mark", "Step 2 — implementation"], cwd=repo_root)
    st = _dispatch_state(args, repo_root, tmpdir, plugin_root)
    if not (plugin_root / "agents" / f"{st.tool_tag}-implementer.md").is_file():
        _err(f"implement step2-dispatch: agent prompt missing: {plugin_root / 'agents' / (st.tool_tag + '-implementer.md')}")
        return 2

    if st.spawn_coder_file.is_file():
        if st.spawn_coder_file.read_text(encoding="utf-8", errors="replace").strip() != st.coder:
            return st.emit_bailed("coder-mismatch-tmpdir-reuse")
    else:
        _write_text_atomic(st.spawn_coder_file, st.coder + "\n")
    if not st.baseline_file.is_file():
        _write_text_atomic(st.baseline_file, _git_stdout(repo_root, "rev-parse", "HEAD") + "\n")
    st.baseline_sha = st.baseline_file.read_text(encoding="utf-8", errors="replace").strip()
    if not st.spawn_branch_file.is_file():
        _write_text_atomic(st.spawn_branch_file, _git_stdout(repo_root, "symbolic-ref", "-q", "--short", "HEAD") + "\n")
    st.spawn_branch = st.spawn_branch_file.read_text(encoding="utf-8", errors="replace").strip()
    session_env = tmpdir / "session-env.sh"
    parent_issue = tmpdir / "parent-issue.md"
    issue_from_parent = _session_get(file=parent_issue, key="ISSUE_NUMBER", default="") if parent_issue.is_file() else ""
    forked_target = _session_get(file=session_env, key="FORKED_TARGET", default="false") if session_env.is_file() else "false"
    issue_anchored = bool(issue_from_parent) or session_env.is_file()
    if forked_target != "true" and issue_anchored and (not st.spawn_branch or st.spawn_branch == "HEAD"):
        return st.emit_bailed("detached-head-prohibited")
    if forked_target != "true" and issue_anchored and st.spawn_branch in {"main", "master"}:
        return st.emit_bailed("main-branch-prohibited")

    resume_count = 0
    if st.resume_count_file.is_file():
        raw = st.resume_count_file.read_text(encoding="utf-8", errors="replace").strip()
        if raw.isdigit():
            resume_count = int(raw)
        else:
            return st.emit_bailed("manifest-schema-invalid")
    if st.answers_file is not None:
        if not st.answers_file.is_file():
            _err(f"implement step2-dispatch: --answers given but path does not exist: {st.answers_file}")
            return 2
        resume_count += 1
        _write_text_atomic(st.resume_count_file, f"{resume_count}\n")
    if resume_count > RESUME_CAP:
        return st.emit_bailed("qa-loop-exceeded")

    for path in (st.manifest_path, st.manifest_raw_path, st.qa_pending_path, st.transcript_path, st.sidecar_log, st.launch_scout_manifest):
        with contextlib.suppress(OSError):
            path.unlink()
    _clear_external_scout_state(tmpdir)
    _write_prelaunch_baseline(st)

    wrapper_rc, kv, _ = _run_launcher(st)
    if wrapper_rc == WRAPPER_VALIDATION_RC:
        return st.emit_bailed("wrapper-validation-failure")
    launcher_exit = kv.get("LAUNCHER_EXIT", "99")
    manifest_written = kv.get("MANIFEST_WRITTEN", "false")
    launcher_status = kv.get("STATUS", "")
    if launcher_status == "cap_hit":
        return st.emit_bailed("cap_hit")
    if (wrapper_rc != 0 or manifest_written != "true" or launcher_exit != "0") and manifest_written != "true":
        dirty = _git_stdout(repo_root, "status", "--porcelain")
        index_lock = repo_root / ".git" / "index.lock"
        current_head = _git_stdout(repo_root, "rev-parse", "HEAD")
        if dirty or index_lock.exists() or current_head != st.baseline_sha:
            return st.emit_bailed("dirty-state-after-timeout")
        wrapper_rc, kv, _ = _run_launcher(st)
        if wrapper_rc == WRAPPER_VALIDATION_RC:
            return st.emit_bailed("wrapper-validation-failure")
        launcher_exit = kv.get("LAUNCHER_EXIT", "99")
        manifest_written = kv.get("MANIFEST_WRITTEN", "false")
        launcher_status = kv.get("STATUS", "")
        if launcher_status == "cap_hit":
            return st.emit_bailed("cap_hit")
    if wrapper_rc != 0:
        return st.emit_bailed(st.runtime_failure_token)
    if manifest_written != "true":
        return st.emit_bailed(st.runtime_failure_token)
    warn_nonzero = False
    if launcher_exit != "0":
        if st.coder == "codex" and _manifest_complete_salvageable(st.manifest_path):
            warn_nonzero = True
            _append_warning(st=st, text=f"Step 4 — {st.tool_tag} exited non-zero (LAUNCHER_EXIT={launcher_exit}) after atomically writing a complete manifest; not discarding it — continuing to validation/commit ({st.nonzero_exit_warn_token}=true). A self-verification step likely failed after the implementation work completed.")
        else:
            return st.emit_bailed(st.runtime_failure_token)

    if not st.manifest_path.is_file() or st.manifest_path.stat().st_size == 0:
        return st.emit_bailed("manifest-missing")
    shutil.copyfile(st.manifest_path, st.manifest_raw_path)
    raw_obj = _json_load(st.manifest_raw_path)
    status = raw_obj.get("status", "") if isinstance(raw_obj, dict) and isinstance(raw_obj.get("status", ""), str) else ""
    schema_version = raw_obj.get("schema_version", "") if isinstance(raw_obj, dict) else ""
    if schema_version and str(schema_version) != "1":
        return st.emit_bailed("manifest-schema-invalid")
    if str(schema_version) != "1":
        return _emit_manifest_invalid_or_recover(st, status, raw_obj)
    if status not in {"complete", "needs_qa", "bailed"}:
        return _emit_manifest_invalid_or_recover(st, status, raw_obj)
    assert isinstance(raw_obj, dict)
    if status == "complete":
        if not _complete_schema_valid(raw_obj):
            return _emit_manifest_invalid_or_recover(st, status, raw_obj)
    elif status == "needs_qa":
        nq = raw_obj.get("needs_qa")
        questions = nq.get("questions") if isinstance(nq, dict) else None
        if not (isinstance(questions, list) and questions):
            repaired = False
            qa_obj = _json_load(st.qa_pending_path)
            if isinstance(qa_obj, dict) and isinstance(qa_obj.get("items"), list) and qa_obj["items"]:
                repaired_questions: list[dict[str, str]] = []
                for idx, item in enumerate(qa_obj["items"]):
                    if isinstance(item, dict):
                        parts = [f"{label}: {item[key]}" for key, label in (("area", "Area"), ("risk", "Risk"), ("suggested_check", "Suggested check")) if item.get(key)]
                        repaired_questions.append({"id": f"q{idx + 1}", "text": ". ".join(parts)})
                if repaired_questions:
                    _write_text_atomic(st.qa_pending_path, json.dumps({"questions": repaired_questions}) + "\n")
                    repaired = True
            if not repaired:
                return st.emit_bailed("manifest-schema-invalid")
        qa_obj = _json_load(st.qa_pending_path)
        if not (isinstance(qa_obj, dict) and isinstance(qa_obj.get("questions"), list) and qa_obj["questions"]):
            return st.emit_bailed("qa-pending-missing")
    elif status == "bailed" and (not isinstance(raw_obj.get("bail_reason"), str) or not raw_obj["bail_reason"]):
        return _emit_manifest_invalid_or_recover(st, status, raw_obj)

    if status != "bailed":
        reason = _post_implementer_safety_reason(st)
        if reason:
            return st.emit_bailed(reason)
        _normalize_scout(st)

    uncovered_plan_path_count = 0
    if status == "complete":
        invalid = _validate_manifest_paths(st, raw_obj)
        if invalid:
            return st.emit_bailed(invalid)
        touched, touch_probe_failures = _working_tree_touched_paths_and_failures(repo_root)
        if touched is None:
            _append_warning(st=st, text="Step 7a.1 — skipped working-tree touched-path diagnostics because git probe(s) failed: " + ", ".join(touch_probe_failures))
        else:
            # Diagnostic-only undeclared path warning.
            declared = {item.get("path") for item in raw_obj.get("files_touched", []) if isinstance(item, dict)} | {p for p in raw_obj.get("tests_added_or_modified", []) if isinstance(p, str)}
            missing = sorted(p for p in touched if p and p not in declared)
            if missing:
                _append_warning(st=st, text=f"- **Step 7a.1 — {len(missing)} working-tree path(s) not declared in manifest files_touched/tests_added_or_modified (may include pre-existing dirty files). First 5**: " + ", ".join(missing[:5]))
        uncovered = _plan_coverage_uncovered_paths(st, touched)
        if uncovered:
            uncovered_plan_path_count = len(uncovered)
            _append_warning(st=st, text=f"- **Step 7a.1 — {len(uncovered)} explicit plan-listed path(s) untouched by the working-tree delta before dispatcher commit. First 10**: " + ", ".join(uncovered[:10]))
        commit_msg = redact.redact_secrets_only(str(raw_obj["commit_message"]))
        commit_msg_file = st.tmpdir / f"{st.tool_tag}-commit-message.txt"
        _write_text_atomic(commit_msg_file, commit_msg)
        commit_stderr = st.tmpdir / f"{st.tool_tag}-commit-stderr.txt"
        add = subprocess.run(
            [GIT_BIN, "-C", str(repo_root), "add", "-A"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False
        )
        if add.returncode != 0:
            commit_stderr.write_text(add.stderr or "git add failed", encoding="utf-8", errors="replace")
            with contextlib.suppress(OSError):
                st.manifest_path.unlink()
            with contextlib.suppress(OSError):
                st.manifest_raw_path.unlink()
            return st.emit_bailed("commit-failed")
        commit = subprocess.run(
            [GIT_BIN, "-C", str(repo_root), "commit", "-F", str(commit_msg_file)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False
        )
        if commit.returncode != 0:
            commit_stderr.write_text(commit.stderr, encoding="utf-8", errors="replace")
            with contextlib.suppress(OSError):
                st.manifest_path.unlink()
            with contextlib.suppress(OSError):
                st.manifest_raw_path.unlink()
            return st.emit_bailed("commit-failed")
        with contextlib.suppress(OSError):
            commit_stderr.unlink()
        _invoke_cli(["run-log", "flush"], cwd=repo_root)

    sanitized = _sanitize_manifest_obj(raw_obj)
    _write_text_atomic(st.manifest_path, json.dumps(sanitized, indent=2, sort_keys=False) + "\n")
    if status == "complete":
        oos_obs = raw_obj.get("oos_observations")
        oos_nonempty = isinstance(oos_obs, list) and bool(oos_obs)
        reason = _materialize_oos(st, oos_observations_nonempty=oos_nonempty)
        if reason:
            return st.emit_bailed(reason)

    if status == "complete":
        _emit_kv(key="STATUS", value="complete")
        _emit_kv(key="TOOL", value=st.tool_tag)
        _emit_kv(key="MANIFEST", value=str(st.manifest_path))
        _emit_kv(key="TRANSCRIPT", value=str(st.transcript_path))
        _emit_kv(key="SIDECAR_LOG", value=str(st.sidecar_log))
        _emit_kv(key="SCOUT_CODER_MANIFEST", value=str(st.scout_coder_manifest))
        _emit_kv(key="SCOUT_CODER_STATUS", value=st.scout_status)
        if warn_nonzero and st.nonzero_exit_warn_token:
            _emit_kv(key=st.nonzero_exit_warn_token, value="true")
        if uncovered_plan_path_count:
            _emit_kv(key="WARN_PLAN_FILES_UNTOUCHED", value="true")
            _emit_kv(key="WARN_PLAN_FILES_UNTOUCHED_COUNT", value=uncovered_plan_path_count)
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="forbidden")
    elif status == "needs_qa":
        _emit_kv(key="STATUS", value="needs_qa")
        _emit_kv(key="TOOL", value=st.tool_tag)
        _emit_kv(key="MANIFEST", value=str(st.manifest_path))
        _emit_kv(key="QA_PENDING", value=str(st.qa_pending_path))
        _emit_kv(key="TRANSCRIPT", value=str(st.transcript_path))
        _emit_kv(key="SIDECAR_LOG", value=str(st.sidecar_log))
        _emit_kv(key="SCOUT_CODER_MANIFEST", value=str(st.scout_coder_manifest))
        _emit_kv(key="SCOUT_CODER_STATUS", value=st.scout_status)
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="forbidden")
    else:
        reason = str(raw_obj.get("bail_reason") or st.bailed_no_reason_token)
        reason = re.sub(r"\s+", " ", "".join(ch for ch in reason if ch >= " " and ch != "\x7f")).strip()[:200] or st.bailed_no_reason_token
        _emit_kv(key="STATUS", value="bailed")
        _emit_kv(key="REASON", value=reason)
        _emit_kv(key="TOOL", value=st.tool_tag)
        _emit_kv(key="MANIFEST", value=str(st.manifest_path))
        _emit_kv(key="TRANSCRIPT", value=str(st.transcript_path))
        _emit_kv(key="SIDECAR_LOG", value=str(st.sidecar_log))
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="forbidden")
    return 0
