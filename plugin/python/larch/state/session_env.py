"""Session/state lifecycle verbs for the larch Python runtime.

Issue #8057 moved ``session setup``'s temp-directory siblings to the Rust owner:
``require-plugin-root``, ``validate-design-tmpdir``, ``write-id``,
``resolve-implement-tmpdir``, and ``cleanup-tmpdir`` no longer register here.
``require_plugin_root``, ``validate_design_tmpdir``, and ``write_id`` survive as
library helpers because Python-owned commands in ``larch.design`` and
``larch.state.bootstrap`` still call them in process; their CLI entrypoints and
the fully orphaned implement-tmpdir resolver are gone.

Issue #8058 moved the eight session-env and run-flag writers — ``write-env``,
``write-design-env``, ``write-implement-env``, ``clear-implement-pointer``,
``persist-run-flags``, ``write-run-params``, ``restore-finalize-state``, and
``resolve-trusted-design-env`` — to the Rust owner, entrypoints and
implementations alike. Nothing here writes a session-env file any more:
``setup`` and ``larch.state.bootstrap`` reach the writer through
:func:`run_session_verb`, which enters the verified bootstrap script, and the
argument renderers below keep one owner for each flag spelling.
``read_finalize_state`` and ``write_finalize_state_merged`` stay because
``implement-finalize teardown`` still reads and merges that file in process.
"""
# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import sys
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Mapping

from larch.agents import agents
from larch.core import config
from larch import io as larch_io
from larch.core import logging_util
from larch.core import proc
from larch.errors import ShipError
from larch.git import gh
from larch.core.proc import Runner
from larch.core.repo_roots import larch_entrypoint

_BOOL = {"true", "false"}
_SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_./~+-]+$")
_SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
# Non-unique placeholder run-log directory names (e.g. ``run-1``). These must
# never be carried forward from a previous session: they collide across runs and
# clones and get re-committed to the repo (issue #4397). Real UUID run dirs and
# ``shared/`` are still carried so resume keeps prior batches.
_PLACEHOLDER_RUN_DIR_RE = re.compile(r"^run-[0-9]+$")
MAX_PATH_VALUE_LEN = 512
TMP_FALLBACK = "/tmp"  # noqa: S108 - parity fallback for larch session roots.
TMP_ROOT = Path(TMP_FALLBACK)

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
    "LARCH_RUN_ID",
    "LARCH_LIVE_MUTATION_OK",
})
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
CALLER_ENV_KEYS = frozenset({
    "REPO",
    "REPO_ROOT",
    "REPO_UNAVAILABLE",
    "CLAUDE_BINARY_FOUND",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "LARCH_TOKEN_SESSION_ID",
    "LARCH_CLAUDE_SOURCE_FILE",
    "LARCH_TIMING_LEDGER",
    "PREV_IMPLEMENT_TMPDIR",
    "LARCH_DYNAMIC_ARCHETYPES_MAX",
})
# Shared /design wrapper-env defaults. design_step2b and plan_quality both
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
    "REPO_ROOT": "",
    "CLAUDE_BINARY_FOUND": "",
    "CODEX_BINARY_FOUND": "",
    "CURSOR_BINARY_FOUND": "",
    "IMPLEMENT_TMPDIR": "",
}

DESIGN_REQUEST_ENV_DEFAULTS: dict[str, str] = {
    "POSITIONAL_KIND": "",
    "POSITIONAL_VALUE": "",
    "partition_requested": "false",
    "brainstorm_requested": "false",
    "approve_requested": "false",
    "skip_approve_requested": "false",
    "no_dedup_requested": "false",
    "run_id": "",
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
# (design_step2b) and the validator wrapper parser (plan_quality).
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
    if not merged.get("CLAUDE_BINARY_FOUND"):
        merged["CLAUDE_BINARY_FOUND"] = "true" if shutil.which("claude") else "false"
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
class WriteIdResult:
    """Result of :func:`write_id`: the id file, its value, and whether it was written."""

    output: Path
    session_id: str
    wrote: bool


@dataclass(frozen=True)
class SetupEmission:
    """One ordered setup stdout action: a ``KEY=value`` pair (``kind='kv'``) or a
    literal non-KV line (``kind='line'``, value in ``key``).
    """

    kind: str
    key: str
    value: str = ""


@dataclass(frozen=True)
class SessionSetupResult:
    session_tmpdir: Path
    session_id: str
    render_cache_dir: Path
    claude_binary_found: str
    exit_code: int = 0
    repo_checked: bool = False
    repo: str = ""
    repo_unavailable: str = "false"
    reviewers_checked: bool = False
    codex_present: str = ""
    cursor_present: str = ""
    codex_binary_found: str = ""
    cursor_binary_found: str = ""
    token_session_id: str = ""
    claude_source_file: str = ""
    session_env_written: bool = False
    stdout_emissions: tuple[SetupEmission, ...] = ()
    stderr_diagnostics: tuple[str, ...] = ()


class SessionSetupError(Exception):
    """Setup preflight failed and must short-circuit the wrapper."""

    def __init__(self, *, returncode: int, output: str) -> None:
        super().__init__(output)
        self.returncode = returncode
        self.output = output


@dataclass(frozen=True)
class GateResult:
    entry_gate: str
    skip_branch_check: str


def _scripts_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "scripts"


def _emit(text: str) -> None:
    logging_util.emit(text)


def _err(message: str) -> None:
    logging_util.BreadcrumbWriter().emit(message)


def _plain_err(message: str) -> None:
    print(message, file=sys.stderr)


def _is_bool(value: str) -> bool:
    return value in _BOOL


def _read_kv_file_text(path: Path) -> str:
    text = path.read_bytes().decode("utf-8", errors="replace")
    if "\r" in text:
        msg = f"session env file contains carriage return: {path}"
        raise ValueError(msg)
    return text


def cleanup_cache_sessions_root(*, env: Mapping[str, str] | None = None) -> Path:
    environ = os.environ if env is None else env
    xdg = environ.get("XDG_CACHE_HOME")
    if xdg:
        base = xdg
    else:
        home = environ.get("HOME", "")
        base = f"{home}/.cache" if home else f"{TMP_FALLBACK}/.cache"
    return Path(base) / "larch" / "sessions"


def check_live_mutation_auth(
    *,
    context_file: Path | None,
    operator_mode: bool,
    run_id: str = "",
    trusted_root: Path | None = None,
) -> tuple[bool, str]:
    """Check authorization for live GitHub issue mutation.

    Returns (authorized, reason). Test denial overrides session-inherited auth
    but not explicit operator-invoked mode. Operator mode bypasses context-file
    validation. Session-backed calls require a regular, non-symlink context file
    under a trusted session root that contains LARCH_LIVE_MUTATION_OK=true with
    a matching run identity.
    """
    if operator_mode:
        return True, config.LIVE_MUTATION_OPERATOR_MODE
    if os.environ.get(config.LIVE_MUTATION_TEST_DENY_KEY) == "true":
        return False, "test-denied"
    if context_file is None:
        return False, config.LIVE_MUTATION_REFUSAL_REASON
    try:
        ctx = Path(context_file)
        if not ctx.exists() or not ctx.is_file() or ctx.is_symlink():
            return False, config.LIVE_MUTATION_REFUSAL_REASON
        if trusted_root is None or not _is_canonical_mutation_session_root(trusted_root):
            return False, config.LIVE_MUTATION_REFUSAL_REASON
        if ctx.parent.resolve() != trusted_root.resolve():
            return False, config.LIVE_MUTATION_REFUSAL_REASON
        auth_value = ""
        ctx_run_id = ""
        for raw in ctx.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip("'\"")
            if k == config.LIVE_MUTATION_AUTH_KEY:
                auth_value = v
            elif k == "LARCH_RUN_ID":
                ctx_run_id = v
        if auth_value != "true":
            return False, config.LIVE_MUTATION_REFUSAL_REASON
        if not ctx_run_id or not _SAFE_RUN_ID_RE.fullmatch(ctx_run_id):
            return False, config.LIVE_MUTATION_REFUSAL_REASON
        if run_id != ctx_run_id:
            return False, config.LIVE_MUTATION_REFUSAL_REASON
        return True, config.LIVE_MUTATION_SESSION_MODE
    except OSError:
        return False, config.LIVE_MUTATION_REFUSAL_REASON


def _is_canonical_mutation_session_root(path: Path) -> bool:
    """Return whether *path* is a larch-created design or implement session."""
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return False
    if not resolved.is_dir() or not re.fullmatch(r"claude-(?:design|implement)-[A-Za-z0-9._-]+", resolved.name):
        return False
    roots = (
        cleanup_cache_sessions_root(),
        TMP_ROOT,
        Path("/private/tmp"),
        Path("/var/folders"),
        Path("/private/var/folders"),
    )
    return any(_strictly_under(path=resolved, root=root) for root in roots)


def check_live_mutation_auth_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session check-live-mutation-auth", add_help=False)
    parser.add_argument("--context-file", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--trusted-root", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    authorized, _reason = check_live_mutation_auth(
        context_file=Path(args.context_file),
        operator_mode=False,
        run_id=args.run_id,
        trusted_root=Path(args.trusted_root),
    )
    return 0 if authorized else config.EXIT_MUTATION_REFUSED


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


def run_log_write_argv(*, log_root: Path, run_id: str, batch: str, input_file: Path) -> list[str]:
    """Build the shared run-log write argv tail for implement artifacts."""
    return [
        "run-log", "write", "--log-root", str(log_root), "--skill", "implement",
        "--run-id", run_id, "--batch", batch, "--input-file", str(input_file),
    ]


def read_finalize_state(path: str | Path) -> dict[str, str]:
    target = Path(path)
    if not target.is_file():
        return {}
    data: dict[str, str] = {}
    try:
        values = larch_io.parse_kv(
            _read_kv_file_text(target),
            duplicate_policy="last",
            skip_comments=True,
            key_pattern=_KEY_RE,
        )
    except ValueError as exc:
        raise ShipError(str(exc)) from exc
    for key, value in values.items():
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


def _validate_repo_root_value(*, value: str, flag: str) -> None:
    if not value:
        return
    if len(value) > MAX_PATH_VALUE_LEN or "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError(f"Invalid {flag}: must be an absolute single-line path")
    if not value.startswith("/"):
        raise ValueError(f"Invalid {flag}: must be an absolute path")


def _parse_key_value_file(path: str) -> dict[str, str]:
    if not path or not Path(path).is_file():
        return {}
    parsed = larch_io.parse_kv(
        _read_kv_file_text(Path(path)),
        duplicate_policy="last",
        skip_comments=True,
        allowed_keys=CALLER_ENV_KEYS,
    )
    return {key: value for key, value in parsed.items() if value}


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


@dataclass(frozen=True)
class WriteEnvParams:
    output: str
    repo_unavailable: str | None
    repo: str = ""
    repo_root: str = ""
    codex_present: str = ""
    cursor_present: str = ""
    codex_available: str = ""
    cursor_available: str = ""
    claude_binary_found: str = ""
    codex_binary_found: str = ""
    cursor_binary_found: str = ""
    auto_mode: str = ""
    forked_target: str = "false"
    timing_ledger: str = ""
    token_session_id: str = ""
    claude_source_file: str = ""
    prev_implement_tmpdir: str = ""
    dynamic_archetypes: str = ""
    run_id: str = ""
    live_mutation_ok: str = ""
    plugin_root_only: bool = False
    value: str = ""


def _write_env_flags(params: WriteEnvParams) -> list[str]:
    """Render the optional ``session write-env`` value flags in CLI order."""
    return [
        argument
        for flag, value in (
            ("--repo", params.repo),
            ("--repo-root", params.repo_root),
            ("--codex-present", params.codex_present),
            ("--cursor-present", params.cursor_present),
            ("--codex-available", params.codex_available),
            ("--cursor-available", params.cursor_available),
            ("--claude-binary-found", params.claude_binary_found),
            ("--codex-binary-found", params.codex_binary_found),
            ("--cursor-binary-found", params.cursor_binary_found),
            ("--auto-mode", params.auto_mode),
            ("--timing-ledger", params.timing_ledger),
            ("--token-session-id", params.token_session_id),
            ("--claude-source-file", params.claude_source_file),
            ("--prev-implement-tmpdir", params.prev_implement_tmpdir),
            ("--dynamic-archetypes", params.dynamic_archetypes),
            ("--run-id", params.run_id),
            ("--live-mutation-ok", params.live_mutation_ok),
        )
        if value
        for argument in (flag, value)
    ]


def write_env_argv(params: WriteEnvParams) -> list[str]:
    """Render the ``session write-env`` flags for the Rust owner."""
    if params.plugin_root_only:
        return ["--plugin-root-only", "--output", params.output, "--value", params.value]
    return [
        "--output", params.output,
        "--repo-unavailable", params.repo_unavailable or "false",
        "--forked-target", params.forked_target,
        *_write_env_flags(params),
    ]


def run_write_env(params: WriteEnvParams) -> proc.CommandResult:
    """Write one session-env file through the Rust owner's verified entrypoint."""
    return proc.run([
        str(larch_entrypoint(_scripts_dir().parent)), "session", "write-env",
        *write_env_argv(params),
    ])


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


def _design_symlink_path(pid: str) -> Path:
    home = Path.home()
    return home / ".cache" / "larch" / "sessions" / (f"current-design-env-{pid}.sh" if pid else "current-design-env.sh")


def _design_run_path(pid: str) -> Path:
    return Path.home() / ".cache" / "larch" / "sessions" / f"design-run-{pid}.sh"


def _step0_parsed_env_path(pid: str) -> Path:
    return Path.home() / ".cache" / "larch" / "sessions" / f"step0-parsed-{pid}.env"


def reap_pid_residuals(claude_pid: str) -> None:
    _validate_claude_pid(claude_pid)
    symlink_path = _design_symlink_path(claude_pid)
    _validate_design_current_env_link(symlink_path=symlink_path, pid=claude_pid)
    with suppress(FileNotFoundError):
        symlink_path.unlink()

    for target in (_design_run_path(claude_pid), _step0_parsed_env_path(claude_pid)):
        larch_io.assert_no_symlink_path_or_ancestors(target)
        with suppress(FileNotFoundError):
            target.unlink()


def _validate_claude_pid(pid: str) -> None:
    if not re.match(r"^[1-9][0-9]{0,6}$", pid):
        raise ValueError("Invalid --claude-pid: must be a positive integer of at most 7 decimal digits")


validate_claude_pid = _validate_claude_pid


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


def write_id(*, output: Path) -> WriteIdResult:
    """Idempotently write a session-id file under an allowed session root.

    Preserves a pre-existing non-empty id (``wrote=False``); otherwise writes a
    fresh uuid/basename id. Raises ``OSError`` on disallowed or unwritable targets.
    """
    if not _writer_target_allowed(output):
        raise OSError(f"output path not under allowed session root: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not _safe_output_parent(output):
        raise OSError(f"output parent is not a writable directory: {output.parent}")
    if output.is_file() and output.stat().st_size > 0:
        existing = ""
        with suppress(OSError):
            lines = output.read_text(encoding="utf-8", errors="replace").splitlines()
            existing = lines[0] if lines else ""
        return WriteIdResult(output=output, session_id=existing, wrote=False)
    session_id = _uuid_or_basename(output.parent)
    _atomic_write(path=output, text=session_id + "\n")
    return WriteIdResult(output=output, session_id=session_id, wrote=True)


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
    try:
        result = entry_gate(
            mode=args.mode,
            is_main=args.is_main,
            is_user_branch=args.is_user_branch,
            user_prefix=args.user_prefix,
            branch_info_supplied=args.branch_info_supplied,
        )
    except ValueError as exc:
        return fail(str(exc))
    logging_util.quiet_init(argv0="session-entry-gate.sh")
    logging_util.emit_kv(key="ENTRY_GATE", value=result.entry_gate)
    logging_util.emit_kv(key="SKIP_BRANCH_CHECK", value=result.skip_branch_check)
    return 0


def entry_gate(
    *,
    mode: str,
    is_main: str,
    is_user_branch: str,
    user_prefix: str,
    branch_info_supplied: str | None,
) -> GateResult:
    """Resolve the entry-gate decision from validated branch inputs.

    Raises ``ValueError`` (carrying the exact ``GATE_ERROR`` message) for an
    invalid mode, empty user prefix, non-boolean flag, or a
    ``--branch-info-supplied`` misused under ``mode=implement``.
    """
    if mode not in {"implement", "design"}:
        raise ValueError(f"invalid mode: {mode}")
    if not user_prefix:
        raise ValueError("--user-prefix must be non-empty")
    if not _is_bool(is_main):
        raise ValueError(f"invalid value for --is-main: {is_main}")
    if not _is_bool(is_user_branch):
        raise ValueError(f"invalid value for --is-user-branch: {is_user_branch}")
    if mode == "implement" and branch_info_supplied is not None:
        raise ValueError("--branch-info-supplied not allowed for mode=implement")
    branch_info = branch_info_supplied or "false"
    if not _is_bool(branch_info):
        raise ValueError(f"invalid value for --branch-info-supplied: {branch_info}")
    resolved_gate = "strict"
    skip_branch_check = "false"
    if (mode == "design" and branch_info == "true") or is_user_branch == "true":
        resolved_gate = "continue"
        skip_branch_check = "true"
    return GateResult(entry_gate=resolved_gate, skip_branch_check=skip_branch_check)


def _repo_from_gh_or_git(runner: Runner) -> str:
    try:
        return gh.resolve_repo(runner) or ""
    except OSError:
        return ""


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


def _setup_repo_root(*, caller: dict[str, str], emissions: list[SetupEmission]) -> str:
    """Resolve the operator repo root once at the session-setup trust boundary.

    Tier order: caller-env value, then ``CLAUDE_PROJECT_DIR``/``REPO_ROOT``
    env, then the setup process cwd (the invoking checkout). Each non-cwd tier
    must pass the shared ``--repo-root`` validation (absolute, single-line,
    bounded); an invalid tier falls through so no unvalidated value reaches
    the line-oriented stdout grammar. Appends the ``REPO_ROOT`` stdout
    emission and returns the resolved value.
    """
    repo_root = str(Path.cwd())
    for candidate in (
        caller.get("REPO_ROOT", "").strip(),
        os.environ.get("CLAUDE_PROJECT_DIR", "").strip(),
        os.environ.get("REPO_ROOT", "").strip(),
    ):
        if not candidate:
            continue
        try:
            _validate_repo_root_value(value=candidate, flag="--repo-root")
        except ValueError:
            continue
        repo_root = candidate
        break
    emissions.append(SetupEmission(kind="kv", key="REPO_ROOT", value=repo_root))
    return repo_root


def _dispatch_session_env_write(params: WriteEnvParams) -> tuple[bool, list[str]]:
    """Dispatch the Rust-owned session-env writer for :func:`setup`.

    Returns whether the file was written and the writer's stderr lines, which the
    caller re-emits as its own diagnostics.
    """
    written = run_write_env(params)
    if written.returncode == 0:
        return True, []
    return False, [line for line in written.stderr.splitlines() if line]


def _setup_write_env_params(  # noqa: PLR0913 - session-env inputs stay explicit seams for one caller
    *,
    write_session_env: str,
    caller: dict[str, str],
    caller_env: str,
    repo_value: str,
    repo_root: str,
    repo_unavailable: str,
    final_codex: str,
    final_cursor: str,
    final_claude_bin: str,
    final_codex_bin: str,
    final_cursor_bin: str,
) -> tuple[WriteEnvParams, list[str]]:
    """Build the session-env :class:`WriteEnvParams` for :func:`setup`.

    Pre-filters caller-supplied dynamic-archetypes and timing-ledger values,
    returning the parameters plus any ordered stderr diagnostics for rejected
    caller-env values (matching the wrapper's warnings).
    """
    diagnostics: list[str] = []
    dyn = caller.get("LARCH_DYNAMIC_ARCHETYPES_MAX", "")
    dynamic_archetypes = ""
    if dyn:
        if dyn in {"0", "1"}:
            dynamic_archetypes = dyn
        else:
            diagnostics.append("session-setup.sh: warning: ignoring invalid LARCH_DYNAMIC_ARCHETYPES_MAX from caller-env (must be 0..1)")
    ledger = caller.get("LARCH_TIMING_LEDGER", "")
    timing_ledger = ""
    if ledger:
        caller_dir = str(Path(caller_env).parent.resolve()) if caller_env else ""
        if _safe_timing_ledger_path(path=ledger, caller_env_dir=caller_dir):
            timing_ledger = ledger
        else:
            diagnostics.append("session-setup.sh: warning: ignoring unsafe LARCH_TIMING_LEDGER from caller-env (not under accepted root)")
    params = WriteEnvParams(
        output=write_session_env,
        repo_unavailable=repo_unavailable,
        repo=repo_value,
        repo_root=repo_root,
        codex_present=final_codex,
        cursor_present=final_cursor,
        claude_binary_found=final_claude_bin,
        codex_binary_found=final_codex_bin,
        cursor_binary_found=final_cursor_bin,
        token_session_id=caller.get("LARCH_TOKEN_SESSION_ID", ""),
        claude_source_file=caller.get("LARCH_CLAUDE_SOURCE_FILE", ""),
        dynamic_archetypes=dynamic_archetypes,
        timing_ledger=timing_ledger,
    )
    return params, diagnostics


def setup(  # noqa: PLR0913 - session-setup CLI flags are independent probe/skip seams
    *,
    prefix: str,
    skip_preflight: bool = False,
    skip_branch_check: bool = False,
    skip_repo_check: bool = False,
    check_reviewers: bool = False,
    skip_codex_probe: bool = False,
    skip_cursor_probe: bool = False,
    write_session_env: str = "",
    caller_env: str = "",
) -> SessionSetupResult:
    """Own the full session-setup side effects and return an ordered emission envelope.

    Performs preflight/stale-plugin probes, session tmpdir/identity creation,
    optional prior-log carry-forward, repo resolution, reviewer probes, and
    optional session-env writing (via :func:`write_env`, never the CLI wrapper).
    Preflight failure raises :class:`SessionSetupError`; other outcomes return a
    :class:`SessionSetupResult` whose ``stdout_emissions``/``stderr_diagnostics``
    reproduce the wrapper's exact successful output without re-probing.
    """
    runner = proc
    emissions: list[SetupEmission] = []
    diagnostics: list[str] = []
    caller = _parse_key_value_file(caller_env)
    if not skip_preflight:
        cmd = [sys.executable, str(Path(__file__).resolve().parents[2] / "cli.py"), "admission", "preflight"]
        if skip_branch_check:
            cmd.append("--skip-branch-check")
        preflight = runner.run(cmd)
        if preflight.returncode != 0:
            raise SessionSetupError(returncode=preflight.returncode, output=preflight.stdout + preflight.stderr)
        stale = runner.run([str(_scripts_dir() / "check-stale-plugin.sh")])
        if stale.returncode != 0:
            diagnostics.append(f"session-setup.sh: warning: stale plugin check failed (rc={stale.returncode}): {stale.stdout}{stale.stderr}")
        elif "STALE_PLUGIN_CHECK=working-tree-ahead" in stale.stdout:
            data = _parse_text_kv(stale.stdout)
            emissions.append(SetupEmission(kind="line", key=f"**⚠ larch: installed plugin version ({data.get('STALE_PLUGIN_INSTALLED_VERSION','')}) is behind the working tree ({data.get('STALE_PLUGIN_WORKING_TREE_VERSION','')}). Reinstall or refresh the plugin from this checkout before the next run to pick up the latest fixes. Continuing with the cached version.**"))
    tmpdir = _make_session_tmpdir(prefix)
    session_id = _uuid_or_basename(tmpdir)
    _write_session_identity(tmpdir=tmpdir, session_id=session_id)
    render_cache_dir = tmpdir / "render-cache"
    emissions.append(SetupEmission(kind="kv", key="SESSION_TMPDIR", value=str(tmpdir)))
    emissions.append(SetupEmission(kind="kv", key="SESSION_ID", value=session_id))
    emissions.append(SetupEmission(kind="kv", key="LARCH_RENDER_CACHE_DIR", value=str(render_cache_dir)))
    prev = caller.get("PREV_IMPLEMENT_TMPDIR", "")
    if prev and (Path(prev) / "larch-logs").is_dir():
        with suppress(OSError):
            shutil.copytree(
                Path(prev) / "larch-logs",
                tmpdir / "larch-logs",
                dirs_exist_ok=True,
                ignore=_ignore_placeholder_run_dirs,
            )
    if not os.environ.get(config.ENV_LARCH_CURSOR_MODEL) and os.environ.get(config.ENV_CLAUDE_PLUGIN_OPTION_CURSOR_MODEL):
        os.environ[config.ENV_LARCH_CURSOR_MODEL] = os.environ[config.ENV_CLAUDE_PLUGIN_OPTION_CURSOR_MODEL]
    if not os.environ.get(config.ENV_LARCH_CODEX_MODEL) and os.environ.get(config.ENV_CLAUDE_PLUGIN_OPTION_CODEX_MODEL):
        os.environ[config.ENV_LARCH_CODEX_MODEL] = os.environ[config.ENV_CLAUDE_PLUGIN_OPTION_CODEX_MODEL]
    repo_value = ""
    repo_unavailable = "false"
    repo_checked = not skip_repo_check
    if repo_checked:
        if caller.get("REPO") or caller.get("REPO_UNAVAILABLE"):
            repo_value = caller.get("REPO", "")
            repo_unavailable = caller.get("REPO_UNAVAILABLE", "false")
        else:
            repo_value = _repo_from_gh_or_git(runner)
            repo_unavailable = "false" if repo_value else "true"
        emissions.extend((
            SetupEmission(kind="kv", key="REPO", value=repo_value),
            SetupEmission(kind="kv", key="REPO_UNAVAILABLE", value=repo_unavailable),
        ))
    repo_root = _setup_repo_root(caller=caller, emissions=emissions)
    final_codex = ""
    final_cursor = ""
    final_claude_bin = caller.get("CLAUDE_BINARY_FOUND", "")
    final_codex_bin = caller.get("CODEX_BINARY_FOUND", "")
    final_cursor_bin = caller.get("CURSOR_BINARY_FOUND", "")
    if final_claude_bin not in _BOOL:
        final_claude_bin = "true" if shutil.which("claude") else "false"
    if check_reviewers:
        # agents.check_reviewers is a real module-level function (see agents.py);
        # a newer pyright misresolves this cross-module attribute while the
        # repo-pinned pyright is clean. Suppress the false positive (#4439).
        reviewer = agents.check_reviewers(  # pyright: ignore[reportAttributeAccessIssue]
            skip_codex_probe=skip_codex_probe or bool(final_codex),
            skip_cursor_probe=skip_cursor_probe or bool(final_cursor),
        )
        probed = reviewer.kv()
        emissions.extend(
            SetupEmission(kind="kv", key=key, value=probed[key])
            for key in ("CODEX_PRESENT", "CURSOR_PRESENT", "CODEX_BINARY_FOUND", "CURSOR_BINARY_FOUND")
            if probed.get(key)
        )
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
            emissions.append(SetupEmission(kind="kv", key="CODEX_BINARY_FOUND", value=final_codex_bin))
        if final_cursor_bin in _BOOL:
            emissions.append(SetupEmission(kind="kv", key="CURSOR_BINARY_FOUND", value=final_cursor_bin))
    emissions.append(SetupEmission(kind="kv", key="CLAUDE_BINARY_FOUND", value=final_claude_bin))
    token_session_id = caller.get("LARCH_TOKEN_SESSION_ID", "")
    claude_source_file = caller.get("LARCH_CLAUDE_SOURCE_FILE", "")
    if token_session_id:
        emissions.append(SetupEmission(kind="kv", key="LARCH_TOKEN_SESSION_ID", value=token_session_id))
    if claude_source_file:
        emissions.append(SetupEmission(kind="kv", key="LARCH_CLAUDE_SOURCE_FILE", value=claude_source_file))
    session_env_written = False
    exit_code = 0
    if write_session_env:
        params, write_diagnostics = _setup_write_env_params(
            write_session_env=write_session_env,
            caller=caller,
            caller_env=caller_env,
            repo_value=repo_value,
            repo_root=repo_root,
            repo_unavailable=repo_unavailable,
            final_codex=final_codex,
            final_cursor=final_cursor,
            final_claude_bin=final_claude_bin,
            final_codex_bin=final_codex_bin,
            final_cursor_bin=final_cursor_bin,
        )
        diagnostics.extend(write_diagnostics)
        session_env_written, write_failures = _dispatch_session_env_write(params)
        diagnostics.extend(write_failures)
        exit_code = 0 if session_env_written else 1
    return SessionSetupResult(
        session_tmpdir=tmpdir,
        session_id=session_id,
        render_cache_dir=render_cache_dir,
        claude_binary_found=final_claude_bin,
        exit_code=exit_code,
        repo_checked=repo_checked,
        repo=repo_value,
        repo_unavailable=repo_unavailable,
        reviewers_checked=check_reviewers,
        codex_present=final_codex,
        cursor_present=final_cursor,
        codex_binary_found=final_codex_bin,
        cursor_binary_found=final_cursor_bin,
        token_session_id=token_session_id,
        claude_source_file=claude_source_file,
        session_env_written=session_env_written,
        stdout_emissions=tuple(emissions),
        stderr_diagnostics=tuple(diagnostics),
    )


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
    if not args.prefix:
        _err("session-setup.sh: --prefix is required")
        return 4
    try:
        result = setup(
            prefix=args.prefix,
            skip_preflight=args.skip_preflight,
            skip_branch_check=args.skip_branch_check,
            skip_repo_check=args.skip_repo_check,
            check_reviewers=args.check_reviewers,
            skip_codex_probe=args.skip_codex_probe,
            skip_cursor_probe=args.skip_cursor_probe,
            write_session_env=args.write_session_env,
            caller_env=args.caller_env,
        )
    except SessionSetupError as exc:
        _emit(exc.output)
        return exc.returncode
    for emission in result.stdout_emissions:
        if emission.kind == "kv":
            logging_util.emit_kv(key=emission.key, value=emission.value)
        else:
            _emit(emission.key)
    for line in result.stderr_diagnostics:
        _err(line)
    return result.exit_code


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


@dataclass(frozen=True)
class BranchDeleteResult:
    cleanup_success: bool
    branch_deleted: bool


def _delete_local_branch(branch: str) -> BranchDeleteResult:
    branch_ref = proc.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"])
    if branch_ref.returncode == 1:
        print(f"Local branch {branch} was already deleted", file=sys.stderr)
        return BranchDeleteResult(cleanup_success=True, branch_deleted=False)
    if branch_ref.returncode != 0:
        print(f"❌ Failed to check local branch {branch}", file=sys.stderr)
        return BranchDeleteResult(cleanup_success=False, branch_deleted=False)
    print(f"🔄 Deleting local branch {branch}...", file=sys.stderr)
    if proc.run(["git", "branch", "-D", "--", branch]).returncode == 0:
        return BranchDeleteResult(cleanup_success=True, branch_deleted=True)
    print(f"❌ Failed to delete local branch {branch}", file=sys.stderr)
    return BranchDeleteResult(cleanup_success=False, branch_deleted=False)


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
        if _transient_run(["git", "fetch", "origin", "main"]).returncode != 0:
            print("⚠ Failed to fetch origin main (continuing)", file=sys.stderr)
        print("🔄 Fast-forwarding local main from origin/main...", file=sys.stderr)
        if _transient_run(["git", "pull", "--ff-only", "origin", "main"]).returncode != 0:
            ahead_after = _numeric_stdout(proc.run(["git", "rev-list", "--count", "origin/main..HEAD"]))
            if ahead_after > 0:
                print(f"❌ Failed to pull origin main; local main is ahead of origin/main by {ahead_after} commit(s). Push or reconcile local main before retrying.", file=sys.stderr)
            else:
                print("❌ Failed to pull origin main", file=sys.stderr)
            return 0
        branch_result = _delete_local_branch(args.branch)
        if branch_result.cleanup_success:
            branch_deleted = "true" if branch_result.branch_deleted else "false"
            cleanup_success = "true"
            print("✅ Local cleanup complete", file=sys.stderr)
        return 0
    finally:
        print(f"CLEANUP_SUCCESS={cleanup_success}")
        print(f"CURRENT_BRANCH={current_branch}")
        print(f"BRANCH_DELETED={branch_deleted}")
