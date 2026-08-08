"""Python Step 7a orchestration for /implement."""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import contextlib
import os
import re
import subprocess
import sys
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io
from larch.core import config
from larch.core import proc
from larch.core import rust_runtime
from larch.core.repo_roots import larch_entrypoint, larch_entrypoint_env, plugin_root
from larch.git import pr_body
from larch.implement.dispatch_helpers import result_env_capture_rows
from larch.report import run_log_batch

_NON_RUNTIME_NAMES = frozenset({"README.md"})
_NON_RUNTIME_EXTS = frozenset({"txt", "tsv"})
_MAX_SMALL_CHANGE_FILES = 2
_result_rows: list[tuple[str, str]] | None = None


@dataclass(frozen=True)
class Step7aBgjobLaunch:
    implement_tmpdir: Path
    issue_number: str
    run_id: str
    no_logs_commit: str
    forked_target: str
    base_remote: str
    base_ref: str


def emit(*, key: str, value: object) -> None:
    _emit_line(f"{key}={value}")


def _emit_line(line: str) -> None:
    print(line)
    _record_result_line(line)


def _record_result_line(line: str) -> None:
    rows = _result_rows
    if rows is None or "\n" in line or "\r" in line or "=" not in line:
        return
    key, value = line.split("=", 1)
    if re.fullmatch(r"[A-Z0-9_]+", key):
        rows.append((key, value))


@contextlib.contextmanager
def _result_env_capture(path: Path | None) -> Generator[None, None, None]:
    global _result_rows  # noqa: PLW0603 - scoped sink for legacy emit helper
    prior = _result_rows
    try:
        with result_env_capture_rows(path) as rows:
            _result_rows = rows
            yield
    finally:
        _result_rows = prior


def _emit_arg_failure(*, bail_reason: str) -> int:
    emit(key="DIAGRAM_STATUS", value="failed")
    emit(key="DIAGRAM_REASON", value="")
    emit(key="DIAGRAM_PATH", value="")
    emit(key="COMMENT_URL", value="")
    emit(key="LOG_CHECKPOINT_STATUS", value="skip")
    emit(key="STEP_7A_BAIL_REASON", value=bail_reason)
    emit(key="REBASE_OUTCOME", value="skipped")
    return 2


def _has_symlink_ancestor(path: Path) -> bool:
    candidate = path.expanduser()
    return candidate.is_symlink() or any(parent.is_symlink() for parent in candidate.parents)


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
        [sys.executable, str(plugin_root(Path(__file__).resolve().parents[3]) / "python" / "cli.py"), *args],
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
    run_log_batch.append_execution_issue(
        log_file=implement_tmpdir / "execution-issues.md",
        category="Warnings",
        entry=f"- **Step 7a — code flow diagram**: {message}"    )


def _checkpoint_execution_issues(implement_tmpdir: Path, *, run_id: str) -> str:
    _run_cli("token", "mark", "Step 8 — ship PR")
    env = {**larch_entrypoint_env(Path(__file__).resolve().parents[3]), "LARCH_TIMING_SKILL": "implement"}
    subprocess.run(
        [str(larch_entrypoint(Path(__file__).resolve().parents[3])), "timing", "mark", "Step 8 — ship PR"],
        env=env,
        check=False,
    )
    log_root = implement_tmpdir / "larch-logs"
    issue_log = implement_tmpdir / "execution-issues.md"
    if not run_id:
        return "skip"
    # lint-subprocess-via-runner: ok the Rust owner reports its outcome as a
    # captured KEY=value envelope, not on this command's own contract stream.
    flush = subprocess.run(
        [
            str(larch_entrypoint(Path(__file__).resolve().parents[3])),
            "execution-issues", "flush",
            "--log-root", str(log_root),
            "--run-id", run_id,
            "--issue-log", str(issue_log),
            "--step-label", "7a",
            "--source-label", "execution-issues.md Step 7a checkpoint",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    status = next(
        (line.split("=", 1)[1] for line in flush.stdout.splitlines() if line.startswith("FLUSH_STATUS=")),
        "",
    )
    if flush.returncode == 0 and status in {"ok", "skip", "already-flushed", "no-records"}:
        return "ok"
    return "degraded"


def _generate_code_flow_diagram(
    implement_tmpdir: Path,
    *,
    base_remote: str,
    base_ref: str,
) -> pr_body.CodeFlowDiagramResult:
    result = pr_body.generate_code_flow_diagram(
        implement_tmpdir,
        base_remote=base_remote,
        base_ref=base_ref,
    )
    retry_sidecar = implement_tmpdir / "code-flow-diagram.retried"
    if retry_sidecar.is_file():
        first_rc = ""
        with contextlib.suppress(OSError, ValueError):
            first_rc = larch_io.read_kv(
                path=retry_sidecar,
                key="FIRST_RC",
                default="",
                duplicate_policy="last",
            ).strip()
        retry_msg = f"code-flow subprocess transient (rc={first_rc}); retried once"
        run_log_batch.append_execution_issue(
            log_file=implement_tmpdir / "execution-issues.md",
            category="Warnings",
            entry=f"- **Step 7a — code flow diagram**: {retry_msg}",
        )
        with contextlib.suppress(OSError):
            retry_sidecar.unlink()
    if result.status == "ok" and result.diagram_file:
        section = implement_tmpdir / "code-flow-section.md"
        section.write_text(
            (implement_tmpdir / "code-flow-diagram.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        return result
    _cleanup_diagram_artifacts(implement_tmpdir, keep_diagram=False)
    if result.exit_code == 0 and result.status != "failed":
        return result
    reason = result.reason or "generation failed"
    _append_diagram_warning(implement_tmpdir=implement_tmpdir, message=reason)
    return pr_body.CodeFlowDiagramResult(
        exit_code=result.exit_code,
        status="failed",
        diagram_file="",
        reason=reason,
    )


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
    return _run_step7a_inner(
        implement_tmpdir,
        issue_number=issue_number,
        run_id=run_id,
        no_logs_commit=no_logs_commit,
        forked_target=forked_target,
        base_remote=base_remote,
        base_ref=base_ref,
    )


def _run_step7a_inner(
    implement_tmpdir: Path,
    *,
    issue_number: str = "",
    run_id: str = "",
    no_logs_commit: bool = False,
    forked_target: bool = False,
    base_remote: str = "origin",
    base_ref: str = "main",
) -> int:
    _ = no_logs_commit  # Terminal publication suppression is owned by Step 18.
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
    _run_cli("token", "mark", "Step 7a — pre-ship")
    # lint-subprocess-via-runner: ok timing-mark needs LARCH_TIMING_SKILL env; _run_cli does not support custom env
    subprocess.run(
        [str(larch_entrypoint(Path(__file__).resolve().parents[3])), "timing", "mark", "Step 7a — pre-ship"],
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
        diagram_result = _generate_code_flow_diagram(
            implement_tmpdir,
            base_remote=base_remote,
            base_ref=base_ref,
        )
        diagram_status = diagram_result.status
        diagram_path = diagram_result.diagram_file
        diagram_reason = diagram_result.reason if diagram_status == "failed" else ""

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
    probe = rust_runtime.checkpoint_probe(
        proc,
        step_prefix="7a.r",
        short_name="diagrams",
        base_remote=base_remote,
        base_ref=base_ref,
    )
    rebase_out.write_text(probe.stdout, encoding="utf-8")
    for line in probe.stdout.splitlines():
        if line.strip():
            _emit_line(line)
    log_checkpoint_status = _checkpoint_execution_issues(implement_tmpdir, run_id=run_id)
    if probe.exit_code != 0:
        emit(key="DIAGRAM_STATUS", value=diagram_status)
        emit(key="DIAGRAM_REASON", value=diagram_reason)
        emit(key="DIAGRAM_PATH", value=diagram_path)
        emit(key="COMMENT_URL", value=comment_url)
        emit(key="LOG_CHECKPOINT_STATUS", value=log_checkpoint_status)
        emit(key="STEP_7A_BAIL_REASON", value=bail)
        emit(key="REBASE_OUTCOME", value="conflict" if probe.exit_code == 1 else "failed")
        return probe.exit_code

    rebase_outcome = "skipped"
    for line in probe.stdout.splitlines():
        if line.startswith("REBASE_OUTCOME="):
            rebase_outcome = line.partition("=")[2].strip() or "skipped"
    emit(key="DIAGRAM_STATUS", value=diagram_status)
    emit(key="DIAGRAM_REASON", value=diagram_reason)
    emit(key="DIAGRAM_PATH", value=diagram_path)
    emit(key="COMMENT_URL", value=comment_url)
    emit(key="LOG_CHECKPOINT_STATUS", value=log_checkpoint_status)
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
    parser.add_argument("--bgjob-launch", choices=("true", "false"), default="false")
    parser.add_argument("--bgjob-merge-result-env", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return _emit_arg_failure(bail_reason="argv")
    raw_tmpdir = args.implement_tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not raw_tmpdir:
        return _emit_arg_failure(bail_reason="missing-implement-tmpdir")
    if _has_symlink_ancestor(Path(raw_tmpdir)):
        return _emit_arg_failure(bail_reason="invalid-implement-tmpdir")
    if args.bgjob_launch == "true":
        return _launch_step7a_bgjob(
            Step7aBgjobLaunch(
                implement_tmpdir=Path(raw_tmpdir),
                issue_number=args.issue_number,
                run_id=args.run_id,
                no_logs_commit=args.no_logs_commit,
                forked_target=args.forked_target,
                base_remote=args.base_remote,
                base_ref=args.base_ref,
            )
        )
    merge_result_env = Path(args.bgjob_merge_result_env) if args.bgjob_merge_result_env else None
    with _result_env_capture(merge_result_env):
        return run_step7a(
            Path(raw_tmpdir),
            issue_number=args.issue_number,
            run_id=args.run_id,
            no_logs_commit=args.no_logs_commit == "true",
            forked_target=args.forked_target == "true",
            base_remote=args.base_remote,
            base_ref=args.base_ref,
        )


def _launch_step7a_bgjob(spec: Step7aBgjobLaunch) -> int:
    step = "implement-step7a"
    merge_result_env = spec.implement_tmpdir / "bgjob" / f"{step}.merge.env"
    merge_result_env.parent.mkdir(parents=True, exist_ok=True)
    larch_io.atomic_write(path=merge_result_env, text="", nofollow=True, mode=0o600)
    result = _run_cli(
        "bgjob",
        "start",
        "--step",
        step,
        "--tmpdir",
        str(spec.implement_tmpdir),
        "--budget-s",
        "1800",
        "--merge-result-env",
        str(merge_result_env),
        "--",
        sys.executable,
        str(plugin_root(Path(__file__).resolve().parents[3]) / "python" / "cli.py"),
        "implement",
        "step-7a",
        "--implement-tmpdir",
        str(spec.implement_tmpdir),
        "--issue-number",
        spec.issue_number,
        "--run-id",
        spec.run_id,
        "--no-logs-commit",
        spec.no_logs_commit,
        "--forked-target",
        spec.forked_target,
        "--base-remote",
        spec.base_remote,
        "--base-ref",
        spec.base_ref,
        "--bgjob-merge-result-env",
        str(merge_result_env),
    )
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode
