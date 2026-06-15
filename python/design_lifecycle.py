"""Python CLI entrypoints and shared helpers for /design lifecycle phases."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from collections.abc import Iterable, Sequence


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
