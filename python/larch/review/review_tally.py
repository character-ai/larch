# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Review vote tally, tally emission, and log-phase CLI entry points."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import suppress
from collections import defaultdict
from pathlib import Path
from typing import NoReturn, cast

from larch import io as larch_io
from larch.review import findings_ledger
from larch.core import logging_util
from larch.review import voting
from larch.review.review_types import JudgeSeverity, ReviewVote

_PLUGIN_ROOT = Path(__file__).resolve().parents[3]
_THREE_SLOT_COUNT = 3
# Issue #4880: smallest effective panel for which a per-item valid-vote count below quorum is a
# meaningful degradation signal (a 1-voter panel can never drop "below quorum").
_MIN_DEGRADABLE_PANEL = 2
_CLASSIFICATION_HEADER = (
    "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tscope"
)
_OOS_AGGREGATE_POOL = "oos-aggregate-pool.md"
_OOS_HEADER_RE = re.compile(r"^###\s+OOS_(\d+):", re.MULTILINE)
_OOS_POOL_HEADER_RE = re.compile(r"^###\s+(?:OOS|FINDING)_\d+:", re.MULTILINE)


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def _die(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def _read(path: Path) -> str:
    return larch_io.read_text(path)


def _write(*, path: Path, text: str) -> None:
    larch_io.write_text(path=path, text=text)


def _append(*, path: Path, text: str) -> None:
    larch_io.append_text(path=path, text=text)


def _kv_parse(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text)


def _parse_multi(*, argv: list[str], flag: str) -> tuple[list[str], list[str]]:
    out: list[str] = []
    rest: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] == flag:
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                out.append(argv[i])
                i += 1
        else:
            rest.append(argv[i])
            i += 1
    return rest, out


def _parse_tally_args(argv: list[str]) -> argparse.Namespace:
    rest, voter_files = _parse_multi(argv=argv, flag="--voter-files")
    rest, voter_tools = _parse_multi(argv=rest, flag="--voter-tools")
    parser = argparse.ArgumentParser(prog="tally-code-votes")
    parser.add_argument("--ballot-file", required=True)
    parser.add_argument("--review-tmpdir", required=True)
    parser.add_argument("--session-env-path", default="")
    parser.add_argument("--scope-files", default="")
    parser.add_argument("--plan-file", default="")
    parser.add_argument("--manifest-file", default="")
    parser.add_argument("--collector-results-file", default="")
    parser.add_argument("--not-substantive-count", default="0")
    parser.add_argument("--cursor-available", default="")
    parser.add_argument("--codex-available", default="")
    parser.add_argument("--round-num", default="1")
    parser.add_argument("--both-down", default="false")
    parser.add_argument("--proposer-map-file", default="")
    args = parser.parse_args(rest)
    args.voter_files = voter_files
    args.voter_tools = voter_tools
    return args


def _nested_implement_round(*, review_tmpdir: Path, session_env_path: str) -> bool:
    try:
        review_real = review_tmpdir.resolve()
    except OSError:
        return False
    if not re.match(r"round-[0-9]+$", review_real.name):
        return False
    parent = review_real.parent
    impl = os.environ.get("IMPLEMENT_TMPDIR", "")
    if impl:
        try:
            if Path(impl).resolve() == parent:
                return True
        except OSError:
            return False
    if session_env_path:
        try:
            return Path(session_env_path).parent.resolve() == parent
        except OSError:
            return False
    return False


def _sanitize_classification_text_cell(cell: str) -> str:
    cleaned = re.sub(r"[\t\r\n]", " ", cell)
    cleaned = re.sub(r"\s*\|\s*", "|", cleaned)
    if cleaned.startswith(("=", "+", "-", "@")):
        return "'" + cleaned
    return cleaned


def _reviewer_slots_for_tsv(reviewer: str) -> str:
    return "|".join(part.strip() for part in reviewer.split(",") if part.strip())


def _sanitize_vote(vote: str) -> str:
    return vote if vote in {item.value for item in ReviewVote} else ""


def _sanitize_correctness(value: str) -> str:
    return value if value in {"true", "partially-true", "false-positive", "uncertain"} else ""


def _sanitize_severity(value: str) -> str:
    return value if value in {item.value for item in JudgeSeverity} else ""


def _sanitize_quality(value: str) -> str:
    return value if value in {"excellent", "good", "adequate", "weak", "no-fix", "uncertain"} else ""


def _sanitize_uncertain(value: str) -> str:
    return value if value in {"true", "false"} else "true"


def _sanitize_result(value: str) -> str:
    return value if value in {"accepted", "rejected", "neutral"} else ""


def _classification_row(*,
    item_id: str,
    reviewer: str,
    result: str,
    cells: list[tuple[str, str, str, str, str, str | None]],
    three_slot: bool,
    is_oos: bool,
) -> str:
    row = [item_id, _sanitize_classification_text_cell(_reviewer_slots_for_tsv(reviewer)), _sanitize_result(result)]
    for idx in range(3):
        vote = correctness = severity = quality = uncertain = ""
        tool: str | None = None
        if idx < len(cells):
            vote, correctness, severity, quality, uncertain, tool = cells[idx]
        has_rating = bool(vote or correctness or severity or quality or uncertain)
        if three_slot and not has_rating:
            row.extend(["", "", "", "", "", _sanitize_classification_text_cell(tool or "")])
            continue
        clean_vote = _sanitize_vote(vote or "JUDGE_ERROR") if has_rating else ""
        clean_correctness = _sanitize_correctness(correctness)
        clean_severity = _sanitize_severity(severity)
        clean_quality = _sanitize_quality(quality)
        clean_uncertain = uncertain
        if has_rating and (not clean_correctness or not clean_severity or not clean_quality):
            clean_uncertain = "true"
        row.extend([clean_vote, clean_correctness, clean_severity, clean_quality, _sanitize_uncertain(clean_uncertain) if has_rating else ""])
        if three_slot:
            row.append(_sanitize_classification_text_cell(tool or ""))
    row.append("oos" if is_oos else "in_scope")
    return "\t".join(row)


def _voter_votes_and_severities(
    cells: list[tuple[str, str, str, str, str, str | None]],
    *,
    voter_tools: list[str],
    three_slot: bool,
) -> tuple[list[tuple[str, str]], list[str]]:
    if three_slot:
        return (
            [(str(voter_tools[idx]), cells[idx][0] if idx < len(cells) else "") for idx in range(3)],
            [cells[idx][2] if idx < len(cells) else "" for idx in range(3)],
        )
    return (
        [(f"v{pos}", cells[pos - 1][0] if pos - 1 < len(cells) else "") for pos in range(1, 4)],
        [cells[pos - 1][2] if pos - 1 < len(cells) else "" for pos in range(1, 4)],
    )


def _block_files(*, ballot_file: Path, review_tmpdir: Path) -> list[Path]:
    block_dir = Path(tempfile.mkdtemp(prefix="larch-tally-blocks-", dir=str(review_tmpdir)))
    try:
        voting.split_ballot(ballot_file=ballot_file, out_dir=block_dir)
    except SystemExit as exc:
        raise RuntimeError("duplicate or malformed FINDING/OOS headings in ballot") from exc
    return sorted(block_dir.glob("*.md"), key=lambda p: (0 if p.stem.startswith("FINDING_") else 1, int(p.stem.split("_", 1)[1]) if p.stem.split("_", 1)[1].isdigit() else 0))


def _parse_rate_ok(*, voter_file: str, ballot_file: Path, review_tmpdir: Path, tool: str, slot: str = "") -> bool:
    if not voter_file or not Path(voter_file).is_file() or Path(voter_file).stat().st_size == 0:
        return False
    cmd = [
        "python3",
        str(_PLUGIN_ROOT / "python" / "cli.py"),
        "voting",
        "parse-rate-check",
        "--voter-file",
        voter_file,
        "--ballot-file",
        str(ballot_file),
        "--id-grammar",
        "finding-oos",
        "--review-tmpdir",
        str(review_tmpdir),
        "--log-mode",
        "none",
        "--voter-tool",
        tool,
    ]
    if slot:
        cmd.extend(["--slot", slot])
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        _die(f"tally-code-votes: voter parse-rate check failed for {voter_file}")
    status = _kv_parse(proc.stdout).get("PARSE_RATE_STATUS", "")
    if not status:
        _die(f"tally-code-votes: voter parse-rate check emitted no PARSE_RATE_STATUS for {voter_file}")
    return status == "OK"


def _scope_drift(*, block: Path, scope_files: str, plan_file: str) -> bool:
    if not scope_files or not Path(scope_files).is_file() or Path(scope_files).stat().st_size == 0:
        return False
    heading = _read(block).splitlines()[0] if _read(block).splitlines() else ""
    heading = heading.replace("`", "").replace("*", "").replace("_", "")
    paths = [re.sub(r":[0-9]+$", "", p) for p in re.findall(r"[a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+:[0-9]+", heading)]
    if not paths:
        return False
    scope_text = _read(Path(scope_files))
    plan_text = _read(Path(plan_file)) if plan_file and Path(plan_file).is_file() else ""
    return all(path not in scope_text.splitlines() and path not in plan_text for path in paths)


def _not_substantive_warning(count: int) -> str:
    return (
        f"**⚠ Degraded code-review panel: {count} reviewer slot(s) emitted narrative-only output "
        "(NOT_SUBSTANTIVE). Dead slots are shown in the scoreboard below.**"
    )


def _seed_oos_seq(session_env_path: str) -> int:
    if not session_env_path:
        return 0
    accumulated = Path(session_env_path).parent / "accumulated-oos.md"
    if not accumulated.is_file() or accumulated.stat().st_size == 0:
        return 0
    count = 0
    in_block = False
    for line in _read(accumulated).splitlines():
        if re.match(r"^###[ \t]+(OOS_[0-9]+:|FINDING_[0-9]+:)", line):
            if in_block:
                count += 1
            in_block = True
    if in_block:
        count += 1
    return count


def _static_focus_area(slug: str) -> str:
    return {
        "structure": "code-quality",
        "correctness": "correctness",
        "testing": "risk-integration",
        "security": "security",
        "edge-cases": "correctness",
        "plan-fidelity": "architecture",
        "plan-fidelity-auto": "architecture",
    }.get(slug, "code-quality")


def _write_archetype_map(manifest_file: Path) -> dict[str, tuple[str, str, str]]:
    mapping: dict[str, tuple[str, str, str]] = {}
    order: list[str] = []
    if not manifest_file.is_file():
        return mapping
    for line in _read(manifest_file).splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        output = str(row.get("output") or "")
        base = voting.normalize_reviewer_basename(output.rsplit("/", 1)[-1] if output else "")
        slot = str(row.get("slot") or "")
        focus = str(row.get("focus_area") or "")
        weight = str(row.get("weight") or "1")
        if base == "codex-generalist-output.txt":
            archetype, focus, weight = "generic", "code-quality", "1"
        elif base.startswith("dyn-") and base.endswith("-output.txt"):
            archetype = slot if slot.startswith("dyn-") else base.removesuffix("-output.txt")
            focus = focus or "code-quality"
        elif re.match(r"^(cursor|codex)-specialist-.+-output\.txt$", base):
            static_slug = base.removeprefix("cursor-specialist-").removeprefix("codex-specialist-").removesuffix("-output.txt")
            archetype = static_slug
            focus = _static_focus_area(static_slug)
            weight = "1"
        else:
            archetype = slot or base.removesuffix("-output.txt")
            focus = focus or "code-quality"
            weight = "1"
        if not weight.isdigit():
            weight = "1"
        if base not in mapping:
            order.append(base)
        mapping[base] = (archetype, focus, weight)
    return {base: mapping[base] for base in order}


def _parse_collector_status(collector_file: str) -> dict[str, str]:
    if not collector_file or not Path(collector_file).is_file():
        return {}
    status_map: dict[str, str] = {}
    cr_file = ""
    cr_status = ""
    for line in _read(Path(collector_file)).splitlines():
        if not line:
            if cr_file and cr_status:
                status_map[voting.normalize_reviewer_basename(cr_file)] = cr_status
            cr_file = ""
            cr_status = ""
        elif line.startswith("REVIEWER_FILE="):
            cr_file = line[len("REVIEWER_FILE=") :]
        elif line.startswith("STATUS="):
            cr_status = line[len("STATUS=") :]
    if cr_file and cr_status:
        status_map[voting.normalize_reviewer_basename(cr_file)] = cr_status
    return status_map


def _append_manifest_dead_rows(
    tally_lines: list[str],
    *,
    manifest_file: Path,
    collector_file: str,
    score_rows: list[tuple[str, str, str, int]],
) -> None:
    collector_status = _parse_collector_status(collector_file)
    seen = {voting.normalize_reviewer_basename(reviewer) for reviewer, _kind, _result, _accepted_weight in score_rows}
    for line in _read(manifest_file).splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        output = str(row.get("output") or "")
        base = voting.normalize_reviewer_basename(output.rsplit("/", 1)[-1] if output else "")
        if not base or base in seen:
            continue
        status = collector_status.get(base, "OK")
        label = re.sub(r"(?:-output)?\.txt$", "", base)
        tally_lines.append(f"| {label} | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | STATUS={status} |\n")


def _write_yield_tsv(*,
    yield_path: Path,
    archetype_map: dict[str, tuple[str, str, str]],
    score_rows: list[tuple[str, str, str, int]],
) -> list[str]:
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for reviewer, kind, result, _accepted_weight in score_rows:
        if kind != "finding":
            continue
        base = voting.normalize_reviewer_basename(reviewer)
        totals[base][0] += 1
        if result == "accepted":
            totals[base][1] += 1
        elif result == "rejected":
            totals[base][2] += 1
    lines = ["archetype_name\tfocus_area\tweight\tfindings_total\tfindings_accepted\tfindings_rejected\tyield_ratio\n"]
    for base, (archetype, focus, weight) in archetype_map.items():
        total, accepted, rejected = totals.get(base, [0, 0, 0])
        ratio = "n/a" if total == 0 else f"{accepted / total:.6f}"
        lines.append(f"{archetype}\t{focus}\t{weight}\t{total}\t{accepted}\t{rejected}\t{ratio}\n")
    _write(path=yield_path, text="".join(lines))
    orphans: list[str] = []
    for reviewer, _kind, _result, _accepted_weight in score_rows:
        base = voting.normalize_reviewer_basename(reviewer)
        if base not in archetype_map and base not in orphans:
            orphans.append(base)
    return orphans


def _record_code_review_score_rows(
    *,
    score_state: tuple[list[tuple[str, str, str, int]], defaultdict[str, float], float],
    reviewer: str,
    classification: tuple[str, str, bool],
    cells: list[tuple[str, str, str, str, str, str | None]],
) -> int:
    score_rows, bonus_by_reviewer, active_bonus = score_state
    kind, result, neutral_rescued = classification
    score_kind = "oos" if kind == "oos" or neutral_rescued else "finding"
    accepted_weight = (
        voting.accepted_finding_points_from_severities(
            [cell[2] for cell in cells],
            votes=[cell[0] for cell in cells],
        )
        if score_kind == "finding" and result == "accepted"
        else 0
    )
    reviewer_slots = [part.strip() for part in reviewer.split(",") if part.strip()]
    score_rows.extend((reviewer_slot, score_kind, result, accepted_weight) for reviewer_slot in reviewer_slots)
    if score_kind == "finding" and result == "accepted" and len(reviewer_slots) == 1 and active_bonus > 0:
        bonus_by_reviewer[reviewer_slots[0]] += active_bonus
        return 1
    return 0


def _record_tally(*, tally_file: Path, item_id: str, accepted: bool, outcome: str) -> None:
    prefix, number = item_id.split("_", 1)
    _append(path=tally_file, text=f"{prefix}_{number}_ACCEPTED={'true' if accepted else 'false'}\n")
    if outcome == "accepted":
        _append(path=tally_file, text=f"{prefix}_{number}_OUTCOME=accepted\n")
    elif outcome == "oos":
        _append(path=tally_file, text=f"{prefix}_{number}_OUTCOME=oos\n")
    else:
        _append(path=tally_file, text=f"{prefix}_{number}_OUTCOME=rejected\n")
        subtype = "true_rejected" if outcome == "rejected" else "neutral"
        _append(path=tally_file, text=f"{prefix}_{number}_REJECTED_SUBTYPE={subtype}\n")


def _normalize_oos_header_text(*, text: str, seq: int) -> str:
    return re.sub(r"^### (?:FINDING|OOS)_[0-9]+:", f"### OOS_{seq}:", text, count=1, flags=re.MULTILINE)


def _aggregate_parent(*, review_tmpdir: Path, session_env_path: str = "", implement_tmpdir: str = "") -> Path:
    if session_env_path:
        return Path(session_env_path).parent
    if implement_tmpdir and Path(implement_tmpdir).is_dir():
        return Path(implement_tmpdir)
    return review_tmpdir


def _aggregate_oos_blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    matches = list(_OOS_POOL_HEADER_RE.finditer(normalized))
    if not matches:
        return []
    blocks: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        block = normalized[match.start():end].strip("\n")
        if block:
            blocks.append(block + "\n")
    return blocks


def _aggregate_block_identity(block: str) -> str:
    body = re.sub(r"(?m)^[ \t]*-[ \t]+\*\*Filed[ \t]*URL\*\*:[^\n]*(?:\n|$)", "", block)
    body = re.sub(r"(?m)^Vote tally:.*(?:\n|$)", "", body).strip()
    body = re.sub(r"^###\s+(?:OOS|FINDING)_\d+:", "### ITEM:", body, count=1)
    return re.sub(r"\s+", " ", body).strip().lower()


def _append_oos_pool_candidate(*, pool_file: Path, text: str) -> None:
    if not voting.artifact_marked_fileable(text):
        return
    identity = _aggregate_block_identity(text)
    if not identity:
        return
    existing = pool_file.read_text(encoding="utf-8", errors="replace") if pool_file.is_file() else ""
    if identity in {_aggregate_block_identity(block) for block in _aggregate_oos_blocks(existing)}:
        return
    pool_file.parent.mkdir(parents=True, exist_ok=True)
    separator = "" if not existing or existing.endswith("\n") else "\n"
    with pool_file.open("a", encoding="utf-8") as handle:
        _ = handle.write(separator + text.rstrip("\n") + "\n")


def _next_oos_number(text: str) -> int:
    numbers = [int(match.group(1)) for match in _OOS_HEADER_RE.finditer(text)]
    return max(numbers, default=0) + 1


def _promote_aggregate_oos_pool(*, sink: Path, pool: Path, main_agent: Path | None = None) -> None:
    sink_text = _read(sink) if sink.is_file() else ""
    accepted_seen = {_aggregate_block_identity(block) for block in _aggregate_oos_blocks(sink_text)}
    main_blocks = (
        [
            block
            for block in _aggregate_oos_blocks(_read(main_agent))
            if not voting.is_security_block_text(block)
        ]
        if main_agent is not None and main_agent.is_file()
        else []
    )
    pool_blocks = (
        [
            block
            for block in _aggregate_oos_blocks(_read(pool))
            if not voting.is_security_block_text(block)
            and re.search(r"(?mi)^Vote tally:.*\bResult=accepted\b", block)
            and voting.artifact_marked_fileable(block)
        ]
        if pool.is_file()
        else []
    )
    next_num = _next_oos_number(sink_text)
    promoted: list[str] = []
    for block in [*main_blocks, *pool_blocks]:
        identity = _aggregate_block_identity(block)
        if not identity or identity in accepted_seen:
            continue
        promoted.append(_normalize_oos_header_text(text=block, seq=next_num).rstrip("\n") + "\n")
        accepted_seen.add(identity)
        next_num += 1
    if not promoted:
        return
    separator = "" if not sink_text or sink_text.endswith("\n") else "\n"
    with sink.open("a", encoding="utf-8") as handle:
        _ = handle.write(separator + "\n".join(promoted))


def _resolve_proposer_map(*,
    ballot_file: Path,
    review_tmpdir: Path,
    explicit_map: str,
) -> tuple[str, bool]:
    proposer_map_file = explicit_map or ""
    proposer_sidecar_required = bool(proposer_map_file)
    if not proposer_map_file:
        default_map = review_tmpdir / "proposer-map.tsv"
        if default_map.is_file() and voting.ballot_is_neutralized(ballot_file):
            proposer_map_file = str(default_map)
            proposer_sidecar_required = True
    if not proposer_sidecar_required and voting.ballot_is_neutralized(ballot_file):
        proposer_sidecar_required = True
    if proposer_map_file and voting.ballot_is_neutralized(ballot_file):
        voting.validate_proposer_map_for_neutralized_ballot(ballot_file=ballot_file, map_file=proposer_map_file)
    return proposer_map_file, proposer_sidecar_required


def _proposer_for_item(*, item_id: str, block: Path, map_file: str, sidecar_required: bool) -> str:
    return voting.proposer_for_item(item_id=item_id, block_file=block, map_file=map_file, sidecar_required=sidecar_required)


def _artifact_text_for_item(*, item_id: str, block: Path, map_file: str) -> str:
    text = _read(block)
    reviewer_line = voting.reviewer_line_for_item(item_id=item_id, map_file=map_file)
    return voting.restore_reviewer_attribution(block_text=text, reviewer_line=reviewer_line)


def _security_block(block: Path) -> bool:
    try:
        return voting.is_security_block(block)
    except SystemExit as exc:
        raise RuntimeError("security classifier failed") from exc


def _execution_issues_log(session_env_path: str) -> Path | None:
    if os.environ.get("LARCH_EXECUTION_ISSUES_LOG"):
        return Path(os.environ["LARCH_EXECUTION_ISSUES_LOG"])
    if session_env_path:
        return Path(session_env_path).parent / "execution-issues.md"
    if os.environ.get("IMPLEMENT_TMPDIR"):
        return Path(os.environ["IMPLEMENT_TMPDIR"]) / "execution-issues.md"
    return None


def surface_warning(*, session_env_path: str, entry: str) -> None:
    """Issue #4880: surface a degraded-panel warning to the operator-visible run-summary.

    The run-summary "Warnings" count is harvested from ``execution-issues.md`` (category
    ``Warnings``). Degraded-panel signals previously landed only in the per-round
    ``voting-tally.md`` artifact, so they never reached the operator's run-summary. Best-effort:
    a no-op when no execution-issues log can be resolved (e.g. a standalone tally invocation).
    """
    log = _execution_issues_log(session_env_path=session_env_path)
    if log is None:
        return
    cmd = [
        sys.executable,
        str(_PLUGIN_ROOT / "python" / "cli.py"),
        "run-log",
        "append-entry",
        "--log",
        str(log),
        "--category",
        "Warnings",
        "--entry",
        entry,
    ]
    with suppress(OSError):
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def _ledger_title(*, block_text: str, item_id: str) -> str:
    first = block_text.splitlines()[0] if block_text.splitlines() else ""
    title = re.sub(rf"^###\s+{re.escape(item_id)}:\s*", "", first).strip()
    return title or item_id


def _ledger_file_line(block_text: str) -> str:
    for regex in voting.FILE_LINE_REGEXES.values():
        match = re.search(regex, block_text)
        if match:
            return match.group(0).strip(" \t\n\r`*()[],:;")
    return ""


def _ledger_reason(block_text: str) -> str:
    for line in block_text.splitlines()[1:]:
        normalized = line.replace("*", "").strip()
        if re.match(r"^[- ]*(Concern|Scenario|Reason|Suggested (revision|fix)):", normalized, re.IGNORECASE):
            return re.sub(r"^[- ]*[^:]+:\s*", "", normalized).strip()
    return ""


def _ledger_entry(*, item_id: str, block_text: str, outcome: str, vote_tally: str) -> dict[str, object]:
    return {
        "finding_id": item_id,
        "title": _ledger_title(block_text=block_text, item_id=item_id),
        "file_line": _ledger_file_line(block_text),
        "outcome": outcome,
        "vote_tally": vote_tally,
        "reason": _ledger_reason(block_text),
    }


def _record_public_oos_artifact(*, oos_file: Path, pool_file: Path, security_sidecar: Path, artifact: str, security: bool, accepted: bool) -> None:
    if security:
        _append(path=security_sidecar, text=artifact)
        return
    _append(path=oos_file, text=artifact)
    if accepted:
        _append_oos_pool_candidate(pool_file=pool_file, text=artifact)


def _finding_oos_reroute_marker(*, block_text: str, neutral_rescued: bool) -> str:
    _ = block_text
    if neutral_rescued:
        return "neutral-rescued"
    return ""


def _record_classification_and_ledger(*,
    class_tsv: Path,
    classification_row: str,
    ledger_entries: list[dict[str, object]],
    ledger_entry: dict[str, object],
) -> None:
    _append(path=class_tsv, text=classification_row + "\n")
    ledger_entries.append(ledger_entry)


def _write_final_tally_outputs(*,
    tally_env: Path,
    counts_text: str,
    review_tmpdir: Path,
    args: argparse.Namespace,
    ledger_entries: list[dict[str, object]],
) -> None:
    findings_ledger.write_round(
        findings_ledger.ledger_root(review_tmpdir, session_env_path=args.session_env_path),
        int(args.round_num),
        ledger_entries,
    )
    _append(path=tally_env, text=counts_text)


def tally_code_votes(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="tally-code-votes")
    try:
        args = _parse_tally_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    ballot_file = Path(args.ballot_file)
    review_tmpdir = Path(args.review_tmpdir)
    if not ballot_file.is_file():
        return _error("tally-code-votes: --ballot-file must name a file")
    if args.manifest_file and not Path(args.manifest_file).is_file():
        return _error("tally-code-votes: --manifest-file must name a file")
    if not str(args.round_num).isdigit() or int(args.round_num) <= 0:
        return _error("tally-code-votes: --round-num must be a positive integer")
    try:
        proposer_map_file, proposer_sidecar_required = _resolve_proposer_map(
            ballot_file=ballot_file,
            review_tmpdir=review_tmpdir,
            explicit_map=str(args.proposer_map_file or "")
        )
    except voting.TallyError as exc:
        return _error(f"tally-code-votes: {exc}")
    active_bonus = voting.unique_finder_bonus_from_env()
    review_tmpdir.mkdir(parents=True, exist_ok=True)
    three_slot = bool(args.voter_tools)
    if three_slot and (len(args.voter_files) != _THREE_SLOT_COUNT or len(args.voter_tools) != _THREE_SLOT_COUNT):
        return _error("tally-code-votes: --voter-tools requires exactly three --voter-files and three tool labels")
    accepted_file = review_tmpdir / "accepted-findings.md"
    rejected_file = review_tmpdir / "rejected-findings.md"
    oos_accepted_file = review_tmpdir / "oos-accepted-review.md"
    security_oos_file = (Path(args.session_env_path).parent if args.session_env_path else oos_accepted_file.parent) / "security-oos-observations.md"
    oos_file = review_tmpdir / "oos.md"
    voting_tally_file = review_tmpdir / "voting-tally.md"
    tally_env = review_tmpdir / "review-tally.env"
    yield_tsv = review_tmpdir / "scout-archetype-yield.tsv"
    class_tsv = review_tmpdir / "findings-classification.tsv" if _nested_implement_round(review_tmpdir=review_tmpdir, session_env_path=args.session_env_path) else review_tmpdir / f"findings-classification-round-{args.round_num}.tsv"
    for path in (accepted_file, rejected_file, oos_accepted_file, oos_file, tally_env):
        _write(path=path, text="")
    oos_accepted_out = Path(args.session_env_path).parent / "oos-accepted-review.md" if args.session_env_path else oos_accepted_file
    if oos_accepted_out != oos_accepted_file:
        _write(path=oos_accepted_out, text="")
    try:
        blocks = _block_files(ballot_file=ballot_file, review_tmpdir=review_tmpdir)
    except RuntimeError:
        return _error("tally-code-votes: duplicate or malformed FINDING/OOS headings in ballot")
    _write(path=class_tsv, text=voting.code_review_classification_header() + "\n" if three_slot else _CLASSIFICATION_HEADER + "\n")
    not_substantive_count = int(args.not_substantive_count) if str(args.not_substantive_count).isdigit() else 0
    if not blocks:
        tally_lines = ["# Code Review Voting Tally\n\n", "Round skipped: no findings to adjudicate.\n\n"]
        if not_substantive_count > 0:
            tally_lines.append(f"{_not_substantive_warning(not_substantive_count)}\n\n")
        tally_lines.append(voting.render_voter_agreement_and_severity_scoreboards([]))
        _write(path=voting_tally_file, text="".join(tally_lines))
        _write_final_tally_outputs(
            tally_env=tally_env,
            counts_text="ACCEPTED_COUNT=0\nREJECTED_COUNT=0\nEXONERATED_COUNT=0\nNEUTRAL_COUNT=0\nOOS_ACCEPTED_COUNT=0\nOOS_REJECTED_COUNT=0\n",
            review_tmpdir=review_tmpdir,
            args=args,
            ledger_entries=[],
        )
        for key, value in {
            "TALLY_STATUS": "skipped-empty-findings",
            "ACCEPTED_COUNT": "0",
            "REJECTED_COUNT": "0",
            "EXONERATED_COUNT": "0",
            "NEUTRAL_COUNT": "0",
            "OOS_ACCEPTED_COUNT": "0",
            "OOS_REJECTED_COUNT": "0",
            "OUT_OF_SCOPE_DRIFT_COUNT": "0",
            "VOTING_TALLY_FILE": str(voting_tally_file),
            "TALLY_FILE": str(tally_env),
            "ACCEPTED_FINDINGS_FILE": str(accepted_file),
            "REJECTED_FINDINGS_FILE": str(rejected_file),
            "OOS_ACCEPTED_FILE": str(oos_accepted_out),
            "OOS_FILE": str(oos_file),
            "TALLY_OK": "true",
            "ELIGIBLE_VOTER_COUNT": "0",
            "VOTER_COUNT": "0",
            "PARSE_FAILED_COUNT": "0",
            "FINDINGS_CLASSIFICATION_TSV_FILE": str(class_tsv),
        }.items():
            logging_util.emit_kv(key=key, value=value)
        return 0
    eligible = 0
    effective_files: list[str] = []
    effective_slot = [False, False, False]
    parse_failed = 0
    if three_slot:
        for idx, voter_file in enumerate(args.voter_files):
            if voter_file and Path(voter_file).is_file() and Path(voter_file).stat().st_size > 0:
                eligible += 1
                if _parse_rate_ok(voter_file=voter_file, ballot_file=ballot_file, review_tmpdir=review_tmpdir, tool=args.voter_tools[idx], slot=str(idx)):
                    effective_slot[idx] = True
                    effective_files.append(voter_file)
                else:
                    parse_failed += 1
    else:
        eligible = 0 if args.both_down == "true" else len(args.voter_files)
        for voter_file in args.voter_files:
            tool = Path(voter_file).name.removesuffix("-vote-output.txt") if voter_file else "claude"
            if _parse_rate_ok(voter_file=voter_file, ballot_file=ballot_file, review_tmpdir=review_tmpdir, tool=tool):
                effective_files.append(voter_file)
            else:
                parse_failed += 1
    effective = max(0, eligible - parse_failed)
    accepted = rejected = exonerated = neutral = oos_accepted = oos_rejected = drift = 0
    if effective == 0:
        for block in blocks:
            try:
                reviewer = _proposer_for_item(
                    item_id=block.stem,
                    block=block,
                    map_file=proposer_map_file,
                    sidecar_required=proposer_sidecar_required
                )
            except voting.TallyError as exc:
                return _error(f"tally-code-votes: {exc}")
            empty_cells = [("", "", "", "", "", args.voter_tools[idx] if three_slot else None) for idx in range(3)] if three_slot else []
            text = _read(block)
            is_oos = block.stem.startswith("OOS_") or bool(re.search(r"\[(OUT_OF_SCOPE|OOS)\]", text.splitlines()[0] if text.splitlines() else ""))
            if not is_oos and _scope_drift(block=block, scope_files=args.scope_files, plan_file=args.plan_file):
                is_oos = True
            _append(path=class_tsv, text=_classification_row(item_id=block.stem, reviewer=reviewer, result="rejected", cells=empty_cells, three_slot=three_slot, is_oos=is_oos) + "\n")
        warning = "**⚠ Degraded code-review panel: 0 judges available. Panel tier: main-agent-required. Manual adjudication needed.**"
        zero_lines = ["# Code Review Voting Tally\n\n", f"{warning}\n\n"]
        if not_substantive_count > 0:
            zero_lines.append(f"{_not_substantive_warning(not_substantive_count)}\n\n")
        if parse_failed and eligible > 0:
            zero_lines.append(
                f"**⚠ Degraded code-review panel: {parse_failed} voter slot(s) emitted narrative-only output "
                "(parse-rate ≥80% JUDGE_ERROR) and were removed from the effective quorum.**\n\n"
            )
        zero_lines.append(voting.render_voter_agreement_and_severity_scoreboards([]))
        _write(path=voting_tally_file, text="".join(zero_lines))
        for key, value in {
            "TALLY_STATUS": "main-agent-vote-required",
            "ACCEPTED_COUNT": "0",
            "REJECTED_COUNT": "0",
            "EXONERATED_COUNT": "0",
            "NEUTRAL_COUNT": "0",
            "OOS_ACCEPTED_COUNT": "0",
            "OOS_REJECTED_COUNT": "0",
            "OUT_OF_SCOPE_DRIFT_COUNT": "0",
            "VOTING_TALLY_FILE": str(voting_tally_file),
            "TALLY_FILE": str(tally_env),
            "ACCEPTED_FINDINGS_FILE": str(accepted_file),
            "REJECTED_FINDINGS_FILE": str(rejected_file),
            "OOS_ACCEPTED_FILE": str(oos_accepted_out),
            "OOS_FILE": str(oos_file),
            "TALLY_OK": "true",
            "ELIGIBLE_VOTER_COUNT": str(eligible),
            "VOTER_COUNT": "0",
            "PARSE_FAILED_COUNT": str(parse_failed),
            "VOTING_SKIPPED_WARNING": warning,
            "FINDINGS_CLASSIFICATION_TSV_FILE": str(class_tsv),
        }.items():
            logging_util.emit_kv(key=key, value=value)
        return 0
    score_rows: list[tuple[str, str, str, int]] = []
    bonus_by_reviewer: defaultdict[str, float] = defaultdict(float)
    sole_finder_reward_count = 0
    agreement_rows: list[dict[str, object]] = []
    ledger_entries: list[dict[str, object]] = []
    tally_lines = ["# Code Review Voting Tally\n\n"]
    if three_slot:
        expected = 3 if (args.codex_available == "true" or args.cursor_available == "true") else 1
    else:
        expected = 1 + (1 if args.codex_available == "true" else 0) + (1 if args.cursor_available == "true" else 0)
    if effective < expected:
        tally_lines.append(f"**⚠ Degraded code-review panel: {effective} judge(s) available. Panel tier: {voting.panel_tier(effective)}.**\n\n")
    if parse_failed:
        tally_lines.append(f"**⚠ Degraded code-review panel: {parse_failed} voter slot(s) emitted narrative-only output (parse-rate ≥80% JUDGE_ERROR) and were removed from the effective quorum.**\n\n")
    if not_substantive_count > 0:
        tally_lines.append(f"{_not_substantive_warning(not_substantive_count)}\n\n")
    tally_lines.append("## Per-finding vote breakdown\n\n| Item | YES | NO | JERR | Result |\n|---|---:|---:|---:|---|\n")
    # Issue #4880: a finding whose per-item valid votes (yes+no) fall below the panel's majority
    # quorum was effectively decided by fewer voters than the panel size — flag it even when each
    # voter's JUDGE_ERROR rate stays under the slot-removal threshold (the silent 67%-per-voter case).
    quorum = effective // 2 + 1
    under_quorum_items: list[str] = []
    oos_seq = _seed_oos_seq(args.session_env_path)
    for block in blocks:
        item_id = block.stem
        yes = no = judge_error = 0
        cells: list[tuple[str, str, str, str, str, str | None]] = []
        if three_slot:
            for idx in range(3):
                tool = args.voter_tools[idx]
                if not effective_slot[idx]:
                    cells.append(("", "", "", "", "", tool))
                    continue
                vote, correctness, severity, quality, uncertain = voting.parse_judge_vote(voter_file=args.voter_files[idx], ballot_id=item_id)
                if not vote:
                    vote = "JUDGE_ERROR"
                cells.append((vote, correctness, severity, quality, uncertain, tool))
                if vote == "YES":
                    yes += 1
                elif vote == "NO":
                    no += 1
                else:
                    judge_error += 1
        else:
            for voter_file in effective_files:
                try:
                    vote, correctness, severity, quality, uncertain = voting.parse_judge_vote(voter_file=voter_file, ballot_id=item_id)
                except FileNotFoundError:
                    vote, correctness, severity, quality, uncertain = "JUDGE_ERROR", "", "", "", "true"
                if not vote:
                    vote = "JUDGE_ERROR"
                cells.append((vote, correctness, severity, quality, uncertain, None))
                if vote == "YES":
                    yes += 1
                elif vote == "NO":
                    no += 1
                else:
                    judge_error += 1
        result = voting.classify_result(yes=yes, no=no, exonerate=0, eligible=effective)
        text = _read(block)
        artifact_text = _artifact_text_for_item(item_id=item_id, block=block, map_file=proposer_map_file)
        is_oos = item_id.startswith("OOS_") or bool(re.search(r"\[(OUT_OF_SCOPE|OOS)\]", text.splitlines()[0] if text.splitlines() else ""))
        if not is_oos and _scope_drift(block=block, scope_files=args.scope_files, plan_file=args.plan_file):
            is_oos = True
            drift += 1
        if is_oos:
            result = voting.classify_oos_result(yes=yes, no=no, exonerate=0, eligible=effective)
        if effective >= _MIN_DEGRADABLE_PANEL and (yes + no) < quorum:
            under_quorum_items.append(item_id)
        voter_votes, voter_severities = _voter_votes_and_severities(
            cells,
            voter_tools=args.voter_tools,
            three_slot=three_slot,
        )
        vote_values = [vote for _label, vote in voter_votes]
        fileable_oos = voting.oos_fileable_from_votes(
            result,
            yes_votes=vote_values,
            severities=voter_severities,
        )
        neutral_rescued = voting.neutral_high_severity_rescue_to_oos(
            result,
            yes_votes=vote_values,
            severities=voter_severities,
        )
        agreement_row = voting.voter_agreement_row_from_panel(
            voting_result=result,
            voter_votes=voter_votes,
            panel="code-review",
            voter_severities=voter_severities,
        )
        if agreement_row is not None:
            agreement_rows.append(agreement_row)
        try:
            reviewer = _proposer_for_item(
                item_id=item_id,
                block=block,
                map_file=proposer_map_file,
                sidecar_required=proposer_sidecar_required
            )
        except voting.TallyError as exc:
            return _error(f"tally-code-votes: {exc}")
        tally_lines.append(f"| {item_id} | {yes} | {no} | {judge_error} | {result} |\n")
        _record_classification_and_ledger(
            class_tsv=class_tsv,
            classification_row=_classification_row(
                item_id=item_id,
                reviewer=reviewer,
                result=result,
                cells=cells,
                three_slot=three_slot,
                is_oos=is_oos or neutral_rescued,
            ),
            ledger_entries=ledger_entries,
            ledger_entry=_ledger_entry(
                item_id=item_id,
                block_text=text,
                outcome="oos" if is_oos or neutral_rescued else result,
                vote_tally=f"YES={yes}/{effective}"
            )
        )
        kind = "oos" if is_oos else "finding"
        score_result = "neutral" if kind == "oos" and result == "accepted" and not fileable_oos else result
        sole_finder_reward_count += _record_code_review_score_rows(
            score_state=(score_rows, bonus_by_reviewer, active_bonus),
            reviewer=reviewer,
            classification=(kind, score_result, neutral_rescued),
            cells=cells,
        )
        try:
            security = _security_block(block)
        except RuntimeError:
            return _error(f"tally-code-votes: security classifier failed for {item_id}")
        reroute_marker = _finding_oos_reroute_marker(block_text=text, neutral_rescued=neutral_rescued)
        if kind == "finding":
            if result == "accepted":
                _append(path=accepted_file, text=artifact_text + "\n")
                accepted += 1
                _record_tally(tally_file=tally_env, item_id=item_id, accepted=True, outcome="accepted")
            elif reroute_marker:
                _record_public_oos_artifact(
                    oos_file=oos_file,
                    pool_file=oos_accepted_out.parent / _OOS_AGGREGATE_POOL,
                    security_sidecar=security_oos_file,
                    artifact=artifact_text + f"\nVote tally: YES={yes} NO={no} JUDGE_ERROR={judge_error} Result={result} ({reroute_marker})\n\n",
                    security=security,
                    accepted=False,
                )
                oos_rejected += 1
                _record_tally(tally_file=tally_env, item_id=item_id, accepted=False, outcome="oos" if neutral_rescued else result)
            else:
                rejected += 1
                if result == "neutral":
                    neutral += 1
                subtype = "dismissed (0 YES)" if result == "rejected" else "neutral (YES below acceptance threshold)"
                _append(path=rejected_file, text=f"### [rejected] {item_id}\n\n**Rejected subtype:** {subtype}\n\n{artifact_text}\nVote tally: YES={yes} NO={no} JUDGE_ERROR={judge_error}\n\n")
                _record_tally(tally_file=tally_env, item_id=item_id, accepted=False, outcome=result)
        else:
            oos_fileable_marker = "true" if fileable_oos else "false"
            _record_public_oos_artifact(
                oos_file=oos_file,
                pool_file=oos_accepted_out.parent / _OOS_AGGREGATE_POOL,
                security_sidecar=security_oos_file,
                artifact=artifact_text + f"\nVote tally: YES={yes} NO={no} JUDGE_ERROR={judge_error} Result={result} Fileable={oos_fileable_marker}\n\n",
                security=security,
                accepted=fileable_oos,
            )
            if fileable_oos:
                if not security:
                    oos_seq += 1
                    normalized = _normalize_oos_header_text(text=artifact_text, seq=oos_seq)
                    _append(path=oos_accepted_file, text=normalized + "\n")
                    if oos_accepted_out != oos_accepted_file:
                        _append(path=oos_accepted_out, text=normalized + "\n")
                    oos_accepted += 1
                _record_tally(tally_file=tally_env, item_id=item_id, accepted=True, outcome="accepted")
            else:
                if result != "accepted":
                    oos_rejected += 1
                _record_tally(tally_file=tally_env, item_id=item_id, accepted=result == "accepted", outcome=result)
    if under_quorum_items:
        tally_lines.insert(
            1,
            f"**⚠ Degraded code-review panel: {len(under_quorum_items)} finding(s) decided below the "
            f"{quorum}-of-{effective} panel quorum because per-item JUDGE_ERROR dropped valid votes "
            f"below quorum ({', '.join(under_quorum_items)}). These items were resolved by the "
            "remaining voter(s) and may warrant manual review.**\n\n",
        )
    tally_lines.append("\n## Reviewer Competition Scoreboard\n\n")
    tally_lines.append("| Reviewer | Proposed | Accepted | Neutral | Rejected | OOS-Proposed | OOS-Accepted | OOS-Neutral | OOS-Rejected | Score | Status |\n")
    tally_lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|\n")
    stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for reviewer, kind, result, accepted_weight in score_rows:
        if kind == "finding":
            stats[reviewer]["proposed"] += 1
            stats[reviewer][result] += 1
            if result == "accepted":
                stats[reviewer]["accepted_weight"] += accepted_weight
        else:
            stats[reviewer]["oos_proposed"] += 1
            stats[reviewer][f"oos_{result}"] += 1
    for reviewer in sorted(stats):
        row = stats[reviewer]
        label = re.sub(r"(?:-output)?\.txt$", "", reviewer)
        score = (
            row["accepted_weight"]
            - (row["neutral"] * voting.NEUTRAL_FINDING_COST)
            + row["oos_accepted"]
            - row["rejected"]
            - row["oos_rejected"]
            + bonus_by_reviewer.get(reviewer, 0.0)
        )
        tally_lines.append(f"| {label} | {row['proposed']} | {row['accepted']} | {row['neutral']} | {row['rejected']} | {row['oos_proposed']} | {row['oos_accepted']} | {row['oos_neutral']} | {row['oos_rejected']} | {voting.format_score(score)} | STATUS=OK |\n")
    if args.manifest_file:
        _append_manifest_dead_rows(
            tally_lines,
            manifest_file=Path(args.manifest_file),
            collector_file=args.collector_results_file,
            score_rows=score_rows,
        )
    if active_bonus > 0 and sole_finder_reward_count:
        tally_lines.append("\n")
        tally_lines.append(voting.unique_finder_bonus_note(bonus=active_bonus, rewarded_count=sole_finder_reward_count))
        tally_lines.append("\n")
    tally_lines.append("\n")
    tally_lines.append(voting.render_voter_agreement_and_severity_scoreboards(agreement_rows))
    _write(path=voting_tally_file, text="".join(tally_lines))
    if args.manifest_file:
        archetype_map = _write_archetype_map(Path(args.manifest_file))
        for orphan in _write_yield_tsv(yield_path=yield_tsv, archetype_map=archetype_map, score_rows=score_rows):
            logging_util.emit_kv(key="WARN", value=f"yield TSV missing manifest entry for reviewer basename: {orphan}")
    _write_final_tally_outputs(
        tally_env=tally_env,
        counts_text=f"ACCEPTED_COUNT={accepted}\nREJECTED_COUNT={rejected}\nEXONERATED_COUNT={exonerated}\nNEUTRAL_COUNT={neutral}\nOOS_ACCEPTED_COUNT={oos_accepted}\nOOS_REJECTED_COUNT={oos_rejected}\n",
        review_tmpdir=review_tmpdir,
        args=args,
        ledger_entries=ledger_entries
    )
    for key, value in {
        "TALLY_STATUS": "ok",
        "ACCEPTED_COUNT": str(accepted),
        "REJECTED_COUNT": str(rejected),
        "EXONERATED_COUNT": str(exonerated),
        "NEUTRAL_COUNT": str(neutral),
        "OOS_ACCEPTED_COUNT": str(oos_accepted),
        "OOS_REJECTED_COUNT": str(oos_rejected),
        "OUT_OF_SCOPE_DRIFT_COUNT": str(drift),
        "VOTING_TALLY_FILE": str(voting_tally_file),
        "TALLY_FILE": str(tally_env),
        "ACCEPTED_FINDINGS_FILE": str(accepted_file),
        "REJECTED_FINDINGS_FILE": str(rejected_file),
        "OOS_ACCEPTED_FILE": str(oos_accepted_out),
        "OOS_FILE": str(oos_file),
        "TALLY_OK": "true",
        "ELIGIBLE_VOTER_COUNT": str(eligible),
        "VOTER_COUNT": str(effective),
        "UNDER_QUORUM_COUNT": str(len(under_quorum_items)),
        "UNDER_QUORUM_ITEMS": ", ".join(under_quorum_items),
        "PARSE_FAILED_COUNT": str(parse_failed),
        "FINDINGS_CLASSIFICATION_TSV_FILE": str(class_tsv),
    }.items():
        logging_util.emit_kv(key=key, value=value)
    if args.manifest_file:
        logging_util.emit_kv(key="YIELD_TSV_FILE", value=str(yield_tsv))
    return 0


def tally_code_votes_main(argv: list[str]) -> int:
    return tally_code_votes(argv)


def _parse_emit_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="emit-tally")
    parser.add_argument("--tally-file", required=True)
    parser.add_argument("--accepted-findings-file", required=True)
    parser.add_argument("--oos-file", required=True)
    parser.add_argument("--review-tmpdir", required=True)
    parser.add_argument("--session-env-path", default="")
    parser.add_argument("--round", default="1")
    parser.add_argument("--mode", required=True, choices=("diff", "description"))
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--scout-status", default="na")
    parser.add_argument("--dynamic-slots", default="0")
    parser.add_argument("--static-slot-count", default="0")
    return parser.parse_args(argv)


def _count_from_tally(*, tally: dict[str, str], key: str) -> int:
    value = tally.get(key, "")
    return int(value) if value.isdigit() else 0


def _fallback_counts_from_tally_text(text: str) -> tuple[int, int, int]:
    tally = _kv_parse(text)
    accepted = _count_from_tally(tally=tally, key="ACCEPTED_COUNT")
    rejected = _count_from_tally(tally=tally, key="REJECTED_COUNT")
    neutral = _count_from_tally(tally=tally, key="NEUTRAL_COUNT")
    if accepted == 0 and "ACCEPTED=true" in text:
        accepted = len(re.findall(r"(?m)^[A-Z_]+_[0-9]+_ACCEPTED=true$", text))
    if rejected == 0:
        if re.search(r"(?m)^[A-Z_]+_[0-9]+_REJECTED_SUBTYPE=", text) or "_OUTCOME=" in text:
            rejected = len(re.findall(r"(?m)^[A-Z_]+_[0-9]+_OUTCOME=rejected$", text))
        else:
            rejected = len(re.findall(r"(?m)^[A-Z_]+_[0-9]+_ACCEPTED=false$", text))
    if neutral == 0 and "NEUTRAL_COUNT" not in tally:
        neutral = 0
    return accepted, rejected, neutral


def _round_summary_counts_from_meta(review_tmpdir: Path) -> tuple[int, int, int] | None:
    meta_path = review_tmpdir / "round-meta.json"
    if not meta_path.is_file():
        return None
    try:
        parsed: object = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    parsed_dict = cast("dict[str, object]", parsed)
    tally = parsed_dict.get("tally")
    if not isinstance(tally, dict):
        return None
    raw_tally = cast("dict[object, object]", tally)
    tally_dict = {str(key): str(value) for key, value in raw_tally.items()}
    return (
        _count_from_tally(tally=tally_dict, key="ACCEPTED_COUNT"),
        _count_from_tally(tally=tally_dict, key="REJECTED_COUNT"),
        _count_from_tally(tally=tally_dict, key="NEUTRAL_COUNT"),
    )


def _round_summary_counts(
    *,
    review_tmpdir: Path,
    accepted: int,
    rejected: int,
    neutral: int,
) -> tuple[int, int, int]:
    meta_counts = _round_summary_counts_from_meta(review_tmpdir)
    if meta_counts is not None:
        return meta_counts
    try:
        from larch.report import progress_report  # noqa: PLC0415

        counts, source = progress_report._round_counts(review_tmpdir)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
    except Exception:  # pylint: disable=broad-except
        return accepted, rejected, neutral
    if not source:
        return accepted, rejected, neutral
    return counts[0], counts[1], counts[2]


def _compact_rejected_findings_from_tally(tally_text: str) -> str:
    compact = "# Rejected Findings\n\n"
    has_outcome_rows = "_OUTCOME=" in tally_text
    for idx, line in enumerate(tally_text.splitlines(), start=1):
        if line.endswith("_OUTCOME=rejected") or (not has_outcome_rows and line.endswith("_ACCEPTED=false")):
            compact += f"{idx}:{line}\n"
    return compact


def _review_round_summary_body(
    *,
    review_tmpdir: Path,
    round_value: str,
    mode: str,
    counts: tuple[int, int, int],
    accepted_file: Path,
) -> str:
    summary_accepted, summary_rejected, summary_neutral = _round_summary_counts(
        review_tmpdir=review_tmpdir,
        accepted=counts[0],
        rejected=counts[1],
        neutral=counts[2],
    )
    body = f"# Review Round {round_value}\n\n- Mode: `{mode}`\n- {summary_accepted} accepted, {summary_rejected} rejected ({summary_neutral} neutral)\n\n"
    if accepted_file.stat().st_size > 0:
        body += "## Accepted Findings\n\n" + _read(accepted_file)
    return body


def _non_security_oos_count(path: Path, *, review_tmpdir: Path) -> int:
    if not path.is_file() or path.stat().st_size == 0:
        return 0
    count = 0
    for block in re.split(r"(?m)^(?=### OOS_[0-9]+:)", _read(path)):
        if not block.startswith("### OOS_"):
            continue
        fd, tmp_name = tempfile.mkstemp(dir=review_tmpdir)
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            tmp.write_text(block, encoding="utf-8")
            if not voting.is_security_block(tmp):
                count += 1
        finally:
            with suppress(OSError):
                tmp.unlink()
    return count


def _emit_dest_dirs(*, session_env_path: str, implement_tmpdir: str) -> list[Path]:
    return ([Path(session_env_path).parent] if session_env_path else []) + (
        [Path(implement_tmpdir)] if implement_tmpdir and Path(implement_tmpdir).is_dir() else []
    )


def _finalize_emit_oos_filing(
    *,
    context: tuple[Path, str, str],
    artifacts: tuple[Path, Path, Path, Path],
) -> str:
    review_tmpdir, session_env_path, implement_tmpdir = context
    round_summary, review_summary, rejected_full, oos_accepted_file = artifacts
    aggregate_parent = _aggregate_parent(
        review_tmpdir=review_tmpdir,
        session_env_path=session_env_path,
        implement_tmpdir=implement_tmpdir,
    )
    _promote_aggregate_oos_pool(
        sink=oos_accepted_file,
        pool=aggregate_parent / _OOS_AGGREGATE_POOL,
        main_agent=aggregate_parent / "oos-accepted-main-agent.md",
    )
    _copy_emit_artifacts(
        dest_dirs=_emit_dest_dirs(session_env_path=session_env_path, implement_tmpdir=implement_tmpdir),
        round_summary=round_summary,
        review_summary=review_summary,
        rejected_full=rejected_full,
        oos_accepted_file=oos_accepted_file,
    )
    return str(_non_security_oos_count(oos_accepted_file, review_tmpdir=review_tmpdir))


def _copy_emit_artifacts(
    *,
    dest_dirs: list[Path],
    round_summary: Path,
    review_summary: Path,
    rejected_full: Path,
    oos_accepted_file: Path,
) -> None:
    for dest_dir in dest_dirs:
        for src, name in (
            (round_summary, "review-round-summary.md"),
            (review_summary, "review-summary.json"),
            (rejected_full, "rejected-findings-full.md"),
            (oos_accepted_file, "oos-accepted-review.md"),
        ):
            with suppress(OSError):
                shutil.copyfile(src, dest_dir / name)


def emit_tally(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="emit-tally")
    try:
        args = _parse_emit_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    tally_file = Path(args.tally_file)
    accepted_file = Path(args.accepted_findings_file)
    review_tmpdir = Path(args.review_tmpdir)
    if not tally_file.is_file():
        return _error("emit-tally: --tally-file must name a file")
    if not accepted_file.is_file():
        return _error("emit-tally: --accepted-findings-file must name a file")
    if not args.dynamic_slots.isdigit() or not args.static_slot_count.isdigit():
        return _error("emit-tally: --dynamic-slots and --static-slot-count must be non-negative integers")
    review_tmpdir.mkdir(parents=True, exist_ok=True)
    tally_text = _read(tally_file)
    tally = _kv_parse(tally_text)
    accepted = _count_from_tally(tally=tally, key="ACCEPTED_COUNT")
    rejected = _count_from_tally(tally=tally, key="REJECTED_COUNT")
    neutral = _count_from_tally(tally=tally, key="NEUTRAL_COUNT")
    if not tally.get("ACCEPTED_COUNT") or not tally.get("REJECTED_COUNT"):
        fb_accepted, fb_rejected, fb_neutral = _fallback_counts_from_tally_text(tally_text)
        if not tally.get("ACCEPTED_COUNT"):
            accepted = fb_accepted
        if not tally.get("REJECTED_COUNT"):
            rejected = fb_rejected
        if not tally.get("NEUTRAL_COUNT"):
            neutral = fb_neutral
    oos_accepted_count = _count_from_tally(tally=tally, key="OOS_ACCEPTED_COUNT")
    round_summary = review_tmpdir / "review-round-summary.md"
    review_summary = review_tmpdir / "review-summary.json"
    rejected_file = review_tmpdir / "rejected-findings.md"
    rejected_full = review_tmpdir / "rejected-findings-full.md"
    oos_accepted_file = review_tmpdir / "oos-accepted-review.md"
    body = _review_round_summary_body(
        review_tmpdir=review_tmpdir,
        round_value=str(args.round),
        mode=str(args.mode),
        counts=(accepted, rejected, neutral),
        accepted_file=accepted_file,
    )
    _write(path=round_summary, text=body)
    if rejected_file.is_file() and rejected_file.stat().st_size > 0:
        shutil.copyfile(rejected_file, rejected_full)
    else:
        _write(path=rejected_full, text="")
        _write(path=rejected_file, text=_compact_rejected_findings_from_tally(tally_text))
    reviewer_paths = sorted(str(path) for path in review_tmpdir.glob("*-output.txt"))
    _write(
        path=review_summary,
        text=json.dumps(
            {
                "schema_version": 3,
                "rounds_completed": int(args.round) if str(args.round).isdigit() else 1,
                "reviewer_output_paths": reviewer_paths,
                "panel": {
                    "scout_status": args.scout_status,
                    "static_slot_count": int(args.static_slot_count),
                    "dynamic_slot_count": int(args.dynamic_slots),
                    "total_slot_count": int(args.static_slot_count) + int(args.dynamic_slots),
                },
                "finding_counts": {
                    "total_accepted": accepted,
                    "total_rejected": rejected,
                    "total_neutral": neutral,
                    "total_exonerated": 0,
                },
                "accepted_count": accepted,
                "rejected_count": rejected,
                "neutral_count": neutral,
                "exonerated_count": 0,
            },
            sort_keys=True,
        )
        + "\n"
    )
    sink_has_content = oos_accepted_file.is_file() and oos_accepted_file.stat().st_size > 0
    sink_count = _non_security_oos_count(oos_accepted_file, review_tmpdir=review_tmpdir)
    if sink_has_content and sink_count >= oos_accepted_count:
        pass
    elif sink_has_content and sink_count < oos_accepted_count:
        print(f"emit-tally: OOS_ACCEPTED_COUNT={oos_accepted_count} but accepted sink has {sink_count} non-security block(s); refusing destructive rebuild", file=sys.stderr)
        return 1
    elif Path(args.oos_file).is_file():
        if oos_accepted_count > 0:
            proc = subprocess.run([sys.executable, str(_PLUGIN_ROOT / "python" / "cli.py"), "oos", "serialize", "--findings-file", args.oos_file, "--output-file", str(oos_accepted_file), *( ["--session-env-path", args.session_env_path] if args.session_env_path else [] )], text=True, capture_output=True, check=False)
            if proc.returncode != 0:
                print(proc.stderr, file=sys.stderr, end="")
                return proc.returncode
            rebuilt_count = _non_security_oos_count(oos_accepted_file, review_tmpdir=review_tmpdir)
            if rebuilt_count != oos_accepted_count:
                print(f"emit-tally: OOS_ACCEPTED_COUNT={oos_accepted_count} but rebuild produced {rebuilt_count} non-security block(s)", file=sys.stderr)
                return 1
    elif oos_accepted_count > 0:
        print("emit-tally: OOS_ACCEPTED_COUNT but oos.md is absent", file=sys.stderr)
        return 1
    else:
        _write(path=oos_accepted_file, text="")
    oos_filing_count = _finalize_emit_oos_filing(
        context=(review_tmpdir, args.session_env_path, args.implement_tmpdir),
        artifacts=(round_summary, review_summary, rejected_full, oos_accepted_file),
    )
    logging_util.emit_kv(key="EMIT_OK", value="true")
    logging_util.emit_kv(key="ROUND_SUMMARY_FILE", value=str(round_summary))
    logging_util.emit_kv(key="REVIEW_SUMMARY_FILE", value=str(review_summary))
    logging_util.emit_kv(key="OOS_FILING_COUNT", value=oos_filing_count)
    return 0


def emit_tally_main(argv: list[str]) -> int:
    return emit_tally(argv)


def _parse_log_phase_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="log-phase")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--action", required=True, choices=("write", "append"))
    parser.add_argument("--payload-file", required=True)
    parser.add_argument("--log-root", default=os.environ.get("LARCH_LOG_ROOT", ""))
    return parser.parse_args(argv)


def log_phase(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="log-phase")
    try:
        args = _parse_log_phase_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    if not Path(args.payload_file).is_file():
        return _error("log-phase: --payload-file must name a file")
    if not re.fullmatch(r"review-context|review-panel-manifest|review-findings|review-tally|review-scout-manifest|difficulty-rating|review-round-summary|panel-prompt-sizes|review-findings-classification-round-[1-5]", args.batch):
        return _error(f"log-phase: unregistered review batch: {args.batch}")
    base = [sys.executable, str(_PLUGIN_ROOT / "python" / "cli.py"), "run-log"]
    if args.action == "write":
        cmd = [*base, "write"]
        file_args = ["--input-file", args.payload_file]
    else:
        cmd = [*base, "append"]
        file_args = ["--record-file", args.payload_file]
    log_args = ["--skill", "review", f"--run-id={args.run_id}", "--batch", args.batch]
    if args.log_root:
        log_args = ["--log-root", args.log_root, *log_args]
    proc = subprocess.run([*cmd, *log_args, *file_args], text=True, capture_output=True, check=False)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    for line in proc.stdout.splitlines():
        logging_util.emit(line)
    if args.batch == "review-panel-manifest" and args.action == "write":
        sibling = Path(args.payload_file).with_name("panel-prompt-sizes.tsv")
        if sibling.is_file() and sibling.stat().st_size > 0:
            extra_log_args = ["--skill", "review", f"--run-id={args.run_id}", "--batch", "panel-prompt-sizes"]
            if args.log_root:
                extra_log_args = ["--log-root", args.log_root, *extra_log_args]
            # lint-subprocess-via-runner: ok sibling panel-prompt-sizes write mirrors the baselined run-log subprocess.run above in this function
            extra = subprocess.run([*base, "write", *extra_log_args, "--input-file", str(sibling)], text=True, capture_output=True, check=False)
            if extra.returncode != 0:
                print("log-phase: warning: failed to write sibling panel-prompt-sizes batch", file=sys.stderr)
                if extra.stderr:
                    print(extra.stderr, file=sys.stderr, end="")
    return proc.returncode


def log_phase_main(argv: list[str]) -> int:
    return log_phase(argv)
# pyright: reportUnusedFunction=false
