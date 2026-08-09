"""Typed consumers of commands owned by the installed Rust runtime."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io
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
