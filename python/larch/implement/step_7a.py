"""Python Step 7a orchestration for /implement."""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import contextlib
import os
import re
import subprocess
import sys
from pathlib import Path
from larch import io as larch_io

from larch.issue import execution_issues
from larch.git import pr_body
from larch.core import run_context
from larch.report import run_logs

_NON_RUNTIME_NAMES = frozenset({"README.md"})
_NON_RUNTIME_EXTS = frozenset({"txt", "tsv"})
_MAX_SMALL_CHANGE_FILES = 2


def emit(*, key: str, value: object) -> None:
    print(f"{key}={value}")


def _plugin_root() -> Path:
    return Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))


def _read_kv(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path=path, key=key, default=default, first_match=True, cr_strip="strip", on_error_default=False)


def _is_non_runtime_path(path: str) -> bool:
    if path.startswith("docs/"):
        return True
    base = Path(path).name
    if base in _NON_RUNTIME_NAMES:
        return True
    if "." not in path:
        return False
    return path.rsplit(".", 1)[-1] in _NON_RUNTIME_EXTS


def _is_small_non_runtime_change(*, base_remote: str, base_ref: str) -> bool:
    merge_base: subprocess.CompletedProcess[str] = subprocess.run(["git", "merge-base", "HEAD", f"{base_remote}/{base_ref}"], text=True, capture_output=True, check=False)  # noqa: S607
    if merge_base.returncode != 0 or not merge_base.stdout.strip():
        return False
    changed: subprocess.CompletedProcess[str] = subprocess.run(["git", "diff", "--name-only", f"{merge_base.stdout.strip()}..HEAD"], text=True, capture_output=True, check=False)  # noqa: S607
    if changed.returncode != 0:
        return False
    paths: list[str] = [line for line in changed.stdout.splitlines() if line.strip()]
    if not paths or len(paths) > _MAX_SMALL_CHANGE_FILES:
        return False
    return all(_is_non_runtime_path(path) for path in paths)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_plugin_root() / "python" / "cli.py"), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _cleanup_diagram_artifacts(implement_tmpdir: Path, *, keep_diagram: bool) -> None:
    section = implement_tmpdir / "code-flow-section.md"
    diagram = implement_tmpdir / "code-flow-diagram.md"
    with contextlib.suppress(OSError):
        section.unlink()
    if not keep_diagram:
        with contextlib.suppress(OSError):
            diagram.unlink()


def _append_diagram_warning(*, implement_tmpdir: Path, message: str) -> None:
    run_logs.append_execution_issue(
        log_file=implement_tmpdir / "execution-issues.md",
        category="Warnings",
        entry=f"- **Step 7a — code flow diagram**: {message}"    )



def _run_log_flush(
    implement_tmpdir: Path,
    *,
    run_id: str,
    no_logs_commit: bool,
    claude_source_file: str,
    defer_git_commit: bool = False,
) -> str:
    log_flush_status = "ok"
    _run_cli("token", "mark", "Step 8 — ship PR")
    env = {**os.environ, "LARCH_TIMING_SKILL": "implement"}
    subprocess.run(
        [sys.executable, str(_plugin_root() / "python" / "cli.py"), "timing", "mark", "Step 8 — ship PR"],
        env=env,
        check=False,
    )
    log_root = implement_tmpdir / "larch-logs"
    issue_log = implement_tmpdir / "execution-issues.md"
    if not run_id:
        return "skip"
    rc, status, _records, _append_log = execution_issues.flush_execution_issues(
        log_root=log_root,
        run_id=run_id,
        issue_log=issue_log,
    )
    if rc != 0 or status not in {"ok", "skip", "already-flushed", "no-records"}:
        log_flush_status = "degraded"
    ctx = run_context.RunContext(
        branch="",
        issue="",
        repo="",
        run_id=run_id,
        tmpdir=str(implement_tmpdir),
        merge=False,
        draft=False,
        forked=False,
        manifest_path=str(log_root / "implement" / run_id / "manifest.json"),
        tool_label="",
        no_admin_fallback=False,
        repo_unavailable=False,
        no_logs_commit=no_logs_commit,
    )
    with_context = ctx.with_(state_file=None)
    try:
        run_logs._render_token_timing_batches(ctx=with_context, log_root=log_root)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        run_logs._stage_vendor_failure_diagnostics(ctx=with_context, log_root=log_root)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
    except Exception:
        log_flush_status = "degraded"
    if claude_source_file:
        capture = _run_cli(
            "run-log",
            "capture-transcript",
            "--source-file",
            claude_source_file,
            "--log-root",
            str(log_root),
            "--skill",
            "implement",
            "--run-id",
            run_id,
            "--no-logs-commit",
            str(no_logs_commit).lower(),
            "--defer-commit",
            "true",
            "--execution-issues-log",
            str(issue_log),
        )
        if capture.returncode != 0:
            log_flush_status = "degraded"
        for line in capture.stdout.splitlines():
            if line.startswith("SESSION_TRANSCRIPT_STATUS="):
                print(line)
    rc2, status2, _, _ = execution_issues.flush_execution_issues(
        log_root=log_root,
        run_id=run_id,
        issue_log=issue_log,
        step_label="7a-post-transcript",
        source_label="execution-issues.md post-transcript refresh",
    )
    if rc2 != 0 or status2 not in {"ok", "skip", "already-flushed", "no-records"}:
        log_flush_status = "degraded"
    if not no_logs_commit and not defer_git_commit:
        refresh = run_logs.flush_logs_pre(runner=run_logs.proc, ctx=with_context, cwd=str(Path.cwd()))
        if refresh.skipped and refresh.reason not in {"no-repo-cwd", "no-logs-commit", "volatile-only"}:
            log_flush_status = "degraded"
        commit = _run_cli(
            "run-log",
            "commit",
            "--log-root",
            str(log_root),
            "--skill",
            "implement",
            "--run-id",
            run_id,
        )
        if commit.returncode != 0:
            log_flush_status = "degraded"
    elif log_flush_status == "ok":
        log_flush_status = "skipped-no-logs-commit"
    return log_flush_status


def run_step7a(
    implement_tmpdir: Path,
    *,
    issue_number: str = "",
    run_id: str = "",
    no_logs_commit: bool = False,
    forked_target: bool = False,
    base_remote: str = "origin",
    base_ref: str = "main",
) -> int:
    implement_tmpdir.mkdir(parents=True, exist_ok=True)
    session_env = implement_tmpdir / "session-env.sh"
    if not issue_number:
        issue_number = _read_kv(path=session_env, key="LARCH_ISSUE_NUMBER")
    if not run_id:
        run_id = _read_kv(path=session_env, key="LARCH_RUN_ID") or (
            (implement_tmpdir / "session-id").read_text(encoding="utf-8").strip()
            if (implement_tmpdir / "session-id").is_file()
            else ""
        )
    if session_env.is_file() and not forked_target:
        forked_target = _read_kv(path=session_env, key="LARCH_FORKED_TARGET", default="false") == "true"
    if forked_target:
        base_remote = "upstream"
    repo = ""
    if session_env.is_file():
        if forked_target:
            repo = _read_kv(path=session_env, key="UPSTREAM_REPO")
        if not repo:
            repo = _read_kv(path=session_env, key="REPO")
        if not repo:
            repo = _read_kv(path=session_env, key="UPSTREAM_REPO")
    claude_source = _read_kv(path=session_env, key="LARCH_CLAUDE_SOURCE_FILE")

    _run_cli("token", "mark", "Step 7a — pre-ship")
    subprocess.run(
        [sys.executable, str(_plugin_root() / "python" / "cli.py"), "timing", "mark", "Step 7a — pre-ship"],
        env={**os.environ, "LARCH_TIMING_SKILL": "implement"},
        check=False,
    )

    diagram_status = "skipped"
    diagram_reason = ""
    diagram_path = ""
    comment_url = ""
    bail = ""
    if _is_small_non_runtime_change(base_remote=base_remote, base_ref=base_ref):
        diagram_status = "skip"
        _cleanup_diagram_artifacts(implement_tmpdir, keep_diagram=False)
        print("⏩ 7a: pre-ship status=skip reason=small-non-runtime-change elapsed=0s")
    else:
        diagram_rc, diagram_status, diagram_path, reason = pr_body.generate_code_flow_diagram(
            implement_tmpdir,
            base_remote=base_remote,
            base_ref=base_ref,
        )
        retry_sidecar = implement_tmpdir / "code-flow-diagram.retried"
        if retry_sidecar.is_file():
            first_rc = ""
            with contextlib.suppress(OSError, ValueError):
                for line in retry_sidecar.read_text(encoding="utf-8").splitlines():
                    if line.startswith("FIRST_RC="):
                        first_rc = line.split("=", 1)[1].strip()
            retry_msg = f"code-flow subprocess transient (rc={first_rc}); retried once"
            run_logs.append_execution_issue(
                log_file=implement_tmpdir / "execution-issues.md",
                category="Warnings",
                entry=f"- **Step 7a — code flow diagram**: {retry_msg}",
            )
            with contextlib.suppress(OSError):
                retry_sidecar.unlink()
        keep_diagram = diagram_status == "ok" and bool(diagram_path)
        if keep_diagram:
            section = implement_tmpdir / "code-flow-section.md"
            section.write_text((implement_tmpdir / "code-flow-diagram.md").read_text(encoding="utf-8"), encoding="utf-8")
        else:
            _cleanup_diagram_artifacts(implement_tmpdir, keep_diagram=False)
        if diagram_rc != 0 or diagram_status == "failed":
            diagram_status = "failed"
            diagram_reason = reason or "generation failed"
            diagram_path = ""
            _append_diagram_warning(implement_tmpdir=implement_tmpdir, message=diagram_reason)

    if issue_number and (implement_tmpdir / "code-flow-section.md").is_file() and (implement_tmpdir / "code-flow-section.md").stat().st_size > 0:
        upsert_args = ["diagrams", "upsert", "--issue", issue_number, "--code-flow-file", str(implement_tmpdir / "code-flow-section.md")]
        if repo:
            upsert_args.extend(["--repo", repo])
        upsert = _run_cli(*upsert_args)
        if upsert.returncode == 0:
            m: re.Match[str] | None = re.search(r"^COMMENT_URL=(.*)$", upsert.stdout, re.MULTILINE)
            upsert_status: re.Match[str] | None = re.search(r"^UPSERT_STATUS=(.*)$", upsert.stdout, re.MULTILINE)
            if upsert_status and upsert_status.group(1) != "failed" and m:
                comment_url = m.group(1)

    rebase_out = implement_tmpdir / "rebase-checkpoint-probe.stdout"
    probe = _run_cli(
        "push",
        "checkpoint-probe",
        "7a.r",
        "diagrams",
        "--base-remote",
        base_remote,
        "--base-ref",
        base_ref,
    )
    rebase_out.write_text(probe.stdout, encoding="utf-8")
    for line in probe.stdout.splitlines():
        if line.strip():
            print(line)
    log_flush_status = _run_log_flush(
        implement_tmpdir,
        run_id=run_id,
        no_logs_commit=no_logs_commit,
        claude_source_file=claude_source,
        defer_git_commit=probe.returncode != 0,
    )
    if probe.returncode != 0:
        emit(key="DIAGRAM_STATUS", value=diagram_status)
        emit(key="DIAGRAM_REASON", value=diagram_reason)
        emit(key="DIAGRAM_PATH", value=diagram_path)
        emit(key="COMMENT_URL", value=comment_url)
        emit(key="LOG_FLUSH_STATUS", value=log_flush_status)
        emit(key="STEP_7A_BAIL_REASON", value=bail)
        emit(key="REBASE_OUTCOME", value="conflict" if probe.returncode == 1 else "failed")
        return probe.returncode

    rebase_outcome = "skipped"
    for line in probe.stdout.splitlines():
        if line.startswith("REBASE_OUTCOME="):
            rebase_outcome = line.partition("=")[2].strip() or "skipped"
    emit(key="DIAGRAM_STATUS", value=diagram_status)
    emit(key="DIAGRAM_REASON", value=diagram_reason)
    emit(key="DIAGRAM_PATH", value=diagram_path)
    emit(key="COMMENT_URL", value=comment_url)
    emit(key="LOG_FLUSH_STATUS", value=log_flush_status)
    emit(key="STEP_7A_BAIL_REASON", value=bail)
    emit(key="REBASE_OUTCOME", value=rebase_outcome)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-7a")
    parser.add_argument("--implement-tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", ""))
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--no-logs-commit", choices=("true", "false"), default="false")
    parser.add_argument("--forked-target", choices=("true", "false"), default="false")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        emit(key="DIAGRAM_STATUS", value="failed")
        emit(key="DIAGRAM_REASON", value="")
        emit(key="DIAGRAM_PATH", value="")
        emit(key="COMMENT_URL", value="")
        emit(key="LOG_FLUSH_STATUS", value="skip")
        emit(key="STEP_7A_BAIL_REASON", value="argv")
        emit(key="REBASE_OUTCOME", value="skipped")
        return 2
    if not args.implement_tmpdir:
        emit(key="DIAGRAM_STATUS", value="failed")
        emit(key="DIAGRAM_REASON", value="")
        emit(key="DIAGRAM_PATH", value="")
        emit(key="COMMENT_URL", value="")
        emit(key="LOG_FLUSH_STATUS", value="skip")
        emit(key="STEP_7A_BAIL_REASON", value="missing-implement-tmpdir")
        emit(key="REBASE_OUTCOME", value="skipped")
        return 2
    return run_step7a(
        Path(args.implement_tmpdir),
        issue_number=args.issue_number,
        run_id=args.run_id,
        no_logs_commit=args.no_logs_commit == "true",
        forked_target=args.forked_target == "true",
        base_remote=args.base_remote,
        base_ref=args.base_ref,
    )
