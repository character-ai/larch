"""Step 0 environment constants, wrapper-arg parser, bash-quoting codec, and env loaders."""
# pylint: disable=cyclic-import
# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

import argparse
import contextlib
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from collections.abc import Iterable, Mapping, Sequence

from larch.state import session_env

_SUBPROCESS_RUN = subprocess.run

COMMON_ENV_DEFAULTS: dict[str, str] = {
    **session_env.COMMON_DESIGN_ENV_DEFAULTS,
    "POSITIONAL_KIND": "",
    "POSITIONAL_VALUE": "",
    "partition_requested": "false",
    "brainstorm_requested": "false",
    "approve_requested": "false",
    "skip_approve_requested": "false",
    "no_dedup_requested": "false",
    "run_id": "",
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
PARSED_ENV_KEYS = (
    "partition_requested",
    "brainstorm_requested",
    "approve_requested",
    "skip_approve_requested",
    "no_dedup_requested",
    "run_id",
    "POSITIONAL_KIND",
    "POSITIONAL_VALUE",
)
ROUTE_STATE_KEYS = frozenset({"ROUTE", "RESUME_STEP", "HAS_CLARIFY_LABEL", "ISSUE_NUMBER", "ISSUE_TITLE", "REPO", "brainstorm_requested"})
ROUTE_RESULT_KEYS = frozenset({
    "ROUTE",
    "BRAINSTORM_PREFIX",
    "TITLE_FILTER_REASON",
    "TITLE_FILTER_MARKER",
    "MARKER_AGE",
    "MARKER_TTL",
    "DESIGN_REENTRY_MARKER_PATH",
    "RESUME_STEP",
    "SESSION_ID",
    "RUN_ID",
    "BRAINSTORM_DONE",
    "MARKER_CLEARED",
})
INIT_RESULT_KEYS = frozenset({"INIT_STATUS", "RENAMED", "RUN_PARAMS_PATH"})


def _emit_step0_route_rows(*, route: str, resume_step: str, route_env: Mapping[str, str], env: Mapping[str, str]) -> None:
    if resume_step:
        if route_env.get("MARKER_CLEARED"):
            print(f"MARKER_CLEARED={route_env['MARKER_CLEARED']}")
        print(f"🔓 resumed from STEP={resume_step}")
    print(f"ROUTE={route}")
    if resume_step:
        print(f"RESUME_STEP={resume_step}")
    if route_env.get("MARKER_CLEARED"):
        print(f"MARKER_CLEARED={route_env['MARKER_CLEARED']}")
    for key in ("TITLE_FILTER_REASON", "TITLE_FILTER_MARKER", "DESIGN_REENTRY_MARKER_PATH"):
        if route_env.get(key):
            print(f"{key}={route_env[key]}")
    print(f"HAS_CLARIFY_LABEL={env.get('HAS_CLARIFY_LABEL', 'false')}")
    print(f"ISSUE_NUMBER={env.get('ISSUE_NUMBER', '')}")
    print(f"ISSUE_TITLE={env.get('ISSUE_TITLE', '')}")
    if env.get("REPO"):
        print(f"REPO={env['REPO']}")


def _emit_step0_init_rows(result: Mapping[str, str]) -> None:
    for key in ("INIT_STATUS", "RENAMED", "RUN_PARAMS_PATH"):
        print(f"{key}={result.get(key, '')}")

_TEMPLATE_PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}"
PARSE_VALIDATION_RC = 3
CONFIGURATION_ERROR_RC = 2


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[3]


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


def _bash_percent_q(value: str) -> str:
    proc = _SUBPROCESS_RUN(
        ["bash", "-c", 'printf "%q" "$1"', "_", value],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return proc.stdout
    if value == "":
        return "''"
    return shlex.quote(value)


def write_bash_quoted_env(*, path: Path, data: Mapping[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={_bash_percent_q(data.get(key, ''))}\n" for key in PARSED_ENV_KEYS]
    path.write_text("".join(lines), encoding="utf-8")


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
    allow = set(allow_keys)
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in allow:
            data[key] = _decode_shell_assignment_value(value)
    return data


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
    allow = set(allow_keys)
    data: dict[str, str] = {}
    for raw in read_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ")
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key not in allow:
            continue
        data[key] = _decode_shell_assignment_value(value)
    return data


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


def _parsed_cache_path(claude_pid: str) -> Path:
    return Path.home() / ".cache" / "larch" / "sessions" / f"step0-parsed-{claude_pid}.env"


def _run_parse_argv(*, public_argv: Sequence[str], plugin_root: Path) -> tuple[int, dict[str, str], str]:
    with tempfile.NamedTemporaryFile(prefix="larch-argv.", delete=False) as out:
        out_path = Path(out.name)
    try:
        proc = subprocess.run(
            [sys.executable, str(plugin_root / "python" / "cli.py"), "design", "parse-argv", "--output", str(out_path), *public_argv],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        data = load_bash_quoted_env(path=out_path, allow_keys=[*PARSED_ENV_KEYS, "VALIDATION_ERROR"])
        return proc.returncode, data, proc.stderr
    finally:
        with contextlib.suppress(FileNotFoundError):
            out_path.unlink()


def _validate_parse_result(*, rc: int, data: dict[str, str], stderr_text: str) -> None:
    positional = data.get("POSITIONAL_VALUE", "")
    if "PUBLIC_ARGV_WORDS" in stderr_text or positional in {"${PUBLIC_ARGV_WORDS}", "$PUBLIC_ARGV_WORDS"}:
        print("**⚠ /design: skill loader did not expand public argv words; aborting before session setup.**", file=sys.stderr)
        raise SystemExit(1)
    validation_error = data.get("VALIDATION_ERROR", "")
    if rc == PARSE_VALIDATION_RC:
        if validation_error:
            print(f"**⚠ /design: unrecognized or disallowed public flag — aborting before session setup.** {validation_error}", file=sys.stderr)
        else:
            print("**⚠ /design: unrecognized or disallowed public flag — aborting before session setup.**", file=sys.stderr)
        raise SystemExit(1)
    if rc == 0:
        if validation_error:
            print(f"**⚠ /design: design parse-argv reported VALIDATION_ERROR but exited {rc}; aborting before session setup.**", file=sys.stderr)
            raise SystemExit(1)
    else:
        print(f"**⚠ /design: design parse-argv failed (exit {rc}); aborting before session setup.**", file=sys.stderr)
        raise SystemExit(1)
    if data.get("POSITIONAL_KIND", "") not in {"issue", "verbal", "none"}:
        print("**⚠ /design: design parse-argv emitted invalid POSITIONAL_KIND; aborting before session setup.**", file=sys.stderr)
        raise SystemExit(1)


def _parse_and_persist(*, ns: Step0WrapperNs, plugin_root: Path) -> tuple[Path, dict[str, str]]:
    rc, data, stderr_text = _run_parse_argv(public_argv=ns.public_argv, plugin_root=plugin_root)
    _validate_parse_result(rc=rc, data=data, stderr_text=stderr_text)
    for key in PARSED_ENV_KEYS:
        data.setdefault(key, "false" if key.endswith("_requested") or key == "no_dedup_requested" else "")
    if not data.get("POSITIONAL_KIND"):
        data["POSITIONAL_KIND"] = "none"
    cache = _parsed_cache_path(ns.claude_pid)
    write_bash_quoted_env(path=cache, data=data)
    return cache, data


def _emit_parse_kvs(*, cache: Path, data: Mapping[str, str]) -> None:
    print(f"STEP0_PARSED_ENV_PATH={cache}")
    print(f"PARTITION_REQUESTED={data.get('partition_requested', 'false')}")
    print(f"BRAINSTORM_REQUESTED={data.get('brainstorm_requested', 'false')}")
    print(f"APPROVE_REQUESTED={data.get('approve_requested', 'false')}")
    print(f"SKIP_APPROVE_REQUESTED={data.get('skip_approve_requested', 'false')}")
    print(f"NO_DEDUP_REQUESTED={data.get('no_dedup_requested', 'false')}")
    print(f"RUN_ID={data.get('run_id', '')}")
    print(f"POSITIONAL_KIND={data.get('POSITIONAL_KIND', '')}")
    print(f"POSITIONAL_VALUE={data.get('POSITIONAL_VALUE', '')}")


def step0_parse_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    plugin_root = require_plugin_root(ns.plugin_root)
    if not ns.plugin_root:
        print(f"/design Step 0-pre: CLAUDE_PLUGIN_ROOT is empty after export — skill loader must expand {_TEMPLATE_PLUGIN_ROOT} in the template line before Bash runs; abort", file=sys.stderr)
        return 1
    cache, data = _parse_and_persist(ns=ns, plugin_root=plugin_root)
    _emit_parse_kvs(cache=cache, data=data)
    return 0
