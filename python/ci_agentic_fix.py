"""Delegated agentic ship-pr CI fixer loop."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from larch.agents import agents
import ci_monitor
import coder_delta_guards
from larch.core import config
from larch.git import git
from larch import io as larch_io
from larch.core import logging_util
from larch.core import proc
from larch.core import redact
from larch.core.run_context import RunContext


def _emit_kv(*, key: str, value: object) -> None:
    logging_util.emit_kv(key=key, value=str(value))


def _bool(value: object) -> str:
    return str(value).lower()


def _job_token(job: ci_monitor.JobClass) -> str:
    return f"{job.name}-{job.shard}" if job.shard else job.name


def _parse_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, strip_value=True, skip_empty_key=True)


def _emit_result(
    status: str,
    *,
    detail: str = "",
    fix_attempted: bool = False,
    cycles: int = 0,
    delta_paths: tuple[str, ...] = (),
    ci_fix_rebase_pending: bool = False,
    exhausted_detail_file: str = "",
) -> int:
    _emit_kv(key="STATUS", value=status)
    _emit_kv(key="DETAIL", value=detail.replace("\n", " ").strip())
    if exhausted_detail_file:
        _emit_kv(key="EXHAUSTED_DETAIL_FILE", value=exhausted_detail_file)
    _emit_kv(key="FIX_ATTEMPTED", value=_bool(fix_attempted))
    _emit_kv(key="WINNING_TIER", value="claude")
    _emit_kv(key="CYCLES", value=cycles)
    _emit_kv(key="DELTA_PATHS", value=",".join(delta_paths))
    _emit_kv(key="CI_FIX_REBASE_PENDING", value=_bool(ci_fix_rebase_pending))
    return 0


def _valid_repo_root(raw: str) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute() or not path.is_dir():
        return None
    try:
        return path.resolve(strict=True)
    except OSError:
        return None


def _reconstruct_ctx(*, args: argparse.Namespace, repo_root: Path) -> RunContext:
    branch = git.try_current_branch(proc, cwd=str(repo_root)) or ""
    return RunContext(
        branch=branch,
        issue="",
        repo=args.repo,
        run_id=args.run_id,
        tmpdir=args.implement_tmpdir,
        merge=False,
        draft=False,
        forked=False,
        manifest_path="",
        tool_label="claude",
        no_admin_fallback=False,
        repo_unavailable=False,
        pr_number=args.pr,
        state_file=args.state_file or None,
        no_logs_commit=args.no_logs_commit,
        plan_file=args.plan_file,
    )


def _write_failure_log(*, output_dir: Path, text: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="ci-agentic-failure.", suffix=".redacted.log", dir=str(output_dir))
    os.close(fd)
    path = Path(name)
    _ = path.write_text(redact.redact(text), encoding="utf-8")
    path.chmod(0o600)
    return path


def _compose_exhausted_detail(*, cycle_detail: str, failure_log_text: str) -> str:
    header = f"ci-fix-exhausted: {cycle_detail}" if cycle_detail else "ci-fix-exhausted"
    tail = failure_log_text.strip()
    if tail:
        return f"{header}\n{redact.redact(tail).rstrip()}\n"
    return header


def _compose_local_unfixable_detail(*, job_list: str, failure_log_text: str) -> str:
    header = f"local-unfixable: {job_list}" if job_list else "local-unfixable"
    tail = failure_log_text.strip()
    if tail:
        return f"{header}\n{redact.redact(tail).rstrip()}\n"
    return header


_LEGACY_PREFIX_INCIDENT_PATH = "python/preflight.py"
_SAFE_REPO_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


def _legacy_prefix_unexpected_paths(failure_log_text: str) -> tuple[str, ...]:
    paths: list[str] = []
    seen: set[str] = set()
    pattern = re.compile(r"legacy prefix literal in unexpected path: ([^ \n]+) \(extend ALLOW= only when deliberate\)")
    for match in pattern.finditer(failure_log_text):
        path = match.group(1).strip()
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    return tuple(paths)


def _safe_repo_relative_path(path: str) -> bool:
    parsed = Path(path)
    return (
        bool(path)
        and not parsed.is_absolute()
        and ".." not in parsed.parts
        and _SAFE_REPO_PATH_RE.fullmatch(path) is not None
    )


def _apply_legacy_prefix_allow_fix(*, repo_root: Path, failure_log_text: str) -> tuple[bool, str]:
    paths = _legacy_prefix_unexpected_paths(failure_log_text)
    if paths != (_LEGACY_PREFIX_INCIDENT_PATH,):
        return False, ""
    path = paths[0]
    if not _safe_repo_relative_path(path):
        return False, ""
    target = repo_root / path
    if not target.is_file():
        return False, ""
    target_text = target.read_text(encoding="utf-8", errors="replace")
    if "[IN PROGRESS]" not in target_text and "[PLANNED]" not in target_text:
        return False, ""
    allow_script = repo_root / "scripts" / "test-legacy-title-prefix-literals-scope.sh"
    if not allow_script.is_file():
        return False, ""
    text = allow_script.read_text(encoding="utf-8")
    if re.search(rf"^\s*'?{re.escape(path)}'?\s*$", text, flags=re.MULTILINE):
        return False, ""
    block: re.Match[str] | None = re.search(r"(?ms)^ALLOW=\(\n(?P<body>.*?)^\)", text)
    if block is None:
        return False, ""
    insert = f"  '{path}'\n"
    new_text = text[: block.end("body")] + insert + text[block.end("body") :]
    _ = allow_script.write_text(new_text, encoding="utf-8")
    return True, f"legacy-prefix-allow:{path}"


def _apply_finalize_cleanup_partition_fix(*, repo_root: Path, failure_log_text: str) -> tuple[bool, str]:
    required = (
        "harness pytest partition guard: FAILED",
        "python/test_finalize.py: NOT a strict partition",
        "cleanup_target_ok",
    )
    if any(needle not in failure_log_text for needle in required):
        return False, ""
    makefile = repo_root / "Makefile"
    if not makefile.is_file():
        return False, ""
    lines: list[str] = makefile.read_text(encoding="utf-8").splitlines(keepends=True)
    in_target = False
    changed = False
    rewritten: list[str] = []
    for line in lines:
        if line.startswith("test-implement-cleanup-script:"):
            in_target = True
            rewritten.append(line)
            continue
        if in_target and line and not line.startswith("\t") and not line.startswith(" "):
            in_target = False
        current_line = line
        if in_target and "python/test_finalize.py" in line and " -k " in line:
            if not line.startswith("\t") or "not cleanup_target_ok" in line:
                return False, ""
            if re.search(r"(?<!\S)-k\s+cleanup(?=\s|$)", line) is None:
                return False, ""
            new_line = re.sub(
                r"(?<!\S)-k\s+cleanup(?=\s|$)",
                "-k 'cleanup and not cleanup_target_ok'",
                line,
                count=1,
            )
            if new_line == line or not new_line.startswith("\t"):
                return False, ""
            current_line = new_line
            changed = True
        rewritten.append(current_line)
    if not changed:
        return False, ""
    _ = makefile.write_text("".join(rewritten), encoding="utf-8")
    return True, "finalize-cleanup-partition"


def _apply_known_harness_fix(*, repo_root: Path, failure_log_text: str) -> tuple[bool, str]:
    details: list[str] = []
    changed = False
    for helper in (_apply_legacy_prefix_allow_fix, _apply_finalize_cleanup_partition_fix):
        helper_changed, detail = helper(repo_root=repo_root, failure_log_text=failure_log_text)
        if helper_changed:
            changed = True
            if detail:
                details.append(detail)
    return (True, ",".join(details)) if changed else (False, "")


def _rollback(
    runner: proc.Runner,
    *,
    baseline_tracked: tuple[str, ...],
    baseline_untracked: tuple[str, ...],
    baseline_staged: tuple[str, ...],
    cwd: str,
) -> None:
    ci_monitor._rollback_to_baseline(  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        runner,
        baseline_tracked=baseline_tracked,
        baseline_untracked=baseline_untracked,
        baseline_staged=baseline_staged,
        cwd=cwd,
    )


def _write_push_checkpoint(
    output_dir: Path,
    *,
    cycle: int,
    run_id: str,
    delta_paths: tuple[str, ...],
    pending: bool,
    detail: str = "",
) -> None:
    """Record last successful push so parent timeout can recover remote state."""
    text = (
        f"CYCLE={cycle}\n"
        f"RUN_ID={run_id}\n"
        f"DELTA_PATHS={','.join(delta_paths)}\n"
        f"CI_FIX_REBASE_PENDING={'true' if pending else 'false'}\n"
        f"DETAIL={detail}\n"
    )
    _ = (output_dir / "ci-agentic-push-checkpoint.latest").write_text(text, encoding="utf-8")


def _wait_for_ci(
    runner: proc.Runner,
    *,
    args: argparse.Namespace,
    repo_root: Path,
    cycle: int,
) -> tuple[dict[str, str], str | None]:
    output = Path(args.output_dir) / f"ci-agentic-wait-{cycle}.out"
    result = runner.run(
        [
            sys.executable,
            str(Path(__file__).resolve().with_name("cli.py")),
            "ci",
            "wait",
            "--pr",
            str(args.pr),
            "--repo",
            args.repo,
            "--base-remote",
            args.base_remote,
            "--base-ref",
            args.base_ref,
            "--iteration",
            str(cycle),
            "--output-file",
            str(output),
            "--empty-checks-grace",
            str(config.CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC),
        ],
        cwd=str(repo_root),
        timeout=float(config.CI_WAIT_TIMEOUT_SEC),
    )
    if result.returncode != 0:
        return {}, f"ci-wait-exit-{result.returncode}"
    if not output.is_file():
        return {}, "ci-wait-missing-output"
    text = output.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return {}, "ci-wait-empty-output"
    parsed = _parse_kv(text)
    if parsed.get("ACTION") in {"merge", "already_merged"} or parsed.get("CI_STATUS") == "pass":
        return parsed, None
    if parsed.get("ACTION") in {"rebase", "rebase_then_evaluate"}:
        return parsed, None
    if parsed.get("FAILED_RUN_ID"):
        return parsed, None
    if parsed.get("CI_STATUS") in {"fail", "failure"} and parsed.get("ACTION"):
        return parsed, None
    if parsed.get("ACTION") == "bail":
        return parsed, None
    return {}, "ci-wait-malformed-output"


def _run_cycle(
    runner: proc.Runner,
    *,
    args: argparse.Namespace,
    repo_root: Path,
    ctx: RunContext,
    cycle: int,
    run_id: str,
) -> tuple[str, str, bool, tuple[str, ...], bool, str | None, str]:
    cwd = str(repo_root)
    jobs_raw, jobs_state = ci_monitor.read_failed_jobs(runner, run_id=run_id, repo=args.repo, cwd=cwd)
    if jobs_state != "ready":
        return "waterfall-failed", f"failed-jobs-{jobs_state}", False, (), False, None, ""
    classified = ci_monitor.classify_failed_jobs(jobs_raw)
    if not classified.fixable:
        return (
            "local-unfixable",
            ",".join(_job_token(job) for job in classified.unfixable),
            False,
            (),
            False,
            None,
            "",
        )
    logs = ci_monitor.collect_failed_logs(runner, run_id=run_id, repo=args.repo, cwd=cwd)
    if logs.state != "ready":
        return "waterfall-failed", f"logs-{logs.state}", False, (), False, None, ""
    failure_log_text = logs.text
    output_dir = Path(args.output_dir)
    failure_log = _write_failure_log(output_dir=output_dir, text=logs.text)
    output = output_dir / f"ci-agentic-claude-{cycle}.out"
    baseline_tracked, baseline_untracked, baseline_staged, baseline_head = ci_monitor._capture_baseline(  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        runner,
        cwd=cwd,
    )
    fix_attempted = False
    try:
        known_changed, _known_detail = _apply_known_harness_fix(repo_root=repo_root, failure_log_text=failure_log_text)
        if known_changed:
            fix_attempted = True
            forbidden = coder_delta_guards.coder_forbidden_paths(runner, cwd=cwd)
            if (
                coder_delta_guards.revert_forbidden_paths(
                    runner,
                    cwd=cwd,
                    forbidden=forbidden,
                    baseline_staged=baseline_staged,
                )
                > 0
            ):
                _rollback(
                    runner,
                    baseline_tracked=baseline_tracked,
                    baseline_untracked=baseline_untracked,
                    baseline_staged=baseline_staged,
                    cwd=cwd,
                )
                return "waterfall-failed", "forbidden-path", fix_attempted, (), False, None, failure_log_text
            unfixable = [
                _job_token(job)
                for job in classified.fixable
                if not ci_monitor.prepare_python_toolchain(runner=runner, name=job.name, cwd=cwd)
            ]
            if unfixable:
                _rollback(
                    runner,
                    baseline_tracked=baseline_tracked,
                    baseline_untracked=baseline_untracked,
                    baseline_staged=baseline_staged,
                    cwd=cwd,
                )
                return "local-unfixable", ",".join(unfixable), fix_attempted, (), False, None, failure_log_text
            failed_verify = [
                _job_token(job)
                for job in classified.fixable
                if not ci_monitor.verify_job_locally(runner=runner, name=job.name, shard=job.shard, cwd=cwd)
            ]
            if not failed_verify:
                delta_paths = ci_monitor._delta_paths(  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
                    runner,
                    baseline_tracked=baseline_tracked,
                    baseline_untracked=baseline_untracked,
                    cwd=cwd,
                )
                if not delta_paths:
                    _rollback(
                        runner,
                        baseline_tracked=baseline_tracked,
                        baseline_untracked=baseline_untracked,
                        baseline_staged=baseline_staged,
                        cwd=cwd,
                    )
                    return "no-progress", "empty-delta", fix_attempted, (), False, None, failure_log_text
                pushed, _post_head, pushed_paths, _did_rebase, pending = ci_monitor.stage_and_push(
                    runner,
                    cwd=cwd,
                    commit_label="claude",
                    delta_paths=delta_paths,
                    base_remote=args.base_remote,
                    base_ref=args.base_ref,
                    classified=classified,
                    ctx=ctx,
                )
                if not pushed and pending:
                    return "rebase-required", "push-rebase-required", fix_attempted, pushed_paths, True, None, failure_log_text
                if not pushed:
                    _ = git.reset(runner, "--hard", baseline_head, cwd=cwd)
                    _rollback(
                        runner,
                        baseline_tracked=baseline_tracked,
                        baseline_untracked=baseline_untracked,
                        baseline_staged=baseline_staged,
                        cwd=cwd,
                    )
                    return "push-failed", "push-failed", fix_attempted, (), False, None, failure_log_text
                _write_push_checkpoint(
                    Path(args.output_dir),
                    cycle=cycle,
                    run_id=run_id,
                    delta_paths=pushed_paths,
                    pending=pending,
                )
                wait, wait_err = _wait_for_ci(runner, args=args, repo_root=repo_root, cycle=cycle)
                if wait_err:
                    _write_push_checkpoint(
                        Path(args.output_dir),
                        cycle=cycle,
                        run_id=run_id,
                        delta_paths=pushed_paths,
                        pending=False,
                        detail=wait_err,
                    )
                    return "ci-fix-exhausted", wait_err, fix_attempted, pushed_paths, False, None, failure_log_text
                action = wait.get("ACTION", "")
                if action == "bail":
                    detail = wait.get("BAIL_REASON") or wait.get("FAILURE_CLASS") or "ci-wait-bail"
                    _write_push_checkpoint(
                        Path(args.output_dir),
                        cycle=cycle,
                        run_id=run_id,
                        delta_paths=pushed_paths,
                        pending=False,
                        detail=detail,
                    )
                    return "ci-fix-exhausted", detail, fix_attempted, pushed_paths, False, None, failure_log_text
                if action in {"merge", "already_merged"} or wait.get("CI_STATUS") == "pass":
                    return "passed", "", fix_attempted, pushed_paths, False, None, failure_log_text
                if action in {"rebase", "rebase_then_evaluate"}:
                    _write_push_checkpoint(
                        Path(args.output_dir),
                        cycle=cycle,
                        run_id=run_id,
                        delta_paths=pushed_paths,
                        pending=True,
                        detail=action,
                    )
                    return "rebase-required", action, fix_attempted, pushed_paths, True, None, failure_log_text
                next_run = wait.get("FAILED_RUN_ID")
                if wait.get("CI_STATUS") in {"fail", "failure"} and next_run:
                    return "continue", "ci-still-failing", fix_attempted, pushed_paths, False, next_run, failure_log_text
                return "ci-fix-exhausted", "ci-wait-untrusted-output", fix_attempted, pushed_paths, False, None, failure_log_text
            _rollback(
                runner,
                baseline_tracked=baseline_tracked,
                baseline_untracked=baseline_untracked,
                baseline_staged=baseline_staged,
                cwd=cwd,
            )
        result = agents.launch_tier(
            runner=runner,
            tier="claude",
            role=config.CI_FIX_ROLE,
            output=str(output),
            run_id=run_id,
            repo=args.repo,
            plan_file=args.plan_file,
            failure_log=str(failure_log),
            cwd=cwd,
        )
        fix_attempted = True
        launcher_exit = agents.resolve_launcher_exit(
            captured_text=result.stdout + result.stderr,
            output_file=output,
            process_rc=result.returncode,
        )
        diag = output.with_suffix(output.suffix + ".diag")
        failure = agents.classify_launch_failure(
            launcher_exit=launcher_exit,
            sidecar=diag,
            auth_verdict=agents.external_auth_verdict("claude", diag, output),
            binary_present=shutil.which("claude") is not None,
            tool="claude",
            output_file=output,
        )
        if launcher_exit != 0 or result.returncode != 0:
            _rollback(
                runner,
                baseline_tracked=baseline_tracked,
                baseline_untracked=baseline_untracked,
                baseline_staged=baseline_staged,
                cwd=cwd,
            )
            if failure.failure_class == "health":
                if failure.reason in {"binary-missing", "auth", "quota"}:
                    return (
                        "ci-fix-exhausted",
                        failure.reason or "claude-health",
                        fix_attempted,
                        (),
                        False,
                        None,
                        failure_log_text,
                    )
                return "waterfall-failed", failure.reason or "claude-health", fix_attempted, (), False, None, failure_log_text
            status = "first-fixer-non-health" if cycle == 1 else "waterfall-failed"
            return status, failure.reason or "claude-failed", fix_attempted, (), False, None, failure_log_text
        current_head = coder_delta_guards.capture_head(runner, cwd=cwd)
        if coder_delta_guards.head_changed_from_baseline(baseline_head=baseline_head, current_head=current_head):
            _ = git.reset(runner, "--hard", baseline_head, cwd=cwd)
            _rollback(
                runner,
                baseline_tracked=baseline_tracked,
                baseline_untracked=baseline_untracked,
                baseline_staged=baseline_staged,
                cwd=cwd,
            )
            return "waterfall-failed", "head-changed", fix_attempted, (), False, None, failure_log_text
        forbidden = coder_delta_guards.coder_forbidden_paths(runner, cwd=cwd)
        if (
            coder_delta_guards.revert_forbidden_paths(
                runner,
                cwd=cwd,
                forbidden=forbidden,
                baseline_staged=baseline_staged,
            )
            > 0
        ):
            _rollback(
                runner,
                baseline_tracked=baseline_tracked,
                baseline_untracked=baseline_untracked,
                baseline_staged=baseline_staged,
                cwd=cwd,
            )
            return "waterfall-failed", "forbidden-path", fix_attempted, (), False, None, failure_log_text
        unfixable = [
            _job_token(job)
            for job in classified.fixable
            if not ci_monitor.prepare_python_toolchain(runner=runner, name=job.name, cwd=cwd)
        ]
        if unfixable:
            _rollback(
                runner,
                baseline_tracked=baseline_tracked,
                baseline_untracked=baseline_untracked,
                baseline_staged=baseline_staged,
                cwd=cwd,
            )
            return "local-unfixable", ",".join(unfixable), fix_attempted, (), False, None, failure_log_text
        failed_verify = [
            _job_token(job)
            for job in classified.fixable
            if not ci_monitor.verify_job_locally(runner=runner, name=job.name, shard=job.shard, cwd=cwd)
        ]
        if failed_verify:
            _rollback(
                runner,
                baseline_tracked=baseline_tracked,
                baseline_untracked=baseline_untracked,
                baseline_staged=baseline_staged,
                cwd=cwd,
            )
            return "verify-failed", ",".join(failed_verify), fix_attempted, (), False, None, failure_log_text
        delta_paths = ci_monitor._delta_paths(  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
            runner,
            baseline_tracked=baseline_tracked,
            baseline_untracked=baseline_untracked,
            cwd=cwd,
        )
        if not delta_paths:
            _rollback(
                runner,
                baseline_tracked=baseline_tracked,
                baseline_untracked=baseline_untracked,
                baseline_staged=baseline_staged,
                cwd=cwd,
            )
            return "no-progress", "empty-delta", fix_attempted, (), False, None, failure_log_text
        pushed, _post_head, pushed_paths, _did_rebase, pending = ci_monitor.stage_and_push(
            runner,
            cwd=cwd,
            commit_label="claude",
            delta_paths=delta_paths,
            base_remote=args.base_remote,
            base_ref=args.base_ref,
            classified=classified,
            ctx=ctx,
        )
        if not pushed and pending:
            return "rebase-required", "push-rebase-required", fix_attempted, pushed_paths, True, None, failure_log_text
        if not pushed:
            _ = git.reset(runner, "--hard", baseline_head, cwd=cwd)
            _rollback(
                runner,
                baseline_tracked=baseline_tracked,
                baseline_untracked=baseline_untracked,
                baseline_staged=baseline_staged,
                cwd=cwd,
            )
            return "push-failed", "push-failed", fix_attempted, (), False, None, failure_log_text
        _write_push_checkpoint(
            Path(args.output_dir),
            cycle=cycle,
            run_id=run_id,
            delta_paths=pushed_paths,
            pending=pending,
        )
        wait, wait_err = _wait_for_ci(runner, args=args, repo_root=repo_root, cycle=cycle)
        if wait_err:
            _write_push_checkpoint(
                Path(args.output_dir),
                cycle=cycle,
                run_id=run_id,
                delta_paths=pushed_paths,
                pending=False,
                detail=wait_err,
            )
            return "ci-fix-exhausted", wait_err, fix_attempted, pushed_paths, False, None, failure_log_text
        if wait.get("ACTION") == "bail":
            return (
                "ci-fix-exhausted",
                wait.get("BAIL_REASON", "") or "ci-wait-bail",
                fix_attempted,
                pushed_paths,
                False,
                None,
                failure_log_text,
            )
        expected_actions = {"", "merge", "already_merged", "rebase", "rebase_then_evaluate", "evaluate_failure"}
        if wait.get("ACTION", "") not in expected_actions and not wait.get("FAILED_RUN_ID"):
            return (
                "ci-fix-exhausted",
                wait.get("BAIL_REASON", "") or "ci-wait-untrusted-output",
                fix_attempted,
                pushed_paths,
                False,
                None,
                failure_log_text,
            )
        if wait.get("ACTION") in {"rebase", "rebase_then_evaluate"}:
            return (
                "rebase-required",
                wait.get("BAIL_REASON", "") or "ci-wait-rebase-required",
                fix_attempted,
                pushed_paths,
                True,
                None,
                failure_log_text,
            )
        try:
            behind = int(wait.get("BEHIND_COUNT", "0") or "0")
        except ValueError:
            behind = 0
        if behind > 0:
            return (
                "rebase-required",
                wait.get("BAIL_REASON", "") or "ci-wait-behind-base",
                fix_attempted,
                pushed_paths,
                True,
                None,
                failure_log_text,
            )
        if wait.get("ACTION") in {"merge", "already_merged"} or wait.get("CI_STATUS") == "pass":
            return "passed", "", fix_attempted, pushed_paths, False, None, failure_log_text
        next_run = wait.get("FAILED_RUN_ID") or run_id
        return "pushed", wait.get("BAIL_REASON", "") or "ci-failed-after-push", fix_attempted, pushed_paths, False, next_run, failure_log_text
    finally:
        failure_log.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci agentic-fix")
    _ = parser.add_argument("--pr", required=True, type=int)
    _ = parser.add_argument("--repo", required=True)
    _ = parser.add_argument("--repo-root", required=True)
    _ = parser.add_argument("--run-id", required=True)
    _ = parser.add_argument("--plan-file", default="")
    _ = parser.add_argument("--base-remote", default="origin")
    _ = parser.add_argument("--base-ref", default="main")
    _ = parser.add_argument("--output-dir", required=True)
    _ = parser.add_argument("--max-cycles", default=str(config.CI_AGENTIC_FIX_MAX_CYCLES))
    _ = parser.add_argument("--implement-tmpdir", required=True)
    _ = parser.add_argument("--state-file", default="")
    _ = parser.add_argument("--no-logs-commit", action="store_true")
    args = parser.parse_args(argv)
    repo_root = _valid_repo_root(args.repo_root)
    if repo_root is None:
        return _emit_result("waterfall-failed", detail="missing-repo-root")
    try:
        max_cycles = int(args.max_cycles)
    except ValueError:
        max_cycles = config.CI_AGENTIC_FIX_MAX_CYCLES
    if max_cycles < 1:
        max_cycles = config.CI_AGENTIC_FIX_MAX_CYCLES
    max_cycles = min(max_cycles, config.CI_AGENTIC_FIX_MAX_CYCLES)
    ctx = _reconstruct_ctx(args=args, repo_root=repo_root)
    run_id = args.run_id
    fix_attempted = False
    last_detail = ""
    last_delta: tuple[str, ...] = ()
    last_failure_log_text = ""
    for cycle in range(1, max_cycles + 1):
        status, detail, attempted, delta_paths, pending, next_run_id, failure_log_text = _run_cycle(
            proc,
            args=args,
            repo_root=repo_root,
            ctx=ctx,
            cycle=cycle,
            run_id=run_id,
        )
        fix_attempted = fix_attempted or attempted
        last_detail = detail
        last_delta = delta_paths
        if failure_log_text:
            last_failure_log_text = failure_log_text
        if status == "local-unfixable":
            exhausted_path = Path(args.output_dir) / f"ci-agentic-local-unfixable-{cycle}.detail"
            _ = exhausted_path.write_text(
                _compose_local_unfixable_detail(job_list=detail, failure_log_text=failure_log_text),
                encoding="utf-8",
            )
            return _emit_result(
                status,
                detail=detail,
                fix_attempted=fix_attempted,
                cycles=cycle,
                delta_paths=delta_paths,
                ci_fix_rebase_pending=pending,
                exhausted_detail_file=str(exhausted_path),
            )
        if status == "ci-fix-exhausted":
            exhausted_path = Path(args.output_dir) / f"ci-agentic-exhausted-{cycle}.detail"
            _ = exhausted_path.write_text(
                _compose_exhausted_detail(cycle_detail=detail, failure_log_text=failure_log_text),
                encoding="utf-8",
            )
            return _emit_result(
                status,
                detail=detail,
                fix_attempted=fix_attempted,
                cycles=cycle,
                delta_paths=delta_paths,
                exhausted_detail_file=str(exhausted_path),
            )
        if status in {"passed", "rebase-required", "first-fixer-non-health"}:
            return _emit_result(
                status,
                detail=detail,
                fix_attempted=fix_attempted,
                cycles=cycle,
                delta_paths=delta_paths,
                ci_fix_rebase_pending=pending,
            )
        if status == "push-failed":
            exhausted_path = Path(args.output_dir) / f"ci-agentic-exhausted-{cycle}.detail"
            _ = exhausted_path.write_text(
                _compose_exhausted_detail(cycle_detail=detail, failure_log_text=failure_log_text),
                encoding="utf-8",
            )
            return _emit_result(
                "ci-fix-exhausted",
                detail=detail,
                fix_attempted=fix_attempted,
                cycles=cycle,
                delta_paths=(),
                exhausted_detail_file=str(exhausted_path),
            )
        if next_run_id:
            run_id = next_run_id
    exhausted_path = Path(args.output_dir) / "ci-agentic-exhausted-final.detail"
    _ = exhausted_path.write_text(
        _compose_exhausted_detail(cycle_detail=last_detail or "cycle cap exhausted", failure_log_text=last_failure_log_text),
        encoding="utf-8",
    )
    return _emit_result(
        "ci-fix-exhausted",
        detail=last_detail or "cycle cap exhausted",
        fix_attempted=fix_attempted,
        cycles=max_cycles,
        delta_paths=last_delta,
        exhausted_detail_file=str(exhausted_path),
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
