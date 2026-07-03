"""Design route main and init-runparams helpers."""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportPrivateUsage=false, reportUnusedFunction=false
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence

from larch import io as larch_io

def _usage() -> None:
    print(
        "usage: read-result-env.sh --input PATH [--fallback-input PATH] --allow KEY ... --output PATH",
        file=sys.stderr,
    )


def route_main(argv: Sequence[str]) -> int:
    args = list(argv)
    required: dict[str, str] = {
        "--design-tmpdir": "",
        "--issue": "",
        "--issue-title": "",
        "--issue-body-file": "",
        "--has-clarify-label": "",
        "--claude-pid": "",
        "--session-id": "",
    }
    optional: dict[str, str] = {
        "--repo": "",
        "--partition-requested": "false",
        "--brainstorm-requested": "false",
        "--approve-requested": "false",
        "--skip-approve-requested": "false",
        "--difficulty": "",
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
        pause_cmd = [sys.executable, str(Path(__file__).resolve().parents[2] / "cli.py"), "design", "pause-load", "--design-tmpdir", str(design_tmpdir), "--issue", required["--issue"]]
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
            str(Path(__file__).resolve().parents[2] / "cli.py"),
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
            run_params=design_tmpdir / "run-params.json",
            warn_lines=warn_lines,
            merge_partition=optional["--partition-requested"] == "true",
            merge_brainstorm=optional["--brainstorm-requested"] == "true" or brainstorm_prefix == "true",
            merge_approve=optional["--approve-requested"] == "true",
            merge_skip_approve=optional["--skip-approve-requested"] == "true",
            difficulty=optional["--difficulty"],
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
    _write_kv_file(path=result_env, rows=out)  # pyright: ignore[reportUnusedCallResult]
    for key, value in out:
        print(f"{key}={value}")
    return 0


def init_runparams_main(argv: Sequence[str]) -> int:
    args = list(argv)
    parsed: dict[str, str] = {}
    i = 0
    while i < len(args):
        token = args[i]
        if token in {"--design-tmpdir", "--issue", "--session-id", "--claude-pid", "--partition-requested", "--brainstorm-requested", "--approve-requested", "--skip-approve-requested", "--repo", "--difficulty"}:
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
    root = Path(__file__).resolve().parents[3]

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
        _write_kv_file(path=result_env, rows=[("INIT_STATUS", init_status), ("RUN_PARAMS_PATH", str(run_params_path))])  # pyright: ignore[reportUnusedCallResult]
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
            "--difficulty",
            parsed.get("--difficulty", ""),
            "--output",
            str(run_params_path),
        ],
        check=False,
    )
    if write_params.returncode != 0:
        init_status = "contract-drift"
        _write_kv_file(path=result_env, rows=[("INIT_STATUS", init_status), ("RUN_PARAMS_PATH", str(run_params_path))])  # pyright: ignore[reportUnusedCallResult]
        print("INIT_STATUS=contract-drift")
        return 1

    _merge_router_flags(
        run_params=run_params_path,
        warn_lines=warn_lines,
        merge_partition=parsed["--partition-requested"] == "true",
        merge_brainstorm=parsed["--brainstorm-requested"] == "true",
        merge_approve=parsed["--approve-requested"] == "true",
        merge_skip_approve=parsed["--skip-approve-requested"] == "true",
        difficulty=parsed.get("--difficulty", ""),
    )
    result_rows: list[tuple[str, str]] = [("INIT_STATUS", init_status), ("RENAMED", renamed), ("RUN_PARAMS_PATH", str(run_params_path))]
    result_rows.extend(("WARN", w) for w in warn_lines)
    _write_kv_file(path=result_env, rows=result_rows)  # pyright: ignore[reportUnusedCallResult]
    for key, value in result_rows:
        print(f"{key}={value}")
    return 0


def _write_kv_file(*, path: Path, rows: list[tuple[str, str]]) -> bool:
    try:
        larch_io.write_kvs(path=path, values=rows, atomic=False, create_parent=False)
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
    *, run_params: Path,
    warn_lines: list[str],
    merge_partition: bool,
    merge_brainstorm: bool,
    merge_approve: bool,
    merge_skip_approve: bool,
    difficulty: str = "",
) -> None:
    if not (merge_partition or merge_brainstorm or merge_approve or merge_skip_approve or difficulty):
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
        if difficulty:
            data["difficulty_override"] = difficulty
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
