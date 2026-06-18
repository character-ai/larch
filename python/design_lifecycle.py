"""Python CLI entrypoints and shared helpers for /design lifecycle phases."""
# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedFunction=false

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
import sys
import tempfile
from pathlib import Path

import design_pause
from collections.abc import Iterable, Mapping, Sequence


def _valid_var_name(value: str) -> bool:
    if not value or value[0].isdigit():
        return False
    return all(ch.isalnum() or ch == "_" for ch in value)


def _quote_single(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def phase_driver_read_result_env(path: str | Path, allow_keys: Iterable[str]) -> list[tuple[str, str]]:
    """Read allowlisted KEY=VALUE records from a result-env file.

    Blank and malformed lines are skipped. Values containing CR or LF are
    refused, matching the shell phase-driver trust boundary.
    """
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise OSError(f"result env is not a regular file: {source}")
    allow = set(allow_keys)
    pairs: list[tuple[str, str]] = []
    for raw in source.read_bytes().decode("utf-8", errors="replace").split("\n"):
        if raw == "":
            continue
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key not in allow:
            continue
        if "\n" in value or "\r" in value:
            continue
        pairs.append((key, value))
    return pairs


def _replay_warn_error(path: Path) -> None:
    for raw in path.read_bytes().decode("utf-8", errors="replace").split("\n"):
        if raw == "":
            continue
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key in {"WARN", "ERROR"}:
            print(f"{key}={value}")


def _classify_input(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if not path.exists():
        return "missing"
    if not path.is_file():
        return "nonregular"
    return "regular"


def read_result_env_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="cli.py design read-result-env",
        add_help=False,
    )
    parser.add_argument("--input", dest="input_path")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--fallback-input", dest="fallback_input", default="")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--allow", dest="allow", action="append", default=[])  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--output", dest="output_path")  # pyright: ignore[reportUnusedCallResult]
    try:
        ns, extra = parser.parse_known_args(list(argv))
    except SystemExit:
        _usage()
        return 1
    if extra or not ns.input_path or not ns.output_path or any(not _valid_var_name(k) for k in ns.allow):
        _usage()
        return 1

    input_path = Path(ns.input_path)
    fallback_path = Path(ns.fallback_input) if ns.fallback_input else None
    source_path: Path
    primary_kind = _classify_input(input_path)
    if primary_kind == "regular":
        source_path = input_path
    else:
        if fallback_path is None:
            return 1
        if primary_kind == "symlink":
            if str(input_path).endswith(".design-init-runparams-result.env"):
                print("**⚠ Step 0b: design-init-runparams result env is a symlink; refusing to source**")
            else:
                print(f"WARN=read-result-env input is a symlink; refusing primary path: {input_path}")
        if fallback_path.is_symlink() or not fallback_path.is_file():
            return 1
        source_path = fallback_path

    output_path = Path(ns.output_path)
    if not output_path.parent.is_dir():
        return 1

    def write_pairs(from_path: Path, tmp_path: Path) -> int:
        _replay_warn_error(from_path)
        try:
            pairs = phase_driver_read_result_env(from_path, ns.allow)
        except OSError:
            return 1
        with tmp_path.open("w", encoding="utf-8") as handle:
            for key, value in pairs:
                handle.write(f"{key}={_quote_single(value)}\n")  # pyright: ignore[reportUnusedCallResult]
        return 0

    fd = -1
    tmp_name = ""
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{output_path.name}.", dir=str(output_path.parent))
        os.close(fd)
        fd = -1
        tmp_path = Path(tmp_name)
        if write_pairs(source_path, tmp_path) != 0:
            return 1
        if tmp_path.stat().st_size == 0 and primary_kind == "regular" and fallback_path is not None and fallback_path.is_file() and not fallback_path.is_symlink():
            source_path = fallback_path
            if write_pairs(source_path, tmp_path) != 0:
                return 1
        tmp_path.replace(output_path)  # pyright: ignore[reportUnusedCallResult]
        tmp_name = ""
        return 0
    finally:
        if fd >= 0:
            os.close(fd)
        if tmp_name:
            with contextlib.suppress(FileNotFoundError):
                Path(tmp_name).unlink()


def _usage() -> None:
    print(
        "usage: read-result-env.sh --input PATH [--fallback-input PATH] --allow KEY ... --output PATH",
        file=sys.stderr,
    )


def route_main(argv: Sequence[str]) -> int:
    args = list(argv)
    required = {
        "--design-tmpdir": "",
        "--issue": "",
        "--issue-title": "",
        "--issue-body-file": "",
        "--has-clarify-label": "",
        "--claude-pid": "",
        "--session-id": "",
    }
    optional = {
        "--repo": "",
        "--partition-requested": "false",
        "--brainstorm-requested": "false",
        "--approve-requested": "false",
        "--skip-approve-requested": "false",
    }
    i = 0
    while i < len(args):
        token = args[i]
        if token in required or token in optional:
            if i + 1 >= len(args):
                print(f"design-route.sh: {token} requires a value", file=sys.stderr)
                return 2
            if token in required:
                required[token] = args[i + 1]
            else:
                optional[token] = args[i + 1]
            i += 2
            continue
        if token in {"-h", "--help"}:
            print(
                "Usage: design-route.sh --design-tmpdir PATH --issue N --issue-title STR --issue-body-file PATH "
                "--has-clarify-label true|false --claude-pid N --session-id STR",
                file=sys.stderr,
            )
            return 0
        print(f"design-route.sh: unknown option: {token}", file=sys.stderr)
        return 2
    if any(not value for value in required.values()):
        print("design-route.sh: missing required arguments", file=sys.stderr)
        return 2

    design_tmpdir = Path(required["--design-tmpdir"]).resolve()
    issue_body_file = Path(required["--issue-body-file"])
    if issue_body_file.is_symlink() or not issue_body_file.is_file():
        print("design-route.sh: issue-body-file must be a readable regular file", file=sys.stderr)
        return 2

    result_env = design_tmpdir / ".design-route-result.env"
    warn_lines: list[str] = []
    error_lines: list[str] = []
    route = ""
    brainstorm_prefix = "false"
    title_filter_reason = ""
    title_filter_marker = ""
    resume_step = ""
    session_id = ""
    run_id = ""
    brainstorm_done = ""
    marker_cleared = ""

    body = issue_body_file.read_text(encoding="utf-8", errors="replace")
    if "<!-- larch:design-pause:start -->" in body:
        pause_cmd = [sys.executable, str(Path(__file__).with_name("cli.py")), "design", "pause-load", "--design-tmpdir", str(design_tmpdir), "--issue", required["--issue"]]
        if optional["--repo"]:
            pause_cmd.extend(["--repo", optional["--repo"]])
        pause = subprocess.run(pause_cmd, capture_output=True, text=True, check=False)
        pause_kv = _parse_stdout_kv(pause.stdout)
        warn_lines.extend(pause_kv.get("WARN", []))
        error_lines.extend(pause_kv.get("ERROR", []))
        if pause.returncode == 0 and pause_kv.get("LOAD_OK", ["false"])[-1] == "true" and pause_kv.get("STEP"):
            resume_step = pause_kv["STEP"][-1]
            session_id = pause_kv.get("SESSION_ID", [""])[-1]
            run_id = pause_kv.get("RUN_ID", [""])[-1]
            brainstorm_done = pause_kv.get("BRAINSTORM_DONE", [""])[-1]
            marker_cleared = pause_kv.get("MARKER_CLEARED", [""])[-1]
            route = f"resume@{resume_step}"
        else:
            route = "cancel-pause-load"
            if pause.returncode != 0:
                error_lines.append("design-pause-load-failed")
    else:
        title_cmd = [
            sys.executable,
            str(Path(__file__).with_name("cli.py")),
            "issue",
            "title-eligibility",
            f"--title={required['--issue-title']}",
        ]
        title = subprocess.run(title_cmd, capture_output=True, text=True, check=False)
        title_kv = _parse_stdout_kv(title.stdout)
        if title.returncode != 0:
            route = "cancel-title-filter"
            title_filter_reason = "error"
        elif title_kv.get("LIFECYCLE_REJECT", ["false"])[-1] == "true":
            route = "cancel-title-filter"
            title_filter_reason = "lifecycle"
            title_filter_marker = title_kv.get("LIFECYCLE_MARKER", [""])[-1]
        elif title_kv.get("ARCHIVAL_REPORT", ["false"])[-1] == "true":
            route = "cancel-title-filter"
            title_filter_reason = "archival"
        else:
            if title_kv.get("BRAINSTORM", ["false"])[-1] == "true":
                brainstorm_prefix = "true"
            has_clarify = required["--has-clarify-label"] == "true"
            has_plan = "<!-- larch:plan:start -->" in body and "<!-- larch:plan:end -->" in body
            if has_clarify:
                route = "clarify"
            elif has_plan:
                route = "already-planned"
            else:
                route = "proceed"

    if route.startswith("resume@") or route == "already-planned":
        _merge_router_flags(
            design_tmpdir / "run-params.json",
            warn_lines,
            merge_partition=optional["--partition-requested"] == "true",
            merge_brainstorm=optional["--brainstorm-requested"] == "true" or brainstorm_prefix == "true",
            merge_approve=optional["--approve-requested"] == "true",
            merge_skip_approve=optional["--skip-approve-requested"] == "true",
        )

    out: list[tuple[str, str]] = [("ROUTE", route), ("BRAINSTORM_PREFIX", brainstorm_prefix)]
    if title_filter_reason:
        out.append(("TITLE_FILTER_REASON", title_filter_reason))
    if title_filter_marker:
        out.append(("TITLE_FILTER_MARKER", title_filter_marker))
    if resume_step:
        out.append(("RESUME_STEP", resume_step))
    if session_id:
        out.append(("SESSION_ID", session_id))
    if run_id:
        out.append(("RUN_ID", run_id))
    if brainstorm_done:
        out.append(("BRAINSTORM_DONE", brainstorm_done))
    if marker_cleared:
        out.append(("MARKER_CLEARED", marker_cleared))
    out.extend(("WARN", item) for item in warn_lines)
    out.extend(("ERROR", item) for item in error_lines)
    _write_kv_file(result_env, out)  # pyright: ignore[reportUnusedCallResult]
    for key, value in out:
        print(f"{key}={value}")
    return 0


def init_runparams_main(argv: Sequence[str]) -> int:
    args = list(argv)
    parsed: dict[str, str] = {}
    i = 0
    while i < len(args):
        token = args[i]
        if token in {"--design-tmpdir", "--issue", "--session-id", "--claude-pid", "--partition-requested", "--brainstorm-requested", "--approve-requested", "--skip-approve-requested", "--repo"}:
            if i + 1 >= len(args):
                print(f"design-init-runparams.sh: {token} requires a value", file=sys.stderr)
                return 2
            parsed[token] = args[i + 1]
            i += 2
            continue
        if token == "--classification":
            i += 2
            continue
        if token in {"-h", "--help"}:
            return 0
        print(f"design-init-runparams.sh: unknown option: {token}", file=sys.stderr)
        return 2
    for needed in ("--design-tmpdir", "--issue", "--session-id", "--claude-pid", "--partition-requested", "--brainstorm-requested", "--approve-requested", "--skip-approve-requested"):
        if not parsed.get(needed):
            print("design-init-runparams.sh: missing required arguments", file=sys.stderr)
            return 2

    design_tmpdir = Path(parsed["--design-tmpdir"]).resolve()
    result_env = design_tmpdir / ".design-init-runparams-result.env"
    run_params_path = design_tmpdir / "run-params.json"
    init_status = "ok"
    renamed = "false"
    warn_lines: list[str] = []
    root = Path(__file__).resolve().parents[1]

    write_design = subprocess.run(
        [
            sys.executable,
            str(root / "python" / "cli.py"),
            "session",
            "write-design-env",
            "--output",
            str(design_tmpdir / "source-env.sh"),
            "--design-tmpdir",
            str(design_tmpdir),
            "--session-id",
            parsed["--session-id"],
            "--issue-number",
            parsed["--issue"],
            "--claude-pid",
            parsed["--claude-pid"],
            *(["--repo", parsed["--repo"]] if parsed.get("--repo") else []),
        ],
        check=False,
    )
    if write_design.returncode != 0:
        init_status = "env-refresh-failed"
        _write_kv_file(result_env, [("INIT_STATUS", init_status), ("RUN_PARAMS_PATH", str(run_params_path))])  # pyright: ignore[reportUnusedCallResult]
        print("INIT_STATUS=env-refresh-failed")
        return 1

    rename = subprocess.run(
        [
            sys.executable,
            str(root / "python" / "cli.py"),
            "tracking-issue",
            "rename",
            "--issue",
            parsed["--issue"],
            "--state",
            "designing",
            *(["--repo", parsed["--repo"]] if parsed.get("--repo") else []),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if rename.returncode == 0:
        for line in rename.stdout.splitlines():
            if line.startswith("RENAMED="):
                renamed = line.split("=", 1)[1]
    else:
        warn_lines.append(
            "**⚠ 0b: [DESIGNING] rename failed (python3 python/cli.py tracking-issue rename); continuing with run-params write. Re-invoke /design or rename manually if the title is still wrong.**"
        )

    write_params = subprocess.run(
        [
            sys.executable,
            str(root / "python" / "cli.py"),
            "session",
            "write-run-params",
            "--partition-requested",
            parsed["--partition-requested"],
            "--brainstorm-requested",
            parsed["--brainstorm-requested"],
            "--approve-requested",
            parsed["--approve-requested"],
            "--skip-approve-requested",
            parsed["--skip-approve-requested"],
            "--output",
            str(run_params_path),
        ],
        check=False,
    )
    if write_params.returncode != 0:
        init_status = "contract-drift"
        _write_kv_file(result_env, [("INIT_STATUS", init_status), ("RUN_PARAMS_PATH", str(run_params_path))])  # pyright: ignore[reportUnusedCallResult]
        print("INIT_STATUS=contract-drift")
        return 1

    _merge_router_flags(
        run_params_path,
        warn_lines,
        merge_partition=parsed["--partition-requested"] == "true",
        merge_brainstorm=parsed["--brainstorm-requested"] == "true",
        merge_approve=parsed["--approve-requested"] == "true",
        merge_skip_approve=parsed["--skip-approve-requested"] == "true",
    )
    result_rows: list[tuple[str, str]] = [("INIT_STATUS", init_status), ("RENAMED", renamed), ("RUN_PARAMS_PATH", str(run_params_path))]
    result_rows.extend(("WARN", w) for w in warn_lines)
    _write_kv_file(result_env, result_rows)  # pyright: ignore[reportUnusedCallResult]
    for key, value in result_rows:
        print(f"{key}={value}")
    return 0



COMMON_ENV_DEFAULTS: dict[str, str] = {
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
_TEMPLATE_PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}"
PARSE_VALIDATION_RC = 3
CONFIGURATION_ERROR_RC = 2


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


class WrapperArgs(argparse.Namespace):
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


def _parse_wrapper_args(argv: Sequence[str]) -> WrapperArgs:
    ns = WrapperArgs()
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
    if value == "":
        return "''"
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-")
    out = []
    for ch in value:
        if ch in safe:
            out.append(ch)
        elif ch == "\n":
            out.append("$'\\n'")
        else:
            out.append("\\" + ch)
    return "".join(out)


def write_bash_quoted_env(path: Path, data: Mapping[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={_bash_percent_q(data.get(key, ''))}\n" for key in PARSED_ENV_KEYS]
    path.write_text("".join(lines), encoding="utf-8")


def _decode_shell_assignment_value(value: str) -> str:
    if value == "":
        return ""
    try:
        parts = shlex.split("v=" + value, posix=True)
    except ValueError:
        return value
    if not parts:
        return ""
    first = parts[0]
    return first.split("=", 1)[1] if "=" in first else ""


def load_bash_quoted_env(path: Path, allow_keys: Iterable[str]) -> dict[str, str]:
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


def _load_source_env(path: str | Path, allow_keys: Iterable[str] = SOURCE_ENV_ALLOW) -> dict[str, str]:
    source = Path(path)
    if not str(path) or not source.is_file() or source.is_symlink():
        return {}
    allow = set(allow_keys)
    data: dict[str, str] = {}
    for raw in source.read_text(encoding="utf-8", errors="replace").splitlines():
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


def _load_wrapper_env(ns: WrapperArgs) -> dict[str, str]:
    data = _base_env()
    data.update(_load_source_env(ns.session_env_path))
    if ns.plugin_root:
        data["CLAUDE_PLUGIN_ROOT"] = ns.plugin_root
    if ns.outcome:
        data["SUMMARY_OUTCOME"] = ns.outcome
    return data


def _parsed_cache_path(claude_pid: str) -> Path:
    return Path.home() / ".cache" / "larch" / "sessions" / f"step0-parsed-{claude_pid}.env"


def _run_parse_argv(public_argv: Sequence[str], plugin_root: Path) -> tuple[int, dict[str, str], str]:
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
        data = load_bash_quoted_env(out_path, [*PARSED_ENV_KEYS, "VALIDATION_ERROR"])
        return proc.returncode, data, proc.stderr
    finally:
        with contextlib.suppress(FileNotFoundError):
            out_path.unlink()


def _validate_parse_result(rc: int, data: dict[str, str], stderr_text: str) -> None:
    if "PUBLIC_ARGV_WORDS" in stderr_text or "PUBLIC_ARGV_WORDS" in data.get("POSITIONAL_VALUE", ""):
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


def _parse_and_persist(ns: WrapperArgs, plugin_root: Path) -> tuple[Path, dict[str, str]]:
    rc, data, stderr_text = _run_parse_argv(ns.public_argv, plugin_root)
    _validate_parse_result(rc, data, stderr_text)
    for key in PARSED_ENV_KEYS:
        data.setdefault(key, "false" if key.endswith("_requested") or key == "no_dedup_requested" else "")
    if not data.get("POSITIONAL_KIND"):
        data["POSITIONAL_KIND"] = "none"
    cache = _parsed_cache_path(ns.claude_pid)
    write_bash_quoted_env(cache, data)
    return cache, data


def _emit_parse_kvs(cache: Path, data: Mapping[str, str]) -> None:
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
    cache, data = _parse_and_persist(ns, plugin_root)
    _emit_parse_kvs(cache, data)
    return 0


def _derive_binary_found(env: dict[str, str]) -> None:
    if not env.get("CODEX_BINARY_FOUND"):
        env["CODEX_BINARY_FOUND"] = "true" if shutil.which("codex") else "false"
    if not env.get("CURSOR_BINARY_FOUND"):
        env["CURSOR_BINARY_FOUND"] = "true" if shutil.which("cursor") else "false"


def _cli_cmd(plugin_root: Path, *args: str) -> list[str]:
    return [sys.executable, str(plugin_root / "python" / "cli.py"), *args]


def _run_best_effort(command: Sequence[str], *, env: Mapping[str, str] | None = None) -> None:
    with contextlib.suppress(OSError):
        subprocess.run(list(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=dict(env) if env is not None else None, check=False)


def _pause_args(env: Mapping[str, str], design_tmpdir: str | Path) -> list[str]:
    args = ["design", "pause-save", "--design-tmpdir", str(design_tmpdir), "--issue", env.get("ISSUE_NUMBER", "")]
    if env.get("REPO"):
        args.extend(["--repo", env["REPO"]])
    return args


def check_pause_and_exit(env: Mapping[str, str], design_tmpdir: str | Path | None = None) -> None:
    tmpdir = Path(str(design_tmpdir or env.get("DESIGN_TMPDIR", "")))
    if str(tmpdir) and (tmpdir / ".pause-requested").is_file():
        rc = design_pause.pause_save_main(_pause_args(env, tmpdir))
        raise SystemExit(rc)


def relay_degraded_tools_gate_stdout(stdout: str, design_tmpdir: Path) -> dict[str, str]:
    state = {
        "DEGRADED": "false",
        "BOTH_DOWN": "false",
        "BOTH_DOWN_SEEN": "false",
        "DEGRADED_HARD_FAIL": "false",
        "PRESENCE_INPUT_EMPTY": "false",
    }
    in_explanation = False
    for line in stdout.splitlines():
        if line == "DEGRADED_EXPLANATION_BEGIN":
            in_explanation = True
            print(line)
        elif line == "DEGRADED_EXPLANATION_END":
            in_explanation = False
            print(line)
        elif line.startswith("DEGRADED="):
            state["DEGRADED"] = line.split("=", 1)[1]
            print(line)
        elif line.startswith("BOTH_DOWN="):
            state["BOTH_DOWN"] = line.split("=", 1)[1]
            state["BOTH_DOWN_SEEN"] = "true"
            print(line)
        elif line.startswith("DEGRADED_HARD_FAIL="):
            state["DEGRADED_HARD_FAIL"] = line.split("=", 1)[1]
            print(line)
        elif line.startswith("PRESENCE_INPUT_EMPTY="):
            state["PRESENCE_INPUT_EMPTY"] = line.split("=", 1)[1]
            print(line)
        elif line.startswith(("CODEX_STATE=", "CURSOR_STATE=")) or in_explanation:
            print(line)
    if state["PRESENCE_INPUT_EMPTY"] == "true":
        with contextlib.suppress(OSError):
            with (design_tmpdir / "execution-issues.md").open("a", encoding="utf-8") as handle:
                handle.write("- Step 0 degraded-tools gate: PRESENCE_INPUT_EMPTY=true (caller rehydration warning)\n")
    step0_status = "ok"
    if state["DEGRADED"] == "true":
        if state["BOTH_DOWN_SEEN"] == "true" and state["BOTH_DOWN"] == "true":
            step0_status = "degraded-both-down-hard-fail"
        elif state["BOTH_DOWN_SEEN"] == "true" and state["BOTH_DOWN"] == "false" and (design_tmpdir / ".degraded-tools-gate-prompted").is_file():
            step0_status = "degraded-one-down"
        else:
            step0_status = "needs-degraded-decision"
    state["STEP0_STATUS"] = step0_status
    return state


def step0_session_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    plugin_root = require_plugin_root(ns.plugin_root)
    cache, parsed = _parse_and_persist(ns, plugin_root)
    _emit_parse_kvs(cache, parsed)
    _run_best_effort(_cli_cmd(plugin_root, "timing", "mark", "design Step 0 — session setup"), env={**os.environ, "LARCH_TIMING_SKILL": "design"})
    setup = subprocess.run(
        _cli_cmd(plugin_root, "session", "setup", "--prefix", "claude-design", "--skip-branch-check", "--skip-repo-check", "--check-reviewers"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if setup.stdout:
        print(setup.stdout, end="" if setup.stdout.endswith("\n") else "\n")
    if setup.returncode != 0:
        return setup.returncode
    kv = _parse_stdout_kv(setup.stdout)
    design_tmpdir = kv.get("SESSION_TMPDIR", [""])[-1]
    session_id = kv.get("SESSION_ID", [""])[-1]
    if not design_tmpdir or not session_id:
        print("**⚠ /design: session setup output missing SESSION_TMPDIR or SESSION_ID**", file=sys.stderr)
        return 1
    design_path = Path(design_tmpdir)
    (design_path / ".design-step0-parsed.env").write_bytes(cache.read_bytes())
    env = {**os.environ, "DESIGN_TMPDIR": design_tmpdir, "IMPLEMENT_TMPDIR": os.environ.get("IMPLEMENT_TMPDIR", "")}
    _run_best_effort(_cli_cmd(plugin_root, "token", "mark", "design Step 0 — session setup"), env=env)
    codex_binary = kv.get("CODEX_BINARY_FOUND", [""])[-1]
    cursor_binary = kv.get("CURSOR_BINARY_FOUND", [""])[-1]
    wdce = _cli_cmd(plugin_root, "session", "write-design-env", "--output", str(design_path / "source-env.sh"), "--design-tmpdir", design_tmpdir, "--session-id", session_id, "--claude-pid", ns.claude_pid)
    if codex_binary:
        wdce.extend(["--codex-binary-found", codex_binary])
    if cursor_binary:
        wdce.extend(["--cursor-binary-found", cursor_binary])
    rc = subprocess.run(wdce, check=False).returncode
    if rc != 0:
        return rc
    gate = subprocess.run(
        _cli_cmd(
            plugin_root,
            "agent",
            "degraded-tools-gate",
            "--skill",
            "design",
            "--codex-present",
            kv.get("CODEX_PRESENT", ["false"])[-1] or "false",
            "--cursor-present",
            kv.get("CURSOR_PRESENT", ["false"])[-1] or "false",
            "--codex-binary-found",
            codex_binary or "false",
            "--cursor-binary-found",
            cursor_binary or "false",
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    state = relay_degraded_tools_gate_stdout(gate.stdout, design_path)
    print(f"STEP0_STATUS={state['STEP0_STATUS']}")
    print(f"DEGRADED={state['DEGRADED']}")
    print(f"BOTH_DOWN={state['BOTH_DOWN']}")
    if state["STEP0_STATUS"] == "degraded-both-down-hard-fail":
        print("DEGRADED_HARD_FAIL=true")
    if state["STEP0_STATUS"] == "needs-degraded-decision":
        print("DEGRADED_PROMPT_REQUIRED=true")
    return gate.returncode


def resolve_repo() -> str:
    gh = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], capture_output=True, text=True, check=False)  # noqa: S607
    if gh.returncode == 0 and gh.stdout.strip():
        return gh.stdout.strip()
    origin = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=False)  # noqa: S607
    url = origin.stdout.strip()
    if not url:
        return ""
    url = url.removesuffix(".git")
    if ":" in url and not url.startswith("http"):
        tail = url.split(":", 1)[1]
    else:
        tail = url.rstrip("/").split("github.com/", 1)[-1]
    return tail if re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", tail) else ""


def _read_json_issue(issue_number: str, repo: str) -> tuple[str, str, str]:
    command = ["gh", "issue", "view", issue_number]
    if repo:
        command.extend(["--repo", repo])
    command.extend(["--json", "body,labels,number,title"])
    last = subprocess.CompletedProcess(command, 1, "", "")
    for attempt in range(2):
        last = subprocess.run(command, capture_output=True, text=True, check=False)
        if last.returncode == 0:
            break
        if attempt == 0:
            time.sleep(1)
    if last.returncode != 0:
        raise RuntimeError("gh issue view failed")
    raw = json.loads(last.stdout or "{}")
    labels = raw.get("labels", [])
    has_clarify = any(isinstance(label, dict) and label.get("name") == "needs-design-clarification" for label in labels)
    return str(raw.get("title") or ""), str(raw.get("body") or ""), "true" if has_clarify else "false"


def _read_result_pairs(primary: Path, fallback: Path | None, allow: Iterable[str]) -> dict[str, str]:
    try:
        pairs = phase_driver_read_result_env(primary, allow)
    except OSError:
        pairs = []
    if not pairs and fallback is not None and fallback.is_file() and not fallback.is_symlink():
        pairs = phase_driver_read_result_env(fallback, allow)
    return dict(pairs)


def step0_route_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    design_tmpdir = Path(env.get("DESIGN_TMPDIR", ""))
    check_pause_and_exit(env, design_tmpdir)
    parsed = load_bash_quoted_env(design_tmpdir / ".design-step0-parsed.env", PARSED_ENV_KEYS)
    env.update(parsed)
    if ns.issue_number:
        if re.match(r"^[0-9]+$", ns.issue_number):
            env["ISSUE_NUMBER"] = ns.issue_number
        else:
            print("**⚠ Step 0b: --issue-number requires numeric value; aborting /design**", file=sys.stderr)
            return 1
    kind = env.get("POSITIONAL_KIND", "none") or "none"
    if kind == "issue":
        if re.match(r"^[0-9]+$", env.get("POSITIONAL_VALUE", "")):
            env["ISSUE_NUMBER"] = env["POSITIONAL_VALUE"]
        else:
            print("**⚠ Step 0b: POSITIONAL_KIND=issue requires numeric POSITIONAL_VALUE; aborting /design**", file=sys.stderr)
            return 1
    elif kind == "verbal":
        if not env.get("ISSUE_NUMBER"):
            print("**⚠ Step 0b: POSITIONAL_KIND=verbal requires ISSUE_NUMBER from /larch:issue before routing; aborting /design**", file=sys.stderr)
            return 1
    elif kind != "none":
        print(f"**⚠ Step 0b: invalid POSITIONAL_KIND={kind or '<empty>'}; aborting /design**", file=sys.stderr)
        return 1
    if env.get("ISSUE_NUMBER"):
        if not env.get("REPO"):
            env["REPO"] = resolve_repo()
        try:
            title, body, has_clarify = _read_json_issue(env["ISSUE_NUMBER"], env.get("REPO", ""))
        except (RuntimeError, json.JSONDecodeError):
            print(f"**⚠ Step 0b: gh issue view failed for issue {env['ISSUE_NUMBER']}; aborting /design**", file=sys.stderr)
            return 1
        env["ISSUE_TITLE"] = title
        env["HAS_CLARIFY_LABEL"] = has_clarify
        (design_tmpdir / "issue-body.txt").write_text(body, encoding="utf-8")
    with tempfile.NamedTemporaryFile(prefix="larch-route-stdout.", delete=False, mode="w+", encoding="utf-8") as capture:
        capture_path = Path(capture.name)
    try:
        route_cmd = _cli_cmd(
            plugin_root,
            "design",
            "route",
            "--design-tmpdir",
            str(design_tmpdir),
            "--issue",
            env.get("ISSUE_NUMBER", ""),
            "--issue-title",
            env.get("ISSUE_TITLE", ""),
            "--issue-body-file",
            str(design_tmpdir / "issue-body.txt"),
            "--has-clarify-label",
            env.get("HAS_CLARIFY_LABEL", "false"),
            "--claude-pid",
            ns.claude_pid,
            "--session-id",
            env.get("SESSION_ID", ""),
            "--partition-requested",
            env.get("partition_requested", "false"),
            "--brainstorm-requested",
            env.get("brainstorm_requested", "false"),
            "--approve-requested",
            env.get("approve_requested", "false"),
            "--skip-approve-requested",
            env.get("skip_approve_requested", "false"),
        )
        if env.get("REPO"):
            route_cmd.extend(["--repo", env["REPO"]])
        proc = subprocess.run(route_cmd, capture_output=True, text=True, check=False)
        capture_path.write_text(proc.stdout, encoding="utf-8")
        if proc.returncode == CONFIGURATION_ERROR_RC:
            print("**⚠ Step 0b: design-route.sh configuration error (exit 2); aborting /design**", file=sys.stderr)
            return 1
        if proc.returncode != 0:
            print(f"**⚠ Step 0b: design-route.sh failed (exit {proc.returncode}); aborting /design**", file=sys.stderr)
            return 1
        route_env = _read_result_pairs(design_tmpdir / ".design-route-result.env", capture_path, ROUTE_RESULT_KEYS)
    finally:
        with contextlib.suppress(FileNotFoundError):
            capture_path.unlink()
    if not route_env:
        print("**⚠ Step 0b: could not read design-route result env; aborting /design**", file=sys.stderr)
        return 1
    route = route_env.get("ROUTE", "")
    if route_env.get("BRAINSTORM_PREFIX") == "true":
        env["brainstorm_requested"] = "true"
        print("**ℹ /design: detected Brainstorm title prefix — auto-enabling brainstorm mode (run-params `brainstorm_requested=true`) even though --brainstorm was not on argv.**")  # noqa: RUF001
    if route == "cancel-pause-load":
        print("**⚠ /design: pause resume state could not be loaded safely; aborting before fresh routing. Inspect pause-load ERROR breadcrumbs above, fix the pause block, then re-invoke /design.**", file=sys.stderr)
        return 1
    resume_step = ""
    if route.startswith("resume@"):
        resume_step = route.removeprefix("resume@")
        if route_env.get("MARKER_CLEARED"):
            print(f"MARKER_CLEARED={route_env['MARKER_CLEARED']}")
        print(f"🔓 resumed from STEP={resume_step}")
    valid = route in {"proceed", "clarify", "already-planned", "cancel-title-filter", "cancel-reentry-guard", "cancel-pause-load"} or (route.startswith("resume@") and bool(route.removeprefix("resume@")))
    if not valid:
        print("**⚠ Step 0b: missing or invalid ROUTE after design-route.sh; aborting /design**", file=sys.stderr)
        return 1
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
    rows = [
        ("ROUTE", route),
        *([("RESUME_STEP", resume_step)] if resume_step else []),
        ("HAS_CLARIFY_LABEL", env.get("HAS_CLARIFY_LABEL", "false")),
        ("ISSUE_NUMBER", env.get("ISSUE_NUMBER", "")),
        ("ISSUE_TITLE", env.get("ISSUE_TITLE", "")),
    ]
    if env.get("REPO"):
        rows.append(("REPO", env["REPO"]))
    if env.get("brainstorm_requested"):
        rows.append(("brainstorm_requested", env["brainstorm_requested"]))
    _write_kv_file(design_tmpdir / ".design-step0-route-state.env", rows)
    return 0


def _load_route_result_route(design_tmpdir: Path) -> str:
    result = _read_result_pairs(design_tmpdir / ".design-route-result.env", None, ["ROUTE"])
    return result.get("ROUTE", "")


def step0_init_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    design_tmpdir = Path(env.get("DESIGN_TMPDIR", ""))
    check_pause_and_exit(env, design_tmpdir)
    env.update(load_bash_quoted_env(design_tmpdir / ".design-step0-parsed.env", PARSED_ENV_KEYS))
    env.update(load_bash_quoted_env(design_tmpdir / ".design-step0-route-state.env", ROUTE_STATE_KEYS))
    init_route = _load_route_result_route(design_tmpdir)
    if init_route in {"proceed", "already-planned"}:
        issue_body = design_tmpdir / "issue-body.txt"
        if issue_body.is_file():
            prefix = f"# {env.get('ISSUE_TITLE', '')}\n\n" if env.get("ISSUE_TITLE") else ""
            (design_tmpdir / "feature-description.txt").write_text(prefix + issue_body.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        elif env.get("POSITIONAL_KIND") == "verbal" and env.get("POSITIONAL_VALUE"):
            (design_tmpdir / "feature-description.txt").write_text(env["POSITIONAL_VALUE"] + "\n", encoding="utf-8")
    with tempfile.NamedTemporaryFile(prefix="larch-init-stdout.", delete=False, mode="w+", encoding="utf-8") as capture:
        capture_path = Path(capture.name)
    try:
        cmd = _cli_cmd(
            plugin_root,
            "design",
            "init-runparams",
            "--design-tmpdir",
            str(design_tmpdir),
            "--issue",
            env.get("ISSUE_NUMBER", ""),
            "--session-id",
            env.get("SESSION_ID", ""),
            "--claude-pid",
            ns.claude_pid,
            "--partition-requested",
            env.get("partition_requested", "false"),
            "--brainstorm-requested",
            env.get("brainstorm_requested", "false"),
            "--approve-requested",
            env.get("approve_requested", "false"),
            "--skip-approve-requested",
            env.get("skip_approve_requested", "false"),
        )
        if env.get("REPO"):
            cmd.extend(["--repo", env["REPO"]])
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        capture_path.write_text(proc.stdout, encoding="utf-8")
        if proc.returncode == CONFIGURATION_ERROR_RC:
            print("**⚠ Step 0b: design-init-runparams.sh configuration error (exit 2); aborting /design**", file=sys.stderr)
            return 1
        if proc.returncode not in {0, 1}:
            print(f"**⚠ Step 0b: design-init-runparams.sh failed (exit {proc.returncode}); aborting /design**", file=sys.stderr)
            return 1
        result = _read_result_pairs(design_tmpdir / ".design-init-runparams-result.env", capture_path, INIT_RESULT_KEYS)
    finally:
        with contextlib.suppress(FileNotFoundError):
            capture_path.unlink()
    if not result:
        print("**⚠ Step 0b: read-result-env.sh failed for design-init-runparams result (exit 1); aborting /design**", file=sys.stderr)
        return 1
    init_status = result.get("INIT_STATUS", "")
    if proc.returncode == 0 and (init_status != "ok" or not (design_tmpdir / "run-params.json").is_file()):
        print("**⚠ Step 0b: design-init-runparams.sh exited 0 without INIT_STATUS=ok and run-params.json; aborting /design**", file=sys.stderr)
        return 1
    if proc.returncode == 1:
        print(f"**⚠ Step 0b: design-init-runparams.sh failed (INIT_STATUS={init_status or 'unknown'}); aborting /design**", file=sys.stderr)
        return 1
    return 0


def _append_failure(plugin_root: Path, design_tmpdir: Path, site: str, tool: str, exit_code: int | str, category: str, output_file: Path) -> bool:
    result = subprocess.run(
        _cli_cmd(plugin_root, "run-log", "append-failure", "--log", str(design_tmpdir / "execution-issues.md"), "--site", site, "--tool", tool, "--exit-code", str(exit_code), "--category", category, "--output-file", str(output_file), "--redact"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def step0_clarify_hard_halt_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    if not env.get("DESIGN_TMPDIR"):
        print("/design Step 0b clarify hard halt: DESIGN_TMPDIR required", file=sys.stderr)
        return 1
    design_tmpdir = Path(env["DESIGN_TMPDIR"]).resolve()
    check_pause_and_exit(env, design_tmpdir)
    detail = Path(ns.failure_detail_log or env.get("CLARIFY_FAILURE_LOG") or design_tmpdir / "clarify-loop.failure.log")
    try:
        resolved_detail = detail.resolve(strict=False)
        if design_tmpdir not in resolved_detail.parents and resolved_detail != design_tmpdir:
            detail = design_tmpdir / "clarify-loop.failure.log"
    except OSError:
        detail = design_tmpdir / "clarify-loop.failure.log"
    if not detail.is_file():
        detail.write_text("clarify loop hard halt\n", encoding="utf-8")
    stdout_log = design_tmpdir / "design-stage-terminal-state.stdout.log"
    stderr_log = design_tmpdir / "design-stage-terminal-state.stderr.log"
    helper = plugin_root / "skills" / "design" / "scripts" / "design-stage-terminal-state.sh"
    with stdout_log.open("w", encoding="utf-8") as out, stderr_log.open("w", encoding="utf-8") as err:
        stage = subprocess.run(
            [str(helper), "--design-tmpdir", str(design_tmpdir), "--outcome", "failed-clarify", "--step", "clarify", "--phase", "clarify-loop", "--site", "clarify-loop", "--trigger", "failed", "--bail-reason", "clarify-hard-halt", "--exit-code", ns.exit_code or "1", "--source-script", "clarify-loop", "--summary-outcome", "failed-clarify", "--failure-detail-log", str(detail)],
            stdout=out,
            stderr=err,
            check=False,
        )
    stdout_text = stdout_log.read_text(encoding="utf-8", errors="replace") if stdout_log.is_file() else ""
    if "STAGED=false" in stdout_text.splitlines():
        _append_failure(plugin_root, design_tmpdir, "design Step 0b clarify hard halt", "design-stage-terminal-state.sh", 0, "Warnings", stdout_log)
    elif stage.returncode != 0:
        _append_failure(plugin_root, design_tmpdir, "design Step 0b clarify hard halt", "design-stage-terminal-state.sh", stage.returncode, "Warnings", stderr_log)
    os.environ["SUMMARY_OUTCOME"] = "failed-clarify"
    return 0


def step0_abort_cleanup_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    if not env.get("DESIGN_TMPDIR"):
        print("/design Step 0 abort-cleanup: DESIGN_TMPDIR required", file=sys.stderr)
        return 1
    design_tmpdir = Path(env["DESIGN_TMPDIR"])
    print("**⚠ /design: aborted by operator — external tool unhealthy; re-run once it recovers.**")
    _append_failure(plugin_root, design_tmpdir, "design Step 0", "degraded-tools-gate", 0, "Warnings", design_tmpdir / "execution-issues.md")
    return subprocess.run(_cli_cmd(plugin_root, "session", "cleanup-tmpdir", "--dir", str(design_tmpdir)), check=False).returncode


def step0_ap_continue_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    completed = Path(env.get("DESIGN_TMPDIR", "")) / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    for name in ("step-1c", "step-1d", "step-1d.5"):
        (completed / name).write_text("", encoding="utf-8")
    check_pause_and_exit(env)
    return 0


def step0c_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    _derive_binary_found(env)
    check_pause_and_exit(env)
    design_tmpdir = Path(env.get("DESIGN_TMPDIR", ""))
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-0c").write_text("", encoding="utf-8")
    _run_best_effort(_cli_cmd(plugin_root, "timing", "mark", "design folded discussion block"), env={**os.environ, "LARCH_TIMING_SKILL": "design"})
    return 0


def brainstorm_stderr_sink_for_output(output_path: Path, design_tmpdir: Path) -> Path | None:
    meta = output_path.with_name(output_path.name + ".meta")
    if meta.is_file():
        for line in meta.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("STDERR_SINK=") and line.split("=", 1)[1]:
                return Path(line.split("=", 1)[1])
    if output_path.name == "cursor-brainstorm-output.txt":
        return design_tmpdir / "cursor-brainstorm-launch.failure.log"
    if output_path.name == "codex-brainstorm-output.txt":
        return design_tmpdir / "codex-brainstorm-launch.failure.log"
    return None


def _launch_tool_for_sink(sink: Path) -> str:
    name = sink.name
    return name.removesuffix(".failure.log") if name.endswith(".failure.log") else name


def brainstorm_collect_launch_failure_once(plugin_root: Path, design_tmpdir: Path, log_path: Path, tool: str) -> None:
    if not log_path.is_file() or log_path.stat().st_size == 0:
        return
    sentinel = design_tmpdir / f".brainstorm-{log_path.name}.runlog-appended"
    if sentinel.exists():
        return
    exit_code = "1"
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("LAUNCHER_EXIT=") and line.split("=", 1)[1].isdigit():
            exit_code = line.split("=", 1)[1]
            break
    if _append_failure(plugin_root, design_tmpdir, "design Step 1d.5", tool, exit_code, "External Reviewer Issues", log_path):
        sentinel.write_text("", encoding="utf-8")


def _brainstorm_dirty_checkpoint(plugin_root: Path, design_tmpdir: Path, paths: Sequence[Path]) -> None:
    recovery = False
    reason = ""
    for path in paths:
        sidecar = path.with_name(path.name + ".dirty-tree")
        if sidecar.is_file():
            side = _parse_stdout_kv(sidecar.read_text(encoding="utf-8", errors="replace")).get("STATUS", ["unknown"])[-1] or "unknown"
            if side in {"dirty", "unknown"}:
                recovery = True
                reason = side
    stdout_path = design_tmpdir / "brainstorm-dirty-tree.checkpoint.out"
    stderr_path = design_tmpdir / "brainstorm-dirty-tree.checkpoint.err"
    proc = subprocess.run(_cli_cmd(plugin_root, "dirty-tree", "checkpoint"), capture_output=True, text=True, check=False)
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    status = _parse_stdout_kv(proc.stdout).get("STATUS", [""])[-1]
    if proc.returncode != 0 and not status:
        status = "unknown"
    if status in {"dirty", "unknown"}:
        recovery = True
        reason = reason or status
    if recovery:
        text = f"STAGE=brainstorm-collection\nRECOVERY_REQUIRED=true\nDIRTY_TREE_STATUS={reason or 'unknown'}\n"
        if stdout_path.stat().st_size:
            text += stdout_path.read_text(encoding="utf-8", errors="replace")
        (design_tmpdir / "dirty-tree-detected.env").write_text(text, encoding="utf-8")
        print(f"WARN=brainstorm-collection dirty-tree recovery required (status={reason or 'unknown'})")
    else:
        (design_tmpdir / "dirty-tree-detected.env").write_text("STAGE=brainstorm-collection\nRECOVERY_REQUIRED=false\n", encoding="utf-8")


def step1d5_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    design_tmpdir = Path(env.get("DESIGN_TMPDIR", ""))
    if ns.mode == "entry":
        completed = design_tmpdir / ".completed"
        completed.mkdir(parents=True, exist_ok=True)
        for name in ("step-1c", "step-1d"):
            (completed / name).write_text("", encoding="utf-8")
        check_pause_and_exit(env)
        _run_best_effort(_cli_cmd(plugin_root, "timing", "mark", "design Step 1d.5 — brainstorm"), env={**os.environ, "LARCH_TIMING_SKILL": "design"})
        return 0
    if ns.mode == "collect":
        check_pause_and_exit(env)
        if not ns.public_argv:
            print("design-step1d5.sh: --mode collect requires at least one output path after --", file=sys.stderr)
            return 2
        paths = [Path(item) for item in ns.public_argv]
        collect = subprocess.run(_cli_cmd(plugin_root, "agent", "collect-results", "--timeout", "1260", *[str(p) for p in paths]), capture_output=True, text=True, check=False)
        (design_tmpdir / "brainstorm-collect.stdout.log").write_text(collect.stdout, encoding="utf-8")
        (design_tmpdir / "brainstorm-collect.stderr.log").write_text(collect.stderr, encoding="utf-8")
        if collect.stdout:
            print(collect.stdout, end="" if collect.stdout.endswith("\n") else "\n")
        if collect.returncode != 0:
            failure = design_tmpdir / "brainstorm-collect.failure.log"
            failure.write_text(collect.stdout + collect.stderr, encoding="utf-8")
            _append_failure(plugin_root, design_tmpdir, "design Step 1d.5", "agent collect-results", collect.returncode, "External Reviewer Issues", failure)
        for path in paths:
            sink = brainstorm_stderr_sink_for_output(path, design_tmpdir)
            if sink is not None:
                brainstorm_collect_launch_failure_once(plugin_root, design_tmpdir, sink, _launch_tool_for_sink(sink))
        _brainstorm_dirty_checkpoint(plugin_root, design_tmpdir, paths)
        return 0
    if ns.mode == "complete":
        completed = design_tmpdir / ".completed"
        completed.mkdir(parents=True, exist_ok=True)
        (completed / "step-1d.5").write_text("", encoding="utf-8")
        check_pause_and_exit(env)
        return 0
    print("design-step1d5.sh: --mode required", file=sys.stderr)
    return 2


def step1d7_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    _derive_binary_found(env)
    check_pause_and_exit(env)
    skip = False
    try:
        data = json.loads((Path(env.get("DESIGN_TMPDIR", "")) / "run-params.json").read_text(encoding="utf-8"))
        skip = bool(data.get("skip_approve_requested")) if isinstance(data, dict) else False
    except (OSError, json.JSONDecodeError):
        skip = False
    print(f"SKIP_APPROVE_REQUESTED={'true' if skip else 'false'}")
    return 0


def step1e_reentry_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    design_tmpdir = Path(env.get("DESIGN_TMPDIR", ""))
    for name in ("step-1e", "step-2a", "step-2a.5", "step-2b", "step-2b.5", "step-3", "step-3.5", "step-3b", "step-4", "step-4b"):
        with contextlib.suppress(FileNotFoundError):
            (design_tmpdir / ".completed" / name).unlink()
    for path in design_tmpdir.glob(".gate-b-postapply-ready-*"):
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
    check_pause_and_exit(env)
    return 0

def driver_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    _ = parser.add_argument("--design-tmpdir")
    _ = parser.add_argument("--action-file")
    _ = parser.add_argument("--resume-from", default="")
    try:
        ns, extra = parser.parse_known_args(list(argv))
    except SystemExit:
        return 2
    if extra or not ns.design_tmpdir:
        return 2
    design_tmpdir = Path(ns.design_tmpdir).resolve()
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    consumer_repo_root = subprocess.run(["git", "-C", str(Path.cwd()), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False).stdout.strip() or str(root)  # noqa: S607

    action_lines: list[str]
    if ns.action_file:
        action_lines = Path(ns.action_file).read_text(encoding="utf-8", errors="replace").splitlines()
    else:
        action_lines = sys.stdin.read().splitlines()

    resume_seen = not ns.resume_from
    resume_norm = _normalize_step(ns.resume_from)

    for line in action_lines:
        if not line:
            continue
        if not line.startswith("ACTION="):
            print(f"ACTION_PASSTHROUGH={line}")
            continue
        action = line[len("ACTION="):].split(" ", 1)[0]
        if action == "CLASSIFY":
            print("STEP_FAILED=CLASSIFY REASON=deprecated-action")
            return 2
        if action not in {"EMIT_PLAN", "TALLY", "FINALIZE", "VALIDATE_PLAN_COMMANDS"}:
            print(f"ACTION_PASSTHROUGH={line}")
            continue
        sentinel = completed / _normalize_step(action)
        no_sentinel = action in {"EMIT_PLAN", "VALIDATE_PLAN_COMMANDS"}
        if not resume_seen:
            if action == ns.resume_from or _normalize_step(action) == resume_norm:
                resume_seen = True
            elif sentinel.exists() and not no_sentinel:
                print(f"STEP_SKIPPED={action} REASON=completed-before-resume")
                continue
            else:
                print(f"STEP_SKIPPED={action} REASON=before-resume")
                continue
        elif sentinel.exists() and not no_sentinel:
            print(f"STEP_SKIPPED={action} REASON=already-completed")
            continue
        args_text = _extract_args(line)
        action_args: list[str] = []
        if args_text:
            try:
                action_args = shlex.split(args_text)
            except ValueError:
                print(f"STEP_FAILED={action} REASON=bad-args")
                return 2
        print(f"STEP_STARTED={action}")
        command: list[str]
        if action == "EMIT_PLAN":
            command = [sys.executable, str(root / "python" / "cli.py"), "plan-review", "emit", "--design-tmpdir", str(design_tmpdir), *action_args]
        elif action == "TALLY":
            command = [sys.executable, str(root / "python" / "cli.py"), "plan-review", "tally", "--design-tmpdir", str(design_tmpdir), *action_args]
        elif action == "FINALIZE":
            command = [sys.executable, str(root / "python" / "cli.py"), "plan-review", "finalize", "--design-tmpdir", str(design_tmpdir), *action_args]
        else:
            env = os.environ.copy()
            env["DESIGN_TMPDIR"] = str(design_tmpdir)
            command = [sys.executable, str(root / "python" / "cli.py"), "plan", "validate", "--design-tmpdir", str(design_tmpdir), "--repo-root", consumer_repo_root, *action_args]
            proc_out = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
            if proc_out.stdout:
                print(proc_out.stdout, end="")
            if proc_out.returncode != 0:
                print(f"STEP_FAILED={action} REASON=exit-{proc_out.returncode}")
                return int(proc_out.returncode)
            if not no_sentinel:
                _ = sentinel.write_text("", encoding="utf-8")
            print(f"STEP_COMPLETED={action}")
            continue
        proc_out = subprocess.run(command, capture_output=True, text=True, check=False)
        if proc_out.stdout:
            print(proc_out.stdout, end="")
        if proc_out.returncode != 0:
            print(f"STEP_FAILED={action} REASON=exit-{proc_out.returncode}")
            return int(proc_out.returncode)
        if not no_sentinel:
            _ = sentinel.write_text("", encoding="utf-8")
        print(f"STEP_COMPLETED={action}")
    return 0


def _write_kv_file(path: Path, rows: list[tuple[str, str]]) -> bool:
    try:
        with path.open("w", encoding="utf-8") as handle:
            for key, value in rows:
                handle.write(f"{key}={value}\n")  # pyright: ignore[reportUnusedCallResult]
    except OSError:
        return False
    return True


def _parse_stdout_kv(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out.setdefault(key, []).append(value)
    return out


def _merge_router_flags(
    run_params: Path,
    warn_lines: list[str],
    *,
    merge_partition: bool,
    merge_brainstorm: bool,
    merge_approve: bool,
    merge_skip_approve: bool,
) -> None:
    if not (merge_partition or merge_brainstorm or merge_approve or merge_skip_approve):
        return
    if not run_params.is_file() or run_params.is_symlink():
        warn_lines.append(
            "**⚠ 0b: cannot merge current router flags into run-params.json on resumed/already-planned flow; file missing or unsafe. Re-run from Step 0b after repairing run params.**"
        )
        return
    try:
        _raw = json.loads(run_params.read_text(encoding="utf-8"))
        if not isinstance(_raw, dict):
            return
        data: dict[str, object] = _raw  # type: ignore[assignment]
        data["partition_requested"] = bool(data.get("partition_requested")) or merge_partition
        data["brainstorm_requested"] = bool(data.get("brainstorm_requested")) or merge_brainstorm
        data["approve_requested"] = bool(data.get("approve_requested")) or merge_approve
        data["skip_approve_requested"] = bool(data.get("skip_approve_requested")) or merge_skip_approve
        _ = run_params.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        warn_lines.append("**⚠ 0b: jq unavailable or run-params parse failed; current router flags may not persist into resumed/already-planned flow.**")


def _normalize_step(value: str) -> str:
    lowered = value.lower()
    return "".join(ch if (ch.isalnum() or ch in "._-") else "-" for ch in lowered)


def _extract_args(line: str) -> str:
    marker = " ARGS="
    if marker not in line:
        return ""
    return line.split(marker, 1)[1]
