"""Round execution for the review-and-fix subsystem.

Contains review_core_capture, _run_round, and all supporting helpers
for executing a single review-and-fix round.
"""
# ruff: noqa: PLR2004
# pyright: reportUnusedCallResult=false, reportArgumentType=false

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Mapping

from larch.core import config
from larch.calibration import difficulty
from larch.report import progress_report
from larch.review import review_core_body
from larch.review import review_pipeline
from larch.review import review_tally
from larch.review import voting
from larch.review._raf_util import (
    _PY_CLI,
    _capture_emit_to,
    _core_round_state,
    _count_findings,
    _emit_kv,
    _err,
    _git_head,
    _parse_env_file,
    _prior_summary_counts,
    _read_text,
    _run,
    _session_get,
    _temporary_env,
    _write_env,
    _write_text,
)
from larch.review.batch_report import (
    _FINDING_RE,
    _OOS_HEADING_RE,
    _append_round_oos_artifact,
    _compose_review_findings_output,
    _core_status_is,
    _derive_code_review_tally,
    _process_skipped_findings,
    _reviewer_prune_status_records,
    _clear_reviewer_prune_round,
    flush_round_log_after_coder,
    flush_scout_manifest,
    write_rejected_findings_aggregate,
)
from larch.review.coder_runner import CoderResult, apply_findings_with_coder
from larch.review.snapshot import _write_pre_coder_snapshot
from larch.review.review_types import ReviewCoreStatus, parse_findings

ReviewCoreImpl = Callable[[list[str]], int]


@dataclass(frozen=True)
class RoundResult:
    rc: int
    status: str
    core_status: str
    round_num: int
    accepted_count: int
    rejected_count: int
    exonerated_count: int
    neutral_count: int
    total_accepted_count: int
    total_rejected_count: int
    total_exonerated_count: int
    total_neutral_count: int
    accepted_file: Path
    rejected_file: Path
    round_dir: Path
    summary_file: Path
    accumulated_oos_file: Path
    coder: CoderResult
    degraded_round: bool = False
    skipped_finding_count: int = 0


@dataclass(frozen=True)
class _VoterSlots:
    voter_files: list[str]
    voter_tools: list[str]
    readable_paths: list[Path]


def review_core_capture(*,
    core_args: list[str],
    env_path: str | Path,
    review_core_impl: ReviewCoreImpl | None = None,
    implement_tmpdir: str | Path | None = None,
) -> int:
    """Run review core in-process and write its contract stream to ``env_path``."""
    output = Path(env_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    override = os.environ.get("REVIEW_AND_FIX_REVIEW_CORE_SH", "")
    if review_core_impl is None and override and os.environ.get("LARCH_TEST_REVIEW_CORE_OVERRIDE") != "1":
        _err(
            f"review-and-fix: ignoring REVIEW_AND_FIX_REVIEW_CORE_SH={override} "
            "(set LARCH_TEST_REVIEW_CORE_OVERRIDE=1 for harness stubs)"
        )
        override = ""
    if review_core_impl is None and override:
        override_path = Path(override)
        if not override_path.is_file() or not os.access(override_path, os.X_OK):
            _err(f"review-and-fix: REVIEW_AND_FIX_REVIEW_CORE_SH is not executable: {override}")
            _write_text(path=output, text="REVIEW_CORE_STATUS=error\nREVIEW_CORE_ERROR=override-not-executable\n")
            return 2
        env = os.environ.copy()
        if implement_tmpdir is not None:
            env["IMPLEMENT_TMPDIR"] = str(implement_tmpdir)
        result = _run([override, *core_args], env=env)
        _write_text(path=output, text=result.stdout)
        if result.stderr:
            _err(result.stderr.rstrip())
        return result.returncode
    impl = review_core_impl or review_pipeline.review_core
    buffer = io.StringIO()
    with _temporary_env(name=config.ENV_IMPLEMENT_TMPDIR, value=str(implement_tmpdir) if implement_tmpdir is not None else os.environ.get(config.ENV_IMPLEMENT_TMPDIR)):
        try:
            with _capture_emit_to(buffer):
                rc = int(impl(list(core_args)))
        except BaseException as exc:  # preserve cleanup, convert to contract failure
            buffer.write(f"REVIEW_CORE_STATUS=exception\nREVIEW_CORE_ERROR={type(exc).__name__}\n")
            rc = 1
    _write_text(path=output, text=buffer.getvalue())
    return rc


def _filter_in_scope(*, accepted_file: Path, output: Path) -> None:
    text = _read_text(accepted_file)
    first = re.search(r"^### FINDING_[0-9]+:", text, flags=re.MULTILINE)
    preamble = text[: first.start()] if first else text
    kept = [finding.block.rstrip() for finding in parse_findings(accepted_file, boundary="finding_heading") if not _OOS_HEADING_RE.match(finding.block.splitlines()[0] if finding.block else "")]
    findings_text = "\n\n".join(kept) + ("\n" if kept else "")
    _write_text(path=output, text=preamble + findings_text)


def _high_severity_count(path: Path) -> int:
    _HIGH_RE = re.compile(
        r"(^### FINDING_[0-9]+:[^\n]*(\*\*Major\*\*|\*\*Blocking\*\*|\*\*Important\*\*|\*\*Critical\*\*|\*\*High\*\*)"
        r"|\*\*[Mm]ajor\*\*"
        r"|\*\*[Bb]locking\*\*"
        r"|\*\*[Ii]mportant\*\*"
        r"|^- \*\*Severity\*\*:\s*major(?:[\s,:;.\)]|$)"
        r"|^- \*\*Concern\*\*:\s*\[[Mm]ajor\](?:[\s,:;.\)]|$)"
        r"|^- \*\*Concern\*\*:\s*\[[Bb]locking\](?:[\s,:;.\)]|$)"
        r"|^- \*\*Concern\*\*:\s*\[[Ii]mportant\](?:[\s,:;.\)]|$))"
    )
    if not path.is_file():
        return 0
    return sum(1 for line in _read_text(path).splitlines() if _HIGH_RE.search(line))


def _nit_count(path: Path) -> int:
    count = 0
    in_block = False
    nit = False
    for line in _read_text(path).splitlines() if path.is_file() else []:
        if _FINDING_RE.match(line):
            if in_block and nit:
                count += 1
            in_block = True
            nit = False
        elif in_block and line.startswith("### "):
            if nit:
                count += 1
            in_block = False
            nit = False
        elif in_block and line.startswith("- **Severity**: nit"):
            nit = True
    if in_block and nit:
        count += 1
    return count


def _important_present(path: Path) -> bool:
    _HIGH_RE = re.compile(
        r"(^### FINDING_[0-9]+:[^\n]*(\*\*Major\*\*|\*\*Blocking\*\*|\*\*Important\*\*|\*\*Critical\*\*|\*\*High\*\*)"
        r"|\*\*[Mm]ajor\*\*"
        r"|\*\*[Bb]locking\*\*"
        r"|\*\*[Ii]mportant\*\*"
        r"|^- \*\*Severity\*\*:\s*major(?:[\s,:;.\)]|$)"
        r"|^- \*\*Concern\*\*:\s*\[[Mm]ajor\](?:[\s,:;.\)]|$)"
        r"|^- \*\*Concern\*\*:\s*\[[Bb]locking\](?:[\s,:;.\)]|$)"
        r"|^- \*\*Concern\*\*:\s*\[[Ii]mportant\](?:[\s,:;.\)]|$))"
    )
    return any(_HIGH_RE.search(line) for line in _read_text(path).splitlines()) if path.is_file() else False


def _write_summary(*, path: Path, result: RoundResult, round_cap: int) -> None:
    data = {
        "schema_version": 3,
        "status": result.status,
        "review_core_status": result.core_status,
        "round_num": result.round_num,
        "rounds_completed": result.round_num,
        "round_cap": round_cap,
        "panel_tier": getattr(result, "panel_tier", ""),
        "accepted_count": result.total_accepted_count,
        "rejected_count": result.total_rejected_count,
        "exonerated_count": result.total_exonerated_count,
        "neutral_count": result.total_neutral_count,
        "approved_fixes_file": str(result.accepted_file),
        "review_round_dir": str(result.round_dir),
        "accumulated_oos_file": str(result.accumulated_oos_file),
        "accumulated_oos_markdown_file": str(result.round_dir.parent / "accumulated-oos.md"),
        "coder_tool": result.coder.tool,
        "coder_status": result.coder.status,
        "submodule_scrub_count": result.coder.scrub_count,
        "submodule_revert_count": result.coder.revert_count,
        "coder_commit_sha": result.coder.commit_sha,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    _write_text(path=tmp, text=json.dumps(data, sort_keys=True, indent=2) + "\n")
    tmp.replace(path)


def _timing_row_matches(
    parts: list[str],
    *,
    round_num: int,
    start_s: int,
    end_s: int,
    step_label: str,
) -> bool:
    if len(parts) < 8:
        return False
    return (
        parts[1] == "round"
        and parts[3] == "implement"
        and parts[4] == step_label
        and parts[5] == str(round_num)
        and parts[6] == str(start_s)
        and parts[7] == str(end_s)
    )


def _core_args_for_round(*, args: argparse.Namespace, round_dir: Path, dynamic_archetypes: str, prune_ledger: Path) -> list[str]:
    panel_tier = difficulty.normalize_tier(getattr(args, "panel_tier", ""), difficulty.MODERATE)
    core_args = [
        "--mode", "diff",
        "--output-dir", str(round_dir),
        "--session-env-path", str(args.session_env_path),
        "--codex-available", args.codex_available,
        "--cursor-available", args.cursor_available,
        "--panel", difficulty.threshold_panel_for_tier(panel_tier),
        "--tier", panel_tier,
        "--escalated-round", str(getattr(args, "escalated_round", "false") or "false").lower(),
        "--round-num", str(args.round_num),
        "--dynamic-archetypes", dynamic_archetypes,
        "--prune-ledger", str(prune_ledger),
        "--site", "implement Step 5",
    ]
    for opt, attr in (
        ("--diff-file", "diff_file"),
        ("--commit-count", "commit_count"),
        ("--plan-file", "plan_file"),
        ("--feature-file", "feature_file"),
        ("--run-id", "run_id"),
        ("--pre-scouted-manifest", "pre_scouted_manifest"),
    ):
        value = getattr(args, attr, "")
        if value:
            core_args.extend([opt, str(value)])
    return core_args


def _dynamic_archetypes(*, args: argparse.Namespace, implement_tmpdir: Path) -> str:
    value = getattr(args, "dynamic_archetypes", "") or os.environ.get("LARCH_DYNAMIC_ARCHETYPES_MAX", "")
    if not value and args.session_env_path:
        value = _session_get(session_env_path=Path(args.session_env_path), key="LARCH_DYNAMIC_ARCHETYPES_MAX", default="")
    if not value:
        value = "1" if implement_tmpdir.is_dir() else "0"
    if value not in {"0", "1"}:
        raise ValueError("--dynamic-archetypes/LARCH_DYNAMIC_ARCHETYPES_MAX must be an integer from 0 to 1")
    return value


def _surface_parse_failed_warning(*, core: dict[str, str], round_num: int, session_env_path: str) -> None:
    """Issue #5345: surface the parse-failed warning after degraded-retry settles.

    Called only when the panel remains degraded after the retry attempt, so a successful retry
    never leaves a stale warning in the run summary.
    """
    pf_count_raw = core.get("PARSE_FAILED_COUNT", "0")
    pf_count = int(pf_count_raw) if pf_count_raw.isdigit() else 0
    if pf_count == 0:
        return
    review_tally.surface_warning(
        session_env_path=session_env_path,
        entry=(
            f"- **code-review panel (round {round_num})**: {pf_count} voter slot(s) emitted "
            "narrative-only output (per-voter JUDGE_ERROR above the parse-rate threshold) and were "
            "removed from the effective quorum."
        ),
    )


def _surface_under_quorum_warning(*, core: dict[str, str], round_num: int, session_env_path: str) -> None:
    """Issue #5334: surface the under-quorum warning once, from the final panel state."""
    uq_count_raw = core.get("UNDER_QUORUM_COUNT", "0")
    uq_count = int(uq_count_raw) if uq_count_raw.isdigit() else 0
    if uq_count == 0:
        return
    uq_items = core.get("UNDER_QUORUM_ITEMS", "")
    voter_count_raw = core.get("VOTER_COUNT", "0")
    voter_count = int(voter_count_raw) if voter_count_raw.isdigit() else 0
    quorum = voter_count // 2 + 1 if voter_count > 0 else 0
    review_tally.surface_warning(
        session_env_path=session_env_path,
        entry=(
            f"- **code-review panel (round {round_num})**: {uq_count} finding(s) "
            f"decided below the {quorum}-of-{voter_count} panel quorum due to per-item JUDGE_ERROR "
            f"({uq_items}); resolved by the remaining voter(s)."
        ),
    )


def _env_int(*, mapping: dict[str, str], key: str) -> int:
    value = mapping.get(key, "0") or "0"
    return int(value) if value.isdigit() else 0


def _dynamic_evidence_in_dropped_file(path: Path | None) -> bool:
    if path is None or not path.is_file():
        return False
    for line in _read_text(path).splitlines():
        slot, _tool, _reason, *_rest = [*line.split("\t"), "", "", ""]
        if slot.startswith("dyn-"):
            return True
    return False


def _dynamic_evidence_in_manifest(path: Path | None, *, dropped_slots_file: Path | None = None) -> bool:
    if path is None or not path.is_file():
        return False
    if dropped_slots_file is None or not dropped_slots_file.is_file():
        return False
    dropped_slots: set[str] = set()
    for line in _read_text(dropped_slots_file).splitlines():
        slot, _tool, _reason, *_rest = [*line.split("\t"), "", "", ""]
        if slot:
            dropped_slots.add(slot)
    if not dropped_slots:
        return False
    for line in _read_text(path).splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        slot = row.get("slot")
        if isinstance(slot, str) and slot.startswith("dyn-") and slot in dropped_slots:
            return True
    return False


def _merge_warn_tokens(*values: str) -> str:
    tokens: list[str] = []
    seen: set[str] = set()
    for value in values:
        for raw_token in value.split(";"):
            token = raw_token.strip()
            if token and token not in seen:
                seen.add(token)
                tokens.append(token)
    return ";".join(tokens)


def _core_zero_survivor_panel_failed(core: Mapping[str, str]) -> bool:
    return (
        core.get("REVIEW_CORE_STATUS") == "panel-failed"
        and core.get("THRESHOLD_REASON") == "no successful launched reviewer output"
    )


def _merge_dropped_reviewer_attempt(*, round_dir: Path, threshold_env: Path) -> None:
    if not threshold_env.is_file():
        return
    current = _parse_env_file(round_dir / "dropped-reviewer-attempts.env")
    attempt = _parse_env_file(threshold_env)
    merged: dict[str, str | int] = {
        "DYNAMIC_FAILED_SLOTS": max(_env_int(mapping=current, key="DYNAMIC_FAILED_SLOTS"), _env_int(mapping=attempt, key="DYNAMIC_FAILED_SLOTS")),
        "DYNAMIC_DROPPED_SLOTS": max(_env_int(mapping=current, key="DYNAMIC_DROPPED_SLOTS"), _env_int(mapping=attempt, key="DYNAMIC_DROPPED_SLOTS")),
        "STRAGGLER_DROPPED_COUNT": max(_env_int(mapping=current, key="STRAGGLER_DROPPED_COUNT"), _env_int(mapping=attempt, key="STRAGGLER_DROPPED_COUNT")),
    }
    warn = _merge_warn_tokens(current.get("WATERFALL_WARN", ""), attempt.get("WATERFALL_WARN", ""))
    if warn:
        merged["WATERFALL_WARN"] = warn
    _write_env(path=round_dir / "dropped-reviewer-attempts.env", values=merged)


def _resolve_dropped_slots_file(*, round_dir: Path, core: dict[str, str]) -> Path | None:
    dropped_candidates = sorted(round_dir.glob("*.dropped-slots"))
    dropped_candidates.sort(key=lambda path: (not path.name.endswith(".output-files.dropped-slots"), path.name))
    if dropped_candidates:
        return dropped_candidates[0]
    for source in (core, _parse_env_file(round_dir / "review-core-dispatch.env")):
        dispatch_dropped = source.get("DROPPED_SLOTS_FILE", "")
        if dispatch_dropped:
            candidate = Path(dispatch_dropped)
            if candidate.is_file():
                return candidate
    return None


def _strict_env_int(mapping: Mapping[str, str], key: str) -> int | None:
    value = mapping.get(key)
    return int(value) if value is not None and value.isdigit() else None


def _pure_under_quorum_degradation(core: dict[str, str], threshold_env: Path, round_dir: Path) -> bool:
    required_threshold_keys = (
        "FAILED_SLOTS",
        "NOT_SUBSTANTIVE_SLOTS",
        "DYNAMIC_FAILED_SLOTS",
        "DYNAMIC_DROPPED_SLOTS",
    )
    required_core_keys = ("UNDER_QUORUM_COUNT", "PARSE_FAILED_COUNT", "VOTER_COUNT")
    threshold = _parse_env_file(threshold_env) if threshold_env.is_file() and os.access(threshold_env, os.R_OK) else {}
    threshold_values = {key: _strict_env_int(threshold, key) for key in required_threshold_keys}
    core_values = {key: _strict_env_int(core, key) for key in required_core_keys}
    pure = bool(threshold) and all(value is not None for value in threshold_values.values()) and all(value is not None for value in core_values.values())
    if pure:
        pure = (
            int(core_values["UNDER_QUORUM_COUNT"] or 0) > 0
            and int(core_values["PARSE_FAILED_COUNT"] or 0) == 0
            and all(int(value or 0) == 0 for value in threshold_values.values())
        )
    tally = _parse_env_file(round_dir / "review-core-tally.env")
    eligible = _strict_env_int(tally, "ELIGIBLE_VOTER_COUNT")
    voters = _strict_env_int(tally, "VOTER_COUNT")
    if pure and eligible is not None and voters is not None and eligible < voters:
        pure = False
    attempts = _parse_env_file(round_dir / "dropped-reviewer-attempts.env")
    straggler = _strict_env_int(attempts, "STRAGGLER_DROPPED_COUNT")
    if pure and straggler is not None and straggler != 0:
        pure = False
    dropped_file = _resolve_dropped_slots_file(round_dir=round_dir, core=core)
    if pure and (
        _dynamic_evidence_in_dropped_file(dropped_file)
        or _dynamic_evidence_in_manifest(round_dir / "panel-manifest.ndjson", dropped_slots_file=dropped_file)
    ):
        pure = False
    tally_text = _read_text(round_dir / "voting-tally.md") if (round_dir / "voting-tally.md").is_file() else ""
    mixed_banner_markers = (
        "judge(s) available",
        "judges available",
        "narrative-only output",
        "NOT_SUBSTANTIVE",
    )
    if pure and any(marker in tally_text for marker in mixed_banner_markers):
        pure = False
    return pure


def _under_quorum_item_ids(core: dict[str, str]) -> list[str]:
    return [item.strip() for item in core.get("UNDER_QUORUM_ITEMS", "").split(",") if item.strip()]


def _extract_ballot_blocks(source: Path, item_ids: set[str]) -> tuple[str, bool]:
    if not source.is_file() or not item_ids:
        return "", False
    requested = {item.upper() for item in item_ids}
    found: set[str] = set()
    blocks: list[str] = []
    current_id = ""
    current_lines: list[str] = []
    for raw in _read_text(source).splitlines(keepends=True):
        match = voting.BALLOT_HEADING_RE.match(raw.rstrip("\n"))
        if match:
            if current_id.upper() in requested:
                blocks.append("".join(current_lines))
                found.add(current_id.upper())
            current_id = match.group(1)
            current_lines = [raw]
        elif current_id:
            current_lines.append(raw)
    if current_id.upper() in requested:
        blocks.append("".join(current_lines))
        found.add(current_id.upper())
    restricted = "\n".join(block.rstrip("\n") for block in blocks).rstrip() + ("\n" if blocks else "")
    return restricted, found == requested


def _write_under_quorum_ballot(source: Path, output: Path, item_ids: set[str]) -> bool:
    restricted, all_present = _extract_ballot_blocks(source, item_ids)
    ok = all_present and bool(restricted.strip())
    if ok:
        output.parent.mkdir(parents=True, exist_ok=True)
        _write_text(path=output, text=restricted)
    return ok


def _review_voter_slots(round_dir: Path) -> _VoterSlots | None:
    voters = _parse_env_file(round_dir / "review-core-voters.env")
    voter_files: list[str] = []
    voter_tools: list[str] = []
    readable_paths: list[Path] = []
    for idx, default_tool in enumerate(("codex-validity", "codex-plan-fidelity", "codex-pragmatism"), start=1):
        path = voters.get(f"VOTER_{idx}_PATH", "")
        tool = voters.get(f"VOTER_{idx}_TOOL", default_tool) or default_tool
        candidate = Path(path) if path else Path()
        if not path or not candidate.is_file() or not os.access(candidate, os.R_OK):
            return None
        voter_files.append(path)
        voter_tools.append(tool)
        readable_paths.append(candidate)
    return _VoterSlots(voter_files=voter_files, voter_tools=voter_tools, readable_paths=readable_paths)


def _snapshot_original_voters(round_dir: Path, revote_dir: Path, slots: _VoterSlots) -> list[Path]:
    del round_dir
    revote_dir.mkdir(parents=True, exist_ok=True)
    snapshots: list[Path] = []
    for idx, original in enumerate(slots.readable_paths, start=1):
        snapshot = revote_dir / f"original-voter-{idx}.txt"
        shutil.copyfile(original, snapshot)
        snapshots.append(snapshot)
    return snapshots


def _targeted_vote_lines(*, revote_file: str, under_quorum_ids: set[str]) -> list[str]:
    path = Path(revote_file) if revote_file else Path()
    if not path.is_file():
        return []
    normalized = voting._normalize_markdown_table_votes(_read_text(path))  # noqa: SLF001 - targeted retry must mirror voter parser normalization.
    id_pattern = "|".join(re.escape(item) for item in sorted(under_quorum_ids))
    vote_re = re.compile(rf"^(?:{id_pattern}):\s*(?:YES|NO|EXONERATE)\b", re.IGNORECASE)
    return [line for line in normalized.splitlines() if vote_re.match(line)]


def _merge_targeted_voter_outputs(
    *,
    originals: list[Path],
    revote_files: list[str],
    under_quorum_ids: set[str],
    output_paths: list[str],
) -> list[str]:
    merged_files: list[str] = []
    for idx, original in enumerate(originals):
        output = Path(output_paths[idx])
        original_text = _read_text(original)
        lines = _targeted_vote_lines(
            revote_file=revote_files[idx] if idx < len(revote_files) else "",
            under_quorum_ids=under_quorum_ids,
        )
        merged_text = original_text.rstrip() + ("\n" if original_text.rstrip() else "")
        if lines:
            merged_text += "\n".join(lines) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        _write_text(path=output, text=merged_text)
        merged_files.append(str(output))
    return merged_files


def _build_targeted_dispatch_args(
    round_dir: Path,
    args: argparse.Namespace,
    restricted_ballot: Path,
    revote_dir: Path,
) -> list[str] | None:
    if not restricted_ballot.is_file():
        return None
    dispatch_args = [
        "--ballot-file",
        str(restricted_ballot),
        "--review-tmpdir",
        str(revote_dir),
        "--codex-available",
        str(args.codex_available),
        "--cursor-available",
        str(args.cursor_available),
        "--round-num",
        str(args.round_num),
        "--site",
        "implement Step 5",
    ]
    for flag, value in (
        ("--session-env-path", getattr(args, "session_env_path", "")),
        ("--diff-file", getattr(args, "diff_file", "")),
        ("--plan-file", getattr(args, "plan_file", "")),
    ):
        if value and (flag != "--plan-file" or Path(value).is_file()):
            dispatch_args.extend([flag, str(value)])
    del round_dir
    return dispatch_args


def _build_targeted_tally_args(
    round_dir: Path,
    core: dict[str, str],
    args: argparse.Namespace,
    merged_voter_files: list[str],
    voter_tools: list[str],
) -> list[str] | None:
    findings = round_dir / "findings.md"
    proposer_map = round_dir / "proposer-map.tsv"
    if not findings.is_file() or not proposer_map.is_file() or not merged_voter_files or len(merged_voter_files) != len(voter_tools):
        return None
    tally_args = [
        "--ballot-file",
        str(findings),
        "--review-tmpdir",
        str(round_dir),
        "--cursor-available",
        str(args.cursor_available),
        "--codex-available",
        str(args.codex_available),
        "--round-num",
        str(args.round_num),
        "--proposer-map-file",
        str(proposer_map),
    ]
    session_env_path = getattr(args, "session_env_path", "")
    if session_env_path:
        tally_args.extend(["--session-env-path", str(session_env_path)])
    gather = _parse_env_file(round_dir / "review-core-gather.env")
    scope_files = gather.get("FILE_LIST_FILE", "")
    if scope_files and Path(scope_files).is_file() and Path(scope_files).stat().st_size:
        tally_args.extend(["--scope-files", scope_files])
    plan_file = getattr(args, "plan_file", "")
    if plan_file and Path(plan_file).is_file():
        tally_args.extend(["--plan-file", str(plan_file)])
    panel_manifest = round_dir / "panel-manifest.ndjson"
    if panel_manifest.is_file():
        tally_args.extend(["--manifest-file", str(panel_manifest)])
    collector_results = round_dir / "collector-results.env"
    if collector_results.is_file():
        tally_args.extend(["--collector-results-file", str(collector_results)])
    threshold = _parse_env_file(round_dir / "review-core-threshold.env")
    not_substantive = _strict_env_int(threshold, "NOT_SUBSTANTIVE_SLOTS")
    if not_substantive is not None and not_substantive > 0:
        tally_args.extend(["--not-substantive-count", str(not_substantive)])
    if core.get("PANEL_MANIFEST") and "--manifest-file" not in tally_args and Path(core["PANEL_MANIFEST"]).is_file():
        tally_args.extend(["--manifest-file", core["PANEL_MANIFEST"]])
    tally_args.extend(["--voter-files", *merged_voter_files, "--voter-tools", *voter_tools])
    return tally_args


def _build_targeted_emit_args(round_dir: Path, core: dict[str, str], tally_env_path: Path, args: argparse.Namespace) -> list[str] | None:
    tally = _parse_env_file(tally_env_path)
    accepted_file = Path(tally.get("ACCEPTED_FINDINGS_FILE", str(round_dir / "accepted-findings.md")))
    if not tally_env_path.is_file() or not accepted_file.is_file():
        return None
    gather = _parse_env_file(round_dir / "review-core-gather.env")
    dispatch = _parse_env_file(round_dir / "review-core-dispatch.env")
    emit = _parse_env_file(round_dir / "review-core-emit.env")
    mode = core.get("MODE") or gather.get("MODE") or "diff"
    scout_status = core.get("SCOUT_STATUS") or dispatch.get("SCOUT_STATUS") or emit.get("SCOUT_STATUS") or "na"
    dynamic_slots = core.get("DYNAMIC_SLOTS") or dispatch.get("DYNAMIC_SLOTS") or emit.get("DYNAMIC_SLOTS") or "0"
    static_slot_count = core.get("STATIC_SLOT_COUNT") or dispatch.get("STATIC_SLOT_COUNT") or emit.get("STATIC_SLOT_COUNT") or "0"
    del args
    return [
        "--tally-file",
        str(tally.get("TALLY_FILE", str(tally_env_path))),
        "--accepted-findings-file",
        str(accepted_file),
        "--oos-file",
        str(round_dir / "oos.md"),
        "--review-tmpdir",
        str(round_dir),
        "--round",
        str(core.get("ROUND_NUM", "1")),
        "--mode",
        mode,
        "--scout-status",
        scout_status,
        "--dynamic-slots",
        dynamic_slots,
        "--static-slot-count",
        static_slot_count,
    ]


def _targeted_final_status(*, round_dir: Path, core: dict[str, str], tally: dict[str, str], args: argparse.Namespace) -> str:
    mode = core.get("MODE") or _parse_env_file(round_dir / "review-core-gather.env").get("MODE") or "diff"
    accepted = tally.get("ACCEPTED_COUNT", "0") or "0"
    status = "ok"
    if mode == "diff" and accepted.isdigit() and int(accepted) > 0:
        cap_raw = core.get("EFFECTIVE_ROUND_CAP") or str(getattr(args, "round_cap", "") or "")
        cap = int(cap_raw) if cap_raw.isdigit() else difficulty.tier_ceiling(difficulty.normalize_tier(getattr(args, "panel_tier", ""), difficulty.MODERATE))
        round_num = int(str(getattr(args, "round_num", "1") or "1"))
        status = "cap-reached" if round_num >= cap else "fix-required"
    return status


def _apply_targeted_retally_outputs(
    round_dir: Path,
    core_out: Path,
    core: dict[str, str],
    tally: dict[str, str],
    emit: dict[str, str],
    args: argparse.Namespace,
    *,
    prune_ledger: Path,
    round_num: int,
    panel_manifest: Path,
) -> dict[str, str]:
    updated = {**core, **tally, **emit}
    status = _targeted_final_status(round_dir=round_dir, core=updated, tally=tally, args=args)
    updated["REVIEW_CORE_STATUS"] = status
    updated["ROUND_NUM"] = str(round_num)
    updated["ACCEPTED_FINDINGS_FILE"] = tally.get("ACCEPTED_FINDINGS_FILE", str(round_dir / "accepted-findings.md"))
    updated["REJECTED_FINDINGS_FILE"] = str(round_dir / "rejected-findings.md")
    updated["FINDINGS_FILE"] = str(round_dir / "findings.md")
    classification = updated.get("FINDINGS_CLASSIFICATION_TSV_FILE", "")
    rows = review_core_body._record_classification(  # noqa: SLF001 - targeted retally must update the same classification sidecar.
        review_tmpdir=round_dir,
        round_num=round_num,
        classification_file=classification,
    )
    for key, value in rows:
        updated[str(key)] = str(value)
    if _reviewer_prune_status_records(status):
        review_core_body._record_prune_round(  # noqa: SLF001 - targeted retally must refresh the same prune ledger.
            prune_ledger=str(prune_ledger),
            round_num=round_num,
            panel_manifest=str(panel_manifest),
            classification_file=classification,
        )
    else:
        _clear_reviewer_prune_round(ledger=prune_ledger, round_num=round_num, work_dir=round_dir)
    _write_env(path=core_out, values=updated)
    return updated


def _targeted_artifact_names() -> tuple[str, ...]:
    return (
        "voting-tally.md",
        "accepted-findings.md",
        "rejected-findings.md",
        "rejected-findings-full.md",
        "oos.md",
        "oos-accepted-review.md",
        "review-round-summary.md",
        "review-summary.json",
    )


def _backup_targeted_artifacts(round_dir: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    for name in _targeted_artifact_names():
        source = round_dir / name
        if source.is_file():
            shutil.copyfile(source, backup_dir / name)


def _restore_targeted_artifacts(round_dir: Path, backup_dir: Path) -> None:
    for name in _targeted_artifact_names():
        source = backup_dir / name
        target = round_dir / name
        if source.is_file():
            shutil.copyfile(source, target)
        else:
            target.unlink(missing_ok=True)


def _run_under_quorum_revote(
    round_dir: Path,
    core: dict[str, str],
    args: argparse.Namespace,
    threshold_env: Path,
    *,
    prune_ledger: Path,
    round_num: int,
) -> bool:
    del threshold_env
    item_ids = {item.upper() for item in _under_quorum_item_ids(core)}
    revote_dir = round_dir / "under-quorum-revote"
    slots = _review_voter_slots(round_dir)
    ok = bool(item_ids) and slots is not None
    if ok:
        originals = _snapshot_original_voters(round_dir, revote_dir, slots)
        restricted_ballot = revote_dir / "under-quorum-ballot.md"
        ok = _write_under_quorum_ballot(round_dir / "findings.md", restricted_ballot, item_ids)
    else:
        originals = []
        restricted_ballot = revote_dir / "under-quorum-ballot.md"
    dispatch_env: dict[str, str] = {}
    if ok:
        dispatch_args = _build_targeted_dispatch_args(round_dir, args, restricted_ballot, revote_dir)
        ok = dispatch_args is not None
    else:
        dispatch_args = None
    if ok and dispatch_args is not None:
        commands = review_core_body._review_commands()  # noqa: SLF001 - targeted retry reuses review-core command overrides.
        dispatch_result = (
            review_core_body._run_command_string(command=commands.dispatch_voters, args=dispatch_args)  # noqa: SLF001 - targeted retry reuses review-core command overrides.
            if commands.dispatch_voters
            else review_core_body._run_python_cli(["agent", "dispatch-voters", *dispatch_args])  # noqa: SLF001 - targeted retry reuses review-core command overrides.
        )
        _write_text(path=revote_dir / "review-core-voters.env", text=dispatch_result.stdout)
        dispatch_env = _parse_env_file(revote_dir / "review-core-voters.env")
        ok = dispatch_result.returncode == 0
    revote_files = [dispatch_env.get(f"VOTER_{idx}_PATH", "") for idx in range(1, 4)]
    merged_paths = [str(round_dir / f"under-quorum-merged-voter-{idx}.txt") for idx in range(1, 4)]
    if ok and slots is not None:
        merged = _merge_targeted_voter_outputs(
            originals=originals,
            revote_files=revote_files,
            under_quorum_ids=item_ids,
            output_paths=merged_paths,
        )
        tally_args = _build_targeted_tally_args(round_dir, core, args, merged, slots.voter_tools)
        ok = tally_args is not None
    else:
        tally_args = None
    tally_env_path = revote_dir / "review-core-targeted-tally.env"
    backup_dir = revote_dir / "pre-targeted-final"
    if ok and tally_args is not None:
        _backup_targeted_artifacts(round_dir, backup_dir)
        commands = review_core_body._review_commands()  # noqa: SLF001 - targeted retry reuses review-core command overrides.
        tally_result = (
            review_core_body._run_command_string(command=commands.tally, args=tally_args)  # noqa: SLF001 - targeted retry reuses review-core command overrides.
            if commands.tally
            else review_core_body._call_maybe_override(command="", review_name="tally-code-votes", args=tally_args)  # noqa: SLF001 - targeted retry reuses review-core command overrides.
        )
        _write_text(path=tally_env_path, text=tally_result.stdout)
        tally = _parse_env_file(tally_env_path)
        ok = bool(tally.get("TALLY_STATUS")) and tally.get("TALLY_STATUS") != "main-agent-vote-required"
    else:
        tally = {}
    emit: dict[str, str] = {}
    if ok:
        emit_args = _build_targeted_emit_args(round_dir, core, tally_env_path, args)
        ok = emit_args is not None
    else:
        emit_args = None
    if ok and emit_args is not None:
        commands = review_core_body._review_commands()  # noqa: SLF001 - targeted retry reuses review-core command overrides.
        with _temporary_env(name=config.ENV_IMPLEMENT_TMPDIR, value=str(getattr(args, "implement_tmpdir", ""))):
            emit = review_core_body._emit_tally_with_context(  # noqa: SLF001 - targeted retally must mirror emit-tally context.
                commands=commands,
                args=emit_args,
                out_file=revote_dir / "review-core-targeted-emit.env",
                session_env_path=str(getattr(args, "session_env_path", "")),
            )
        ok = emit.get("EMIT_OK") == "true"
    if ok:
        _apply_targeted_retally_outputs(
            round_dir,
            round_dir / "review-core.env",
            core,
            tally,
            emit,
            args,
            prune_ledger=prune_ledger,
            round_num=round_num,
            panel_manifest=round_dir / "panel-manifest.ndjson",
        )
    elif backup_dir.is_dir():
        _restore_targeted_artifacts(round_dir, backup_dir)
    return ok


def _surface_dropped_reviewer_warning(
    *,
    core: dict[str, str],
    round_num: int,
    session_env_path: str,
    attempts_env: Path | None,
    threshold_env: Path | None,
    dropped_slots_file: Path | None,
    panel_manifest: Path | None,
) -> None:
    sources = [
        core,
        _parse_env_file(threshold_env) if threshold_env and threshold_env.is_file() else {},
        _parse_env_file(attempts_env) if attempts_env and attempts_env.is_file() else {},
    ]
    dynamic_failed = max(_env_int(mapping=source, key="DYNAMIC_FAILED_SLOTS") for source in sources)
    dynamic_dropped = max(_env_int(mapping=source, key="DYNAMIC_DROPPED_SLOTS") for source in sources)
    straggler = max(_env_int(mapping=source, key="STRAGGLER_DROPPED_COUNT") for source in sources)
    has_dynamic_backstop = straggler > 0 and (
        _dynamic_evidence_in_dropped_file(dropped_slots_file)
        or _dynamic_evidence_in_manifest(panel_manifest, dropped_slots_file=dropped_slots_file)
    )
    if dynamic_failed == 0 and dynamic_dropped == 0 and not has_dynamic_backstop:
        return
    review_tally.surface_warning(
        session_env_path=session_env_path,
        entry=(
            f"- **code-review panel (round {round_num})**: dynamic reviewer slot drop/failure detected "
            f"(failed={dynamic_failed}, dropped={dynamic_dropped}, stragglers={straggler}); "
            "review continued with the remaining panel output."
        ),
    )


def _run_round(args: argparse.Namespace, *, suppress_emit: bool, review_core_impl: ReviewCoreImpl | None = None) -> RoundResult:
    implement_tmpdir = Path(args.implement_tmpdir).resolve()
    round_num = int(args.round_num)
    round_dir = implement_tmpdir / f"round-{round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)
    if round_num == 1:
        _run([sys.executable, str(_PY_CLI), "git", "snapshot-untracked", "--output", str(implement_tmpdir / "pre-review-untracked.txt")])
        head = _git_head()
        if head:
            _write_text(path=implement_tmpdir / "pre-review-head.txt", text=head + "\n")
    prune_ledger = implement_tmpdir / "reviewer-prune-ledger.tsv"
    prune_ledger.parent.mkdir(parents=True, exist_ok=True)
    prune_ledger.touch(exist_ok=True)
    dynamic = _dynamic_archetypes(args=args, implement_tmpdir=implement_tmpdir)
    core_out = round_dir / "review-core.env"
    core_args = _core_args_for_round(args=args, round_dir=round_dir, dynamic_archetypes=dynamic, prune_ledger=prune_ledger)
    threshold_env = round_dir / "review-core-threshold.env"
    attempts_env = round_dir / "dropped-reviewer-attempts.env"
    degraded_retry_flag = round_dir / "degraded-retry.flag"
    degraded_retry_done = round_dir / "degraded-retry.done"
    degraded_retry_flag.unlink(missing_ok=True)
    if not degraded_retry_done.is_file():
        attempts_env.unlink(missing_ok=True)
    core_rc = 0
    if degraded_retry_done.is_file() and core_out.is_file():
        _err(f"↻ /implement Step 5: round {round_num} degraded retry already settled; reloading round artifacts.")
    else:
        core_rc = review_core_capture(core_args=core_args, env_path=core_out, review_core_impl=review_core_impl, implement_tmpdir=implement_tmpdir)
        _merge_dropped_reviewer_attempt(round_dir=round_dir, threshold_env=threshold_env)
    core = _parse_env_file(core_out)
    (
        core_status,
        accepted_count,
        rejected_count,
        exonerated_count,
        neutral_count,
        accepted_file,
        rejected_file,
    ) = _core_round_state(core=core, round_dir=round_dir)
    oos_jsonl = implement_tmpdir / "accumulated-oos.jsonl"
    oos_markdown = implement_tmpdir / "accumulated-oos.md"
    round_oos = round_dir / "oos-accepted-review.md"
    degraded_this_round = False
    voting_tally_file = round_dir / "voting-tally.md"
    degraded_banner_present = voting_tally_file.is_file() and "⚠ Degraded code-review panel" in _read_text(voting_tally_file)
    retry_degraded_panel = degraded_banner_present and not _core_status_is(core_status, ReviewCoreStatus.zero_findings)
    if retry_degraded_panel:
        degraded_this_round = True
        if degraded_retry_done.is_file():
            _err(f"↻ /implement Step 5: round {round_num} degraded retry sentinel present; using settled degraded retry result.")
        else:
            _err(f"⏳ /implement Step 5: round {round_num} panel was degraded (banner triggered); retrying once.")
            degraded_retry_flag.touch()
            shutil.copyfile(voting_tally_file, round_dir / "voting-tally-degraded-attempt-1.md")
            targeted_ok = _pure_under_quorum_degradation(core, threshold_env, round_dir) and _run_under_quorum_revote(
                round_dir,
                core,
                args,
                threshold_env,
                prune_ledger=prune_ledger,
                round_num=round_num,
            )
            if not targeted_ok:
                _append_round_oos_artifact(round_num=round_num, round_oos=round_oos, oos_jsonl=oos_jsonl, oos_markdown=oos_markdown)
                core_rc = review_core_capture(core_args=core_args, env_path=core_out, review_core_impl=review_core_impl, implement_tmpdir=implement_tmpdir)
                _merge_dropped_reviewer_attempt(round_dir=round_dir, threshold_env=threshold_env)
            core = _parse_env_file(core_out)
            (
                core_status,
                accepted_count,
                rejected_count,
                exonerated_count,
                neutral_count,
                accepted_file,
                rejected_file,
            ) = _core_round_state(core=core, round_dir=round_dir)
            degraded_retry_done.touch()
            if not targeted_ok and not _reviewer_prune_status_records(core_status):
                _clear_reviewer_prune_round(ledger=prune_ledger, round_num=round_num, work_dir=round_dir)
            retry_tally_text = _read_text(voting_tally_file) if voting_tally_file.is_file() else ""
            attempt_1_text = _read_text(round_dir / "voting-tally-degraded-attempt-1.md")
            if voting_tally_file.is_file() and "⚠ Degraded code-review panel" in retry_tally_text:
                if retry_tally_text != attempt_1_text:
                    shutil.copyfile(voting_tally_file, round_dir / "voting-tally-degraded-attempt-2.md")
                _err(f"⚠ /implement Step 5: round {round_num} panel retry also degraded; proceeding best-effort.")
            else:
                degraded_this_round = False
    _surface_under_quorum_warning(core=core, round_num=round_num, session_env_path=args.session_env_path)
    _surface_dropped_reviewer_warning(
        core=core,
        round_num=round_num,
        session_env_path=args.session_env_path,
        attempts_env=attempts_env,
        threshold_env=threshold_env,
        dropped_slots_file=_resolve_dropped_slots_file(round_dir=round_dir, core=core),
        panel_manifest=round_dir / "panel-manifest.ndjson",
    )
    if degraded_this_round:
        _surface_parse_failed_warning(core=core, round_num=round_num, session_env_path=args.session_env_path)
    _append_round_oos_artifact(round_num=round_num, round_oos=round_oos, oos_jsonl=oos_jsonl, oos_markdown=oos_markdown)
    rejected_full = round_dir / "rejected-findings-full.md"
    if rejected_full.is_file():
        with contextlib.suppress(OSError):
            shutil.copyfile(rejected_full, implement_tmpdir / "rejected-findings-full.md")
    write_rejected_findings_aggregate(impl_tmpdir=implement_tmpdir, fallback_file=rejected_file)
    coder = CoderResult(0)
    skipped_finding_count = 0
    classifier_failed = False
    in_scope = round_dir / "accepted-in-scope-findings.md"
    if accepted_count > 0 and accepted_file.is_file() and accepted_file.stat().st_size:
        _filter_in_scope(accepted_file=accepted_file, output=in_scope)
        if _count_findings(in_scope) > 0:
            _write_pre_coder_snapshot(round_dir)
            coder = apply_findings_with_coder(input_file=in_scope, round_dir=round_dir, result_file=round_dir / "coder.env", round_num=round_num)
            if coder.status == "applied" and coder.log_file:
                skipped_finding_count, classifier_failed = _process_skipped_findings(
                    round_dir=round_dir,
                    in_scope_file=in_scope,
                    coder_log=Path(coder.log_file),
                    implement_tmpdir=implement_tmpdir
                )
    status = "complete"
    exit_code = 0
    if _core_zero_survivor_panel_failed(core):
        status = "self-review-required"
    elif _core_status_is(core_status, ReviewCoreStatus.panel_failed, ReviewCoreStatus.aggregator_validation_exhausted):
        status = str(core_status)
        exit_code = 2
    elif _core_status_is(core_status, ReviewCoreStatus.main_agent_vote_required):
        status = "main-agent-vote-required"
    elif _core_status_is(core_status, ReviewCoreStatus.fix_required, ReviewCoreStatus.cap_reached):
        if coder.rc == 4 or coder.status == "main-agent-required":
            status = "coder-main-agent-required"
        elif coder.rc in {2, 3} or coder.status == "submodule-violation":
            status = "coder-failed"
            exit_code = 2
        elif coder.status == "applied":
            status = "fix-applied"
        elif coder.status == "no-changes":
            status = "no-changes"
        else:
            status = "in-scope-filtered-out"
    elif _core_status_is(core_status, ReviewCoreStatus.prune_skipped):
        status = "prune-skipped"
    elif _core_status_is(core_status, ReviewCoreStatus.zero_findings, ReviewCoreStatus.ok):
        status = "complete"
    else:
        status = core_status
    if core_rc != 0 and exit_code == 0 and status != "self-review-required":
        exit_code = core_rc
    if status in {"complete", "no-changes"} and accepted_count > 0 and not degraded_this_round:
        nit = min(_nit_count(accepted_file), accepted_count)
        non_nit = accepted_count - nit
        findings_path = round_dir / "findings.md"
        if non_nit <= 5:
            if findings_path.is_file() and os.access(findings_path, os.R_OK):
                if not _important_present(findings_path):
                    status = "converged-small-changes"
            elif non_nit > 0:
                _err(f"review-and-fix: findings file not readable for Important check: {findings_path}")
                classifier_failed = True
    if classifier_failed:
        status = "classifier-failed"
        exit_code = 2
    if status == "fix-applied":
        with contextlib.suppress(FileNotFoundError):
            (round_dir / "post-coder-head.txt").unlink()
        head = _git_head()
        if head:
            post = round_dir / "post-coder-head.txt"
            _write_text(path=post, text=head + "\n")
            post.chmod(0o444)
    prior_accepted, prior_rejected, prior_exonerated, prior_neutral = _prior_summary_counts(implement_tmpdir=implement_tmpdir, round_num=round_num)
    total_accepted = prior_accepted + accepted_count
    total_rejected = prior_rejected + rejected_count
    total_exonerated = prior_exonerated + exonerated_count
    total_neutral = prior_neutral + neutral_count
    summary_file = implement_tmpdir / "review-and-fix-summary.json"
    accumulated_oos = implement_tmpdir / "accumulated-oos.jsonl"
    composed_findings = round_dir / "review-findings-full.composed.jsonl"
    composed_ok = False
    if exit_code == 0:
        composed_ok = _compose_review_findings_output(impl_tmpdir=implement_tmpdir, output=composed_findings)
        if composed_ok:
            derived_accepted, derived_rejected = _derive_code_review_tally(composed_findings)
            total_accepted = derived_accepted
            total_rejected = derived_rejected
        elif status in {"complete", "no-changes", "converged-small-changes"}:
            status = "tally-flush-failed"
            exit_code = 2
    result = RoundResult(
        exit_code,
        status,
        core_status,
        round_num,
        accepted_count,
        rejected_count,
        exonerated_count,
        neutral_count,
        total_accepted,
        total_rejected,
        total_exonerated,
        total_neutral,
        accepted_file,
        rejected_file,
        round_dir,
        summary_file,
        accumulated_oos,
        coder,
        degraded_this_round,
        skipped_finding_count,
    )
    _write_summary(path=summary_file, result=result, round_cap=int(getattr(args, "round_cap", 2) or 2))
    flush_scout_manifest(implement_tmpdir=implement_tmpdir, run_id=getattr(args, "run_id", "") or "", round_num=round_num, round_dir=round_dir, core=core)
    with contextlib.suppress(Exception):
        progress_report.write_implement_round_meta(round_dir)
    flush_round_log_after_coder(impl_tmpdir=implement_tmpdir, run_id=getattr(args, "run_id", "") or "", round_num=round_num, round_dir=round_dir)
    env_file = round_dir / "review-and-fix.env"
    _write_text(path=env_file, text=f"REVIEW_AND_FIX_STATUS={status}\n")
    if not suppress_emit:
        _emit_round_kvs(result)
    return result


def _emit_round_kvs(result: RoundResult) -> None:
    _emit_kv(key="REVIEW_AND_FIX_STATUS", value=result.status)
    _emit_kv(key="REVIEW_CORE_STATUS", value=result.core_status)
    _emit_kv(key="ROUND_NUM", value=result.round_num)
    _emit_kv(key="ACCEPTED_COUNT", value=result.accepted_count)
    _emit_kv(key="REJECTED_COUNT", value=result.rejected_count)
    _emit_kv(key="TOTAL_ACCEPTED_COUNT", value=result.total_accepted_count)
    _emit_kv(key="TOTAL_REJECTED_COUNT", value=result.total_rejected_count)
    _emit_kv(key="EXONERATED_COUNT", value=result.exonerated_count)
    _emit_kv(key="NEUTRAL_COUNT", value=result.neutral_count)
    _emit_kv(key="FIX_COUNT", value=result.coder.input_count)
    _emit_kv(key="APPROVED_FIXES_FILE", value=str(result.accepted_file))
    _emit_kv(key="REJECTED_FINDINGS_FILE", value=str(result.rejected_file))
    _emit_kv(key="FINDINGS_FILE", value=str(result.round_dir / "findings.md"))
    _emit_kv(key="REVIEW_ROUND_DIR", value=str(result.round_dir))
    _emit_kv(key="REVIEW_AND_FIX_SUMMARY_FILE", value=str(result.summary_file))
    _emit_kv(key="ACCUMULATED_OOS_FILE", value=str(result.accumulated_oos_file))
    _emit_kv(key="TOTAL_EXONERATED_COUNT", value=result.total_exonerated_count)
    _emit_kv(key="TOTAL_NEUTRAL_COUNT", value=result.total_neutral_count)
    _emit_kv(key="CODER_TOOL", value=result.coder.tool)
    _emit_kv(key="CODER_STATUS", value=result.coder.status)
    if result.coder.log_file:
        _emit_kv(key="CODER_LOG_FILE", value=result.coder.log_file)
    if result.coder.commit_sha:
        _emit_kv(key="CODER_COMMIT_SHA", value=result.coder.commit_sha)
    _emit_kv(key="SUBMODULE_SCRUB_COUNT", value=result.coder.scrub_count)
    _emit_kv(key="SUBMODULE_REVERT_COUNT", value=result.coder.revert_count)
    _emit_kv(key="SKIPPED_FINDING_COUNT", value=result.skipped_finding_count)
    _emit_kv(key="DEGRADED_ROUND", value=result.degraded_round)
# pyright: reportPrivateUsage=false, reportUnusedFunction=false, reportUnknownVariableType=false, reportUnknownMemberType=false
