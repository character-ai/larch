"""Session/state lifecycle verbs for the larch Python runtime."""
# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import sys
import tempfile
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Callable, Iterable, Mapping

from larch.agents import agents
from larch.core import config
from larch import io as larch_io
from larch.core import logging_util
from larch.core import proc
from larch.errors import ShipError
from larch.git import gh
from larch.core.proc import Runner

_BOOL = {"true", "false"}
_SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_./~+-]+$")
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
# Non-unique placeholder run-log directory names (e.g. ``run-1``). These must
# never be carried forward from a previous session: they collide across runs and
# clones and get re-committed to the repo (issue #4397). Real UUID run dirs and
# ``shared/`` are still carried so resume keeps prior batches.
_PLACEHOLDER_RUN_DIR_RE = re.compile(r"^run-[0-9]+$")
MAX_PATH_VALUE_LEN = 512
TMP_FALLBACK = "/tmp"  # noqa: S108 - parity fallback for larch session roots.
TMP_ROOT = Path(TMP_FALLBACK)

WRITE_ENV_KEYS = frozenset({
    "REPO",
    "REPO_UNAVAILABLE",
    "FORKED_TARGET",
    "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "LARCH_AUTO_MODE",
    "LARCH_TIMING_LEDGER",
    "LARCH_TOKEN_SESSION_ID",
    "LARCH_CLAUDE_SOURCE_FILE",
    "PREV_IMPLEMENT_TMPDIR",
    "LARCH_DYNAMIC_ARCHETYPES_MAX",
    "LARCH_RUN_ID",
    "LARCH_CLAUDE_PLUGIN_ROOT",
})
WRITE_DESIGN_ENV_KEYS = frozenset({
    "DESIGN_TMPDIR",
    "SESSION_TMPDIR",
    "SESSION_ID",
    "REPO",
    "REPO_ROOT",
    "ISSUE_NUMBER",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT",
    "CLAUDE_PLUGIN_ROOT",
    "LARCH_CLAUDE_SOURCE_FILE",
})
RUN_FLAG_KEYS = frozenset({"QUICK_MODE", "NO_ISSUES", "FORCE_REQUESTED", "SELF_REVIEW_REQUESTED", "SELF_IMPLEMENT_REQUESTED", "DIFFICULTY_OVERRIDE"})
# Core finalize state-file keys shared with finalize._COMMON_REQUIRED_KEYS.
# Single source of truth so the two lists cannot drift (and to avoid
# duplicate-code, pylint R0801).
FINALIZE_STATE_CORE_KEYS = (
    "BRANCH_NAME",
    "PR_NUMBER",
    "PR_TITLE",
    "PR_URL",
    "ISSUE_NUMBER",
    "REPO",
    "DRAFT",
    "MERGE",
    "DEFERRED",
    "REPO_UNAVAILABLE",
    "PR_CLOSED",
    "DESIGN_ONLY_DONE",
    "BAIL_NEEDS_USER_INPUT",
    "STALL_TRACKING",
)
RESTORE_FINALIZE_KEYS = (
    *FINALIZE_STATE_CORE_KEYS,
    "STALL_STEP",
    "DONE_RENAME_APPLIED",
    "RUN_ID",
    "EXPECTED_SESSION_ID",
    "EXPECTED_TMPDIR_BASENAME_PREFIX",
    "NO_LOGS_COMMIT",
)
RESTORE_FINALIZE_DEFAULTS = {
    "DESIGN_ONLY_DONE": "false",
    "DRAFT": "false",
    "MERGE": "false",
    "DEFERRED": "false",
    "REPO_UNAVAILABLE": "false",
    "PR_CLOSED": "false",
    "BAIL_NEEDS_USER_INPUT": "false",
    "STALL_TRACKING": "false",
    "DONE_RENAME_APPLIED": "false",
    "NO_LOGS_COMMIT": "false",
}
CALLER_ENV_KEYS = frozenset({
    "REPO",
    "REPO_UNAVAILABLE",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "LARCH_TOKEN_SESSION_ID",
    "LARCH_CLAUDE_SOURCE_FILE",
    "LARCH_TIMING_LEDGER",
    "PREV_IMPLEMENT_TMPDIR",
    "LARCH_DYNAMIC_ARCHETYPES_MAX",
})
# Shared /design wrapper-env defaults. design_lifecycle and plan_quality both
# build wrapper-env dicts that overlap on this common core; defining it once
# keeps the two literals from re-introducing a duplicate-code run (R0801).
COMMON_DESIGN_ENV_DEFAULTS: dict[str, str] = {
    "DESIGN_TMPDIR": "",
    "SESSION_TMPDIR": "",
    "SESSION_ID": "",
    "ISSUE_NUMBER": "",
    "ISSUE_TITLE": "",
    "HAS_CLARIFY_LABEL": "false",
    "REPO": "",
    "CODEX_BINARY_FOUND": "",
    "CURSOR_BINARY_FOUND": "",
    "IMPLEMENT_TMPDIR": "",
}
# Validator status keys shared by the Step 2b postplan and validator wrappers.
VALIDATOR_STATUS_ENV_DEFAULTS: dict[str, str] = {
    "STEP3_REVIEW_LOOP_STATUS": "",
    "LOOP_STATUS": "",
    "VALIDATE_STATUS": "",
    "VALIDATE_DEFECT_COUNT": "",
    "VALIDATE_MISSING_SCRIPT_COUNT": "",
    "VALIDATE_UNSAFE_TOKEN_COUNT": "",
    "VALIDATE_SKIPPED_COUNT": "",
    "VALIDATE_LOG_FILE": "",
    "_validator_target_file": "",
}
# CLI flag -> attribute/key name map shared by the design step2 wrapper parser
# (design_lifecycle) and the validator wrapper parser (plan_quality).
WRAPPER_VALUE_FLAGS: dict[str, str] = {
    "--session-env-path": "session_env_path",
    "--claude-pid": "claude_pid",
    "--plugin-root": "plugin_root",
    "--mode": "mode",
    "--site": "site",
    "--outcome": "outcome",
    "--step3-review-loop-status": "step3_review_loop_status",
    "--loop-status": "loop_status",
    "--validator-target-file": "validator_target_file",
    "--validate-log-file": "validate_log_file",
    "--validate-defect-count": "validate_defect_count",
    "--validate-unsafe-token-count": "validate_unsafe_token_count",
    "--validate-skipped-count": "validate_skipped_count",
}


def parse_allowlisted_env_line(
    *, raw: str,
    allowlist: frozenset[str] | set[str],
    name_validator: Callable[[str], bool] | None = None,
    reject_newline_rhs: bool = False,
) -> tuple[str, str] | None:
    """Parse one ``KEY=value`` (or ``export KEY=value``) line against an allowlist.

    Returns ``(key, value)`` when the line names an allowlisted key whose value
    is a single shell token, else ``None``. ``name_validator`` adds a syntactic
    key check; ``reject_newline_rhs`` rejects raw newlines before shell-splitting.
    """
    line = raw.strip()
    if not line or line.startswith("#"):
        return None
    line = line.removeprefix("export ")
    if "=" not in line:
        return None
    key, rhs = line.split("=", 1)
    key = key.strip()
    if key not in allowlist:
        return None
    if name_validator is not None and not name_validator(key):
        return None
    if reject_newline_rhs and ("\n" in rhs or "\r" in rhs):
        return None
    try:
        parts = shlex.split(rhs, posix=True)
    except ValueError:
        return None
    if len(parts) > 1:
        return None
    value = parts[0] if parts else ""
    if "\n" in value or "\r" in value:
        return None
    return key, value


def finalize_wrapper_env(merged: dict[str, str]) -> dict[str, str]:
    """Default codex/cursor binary detection, export ``merged`` into the process
    environment, and return it. Shared tail of the design and validator wrapper
    env resolvers.
    """
    if not merged.get("CODEX_BINARY_FOUND"):
        merged["CODEX_BINARY_FOUND"] = "true" if shutil.which("codex") else "false"
    if not merged.get("CURSOR_BINARY_FOUND"):
        merged["CURSOR_BINARY_FOUND"] = "true" if shutil.which("cursor") else "false"
    for key, value in merged.items():
        os.environ[key] = value
    return merged


def require_plugin_root() -> int:
    """Return 0 when CLAUDE_PLUGIN_ROOT is set to an expanded path, else 1 after
    printing a wrapper diagnostic. Shared plugin-root guard for the design and
    validator wrappers.
    """
    literal = "${CLAUDE_PLUGIN_ROOT}"
    value = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not value:
        print("/design wrapper: CLAUDE_PLUGIN_ROOT is empty; abort", file=sys.stderr)
        return 1
    if value == literal:
        print(f"/design wrapper: CLAUDE_PLUGIN_ROOT is the unexpanded template literal {literal}; abort", file=sys.stderr)
        return 1
    return 0


@dataclass(frozen=True)
class SessionSetupResult:
    session_tmpdir: Path
    session_id: str
    repo: str = ""
    repo_unavailable: str = "false"


@dataclass(frozen=True)
class GateResult:
    entry_gate: str
    skip_branch_check: str


def _scripts_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "scripts"


def _emit(text: str) -> None:
    logging_util.emit(text)


def _emit_kv(*, key: str, value: str) -> None:
    logging_util.emit_kv(key=key, value=value)


def _err(message: str) -> None:
    logging_util.BreadcrumbWriter().emit(message)


def _plain_err(message: str) -> None:
    print(message, file=sys.stderr)


def _is_bool(value: str) -> bool:
    return value in _BOOL


def _external_timeout() -> str:
    value = os.environ.get(config.ENV_LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT, "60")
    return value if value.isdigit() else "60"


def _validate_no_newlines(data: dict[str, str]) -> None:
    for key, value in data.items():
        if "\n" in value or "\r" in value:
            raise ValueError(f"value for {key} contains newline or carriage return")


def _validate_writer_keys(*, data: dict[str, str], allowed: frozenset[str]) -> None:
    for key in data:
        if key not in allowed:
            raise ValueError(f"disallowed writer key: {key}")


def _read_kv_file_text(path: Path) -> str:
    text = path.read_bytes().decode("utf-8", errors="replace")
    if "\r" in text:
        msg = f"session env file contains carriage return: {path}"
        raise ValueError(msg)
    return text


IMPLEMENT_SENTINEL_RELS = (
    Path("design-export") / "manifest.env",
    Path("review-round-summary.md"),
    Path(".bump-version-armed"),
    Path(".release-armed"),
)
IMPLEMENT_TMPDIR_TTL_SECONDS = 21600


def cleanup_cache_sessions_root(*, env: Mapping[str, str] | None = None) -> Path:
    environ = os.environ if env is None else env
    xdg = environ.get("XDG_CACHE_HOME")
    if xdg:
        base = xdg
    else:
        home = environ.get("HOME", "")
        base = f"{home}/.cache" if home else f"{TMP_FALLBACK}/.cache"
    return Path(base) / "larch" / "sessions"


def implement_session_roots(*, env: Mapping[str, str] | None = None) -> tuple[Path, ...]:
    return (
        cleanup_cache_sessions_root(env=env),
        TMP_ROOT,
        Path("/private/tmp"),
    )


def _resolved(path: Path) -> Path:
    return path.resolve(strict=False)


def _under(*, path: Path, root: Path) -> bool:
    try:
        resolved = _resolved(path)
        resolved_root = _resolved(root)
    except OSError:
        return False
    return resolved == resolved_root or resolved_root in resolved.parents


def _strictly_under(*, path: Path, root: Path) -> bool:
    try:
        resolved = _resolved(path)
        resolved_root = _resolved(root)
    except OSError:
        return False
    return resolved_root in resolved.parents


def is_allowed_session_tmpdir(path: str | Path) -> bool:
    candidate = Path(path)
    if not str(candidate):
        return False
    roots = (TMP_ROOT, Path("/private/tmp"), Path("/var/folders"), Path("/private/var/folders"), cleanup_cache_sessions_root())
    return any(_strictly_under(path=candidate, root=root) for root in roots)


def _writer_target_allowed(path: str | Path) -> bool:
    candidate = Path(path)
    roots = (TMP_ROOT, Path("/private/tmp"), Path("/var/folders"), Path("/private/var/folders"), cleanup_cache_sessions_root())
    return any(_under(path=candidate, root=root) for root in roots)


def _safe_output_parent(path: Path) -> bool:
    parent = path.parent
    return parent.exists() and parent.is_dir() and not parent.is_symlink()


def _atomic_write(*, path: Path, text: str, create_parent: bool = False, mode: int = 0o600) -> None:
    larch_io.atomic_write(path=path, text=text, create_parent=create_parent, mode=mode, temp_name=path.with_suffix(path.suffix + ".tmp"), nofollow=True, exclusive=True)


def _kv_text(data: dict[str, str] | Iterable[tuple[str, str]]) -> str:
    return larch_io.format_kvs(data)


def read_finalize_state(path: str | Path) -> dict[str, str]:
    target = Path(path)
    if not target.is_file():
        return {}
    data: dict[str, str] = {}
    try:
        lines = _read_kv_file_text(target).splitlines()
    except ValueError as exc:
        raise ShipError(str(exc)) from exc
    for line in lines:
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not _KEY_RE.match(key):
            continue
        try:
            parsed = shlex.split(value, posix=True)
        except ValueError:
            parsed = [value]
        data[key] = parsed[0] if len(parsed) == 1 else value
    for key, value in data.items():
        if "\n" in value or "\r" in value:
            msg = f"finalize-state value for {key} contains a newline"
            raise ShipError(msg)
    return data


def write_finalize_state_merged(*, path: str | Path, data: dict[str, str]) -> None:
    for key, value in data.items():
        if not _KEY_RE.match(key):
            msg = f"invalid finalize-state key: {key}"
            raise ShipError(msg)
        if "\n" in str(value) or "\r" in str(value):
            msg = f"finalize-state value for {key} contains a newline"
            raise ShipError(msg)
    _atomic_write(path=Path(path), text="".join(f"{key}={data[key]}\n" for key in sorted(data)), create_parent=True)


def _read_kv_raw(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    return larch_io.parse_kv(_read_kv_file_text(path), skip_comments=True)


def _read_first_raw_key(*, path: Path, key: str) -> str | None:
    for line in _read_kv_file_text(path).splitlines():
        if "=" not in line:
            continue
        found_key, value = line.split("=", 1)
        if found_key == key:
            return value
    return None


def _first_existing_implement_sentinel(candidate: Path) -> Path | None:
    for rel in IMPLEMENT_SENTINEL_RELS:
        sentinel = candidate / rel
        if sentinel.is_file():
            return sentinel
    return None


def _implement_tmpdir_ttl(env: Mapping[str, str]) -> int:
    raw = env.get("LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS", str(IMPLEMENT_TMPDIR_TTL_SECONDS))
    return int(raw) if raw.isdigit() else IMPLEMENT_TMPDIR_TTL_SECONDS


def resolve_implement_tmpdir(
    hook_cwd: str,
    *,
    env: Mapping[str, str] | None = None,
    now: int | None = None,
) -> str:
    if not hook_cwd:
        return ""
    environ = os.environ if env is None else env
    now_value = int(time.time()) if now is None else now
    best = ""
    best_mtime = -1
    session_id = environ.get("LARCH_TOKEN_SESSION_ID", "")
    for root in implement_session_roots(env=environ):
        try:
            candidates: list[Path] = list(root.glob("claude-implement-*")) if root.is_dir() else []
        except OSError:
            continue
        for candidate in candidates:
            try:
                if not candidate.is_dir():
                    continue
                sentinel = _first_existing_implement_sentinel(candidate)
                if sentinel is None:
                    continue
                keepalive = candidate / ".larch-keepalive"
                if not keepalive.is_file():
                    continue
                if _read_first_raw_key(path=keepalive, key="CLONE_PATH") != hook_cwd:
                    continue
                session_match = False
                if session_id:
                    if _read_first_raw_key(path=keepalive, key="SESSION_ID") != session_id:
                        continue
                    session_match = True
                mtime = int(sentinel.stat().st_mtime)
            except (OSError, ValueError):
                continue
            if not session_match:
                ttl = _implement_tmpdir_ttl(environ)
                if ttl > 0:
                    if now_value <= 0:
                        continue
                    if now_value - mtime >= ttl:
                        continue
            candidate_text = str(candidate)
            if mtime > best_mtime or (mtime == best_mtime and (not best or candidate_text < best)):
                best_mtime = mtime
                best = candidate_text
    return best


def resolve_implement_tmpdir_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session resolve-implement-tmpdir", add_help=False)
    parser.add_argument("--cwd", default="")
    try:
        args = parser.parse_args(argv)
        resolved = resolve_implement_tmpdir(args.cwd)
    except (OSError, ValueError, SystemExit) as exc:
        _plain_err(f"resolve-implement-tmpdir: {exc}")
        return 1
    if resolved:
        sys.stdout.write(resolved)
    return 0



def _valid_repo_value(value: str) -> bool:
    if not value:
        return True
    if value.startswith(("--", "/")) or "../" in value or "\\" in value:
        return False
    if "\n" in value or "\r" in value:
        return False
    return bool(_REPO_RE.match(value))

def _validate_plugin_root_value(value: str) -> bool:
    return bool(value) and len(value) <= MAX_PATH_VALUE_LEN and value.startswith("/") and bool(_SAFE_PATH_RE.match(value))


def _validate_path_arg_value(*, value: str, flag: str) -> None:
    if value and (len(value) > MAX_PATH_VALUE_LEN or not _SAFE_PATH_RE.match(value)):
        raise ValueError(f"Invalid {flag}: must match ^[A-Za-z0-9_./~+-]{{1,512}}$")


def _validate_repo_root_value(*, value: str, flag: str) -> None:
    if not value:
        return
    if len(value) > MAX_PATH_VALUE_LEN or "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError(f"Invalid {flag}: must be an absolute single-line path")
    if not value.startswith("/"):
        raise ValueError(f"Invalid {flag}: must be an absolute path")


def _add_optional_design_source_file(*, values: dict[str, str], claude_source_file: str) -> None:
    if claude_source_file:
        values["LARCH_CLAUDE_SOURCE_FILE"] = claude_source_file


def _recover_prior_design_value(*, key: str, prior_file: Path) -> str:
    if not prior_file.is_file():
        return ""
    found = ""
    for line in _read_kv_file_text(prior_file).splitlines():
        parsed = parse_allowlisted_env_line(raw=line, allowlist=WRITE_DESIGN_ENV_KEYS, name_validator=lambda name: bool(_KEY_RE.match(name)), reject_newline_rhs=True)
        if parsed is not None and parsed[0] == key:
            found = parsed[1]
    return found


def _base_design_writer_values(args: argparse.Namespace, *, prior_file: Path | None = None) -> dict[str, str]:
    values: dict[str, str] = {
        "DESIGN_TMPDIR": args.design_tmpdir,
        "SESSION_TMPDIR": args.design_tmpdir,
        "SESSION_ID": args.session_id,
    }
    if args.repo:
        values["REPO"] = args.repo
    repo_root = args.repo_root.strip()
    if not repo_root and prior_file is not None:
        repo_root = _recover_prior_design_value(key="REPO_ROOT", prior_file=prior_file)
    if not repo_root:
        repo_root = os.environ.get("CLAUDE_PROJECT_DIR", "").strip() or os.environ.get("REPO_ROOT", "").strip()
    if repo_root:
        _validate_repo_root_value(value=repo_root, flag="--repo-root")
        values["REPO_ROOT"] = repo_root
    if args.issue_number:
        values["ISSUE_NUMBER"] = args.issue_number
    return values


def _write_plugin_root_env(*, output: Path, value: str) -> None:
    if not value:
        return
    if not _validate_plugin_root_value(value):
        return
    if not output.parent.is_dir():
        raise OSError(f"plugin-root.env parent is not a directory: {output.parent}")
    text = f"CLAUDE_PLUGIN_ROOT={value}\nexport CLAUDE_PLUGIN_ROOT\n"
    _atomic_write(path=output, text=text)


def _parse_bool_arg(*, value: str, flag: str) -> str:
    if not _is_bool(value):
        raise ValueError(f"Invalid {flag}: must be true or false")
    return value


def _parse_key_value_file(path: str) -> dict[str, str]:
    if not path or not Path(path).is_file():
        return {}
    data: dict[str, str] = {}
    for line in _read_kv_file_text(Path(path)).splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in CALLER_ENV_KEYS and value:
            data[key] = value
    return data


def _is_path_under_root(*, path: str, root: str) -> bool:
    if not path or not root:
        return False
    return _under(path=Path(path), root=Path(root))


def _safe_timing_ledger_path(*, path: str, caller_env_dir: str) -> bool:
    if not path or "\n" in path or "\r" in path or not path.startswith("/"):
        return False
    if len(path) > MAX_PATH_VALUE_LEN or not _SAFE_PATH_RE.match(path):
        return False
    for root in (os.environ.get("TMPDIR", TMP_FALLBACK), os.environ.get("IMPLEMENT_TMPDIR", ""), os.environ.get("DESIGN_TMPDIR", ""), os.environ.get("REVIEW_TMPDIR", ""), caller_env_dir):
        if _is_path_under_root(path=path, root=root):
            return True
    return False


def write_env_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session write-env", add_help=False)
    parser.add_argument("--output")
    parser.add_argument("--repo", default="")
    parser.add_argument("--repo-unavailable")
    parser.add_argument("--codex-present", default="")
    parser.add_argument("--cursor-present", default="")
    parser.add_argument("--codex-available", default="")
    parser.add_argument("--cursor-available", default="")
    parser.add_argument("--codex-binary-found", default="")
    parser.add_argument("--cursor-binary-found", default="")
    parser.add_argument("--auto-mode", default="")
    parser.add_argument("--forked-target", default="false")
    parser.add_argument("--timing-ledger", default="")
    parser.add_argument("--token-session-id", default="")
    parser.add_argument("--claude-source-file", default="")
    parser.add_argument("--prev-implement-tmpdir", default="")
    parser.add_argument("--dynamic-archetypes", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--plugin-root-only", action="store_true")
    parser.add_argument("--value", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    logging_util.quiet_init(argv0="write-session-env.sh")
    try:
        output = args.output or ""
        if not output:
            raise ValueError("Missing required arguments: --output, --repo-unavailable")
        out_path = Path(output)
        if args.plugin_root_only:
            if not _validate_plugin_root_value(args.value):
                return 0
            _write_plugin_root_env(output=out_path, value=args.value)
            return 0
        if args.repo_unavailable is None:
            raise ValueError("Missing required arguments: --output, --repo-unavailable")
        for flag in ("codex_present", "cursor_present", "codex_available", "cursor_available", "codex_binary_found", "cursor_binary_found", "auto_mode"):
            value = getattr(args, flag)
            if value:
                _parse_bool_arg(value=value, flag=f"--{flag.replace('_', '-')}")
        _parse_bool_arg(value=args.forked_target, flag="--forked-target")
        if args.token_session_id and not _SAFE_ID_RE.match(args.token_session_id):
            raise ValueError("Invalid --token-session-id: must match ^[A-Za-z0-9_.-]{1,128}$")
        for flag, value in (("--claude-source-file", args.claude_source_file), ("--timing-ledger", args.timing_ledger)):
            _validate_path_arg_value(value=value, flag=flag)
        if args.prev_implement_tmpdir:
            if len(args.prev_implement_tmpdir) > MAX_PATH_VALUE_LEN or not _SAFE_PATH_RE.match(args.prev_implement_tmpdir):
                raise ValueError("Invalid --prev-implement-tmpdir: must match ^[A-Za-z0-9_./~+-]{1,512}$")
            if not args.prev_implement_tmpdir.startswith("/"):
                raise ValueError("Invalid --prev-implement-tmpdir: must be an absolute path")
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        if plugin_root and not _validate_plugin_root_value(plugin_root):
            raise ValueError("Invalid CLAUDE_PLUGIN_ROOT: must be an absolute path matching ^[A-Za-z0-9_./~+-]{1,512}$")
        if args.dynamic_archetypes and args.dynamic_archetypes not in {"0", "1"}:
            raise ValueError("Invalid --dynamic-archetypes: must be an integer from 0 to 1")
        if args.run_id and not _SAFE_RUN_ID_RE.match(args.run_id):
            raise ValueError("Invalid --run-id: must match ^[A-Za-z0-9._-]{1,128}$")
        data: dict[str, str] = {
            "REPO": args.repo,
            "REPO_UNAVAILABLE": args.repo_unavailable,
            "FORKED_TARGET": args.forked_target,
            "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT": _external_timeout(),
        }
        if args.codex_binary_found:
            data["CODEX_BINARY_FOUND"] = args.codex_binary_found
        if args.cursor_binary_found:
            data["CURSOR_BINARY_FOUND"] = args.cursor_binary_found
        if args.auto_mode:
            data["LARCH_AUTO_MODE"] = args.auto_mode
        if args.timing_ledger:
            data["LARCH_TIMING_LEDGER"] = args.timing_ledger
        if args.token_session_id:
            data["LARCH_TOKEN_SESSION_ID"] = args.token_session_id
        if args.claude_source_file:
            data["LARCH_CLAUDE_SOURCE_FILE"] = args.claude_source_file
        if args.prev_implement_tmpdir:
            data["PREV_IMPLEMENT_TMPDIR"] = args.prev_implement_tmpdir
        if args.dynamic_archetypes:
            data["LARCH_DYNAMIC_ARCHETYPES_MAX"] = args.dynamic_archetypes
        if args.run_id:
            data["LARCH_RUN_ID"] = args.run_id
        if plugin_root:
            data["LARCH_CLAUDE_PLUGIN_ROOT"] = plugin_root
        _validate_writer_keys(data=data, allowed=WRITE_ENV_KEYS)
        _validate_no_newlines(data)
        if output == "/dev/null":
            return 0
        if not _writer_target_allowed(out_path):
            raise ValueError(f"output path not under allowed session root: {output}")
        if not _safe_output_parent(out_path):
            raise OSError(f"output parent is not a writable directory: {out_path.parent}")
        _atomic_write(path=out_path, text=_kv_text(data))
        if plugin_root:
            _write_plugin_root_env(output=out_path.parent / "plugin-root.env", value=plugin_root)
        return 0
    except (OSError, ValueError) as exc:
        _err(f"ERROR={exc}")
        return 1


def _split_ancestor_tail(candidate: str) -> tuple[str, str]:
    path = candidate.rstrip("/") or "/"
    tail = ""
    while not Path(path).exists() and path != "/":
        base = Path(path).name
        if base:
            tail = f"{base}/{tail}" if tail else base
        parent = str(Path(path).parent)
        path = parent or "/"
    return path, tail


def _canonical_prefix(prefix: Path) -> str:
    try:
        resolved = prefix.resolve(strict=True) if prefix.is_dir() else prefix
    except OSError:
        resolved = prefix
    return f"{str(resolved).rstrip('/')}/"


def validate_design_tmpdir(candidate: str) -> tuple[bool, str]:
    if not candidate:
        return False, "design-tmpdir: path is required"
    if "\n" in candidate or "\r" in candidate:
        return False, "design-tmpdir: path must not contain newline or carriage return"
    if not candidate.startswith("/"):
        return False, "Invalid --design-tmpdir: must be an absolute path"
    segments = [segment for segment in candidate.split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        return False, "design-tmpdir: path must not contain '.' or '..' segments"
    ancestor, tail = _split_ancestor_tail(candidate)
    try:
        resolved_ancestor = Path(ancestor).resolve(strict=True)
    except OSError:
        return False, "design-tmpdir: parent resolution failed"
    resolved_candidate = resolved_ancestor / tail if tail else resolved_ancestor
    resolved = resolved_candidate
    cand = Path(candidate)
    if cand.exists():
        if cand.is_symlink() and not cand.is_dir():
            return False, "design-tmpdir: leaf symlink must resolve to a directory"
        if not cand.is_dir():
            return False, "design-tmpdir: path must name a directory"
        try:
            resolved = cand.resolve(strict=True)
        except OSError:
            if cand.is_symlink():
                return False, "design-tmpdir: leaf symlink must resolve to a directory"
    allow = [
        _canonical_prefix(cleanup_cache_sessions_root()),
        _canonical_prefix(Path(os.environ["TMPDIR"])) if os.environ.get("TMPDIR") else "",
        _canonical_prefix(TMP_ROOT),
    ]
    resolved_cmp = f"{str(resolved).rstrip('/')}/"
    if not any(prefix and resolved_cmp.startswith(prefix) for prefix in allow):
        return False, f"design-tmpdir: path not under allowlist after resolution: {resolved}"
    return True, ""


def validate_design_tmpdir_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session validate-design-tmpdir", add_help=False)
    parser.add_argument("path", nargs="?", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    ok, message = validate_design_tmpdir(args.path)
    if not ok:
        _plain_err(message)
        return 2
    return 0


def _recover_prior_bool(*, key: str, prior_file: Path) -> str:
    if not prior_file.is_file():
        return ""
    pattern = re.compile(rf"^export {re.escape(key)}=(true|false)$")
    found = ""
    for line in _read_kv_file_text(prior_file).splitlines():
        m = pattern.match(line)
        if m:
            found = m.group(1)
    return found


def _export_line(*, key: str, value: str) -> str:
    return f"export {key}={shlex.quote(value)}\n"


def _design_symlink_path(pid: str) -> Path:
    home = Path.home()
    return home / ".cache" / "larch" / "sessions" / (f"current-design-env-{pid}.sh" if pid else "current-design-env.sh")


def _design_run_path(pid: str) -> Path:
    return Path.home() / ".cache" / "larch" / "sessions" / f"design-run-{pid}.sh"


def _design_run_launcher_text(*, pid: str, plugin_root: str) -> str:
    quoted_plugin_root = shlex.quote(plugin_root)
    return (
        "#!/usr/bin/env bash\n"
        "set -uo pipefail\n"
        f"PLUGIN_ROOT={quoted_plugin_root}\n"
        f'SESSION_ENV_PATH="$HOME/.cache/larch/sessions/current-design-env-{pid}.sh"\n'
        f"CLAUDE_PID={pid}\n"
        'if [ "$#" -lt 1 ]; then\n'
        "  printf '%s\\n' 'ERROR=missing design wrapper script name' >&2\n"
        "  exit 2\n"
        "fi\n"
        'script=$1\n'
        "shift\n"
        'case "$script" in\n'
        r'  ""|*/*|*..*|*\\*|*\;*|*\&*|*\|*|*\$*|*\`*|*\(*|*\)*|*\<*|*\>*|*[[:space:]]*)' "\n"
        "    printf '%s\\n' 'ERROR=invalid design wrapper script name' >&2\n"
        "    exit 2\n"
        "    ;;\n"
        "esac\n"
        'export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"\n'
        'case "$script" in\n'
        "  step0-*.sh|step0c.sh|step1d5.sh|step1d7.sh|step1e-reentry.sh|design-step0-parse.sh|design-step0-session.sh|design-step0-route.sh|design-step0-clarify-hard-halt.sh|design-step0-init.sh|design-step0-abort-cleanup.sh|design-step0-ap-continue.sh|design-step0c.sh|design-step1d5.sh|design-step1d7.sh|design-step1e-reentry.sh)\n"
        "    printf '%s\\n' 'ERROR=ported design wrapper must use bare verb name, not .sh' >&2\n"
        "    exit 2\n"
        "    ;;\n"
        '  design-step2b-drafter.sh)\n'
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" design step2b-drafter --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"\n'
        '    ;;\n'
        '  design-step2b-postplan.sh)\n'
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" design step2b-postplan --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"\n'
        '    ;;\n'
        '  design-step2b5.sh)\n'
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" design step2b5 --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"\n'
        '    ;;\n'
        '  design-step6.sh)\n'
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" design step6 --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"\n'
        '    ;;\n'
        '  design-step6-prelude.sh)\n'
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" design step6-prelude --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"\n'
        '    ;;\n'
        '  design-step6-cleanup.sh)\n'
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" design step6-cleanup --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"\n'
        '    ;;\n'
        '  design-step-validator-autofix.sh)\n'
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" plan validator-autofix --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"\n'
        '    ;;\n'
        '  design-stage-terminal-state.sh)\n'
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" design stage-terminal-state "$@"\n'
        '    ;;\n'
        '  design-failure-report.sh)\n'
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" design failure-report "$@"\n'
        '    ;;\n'
        '  design-step-final-summary.sh)\n'
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" design step-final-summary --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"\n'
        '    ;;\n'
        "  *.sh)\n"
        '    exec "$PLUGIN_ROOT/skills/design/scripts/$script" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"\n'
        "    ;;\n"
        "  step0-parse|step0-session|step0-route|step0-clarify-hard-halt|step0-init|step0-abort-cleanup|step0-ap-continue|step0c|step1d5|step1d7|step1e-reentry)\n"
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" design "$script" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"\n'
        "    ;;\n"
        "  step6|step6-prelude|step6-cleanup)\n"
        '    exec python3 "$PLUGIN_ROOT/python/cli.py" design "$script" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"\n'
        "    ;;\n"
        "  *.*)\n"
        "    printf '%s\\n' 'ERROR=design verb must be bare and must not end in .sh' >&2\n"
        "    exit 2\n"
        "    ;;\n"
        "  *)\n"
        "    printf '%s\\n' 'ERROR=unknown design wrapper verb' >&2\n"
        "    exit 2\n"
        "    ;;\n"
        "esac\n"
    )


def _write_design_run_sh(*, pid: str, plugin_root: str) -> None:
    run_path = _design_run_path(pid)
    run_path.parent.mkdir(parents=True, exist_ok=True)
    _assert_no_symlink_path_or_ancestors(run_path)
    _atomic_write(path=run_path, text=_design_run_launcher_text(pid=pid, plugin_root=plugin_root), mode=0o755)


def _implement_pointer_path(pid: str) -> Path:
    return Path.home() / ".cache" / "larch" / "sessions" / f"current-implement-env-{pid}.sh"


def _implement_run_path(pid: str) -> Path:
    return Path.home() / ".cache" / "larch" / "sessions" / f"implement-run-{pid}.sh"


def _implement_run_launcher_text(pid: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -uo pipefail\n"
        f'POINTER="$HOME/.cache/larch/sessions/current-implement-env-{pid}.sh"\n'
        '[ -f "$POINTER" ] && [ ! -L "$POINTER" ] || { printf \'%s\\n\' "implement-run: missing current-env pointer: $POINTER" >&2; exit 2; }\n'
        'IMPLEMENT_TMPDIR=$(awk \'BEGIN{p="IMPLEMENT_TMPDIR="} index($0,p)==1{print substr($0,length(p)+1); found=1; exit} END{exit found ? 0 : 1}\' "$POINTER" 2>/dev/null) || { printf \'%s\\n\' "implement-run: IMPLEMENT_TMPDIR missing from pointer: $POINTER" >&2; exit 2; }\n'
        '[ -n "$IMPLEMENT_TMPDIR" ] || { printf \'%s\\n\' "implement-run: IMPLEMENT_TMPDIR empty in pointer: $POINTER" >&2; exit 2; }\n'
        'case "$IMPLEMENT_TMPDIR" in /*) ;; *) printf \'%s\\n\' "implement-run: IMPLEMENT_TMPDIR must be absolute: $IMPLEMENT_TMPDIR" >&2; exit 2 ;; esac\n'
        'LARCH_RUN_SH="$IMPLEMENT_TMPDIR/larch-run.sh"\n'
        '[ -f "$LARCH_RUN_SH" ] || { printf \'%s\\n\' "implement-run: missing larch-run.sh: $LARCH_RUN_SH" >&2; exit 2; }\n'
        '[ -x "$LARCH_RUN_SH" ] || { printf \'%s\\n\' "implement-run: larch-run.sh is not executable: $LARCH_RUN_SH" >&2; exit 2; }\n'
        "export IMPLEMENT_TMPDIR\n"
        f'export LARCH_CLAUDE_PID="${{LARCH_CLAUDE_PID:-{pid}}}"\n'
        'exec "$LARCH_RUN_SH" "$@"\n'
    )


def _write_implement_run_sh(pid: str) -> None:
    run_path = _implement_run_path(pid)
    expected_parent = Path.home() / ".cache" / "larch" / "sessions"
    if run_path.parent != expected_parent:
        raise ValueError(f"implement run path mismatch: {run_path}")
    _assert_no_symlink_path_or_ancestors(run_path)
    run_path.parent.mkdir(parents=True, exist_ok=True)
    _assert_no_symlink_path_or_ancestors(run_path)
    _atomic_write(path=run_path, text=_implement_run_launcher_text(pid), create_parent=False, mode=0o755)


def _validate_claude_pid(pid: str) -> None:
    if not re.match(r"^[1-9][0-9]{0,6}$", pid):
        raise ValueError("Invalid --claude-pid: must be a positive integer of at most 7 decimal digits")


def _assert_no_symlink_path_or_ancestors(path: Path) -> None:
    current = path
    while True:
        if current.is_symlink():
            msg = f"refusing symlinked pointer path or ancestor: {current}"
            raise OSError(msg)
        if current == current.parent:
            break
        current = current.parent


def _validate_design_current_env_link(*, symlink_path: Path, pid: str) -> None:
    expected = _design_symlink_path(pid)
    if symlink_path != expected:
        msg = f"design current-env symlink path mismatch: {symlink_path}"
        raise ValueError(msg)
    ancestor = symlink_path.parent
    while True:
        if ancestor.is_symlink():
            msg = f"refusing symlinked ancestor for design current-env link: {ancestor}"
            raise OSError(msg)
        if ancestor == ancestor.parent:
            break
        ancestor = ancestor.parent


def resolve_trusted_design_session_env_source(*, path: Path, claude_pid: str) -> Path | None:
    if not claude_pid or not path.is_symlink():
        return None
    try:
        _validate_design_current_env_link(symlink_path=path, pid=claude_pid)
        resolved = path.resolve()
    except (ValueError, OSError):
        return None
    return resolved if resolved.is_file() else None


def write_design_env_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session write-design-env", add_help=False)
    for flag in ("output", "design-tmpdir", "session-id", "codex-present", "cursor-present", "codex-available", "cursor-available", "codex-binary-found", "cursor-binary-found", "repo", "repo-root", "issue-number", "claude-pid", "claude-source-file"):
        parser.add_argument(f"--{flag}", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    logging_util.quiet_init(argv0="write-design-current-env.sh")
    try:
        if not args.output or not args.design_tmpdir or not args.session_id:
            raise ValueError("Missing required arguments: --output, --design-tmpdir, --session-id")
        for flag in ("codex_present", "cursor_present", "codex_available", "cursor_available", "codex_binary_found", "cursor_binary_found"):
            value = getattr(args, flag)
            if value:
                _parse_bool_arg(value=value, flag=f"--{flag.replace('_', '-')}")
        if args.issue_number and not args.issue_number.isdigit():
            raise ValueError("Invalid --issue-number: must be a non-negative integer")
        if not _valid_repo_value(args.repo):
            raise ValueError("Invalid --repo: must match OWNER/REPO")
        if not _SAFE_ID_RE.match(args.session_id):
            raise ValueError("Invalid --session-id: must match ^[A-Za-z0-9_.-]{1,128}$")
        if args.claude_pid and not re.match(r"^[1-9][0-9]{0,6}$", args.claude_pid):
            raise ValueError("Invalid --claude-pid: must be a positive integer of at most 7 decimal digits")
        _validate_path_arg_value(value=args.claude_source_file, flag="--claude-source-file")
        ok, message = validate_design_tmpdir(args.design_tmpdir)
        if not ok:
            raise ValueError(message)
        out_path = Path(args.output)
        if not out_path.is_absolute():
            raise ValueError("Invalid --output: must be an absolute path")
        if not _writer_target_allowed(out_path):
            raise ValueError(f"output path not under allowed session root: {out_path}")
        if not _safe_output_parent(out_path):
            raise OSError(f"output parent is not a writable directory: {out_path.parent}")
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        if plugin_root and not _validate_plugin_root_value(plugin_root):
            raise ValueError("Invalid CLAUDE_PLUGIN_ROOT: must be an absolute path matching ^[A-Za-z0-9_./~+-]{1,512}$")
        if args.claude_pid and not plugin_root:
            raise ValueError("Missing CLAUDE_PLUGIN_ROOT: required when --claude-pid is set")
        values = _base_design_writer_values(args, prior_file=out_path)
        code_bin_set = "--codex-binary-found" in argv
        cur_bin_set = "--cursor-binary-found" in argv
        recovered: dict[str, str] = {
            "CODEX_BINARY_FOUND": args.codex_binary_found,
            "CURSOR_BINARY_FOUND": args.cursor_binary_found,
        }
        if not recovered["CODEX_BINARY_FOUND"] and not code_bin_set:
            recovered["CODEX_BINARY_FOUND"] = _recover_prior_bool(key="CODEX_BINARY_FOUND", prior_file=out_path)
        if not recovered["CURSOR_BINARY_FOUND"] and not cur_bin_set:
            recovered["CURSOR_BINARY_FOUND"] = _recover_prior_bool(key="CURSOR_BINARY_FOUND", prior_file=out_path)
        for key, value in recovered.items():
            if value:
                _parse_bool_arg(value=value, flag=f"--{key.lower().replace('_', '-')}")
                values[key] = value
        values["LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT"] = _external_timeout()
        _add_optional_design_source_file(values=values, claude_source_file=args.claude_source_file)
        if plugin_root:
            values["CLAUDE_PLUGIN_ROOT"] = plugin_root
        _validate_writer_keys(data=values, allowed=WRITE_DESIGN_ENV_KEYS)
        _validate_no_newlines(values)
        lines = ["#!/usr/bin/env bash\n", "# /design session env — generated by session_env.py. Do not edit.\n"]
        for key, value in values.items():
            lines.append(_export_line(key=key, value=value))
        _atomic_write(path=out_path, text="".join(lines), create_parent=False)
        symlink_path = _design_symlink_path(args.claude_pid)
        if not args.claude_pid:
            _err("WARNING=write-design-current-env.sh: --claude-pid omitted; using legacy current-design-env.sh symlink (transition shim; pass --claude-pid)")
        _validate_design_current_env_link(symlink_path=symlink_path, pid=args.claude_pid)
        symlink_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_link = symlink_path.with_name(f".{symlink_path.name}.tmp.{os.getpid()}")
        with suppress(FileNotFoundError):
            tmp_link.unlink()
        tmp_link.symlink_to(out_path)
        tmp_link.replace(symlink_path)
        if args.claude_pid:
            _write_design_run_sh(pid=args.claude_pid, plugin_root=plugin_root)
        return 0
    except (OSError, ValueError) as exc:
        _err(f"ERROR={exc}")
        return 1


def write_implement_env_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session write-implement-env", add_help=False)
    parser.add_argument("--claude-pid", default="")
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--cwd", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    logging_util.quiet_init(argv0="write-implement-current-env.sh")
    try:
        _validate_claude_pid(args.claude_pid)
        tmpdir = Path(args.implement_tmpdir)
        cwd = Path(args.cwd)
        if not tmpdir.is_absolute() or not tmpdir.is_dir():
            raise ValueError("Invalid --implement-tmpdir: must be an existing absolute directory")
        if not is_allowed_session_tmpdir(tmpdir):
            raise ValueError(
                f"implement-tmpdir: path must be under /tmp/, /private/tmp/, /var/folders/, or {cleanup_cache_sessions_root()}/"
            )
        if not cwd.is_absolute():
            raise ValueError("Invalid --cwd: must be an absolute path")
        try:
            repo_cwd = str(cwd.resolve())
        except OSError:
            repo_cwd = str(cwd)
        data = {
            "IMPLEMENT_TMPDIR": str(tmpdir),
            "REPO_CWD": repo_cwd,
            "SKILL_KIND": "implement",
        }
        _validate_no_newlines(data)
        target = _implement_pointer_path(args.claude_pid)
        expected_parent = Path.home() / ".cache" / "larch" / "sessions"
        if target.parent != expected_parent:
            raise ValueError(f"implement current-env path mismatch: {target}")
        _assert_no_symlink_path_or_ancestors(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        _assert_no_symlink_path_or_ancestors(target)
        _atomic_write(path=target, text=_kv_text(data), create_parent=False)
        _write_implement_run_sh(args.claude_pid)
        return 0
    except (OSError, ValueError) as exc:
        _err(f"ERROR={exc}")
        return 1


def clear_implement_pointer_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session clear-implement-pointer", add_help=False)
    parser.add_argument("--claude-pid", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    logging_util.quiet_init(argv0="clear-implement-current-env.sh")
    try:
        _validate_claude_pid(args.claude_pid)
        target = _implement_pointer_path(args.claude_pid)
        sessions_root = Path.home() / ".cache" / "larch" / "sessions"
        if target.parent != sessions_root or target.name != f"current-implement-env-{args.claude_pid}.sh":
            raise ValueError(f"implement current-env path mismatch: {target}")
        if target.exists() or target.is_symlink():
            target.unlink()
        return 0
    except (OSError, ValueError) as exc:
        _err(f"ERROR={exc}")
        return 1


def read_key_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session read-key", add_help=False)
    parser.add_argument("--file", default=None)
    parser.add_argument("--key", default="")
    parser.add_argument("--default", default=None)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    logging_util.quiet_init(argv0="read-session-env-key.sh")
    if not args.key:
        _err("read-session-env-key.sh: --key is required")
        return 1
    file_set = "--file" in argv
    if args.file is None or args.file == "":
        if file_set and args.default is not None:
            _emit(args.default)
            return 0
        _err("read-session-env-key.sh: --file is required")
        return 1
    path = Path(args.file)
    if not path.is_file():
        if args.default is not None:
            _emit(args.default)
            return 0
        _err(f"read-session-env-key.sh: cannot read {args.file}")
        return 1
    value = ""
    found = False
    prefix = f"{args.key}="
    try:
        lines = _read_kv_file_text(path).splitlines()
    except ValueError as exc:
        _err(str(exc))
        return 1
    except OSError:
        if args.default is not None:
            _emit(args.default)
            return 0
        _err(f"read-session-env-key.sh: cannot read {args.file}")
        return 1
    for line in lines:
        if line.startswith(prefix):
            value = line[len(prefix):]
            found = True
            break
    if (not found or value == "") and args.default is not None:
        value = args.default
    _emit(value)
    return 0


def read_keys_main(argv: list[str]) -> int:
    """Batch sibling of read_key_main: read many keys from one KV file in a
    single process and emit `KEY=value` lines (input order).

    Each `--key` is `NAME` or `NAME=DEFAULT` (split on the first `=`). A key
    that is absent or empty in the file falls back to its DEFAULT, or to the
    empty string when no DEFAULT was given. A missing/empty/unreadable file
    resolves every key to its default; only an entirely absent `--file` flag
    is an error. Carriage-return injection is rejected exactly as read_key.
    Collapses N `session read-key` spawns (one process each) into one.
    """
    parser = argparse.ArgumentParser(prog="session read-keys", add_help=False)
    parser.add_argument("--file", default=None)
    parser.add_argument("--key", action="append", default=[])
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    logging_util.quiet_init(argv0="read-session-env-keys.sh")
    if not args.key:
        _err("read-session-env-keys.sh: at least one --key is required")
        return 1
    if "--file" not in argv:
        _err("read-session-env-keys.sh: --file is required")
        return 1
    specs: list[tuple[str, str | None]] = []
    for raw in args.key:
        if "=" in raw:
            name, default = raw.split("=", 1)
            specs.append((name, default))
        else:
            specs.append((raw, None))
    for name, _ in specs:
        if not name:
            _err("read-session-env-keys.sh: empty --key name")
            return 1
    found: dict[str, str] = {}
    if args.file:
        path = Path(args.file)
        if path.is_file():
            try:
                lines = _read_kv_file_text(path).splitlines()
            except ValueError as exc:
                _err(str(exc))
                return 1
            except OSError:
                lines = []
            for line in lines:
                idx = line.find("=")
                if idx <= 0:
                    continue
                name = line[:idx]
                if name not in found:  # first occurrence wins, matching read_key
                    found[name] = line[idx + 1:]
    out_lines: list[str] = []
    for name, default in specs:
        value = found.get(name, "")
        if (name not in found or value == "") and default is not None:
            value = default
        out_lines.append(f"{name}={value}")
    _emit("\n".join(out_lines))
    return 0


def _uuid_or_basename(parent: Path) -> str:
    try:
        result = proc.run(["uuidgen"])
        if result.returncode == 0:
            value = result.stdout.strip()
            if value:
                return value
    except (FileNotFoundError, OSError):
        pass
    return parent.name


def write_id_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session write-id", add_help=False)
    parser.add_argument("--output", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        logging_util.quiet_init(argv0="write-session-id.sh")
        _emit_kv(key="FAILED", value="true")
        _emit_kv(key="ERROR", value="unknown flag")
        return 1
    logging_util.quiet_init(argv0="write-session-id.sh")
    if not args.output:
        _emit_kv(key="FAILED", value="true")
        _emit_kv(key="ERROR", value="--output is required")
        return 1
    out = Path(args.output)
    try:
        if not _writer_target_allowed(out):
            raise OSError(f"output path not under allowed session root: {out}")
        out.parent.mkdir(parents=True, exist_ok=True)
        if not _safe_output_parent(out):
            raise OSError(f"output parent is not a writable directory: {out.parent}")
        if out.is_file() and out.stat().st_size > 0:
            return 0
        _atomic_write(path=out, text=_uuid_or_basename(out.parent) + "\n")
        return 0
    except OSError as exc:
        _emit_kv(key="FAILED", value="true")
        _emit_kv(key="ERROR", value=str(exc))
        return 1


def persist_run_flags_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session persist-run-flags", add_help=False)
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--quick-mode", default="false")
    parser.add_argument("--no-issues", default="")
    parser.add_argument("--force-requested", default="false")
    parser.add_argument("--self-review-requested", default="false")
    parser.add_argument("--self-implement-requested", default="false")
    parser.add_argument("--difficulty-override", default="")
    try:
        args = parser.parse_args(argv)
        if not args.implement_tmpdir:
            raise ValueError("--implement-tmpdir is required")
        if not Path(args.implement_tmpdir).is_dir():
            raise ValueError("--implement-tmpdir not a directory")
        for flag in ("quick_mode", "no_issues", "force_requested", "self_review_requested", "self_implement_requested"):
            value = getattr(args, flag)
            if value not in _BOOL:
                raise ValueError(f"--{flag.replace('_', '-')} must be true or false")
        if args.difficulty_override and args.difficulty_override not in {"TRIVIAL", "MODERATE", "HARD"}:
            raise ValueError("--difficulty-override must be empty, TRIVIAL, MODERATE, or HARD")
        data: dict[str, str] = {
            "QUICK_MODE": args.quick_mode,
            "NO_ISSUES": args.no_issues,
            "FORCE_REQUESTED": args.force_requested,
            "SELF_REVIEW_REQUESTED": args.self_review_requested,
            "SELF_IMPLEMENT_REQUESTED": args.self_implement_requested,
            "DIFFICULTY_OVERRIDE": args.difficulty_override,
        }
        target = Path(args.implement_tmpdir) / "run-flags.sh"
        if not _writer_target_allowed(target):
            raise ValueError(f"output path not under allowed session root: {target}")
        if not _safe_output_parent(target):
            raise OSError(f"output parent is not a writable directory: {target.parent}")
        _validate_writer_keys(data=data, allowed=RUN_FLAG_KEYS)
        _validate_no_newlines(data)
        _atomic_write(path=target, text=_kv_text(data))
        print("RUN_FLAGS_PERSISTED=true")
        return 0
    except (OSError, SystemExit, ValueError) as exc:
        _plain_err(f"persist-implement-run-flags.sh: {exc}")
        return 2


def write_run_params_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session write-run-params", add_help=False)
    parser.add_argument("--output", default="")
    parser.add_argument("--partition-requested", default="")
    parser.add_argument("--brainstorm-requested", default="")
    parser.add_argument("--approve-requested", default="")
    parser.add_argument("--skip-approve-requested", default="")
    parser.add_argument("--difficulty", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    logging_util.quiet_init(argv0="write-run-params.sh")
    try:
        if not args.output:
            raise ValueError("missing required flag: --output")
        for flag in ("partition_requested", "brainstorm_requested", "approve_requested", "skip_approve_requested"):
            cli_flag = f"--{flag.replace('_', '-')}"
            if cli_flag not in argv:
                continue
            value = getattr(args, flag)
            if not value:
                raise ValueError(f"invalid {cli_flag}: requires a value")
            if value not in _BOOL:
                raise ValueError(f"invalid {cli_flag}: {value}")
        if args.difficulty and args.difficulty not in {"TRIVIAL", "MODERATE", "HARD"}:
            raise ValueError(f"invalid --difficulty: {args.difficulty}")
        out = Path(args.output)
        if not out.is_absolute():
            raise ValueError(f"--output must be absolute: {out}")
        if not _writer_target_allowed(out):
            raise ValueError(f"output path not under allowed session root: {out}")
        if not out.parent.is_dir():
            _err(f"write-run-params.sh: output directory not found: {out.parent}")
            return 1
        if not _safe_output_parent(out):
            raise OSError(f"output parent is not a writable directory: {out.parent}")
        payload = {
            "schema_version": 3,
            "partition_requested": args.partition_requested == "true",
            "brainstorm_requested": args.brainstorm_requested == "true",
            "approve_requested": args.approve_requested == "true",
            "skip_approve_requested": args.skip_approve_requested == "true",
            "difficulty_override": args.difficulty,
        }
        _atomic_write(path=out, text=json.dumps(payload, indent=2, sort_keys=False) + "\n")
        _emit_kv(key="RUN_PARAMS_WRITTEN", value=str(out))
        return 0
    except (OSError, ValueError) as exc:
        _err(f"write-run-params.sh: {exc}")
        return 2


def restore_finalize_state_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session restore-finalize-state", add_help=False)
    parser.add_argument("--implement-tmpdir", default="")
    try:
        args = parser.parse_args(argv)
        if not args.implement_tmpdir:
            raise ValueError("--implement-tmpdir is required")
        tmpdir = Path(args.implement_tmpdir)
        if not tmpdir.is_dir():
            raise ValueError("--implement-tmpdir must exist")
        if not _writer_target_allowed(tmpdir):
            raise ValueError(f"--implement-tmpdir not under allowed session root: {tmpdir}")
    except (SystemExit, ValueError) as exc:
        _plain_err(f"restore-finalize-state.sh: {exc}")
        return 2
    state_file = tmpdir / "ship-pr-state.sh"
    finalize_file = tmpdir / "finalize-state.sh"
    bail_reason_file = tmpdir / "final-bail-reason.txt"
    if not state_file.is_file():
        _plain_err(f"restore-finalize-state.sh: warning: missing ship-pr state file: {state_file}")
        return 1
    state = _read_kv_raw(state_file)
    existing = _read_kv_raw(finalize_file)
    output: list[tuple[str, str]] = []
    existing_stall_tracking = existing.get("STALL_TRACKING", "")
    existing_stall_step = existing.get("STALL_STEP", "")
    for key in RESTORE_FINALIZE_KEYS:
        value = state.get(key, "")
        if existing_stall_tracking == "true":
            if key == "STALL_TRACKING":
                value = "true"
            elif key == "STALL_STEP" and existing_stall_step:
                value = existing_stall_step
        if value == "":
            value = existing.get(key, RESTORE_FINALIZE_DEFAULTS.get(key, ""))
        output.append((key, value))
    _validate_no_newlines(dict(output))
    _atomic_write(path=finalize_file, text=_kv_text(output))
    bail_reason = state.get("BAIL_REASON", "")
    _atomic_write(path=bail_reason_file, text=bail_reason, create_parent=True)
    run_id = state.get("RUN_ID", "")
    if bail_reason and run_id:
        _ = proc.run([
            "python3",
            str(_scripts_dir().parent / "python" / "cli.py"),
            "run-log",
            "write",
            "--log-root",
            str(tmpdir / "larch-logs"),
            "--skill",
            "implement",
            "--run-id",
            run_id,
            "--batch",
            "final-bail-reason",
            "--input-file",
            str(bail_reason_file),
        ])
    return 0


def cleanup_tmpdir_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session cleanup-tmpdir", add_help=False)
    parser.add_argument("--dir", dest="dir", default="")
    parser.add_argument("pos", nargs="?")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        logging_util.quiet_init(argv0="cleanup-tmpdir.sh")
        _err("Usage: cleanup-tmpdir.sh --dir <path>")
        return 1
    logging_util.quiet_init(argv0="cleanup-tmpdir.sh")
    target = args.dir or args.pos or ""
    if not target:
        _err("ERROR: --dir is required and must be non-empty")
        return 1
    if not is_allowed_session_tmpdir(target):
        _err(f"ERROR: --dir must be under /tmp/, /private/tmp/, /var/folders/, or {cleanup_cache_sessions_root()}/ (got: {target})")
        return 1
    audit_log = Path(os.environ.get("TMPDIR", TMP_FALLBACK)) / "larch-cleanup-audit.log"
    ts = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    parent = "?"
    with suppress(Exception):
        result = proc.run(["ps", "-o", "comm=", "-p", str(os.getppid())])
        parent = re.sub(r"\s+", "_", result.stdout.strip()) or "?"
    with suppress(OSError):
        with audit_log.open("a", encoding="utf-8") as handle:
            handle.write(f"{ts} pid={os.getpid()} ppid={os.getppid()} parent={parent} dir={target}\n")
    target_path = Path(target)
    if not target_path.exists():
        return 0
    try:
        shutil.rmtree(target_path)
    except OSError as exc:
        _err(f"ERROR: cleanup-tmpdir failed: {exc}")
        return 1
    if target_path.exists():
        _err(f"ERROR: cleanup-tmpdir failed: directory still exists: {target}")
        return 1
    return 0


def entry_gate_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session entry-gate", add_help=False)
    parser.add_argument("--mode", default="")
    parser.add_argument("--current-branch", default="")
    parser.add_argument("--is-main", default="")
    parser.add_argument("--is-user-branch", default="")
    parser.add_argument("--user-prefix", default="")
    parser.add_argument("--branch-info-supplied", default=None)
    try:
        args, extra = parser.parse_known_args(argv)
    except SystemExit:
        return 4
    def fail(message: str) -> int:
        _plain_err(f"GATE_ERROR={message}")
        return 4
    if extra:
        return fail(f"unknown argument: {extra[0]}")
    supplied = {
        "--mode": "--mode" in argv,
        "--current-branch": "--current-branch" in argv,
        "--user-prefix": "--user-prefix" in argv,
        "--is-main": "--is-main" in argv,
        "--is-user-branch": "--is-user-branch" in argv,
    }
    for flag, was_supplied in supplied.items():
        if not was_supplied:
            return fail(f"missing required flag {flag}")
    if args.mode not in {"implement", "design"}:
        return fail(f"invalid mode: {args.mode}")
    if not args.user_prefix:
        return fail("--user-prefix must be non-empty")
    if not _is_bool(args.is_main):
        return fail(f"invalid value for --is-main: {args.is_main}")
    if not _is_bool(args.is_user_branch):
        return fail(f"invalid value for --is-user-branch: {args.is_user_branch}")
    if args.mode == "implement" and args.branch_info_supplied is not None:
        return fail("--branch-info-supplied not allowed for mode=implement")
    branch_info = args.branch_info_supplied or "false"
    if not _is_bool(branch_info):
        return fail(f"invalid value for --branch-info-supplied: {branch_info}")
    entry_gate = "strict"
    skip_branch_check = "false"
    if (args.mode == "design" and branch_info == "true") or args.is_user_branch == "true":
        entry_gate = "continue"
        skip_branch_check = "true"
    logging_util.quiet_init(argv0="session-entry-gate.sh")
    _emit_kv(key="ENTRY_GATE", value=entry_gate)
    _emit_kv(key="SKIP_BRANCH_CHECK", value=skip_branch_check)
    return 0


def _repo_from_gh_or_git(runner: Runner) -> str:
    try:
        gh_result = gh.repo_name_with_owner_read(runner)
    except (FileNotFoundError, OSError):
        gh_result = proc.CommandResult(("gh",), 127, "", "", 0.0)
    if gh_result.returncode == 0 and gh_result.stdout.strip():
        return gh_result.stdout.strip()
    helper = runner.run([sys.executable, str(Path(__file__).resolve().parents[2] / "cli.py"), "gh", "remote-repo", "origin"])
    return helper.stdout.strip() if helper.returncode == 0 else ""


def _make_session_tmpdir(prefix: str) -> Path:
    clone_tag = re.sub(r"[^A-Za-z0-9_-]", "_", Path.cwd().name)[:32] or "_"
    cache_root = cleanup_cache_sessions_root()
    template_prefix = f"{prefix}-{clone_tag}-"
    try:
        cache_root.mkdir(parents=True, exist_ok=True)
        probe = cache_root / f".larch-write-probe.{os.getpid()}"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return Path(tempfile.mkdtemp(prefix=template_prefix, dir=cache_root))
    except OSError:
        _err("session-setup.sh: warning: cache session root unavailable, falling back to /tmp")
        return Path(tempfile.mkdtemp(prefix=template_prefix, dir=TMP_FALLBACK))


def _write_session_identity(*, tmpdir: Path, session_id: str) -> None:
    (tmpdir / "session-id").write_text(session_id + "\n", encoding="utf-8")
    sentinel = tmpdir / ".larch-keepalive"
    try:
        sentinel.write_text(f"# larch session identity (hook routing)\nCLONE_PATH={Path.cwd()}\nSESSION_ID={session_id}\n", encoding="utf-8")
    except OSError:
        _err(f"session-setup.sh: warning: failed to write session identity: {sentinel}")


def _ignore_placeholder_run_dirs(_: str, names: list[str]) -> set[str]:  # lint-keyword-only: ok shutil.copytree ignore callback
    """Drop placeholder run-log dirs for the ``shutil.copytree`` ``ignore`` hook.

    Returns the subset of ``names`` matching the non-unique ``run-<N>`` pattern so
    a fresh session never inherits a stale shared run directory (issue #4397).
    """
    return {name for name in names if _PLACEHOLDER_RUN_DIR_RE.match(name)}


def setup_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session setup", add_help=False)
    parser.add_argument("--prefix", default="")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--skip-branch-check", action="store_true")
    parser.add_argument("--skip-repo-check", action="store_true")
    parser.add_argument("--check-reviewers", action="store_true")
    parser.add_argument("--skip-codex-probe", action="store_true")
    parser.add_argument("--skip-cursor-probe", action="store_true")
    parser.add_argument("--write-session-env", default="")
    parser.add_argument("--caller-env", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 4
    logging_util.quiet_init(argv0="session-setup.sh")
    runner = proc
    if not args.prefix:
        _err("session-setup.sh: --prefix is required")
        return 4
    caller = _parse_key_value_file(args.caller_env)
    if not args.skip_preflight:
        cmd = [sys.executable, str(Path(__file__).resolve().parents[2] / "cli.py"), "admission", "preflight"]
        if args.skip_branch_check:
            cmd.append("--skip-branch-check")
        preflight = runner.run(cmd)
        if preflight.returncode != 0:
            _emit(preflight.stdout + preflight.stderr)
            return preflight.returncode
        stale = runner.run([str(_scripts_dir() / "check-stale-plugin.sh")])
        if stale.returncode != 0:
            _err(f"session-setup.sh: warning: stale plugin check failed (rc={stale.returncode}): {stale.stdout}{stale.stderr}")
        elif "STALE_PLUGIN_CHECK=working-tree-ahead" in stale.stdout:
            data = _parse_text_kv(stale.stdout)
            _emit(f"**⚠ larch: installed plugin version ({data.get('STALE_PLUGIN_INSTALLED_VERSION','')}) is behind the working tree ({data.get('STALE_PLUGIN_WORKING_TREE_VERSION','')}). Reinstall or refresh the plugin from this checkout before the next run to pick up the latest fixes. Continuing with the cached version.**")
    tmpdir = _make_session_tmpdir(args.prefix)
    session_id = _uuid_or_basename(tmpdir)
    _write_session_identity(tmpdir=tmpdir, session_id=session_id)
    _emit_kv(key="SESSION_TMPDIR", value=str(tmpdir))
    _emit_kv(key="SESSION_ID", value=session_id)
    _emit_kv(key="LARCH_RENDER_CACHE_DIR", value=str(tmpdir / "render-cache"))
    prev = caller.get("PREV_IMPLEMENT_TMPDIR", "")
    if prev and (Path(prev) / "larch-logs").is_dir():
        with suppress(OSError):
            shutil.copytree(
                Path(prev) / "larch-logs",
                tmpdir / "larch-logs",
                dirs_exist_ok=True,
                ignore=_ignore_placeholder_run_dirs,
            )
    if not os.environ.get("LARCH_CURSOR_MODEL") and os.environ.get("CLAUDE_PLUGIN_OPTION_CURSOR_MODEL"):
        os.environ["LARCH_CURSOR_MODEL"] = os.environ["CLAUDE_PLUGIN_OPTION_CURSOR_MODEL"]
    if not os.environ.get("LARCH_CODEX_MODEL") and os.environ.get("CLAUDE_PLUGIN_OPTION_CODEX_MODEL"):
        os.environ["LARCH_CODEX_MODEL"] = os.environ["CLAUDE_PLUGIN_OPTION_CODEX_MODEL"]
    repo_value = ""
    repo_unavailable = "false"
    if not args.skip_repo_check:
        if caller.get("REPO") or caller.get("REPO_UNAVAILABLE"):
            repo_value = caller.get("REPO", "")
            repo_unavailable = caller.get("REPO_UNAVAILABLE", "false")
        else:
            repo_value = _repo_from_gh_or_git(runner)
            repo_unavailable = "false" if repo_value else "true"
        _emit_kv(key="REPO", value=repo_value)
        _emit_kv(key="REPO_UNAVAILABLE", value=repo_unavailable)
    final_codex = ""
    final_cursor = ""
    final_codex_bin = caller.get("CODEX_BINARY_FOUND", "")
    final_cursor_bin = caller.get("CURSOR_BINARY_FOUND", "")
    if args.check_reviewers:
        # agents.check_reviewers is a real module-level function (see agents.py);
        # a newer pyright misresolves this cross-module attribute while the
        # repo-pinned pyright is clean. Suppress the false positive (#4439).
        reviewer = agents.check_reviewers(  # pyright: ignore[reportAttributeAccessIssue]
            skip_codex_probe=args.skip_codex_probe or bool(final_codex),
            skip_cursor_probe=args.skip_cursor_probe or bool(final_cursor),
        )
        probed = reviewer.kv()
        for key in ("CODEX_PRESENT", "CURSOR_PRESENT", "CODEX_BINARY_FOUND", "CURSOR_BINARY_FOUND"):
            if probed.get(key):
                _emit_kv(key=key, value=probed[key])
        final_codex = probed.get("CODEX_PRESENT", "")
        final_cursor = probed.get("CURSOR_PRESENT", "")
        final_codex_bin = probed.get("CODEX_BINARY_FOUND", "")
        final_cursor_bin = probed.get("CURSOR_BINARY_FOUND", "")
    else:
        if final_codex_bin not in _BOOL and final_codex in _BOOL:
            final_codex_bin = final_codex
        if final_cursor_bin not in _BOOL and final_cursor in _BOOL:
            final_cursor_bin = final_cursor
        if final_codex_bin in _BOOL:
            _emit_kv(key="CODEX_BINARY_FOUND", value=final_codex_bin)
        if final_cursor_bin in _BOOL:
            _emit_kv(key="CURSOR_BINARY_FOUND", value=final_cursor_bin)
    if caller.get("LARCH_TOKEN_SESSION_ID"):
        _emit_kv(key="LARCH_TOKEN_SESSION_ID", value=caller["LARCH_TOKEN_SESSION_ID"])
    if caller.get("LARCH_CLAUDE_SOURCE_FILE"):
        _emit_kv(key="LARCH_CLAUDE_SOURCE_FILE", value=caller["LARCH_CLAUDE_SOURCE_FILE"])
    if args.write_session_env:
        wargs = ["--output", args.write_session_env, "--repo-unavailable", repo_unavailable]
        if repo_value:
            wargs.extend(["--repo", repo_value])
        if final_codex:
            wargs.extend(["--codex-present", final_codex])
        if final_cursor:
            wargs.extend(["--cursor-present", final_cursor])
        if final_codex_bin:
            wargs.extend(["--codex-binary-found", final_codex_bin])
        if final_cursor_bin:
            wargs.extend(["--cursor-binary-found", final_cursor_bin])
        if caller.get("LARCH_TOKEN_SESSION_ID"):
            wargs.extend(["--token-session-id", caller["LARCH_TOKEN_SESSION_ID"]])
        if caller.get("LARCH_CLAUDE_SOURCE_FILE"):
            wargs.extend(["--claude-source-file", caller["LARCH_CLAUDE_SOURCE_FILE"]])
        dyn = caller.get("LARCH_DYNAMIC_ARCHETYPES_MAX", "")
        if dyn:
            if dyn in {"0", "1"}:
                wargs.extend(["--dynamic-archetypes", dyn])
            else:
                _err("session-setup.sh: warning: ignoring invalid LARCH_DYNAMIC_ARCHETYPES_MAX from caller-env (must be 0..1)")
        ledger = caller.get("LARCH_TIMING_LEDGER", "")
        if ledger:
            caller_dir = str(Path(args.caller_env).parent.resolve()) if args.caller_env else ""
            if _safe_timing_ledger_path(path=ledger, caller_env_dir=caller_dir):
                wargs.extend(["--timing-ledger", ledger])
            else:
                _err("session-setup.sh: warning: ignoring unsafe LARCH_TIMING_LEDGER from caller-env (not under accepted root)")
        rc = write_env_main(wargs)
        if rc != 0:
            return rc
    return 0


def _parse_text_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, skip_comments=True)


def _numeric_stdout(result: proc.CommandResult) -> int:
    text = result.stdout.strip() or "0"
    return int(text) if text.isdigit() else 0


def _transient_run(argv: list[str]) -> proc.CommandResult:
    last = proc.run(argv)
    for _ in range(2):
        if last.returncode == 0:
            return last
        last = proc.run(argv)
    return last


def local_cleanup_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session local-cleanup", add_help=False)
    parser.add_argument("--branch", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print("Usage: local-cleanup.sh --branch BRANCH_NAME", file=sys.stderr)
        return 1
    if not args.branch:
        print("ERROR: --branch is required", file=sys.stderr)
        print("Usage: local-cleanup.sh --branch BRANCH_NAME", file=sys.stderr)
        return 1
    if args.branch == "main":
        print("ERROR: --branch must not be 'main'", file=sys.stderr)
        return 1
    cleanup_success = "false"
    current_branch = "unknown"
    branch_deleted = "false"
    try:
        print("🔄 Switching to main...", file=sys.stderr)
        if proc.run(["git", "checkout", "main"]).returncode != 0:
            print("❌ Failed to checkout main", file=sys.stderr)
            current_branch = proc.run(["git", "symbolic-ref", "--short", "HEAD"]).stdout.strip() or "unknown"
            return 0
        current_branch = "main"
        print("🔄 Fetching origin main...", file=sys.stderr)
        pre_fetch_sha = proc.run(["git", "rev-parse", "origin/main"]).stdout.strip() or "origin/main"
        if _transient_run(["git", "fetch", "origin", "main"]).returncode != 0:
            print("⚠ Failed to fetch origin main (continuing)", file=sys.stderr)
        ahead_before = _numeric_stdout(proc.run(["git", "rev-list", "--count", "origin/main..HEAD"]))
        if ahead_before > 0:
            subjects = proc.run(["git", "log", "origin/main..HEAD", "--format=%s"])
            subject_lines = [line for line in subjects.stdout.splitlines() if line]
            all_flushes = subjects.returncode == 0 and (
                not subject_lines or all(line.startswith(config.FLUSH_COMMIT_SUBJECT_PREFIX) for line in subject_lines)
            )
            diff = proc.run(["git", "diff", "--name-only", pre_fetch_sha, "HEAD"])
            diff_lines = [line for line in diff.stdout.splitlines() if line]
            larch_only = diff.returncode == 0 and (
                not diff_lines or all(line.startswith("larch-logs/") for line in diff_lines)
            )
            if all_flushes and larch_only:
                print(f"⚠ Dropping {ahead_before} prior-run larch-log flush commit(s) before pull...", file=sys.stderr)
                _ = proc.run(["git", "reset", "--hard", "origin/main"])
        print("🔄 Fast-forwarding local main from origin/main...", file=sys.stderr)
        if _transient_run(["git", "pull", "--ff-only", "origin", "main"]).returncode != 0:
            ahead_after = _numeric_stdout(proc.run(["git", "rev-list", "--count", "origin/main..HEAD"]))
            if ahead_after > 0:
                print(f"❌ Failed to pull origin main; local main is ahead of origin/main by {ahead_after} commit(s). Push or reconcile local main before retrying.", file=sys.stderr)
            else:
                print("❌ Failed to pull origin main", file=sys.stderr)
            return 0
        print(f"🔄 Deleting local branch {args.branch}...", file=sys.stderr)
        if proc.run(["git", "branch", "-D", "--", args.branch]).returncode == 0:
            branch_deleted = "true"
        else:
            print(f"⚠ Failed to delete branch {args.branch} (may already be deleted)", file=sys.stderr)
        cleanup_success = "true"
        print("✅ Local cleanup complete", file=sys.stderr)
        return 0
    finally:
        print(f"CLEANUP_SUCCESS={cleanup_success}")
        print(f"CURRENT_BRANCH={current_branch}")
        print(f"BRANCH_DELETED={branch_deleted}")
