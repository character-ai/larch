"""Python CLI entrypoint for the /implement Step 1 plan-log helper."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from collections.abc import Sequence


def _fail(msg: str) -> int:
    print(f"run-step1-plan-log.sh: {msg}", file=sys.stderr)
    return 2


def _session_get(*, path: Path, key: str, default: str = "") -> str:
    if not path.is_file():
        return default
    # Read inside the try, scan outside it: narrows the OSError scope and keeps
    # this helper structurally distinct from design_lifecycle._read_env_value
    # (avoids pylint R0801 duplicate-code across the two modules).
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return default
    prefix = f"{key}="
    for raw in text.splitlines():
        if raw.startswith(prefix):
            return raw[len(prefix):] or default
    return default


def _resolve_run_id(*, session_env_path: Path, implement_tmpdir: Path, session_id_file: Path) -> str:
    run_id = _session_get(path=session_env_path, key="RUN_ID", default="")
    if not run_id:
        run_id = _session_get(path=implement_tmpdir / "parent-issue.md", key="RUN_ID", default="")
    if not run_id:
        manifests: list[Path] = list((implement_tmpdir / "larch-logs" / "implement").glob("*/manifest.json"))
        if len(manifests) == 1:
            run_id = manifests[0].parent.name
    if not run_id and session_id_file.is_file():
        try:
            run_id = session_id_file.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            run_id = ""
    return run_id


def _append_log_write_failure(*, plugin_root: Path, implement_tmpdir: Path, site: str, tool: str, output_file: Path) -> None:
    helper = plugin_root / "python" / "cli.py"
    if not helper.is_file():
        print(f"run-step1-plan-log.sh: best-effort log write failed for {tool} (see {output_file})", file=sys.stderr)
        return
    _ = subprocess.run(
        [
            sys.executable,
            str(helper),
            "run-log",
            "append-failure",
            "--log",
            str(implement_tmpdir / "execution-issues.md"),
            "--site",
            site,
            "--tool",
            tool,
            "--exit-code",
            "1",
            "--category",
            "Warnings",
            "--output-file",
            str(output_file),
            "--redact",
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def step1_log_main(argv: Sequence[str]) -> int:
    args = list(argv)
    implement_tmpdir_arg = ""
    goal_text = ""
    goal_text_set = False
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--implement-tmpdir":
            if i + 1 >= len(args):
                return _fail("--implement-tmpdir requires a value")
            implement_tmpdir_arg = args[i + 1]
            i += 2
            continue
        if token == "--goal-text":
            if i + 1 >= len(args):
                return _fail("--goal-text requires a value")
            goal_text = args[i + 1]
            goal_text_set = True
            i += 2
            continue
        if token in {"-h", "--help"}:
            print("Usage: run-step1-plan-log.sh --implement-tmpdir PATH --goal-text TEXT", file=sys.stderr)
            return 0
        print("Usage: run-step1-plan-log.sh --implement-tmpdir PATH --goal-text TEXT", file=sys.stderr)
        return _fail(f"unknown option: {token}")

    if not implement_tmpdir_arg:
        print("Usage: run-step1-plan-log.sh --implement-tmpdir PATH --goal-text TEXT", file=sys.stderr)
        return _fail("--implement-tmpdir is required")
    if not goal_text_set:
        print("Usage: run-step1-plan-log.sh --implement-tmpdir PATH --goal-text TEXT", file=sys.stderr)
        return _fail("--goal-text is required")

    implement_tmpdir = Path(implement_tmpdir_arg)
    if not implement_tmpdir.is_dir():
        return _fail(f"--implement-tmpdir not a directory: {implement_tmpdir_arg}")
    implement_tmpdir = implement_tmpdir.resolve()
    session_env_path = implement_tmpdir / "session-env.sh"
    if not session_env_path.is_file():
        return _fail(f"session-env not readable: {session_env_path}")

    run_id = _resolve_run_id(session_env_path=session_env_path, implement_tmpdir=implement_tmpdir, session_id_file=implement_tmpdir / "session-id")
    if not run_id:
        return _fail("RUN_ID unresolved from session-env, parent-issue, manifest, or session-id")

    plan_file = implement_tmpdir / "plan.txt"
    if not plan_file.is_file():
        return _fail(f"plan file not found at conventional path: {plan_file}")

    plugin_root = Path(
        os.environ.get("CLAUDE_PLUGIN_ROOT")
        or _session_get(path=session_env_path, key="LARCH_CLAUDE_PLUGIN_ROOT", default="")
        or Path(__file__).resolve().parents[3]
    )
    if not plugin_root.is_dir():
        return _fail(f"plugin root not a directory: {plugin_root}")
    os.environ["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    os.environ["IMPLEMENT_TMPDIR"] = str(implement_tmpdir)

    compose_override = os.environ.get("RUN_STEP1_COMPOSE_CMD", "").strip()
    if compose_override:
        compose_cmd: list[str] = shlex.split(compose_override)
    else:
        compose_cmd = [sys.executable, str(plugin_root / "python" / "cli.py"), "plan", "compose-goals-test"]

    larch_log_override = os.environ.get("RUN_STEP1_LARCH_LOG_SH", "").strip()
    if larch_log_override:
        if not os.access(larch_log_override, os.X_OK):
            return _fail(f"run-log override not executable: {larch_log_override}")
        larch_log_cmd: list[str] = [larch_log_override]
    else:
        if shutil.which("python3") is None:
            return _fail("python3 not found")
        cli_py = plugin_root / "python" / "cli.py"
        if not cli_py.is_file():
            return _fail(f"python CLI missing: {cli_py}")
        larch_log_cmd = [sys.executable, str(cli_py), "run-log"]

    output_file = implement_tmpdir / "plan-goals-test.md"
    fd, tmp_name = tempfile.mkstemp(prefix="plan-goals-test.md.tmp.", dir=str(implement_tmpdir))
    os.close(fd)
    tmp_output = Path(tmp_name)
    try:
        with tmp_output.open("w", encoding="utf-8") as handle:
            compose: subprocess.CompletedProcess[str] = subprocess.run(
                [*compose_cmd, "--plan-file", str(plan_file), "--goal-text", goal_text],
                check=False,
                text=True,
                stdout=handle,
            )
        if compose.returncode != 0:
            return int(compose.returncode)
        _ = tmp_output.replace(output_file)
        tmp_name = ""
    finally:
        if tmp_name:
            Path(tmp_name).unlink(missing_ok=True)

    write_result: subprocess.CompletedProcess[str] = subprocess.run(
        [
            *larch_log_cmd,
            "write",
            "--log-root",
            str(implement_tmpdir / "larch-logs"),
            "--skill",
            "implement",
            "--run-id",
            run_id,
            "--batch",
            "plan-goals-test",
            "--input-file",
            str(output_file),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    if write_result.stdout:
        _ = sys.stdout.write(write_result.stdout)
    if write_result.stderr:
        _ = sys.stderr.write(write_result.stderr)
    if write_result.returncode != 0:
        return int(write_result.returncode)

    parent_issue = implement_tmpdir / "parent-issue.md"
    if parent_issue.is_file():
        parent_issue_fail_log = implement_tmpdir / "parent-issue-write.failure.log"
        parent_write: subprocess.CompletedProcess[str] = subprocess.run(
            [
                *larch_log_cmd,
                "write",
                "--log-root",
                str(implement_tmpdir / "larch-logs"),
                "--skill",
                "implement",
                "--run-id",
                run_id,
                "--batch",
                "parent-issue",
                "--input-file",
                str(parent_issue),
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        if parent_write.returncode != 0:
            _ = parent_issue_fail_log.write_text(
                (parent_write.stdout or "") + (parent_write.stderr or ""),
                encoding="utf-8",
            )
            _append_log_write_failure(
                plugin_root=plugin_root,
                implement_tmpdir=implement_tmpdir,
                site="1",
                tool="python3 python/cli.py run-log write parent-issue",
                output_file=parent_issue_fail_log,
            )
    return 0
