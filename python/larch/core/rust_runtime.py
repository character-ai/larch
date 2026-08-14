"""Typed consumers of commands owned by the installed Rust runtime."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io
from larch.core import config
from larch.core.proc import CommandResult, ProcRunner, Runner
from larch.core.repo_roots import larch_entrypoint
from larch.core.run_context import RunContext


@dataclass(frozen=True)
class PhantomProbeOutput:
    """Validated advisory output from the Rust phantom-probe owner."""

    lines: tuple[str, ...]


@dataclass(frozen=True)
class DirtyTreeOutput:
    """Validated result rows from a Rust-owned dirty-tree command."""

    lines: tuple[str, ...]


@dataclass(frozen=True)
class DirtyTreeRequest:
    """One validated Rust dirty-tree invocation contract."""

    command: str
    arguments: tuple[str, ...]
    mode: str
    fallback: tuple[str, ...]


@dataclass(frozen=True)
class PushOutput:
    """Validated result from the Rust-owned branch push command."""

    status: str
    branch: str = ""


@dataclass(frozen=True)
class IssueStateOutput:
    """Validated result from the Rust-owned ``issue state`` command.

    ``failed`` is the caller's only success test: a refused read emits the
    ``FAILED=true`` envelope with no state rows, and a missing envelope is
    treated the same way, so an unusable read never reads as an open issue.
    """

    failed: bool
    state: str = ""
    url: str = ""
    is_pr: bool = False


@dataclass(frozen=True)
class TrackingIssueCommentOutput:
    """Validated comment result from the Rust tracking-issue owner."""

    failed: bool
    comment_id: str = ""
    comment_url: str = ""
    updated: bool = False
    error: str = ""


@dataclass(frozen=True)
class TrackingIssueCreateOutput:
    """Validated create result from the Rust tracking-issue owner."""

    failed: bool
    issue_number: str = ""
    issue_url: str = ""
    error: str = ""


@dataclass(frozen=True)
class TrackingIssueTitleOutput:
    """Validated title result from the Rust tracking-issue owner."""

    failed: bool
    changed: bool = False
    new_title: str = ""
    error: str = ""


@dataclass(frozen=True)
class TrackingIssueReadOutput:
    """Validated read result from the Rust tracking-issue owner."""

    failed: bool
    values: Mapping[str, str]
    error: str = ""


@dataclass(frozen=True)
class TrackingIssueSentinelOutput:
    """Validated local sentinel result from the Rust tracking-issue reader."""

    failed: bool
    issue_number: str = ""
    run_id: str = ""
    adopted: str = ""
    error: str = ""


@dataclass(frozen=True)
class ExecutionIssuesAppendOutput:
    """Validated result from the Rust execution-issue append owner."""

    failed: bool
    status: str = ""
    error: str = ""


@dataclass(frozen=True)
class ExecutionIssuesFlushOutput:
    """Validated result from one Rust execution-issue flush boundary."""

    failed: bool
    status: str = ""
    records: int = 0
    append_log_file: str = ""
    error: str = ""


@dataclass(frozen=True)
class ExecutionIssuesRefreshOutput:
    """Validated result from the Rust execution-issue refresh owner."""

    failed: bool
    refreshed: bool = False
    reason: str = ""
    error: str = ""


@dataclass(frozen=True)
class IssueParsedItem:
    """One item published by the Rust-owned ``issue parse-input`` command."""

    title: str
    body_file: str = ""
    reviewer: str = ""
    vote: str = ""
    phase: str = ""
    malformed: bool = False


@dataclass(frozen=True)
class IssueParseInputOutput:
    """Validated result from the Rust-owned ``issue parse-input`` command.

    ``exit_code`` is the caller's only success test. A refused parse, a missing
    ``ITEMS_TOTAL`` row, and a row count that disagrees with it are all reported
    as a failure with no items, so a partial parse never reaches a filing loop.
    """

    items: tuple[IssueParsedItem, ...] = ()
    exit_code: int = 0
    error: str = ""


@dataclass(frozen=True)
class IssueCreateOutput:
    """Validated result from the Rust-owned ``issue create-one`` command.

    ``exit_code`` is the caller's only success test: every refusal publishes
    ``ISSUE_FAILED=true`` with a non-zero code, and a zero exit that carries no
    issue number is treated as a failure too, so a partial envelope never reads
    as a filed issue.
    """

    exit_code: int = 0
    number: str = ""
    url: str = ""
    issue_id: str = ""
    title: str = ""
    error: str = ""


@dataclass(frozen=True)
class IssueEdgeOutput:
    """Validated result from a Rust-owned issue-graph write.

    ``added`` is the caller's only success test: every refusal publishes its
    ``*_FAILED=true`` row with a non-zero code, and a zero exit that carries no
    added row is treated as a failure too, so an unproven edge never reads as
    an applied one.
    """

    added: bool = False
    exit_code: int = 0
    error: str = ""


@dataclass(frozen=True)
class CheckpointProbeOutput:
    """Parsed result from the Rust-owned ``push checkpoint-probe`` command.

    ``routing`` holds the ``KEY=value`` rebase-routing rows; ``advisory_lines``
    holds the trailing ``PHANTOM_*`` phantom-probe rows. The split mirrors the
    retired Python ``CheckpointProbeResult`` so consumers keep their contract.
    """

    exit_code: int
    stdout: str
    stderr: str
    routing: dict[str, str]
    advisory_lines: tuple[str, ...]


@dataclass(frozen=True)
class RunLogRefreshOutput:
    """Validated result from the Rust-owned mutable run-log refresh."""

    skipped: bool
    reason: str
    error: str = ""


def _run_log_refresh_args(
    ctx: RunContext,
    *,
    strict_final_report: bool = False,
    postmerge: bool = False,
    merge_result: str = "",
    render_reports: bool = True,
) -> list[str]:
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "run-log",
        "refresh",
        "--implement-tmpdir",
        ctx.tmpdir,
        "--run-id",
        ctx.run_id,
        "--no-logs-commit",
        "true" if ctx.no_logs_commit else "false",
        "--forked-target",
        "true" if ctx.forked else "false",
        "--stall-tracking",
        "true" if ctx.stall_tracking else "false",
    ]
    for option, value in (
        ("--state-file", ctx.state_file or ""),
        (
            "--merge-result",
            merge_result or ("" if ctx.state_file else ctx.merge_result),
        ),
        ("--stall-step", ctx.stall_step),
        ("--pr-number", str(ctx.pr_number or "")),
    ):
        if value:
            argv.extend([option, value])
    if strict_final_report:
        argv.extend(["--strict-final-report", "true"])
    if postmerge:
        argv.extend([
            "--postmerge", "true",
            "--render-reports", "true" if render_reports else "false",
        ])
    return argv


def _refresh_skip_from_result(result: CommandResult) -> RunLogRefreshOutput:
    returncode: int = result.returncode
    stdout: str = result.stdout
    stderr: str = result.stderr
    tokens: dict[str, str] = larch_io.parse_kv(
        "\n".join(stdout.split()),
        skip_empty_key=True,
        allowed_keys={"REFRESH_COMMITTED", "REFRESH_SKIPPED", "REASON"},
    )
    if returncode == 0 and tokens.get("REFRESH_COMMITTED") == "true":
        return RunLogRefreshOutput(skipped=False, reason="")
    reason: str = tokens.get("REASON", "manifest-recovery-failed")
    error: str = stdout.partition(" ERROR=")[2].strip()
    if returncode != 0 or "REASON" not in tokens:
        error = error or " ".join((stderr or stdout).split())[:500]
    return RunLogRefreshOutput(skipped=True, reason=reason, error=error)


def refresh_logs_checkpoint(
    runner: Runner,
    *,
    ctx: RunContext,
    cwd: str | None = None,
    strict_final_report: bool = False,
) -> RunLogRefreshOutput:
    """Refresh mutable run-log artifacts through their Rust owner."""
    result: CommandResult = runner.run(
        _run_log_refresh_args(ctx, strict_final_report=strict_final_report),
        cwd=cwd,
    )
    return _refresh_skip_from_result(result)


def refresh_postmerge_snapshot(
    ctx: RunContext,
    *,
    merge_result: str | None = None,
    runner: Runner | None = None,
) -> RunLogRefreshOutput:
    """Refresh the post-merge snapshot through the same Rust flush owner."""
    active_runner: Runner = runner or ProcRunner()
    result: CommandResult = active_runner.run(
        _run_log_refresh_args(
            ctx,
            postmerge=True,
            merge_result=merge_result or "",
            render_reports=runner is not None,
        )
    )
    return _refresh_skip_from_result(result)


def finalize_postmerge_logs(
    ctx: RunContext,
    *,
    merge_result: str | None = None,
    runner: Runner | None = None,
) -> RunLogRefreshOutput:
    """Finalize post-merge logs through the Rust refresh owner."""
    return refresh_postmerge_snapshot(ctx, merge_result=merge_result, runner=runner)


_STALL_OUTCOME_KEYS = frozenset({
    "IMPLEMENT_NORMALIZED_OUTCOME",
    "IMPLEMENT_OUTCOME_SUCCEEDED",
    "IMPLEMENT_MERGE_DOWNGRADED",
    "IMPLEMENT_ANY_STALL_TRACKING",
    "IMPLEMENT_MEMORY_STALL_TRACKING",
    "IMPLEMENT_SHIP_STALL_TRACKING",
    "IMPLEMENT_FINALIZE_STALL_TRACKING",
    "IMPLEMENT_SESSION_STALL_TRACKING",
    "IMPLEMENT_MERGE_RESULT",
    "IMPLEMENT_PR_NUMBER",
    "IMPLEMENT_DRAFT",
    "IMPLEMENT_MERGE",
    "IMPLEMENT_FORKED_TARGET",
    "IMPLEMENT_CI_PASSED",
    "IMPLEMENT_DESIGN_ONLY_DONE",
    "IMPLEMENT_BAIL_NEEDS_USER_INPUT",
})


def normalized_stall_outcome_values(
    runner: Runner,
    *,
    implement_tmpdir: str,
    in_memory_stall_tracking: str = "",
) -> dict[str, str]:
    """Invoke the Rust outcome owner and validate its fixed KV envelope."""
    argv = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "stall-recovery",
        "normalize-outcome",
        "--implement-tmpdir",
        implement_tmpdir,
    ]
    if in_memory_stall_tracking:
        argv.extend(["--in-memory-stall-tracking", in_memory_stall_tracking])
    result = runner.run(argv)
    parsed = larch_io.parse_kv(result.stdout, skip_empty_key=True)
    if result.returncode != 0 or "IMPLEMENT_NORMALIZED_OUTCOME" not in parsed:
        return {}
    return {key: value for key, value in parsed.items() if key in _STALL_OUTCOME_KEYS}


@dataclass(frozen=True)
class FinalReportOutput:
    """Validated envelope from the Rust-owned ``final-report write`` command."""

    exit_code: int
    comment_url: str = ""
    error: str = ""


def final_report_write(
    runner: Runner,
    *,
    implement_tmpdir: str,
    comment_only: bool = False,
    print_stdout: bool = False,
    skip_tracking_upsert: bool = False,
) -> FinalReportOutput:
    """Invoke the Rust final-report owner and validate its fixed KV envelope."""
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "final-report",
        "write",
        "--implement-tmpdir",
        implement_tmpdir,
    ]
    for flag, enabled in (
        ("--comment-only", comment_only),
        ("--print-stdout", print_stdout),
        ("--skip-tracking-upsert", skip_tracking_upsert),
    ):
        if enabled:
            argv.append(flag)
    result = runner.run(argv)
    parsed = larch_io.parse_kv(result.stdout, skip_empty_key=True)
    return FinalReportOutput(
        exit_code=result.returncode,
        comment_url=parsed.get("COMMENT_URL", ""),
        error=parsed.get("ERROR", ""),
    )


def checkpoint_probe(  # noqa: PLR0913 - mirrors the checkpoint-probe CLI arg surface (step, name, forked, base) plus the injected runner
    runner: Runner,
    *,
    step_prefix: str,
    short_name: str,
    forked_target: str = "false",
    base_remote: str | None = None,
    base_ref: str | None = None,
    cwd: str | None = None,
) -> CheckpointProbeOutput:
    """Invoke the Rust checkpoint-probe owner and split routing from phantom advisory."""
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "push",
        "checkpoint-probe",
        step_prefix,
        short_name,
        "--forked-target",
        forked_target,
    ]
    if base_remote is not None:
        argv.extend(["--base-remote", base_remote])
    if base_ref is not None:
        argv.extend(["--base-ref", base_ref])
    result = runner.run(argv, cwd=cwd)
    routing: dict[str, str] = {}
    advisory: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        if line.startswith("PHANTOM_"):
            advisory.append(line)
        elif "=" in line:
            key, _, value = line.partition("=")
            routing[key] = value
        else:
            advisory.append(line)
    return CheckpointProbeOutput(
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        routing=routing,
        advisory_lines=tuple(advisory),
    )


def phantom_probe(runner: Runner, *, step: str, cwd: str | None = None) -> PhantomProbeOutput:
    """Invoke the Rust owner and fail closed when its KV envelope is absent."""
    result = runner.run(
        [str(larch_entrypoint(Path(__file__).resolve().parents[3])), "git", "phantom-probe", "--step", step],
        cwd=cwd,
    )
    lines = tuple(line for line in result.stdout.splitlines() if line)
    if result.returncode != 0 or not any(line.startswith("PHANTOM_STATUS=") for line in lines):
        return PhantomProbeOutput(
            lines=("PHANTOM_STATUS=unknown", "PHANTOM_REASON=phantom-probe-failed"),
        )
    return PhantomProbeOutput(lines=lines)


def dirty_tree_checkpoint(runner: Runner, *, cwd: str | None = None) -> DirtyTreeOutput:
    """Invoke the Rust checkpoint owner and fail closed without a status envelope."""
    return _dirty_tree(
        runner,
        DirtyTreeRequest(
            command="checkpoint",
            arguments=(),
            mode="checkpoint",
            fallback=("STATUS=unknown", "MODE=checkpoint", "REASON=dirty-tree-checkpoint-failed"),
        ),
        cwd=cwd,
    )


def dirty_tree_baseline(
    runner: Runner,
    *,
    baseline_path: str,
    sidecar: str = "",
    cwd: str | None = None,
) -> DirtyTreeOutput:
    """Invoke the Rust baseline owner and retain its byte-path sidecar contract."""
    arguments = ["--baseline", baseline_path]
    if sidecar:
        arguments.extend(["--sidecar", sidecar])
    baseline_state = "present" if Path(baseline_path).is_file() else "missing"
    return _dirty_tree(
        runner,
        DirtyTreeRequest(
            command="baseline",
            arguments=tuple(arguments),
            mode="baseline",
            fallback=(
                "STATUS=unknown",
                "MODE=baseline",
                f"UNTRACKED_BASELINE={baseline_state}",
                "REASON=dirty-tree-baseline-failed",
            ),
        ),
        cwd=cwd,
    )


def _dirty_tree(
    runner: Runner,
    request: DirtyTreeRequest,
    *,
    cwd: str | None,
) -> DirtyTreeOutput:
    result = runner.run(
        [
            str(larch_entrypoint(Path(__file__).resolve().parents[3])),
            "dirty-tree",
            request.command,
            *request.arguments,
        ],
        cwd=cwd,
    )
    lines = tuple(line for line in result.stdout.splitlines() if line)
    if result.returncode != 0 or f"MODE={request.mode}" not in lines or not any(
        line.startswith("STATUS=") for line in lines
    ):
        return DirtyTreeOutput(lines=request.fallback)
    return DirtyTreeOutput(lines=lines)


def push_branch(runner: Runner, *, cwd: str | None = None) -> PushOutput:
    """Invoke the Rust owner and require its success KV contract."""
    result = runner.run(
        [str(larch_entrypoint(Path(__file__).resolve().parents[3])), "push", "branch"],
        cwd=cwd,
    )
    values = larch_io.parse_kv(result.stdout, skip_empty_key=True)
    if result.returncode != 0:
        return PushOutput(status="failed", branch=values.get("BRANCH", ""))
    branch = values.get("BRANCH", "")
    if not branch:
        return PushOutput(status="failed")
    return PushOutput(status="pushed", branch=branch)


def issue_state(
    runner: Runner,
    *,
    issue: str,
    repo: str | None = None,
    cwd: str | None = None,
) -> IssueStateOutput:
    """Invoke the Rust owner and fail closed without its state envelope."""
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "issue",
        "state",
        "--issue",
        issue,
    ]
    if repo:
        argv.extend(["--repo", repo])
    result = runner.run(argv, cwd=cwd)
    values: dict[str, str] = larch_io.parse_kv(result.stdout, skip_empty_key=True)
    if result.returncode != 0 or values.get("FAILED") == "true" or "STATE" not in values:
        return IssueStateOutput(failed=True)
    return IssueStateOutput(
        failed=False,
        state=values.get("STATE", ""),
        url=values.get("URL", ""),
        is_pr=values.get("IS_PR", "") == "true",
    )


def _execution_issues_run(
    runner: Runner,
    *,
    verb: str,
    arguments: Sequence[str],
    cwd: str | None = None,
) -> tuple[CommandResult, dict[str, str], bool]:
    """Invoke one execution-issue verb and reject ambiguous KV envelopes."""
    result = runner.run(
        [
            str(larch_entrypoint(Path(__file__).resolve().parents[3])),
            "execution-issues",
            verb,
            *arguments,
        ],
        cwd=cwd,
    )
    rows = larch_io.parse_kv(
        result.stdout, duplicate_policy="all", skip_empty_key=True
    )
    malformed_line = any(
        "=" not in line or not line.split("=", 1)[0]
        for line in result.stdout.splitlines()
    )
    malformed = malformed_line or any(len(values) != 1 for values in rows.values())
    return result, {key: values[0] for key, values in rows.items() if values}, malformed


def _execution_issues_error(result: CommandResult, values: Mapping[str, str]) -> str:
    return (
        values.get("ERROR", "")
        or " ".join((result.stderr or result.stdout).split())[:500]
        or "invalid execution-issues envelope"
    )


def execution_issues_append(  # noqa: PLR0913 - mirrors the Rust execution-issues append option surface
    runner: Runner,
    *,
    log: str,
    category: str,
    entry: str,
    existing_batch: str = "",
    redact_entry: bool = False,
    cwd: str | None = None,
) -> ExecutionIssuesAppendOutput:
    """Append category-keyed Markdown chunks through ``scripts/larch.sh``."""
    arguments = [
        "--log",
        log,
        "--category",
        category,
        "--entry",
        entry,
        "--report-status",
        "--spaced-section",
    ]
    if existing_batch:
        arguments.extend(["--existing-batch", existing_batch])
    if redact_entry:
        arguments.append("--redact")
    result, values, malformed = _execution_issues_run(
        runner, verb="append", arguments=arguments, cwd=cwd
    )
    status = values.get("APPEND_STATUS", "")
    failed = (
        result.returncode != 0
        or malformed
        or set(values) != {"APPEND_STATUS"}
        or status not in {"appended", "duplicate"}
    )
    return ExecutionIssuesAppendOutput(
        failed=failed,
        status=status,
        error=(
            _execution_issues_error(result, values)
            if failed and result.returncode != 0
            else "invalid execution-issues envelope" if failed else ""
        ),
    )


def _execution_issues_flush(  # noqa: PLR0913 - owns one typed process envelope
    runner: Runner,
    *,
    verb: str,
    log_root: str,
    run_id: str,
    issue_log: str = "",
    batch: str = "execution-issues",
    step_label: str = "",
    source_label: str = "",
    record_file: str = "",
    cwd: str | None = None,
) -> ExecutionIssuesFlushOutput:
    arguments = ["--log-root", log_root, "--run-id", run_id]
    for option, value in (
        ("--issue-log", issue_log),
        ("--step-label", step_label),
        ("--source-label", source_label),
        ("--record-file", record_file),
    ):
        if value:
            arguments.extend([option, value])
    if batch != "execution-issues":
        arguments.extend(["--batch", batch])
    result, values, malformed = _execution_issues_run(
        runner, verb=verb, arguments=arguments, cwd=cwd
    )
    status = values.get("FLUSH_STATUS", "")
    records_text = values.get("RECORDS", "")
    allowed = {"FLUSH_STATUS", "RECORDS", "APPEND_LOG_FILE", "ERROR"}
    failed = (
        result.returncode != 0
        or malformed
        or not set(values).issubset(allowed)
        or not {"FLUSH_STATUS", "RECORDS"}.issubset(values)
        or status
        not in {"skip", "already-flushed", "no-records", "ok", "rendered"}
        or not records_text.isascii()
        or not records_text.isdigit()
        or (status in {"skip", "already-flushed", "no-records"} and records_text != "0")
        or (status == "ok" and records_text == "0")
        or "ERROR" in values
    )
    return ExecutionIssuesFlushOutput(
        failed=failed,
        status=status,
        records=int(records_text) if records_text.isascii() and records_text.isdigit() else 0,
        append_log_file=values.get("APPEND_LOG_FILE", ""),
        error=_execution_issues_error(result, values) if failed else "",
    )


def execution_issues_flush(  # noqa: PLR0913 - mirrors the Rust execution-issues flush option surface
    runner: Runner,
    *,
    log_root: str,
    run_id: str,
    issue_log: str = "",
    batch: str = "execution-issues",
    step_label: str = "",
    source_label: str = "",
    cwd: str | None = None,
) -> ExecutionIssuesFlushOutput:
    """Publish and clear one execution-issue ledger through Rust."""
    return _execution_issues_flush(
        runner,
        verb="flush",
        log_root=log_root,
        run_id=run_id,
        issue_log=issue_log,
        batch=batch,
        step_label=step_label,
        source_label=source_label,
        cwd=cwd,
    )


def execution_issues_flush_safety_net(  # noqa: PLR0913 - mirrors the Rust execution-issues safety-net option surface
    runner: Runner,
    *,
    log_root: str,
    run_id: str,
    issue_log: str = "",
    batch: str = "execution-issues",
    step_label: str = "",
    source_label: str = "",
    record_file: str = "",
    cwd: str | None = None,
) -> ExecutionIssuesFlushOutput:
    """Publish without clearing, or render records, through Rust."""
    return _execution_issues_flush(
        runner,
        verb="flush-safety-net",
        log_root=log_root,
        run_id=run_id,
        issue_log=issue_log,
        batch=batch,
        step_label=step_label,
        source_label=source_label,
        record_file=record_file,
        cwd=cwd,
    )


def execution_issues_refresh(
    runner: Runner,
    *,
    implement_tmpdir: str,
    best_effort: bool = False,
    cwd: str | None = None,
) -> ExecutionIssuesRefreshOutput:
    """Refresh the run metadata projection through the Rust owner."""
    arguments = ["--implement-tmpdir", implement_tmpdir]
    if best_effort:
        arguments.append("--best-effort")
    result, values, malformed = _execution_issues_run(
        runner, verb="refresh", arguments=arguments, cwd=cwd
    )
    refreshed = values.get("REFRESHED", "")
    allowed = {"REFRESHED", "REASON", "ERROR"}
    valid_detail = not ({"REASON", "ERROR"} <= set(values))
    failed = (
        result.returncode != 0
        or malformed
        or not set(values).issubset(allowed)
        or refreshed not in {"true", "false"}
        or not valid_detail
        or (refreshed == "true" and "ERROR" in values)
        or (refreshed == "false" and not values.get("ERROR"))
        or refreshed == "false"
    )
    return ExecutionIssuesRefreshOutput(
        failed=failed,
        refreshed=refreshed == "true" and not failed,
        reason=values.get("REASON", ""),
        error=_execution_issues_error(result, values) if failed else "",
    )


def _tracking_issue_run(  # noqa: PLR0913 - owns one typed process envelope
    runner: Runner,
    *,
    verb: str,
    arguments: Sequence[str],
    success_keys: frozenset[str],
    cwd: str | None = None,
    run_id: str = "",
) -> tuple[CommandResult, dict[str, str]]:
    child_env: Mapping[str, str] | None = (
        None if not run_id else {**os.environ, "RUN_ID": run_id}
    )
    result = runner.run(
        [
            str(larch_entrypoint(Path(__file__).resolve().parents[3])),
            "tracking-issue",
            verb,
            *arguments,
        ],
        cwd=cwd,
        env=child_env,
    )
    stdout_rows = larch_io.parse_kv(
        result.stdout, duplicate_policy="all", skip_empty_key=True
    )
    stderr_rows = larch_io.parse_kv(
        result.stderr, duplicate_policy="all", skip_empty_key=True
    )
    stdout = {key: rows[0] for key, rows in stdout_rows.items() if rows}
    stderr = {key: rows[0] for key, rows in stderr_rows.items() if rows}
    malformed = any(len(rows) != 1 for rows in (*stdout_rows.values(), *stderr_rows.values()))
    conflicts = stdout.keys() & stderr.keys()
    values = {**stderr, **stdout}
    if malformed or conflicts:
        values["FAILED"] = "true"
        values["ERROR"] = "conflicting tracking-issue envelope"
    elif (result.returncode == 0 and set(values) != set(success_keys)) or (
        result.returncode != 0
        and (
            set(values) != {"FAILED", "ERROR"}
            or values.get("FAILED") != "true"
            or not values.get("ERROR")
        )
    ):
        values["FAILED"] = "true"
        values["ERROR"] = "invalid tracking-issue envelope"
    return result, values


def _tracking_error(result: CommandResult, values: Mapping[str, str]) -> str:
    return (
        values.get("ERROR", "")
        or " ".join((result.stderr or result.stdout).split())[:500]
        or "incomplete tracking-issue envelope"
    )


def _positive_ascii_decimal(value: str) -> bool:
    return value.isascii() and value.isdigit() and bool(value.strip("0"))


def tracking_issue_append_comment(  # noqa: PLR0913 - mirrors the Rust command option surface
    runner: Runner,
    *,
    issue: str,
    body_file: str,
    repo: str = "",
    lifecycle_marker: str = "",
    cwd: str | None = None,
) -> TrackingIssueCommentOutput:
    """Append one idempotent comment through ``scripts/larch.sh``."""
    arguments = ["--issue", issue, "--body-file", body_file]
    if lifecycle_marker:
        arguments.extend(["--lifecycle-marker", lifecycle_marker])
    if repo:
        arguments.extend(["--repo", repo])
    result, values = _tracking_issue_run(
        runner,
        verb="append-comment",
        arguments=arguments,
        success_keys=frozenset({"COMMENT_ID", "COMMENT_URL"}),
        cwd=cwd,
    )
    failed = result.returncode != 0 or values.get("FAILED") == "true"
    comment_id = values.get("COMMENT_ID", "")
    comment_url = values.get("COMMENT_URL", "")
    if not failed and (
        not _positive_ascii_decimal(comment_id)
        or f"#issuecomment-{comment_id}" not in comment_url
    ):
        failed = True
    return TrackingIssueCommentOutput(
        failed=failed,
        comment_id=comment_id,
        comment_url=comment_url,
        error=_tracking_error(result, values) if failed else "",
    )


def tracking_issue_create(
    runner: Runner,
    *,
    title: str,
    body_file: str,
    repo: str = "",
    cwd: str | None = None,
) -> TrackingIssueCreateOutput:
    """Create one tracking issue through ``scripts/larch.sh``."""
    arguments = ["--title", title, "--body-file", body_file]
    if repo:
        arguments.extend(["--repo", repo])
    result, values = _tracking_issue_run(
        runner,
        verb="create-issue",
        arguments=arguments,
        success_keys=frozenset({"ISSUE_NUMBER", "ISSUE_URL"}),
        cwd=cwd,
    )
    failed = result.returncode != 0 or values.get("FAILED") == "true"
    number = values.get("ISSUE_NUMBER", "")
    url = values.get("ISSUE_URL", "")
    if not failed and (
        not _positive_ascii_decimal(number) or f"/issues/{number}" not in url
    ):
        failed = True
    return TrackingIssueCreateOutput(
        failed=failed,
        issue_number=number,
        issue_url=url,
        error=_tracking_error(result, values) if failed else "",
    )


def tracking_issue_mark_false_positive(
    runner: Runner,
    *,
    issue: str,
    repo: str = "",
    cwd: str | None = None,
) -> TrackingIssueTitleOutput:
    """Mark one title through ``scripts/larch.sh``."""
    arguments = ["--issue", issue]
    if repo:
        arguments.extend(["--repo", repo])
    result, values = _tracking_issue_run(
        runner,
        verb="mark-false-positive",
        arguments=arguments,
        success_keys=frozenset({"MARKED", "NEW_TITLE"}),
        cwd=cwd,
    )
    failed = (
        result.returncode != 0
        or values.get("FAILED") == "true"
        or not values
    )
    title = values.get("NEW_TITLE", "")
    if not failed and (
        values.get("MARKED") not in {"true", "false"}
        or "[FALSE-POSITIVE]" not in title
    ):
        failed = True
    return TrackingIssueTitleOutput(
        failed=failed,
        changed=values.get("MARKED") == "true",
        new_title=title,
        error=_tracking_error(result, values) if failed else "",
    )


def tracking_issue_read(
    runner: Runner,
    *,
    arguments: Sequence[str],
    cwd: str | None = None,
) -> TrackingIssueReadOutput:
    """Read a tracking issue or sentinel through ``scripts/larch.sh``."""
    flags = frozenset(arguments[::2])
    if "--sentinel" in flags:
        success_keys = frozenset({"ISSUE_NUMBER", "RUN_ID", "ADOPTED"})
    elif "--body-out" in flags:
        success_keys = frozenset({"BODY_FILE", "BODY_SHA256"})
    elif "--comment-marker" in flags:
        success_keys = frozenset({"FOUND", "COMMENT_ID", "COMMENT_FILE"})
    else:
        success_keys = frozenset({"ISSUE_NUMBER", "TASK_SOURCE", "TASK_FILE"})
    result, values = _tracking_issue_run(
        runner,
        verb="read",
        arguments=arguments,
        success_keys=success_keys,
        cwd=cwd,
    )
    failed = (
        result.returncode != 0
        or values.get("FAILED") == "true"
        or not values
    )
    return TrackingIssueReadOutput(
        failed=failed,
        values=values,
        error=_tracking_error(result, values) if failed else "",
    )


def tracking_issue_read_marker(  # noqa: PLR0913 - mirrors the Rust command option surface
    runner: Runner,
    *,
    issue: str,
    marker: str,
    output_file: str,
    repo: str = "",
    cwd: str | None = None,
) -> TrackingIssueReadOutput:
    """Materialize one uniquely marker-owned comment through the Rust reader."""
    arguments = [
        "--issue",
        issue,
        "--comment-marker",
        marker,
        "--comment-out",
        output_file,
    ]
    if repo:
        arguments.extend(["--repo", repo])
    result = tracking_issue_read(runner, arguments=arguments, cwd=cwd)
    found = result.values.get("FOUND", "")
    comment_id = result.values.get("COMMENT_ID", "")
    try:
        materialized = Path(output_file).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        materialized = ""
        materialized_ok = False
    else:
        first_line = materialized.split("\n", 1)[0].removeprefix("\ufeff").removesuffix("\r")
        materialized_ok = (found == "true" and first_line == marker) or (
            found == "false" and not materialized
        )
    complete = (
        found in {"true", "false"}
        and result.values.get("COMMENT_FILE") == output_file
        and materialized_ok
        and (
            (found == "true" and _positive_ascii_decimal(comment_id))
            or (found == "false" and not comment_id)
        )
    )
    if result.failed or complete:
        return result
    return TrackingIssueReadOutput(
        failed=True,
        values=result.values,
        error="incomplete tracking-issue envelope",
    )


def tracking_issue_read_body(
    runner: Runner,
    *,
    issue: str,
    output_file: str,
    repo: str = "",
    cwd: str | None = None,
) -> TrackingIssueReadOutput:
    """Materialize one exact issue body through the Rust reader."""
    arguments = ["--issue", issue, "--body-out", output_file]
    if repo:
        arguments.extend(["--repo", repo])
    result = tracking_issue_read(runner, arguments=arguments, cwd=cwd)
    try:
        materialized = Path(output_file).read_bytes()
    except OSError:
        materialized_ok = False
    else:
        digest = hashlib.sha256(materialized).hexdigest()
        materialized_ok = (
            result.values.get("BODY_FILE") == output_file
            and result.values.get("BODY_SHA256") == digest
        )
    if result.failed or materialized_ok:
        return result
    return TrackingIssueReadOutput(
        failed=True,
        values=result.values,
        error="incomplete tracking-issue envelope",
    )


def tracking_issue_read_sentinel(
    runner: Runner,
    *,
    sentinel: str,
    cwd: str | None = None,
) -> TrackingIssueSentinelOutput:
    """Read one adoption sentinel through ``scripts/larch.sh``."""
    result = tracking_issue_read(
        runner,
        arguments=["--sentinel", sentinel],
        cwd=cwd,
    )
    issue_number = result.values.get("ISSUE_NUMBER", "")
    run_id = result.values.get("RUN_ID", "")
    adopted = result.values.get("ADOPTED", "")
    complete = (
        (not issue_number or _positive_ascii_decimal(issue_number))
        and (
            not run_id
            or (
                run_id.isascii()
                and all(character.isalnum() or character in "._-" for character in run_id)
            )
        )
        and adopted in {"", "true", "false"}
        and {"ISSUE_NUMBER", "RUN_ID", "ADOPTED"}.issubset(result.values)
    )
    failed = result.failed or not complete
    return TrackingIssueSentinelOutput(
        failed=failed,
        issue_number=issue_number,
        run_id=run_id,
        adopted=adopted,
        error=(
            result.error
            if result.failed
            else "incomplete tracking-issue envelope" if not complete else ""
        ),
    )


def tracking_issue_rename(  # noqa: PLR0913 - mirrors the Rust command option surface
    runner: Runner,
    *,
    issue: str,
    state: str,
    repo: str = "",
    run_id: str = "",
    lease_branch: str = "",
    head_sha: str = "",
    expected_updated_at: str = "",
    expected_body_sha256: str = "",
    expected_title_sha256: str = "",
    expected_labels_sha256: str = "",
    cwd: str | None = None,
) -> TrackingIssueTitleOutput:
    """Apply one plain, initial, or terminal title transition in Rust."""
    arguments = ["--issue", issue, "--state", state]
    for option, value in (
        ("--repo", repo),
        ("--run-id", run_id),
        ("--lease-branch", lease_branch),
        ("--head-sha", head_sha),
        ("--expected-updated-at", expected_updated_at),
        ("--expected-body-sha256", expected_body_sha256),
        ("--expected-title-sha256", expected_title_sha256),
        ("--expected-labels-sha256", expected_labels_sha256),
    ):
        if value:
            arguments.extend([option, value])
    result, values = _tracking_issue_run(
        runner,
        verb="rename",
        arguments=arguments,
        success_keys=frozenset({"RENAMED", "NEW_TITLE"}),
        cwd=cwd,
    )
    failed = result.returncode != 0 or values.get("FAILED") == "true"
    title = values.get("NEW_TITLE", "")
    expected_prefix = config.TRACKING_ISSUE_PREFIX_BY_STATE.get(state, "")
    if not failed and (
        values.get("RENAMED") not in {"true", "false"}
        or not expected_prefix
        or not title.startswith(expected_prefix)
    ):
        failed = True
    return TrackingIssueTitleOutput(
        failed=failed,
        changed=values.get("RENAMED") == "true",
        new_title=title,
        error=_tracking_error(result, values) if failed else "",
    )


def tracking_issue_upsert_summary(  # noqa: PLR0913 - mirrors the Rust command option surface
    runner: Runner,
    *,
    issue: str,
    marker: str,
    content_file: str,
    repo: str = "",
    comment_id: str = "",
    delete_if_empty: bool = False,
    run_id: str = "",
    cwd: str | None = None,
) -> TrackingIssueCommentOutput:
    """Upsert one marker comment through ``scripts/larch.sh``."""
    arguments = ["--issue", issue, "--marker", marker, "--content-file", content_file]
    if repo:
        arguments.extend(["--repo", repo])
    if comment_id:
        arguments.extend(["--comment-id", comment_id])
    if delete_if_empty:
        arguments.extend(["--delete-if-empty", "true"])
    result, values = _tracking_issue_run(
        runner,
        verb="upsert-summary",
        arguments=arguments,
        success_keys=frozenset({"COMMENT_ID", "COMMENT_URL", "UPDATED"}),
        cwd=cwd,
        run_id=run_id,
    )
    failed = result.returncode != 0 or values.get("FAILED") == "true"
    result_id = values.get("COMMENT_ID", "")
    url = values.get("COMMENT_URL", "")
    content_empty = False
    if delete_if_empty:
        try:
            content_empty = Path(content_file).read_text(encoding="utf-8").strip() == ""
        except (OSError, UnicodeError):
            failed = True
    updated = values.get("UPDATED", "")
    complete_empty_result = (
        content_empty and not result_id and not url and updated == "false"
    )
    complete_comment_result = _positive_ascii_decimal(result_id) and (
        (content_empty and not url) or f"#issuecomment-{result_id}" in url
    )
    if not failed and (
        updated not in {"true", "false"}
        or not (complete_empty_result or complete_comment_result)
    ):
        failed = True
    return TrackingIssueCommentOutput(
        failed=failed,
        comment_id=result_id,
        comment_url=url,
        updated=updated == "true",
        error=_tracking_error(result, values) if failed else "",
    )


def issue_info(
    runner: Runner,
    *,
    issue: str,
    field: str,
    repo: str | None = None,
    cwd: str | None = None,
) -> str:
    """Read one issue field (``state`` or ``url``) through the Rust owner.

    The command reports every refusal as an empty value, so an unreadable
    field, an unresolvable repository, and an unreachable API are one outcome.
    """
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "issue",
        "info",
        "--issue",
        issue,
        "--field",
        field,
    ]
    if repo:
        argv.extend(["--repo", repo])
    result = runner.run(argv, cwd=cwd)
    if result.returncode != 0:
        return ""
    values: dict[str, str] = larch_io.parse_kv(result.stdout, skip_empty_key=True)
    return values.get("VALUE", "")


_ISSUE_ITEM_FIELDS = {
    "TITLE": "title",
    "BODY_FILE": "body_file",
    "REVIEWER": "reviewer",
    "VOTE_TALLY": "vote",
    "PHASE": "phase",
}


def parse_issue_input(
    runner: Runner,
    *,
    input_file: Path,
    output_dir: Path,
    cwd: str | None = None,
) -> IssueParseInputOutput:
    """Parse one issue-input file through its Rust owner.

    The command materializes each non-empty body itself and reports the item
    rows on stdout, so this consumer only validates and types that envelope.
    """
    result: CommandResult = runner.run(
        [
            str(larch_entrypoint(Path(__file__).resolve().parents[3])),
            "issue",
            "parse-input",
            "--input-file",
            str(input_file),
            "--output-dir",
            str(output_dir),
        ],
        cwd=cwd,
    )
    if result.returncode != 0:
        return IssueParseInputOutput(
            exit_code=result.returncode,
            error=" ".join((result.stderr or result.stdout).split())[:500],
        )
    fields: dict[int, dict[str, str]] = {}
    total: int | None = None
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if not separator:
            continue
        if key == "ITEMS_TOTAL":
            total = int(value) if value.isdigit() else None
            continue
        if not key.startswith("ITEM_"):
            continue
        position, _, suffix = key[len("ITEM_") :].partition("_")
        if not position.isdigit() or (suffix not in _ISSUE_ITEM_FIELDS and suffix != "MALFORMED"):
            continue
        fields.setdefault(int(position), {})[suffix] = value
    if total is None or len(fields) != total or sorted(fields) != list(range(1, total + 1)):
        return IssueParseInputOutput(exit_code=1, error="issue parse-input published an incomplete item envelope")
    items = tuple(
        IssueParsedItem(
            malformed=fields[position].get("MALFORMED") == "true",
            **{
                attribute: fields[position].get(suffix, "")
                for suffix, attribute in _ISSUE_ITEM_FIELDS.items()
            },
        )
        for position in range(1, total + 1)
    )
    return IssueParseInputOutput(items=items)


def issue_create_one(  # noqa: PLR0913 - mirrors the create-one CLI option surface plus the injected runner
    runner: Runner,
    *,
    title: str,
    title_prefix: str = "",
    body_file: str = "",
    labels: Sequence[str] = (),
    repo: str = "",
    context_file: str = "",
    run_id: str = "",
    trusted_root: str = "",
    cwd: str | None = None,
) -> IssueCreateOutput:
    """File one issue through the Rust owner and fail closed without its rows.

    The command owns redaction, title-prefix normalization, label probing, and
    the live-mutation gate, so this consumer only validates and types the
    envelope it publishes.
    """
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "issue",
        "create-one",
        "--title",
        title,
    ]
    if title_prefix:
        argv.extend(["--title-prefix", title_prefix])
    if body_file:
        argv.extend(["--body-file", body_file])
    for label in labels:
        argv.extend(["--label", label])
    if repo:
        argv.extend(["--repo", repo])
    if context_file:
        argv.extend(["--context-file", context_file, "--run-id", run_id, "--trusted-root", trusted_root])
    result: CommandResult = runner.run(argv, cwd=cwd)
    values: dict[str, str] = larch_io.parse_kv(result.stdout, skip_empty_key=True)
    error = values.get("ISSUE_ERROR", "") or " ".join((result.stderr or result.stdout).split())[:500]
    if result.returncode != 0 or values.get("ISSUE_FAILED") == "true":
        return IssueCreateOutput(exit_code=result.returncode or 1, error=error)
    if not values.get("ISSUE_NUMBER", "").isdigit() or not values.get("ISSUE_URL", ""):
        return IssueCreateOutput(exit_code=1, error="issue create-one published an incomplete envelope")
    return IssueCreateOutput(
        number=values["ISSUE_NUMBER"],
        url=values["ISSUE_URL"],
        issue_id=values.get("ISSUE_ID", ""),
        title=values.get("ISSUE_TITLE", ""),
    )


def issue_cleanup_failed(
    runner: Runner,
    *,
    issue: str,
    repo: str = "",
    cwd: str | None = None,
) -> bool:
    """Close one orphaned issue through the Rust owner, best effort.

    The command always exits ``0`` and reports its outcome as ``CLOSED``, so a
    refused close is reported here as ``False`` rather than raised: the caller
    has already counted the failure that produced the orphan.
    """
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "issue",
        "cleanup-failed",
        "--issue-number",
        issue,
    ]
    if repo:
        argv.extend(["--repo", repo])
    result: CommandResult = runner.run(argv, cwd=cwd)
    values: dict[str, str] = larch_io.parse_kv(result.stdout, skip_empty_key=True)
    return result.returncode == 0 and values.get("CLOSED") == "true"


def issue_add_blocked_by(  # noqa: PLR0913 - mirrors the add-blocked-by CLI option surface plus the injected runner
    runner: Runner,
    *,
    client: str,
    blocker: str,
    blocker_id: str = "",
    repo: str = "",
    context_file: str = "",
    run_id: str = "",
    trusted_root: str = "",
    cwd: str | None = None,
) -> IssueEdgeOutput:
    """Wire one native blocked-by edge through the Rust owner.

    The command owns the live-mutation gate, the idempotent pre-read, the retry
    contract, and the exact read-back, so this consumer only validates the
    envelope it publishes. ``BLOCKED_BY_ADDED=true`` is the only success, and a
    zero exit without it is reported as a failure rather than an applied edge.
    """
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "issue",
        "add-blocked-by",
        "--client-issue",
        client,
        "--blocker-issue",
        blocker,
    ]
    if blocker_id:
        argv.extend(["--blocker-id", blocker_id])
    if repo:
        argv.extend(["--repo", repo])
    if context_file:
        argv.extend(["--context-file", context_file, "--run-id", run_id, "--trusted-root", trusted_root])
    return _issue_edge_output(runner.run(argv, cwd=cwd), added_key="BLOCKED_BY_ADDED")


def _issue_edge_output(result: CommandResult, *, added_key: str) -> IssueEdgeOutput:
    """Type one issue-graph envelope, failing closed without its added row."""
    values: dict[str, str] = larch_io.parse_kv(result.stdout, skip_empty_key=True)
    if result.returncode == 0 and values.get(added_key) == "true":
        return IssueEdgeOutput(added=True)
    error = values.get("ERROR", "") or " ".join((result.stderr or result.stdout).split())[:500]
    return IssueEdgeOutput(exit_code=result.returncode or 1, error=error)


def block_issue_dependency(  # noqa: PLR0913 - mirrors the /block-issue CLI surface plus the injected runner
    runner: Runner,
    *,
    remove: bool,
    issue: str,
    blocker: str,
    repo: str,
    cwd: str | None = None,
) -> bool:
    """Apply one operator-invoked `/block-issue` dependency mutation.

    The command proves the final relation by read-back before it reports
    ``SUCCESS``, so a zero exit without both receipt rows reads as a failure.
    """
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "block-issue",
        "remove-blocked-by" if remove else "add-blocked-by",
        issue,
        blocker,
        "--repo",
        repo,
        "--operator-invoked",
    ]
    result: CommandResult = runner.run(argv, cwd=cwd)
    values: dict[str, str] = larch_io.parse_kv(result.stdout, skip_empty_key=True)
    return (
        result.returncode == 0
        and values.get("SUCCESS") == "true"
        and values.get("RELATION_VERIFIED") == "true"
    )


def install_statusline(
    runner: Runner,
    *,
    plugin_root: str,
    repo_root: str,
    notice: bool = False,
    cwd: str | None = None,
) -> bool:
    """Invoke the Rust statusline installer, which is fail silent by contract."""
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "progress",
        "install-statusline",
        "--plugin-root",
        plugin_root,
        "--repo-root",
        repo_root,
    ]
    if notice:
        argv.append("--notice")
    return runner.run(argv, cwd=cwd).returncode == 0


def _progress_command(
    runner: Runner,
    *,
    verb: str,
    arguments: Sequence[str],
    cwd: str | None = None,
) -> CommandResult:
    return runner.run(
        [
            str(larch_entrypoint(Path(__file__).resolve().parents[3])),
            "progress",
            verb,
            *arguments,
        ],
        cwd=cwd,
    )


def progress_activate(
    runner: Runner,
    *,
    repo_root: str,
    run_id: str,
    cwd: str | None = None,
) -> bool:
    """Activate one run through the sole Rust progress-state owner."""
    return _progress_command(
        runner,
        verb="activate",
        arguments=("--repo-root", repo_root, "--run-id", run_id),
        cwd=cwd,
    ).returncode == 0


def progress_clear(
    runner: Runner,
    *,
    repo_root: str,
    cwd: str | None = None,
) -> bool:
    """Clear a clone's active pointer through the Rust progress-state owner."""
    return _progress_command(
        runner,
        verb="clear",
        arguments=("--repo-root", repo_root),
        cwd=cwd,
    ).returncode == 0


def progress_deactivate(
    runner: Runner,
    *,
    repo_root: str,
    run_id: str,
    cwd: str | None = None,
) -> bool:
    """Compare-and-clear one run through the Rust progress-state owner."""
    return _progress_command(
        runner,
        verb="deactivate",
        arguments=("--repo-root", repo_root, "--run-id", run_id),
        cwd=cwd,
    ).returncode == 0


def progress_note(  # noqa: PLR0913 - mirrors the Rust progress CLI surface
    runner: Runner,
    *,
    repo_root: str,
    run_id: str,
    skill: str,
    step: str,
    text: str,
    cwd: str | None = None,
) -> bool:
    """Append one named-run breadcrumb through the Rust progress-state owner."""
    return _progress_command(
        runner,
        verb="note",
        arguments=(
            "--repo-root",
            repo_root,
            "--run-id",
            run_id,
            "--skill",
            skill,
            "--step",
            step,
            text,
        ),
        cwd=cwd,
    ).returncode == 0


def progress_cleanup(
    runner: Runner,
    *,
    retention_days: int,
    cwd: str | None = None,
) -> int:
    """Prune stale progress state and return the Rust owner's removed count."""
    result = _progress_command(
        runner,
        verb="cleanup",
        arguments=("--retention-days", str(retention_days)),
        cwd=cwd,
    )
    values = larch_io.parse_kv(result.stdout, skip_empty_key=True)
    removed = values.get("PROGRESS_REMOVED", "")
    if result.returncode != 0 or not removed.isascii() or not removed.isdigit():
        return 0
    return int(removed)


def _timing_command(  # noqa: PLR0913 - internal transport preserves the Rust timing CLI context.
    runner: Runner,
    *,
    verb: str,
    arguments: Sequence[str],
    skill: str,
    ledger: str | None = None,
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> CommandResult:
    """Invoke one Rust-owned timing mutation with explicit session context."""
    env = dict(os.environ)
    if environment is not None:
        env.update(environment)
    env["LARCH_TIMING_SKILL"] = skill
    if ledger:
        env["LARCH_TIMING_LEDGER"] = ledger
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "timing",
        verb,
    ]
    if ledger:
        argv.extend(["--ledger", ledger])
    argv.extend(arguments)
    return runner.run(argv, cwd=cwd, env=env)


def timing_mark(  # noqa: PLR0913 - mirrors the stable Rust timing CLI surface.
    runner: Runner,
    *,
    label: str,
    skill: str,
    ledger: str | None = None,
    if_latest_differs: bool = False,
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> bool:
    """Record one step mark through the sole Rust timing-ledger owner."""
    arguments = ["--if-latest-differs"] if if_latest_differs else []
    arguments.append(label)
    return _timing_command(
        runner,
        verb="mark",
        arguments=arguments,
        skill=skill,
        ledger=ledger,
        environment=environment,
        cwd=cwd,
    ).returncode == 0


def timing_record_vendor_task(  # noqa: PLR0913 - mirrors the stable Rust timing CLI surface.
    runner: Runner,
    *,
    vendor: str,
    task_kind: str,
    start_s: float,
    end_s: float,
    output: str,
    skill: str,
    ledger: str | None = None,
    exit_code: int = 0,
    status: str = "complete",
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> bool:
    """Record one vendor span through the sole Rust timing-ledger owner."""
    return _timing_command(
        runner,
        verb="record-vendor-task",
        arguments=(
            "--vendor",
            vendor,
            "--task-kind",
            task_kind,
            "--start-s",
            str(start_s),
            "--end-s",
            str(end_s),
            "--output",
            output,
            "--exit-code",
            str(exit_code),
            "--status",
            status,
        ),
        skill=skill,
        ledger=ledger,
        environment=environment,
        cwd=cwd,
    ).returncode == 0


def timing_record_round(  # noqa: PLR0913 - mirrors the stable Rust timing CLI surface.
    runner: Runner,
    *,
    skill: str,
    step: str,
    round_num: int,
    start_s: float,
    end_s: float,
    accepted: int,
    rejected: int,
    oos: int | None = None,
    ledger: str | None = None,
    if_round_exists: bool = False,
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> bool:
    """Record one review round through the sole Rust timing-ledger owner."""
    arguments = [
        "--skill",
        skill,
        "--step",
        step,
        "--round",
        str(round_num),
        "--start-s",
        str(start_s),
        "--end-s",
        str(end_s),
        "--accepted",
        str(accepted),
        "--rejected",
        str(rejected),
    ]
    if oos is not None:
        arguments.extend(["--oos", str(oos)])
    if if_round_exists:
        arguments.append("--if-round-exists")
    return _timing_command(
        runner,
        verb="record-round",
        arguments=arguments,
        skill=skill,
        ledger=ledger,
        environment=environment,
        cwd=cwd,
    ).returncode == 0


def _token_command(  # noqa: PLR0913 - internal transport preserves the Rust token CLI context.
    runner: Runner,
    *,
    verb: str,
    arguments: Sequence[str],
    ledger: str | None = None,
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> CommandResult:
    """Invoke one Rust-owned token mutation with explicit session context."""
    env = dict(os.environ)
    if environment is not None:
        env.update(environment)
    if ledger:
        env["LARCH_TOKEN_LEDGER"] = ledger
    argv: list[str] = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "token",
        verb,
    ]
    if ledger:
        argv.extend(["--ledger", ledger])
    argv.extend(arguments)
    return runner.run(argv, cwd=cwd, env=env)


def token_mark(
    runner: Runner,
    *,
    step: str,
    ledger: str | None = None,
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> bool:
    """Record one step mark through the sole Rust token-ledger owner."""
    return _token_command(
        runner,
        verb="mark",
        arguments=(step,),
        ledger=ledger,
        environment=environment,
        cwd=cwd,
    ).returncode == 0


def token_record_vendor(  # noqa: PLR0913 - mirrors the stable Rust token CLI surface.
    runner: Runner,
    *,
    vendor: str,
    fields: Sequence[str],
    ledger: str | None = None,
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> bool:
    """Record one vendor usage row through the sole Rust token-ledger owner."""
    return _token_command(
        runner,
        verb="record-vendor",
        arguments=(vendor, *fields),
        ledger=ledger,
        environment=environment,
        cwd=cwd,
    ).returncode == 0


def token_record_vendor_sidecar(
    runner: Runner,
    *,
    input_path: str,
    ledger: str | None = None,
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> bool:
    """Append one active-ledger vendor row from a KEY=value sidecar."""
    return _token_command(
        runner,
        verb="record-vendor-sidecar",
        arguments=("--input", input_path),
        ledger=ledger,
        environment=environment,
        cwd=cwd,
    ).returncode == 0


def token_append_record(
    runner: Runner,
    *,
    input_path: str,
    tmpdir: str,
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> bool:
    """Append one staging NDJSON row from a KEY=value sidecar."""
    return _token_command(
        runner,
        verb="append-record",
        arguments=("--input", input_path, "--tmpdir", tmpdir),
        environment=environment,
        cwd=cwd,
    ).returncode == 0


def token_dump(
    runner: Runner,
    *,
    ledger: str | None = None,
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> CommandResult:
    """Print the resolved token ledger path and its raw rows."""
    return _token_command(
        runner,
        verb="dump",
        arguments=(),
        ledger=ledger,
        environment=environment,
        cwd=cwd,
    )


def token_lane_write(  # noqa: PLR0913 - mirrors the stable Rust token CLI surface.
    runner: Runner,
    *,
    directory: str,
    phase: str,
    lane: str,
    tool: str,
    total_tokens: str,
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> bool:
    """Write one research/validation lane token sidecar."""
    return _token_command(
        runner,
        verb="lane-write",
        arguments=(
            "--dir",
            directory,
            "--phase",
            phase,
            "--lane",
            lane,
            "--tool",
            tool,
            "--total-tokens",
            total_tokens,
        ),
        environment=environment,
        cwd=cwd,
    ).returncode == 0


def token_lane_report(
    runner: Runner,
    *,
    directory: str,
    environment: Mapping[str, str] | None = None,
    cwd: str | None = None,
) -> CommandResult:
    """Render the research lane token-spend summary."""
    return _token_command(
        runner,
        verb="lane-report",
        arguments=("--dir", directory),
        environment=environment,
        cwd=cwd,
    )


def render_phase_detail(  # noqa: PLR0913 - mirrors the Rust renderer's stable CLI surface plus the injected runner
    runner: Runner,
    *,
    rounds_root: str,
    skill: str,
    timing_ledger: str | None = None,
    token_ledger: str | None = None,
    findings_file: str | None = None,
    top_n: int = 7,
    gantt_enabled: bool = True,
    cwd: str | None = None,
) -> str:
    """Render a bounded review detail through the Rust-owned command."""
    argv = [
        str(larch_entrypoint(Path(__file__).resolve().parents[3])),
        "progress",
        "render-phase-detail",
        "--rounds-root",
        rounds_root,
        "--skill",
        skill,
        "--top-n",
        str(top_n),
    ]
    if timing_ledger:
        argv.extend(["--timing-ledger", timing_ledger])
    if token_ledger:
        argv.extend(["--token-ledger", token_ledger])
    if findings_file:
        argv.extend(["--findings-file", findings_file])
    if not gantt_enabled:
        argv.append("--no-gantt")
    result = runner.run(argv, timeout=15, cwd=cwd)
    return result.stdout if result.returncode == 0 else ""
