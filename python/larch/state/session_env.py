"""Session/state lifecycle verbs for the larch Python runtime.

Issue #8057 moved the six ``session setup`` and temp-directory lifecycle
commands to the Rust owner: ``setup``, ``require-plugin-root``,
``validate-design-tmpdir``, ``write-id``, ``resolve-implement-tmpdir``, and
``cleanup-tmpdir`` no longer register here.
``require_plugin_root``, ``validate_design_tmpdir``, and ``write_id`` survive as
library helpers because Python-owned commands in ``larch.design`` and
``larch.state.bootstrap`` still call them in process; their CLI entrypoints and
the fully orphaned implement-tmpdir resolver are gone.

Issue #8058 moved the eight session-env and run-flag writers — ``write-env``,
``write-design-env``, ``write-implement-env``, ``clear-implement-pointer``,
``persist-run-flags``, ``write-run-params``, ``restore-finalize-state``, and
``resolve-trusted-design-env`` — to the Rust owner, entrypoints and
implementations alike. Nothing here writes a session-env file any more:
``larch.state.bootstrap`` reaches session setup through the verified bootstrap
script, and the argument renderers below keep one owner for each writer flag
spelling.
``read_finalize_state`` and ``write_finalize_state_merged`` stay because
``implement-finalize teardown`` still reads and merges that file in process.
"""
# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false

from __future__ import annotations

import os
import re
import shlex
import shutil
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Mapping

from larch.core import config
from larch import io as larch_io
from larch.core import proc
from larch.errors import ShipError
from larch.core.repo_roots import larch_entrypoint

_SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
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


def _scripts_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "scripts"


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
        try:
            mode_stat = ancestor.lstat()
        except OSError:
            mode_stat = None
        if mode_stat is not None and larch_io.is_refused_symlink(mode_stat):
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
