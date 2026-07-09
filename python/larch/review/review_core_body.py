# pyright: reportArgumentType=false, reportOptionalIterable=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportPrivateUsage=false, reportUnusedCallResult=false, reportUnusedFunction=false
# ruff: noqa: ARG001
# pylint: disable=too-many-branches,too-many-statements,too-many-locals,too-many-arguments,unused-argument,too-many-boolean-expressions
"""Core review pipeline orchestration logic."""

from __future__ import annotations

import contextlib
import os
import re
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path

from larch.core import config, logging_util, proc
from larch.calibration import difficulty
from larch.report import progress_file
from larch.review.review_pipeline_shared import (
    ReviewCommands,
    ReviewCoreBranchContext,
    ReviewCoreResult,
    _append_text,
    _call_maybe_override,
    _collector_records,
    _emit_kv,
    _get,
    _kv_parse,
    _manifest_rows,
    _parse_args,
    _run_command_string,
    _run_python_cli,
    _write_text,
)
from larch.review import voting
from larch.review.review_types import ReviewCoreStatus
from larch.review.review_prune import (
    reviewer_prune_record,
    write_prune_decision_env,
)


def _review_commands() -> ReviewCommands:
    return ReviewCommands(
        gather=os.environ.get("REVIEW_CORE_GATHER_CONTEXT_SH", ""),
        dispatch=os.environ.get("REVIEW_CORE_DISPATCH_PANEL_SH", ""),
        collect=os.environ.get("REVIEW_CORE_COLLECT_FINDINGS_SH", ""),
        threshold=os.environ.get("REVIEW_CORE_CHECK_THRESHOLD_SH", ""),
        aggregate=os.environ.get("REVIEW_CORE_AGGREGATE_FINDINGS_SH", ""),
        tally=os.environ.get("REVIEW_CORE_TALLY_VOTES_SH", ""),
        emit=os.environ.get("REVIEW_CORE_EMIT_TALLY_SH", ""),
        prune_nits=os.environ.get("REVIEW_CORE_PRUNE_NITS_SH", ""),
        dispatch_voters=os.environ.get("REVIEW_CORE_DISPATCH_VOTERS_SH", ""),
    )


def _progress_note(*, step: str, text: str) -> None:
    _ = progress_file.append_breadcrumb(Path.cwd(), "implement", step, text)


def _copy_to_parent(*, file: Path, name: str, session_env_path: str) -> None:
    if session_env_path and file.is_file():
        with contextlib.suppress(OSError):
            shutil.copyfile(file, Path(session_env_path).parent / name)


def _parent_dir(*, session_env_path: str, review_tmpdir: Path) -> Path | None:
    if session_env_path:
        return Path(session_env_path).parent
    implement = os.environ.get("IMPLEMENT_TMPDIR", "")
    if implement:
        return Path(implement)
    return None


def _snapshot_oos(*, review_tmpdir: Path, stem: str, session_env_path: str) -> None:
    for name in ("oos-accepted-review.md", "accumulated-oos.md"):
        src = review_tmpdir / name
        dst = review_tmpdir / f"{stem}.{name}.before.md"
        if src.is_file():
            shutil.copyfile(src, dst)
        else:
            with contextlib.suppress(FileNotFoundError):
                dst.unlink()
    parent = _parent_dir(session_env_path=session_env_path, review_tmpdir=review_tmpdir)
    if parent:
        for name in ("oos-accepted-review.md", "accumulated-oos.md"):
            src = parent / name
            dst = review_tmpdir / f"{stem}.parent-{name}.before.md"
            if src.is_file():
                shutil.copyfile(src, dst)
            else:
                with contextlib.suppress(FileNotFoundError):
                    dst.unlink()


def _restore_oos(*, review_tmpdir: Path, stem: str, session_env_path: str) -> None:
    for name in ("oos-accepted-review.md", "accumulated-oos.md"):
        saved = review_tmpdir / f"{stem}.{name}.before.md"
        dest = review_tmpdir / name
        if saved.is_file():
            shutil.copyfile(saved, dest)
        elif name == "oos-accepted-review.md":
            _write_text(path=dest, text="")
    parent = _parent_dir(session_env_path=session_env_path, review_tmpdir=review_tmpdir)
    if parent:
        for name in ("oos-accepted-review.md", "accumulated-oos.md"):
            saved = review_tmpdir / f"{stem}.parent-{name}.before.md"
            if saved.is_file():
                shutil.copyfile(saved, parent / name)


def _collector_success_count(path: Path) -> int:
    return sum(1 for record in _collector_records(path) if record.get("STATUS") in {"OK", "cap_hit"})


def _static_slug_for_file(file: str) -> str | None:
    from larch.review.review_threshold import _normalize_output_base as _norm_base  # noqa: PLC0415
    base = _norm_base(file)
    if base == "codex-generalist-output.txt":
        return "generalist"
    match = re.match(r"^(?:cursor|codex)-specialist-(.+)-output\.txt$", base)
    return match.group(1) if match else None


def _straggler_excused_static_slugs(dropped_file: Path) -> set[str]:
    straggler_slugs: set[str] = set()
    genuine_failure_slugs: set[str] = set()
    if not dropped_file.is_file():
        return set()
    for line in dropped_file.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = [*line.split("\t"), "", "", ""]
        slot, tool, reason = parts[0], parts[1], parts[2]
        if not slot or slot.startswith("dyn-") or tool not in {"codex", "cursor"}:
            continue
        if reason == "straggler-dropped":
            straggler_slugs.add(slot)
        else:
            genuine_failure_slugs.add(slot)
    return straggler_slugs - genuine_failure_slugs


def _tool_absent_excused_static_slugs(*, dropped_file: Path, collector_success: set[str]) -> set[str]:
    """Excuse a slug only when tool-absent is the sole drop reason and a surviving vendor has collector OK/cap_hit."""
    if not dropped_file.is_file():
        return set()
    tool_absent_slugs: set[str] = set()
    other_failure_slugs: set[str] = set()
    for line in dropped_file.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = [*line.split("\t"), "", "", ""]
        slot, tool, reason = parts[0], parts[1], parts[2]
        if not slot or slot.startswith("dyn-") or tool not in {"codex", "cursor"}:
            continue
        if reason == "tool-absent":
            tool_absent_slugs.add(slot)
        elif reason != "straggler-dropped":
            other_failure_slugs.add(slot)
    return {slug for slug in tool_absent_slugs if slug in collector_success and slug not in other_failure_slugs}


def _static_coverage_reason(*,
    collector: Path,
    manifest: Path,
    outputs: Sequence[str],
    dropped_slots_file: str = "",
) -> str:
    from larch.review.review_pipeline_shared import STATIC_REVIEWERS  # noqa: PLC0415
    from larch.review.review_threshold import _normalize_output_base as _norm_base  # noqa: PLC0415
    success: set[str] = set()
    collector_success: set[str] = set()
    rejected: set[str] = set()
    returned_statuses_by_slug: dict[str, list[str]] = {}
    for record in _collector_records(collector):
        base = Path(record.get("REVIEWER_FILE", "")).name
        slug = _static_slug_for_file(base)
        if not slug:
            continue
        status = record.get("STATUS", "")
        returned_statuses_by_slug.setdefault(slug, []).append(status)
        if status in {"OK", "cap_hit"}:
            collector_success.add(slug)
            success.add(slug)
        else:
            rejected.add(_norm_base(base))
    not_substantive_covered: set[str] = {
        slug
        for slug, statuses in returned_statuses_by_slug.items()
        if statuses and all(status == "NOT_SUBSTANTIVE" for status in statuses)
    }
    from larch.review.review_threshold import _output_file_success  # noqa: PLC0415
    for output in outputs:
        base = Path(output).name
        slug = _static_slug_for_file(base)
        if slug and _norm_base(base) not in rejected and _output_file_success(Path(output)):
            success.add(slug)
    expected: set[str] = set()
    if manifest.is_file():
        for row in _manifest_rows(manifest):
            if "agent" not in row:
                continue
            slug = _static_slug_for_file(Path(str(row.get("output") or "")).name)
            if slug:
                expected.add(slug)
    else:
        expected.update(STATIC_REVIEWERS)
    dropped_path = Path(dropped_slots_file) if dropped_slots_file else None
    excused = _straggler_excused_static_slugs(dropped_path) if dropped_path else set()
    if dropped_path:
        excused |= _tool_absent_excused_static_slugs(dropped_file=dropped_path, collector_success=collector_success)
    missing = sorted((expected - success - not_substantive_covered) - excused)
    return f"no successful static reviewer for archetype(s): {','.join(missing)}" if missing else ""


def _record_classification(*, review_tmpdir: Path, round_num: int, classification_file: str) -> tuple[tuple[str, object], ...]:
    if not classification_file:
        return ()
    map_file = review_tmpdir / "findings-classification-round-map.env"
    existing: list[str] = []
    round_key = f"FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_{round_num}"
    if map_file.is_file():
        existing = [line for line in map_file.read_text(encoding="utf-8", errors="replace").splitlines() if not line.startswith("FINDINGS_CLASSIFICATION_TSV_FILE=") and not line.startswith(round_key + "=")]
    existing.extend([f"FINDINGS_CLASSIFICATION_TSV_FILE={classification_file}", f"{round_key}={classification_file}"])
    _write_text(path=map_file, text="\n".join(existing) + "\n")
    return (("FINDINGS_CLASSIFICATION_TSV_FILE", classification_file), (round_key, classification_file))


def _record_prune_round(*, prune_ledger: str, round_num: int, panel_manifest: str, classification_file: str, label_map: Path | None = None) -> tuple[tuple[str, object], ...]:
    if not prune_ledger or not panel_manifest or not classification_file:
        return ()
    manifest = Path(panel_manifest)
    classification = Path(classification_file)
    if not manifest.is_file() or not classification.is_file():
        return ()
    try:
        reviewer_prune_record(ledger=Path(prune_ledger), round_num=round_num, manifest=manifest, classification=classification, label_map=label_map)
    except Exception as exc:
        return (("WARN", f"reviewer-prune record failed for round {round_num}: {exc}"),)
    return ()


def _ensure_prune_sidecars(*, review_tmpdir: Path, round_num: int) -> None:
    if not (review_tmpdir / "prune-decision.env").is_file():
        write_prune_decision_env(dest=review_tmpdir / "prune-decision.env", round_num=round_num, prune_active="false", prune_status="skipped", panel_full=0, eligible=0, pruned_count=0, pruned_combos="", panel_pruned_empty="false")
    if not (review_tmpdir / "prune-nit.env").is_file():
        _write_text(path=review_tmpdir / "prune-nit.env", text="PRUNED_COUNT=0\nINSCOPE_REMAINING=0\nSTATUS=skipped\n")



def _ballot_block_count(ballot_file: Path) -> int | None:
    try:
        text = ballot_file.read_text(encoding="utf-8", errors="replace")
        return sum(1 for line in text.splitlines() if voting.BALLOT_HEADING_RE.match(line))
    except (OSError, ValueError):
        return None


def _log_review_core_issue(*, review_tmpdir: Path, message: str) -> None:
    with contextlib.suppress(OSError):
        _append_text(path=review_tmpdir / "execution-issues.md", text=f"REVIEW CORE WARNING: {message}\n")

def _write_proposer_sidecar_and_neutralize(*, ballot_file: Path, proposer_map: Path) -> None:
    voting.write_proposer_map(ballot_file=ballot_file, map_file=proposer_map)
    ballot_text = ballot_file.read_text(encoding="utf-8", errors="replace")
    _write_text(path=ballot_file, text=voting.neutralize_reviewer_attribution(text=ballot_text))


def _flush_round_log(*, review_tmpdir: Path, run_id: str, round_num: int) -> None:
    implement = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not run_id or not implement or not Path(implement).is_dir():
        return
    _ensure_prune_sidecars(review_tmpdir=review_tmpdir, round_num=round_num)
    _run_python_cli(
        ["run-log", "write-round", "--log-root", str(Path(implement) / "larch-logs"), "--skill", "implement", "--run-id", run_id, "--round", str(round_num), "--source-dir", str(review_tmpdir)]
    )


def _parse_nonnegative_int(value: str, *, default: int = 0) -> int:
    return int(value) if value.isdigit() else default


def _append_threshold_dispatch_metadata(*, threshold_out: Path, dispatch: Mapping[str, str]) -> None:
    lines: list[str] = []
    for key in ("STRAGGLER_DROPPED_COUNT", "WATERFALL_WARN"):
        value = dispatch.get(key, "")
        if value:
            lines.append(f"{key}={value}")
    if lines:
        prior = threshold_out.read_text(encoding="utf-8", errors="replace") if threshold_out.is_file() else ""
        prefix = "" if not prior or prior.endswith("\n") else "\n"
        _append_text(path=threshold_out, text=prefix + "\n".join(lines) + "\n")


def _finalize_dropped_reviewer_round(*, review_tmpdir: Path) -> None:
    """Keep only already-curated dropped-reviewer diagnostics for round-log staging."""
    for path in review_tmpdir.glob("dropped-*-*.txt"):
        if path.is_file() and path.stat().st_size > 0:
            continue


def _parseable_review_output_present(*, review_tmpdir: Path) -> bool:
    return any((review_tmpdir / name).is_file() and (review_tmpdir / name).stat().st_size > 0 for name in ("findings.md", "oos.md"))


def _zero_survivor_reason_protected(reason: str) -> bool:
    protected_prefixes = (
        "dispatch-panel",
        "no successful static reviewer",
        "tally-code-votes",
        "proposer-map",
        "findings-pre-aggregate",
        "aggregation-validation-exhausted",
    )
    return any(reason.startswith(prefix) for prefix in protected_prefixes)


def _rewrite_threshold_env(*, threshold_out: Path, threshold_ok: str, threshold_reason: str) -> None:
    lines = threshold_out.read_text(encoding="utf-8", errors="replace").splitlines() if threshold_out.is_file() else []
    updated: list[str] = []
    seen_ok = False
    seen_reason = False
    seen_coverage_ok = False
    seen_coverage_reason = False
    for line in lines:
        if line.startswith("THRESHOLD_OK="):
            updated.append(f"THRESHOLD_OK={threshold_ok}")
            seen_ok = True
        elif line.startswith("THRESHOLD_REASON="):
            updated.append(f"THRESHOLD_REASON={threshold_reason}")
            seen_reason = True
        elif line.startswith("COVERAGE_GATE_OK="):
            updated.append("COVERAGE_GATE_OK=false")
            seen_coverage_ok = True
        elif line.startswith("COVERAGE_GATE_REASON="):
            updated.append(f"COVERAGE_GATE_REASON={threshold_reason}")
            seen_coverage_reason = True
        else:
            updated.append(line)
    if not seen_ok:
        updated.append(f"THRESHOLD_OK={threshold_ok}")
    if not seen_reason:
        updated.append(f"THRESHOLD_REASON={threshold_reason}")
    if not seen_coverage_ok:
        updated.append("COVERAGE_GATE_OK=false")
    if not seen_coverage_reason:
        updated.append(f"COVERAGE_GATE_REASON={threshold_reason}")
    _write_text(path=threshold_out, text="\n".join(updated) + "\n")


def _normalize_zero_survivor_threshold(
    *,
    review_tmpdir: Path,
    collector_results: Path,
    threshold_out: Path,
    threshold_ok: str,
    threshold_reason: str,
) -> tuple[str, str, bool]:
    """Normalize all-launched-reviewer runtime collapse to the shared discriminator."""
    success_count = _collector_success_count(collector_results)
    parseable = _parseable_review_output_present(review_tmpdir=review_tmpdir)
    if success_count != 0:
        return threshold_ok, threshold_reason, False
    if parseable:
        _append_text(path=threshold_out, text="COVERAGE_GATE_OK=true\nCOVERAGE_GATE_REASON=parseable reviewer output present\n")
        return threshold_ok, threshold_reason, True
    if _zero_survivor_reason_protected(threshold_reason):
        return threshold_ok, threshold_reason, False
    threshold_ok = "false"
    threshold_reason = "no successful launched reviewer output"
    _rewrite_threshold_env(threshold_out=threshold_out, threshold_ok=threshold_ok, threshold_reason=threshold_reason)
    return threshold_ok, threshold_reason, True


def _core_common_rows(*, status: str, round_num: int, review_tmpdir: Path, panel_mode: str, panel_shape: str, accepted: str = "0", rejected: str = "0", exonerated: str = "0", neutral: str = "0", oos_drift: str = "0", accepted_file: Path | None = None, threshold_reason: str = "") -> tuple[tuple[str, object], ...]:
    rows: list[tuple[str, object]] = [
        ("REVIEW_CORE_STATUS", status),
        ("ROUND_NUM", round_num),
        ("ACCEPTED_COUNT", accepted),
        ("REJECTED_COUNT", rejected),
        ("EXONERATED_COUNT", exonerated),
        ("NEUTRAL_COUNT", neutral),
        ("OUT_OF_SCOPE_DRIFT_COUNT", oos_drift),
        ("FINDINGS_FILE", review_tmpdir / "findings.md"),
        ("ACCEPTED_FINDINGS_FILE", accepted_file or review_tmpdir / "accepted-findings.md"),
        ("REJECTED_FINDINGS_FILE", review_tmpdir / "rejected-findings.md"),
        ("PANEL_MODE", panel_mode),
        ("PANEL_SHAPE", panel_shape),
    ]
    if threshold_reason or status == "panel-failed":
        rows.append(("THRESHOLD_REASON", threshold_reason))
    return tuple(rows)


def _post_gate_panel_failed_exit(  # noqa: PLR0913,RUF100
    *,
    rows: list[tuple[str, object]],
    review_tmpdir: Path,
    run_id: str,
    round_num: int,
    panel_mode: str,
    panel_shape: str,
    threshold_reason: str,
) -> ReviewCoreResult:
    _flush_round_log(review_tmpdir=review_tmpdir, run_id=run_id, round_num=round_num)
    rows.extend(
        _core_common_rows(
            status="panel-failed",
            round_num=round_num,
            review_tmpdir=review_tmpdir,
            panel_mode=panel_mode,
            panel_shape=panel_shape,
            threshold_reason=threshold_reason,
        )
    )
    return ReviewCoreResult(2, ReviewCoreStatus.panel_failed, tuple(rows))


def _prune_nits_for_ballot(
    *,
    commands: ReviewCommands,
    review_tmpdir: Path,
    runner: object = None,
    findings_file: Path | None = None,
    session_env_path: str = "",
) -> object:
    _ = runner
    ballot_file = findings_file or review_tmpdir / "findings.md"
    prune_result = _call_maybe_override(
        command=commands.prune_nits,
        review_name="prune-nit-findings",
        args=[
            "--findings-file",
            str(ballot_file),
            "--audit-file",
            str(review_tmpdir / "oos-dropped-before-vote.md"),
            "--security-audit-file",
            str(
                (Path(session_env_path).parent if session_env_path else review_tmpdir)
                / "security-oos-observations.md"
            ),
        ],
    )
    _write_text(path=review_tmpdir / "review-core-prune-nit.env", text=prune_result.stdout)
    _write_text(path=review_tmpdir / "prune-nit.env", text=prune_result.stdout or "PRUNED_COUNT=0\nINSCOPE_REMAINING=0\nSTATUS=skipped\n")
    pruned_count = _kv_parse(prune_result.stdout).get("PRUNED_COUNT", "0")
    if pruned_count != "0":
        logging_util.diagnostic(f"→ review: nit filter dropped {pruned_count} finding(s) before vote")
    return prune_result


def _emit_core_common(*, status: str, round_num: int, review_tmpdir: Path, panel_mode: str, panel_shape: str, accepted: str = "0", rejected: str = "0", exonerated: str = "0", neutral: str = "0", oos_drift: str = "0", accepted_file: Path | None = None, threshold_reason: str = "") -> None:
    for key, value in _core_common_rows(status=status, round_num=round_num, review_tmpdir=review_tmpdir, panel_mode=panel_mode, panel_shape=panel_shape, accepted=accepted, rejected=rejected, exonerated=exonerated, neutral=neutral, oos_drift=oos_drift, accepted_file=accepted_file, threshold_reason=threshold_reason):
        _emit_kv(key=key, value=value)


def _emit_review_core_result(result: ReviewCoreResult) -> int:
    for key, value in result.rows:
        _emit_kv(key=key, value=value)
    return result.rc


def _emit_tally(*, commands: ReviewCommands, args: Sequence[str], out_file: Path, runner: object = None) -> dict[str, str]:
    if commands.emit:
        result = _run_command_string(command=commands.emit, args=args)
    else:
        from larch.review.review_pipeline_shared import _call_review_command  # noqa: PLC0415
        result = _call_review_command(name="emit-tally", args=args)
    _write_text(path=out_file, text=result.stdout)
    if result.stderr:
        for line in result.stderr.splitlines():
            logging_util.diagnostic(line)
    return _kv_parse(result.stdout)


def _emit_tally_with_context(
    *,
    commands: ReviewCommands,
    args: list[str],
    out_file: Path,
    session_env_path: str,
) -> dict[str, str]:
    if session_env_path:
        args.extend(["--session-env-path", session_env_path])
    implement_tmpdir = os.environ.get(config.ENV_IMPLEMENT_TMPDIR)
    if implement_tmpdir:
        args.extend(["--implement-tmpdir", implement_tmpdir])
    return _emit_tally(commands=commands, args=args, out_file=out_file)


def _zero_findings_branch(*,  # noqa: PLR0913,RUF100
    commands: ReviewCommands,
    review_tmpdir: Path,
    round_num: int,
    mode: str,
    cursor_available: str,
    codex_available: str,
    session_env_path: str,
    panel_manifest: str,
    collector_results: Path,
    not_substantive: int,
    panel_mode: str,
    panel_shape: str,
    scout_status: str,
    dynamic_slots: str,
    static_slot_count: str,
    run_id: str,
    prune_ledger: str,
    prefix_rows: Sequence[tuple[str, object]] = (),
    runner: object = None,
) -> ReviewCoreResult:
    rows: list[tuple[str, object]] = list(prefix_rows)
    voter = review_tmpdir / "zero-findings-voter.txt"
    _write_text(path=voter, text="")
    tally_args = [
        "--ballot-file",
        str(review_tmpdir / "findings.md"),
        "--review-tmpdir",
        str(review_tmpdir),
        "--cursor-available",
        cursor_available,
        "--codex-available",
        codex_available,
        "--round-num",
        str(round_num),
        "--voter-files",
        str(voter),
    ]
    if session_env_path:
        tally_args.extend(["--session-env-path", session_env_path])
    if panel_manifest and Path(panel_manifest).is_file():
        tally_args.extend(["--manifest-file", panel_manifest])
    if collector_results.is_file():
        tally_args.extend(["--collector-results-file", str(collector_results)])
    if not_substantive:
        tally_args.extend(["--not-substantive-count", str(not_substantive)])
    _snapshot_oos(review_tmpdir=review_tmpdir, stem="zero-findings", session_env_path=session_env_path)
    tally_result = _run_command_string(command=commands.tally, args=tally_args) if commands.tally else _call_maybe_override(command="", review_name="tally-code-votes", args=tally_args)
    tally_out = review_tmpdir / "review-core-zero-findings-tally.env"
    _write_text(path=tally_out, text=tally_result.stdout)
    tally = _kv_parse(tally_result.stdout)
    classification = tally.get("FINDINGS_CLASSIFICATION_TSV_FILE", "")
    rows.extend(_record_classification(review_tmpdir=review_tmpdir, round_num=round_num, classification_file=classification))
    if classification and Path(classification).is_file():
        rows.extend(_record_prune_round(prune_ledger=prune_ledger, round_num=round_num, panel_manifest=panel_manifest, classification_file=classification))
    _write_text(path=review_tmpdir / "accepted-findings.md", text="")
    _write_text(path=review_tmpdir / "rejected-findings.md", text="")
    _write_text(path=review_tmpdir / "oos-accepted-review.md", text="")
    emit_args = [
        "--tally-file",
        tally.get("TALLY_FILE", str(review_tmpdir / "review-tally.env")),
        "--accepted-findings-file",
        tally.get("ACCEPTED_FINDINGS_FILE", str(review_tmpdir / "accepted-findings.md")),
        "--oos-file",
        str(review_tmpdir / "oos.md"),
        "--review-tmpdir",
        str(review_tmpdir),
        "--round",
        str(round_num),
        "--mode",
        mode,
        "--scout-status",
        scout_status,
        "--dynamic-slots",
        dynamic_slots,
        "--static-slot-count",
        static_slot_count,
    ]
    _emit_tally_with_context(commands=commands, args=emit_args, out_file=review_tmpdir / "review-core-zero-findings-emit.env", session_env_path=session_env_path)
    _copy_to_parent(file=review_tmpdir / "rejected-findings.md", name="rejected-findings.md", session_env_path=session_env_path)
    _restore_oos(review_tmpdir=review_tmpdir, stem="zero-findings", session_env_path=session_env_path)
    _flush_round_log(review_tmpdir=review_tmpdir, run_id=run_id, round_num=round_num)
    rows.extend(_core_common_rows(status="zero-findings", round_num=round_num, review_tmpdir=review_tmpdir, panel_mode=panel_mode, panel_shape=panel_shape))
    voting_tally = tally.get("VOTING_TALLY_FILE", "")
    if voting_tally:
        rows.append(("VOTING_TALLY_FILE", voting_tally))
    return ReviewCoreResult(0, ReviewCoreStatus.zero_findings, tuple(rows))


def _zero_findings_from_context(ctx: ReviewCoreBranchContext, *, ballot_prefix: Sequence[tuple[str, object]] = ()) -> ReviewCoreResult:
    zero = _zero_findings_branch(
        commands=ctx.commands,
        review_tmpdir=ctx.review_tmpdir,
        round_num=ctx.round_num,
        mode=ctx.mode,
        cursor_available=ctx.cursor_available,
        codex_available=ctx.codex_available,
        session_env_path=ctx.session_env_path,
        panel_manifest=ctx.panel_manifest,
        collector_results=ctx.collector_results,
        not_substantive=ctx.not_substantive,
        panel_mode=ctx.panel_mode,
        panel_shape=ctx.panel_shape,
        scout_status=ctx.scout_status,
        dynamic_slots=ctx.dynamic_slots,
        static_slot_count=ctx.static_slot_count,
        run_id=ctx.run_id,
        prune_ledger=ctx.prune_ledger,
        prefix_rows=ballot_prefix,
        runner=ctx.runner,
    )
    return ReviewCoreResult(0, zero.status, tuple(ctx.rows) + zero.rows)


def _post_gate_panel_failed_exit_from_context(ctx: ReviewCoreBranchContext, *, threshold_reason: str) -> ReviewCoreResult:
    return _post_gate_panel_failed_exit(
        rows=ctx.rows,
        review_tmpdir=ctx.review_tmpdir,
        run_id=ctx.run_id,
        round_num=ctx.round_num,
        panel_mode=ctx.panel_mode,
        panel_shape=ctx.panel_shape,
        threshold_reason=threshold_reason,
    )


def _dispatch_voters_for_ballot(ctx: ReviewCoreBranchContext) -> tuple[list[str], list[str], dict[str, str]]:
    voter_args = [
        "--ballot-file",
        str(ctx.review_tmpdir / "findings.md"),
        "--review-tmpdir",
        str(ctx.review_tmpdir),
        "--codex-available",
        ctx.codex_available,
        "--cursor-available",
        ctx.cursor_available,
        "--round-num",
        str(ctx.round_num),
        "--site",
        ctx.site,
    ]
    if ctx.session_env_path:
        voter_args.extend(["--session-env-path", ctx.session_env_path])
    if ctx.diff_file:
        voter_args.extend(["--diff-file", ctx.diff_file])
    if ctx.plan_file:
        voter_args.extend(["--plan-file", ctx.plan_file])
    voters_result = _run_command_string(command=ctx.commands.dispatch_voters, args=voter_args) if ctx.commands.dispatch_voters else _run_python_cli(["agent", "dispatch-voters", *voter_args])
    voters = _kv_parse(voters_result.stdout)
    _write_text(path=ctx.review_tmpdir / "review-core-voters.env", text=voters_result.stdout)
    voter_files: list[str] = []
    voter_tools: list[str] = []
    rows = ctx.rows if ctx.rows is not None else []
    for idx, default_tool in enumerate(("codex-validity", "codex-plan-fidelity", "codex-pragmatism"), start=1):
        path = voters.get(f"VOTER_{idx}_PATH", "")
        status = voters.get(f"VOTER_{idx}_STATUS", "")
        tool = voters.get(f"VOTER_{idx}_TOOL", default_tool) or default_tool
        voter_tools.append(tool)
        voter_files.append(path if status not in {"failed", "skipped"} and path and Path(path).is_file() and Path(path).stat().st_size else "")
        if voters.get(f"VOTER_{idx}_TOOL"):
            rows.append((f"VOTER_{idx}_TOOL", voters[f"VOTER_{idx}_TOOL"]))
        if status:
            rows.append((f"VOTER_{idx}_STATUS", status))
    return voter_files, voter_tools, voters


def _tally_voted_ballot(ctx: ReviewCoreBranchContext, *, proposer_map: Path, voter_files: list[str], voter_tools: list[str], out_name: str) -> tuple[proc.CommandResult, dict[str, str]]:
    tally_args = [
        "--ballot-file",
        str(ctx.review_tmpdir / "findings.md"),
        "--review-tmpdir",
        str(ctx.review_tmpdir),
        "--cursor-available",
        ctx.cursor_available,
        "--codex-available",
        ctx.codex_available,
        "--round-num",
        str(ctx.round_num),
        "--proposer-map-file",
        str(proposer_map),
    ]
    if ctx.session_env_path:
        tally_args.extend(["--session-env-path", ctx.session_env_path])
    if ctx.scope_files and Path(ctx.scope_files).is_file() and Path(ctx.scope_files).stat().st_size:
        tally_args.extend(["--scope-files", ctx.scope_files])
    if ctx.plan_file and Path(ctx.plan_file).is_file():
        tally_args.extend(["--plan-file", ctx.plan_file])
    if ctx.panel_manifest and Path(ctx.panel_manifest).is_file():
        tally_args.extend(["--manifest-file", ctx.panel_manifest])
    if ctx.collector_results.is_file():
        tally_args.extend(["--collector-results-file", str(ctx.collector_results)])
    if ctx.not_substantive:
        tally_args.extend(["--not-substantive-count", str(ctx.not_substantive)])
    tally_args.extend(["--voter-files", *voter_files, "--voter-tools", *voter_tools])
    tally_result = _run_command_string(command=ctx.commands.tally, args=tally_args) if ctx.commands.tally else _call_maybe_override(command="", review_name="tally-code-votes", args=tally_args)
    tally = _kv_parse(tally_result.stdout)
    _write_text(path=ctx.review_tmpdir / out_name, text=tally_result.stdout)
    return tally_result, tally


def _prepare_pruned_ballot(ctx: ReviewCoreBranchContext, *, findings_file: Path | None = None) -> ReviewCoreResult | None:
    _prune_nits_for_ballot(
        commands=ctx.commands,
        review_tmpdir=ctx.review_tmpdir,
        runner=ctx.runner,
        findings_file=findings_file,
        session_env_path=ctx.session_env_path,
    )
    ballot_file = findings_file or ctx.review_tmpdir / "findings.md"
    block_count = _ballot_block_count(ballot_file)
    if block_count is None:
        return _post_gate_panel_failed_exit_from_context(ctx, threshold_reason="ballot-read-failed")
    if block_count == 0:
        return _zero_findings_from_context(ctx)
    return None


def _handle_validation_exhausted_after_gate(ctx: ReviewCoreBranchContext) -> ReviewCoreResult:
    empty = _prepare_pruned_ballot(ctx)
    if empty is not None:
        return empty

    proposer_map = ctx.review_tmpdir / "proposer-map.tsv"
    try:
        _write_proposer_sidecar_and_neutralize(ballot_file=ctx.review_tmpdir / "findings.md", proposer_map=proposer_map)
    except (OSError, ValueError) as exc:
        logging_util.diagnostic(f"→ review: proposer map preparation failed: {exc}")
        return _post_gate_panel_failed_exit_from_context(ctx, threshold_reason="proposer-map-failed")
    voter_files, voter_tools, _voters = _dispatch_voters_for_ballot(ctx)
    tally_result, tally = _tally_voted_ballot(ctx, proposer_map=proposer_map, voter_files=voter_files, voter_tools=voter_tools, out_name="review-core-aggregator-exhaust-tally.env")
    if tally_result.returncode != 0 and not tally.get("TALLY_STATUS"):
        return _post_gate_panel_failed_exit_from_context(ctx, threshold_reason="tally-code-votes failed")
    classification = tally.get("FINDINGS_CLASSIFICATION_TSV_FILE", "")
    rows = ctx.rows if ctx.rows is not None else []
    rows.extend(_record_classification(review_tmpdir=ctx.review_tmpdir, round_num=ctx.round_num, classification_file=classification))
    emit_args = ["--tally-file", str(ctx.review_tmpdir / "review-core-aggregator-exhaust-tally.env"), "--accepted-findings-file", str(ctx.review_tmpdir / "accepted-findings.md"), "--oos-file", str(ctx.review_tmpdir / "oos.md"), "--review-tmpdir", str(ctx.review_tmpdir), "--round", str(ctx.round_num), "--mode", ctx.mode, "--scout-status", ctx.scout_status, "--dynamic-slots", ctx.dynamic_slots, "--static-slot-count", ctx.static_slot_count]
    _emit_tally_with_context(commands=ctx.commands, args=emit_args, out_file=ctx.review_tmpdir / "review-core-aggregator-exhaust-emit.env", session_env_path=ctx.session_env_path)
    _flush_round_log(review_tmpdir=ctx.review_tmpdir, run_id=ctx.run_id, round_num=ctx.round_num)
    rows.extend(_core_common_rows(status="aggregator-validation-exhausted", round_num=ctx.round_num, review_tmpdir=ctx.review_tmpdir, panel_mode=ctx.panel_mode, panel_shape=ctx.panel_shape, threshold_reason="aggregation-validation-exhausted"))
    if classification:
        rows.append(("FINDINGS_CLASSIFICATION_TSV_FILE", classification))
    return ReviewCoreResult(2, ReviewCoreStatus.aggregator_validation_exhausted, tuple(rows))


def _handle_empty_merge_after_gate(ctx: ReviewCoreBranchContext, *, findings_count: str, pre_aggregate_snapshot: Path) -> ReviewCoreResult | None:
    if findings_count == "0":
        return _zero_findings_from_context(ctx)
    if not pre_aggregate_snapshot.is_file():
        return _post_gate_panel_failed_exit_from_context(ctx, threshold_reason="findings-pre-aggregate-snapshot-missing")
    empty = _prepare_pruned_ballot(ctx, findings_file=pre_aggregate_snapshot)
    if empty is not None:
        return empty
    try:
        shutil.copyfile(pre_aggregate_snapshot, ctx.review_tmpdir / "findings.md")
    except OSError as exc:
        _log_review_core_issue(review_tmpdir=ctx.review_tmpdir, message=f"ballot promote failed: {exc}")
        return _post_gate_panel_failed_exit_from_context(ctx, threshold_reason="ballot-promote-failed")
    return None


def _run_normal_prune(ctx: ReviewCoreBranchContext) -> ReviewCoreResult | None:
    return _prepare_pruned_ballot(ctx)


def _review_core_body(
    parsed: Mapping[str, str | list[str]],
    *,
    mode: str,
    review_tmpdir: Path,
    codex_available: str,
    cursor_available: str,
    panel: str,
    tier: str = "",
    escalated_round: str = "false",
    dynamic: str,
    round_num: int,
    session_env_path: str,
    run_id: str,
    prune_ledger: str,
    site: str,
    runner: object = None,
    commands: ReviewCommands | None = None,
) -> ReviewCoreResult:
    commands = commands or _review_commands()
    tier = difficulty.normalize_tier(tier) or (difficulty.TRIVIAL if panel == "simple" else difficulty.MODERATE)
    panel = difficulty.threshold_panel_for_tier(tier)
    review_tmpdir.mkdir(parents=True, exist_ok=True)

    gather_args = ["--mode", mode, "--output-dir", str(review_tmpdir)]
    if _get(parsed=parsed, key="--description-text"):
        gather_args.extend(["--description-text", _get(parsed=parsed, key="--description-text")])
    if _get(parsed=parsed, key="--scope-files"):
        gather_args.extend(["--scope-files", _get(parsed=parsed, key="--scope-files")])
    gather_result = _call_maybe_override(command=commands.gather, review_name="gather-context", args=gather_args)
    gather_out = review_tmpdir / "review-core-gather.env"
    _write_text(path=gather_out, text=gather_result.stdout)
    gather = _kv_parse(gather_result.stdout)
    diff_file = _get(parsed=parsed, key="--diff-file") or gather.get("DIFF_FILE", "")
    scope_files = _get(parsed=parsed, key="--scope-files") or gather.get("FILE_LIST_FILE", "")
    commit_count = _get(parsed=parsed, key="--commit-count") or gather.get("COMMIT_COUNT", "0")
    mode = gather.get("MODE", mode) or "diff"
    if mode == "description" and gather.get("SCOPE_FILES_COUNT", "0") == "0":
        for name in ("findings.md", "accepted-findings.md", "rejected-findings.md", "oos-accepted-review.md"):
            _write_text(path=review_tmpdir / name, text="")
        _flush_round_log(review_tmpdir=review_tmpdir, run_id=run_id, round_num=round_num)
        rows = [
            ("SCOUT_STATUS", "na"),
            ("DYNAMIC_SLOTS", "0"),
            ("SCOUT_MANIFEST", ""),
            *_core_common_rows(status="zero-findings", round_num=round_num, review_tmpdir=review_tmpdir, panel_mode="normal", panel_shape=panel),
        ]
        return ReviewCoreResult(0, ReviewCoreStatus.zero_findings, tuple(rows))

    dispatch_args = [
        "--mode",
        mode,
        "--review-tmpdir",
        str(review_tmpdir),
        "--panel",
        panel,
        "--tier",
        tier,
        "--escalated-round",
        escalated_round,
        "--codex-available",
        codex_available,
        "--cursor-available",
        cursor_available,
        "--commit-count",
        commit_count or "0",
        "--timing-task-prefix",
        f"review-round{round_num}",
        "--dynamic-archetypes",
        dynamic,
        "--round-num",
        str(round_num),
        "--site",
        site,
    ]
    for value, flag in ((diff_file, "--diff-file"), (scope_files, "--scope-files"), (_get(parsed=parsed, key="--plan-file"), "--plan-file"), (_get(parsed=parsed, key="--feature-file"), "--feature-file"), (_get(parsed=parsed, key="--description-text"), "--description-text"), (session_env_path, "--session-env-path"), (prune_ledger, "--prune-ledger"), (_get(parsed=parsed, key="--pre-scouted-manifest"), "--pre-scouted-manifest")):
        if value:
            dispatch_args.extend([flag, value])
    competition = review_tmpdir / "competition-notice.md"
    if competition.is_file():
        dispatch_args.extend(["--competition-notice-file", str(competition)])
    _progress_note(step="5", text="reviewer panel dispatch running")
    dispatch_result = _call_maybe_override(command=commands.dispatch, review_name="dispatch-panel", args=dispatch_args)
    dispatch_out = review_tmpdir / "review-core-dispatch.env"
    _write_text(path=dispatch_out, text=dispatch_result.stdout)
    if dispatch_result.returncode != 0:
        _ensure_prune_sidecars(review_tmpdir=review_tmpdir, round_num=round_num)
        _flush_round_log(review_tmpdir=review_tmpdir, run_id=run_id, round_num=round_num)
        dispatch_failure_rows = _core_common_rows(status="panel-failed", round_num=round_num, review_tmpdir=review_tmpdir, panel_mode="normal", panel_shape=panel, threshold_reason=f"dispatch-panel exited rc={dispatch_result.returncode}")
        return ReviewCoreResult(2, ReviewCoreStatus.panel_failed, dispatch_failure_rows)
    dispatch = _kv_parse(dispatch_result.stdout)
    external_outputs = dispatch.get("EXTERNAL_OUTPUT_FILES", "")
    claude_outputs = dispatch.get("CLAUDE_OUTPUT_FILES", "")
    panel_mode = dispatch.get("PANEL_MODE", "waterfall")
    panel_shape = dispatch.get("PANEL_SHAPE", panel)
    panel_tier = dispatch.get("PANEL_TIER", tier)
    panel_manifest = dispatch.get("PANEL_MANIFEST", "")
    scout_status = dispatch.get("SCOUT_STATUS", "na")
    scout_fail_reason = dispatch.get("SCOUT_FAIL_REASON", "")
    dynamic_slots = dispatch.get("DYNAMIC_SLOTS", "0")
    static_slot_count = dispatch.get("STATIC_SLOT_COUNT", "0")
    panel_pruned_empty = dispatch.get("PANEL_PRUNED_EMPTY", "false")
    prune_status = dispatch.get("PRUNE_STATUS", "")
    scout_manifest = dispatch.get("SCOUT_MANIFEST", "")
    _write_text(
        path=review_tmpdir / f"scout-round{round_num}-status.env",
        text=f"SCOUT_STATUS={scout_status}\n" + (f"SCOUT_FAIL_REASON={scout_fail_reason}\n" if scout_fail_reason else "") + f"DYNAMIC_SLOTS={dynamic_slots}\nSCOUT_MANIFEST={scout_manifest}\n",
    )
    dispatch_scout_rows: tuple[tuple[str, object], ...] = (
        (("SCOUT_STATUS", scout_status),)
        + ((("SCOUT_FAIL_REASON", scout_fail_reason),) if scout_fail_reason else ())
        + (("DYNAMIC_SLOTS", dynamic_slots),)
        + ((("SCOUT_MANIFEST", scout_manifest),) if scout_manifest else ())
        + ((("PRUNED_COMBOS", dispatch["PRUNED_COMBOS"]),) if dispatch.get("PRUNED_COMBOS") else ())
        + (("PANEL_PRUNED_EMPTY", panel_pruned_empty),)
    )
    if panel_pruned_empty == "true" and prune_status == "pruned-empty":
        _snapshot_oos(review_tmpdir=review_tmpdir, stem="prune-skipped", session_env_path=session_env_path)
        for name in ("findings.md", "accepted-findings.md", "rejected-findings.md", "oos.md", "oos-accepted-review.md"):
            _write_text(path=review_tmpdir / name, text="")
        _write_text(path=review_tmpdir / "voting-tally.md", text="# Code Review Voting Tally\n\nRound skipped: all reviewer combos pruned.\n")
        _restore_oos(review_tmpdir=review_tmpdir, stem="prune-skipped", session_env_path=session_env_path)
        _ensure_prune_sidecars(review_tmpdir=review_tmpdir, round_num=round_num)
        _flush_round_log(review_tmpdir=review_tmpdir, run_id=run_id, round_num=round_num)
        logging_util.diagnostic(f"→ review: round {round_num} skipped: all reviewer combos pruned")
        prune_skipped_rows = dispatch_scout_rows + _core_common_rows(status="prune-skipped", round_num=round_num, review_tmpdir=review_tmpdir, panel_mode=panel_mode, panel_shape=panel_shape)
        return ReviewCoreResult(0, ReviewCoreStatus.prune_skipped, prune_skipped_rows)

    rows: list[tuple[str, object]] = list(dispatch_scout_rows)
    external_array = external_outputs.split() if external_outputs else []
    claude_array = claude_outputs.split() if claude_outputs else []
    collect_args = ["--mode", mode, "--timeout", "1860", "--findings-file", str(review_tmpdir / "findings.md"), "--oos-file", str(review_tmpdir / "oos.md")]
    if session_env_path:
        collect_args.extend(["--session-env-path", session_env_path])
    if external_array:
        collect_args.append("--external-output-files")
        collect_args.extend(external_array)
    if claude_array:
        collect_args.append("--claude-output-files")
        collect_args.extend(claude_array)
    logging_util.diagnostic("→ review: consolidating findings")
    _progress_note(step="5", text="collecting reviewer outputs")
    collect_result = _call_maybe_override(command=commands.collect, review_name="collect-findings", args=collect_args)
    collect_out = review_tmpdir / "review-core-collect.env"
    _write_text(path=collect_out, text=collect_result.stdout)
    collect = _kv_parse(collect_result.stdout)
    collector_results = review_tmpdir / "collector-results.env"
    intended_slots = _parse_nonnegative_int(dispatch.get("SLOT_COUNT", ""), default=_parse_nonnegative_int(static_slot_count) + _parse_nonnegative_int(dynamic_slots))
    launched_slots = _parse_nonnegative_int(dispatch.get("LAUNCHED_SLOTS", ""), default=intended_slots)
    threshold_args = [
        "--collector-results-file",
        str(collector_results),
        "--panel",
        difficulty.threshold_panel_for_tier(panel_tier),
        "--intended-slots",
        str(intended_slots),
        "--launched-slots",
        str(launched_slots),
        "--round-num",
        str(round_num),
    ]
    dropped = dispatch.get("DROPPED_SLOTS_FILE", "")
    if dropped and Path(dropped).is_file():
        threshold_args.extend(["--dropped-slots-file", dropped])
    if panel_manifest and Path(panel_manifest).is_file():
        threshold_args.extend(["--panel-manifest", panel_manifest])
    if external_array or claude_array:
        threshold_args.append("--reviewer-output-files")
        threshold_args.extend(external_array + claude_array)
    _progress_note(step="5", text="checking reviewer failure threshold")
    threshold_result = _call_maybe_override(command=commands.threshold, review_name="check-reviewer-failure-threshold", args=threshold_args)
    threshold_out = review_tmpdir / "review-core-threshold.env"
    _write_text(path=threshold_out, text=threshold_result.stdout)
    threshold = _kv_parse(threshold_result.stdout)
    _append_threshold_dispatch_metadata(threshold_out=threshold_out, dispatch=dispatch)
    threshold = _kv_parse(threshold_out.read_text(encoding="utf-8", errors="replace"))
    _finalize_dropped_reviewer_round(review_tmpdir=review_tmpdir)
    threshold_ok = threshold.get("THRESHOLD_OK", "true")
    threshold_reason = threshold.get("THRESHOLD_REASON", "")
    not_substantive = int(threshold.get("NOT_SUBSTANTIVE_SLOTS", "0") or "0") if threshold.get("NOT_SUBSTANTIVE_SLOTS", "0").isdigit() else 0
    threshold_ok, threshold_reason, coverage_recorded = _normalize_zero_survivor_threshold(
        review_tmpdir=review_tmpdir,
        collector_results=collector_results,
        threshold_out=threshold_out,
        threshold_ok=threshold_ok,
        threshold_reason=threshold_reason,
    )
    if threshold_ok != "false":
        reason = _static_coverage_reason(
            collector=collector_results,
            manifest=Path(panel_manifest),
            outputs=external_array + claude_array,
            dropped_slots_file=dropped
        )
        if reason:
            threshold_ok = "false"
            threshold_reason = reason
            _append_text(path=threshold_out, text=f"COVERAGE_GATE_OK=false\nCOVERAGE_GATE_REASON={reason}\n")
        elif not coverage_recorded:
            _append_text(path=threshold_out, text="COVERAGE_GATE_OK=true\nCOVERAGE_GATE_REASON=static reviewer coverage satisfied\n")
    if threshold_ok == "false":
        for name in ("accepted-findings.md", "rejected-findings.md", "oos-accepted-review.md"):
            _write_text(path=review_tmpdir / name, text="")
        _write_text(path=review_tmpdir / "oos.md", text="")
        tally_file = review_tmpdir / "review-core-panel-failed-tally.env"
        _write_text(path=tally_file, text="ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\n")
        emit_args = ["--tally-file", str(tally_file), "--accepted-findings-file", str(review_tmpdir / "accepted-findings.md"), "--oos-file", str(review_tmpdir / "oos.md"), "--review-tmpdir", str(review_tmpdir), "--round", str(round_num), "--mode", mode, "--scout-status", scout_status, "--dynamic-slots", dynamic_slots, "--static-slot-count", static_slot_count]
        _emit_tally_with_context(commands=commands, args=emit_args, out_file=review_tmpdir / "review-core-panel-failed-emit.env", session_env_path=session_env_path)
        _copy_to_parent(file=review_tmpdir / "rejected-findings.md", name="rejected-findings.md", session_env_path=session_env_path)
        _copy_to_parent(file=review_tmpdir / "oos-accepted-review.md", name="oos-accepted-review.md", session_env_path=session_env_path)
        _flush_round_log(review_tmpdir=review_tmpdir, run_id=run_id, round_num=round_num)
        rows.extend(_core_common_rows(status="panel-failed", round_num=round_num, review_tmpdir=review_tmpdir, panel_mode=panel_mode, panel_shape=panel_shape, threshold_reason=threshold_reason))
        return ReviewCoreResult(2, ReviewCoreStatus.panel_failed, tuple(rows))

    findings_count = collect.get("FINDINGS_COUNT", "0")
    if findings_count == "0":
        zero = _zero_findings_branch(commands=commands, review_tmpdir=review_tmpdir, round_num=round_num, mode=mode, cursor_available=cursor_available, codex_available=codex_available, session_env_path=session_env_path, panel_manifest=panel_manifest, collector_results=collector_results, not_substantive=not_substantive, panel_mode=panel_mode, panel_shape=panel_shape, scout_status=scout_status, dynamic_slots=dynamic_slots, static_slot_count=static_slot_count, run_id=run_id, prune_ledger=prune_ledger)
        return ReviewCoreResult(0, zero.status, dispatch_scout_rows + zero.rows)

    pre_aggregate_snapshot = review_tmpdir / "findings-pre-aggregate.md"
    findings_file = review_tmpdir / "findings.md"
    _prune_nits_for_ballot(
        commands=commands,
        review_tmpdir=review_tmpdir,
        findings_file=findings_file,
        session_env_path=session_env_path,
    )
    post_prune_count = _ballot_block_count(findings_file)
    if post_prune_count is None:
        return _post_gate_panel_failed_exit(
            rows=rows,
            review_tmpdir=review_tmpdir,
            run_id=run_id,
            round_num=round_num,
            panel_mode=panel_mode,
            panel_shape=panel_shape,
            threshold_reason="ballot-read-failed",
        )
    if post_prune_count == 0:
        zero = _zero_findings_branch(
            commands=commands,
            review_tmpdir=review_tmpdir,
            round_num=round_num,
            mode=mode,
            cursor_available=cursor_available,
            codex_available=codex_available,
            session_env_path=session_env_path,
            panel_manifest=panel_manifest,
            collector_results=collector_results,
            not_substantive=not_substantive,
            panel_mode=panel_mode,
            panel_shape=panel_shape,
            scout_status=scout_status,
            dynamic_slots=dynamic_slots,
            static_slot_count=static_slot_count,
            run_id=run_id,
            prune_ledger=prune_ledger,
        )
        return ReviewCoreResult(0, zero.status, dispatch_scout_rows + zero.rows)
    try:
        if findings_file.is_file() and findings_file.stat().st_size > 0:
            shutil.copyfile(findings_file, pre_aggregate_snapshot)
    except OSError as exc:
        _log_review_core_issue(review_tmpdir=review_tmpdir, message=f"pre-aggregate snapshot failed: {exc}")
        return _post_gate_panel_failed_exit(
            rows=rows,
            review_tmpdir=review_tmpdir,
            run_id=run_id,
            round_num=round_num,
            panel_mode=panel_mode,
            panel_shape=panel_shape,
            threshold_reason="findings-pre-aggregate-snapshot-failed",
        )

    aggregate_args = ["--findings-file", str(review_tmpdir / "findings.md"), "--review-tmpdir", str(review_tmpdir), "--codex-present", codex_available, "--cursor-present", cursor_available, "--mode", mode, "--round-num", str(round_num)]
    if session_env_path:
        aggregate_args.extend(["--session-env-path", session_env_path])
    if diff_file:
        aggregate_args.extend(["--diff-file", diff_file])
    if _get(parsed=parsed, key="--plan-file"):
        aggregate_args.extend(["--plan-file", _get(parsed=parsed, key="--plan-file")])
    _progress_note(step="5", text="aggregating reviewer findings")
    aggregate_result = _run_command_string(command=commands.aggregate, args=aggregate_args) if commands.aggregate else _call_maybe_override(command="", review_name="aggregate-findings", args=aggregate_args)
    aggregate_out = review_tmpdir / "review-core-aggregate.env"
    _write_text(path=aggregate_out, text=aggregate_result.stdout)
    aggregate = _kv_parse(aggregate_result.stdout)
    branch_ctx = ReviewCoreBranchContext(
        commands=commands,
        review_tmpdir=review_tmpdir,
        round_num=round_num,
        mode=mode,
        cursor_available=cursor_available,
        codex_available=codex_available,
        session_env_path=session_env_path,
        panel_manifest=panel_manifest,
        collector_results=collector_results,
        not_substantive=not_substantive,
        panel_mode=panel_mode,
        panel_shape=panel_shape,
        scout_status=scout_status,
        dynamic_slots=dynamic_slots,
        static_slot_count=static_slot_count,
        run_id=run_id,
        prune_ledger=prune_ledger,
        site=site,
        diff_file=diff_file,
        scope_files=scope_files,
        plan_file=_get(parsed=parsed, key="--plan-file"),
        runner=runner,
        rows=rows,
    )
    if aggregate.get("REASON") == "validation-exhausted":
        return _handle_validation_exhausted_after_gate(branch_ctx)
    if aggregate.get("REASON") == "ok" and aggregate.get("MERGED_COUNT") == "0":
        empty_merge_result = _handle_empty_merge_after_gate(branch_ctx, findings_count=findings_count, pre_aggregate_snapshot=pre_aggregate_snapshot)
        if empty_merge_result is not None:
            return empty_merge_result
    else:
        normal_gate_result = _run_normal_prune(branch_ctx)
        if normal_gate_result is not None:
            return normal_gate_result

    proposer_map = review_tmpdir / "proposer-map.tsv"
    try:
        _write_proposer_sidecar_and_neutralize(ballot_file=review_tmpdir / "findings.md", proposer_map=proposer_map)
    except (OSError, ValueError) as exc:
        logging_util.diagnostic(f"→ review: proposer map preparation failed: {exc}")
        return _post_gate_panel_failed_exit(rows=rows, review_tmpdir=review_tmpdir, run_id=run_id, round_num=round_num, panel_mode=panel_mode, panel_shape=panel_shape, threshold_reason="proposer-map-failed")

    voter_args = ["--ballot-file", str(review_tmpdir / "findings.md"), "--review-tmpdir", str(review_tmpdir), "--codex-available", codex_available, "--cursor-available", cursor_available, "--round-num", str(round_num), "--site", site]
    if session_env_path:
        voter_args.extend(["--session-env-path", session_env_path])
    if diff_file:
        voter_args.extend(["--diff-file", diff_file])
    if _get(parsed=parsed, key="--plan-file"):
        voter_args.extend(["--plan-file", _get(parsed=parsed, key="--plan-file")])
    _progress_note(step="5", text="dispatching voters")
    voters_result = _run_command_string(command=commands.dispatch_voters, args=voter_args) if commands.dispatch_voters else _run_python_cli(["agent", "dispatch-voters", *voter_args])
    voters = _kv_parse(voters_result.stdout)
    _write_text(path=review_tmpdir / "review-core-voters.env", text=voters_result.stdout)
    voter_files: list[str] = []
    voter_tools: list[str] = []
    for idx, default_tool in enumerate(("codex-validity", "codex-plan-fidelity", "codex-pragmatism"), start=1):
        path = voters.get(f"VOTER_{idx}_PATH", "")
        status = voters.get(f"VOTER_{idx}_STATUS", "")
        tool = voters.get(f"VOTER_{idx}_TOOL", default_tool) or default_tool
        voter_tools.append(tool)
        voter_files.append(path if status not in {"failed", "skipped"} and path and Path(path).is_file() and Path(path).stat().st_size else "")
        if voters.get(f"VOTER_{idx}_TOOL"):
            rows.append((f"VOTER_{idx}_TOOL", voters[f"VOTER_{idx}_TOOL"]))
        if status:
            rows.append((f"VOTER_{idx}_STATUS", status))
    tally_args = ["--ballot-file", str(review_tmpdir / "findings.md"), "--review-tmpdir", str(review_tmpdir), "--cursor-available", cursor_available, "--codex-available", codex_available, "--round-num", str(round_num), "--proposer-map-file", str(proposer_map)]
    if session_env_path:
        tally_args.extend(["--session-env-path", session_env_path])
    if scope_files and Path(scope_files).is_file() and Path(scope_files).stat().st_size:
        tally_args.extend(["--scope-files", scope_files])
    if _get(parsed=parsed, key="--plan-file") and Path(_get(parsed=parsed, key="--plan-file")).is_file():
        tally_args.extend(["--plan-file", _get(parsed=parsed, key="--plan-file")])
    if panel_manifest and Path(panel_manifest).is_file():
        tally_args.extend(["--manifest-file", panel_manifest])
    if collector_results.is_file():
        tally_args.extend(["--collector-results-file", str(collector_results)])
    if not_substantive:
        tally_args.extend(["--not-substantive-count", str(not_substantive)])
    tally_args.extend(["--voter-files", *voter_files, "--voter-tools", *voter_tools])
    _progress_note(step="5", text="tallying votes")
    tally_result = _run_command_string(command=commands.tally, args=tally_args) if commands.tally else _call_maybe_override(command="", review_name="tally-code-votes", args=tally_args)
    tally = _kv_parse(tally_result.stdout)
    _write_text(path=review_tmpdir / "review-core-tally.env", text=tally_result.stdout)
    if tally_result.returncode != 0 and not tally.get("TALLY_STATUS"):
        return _post_gate_panel_failed_exit(rows=rows, review_tmpdir=review_tmpdir, run_id=run_id, round_num=round_num, panel_mode=panel_mode, panel_shape=panel_shape, threshold_reason="tally-code-votes failed")
    for key in (
        "VOTING_SKIPPED_WARNING",
        "YIELD_TSV_FILE",
        "VOTING_TALLY_FILE",
        "UNDER_QUORUM_COUNT",
        "UNDER_QUORUM_ITEMS",
        "PARSE_FAILED_COUNT",
        "VOTER_COUNT",
    ):
        if tally.get(key):
            rows.append((key, tally[key]))
    classification = tally.get("FINDINGS_CLASSIFICATION_TSV_FILE", "")
    rows.extend(_record_classification(review_tmpdir=review_tmpdir, round_num=round_num, classification_file=classification))
    if tally.get("TALLY_STATUS") == "main-agent-vote-required":
        _write_text(path=review_tmpdir / "rejected-findings.md", text="")
        emit_args = ["--tally-file", tally.get("TALLY_FILE", str(review_tmpdir / "review-tally.env")), "--accepted-findings-file", tally.get("ACCEPTED_FINDINGS_FILE", str(review_tmpdir / "accepted-findings.md")), "--oos-file", str(review_tmpdir / "oos.md"), "--review-tmpdir", str(review_tmpdir), "--round", str(round_num), "--mode", mode, "--scout-status", scout_status, "--dynamic-slots", dynamic_slots, "--static-slot-count", static_slot_count]
        _progress_note(step="5", text="post-fix checks running")
        _emit_tally_with_context(commands=commands, args=emit_args, out_file=review_tmpdir / "review-core-main-agent-emit.env", session_env_path=session_env_path)
        _flush_round_log(review_tmpdir=review_tmpdir, run_id=run_id, round_num=round_num)
        rows.extend(_core_common_rows(status="main-agent-vote-required", round_num=round_num, review_tmpdir=review_tmpdir, panel_mode=panel_mode, panel_shape=panel_shape, oos_drift=tally.get("OUT_OF_SCOPE_DRIFT_COUNT", "0")))
        if classification:
            rows.append(("FINDINGS_CLASSIFICATION_TSV_FILE", classification))
        return ReviewCoreResult(0, ReviewCoreStatus.main_agent_vote_required, tuple(rows))
    rows.extend(_record_prune_round(prune_ledger=prune_ledger, round_num=round_num, panel_manifest=panel_manifest, classification_file=classification))
    accepted = tally.get("ACCEPTED_COUNT", "0") or "0"
    rejected = tally.get("REJECTED_COUNT", "0") or "0"
    exonerated = tally.get("EXONERATED_COUNT", "0") or "0"
    neutral = tally.get("NEUTRAL_COUNT", "0") or "0"
    accepted_file = Path(tally.get("ACCEPTED_FINDINGS_FILE", str(review_tmpdir / "accepted-findings.md")))
    tally_file = tally.get("TALLY_FILE", str(review_tmpdir / "review-tally.env"))
    emit_args = ["--tally-file", tally_file, "--accepted-findings-file", str(accepted_file), "--oos-file", str(review_tmpdir / "oos.md"), "--review-tmpdir", str(review_tmpdir), "--round", str(round_num), "--mode", mode, "--scout-status", scout_status, "--dynamic-slots", dynamic_slots, "--static-slot-count", static_slot_count]
    _progress_note(step="5", text="post-fix checks running")
    _emit_tally_with_context(commands=commands, args=emit_args, out_file=review_tmpdir / "review-core-emit.env", session_env_path=session_env_path)
    _copy_to_parent(file=review_tmpdir / "rejected-findings.md", name="rejected-findings.md", session_env_path=session_env_path)
    _copy_to_parent(file=review_tmpdir / "oos-accepted-review.md", name="oos-accepted-review.md", session_env_path=session_env_path)
    _flush_round_log(review_tmpdir=review_tmpdir, run_id=run_id, round_num=round_num)
    status = "ok"
    effective_round_cap = difficulty.tier_ceiling(panel_tier)
    if mode == "diff" and accepted.isdigit() and int(accepted) > 0:
        status = "cap-reached" if round_num >= effective_round_cap else "fix-required"
    rows.extend(_core_common_rows(status=status, round_num=round_num, review_tmpdir=review_tmpdir, panel_mode=panel_mode, panel_shape=panel_shape, accepted=accepted, rejected=rejected, exonerated=exonerated, neutral=neutral, oos_drift=tally.get("OUT_OF_SCOPE_DRIFT_COUNT", "0"), accepted_file=accepted_file))
    rows.append(("PANEL_TIER", panel_tier))
    rows.append(("EFFECTIVE_ROUND_CAP", effective_round_cap))
    if classification:
        rows.append(("FINDINGS_CLASSIFICATION_TSV_FILE", classification))
    return ReviewCoreResult(0, ReviewCoreStatus.from_wire(status), tuple(rows))


def review_core(argv: list[str], *, runner: object = None) -> int:
    logging_util.quiet_init(argv0="review-core")
    usage = "Usage: review core --mode diff|description --output-dir DIR --codex-available true|false --cursor-available true|false [--dynamic-archetypes 0-1] [--pre-scouted-manifest FILE] [--site SITE] [context flags]"
    options = {
        "--mode",
        "--output-dir",
        "--session-env-path",
        "--codex-available",
        "--cursor-available",
        "--diff-file",
        "--commit-count",
        "--scope-files",
        "--plan-file",
        "--feature-file",
        "--description-text",
        "--panel",
        "--tier",
        "--escalated-round",
        "--dynamic-archetypes",
        "--pre-scouted-manifest",
        "--run-id",
        "--round-num",
        "--prune-ledger",
        "--site",
    }
    parsed = _parse_args(argv=argv, usage=usage, options=options)
    if parsed is None:
        return 0
    if not parsed:
        return 2
    mode = _get(parsed=parsed, key="--mode")
    review_tmpdir = Path(_get(parsed=parsed, key="--output-dir"))
    codex_available = _get(parsed=parsed, key="--codex-available")
    cursor_available = _get(parsed=parsed, key="--cursor-available")
    panel = _get(parsed=parsed, key="--panel", default="hard")
    raw_tier = _get(parsed=parsed, key="--tier")
    tier = difficulty.normalize_tier(raw_tier) or (difficulty.TRIVIAL if panel == "simple" else difficulty.MODERATE)
    if raw_tier and not difficulty.normalize_tier(raw_tier):
        logging_util.diagnostic(usage)
        return 2
    if raw_tier:
        panel = difficulty.threshold_panel_for_tier(tier)
    escalated_round = _get(parsed=parsed, key="--escalated-round", default="false")
    dynamic = _get(parsed=parsed, key="--dynamic-archetypes", default=os.environ.get("LARCH_DYNAMIC_ARCHETYPES_MAX") or "0")
    round_raw = _get(parsed=parsed, key="--round-num", default="1")
    if mode not in {"diff", "description"} or not str(review_tmpdir) or codex_available not in {"true", "false"} or cursor_available not in {"true", "false"} or panel not in {"simple", "hard"} or dynamic not in {"0", "1"} or escalated_round not in {"true", "false"} or not round_raw.isdigit() or int(round_raw) <= 0:
        logging_util.diagnostic(usage)
        return 2
    round_num = int(round_raw)
    session_env_path = _get(parsed=parsed, key="--session-env-path", default=os.environ.get("SESSION_ENV_PATH", ""))
    run_id = _get(parsed=parsed, key="--run-id")
    prune_ledger = _get(parsed=parsed, key="--prune-ledger")
    site = _get(parsed=parsed, key="--site", default="review Step 2")
    result = _review_core_body(
        parsed,
        mode=mode,
        review_tmpdir=review_tmpdir,
        codex_available=codex_available,
        cursor_available=cursor_available,
        panel=panel,
        tier=tier,
        escalated_round=escalated_round,
        dynamic=dynamic,
        round_num=round_num,
        session_env_path=session_env_path,
        run_id=run_id,
        prune_ledger=prune_ledger,
        site=site,
        runner=runner,
        commands=_review_commands(),
    )
    return _emit_review_core_result(result)


def review_core_main(argv: list[str]) -> int:
    return review_core(argv)
# pyright: reportAttributeAccessIssue=false
