"""Step 1 brainstorm, drafter prerequisites, and plan-driver helpers."""
# pylint: disable=cyclic-import
# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from collections.abc import Mapping, Sequence

from larch.git.repo_roots import consumer_repo_root

from larch.design.design_router import _extract_args, _normalize_step, _parse_stdout_kv
from larch.design.design_step0 import (
    _append_failure,
    _cli_cmd,
    _derive_binary_found,
    _require_design_tmpdir,
    _run_best_effort,
    check_pause_and_exit,
)
from larch.design.design_step0_env import _load_wrapper_env, _parse_wrapper_args, require_plugin_root

def brainstorm_stderr_sink_for_output(*, output_path: Path, design_tmpdir: Path) -> Path | None:
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


def brainstorm_collect_launch_failure_once(*, plugin_root: Path, design_tmpdir: Path, log_path: Path, tool: str) -> None:
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
    if _append_failure(plugin_root=plugin_root, design_tmpdir=design_tmpdir, site="design Step 1d.5", tool=tool, exit_code=exit_code, category="External Reviewer Issues", output_file=log_path):
        sentinel.write_text("", encoding="utf-8")


def _brainstorm_dirty_checkpoint(*, plugin_root: Path, design_tmpdir: Path, paths: Sequence[Path]) -> None:
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


def _step1d5_brainstorm_requested(design_tmpdir: Path) -> bool:
    run_params = design_tmpdir / "run-params.json"
    if not run_params.is_file() or run_params.is_symlink():
        return False
    try:
        data = json.loads(run_params.read_text(encoding="utf-8"))
    except OSError:
        return False
    except json.JSONDecodeError:
        print("**⚠ Step 1d.5: run-params.json is malformed; defaulting brainstorm_requested=false**", file=sys.stderr)
        return False
    if not isinstance(data, dict):
        return False
    return data.get("brainstorm_requested") is True


def _step1d5_entry_main(*, plugin_root: Path, design_tmpdir: Path, env: Mapping[str, str]) -> int:
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    for name in ("step-1c", "step-1d"):
        (completed / name).write_text("", encoding="utf-8")
    brainstorm_requested = _step1d5_brainstorm_requested(design_tmpdir)
    if (design_tmpdir / ".brainstorm-done").is_file():
        action = "skip"
        skip_kind = "already-complete"
    elif not brainstorm_requested:
        action = "skip"
        skip_kind = "disabled"
    else:
        action = "run"
        skip_kind = ""
    if action == "skip":
        (completed / "step-1d.5").write_text("", encoding="utf-8")
    check_pause_and_exit(env=env, design_tmpdir=design_tmpdir)
    print(f"STEP1D5_ACTION={action}")
    if skip_kind:
        print(f"STEP1D5_SKIP_KIND={skip_kind}")
    _run_best_effort(command=_cli_cmd(plugin_root, "timing", "mark", "design Step 1d.5 — brainstorm"), env={**os.environ, "LARCH_TIMING_SKILL": "design"})
    return 0


def step1d5_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    design_tmpdir = _require_design_tmpdir(env=env)
    if ns.mode == "entry":
        return _step1d5_entry_main(plugin_root=plugin_root, design_tmpdir=design_tmpdir, env=env)
    if ns.mode == "collect":
        check_pause_and_exit(env=env, design_tmpdir=design_tmpdir)
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
            _append_failure(plugin_root=plugin_root, design_tmpdir=design_tmpdir, site="design Step 1d.5", tool="agent collect-results", exit_code=collect.returncode, category="External Reviewer Issues", output_file=failure)
        for path in paths:
            sink = brainstorm_stderr_sink_for_output(output_path=path, design_tmpdir=design_tmpdir)
            if sink is not None:
                brainstorm_collect_launch_failure_once(plugin_root=plugin_root, design_tmpdir=design_tmpdir, log_path=sink, tool=_launch_tool_for_sink(sink))
        _brainstorm_dirty_checkpoint(plugin_root=plugin_root, design_tmpdir=design_tmpdir, paths=paths)
        return 0
    if ns.mode == "complete":
        completed = design_tmpdir / ".completed"
        completed.mkdir(parents=True, exist_ok=True)
        (completed / "step-1d.5").write_text("", encoding="utf-8")
        check_pause_and_exit(env=env, design_tmpdir=design_tmpdir)
        return 0
    print("design-step1d5.sh: --mode required", file=sys.stderr)
    return 2


def step1d7_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    _derive_binary_found(env)
    design_tmpdir = _require_design_tmpdir(env=env)
    if not _step1d5_brainstorm_requested(design_tmpdir):
        completed = design_tmpdir / ".completed"
        completed.mkdir(parents=True, exist_ok=True)
        for name in ("step-1c", "step-1d", "step-1d.5"):
            (completed / name).write_text("", encoding="utf-8")
    check_pause_and_exit(env=env, design_tmpdir=design_tmpdir)
    skip = False
    try:
        data = json.loads((design_tmpdir / "run-params.json").read_text(encoding="utf-8"))
        skip = bool(data.get("skip_approve_requested")) if isinstance(data, dict) else False
    except (OSError, json.JSONDecodeError):
        skip = False
    print(f"SKIP_APPROVE_REQUESTED={'true' if skip else 'false'}")
    return 0


def step1e_reentry_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    design_tmpdir = _require_design_tmpdir(env=env)
    for name in ("step-1e", "step-2a", "step-2a.5", "step-2b", "step-2b.5", "step-3", "step-3.5", "step-3b", "step-4", "step-4b"):
        with contextlib.suppress(FileNotFoundError):
            (design_tmpdir / ".completed" / name).unlink()
    for path in design_tmpdir.glob(".gate-b-postapply-ready-*"):
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
    check_pause_and_exit(env=env, design_tmpdir=design_tmpdir)
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
    root = Path(__file__).resolve().parents[3]
    consumer_root = consumer_repo_root() or root

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
            env: dict[str, str] = os.environ.copy()
            env["DESIGN_TMPDIR"] = str(design_tmpdir)
            command = [sys.executable, str(root / "python" / "cli.py"), "plan", "validate", "--design-tmpdir", str(design_tmpdir), "--repo-root", str(consumer_root), *action_args]
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
