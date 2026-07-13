"""Shared state and wire helpers for review panel and voter dispatch."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Mapping, Sequence
from typing import Literal, Protocol, cast

from larch.agents import _launch_failure
from larch.core import config, external_defaults, logging_util
from larch.report.timing import TimingLedger
from larch.review import _voting_calibration, voting

VoterRowLayout = Literal["code_review_sequential", "plan_review_interleaved"]
PathsFilePolicy = Literal["always", "nonempty"]


class CommandResultLike(Protocol):
    """Minimum result surface required from an injected command runner."""

    @property
    def returncode(self) -> int: ...
    @property
    def stdout(self) -> str: ...


Runner = Callable[..., CommandResultLike]


VoterSlotPolicy = config.VoterPolicyDefault


@dataclass(frozen=True)
class VoterPromptResult:
    """Rendered voter prompt plus its payload accounting."""

    prompt_file: Path | str
    payload_bytes: int = 0


# Mutable: dispatchers update per-voter status and parse-rate fields as slots resolve.
@dataclass
class DispatchState:
    """Canonical three-voter dispatch state."""

    voter_1_path: Path | None
    voter_2_path: Path | None = None
    voter_3_path: Path | None = None
    voter_1_tool: str = "codex-validity"
    voter_2_tool: str = "codex-plan-fidelity"
    voter_3_tool: str = "codex-pragmatism"
    voter_1_status: str = "launched"
    voter_2_status: str = "launched"
    voter_3_status: str = "launched"
    voter_1_parse_rate_status: str = "SKIPPED"
    voter_2_parse_rate_status: str = "SKIPPED"
    voter_3_parse_rate_status: str = "SKIPPED"


def path_for_wire(path: Path | None) -> str:
    """Serialize an optional path only when it crosses a wire boundary."""
    return "" if path is None else str(path)


def _record_pipeline_span(  # noqa: PLR0913 - the six span fields are all load-bearing and not worth bundling for two callers
    *,
    ledger: Path | None,
    skill: str,
    task_kind: str,
    start_s: float,
    end_s: float,
    output: str,
) -> None:
    """Best-effort append of one synthetic pipeline-phase vendor row.

    Shared by the recorders that model a serial span running between two instrumented model
    calls (voter dispatch prep before the voters, reviewer collection before the aggregator).
    The row carries the neutral ``claude`` vendor and a ``complete`` status so the Gantt draws
    it as a labeled bar filling what would otherwise be a blank band. Timing is diagnostic, so
    a missing ledger or a write error is skipped rather than raised.
    """
    if ledger is None or not ledger.is_file():
        return
    with suppress(OSError, ValueError):
        TimingLedger(ledger, skill=skill).record_vendor_task(
            vendor="claude",
            task_kind=task_kind,
            start_s=start_s,
            end_s=end_s,
            output=output,
            status="complete",
        )


def record_voter_dispatch_prep(
    *,
    ledger: Path | None,
    skill: str,
    prep_start: float,
    prep_end: float,
    round_num: int,
) -> None:
    """Record the serial voter pre-dispatch window as a ``voter-dispatch-prep`` vendor row.

    The window covers the blocking work each dispatcher runs before the waterfall spawns any
    voter: the calibration snapshot, the per-slot/tool ``render voter`` subprocess calls, and
    the manifest write. A voter captures its own ``start_s`` only after that phase completes,
    so without this row the Gantt shows a blank band between the aggregator bar and the voter
    bars instead of the render work that fills it (issue #7166). Timing is diagnostic, so a
    missing ledger or a write error is skipped rather than raised.
    """
    _record_pipeline_span(
        ledger=ledger,
        skill=skill,
        task_kind="voter-dispatch-prep",
        start_s=prep_start,
        end_s=prep_end,
        output=f"voter-dispatch-prep-round-{round_num}.out",
    )


def record_reviewer_collect(
    *,
    ledger: Path | None,
    skill: str,
    collect_start: float,
    collect_end: float,
    round_num: int,
) -> None:
    """Record the reviewers-to-aggregator window as a ``reviewer-collect`` vendor row.

    The window covers the serial work each review round runs after the last reviewer finishes
    and before the aggregator model call starts: waiting for reviewer stragglers, collecting
    and de-duplicating reviewer outputs, the failure-threshold check, and nit pruning. A
    reviewer captures its ``end_s`` when its model call finishes and the aggregator captures
    its ``start_s`` only when its model call begins, so without this row the Gantt shows a
    blank band between the reviewer bars and the aggregator bar instead of the collection work
    that fills it (issue #7179). Timing is diagnostic, so a missing ledger or a write error is
    skipped rather than raised.
    """
    _record_pipeline_span(
        ledger=ledger,
        skill=skill,
        task_kind="reviewer-collect",
        start_s=collect_start,
        end_s=collect_end,
        output=f"reviewer-collect-round-{round_num}.out",
    )


def topology_slots(topology_key: str) -> tuple[config.SlotDefault, ...]:
    """Return slot defaults for one topology role."""
    return external_defaults.slot_defaults(topology_key)


def topology_voter_policies(topology_key: str) -> tuple[VoterSlotPolicy, ...]:
    """Return voter policies for one topology role."""
    return external_defaults.voter_policies(topology_key)


def _resolved_model_for_row(tool: str, model_role: str = "", default_model: str = "") -> str:
    """Resolve one manifest model using the canonical role normalization."""
    role = cast("Literal['default', 'review', 'vote', 'fix']", model_role if model_role in {"default", "review", "vote", "fix"} else "default")
    try:
        argv = list(
            _launch_failure.resolve_model_args(
                tool,
                with_effort=tool == "codex",
                default_model=default_model,
                codex_role=role,
            ).argv
        )
    except (KeyError, ValueError):
        return "unknown"
    flag = "--model" if tool == "cursor" else "-m" if tool == "codex" else ""
    if flag and flag in argv:
        index = argv.index(flag)
        return argv[index + 1] if index + 1 < len(argv) else "unknown"
    return "unknown"


resolved_model_for_row = _resolved_model_for_row

def with_manifest_attribution(
    row: Mapping[str, object],
    *,
    model_role: str | None = None,
    default_model: str = "",
) -> dict[str, object]:
    """Copy a manifest row and fill its vendor, role, and resolved model."""
    attributed = dict(row)
    tool = str(attributed.get("tool") or "unknown")
    role = model_role if model_role is not None else str(attributed.get("model_role") or "default")
    _ = attributed.setdefault("vendor", tool)
    if model_role is not None:
        _ = attributed.setdefault("model_role", model_role)
    _ = attributed.setdefault("resolved_model", _resolved_model_for_row(tool, role, default_model))
    return attributed


def append_manifest_row(
    *,
    manifest: Path,
    row: Mapping[str, object],
    model_role: str | None = None,
    default_model: str = "",
) -> None:
    """Append one attributed NDJSON manifest row."""
    attributed = with_manifest_attribution(row, model_role=model_role, default_model=default_model)
    with manifest.open("a", encoding="utf-8") as handle:
        _ = handle.write(json.dumps(attributed, separators=(",", ":")) + "\n")


def fresh_calibration_snapshot(  # noqa: PLR0913 - family-specific roots and injected runner are independent seams
    *,
    work_dir: Path,
    snapshot_argv: Sequence[str],
    runner: Runner,
    cwd: Path | None = None,
    design_tmpdir: Path | None = None,
    review_tmpdir: Path | None = None,
) -> str | None:
    """Create a nonempty calibration snapshot beside its atomic target."""
    target = work_dir / "voter-calibration-stats.tsv"
    with suppress(FileNotFoundError):
        target.unlink()
    if os.environ.get(config.ENV_LARCH_VOTER_CALIBRATION_FEEDBACK, "").strip() == "0":
        return None
    tmp_path: Path | None = None
    try:
        fd, tmp = tempfile.mkstemp(prefix=".voter-calibration-stats.", suffix=".tsv", dir=str(work_dir))
        os.close(fd)
        tmp_path = Path(tmp)
        tmp_path.unlink()
        log_root = _voting_calibration._resolve_voter_calibration_log_root(  # noqa: SLF001 - reuse voting internal calibration log-root resolver  # pyright: ignore[reportPrivateUsage]  # sibling-module private helper, no public resolver exists
            design_tmpdir=design_tmpdir,
            review_tmpdir=review_tmpdir,
        )
        result = runner([*snapshot_argv, "--log-root", str(log_root), "--out", str(tmp_path)], cwd=None if cwd is None else str(cwd))
        if result.returncode != 0 or not tmp_path.is_file() or tmp_path.stat().st_size <= 0:
            return None
        _ = tmp_path.replace(target)
        return str(target)
    except (OSError, RuntimeError, ValueError):
        return None
    finally:
        if tmp_path is not None:
            with suppress(FileNotFoundError):
                tmp_path.unlink()


def validate_parse_rate_result(
    argv: Sequence[str],
    *,
    runner: Runner,
    cwd: Path | None = None,
    runner_kwargs: Mapping[str, object] | None = None,
) -> str:
    """Run parse-rate validation and fail closed on every malformed result."""
    kwargs: dict[str, object] = dict(runner_kwargs or {})
    if cwd is not None:
        kwargs["cwd"] = str(cwd)
    try:
        result = runner(list(argv), **kwargs)
    except (OSError, RuntimeError, ValueError):
        return "NOT_SUBSTANTIVE"
    if result.returncode != 0:
        return "NOT_SUBSTANTIVE"
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines or lines[-1] not in {"OK", "NOT_SUBSTANTIVE"}:
        return "NOT_SUBSTANTIVE"
    return lines[-1]


def emit_final_voter_kvs(  # noqa: PLR0913 - row layout and paths policy are independent wire contracts
    *,
    state: DispatchState,
    voter_paths_file: Path | None,
    dispatch_ok: str,
    row_layout: VoterRowLayout,
    paths_file_policy: PathsFilePolicy,
    emit_kv: Callable[..., None] | None = None,
) -> None:
    """Emit the stable voter contract in-process, followed by dispatch status."""
    emitter = emit_kv or logging_util.emit_kv
    voters = (
        (path_for_wire(state.voter_1_path), state.voter_1_tool, state.voter_1_status, state.voter_1_parse_rate_status),
        (path_for_wire(state.voter_2_path), state.voter_2_tool, state.voter_2_status, state.voter_2_parse_rate_status),
        (path_for_wire(state.voter_3_path), state.voter_3_tool, state.voter_3_status, state.voter_3_parse_rate_status),
    )
    rows = voting.build_voter_status_rows(
        voters=voters,
        voter_paths_file=path_for_wire(voter_paths_file),
        row_layout=row_layout,
        paths_file_policy=paths_file_policy,
    )
    for key, value in rows:
        emitter(key=key, value=value)
    emitter(key="DISPATCH_OK", value=dispatch_ok)
