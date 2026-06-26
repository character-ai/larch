"""/implement Step 16/17 closeout helpers."""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
from contextlib import suppress
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SUMMARY_BEGIN = "---LARCH-SUMMARY-FINAL-BEGIN---"
SUMMARY_END = "---LARCH-SUMMARY-FINAL-END---"
_PY_CLI = Path(__file__).resolve().parents[2] / "cli.py"


def _plugin_root() -> Path:
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if env_root:
        return Path(env_root)
    tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if tmpdir:
        plugin_env = Path(tmpdir) / "plugin-root.env"
        if plugin_env.is_file():
            for line in plugin_env.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("CLAUDE_PLUGIN_ROOT="):
                    return Path(line.split("=", 1)[1])
        session = Path(tmpdir) / "session-env.sh"
        value = _read_key(path=session, key="LARCH_CLAUDE_PLUGIN_ROOT", default="")
        if value:
            return Path(value)
    return Path(__file__).resolve().parents[3]


def _validate_plugin_root(plugin_root: Path) -> int | None:
    cli_path = plugin_root / "python" / "cli.py"
    if not plugin_root.is_dir() or not cli_path.is_file():
        print("**❌ /implement closeout: cannot resolve CLAUDE_PLUGIN_ROOT/python/cli.py.**", file=sys.stderr)
        return 2
    return None


def _read_key(*, path: Path, key: str, default: str = "") -> str:
    result = _run(
        [sys.executable, str(_PY_CLI), "session", "read-key", "--file", str(path), "--key", key, "--default", default],
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    stdout = (result.stdout or "").strip()
    return stdout if result.returncode == 0 else default


def _env_for(*, tmpdir: Path, plugin_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["IMPLEMENT_TMPDIR"] = str(tmpdir)
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    session = tmpdir / "session-env.sh"
    for key in ("LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE", "LARCH_TIMING_LEDGER"):
        env[key] = _read_key(path=session, key=key, default=env.get(key, ""))
    return env


def _resolve_tmpdir(value: str | None) -> Path:
    tmpdir = value or os.environ.get("IMPLEMENT_TMPDIR", "")
    if not tmpdir:
        raise ValueError("IMPLEMENT_TMPDIR required")
    return Path(tmpdir)


def _run(argv: list[str], *, env: dict[str, str], stdout: Any = None, stderr: Any = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, env=env, stdout=stdout, stderr=stderr, check=False)


def _append_failure(
    *,
    tmpdir: Path,
    plugin_root: Path,
    env: dict[str, str],
    site: str,
    tool: str,
    exit_code: int,
    category: str,
    output_file: Path,
) -> None:
    if not output_file.exists():
        with suppress(OSError):
            output_file.write_text("", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(plugin_root / "python" / "cli.py"),
            "run-log",
            "append-failure",
            "--log",
            str(tmpdir / "execution-issues.md"),
            "--site",
            site,
            "--tool",
            tool,
            "--exit-code",
            str(exit_code),
            "--category",
            category,
            "--output-file",
            str(output_file),
            "--redact",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        env=env,
        check=False,
    )


def _summary_nonempty(tmpdir: Path) -> bool:
    path = tmpdir / "summary-final.md"
    return path.is_file() and path.stat().st_size > 0


def _print_summary_markers(tmpdir: Path, *, sentinel: str = ".step17-printed") -> int:
    summary = tmpdir / "summary-final.md"
    try:
        data = summary.read_bytes()
    except OSError:
        print("closeout: cannot read summary-final.md", file=sys.stderr)
        return 1
    body = data.decode("utf-8", errors="replace")
    if data and not data.endswith(b"\n"):
        body += "\n"
    try:
        sys.stdout.write(f"{SUMMARY_BEGIN}\n{body}{SUMMARY_END}\n")
        (tmpdir / sentinel).touch()
    except OSError:
        print("closeout: cannot emit summary markers", file=sys.stderr)
        return 1
    return 0


def step_16(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-16")
    parser.add_argument("--implement-tmpdir", default="")
    args = parser.parse_args(argv)
    try:
        tmpdir = _resolve_tmpdir(args.implement_tmpdir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    plugin_root = _plugin_root()
    if (rc := _validate_plugin_root(plugin_root)) is not None:
        return rc
    env = _env_for(tmpdir=tmpdir, plugin_root=plugin_root)
    run_id = _read_key(path=tmpdir / "session-env.sh", key="LARCH_RUN_ID", default=env.get("RUN_ID", ""))
    if not run_id:
        run_id = _read_key(path=tmpdir / "ship-pr-state.sh", key="RUN_ID", default="")
    if not run_id:
        run_id = _read_key(path=tmpdir / "finalize-state.sh", key="RUN_ID", default="")
    cli = str(plugin_root / "python" / "cli.py")
    _run([sys.executable, cli, "timing", "telemetry-mark", "--implement-tmpdir", str(tmpdir), "--label", "Step 16 — rejected findings"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _run([sys.executable, cli, "review-and-fix", "write-rejected", "--implement-tmpdir", str(tmpdir), "--run-id", run_id, "--log-root", str(tmpdir / "larch-logs")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0


def step_16_main(argv: list[str] | None = None) -> int:
    return step_16(argv)


def _step_16a_slack(*, tmpdir: Path, plugin_root: Path, env: dict[str, str], cli: str) -> None:
    slack_log = tmpdir / "step16a-slack-issue-announce.log"
    with suppress(OSError):
        slack_log.write_text("", encoding="utf-8")
    slack_rc = 0
    try:
        with slack_log.open("w", encoding="utf-8") as handle:
            completed = _run(
                [sys.executable, cli, "slack", "issue-announce", "--implement-tmpdir", str(tmpdir), "--best-effort"],
                env=env,
                stdout=handle,
                stderr=subprocess.STDOUT,
            )
    except OSError:
        completed = _run(
            [sys.executable, cli, "slack", "issue-announce", "--implement-tmpdir", str(tmpdir), "--best-effort"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    slack_rc = completed.returncode
    try:
        slack_text = slack_log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        slack_text = ""
    if "STATUS=failed" in slack_text:
        _append_failure(
            tmpdir=tmpdir,
            plugin_root=plugin_root,
            env=env,
            site="Step 16a — notify",
            tool="python/cli.py slack issue-announce",
            exit_code=slack_rc,
            category="Warnings",
            output_file=slack_log,
        )


def step_16_16a(argv: list[str] | None = None) -> int:
    """Rejected findings replay and Slack notify without final-report write."""
    parser = argparse.ArgumentParser(prog="cli.py implement step-16-16a")
    parser.add_argument("--implement-tmpdir", default="")
    args = parser.parse_args(argv)
    try:
        tmpdir = _resolve_tmpdir(args.implement_tmpdir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    plugin_root = _plugin_root()
    if (rc := _validate_plugin_root(plugin_root)) is not None:
        return rc
    env = _env_for(tmpdir=tmpdir, plugin_root=plugin_root)
    cli = str(plugin_root / "python" / "cli.py")
    step16_log = tmpdir / "step16-write-rejected.failure.log"
    try:
        step_16(["--implement-tmpdir", str(tmpdir)])
    except Exception:
        with suppress(OSError):
            step16_log.write_text("", encoding="utf-8")
        _append_failure(
            tmpdir=tmpdir,
            plugin_root=plugin_root,
            env=env,
            site="Step 16 — rejected findings",
            tool="python/closeout.py step_16",
            exit_code=1,
            category="Tool Failures",
            output_file=step16_log,
        )
    _step_16a_slack(tmpdir=tmpdir, plugin_root=plugin_root, env=env, cli=cli)
    with suppress(OSError):
        (tmpdir / ".step16-16a-done").touch()
    return 0


def step_16_16a_main(argv: list[str] | None = None) -> int:
    return step_16_16a(argv)


def step_17(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-17")
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--no-print-stdout", action="store_true")
    args = parser.parse_args(argv)
    try:
        tmpdir = _resolve_tmpdir(args.implement_tmpdir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    plugin_root = _plugin_root()
    if (rc := _validate_plugin_root(plugin_root)) is not None:
        return rc
    env = _env_for(tmpdir=tmpdir, plugin_root=plugin_root)
    cli = str(plugin_root / "python" / "cli.py")
    _run([sys.executable, cli, "timing", "telemetry-mark", "--implement-tmpdir", str(tmpdir), "--label", "Step 17 — final report"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    summary = tmpdir / "summary-final.md"
    log = tmpdir / "step17-write-final-report.failure.log"
    with suppress(OSError):
        log.write_text("", encoding="utf-8")
    cmd = [sys.executable, cli, "final-report", "write", "--implement-tmpdir", str(tmpdir)]
    if args.no_print_stdout:
        backup = tmpdir / ".summary-final.pre-step17.bak"
        had_backup = False
        if summary.is_file():
            try:
                if backup.exists():
                    backup.unlink()
                shutil.move(str(summary), str(backup))
                had_backup = True
            except OSError:
                print("closeout: cannot backup summary-final.md before Step 17 write", file=sys.stderr)
                return 2
        completed: subprocess.CompletedProcess[str] | None = None
        with suppress(OSError):
            with log.open("w", encoding="utf-8") as handle:
                completed = _run(cmd, env=env, stdout=handle, stderr=subprocess.STDOUT)
        if completed is None:
            completed = _run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if completed.returncode == 0:
            if had_backup:
                backup.unlink(missing_ok=True)
            return 0
        _append_failure(
            tmpdir=tmpdir,
            plugin_root=plugin_root,
            env=env,
            site="Step 17 — final report",
            tool="python/cli.py final-report write",
            exit_code=completed.returncode,
            category="Tool Failures",
            output_file=log,
        )
        if _summary_nonempty(tmpdir):
            if had_backup:
                backup.unlink(missing_ok=True)
            return 0
        if had_backup and backup.is_file():
            with suppress(OSError):
                shutil.move(str(backup), str(summary))
        return completed.returncode
    completed_print: subprocess.CompletedProcess[str] | None = None
    with suppress(OSError):
        with log.open("w", encoding="utf-8") as handle:
            completed_print = _run([*cmd, "--print-stdout"], env=env, stdout=handle, stderr=subprocess.STDOUT)
    if completed_print is None:
        completed_print = _run([*cmd, "--print-stdout"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    completed = completed_print
    if completed.returncode == 0:
        with suppress(OSError):
            sys.stdout.write(log.read_text(encoding="utf-8", errors="replace"))
        if _summary_nonempty(tmpdir):
            with suppress(OSError):
                (tmpdir / ".step17-printed").touch()
    else:
        _append_failure(
            tmpdir=tmpdir,
            plugin_root=plugin_root,
            env=env,
            site="Step 17 — final report",
            tool="python/cli.py final-report write",
            exit_code=completed.returncode,
            category="Tool Failures",
            output_file=log,
        )
    return completed.returncode


def step_17_main(argv: list[str] | None = None) -> int:
    return step_17(argv)


def step_16_17(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-16-17")
    parser.add_argument("--implement-tmpdir", default="")
    args = parser.parse_args(argv)
    try:
        tmpdir = _resolve_tmpdir(args.implement_tmpdir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    plugin_root = _plugin_root()
    if (rc := _validate_plugin_root(plugin_root)) is not None:
        return rc
    env = _env_for(tmpdir=tmpdir, plugin_root=plugin_root)
    cli = str(plugin_root / "python" / "cli.py")
    step16_log = tmpdir / "step16-write-rejected.failure.log"
    try:
        step_16(["--implement-tmpdir", str(tmpdir)])
    except Exception:
        with suppress(OSError):
            step16_log.write_text("", encoding="utf-8")
        _append_failure(
            tmpdir=tmpdir,
            plugin_root=plugin_root,
            env=env,
            site="Step 16 — rejected findings",
            tool="python/closeout.py step_16",
            exit_code=1,
            category="Tool Failures",
            output_file=step16_log,
        )
    _step_16a_slack(tmpdir=tmpdir, plugin_root=plugin_root, env=env, cli=cli)
    with suppress(OSError):
        (tmpdir / ".step16-16a-done").touch()
    step17_log = tmpdir / "step17-write-final-report.failure.log"
    step17_rc = 1
    try:
        step17_rc = step_17(["--implement-tmpdir", str(tmpdir), "--no-print-stdout"])
    except Exception:
        with suppress(OSError):
            step17_log.write_text("", encoding="utf-8")
        _append_failure(
            tmpdir=tmpdir,
            plugin_root=plugin_root,
            env=env,
            site="Step 17 — final report",
            tool="python/closeout.py step_17",
            exit_code=1,
            category="Tool Failures",
            output_file=step17_log,
        )
    if step17_rc == 0 and _summary_nonempty(tmpdir) and _print_summary_markers(tmpdir, sentinel=".step17-printed") != 0:
        print("closeout: failed to emit summary markers", file=sys.stderr)
    return 0


def step_16_17_main(argv: list[str] | None = None) -> int:
    return step_16_17(argv)
