"""Voting, tally, parse-rate, and scoreboard helpers for larch."""
# ruff: noqa: E402, F401
# pylint: disable=unused-import
# pyright: reportPrivateUsage=false, reportUnusedImport=false

from __future__ import annotations

# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false

import hashlib
import math
import os
import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

from larch.review.review_types import (
    JudgeSeverity,
    ParsedBlock,
    ReviewVote,
    code_review_classification_header as _code_review_classification_header,
    is_security_block_text,
    parse_blocks,
)

LONG_EXTS = "cc|cfg|cjs|cpp|css|csv|cs|dart|gradle|groovy|go|html|htm|hpp|java|json|jsx|js|kt|lua|mjs|mk|mm|md|php|pl|proto|py|rb|rs|sass|scala|scss|sh|sql|swift|toml|tsx|tsv|ts|vue|xml|yaml|yml"
SHORT_EXTS = "lock|env|txt|c|h|m|r"
LONG_RE = rf"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*\.({LONG_EXTS})(:[0-9]+(-[0-9]+)?)?($|[^A-Za-z0-9_:/-])"
SHORT_PATH_RE = rf"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*[/_-][A-Za-z0-9_./-]*\.({SHORT_EXTS})(:[0-9]+(-[0-9]+)?)?($|[^A-Za-z0-9_:/-])"
SHORT_LINE_RE = rf"(^|[^A-Za-z0-9])\.?[A-Za-z_][A-Za-z0-9_./-]*\.({SHORT_EXTS}):[0-9]+(-[0-9]+)?($|[^A-Za-z0-9_:/-])"
EXTENSIONLESS_RE = r"(^|[^A-Za-z0-9_])(Makefile|Dockerfile|GNUmakefile)(:[0-9]+(-[0-9]+)?)?"
ANY_RE = f"{LONG_RE}|{SHORT_PATH_RE}|{SHORT_LINE_RE}"

FILE_LINE_REGEXES = {
    "long-re": LONG_RE,
    "short-path-re": SHORT_PATH_RE,
    "short-line-re": SHORT_LINE_RE,
    "extensionless-re": EXTENSIONLESS_RE,
    "any-re": ANY_RE,
    "long-exts": LONG_EXTS,
    "short-exts": SHORT_EXTS,
}


def ledger_title(*, block_text: str, item_id: str) -> str:
    """Extract a ledger title from one finding markdown block."""
    first = block_text.splitlines()[0] if block_text.splitlines() else ""
    title = re.sub(rf"^###\s+{re.escape(item_id)}:\s*", "", first).strip()
    return title or item_id


def ledger_file_line(block_text: str) -> str:
    """Extract the first normalized file/line reference from a finding."""
    for regex in FILE_LINE_REGEXES.values():
        match = re.search(regex, block_text)
        if match:
            return match.group(0).strip(" \t\n\r`*()[],:;")
    return ""


def ledger_reason(block_text: str) -> str:
    """Extract the first structured concern or suggested fix from a finding."""
    for line in block_text.splitlines()[1:]:
        normalized = line.replace("*", "").strip()
        if re.match(r"^[- ]*(Concern|Scenario|Reason|Suggested (revision|fix)):", normalized, re.IGNORECASE):
            return re.sub(r"^[- ]*[^:]+:\s*", "", normalized).strip()
    return ""

_ALLOWED_CODE_REVIEW_HEADERS = {
    "# Rejected Findings",
    "## Accepted Findings",
    "## Rejected Code Review Findings",
    "## Voting Tally",
    "# Code Review Voting Tally",
    "## Per-finding vote breakdown",
    "## Reviewer Competition Scoreboard",
    "## Voter Agreement Scoreboard",
    "## Voter Severity Scoreboard",
}

_CORRECTNESS_VALUES = {"true", "partially-true", "false-positive", "uncertain"}
SEVERITY_MAJOR = JudgeSeverity.major.value

_SEVERITY_VALUES = {severity.value for severity in JudgeSeverity}
HIGH_SEVERITIES = frozenset({JudgeSeverity.major.value})
NEUTRAL_FINDING_COST = 0.25
UNIQUE_FINDER_BONUS_ENV = "LARCH_UNIQUE_FINDER_BONUS"
_QUALITY_VALUES = {"excellent", "good", "adequate", "weak", "no-fix", "uncertain"}
_UNCERTAIN_VALUES = {"true", "false"}

FINDINGS_CLASSIFICATION_HEADER = (
    "finding_id\tfinding_reviewers\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tbody_severity\tscope"
)

CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER = _code_review_classification_header(
    include_tools=True, include_scope=True
)

# Re-exports from sibling module — preserves `voting.X` access for callers and tests.
from larch.review._voting_calibration import (
    ClassificationRowPrep,
    VoterAgreementTsvParse,
    VoterCalibrationDiscoveryRow,
    VoterCalibrationStat,
    _plugin_root,
    classification_row_panel_inputs,
    classification_tsv_schema_supported,
    compute_voter_agreement,
    compute_voter_severity_distribution,
    discover_voter_calibration_logs,
    normalize_voter_label_to_base_tool,
    read_voter_calibration_stats,
    render_voter_agreement_and_severity_scoreboards,
    render_voter_scoreboard,
    render_voter_severity_scoreboard,
    severity_calibration_score,
    valid_panel_severity,
    voter_agreement_row_from_panel,
    voter_agreement_rows_from_tsv,
    voter_calibration_snapshot_main,
    voter_calibration_stats_from_logs,
    write_voter_calibration_stats,
    _normalize_vote_cell,
    _resolve_voter_calibration_log_root,
    _resolve_voter_calibration_window,
)


BALLOT_HEADING_RE = re.compile(r"^### (FINDING_[0-9]+|OOS_[0-9]+):")
PROPOSER_MAP_ATTRIBUTED_HASH_PREFIX = "# attributed_ballot_sha256="
PROPOSER_MAP_NEUTRAL_HASH_PREFIX = "# neutral_ballot_sha256="
REVIEWER_ATTRIBUTION_RE = re.compile(
    r"^(?P<prefix>[\s-]*(?:\*\*Reviewer\(s\)\*\*|\*\*Reviewers?\*\*|Reviewer\(s\)|Reviewers?)\s*:\s*)"
    r"(?P<value>.*?)"
    r"(?P<trailing>[ \t]*)$"
)


class TallyError(ValueError):
    """Raised when tally attribution sidecars cannot score neutralized ballots."""


def findings_classification_header() -> str:
    return FINDINGS_CLASSIFICATION_HEADER


def code_review_classification_header() -> str:
    return CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER


def tokenize_finding_reviewers(*, cell: str, labels: Iterable[str]) -> list[str]:
    label_list = [label for label in labels if label]
    label_set = set(label_list)
    sorted_labels = sorted(label_set, key=lambda label: (-len(label), label))
    tokens: list[str] = []
    seen: set[str] = set()
    for raw_segment in cell.split(","):
        segment = raw_segment.strip()
        if not segment:
            continue
        if segment in label_set:
            if segment not in seen:
                tokens.append(segment)
                seen.add(segment)
            continue
        pos = 0
        while pos < len(segment):
            if segment[pos].isspace():
                pos += 1
                continue
            matched = ""
            for label in sorted_labels:
                if not segment.startswith(label, pos):
                    continue
                end = pos + len(label)
                if end < len(segment) and not segment[end].isspace():
                    continue
                matched = label
                break
            if not matched:
                break
            if matched not in seen:
                tokens.append(matched)
                seen.add(matched)
            pos += len(matched)
    return tokens


def grow_attribution_labels(  # lint-keyword-only: ok *cells vararg prevents bare *
    labels: list[str],
    seen: set[str],
    *cells: str,
) -> None:
    """Extend *labels* with reviewer tokens mined from attribution cells."""

    def add(label: str) -> None:
        clean = label.strip()
        if clean and clean not in seen:
            labels.append(clean)
            seen.add(clean)

    for cell in cells:
        for raw_segment in cell.split(","):
            segment = raw_segment.strip()
            if not segment:
                continue
            matched = tokenize_finding_reviewers(cell=segment, labels=labels)
            if matched:
                for token in matched:
                    add(token)
            elif " " not in segment and "\t" not in segment:
                add(segment)


def split_classification_attribution(
    reviewer_cell: str,
    *,
    column: str,
    labels: Iterable[str] | None = None,
) -> list[str]:
    cell = reviewer_cell.strip()
    if not cell:
        return []
    if column == "finding_reviewers":
        return tokenize_finding_reviewers(cell=cell, labels=labels or [])
    if column == "reviewer_slots":
        return [part.strip() for part in cell.split("|") if part.strip()]
    return [cell]


def strict_majority_yes_major(
    *,
    yes_votes: Iterable[str],
    severities: Iterable[str],
) -> bool:
    severity_values = list(severities)
    total_yes = 0
    major_yes = 0
    for idx, vote in enumerate(yes_votes):
        if vote.strip().upper() != ReviewVote.yes.value:
            continue
        total_yes += 1
        severity = severity_values[idx].strip().lower() if idx < len(severity_values) else ""
        if severity == JudgeSeverity.major.value:
            major_yes += 1
    return total_yes > 0 and major_yes > total_yes / 2


def accepted_finding_points_from_severities(
    severities: Iterable[str],
    *,
    votes: Iterable[str] | None = None,
) -> int:
    severity_values = list(severities)
    vote_values = list(votes) if votes is not None else [ReviewVote.yes.value] * len(severity_values)
    return 2 if strict_majority_yes_major(yes_votes=vote_values, severities=severity_values) else 1


def oos_fileable_from_votes(
    result: str,
    *,
    yes_votes: Iterable[str],
    severities: Iterable[str],
) -> bool:
    return result == "accepted" and strict_majority_yes_major(yes_votes=yes_votes, severities=severities)


def artifact_marked_fileable(block_text: str) -> bool:
    return bool(re.search(r"(?mi)^Vote tally:.*(?:^|[ \t])Fileable=true(?:[ \t]|$)", block_text))


def neutral_high_severity_rescue_to_oos(
    result: str,
    *,
    yes_votes: Iterable[str],
    severities: Iterable[str],
) -> bool:
    return result == "neutral" and strict_majority_yes_major(yes_votes=yes_votes, severities=severities)


def unique_finder_bonus_from_env(env: Mapping[str, str] | None = None) -> float:
    values = os.environ if env is None else env
    raw = (values.get(UNIQUE_FINDER_BONUS_ENV) or "").strip()
    if not raw:
        return 0.0
    try:
        value = float(raw)
    except ValueError:
        return 0.0
    if value <= 0 or not math.isfinite(value):
        return 0.0
    return value


def unique_finder_bonus_note(*, bonus: float, rewarded_count: int) -> str:
    return (
        f"**Unique finder bonus active:** {rewarded_count} accepted in-scope "
        f"sole-finder finding(s) received +{format_score(bonus)} each."
    )


def accepted_points_from_classification_row(
    *,
    cols: dict[str, str],
    header: list[str],
    labels: Iterable[str] | None = None,
) -> int:
    del labels
    if cols.get("voting_result", "").strip() != "accepted":
        return 0
    if "scope" not in header:
        return 1
    if cols.get("scope", "").strip() == "oos":
        return 1
    votes = [cols.get(f"v{idx}_vote", "") for idx in range(1, 4)]
    severities = [cols.get(f"v{idx}_severity", "") for idx in range(1, 4)]
    return accepted_finding_points_from_severities(severities, votes=votes)


_MD_TABLE_VOTE_ID_RE = re.compile(r"^(?:FINDING|OOS)_[0-9]+$")
_BALLOT_ID_ALIAS_RE = re.compile(r"^(FINDING|OOS)_([0-9]+)$")
_MD_TABLE_VOTE_RE = re.compile(r"^(YES|NO|EXONERATE)\b", re.IGNORECASE)


def _strip_md_markers(cell: str) -> str:
    return cell.replace("*", "").replace("`", "").strip()


def _split_table_axis_and_reason(cells: list[str]) -> tuple[list[str], list[str]]:
    axis_parts: list[str] = []
    reason_parts: list[str] = []
    for cell in (_strip_md_markers(c) for c in cells):
        if not cell:
            continue
        for part in re.split(r"[\s]+", cell.strip()):
            if part.startswith(("CORRECTNESS=", "SEVERITY=", "QUALITY=", "UNCERTAIN=")):
                axis_parts.append(part)
            elif part:
                reason_parts.append(part)
    return axis_parts, reason_parts


def _normalize_markdown_table_votes(text: str) -> str:
    """Rewrite markdown-table vote rows into anchored ``FINDING_N: VOTE`` lines.

    Some voters emit votes as a markdown table (``| FINDING_1 | **YES** | reason |``)
    instead of the required anchored grammar. The anchored parsers below only
    match lines that start with ``<id>:``; a table row would otherwise count as
    JUDGE_ERROR and drop the voter from quorum (issue #5078). Recognizable table
    vote rows are converted in place; every other line passes through unchanged.
    """
    if "|" not in text:
        return text
    out: list[str] = []
    for line in text.splitlines():
        rewritten = line
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) >= 2:  # noqa: PLR2004
                ballot_id = _strip_md_markers(cells[0]).upper()
                vote_match = _MD_TABLE_VOTE_RE.match(_strip_md_markers(cells[1]))
                if _MD_TABLE_VOTE_ID_RE.match(ballot_id) and vote_match:
                    axis_parts, reason_parts = _split_table_axis_and_reason(cells[2:])
                    vote_line = f"{ballot_id}: {vote_match.group(1).upper()}"
                    if axis_parts:
                        vote_line += " " + " ".join(axis_parts)
                    if reason_parts:
                        vote_line += " -- " + " ".join(reason_parts)
                    rewritten = vote_line
        out.append(rewritten)
    return "\n".join(out)


def alias_ballot_id(ballot_id: str, ballot_id_set: Iterable[str]) -> str:
    ballot_ids = set(ballot_id_set)
    if ballot_id not in ballot_ids:
        return ""
    match = _BALLOT_ID_ALIAS_RE.fullmatch(ballot_id)
    if not match:
        return ""
    prefix, number = match.groups()
    alias_prefix = "OOS" if prefix == "FINDING" else "FINDING"
    alias_id = f"{alias_prefix}_{number}"
    return "" if alias_id in ballot_ids else alias_id


def _vote_for_id_from_lines(*, ballot_id: str, lines: Iterable[str]) -> str:
    result = "JUDGE_ERROR"
    pattern = re.compile(rf"^{re.escape(ballot_id)}:\s*(YES|NO|EXONERATE)(?:[\s-]|$)", re.IGNORECASE)
    for line in lines:
        match = pattern.search(line)
        if match:
            token = match.group(1).upper()
            result = "NO" if token == "EXONERATE" else token
    return result


def vote_for_id_text(*, ballot_id: str, text: str, alias_id: str = "") -> str:
    """Return one normalized vote from already-read voter output text."""
    lines = _normalize_markdown_table_votes(text).splitlines()
    result = _vote_for_id_from_lines(ballot_id=ballot_id, lines=lines)
    if result != "JUDGE_ERROR" or not alias_id:
        return result
    return _vote_for_id_from_lines(ballot_id=alias_id, lines=lines)


def vote_for_id(*, ballot_id: str, voter_file: str | Path, alias_id: str = "") -> str:
    try:
        raw = Path(voter_file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "JUDGE_ERROR"
    return vote_for_id_text(ballot_id=ballot_id, text=raw, alias_id=alias_id)


def reviewer_for_block(block_file: str | Path) -> str:
    try:
        lines = Path(block_file).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "unknown"
    for line in lines:
        match = REVIEWER_ATTRIBUTION_RE.match(line)
        if match:
            value = _normalize_reviewer_value(match.group("value"))
            return value or "unknown"
    return "unknown"


def _normalize_reviewer_value(value: str) -> str:
    return value.replace("*", "").strip()


def normalize_reviewer_basename(value: str) -> str:
    """Reduce a reviewer output path to its basename with waterfall/retry
    suffixes removed so manifest phase-1 paths match collector files.

    Strips a trailing ``.txt`` (re-appended to the result) and any chained
    ``-phase2`` / ``-phase3`` / ``-retry`` suffixes accreted by the reviewer
    waterfall.
    """
    base = Path(value).name
    if base.endswith(".txt"):
        stem, ext = base[:-4], ".txt"
    else:
        stem, ext = base, ""
    while True:
        for suffix in ("-phase2", "-phase3", "-retry"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        else:
            break
    return stem + ext


def _safe_tsv_cell(value: str) -> str:
    return re.sub(r"[\t\r\n]+", " ", value).strip()


def _parsed_ballot_blocks(text: str) -> list[ParsedBlock]:
    """Parse ballot items with the shared canonical reviewer-item grammar."""
    return parse_blocks(text, boundary="item-heading")


def _ballot_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    for parsed in _parsed_ballot_blocks(text):
        if parsed.item_id in blocks:
            raise ValueError(f"duplicate ballot heading {parsed.item_id}")
        blocks[parsed.item_id] = parsed.block
    return blocks


def neutralize_reviewer_attribution(*, text: str, token: str = "anonymous") -> str:  # noqa: S107
    def neutralize_block(block: str) -> str:
        lines: list[str] = []
        attribution_done = False
        for raw in block.splitlines(keepends=True):
            line = raw.removesuffix("\n")
            newline = "\n" if raw.endswith("\n") else ""
            match = REVIEWER_ATTRIBUTION_RE.match(line)
            if match and not attribution_done:
                lines.append(f"{match.group('prefix')}{token}{match.group('trailing')}{newline}")
                attribution_done = True
            else:
                lines.append(raw)
        return "".join(lines)

    output: list[str] = []
    cursor = 0
    for parsed in _parsed_ballot_blocks(text):
        output.append(text[cursor : parsed.start])
        output.append(neutralize_block(parsed.block))
        cursor = parsed.end
    output.append(text[cursor:])
    return "".join(output)


def _ballot_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _usable_proposer_value(value: str) -> str:
    normalized = _normalize_reviewer_value(value)
    if not normalized or _is_neutral_reviewer(normalized):
        return ""
    return normalized


def proposer_map_from_ballot(text: str) -> dict[str, tuple[str, str]]:
    proposer_map: dict[str, tuple[str, str]] = {}
    for item_id, block in _ballot_blocks(text).items():
        for line in block.splitlines():
            match = REVIEWER_ATTRIBUTION_RE.match(line)
            if match:
                reviewer = _usable_proposer_value(match.group("value"))
                if not reviewer:
                    raise ValueError(f"ballot item {item_id} has missing or neutral reviewer attribution")
                proposer_map[item_id] = (reviewer, line)
                break
    return proposer_map


def validate_proposer_map_coverage(
    *, ballot_text: str,
    proposer_map: dict[str, tuple[str, str]],
) -> None:
    missing = [item_id for item_id in _ballot_blocks(ballot_text) if item_id not in proposer_map]
    if missing:
        raise ValueError(f"proposer map missing item(s): {', '.join(missing)}")


def write_proposer_map(*, ballot_file: Path, map_file: Path) -> None:
    text = ballot_file.read_text(encoding="utf-8", errors="replace")
    if ballot_text_is_neutralized(text):
        raise ValueError("cannot write proposer map from neutralized ballot")
    proposer_map = proposer_map_from_ballot(text)
    validate_proposer_map_coverage(ballot_text=text, proposer_map=proposer_map)
    map_file.parent.mkdir(parents=True, exist_ok=True)
    attributed_hash = _ballot_sha256(text)
    neutral_hash = _ballot_sha256(neutralize_reviewer_attribution(text=text))
    lines = [
        f"{PROPOSER_MAP_ATTRIBUTED_HASH_PREFIX}{attributed_hash}\n",
        f"{PROPOSER_MAP_NEUTRAL_HASH_PREFIX}{neutral_hash}\n",
        "item_id\treviewer\treviewer_line\n",
    ]
    for item_id in _ballot_blocks(text):
        reviewer, reviewer_line = proposer_map[item_id]
        lines.append(f"{item_id}\t{_safe_tsv_cell(reviewer)}\t{_safe_tsv_cell(reviewer_line)}\n")
    tmp = map_file.with_name(f"{map_file.name}.{os.getpid()}.tmp")
    _ = tmp.write_text("".join(lines), encoding="utf-8")
    _ = tmp.replace(map_file)


def read_proposer_map(map_file: str | Path) -> dict[str, tuple[str, str]]:
    path = Path(map_file)
    if not path.is_file():
        return {}
    proposer_map: dict[str, tuple[str, str]] = {}
    try:
        rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    for row in rows[1:] if rows and rows[0].split("\t")[:3] == ["item_id", "reviewer", "reviewer_line"] else rows:
        parts = row.split("\t")
        if len(parts) != 3:  # noqa: PLR2004
            continue
        item_id, reviewer, reviewer_line = (part.strip() for part in parts)
        if not BALLOT_HEADING_RE.match(f"### {item_id}:") or not reviewer or not reviewer_line:
            continue
        proposer_map[item_id] = (reviewer, reviewer_line)
    return proposer_map


def _is_neutral_reviewer(value: str) -> bool:
    return value.strip().lower() == "anonymous"


def ballot_text_is_neutralized(text: str) -> bool:
    for parsed in _parsed_ballot_blocks(text):
        for line in parsed.block.splitlines():
            match = REVIEWER_ATTRIBUTION_RE.match(line)
            if match:
                value = match.group("value").replace("*", "").strip().lower()
                return value == "anonymous"
    return False


def ballot_is_neutralized(ballot_file: str | Path) -> bool:
    try:
        text = Path(ballot_file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return ballot_text_is_neutralized(text)


def _proposer_map_hashes(rows: list[str]) -> tuple[str, str]:
    attributed_hash = ""
    neutral_hash = ""
    for row in rows:
        if row.startswith(PROPOSER_MAP_ATTRIBUTED_HASH_PREFIX):
            attributed_hash = row.removeprefix(PROPOSER_MAP_ATTRIBUTED_HASH_PREFIX).strip()
        elif row.startswith(PROPOSER_MAP_NEUTRAL_HASH_PREFIX):
            neutral_hash = row.removeprefix(PROPOSER_MAP_NEUTRAL_HASH_PREFIX).strip()
    return attributed_hash, neutral_hash


def validate_proposer_map_for_neutralized_ballot(*, ballot_file: str | Path, map_file: str | Path) -> None:
    ballot_path = Path(ballot_file)
    map_path = Path(map_file)
    if not map_path.is_file():
        raise TallyError(f"proposer map file missing: {map_file}")
    try:
        ballot_text = ballot_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise TallyError(f"ballot file unreadable: {ballot_file}") from exc
    try:
        rows = map_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise TallyError(f"proposer map unreadable: {map_file}") from exc
    _, neutral_hash = _proposer_map_hashes(rows)
    if not neutral_hash:
        raise TallyError("proposer map missing neutral_ballot_sha256 stamp")
    if _ballot_sha256(ballot_text) != neutral_hash:
        raise TallyError("proposer map stale for current ballot")
    proposer_map = read_proposer_map(map_file)
    ballot_ids = set(_ballot_blocks(ballot_text))
    map_ids = set(proposer_map)
    if ballot_ids != map_ids:
        missing = sorted(ballot_ids - map_ids)
        extra = sorted(map_ids - ballot_ids)
        details: list[str] = []
        if missing:
            details.append(f"missing item(s): {', '.join(missing)}")
        if extra:
            details.append(f"extra item(s): {', '.join(extra)}")
        raise TallyError(f"proposer map item mismatch ({'; '.join(details)})")
    for item_id, (reviewer, _) in proposer_map.items():
        if not _usable_proposer_value(reviewer):
            raise TallyError(f"proposer map has neutral or empty reviewer for {item_id}")


def proposer_for_item(
    *,
    item_id: str,
    block_file: str | Path,
    map_file: str | Path = "",
    sidecar_required: bool = False,
) -> str:
    reviewer = reviewer_for_block(block_file)
    if not _is_neutral_reviewer(reviewer):
        return reviewer
    sidecar_present = bool(map_file) and Path(map_file).is_file()
    if sidecar_present or sidecar_required:
        row = read_proposer_map(map_file).get(item_id) if map_file else None
        if row and _usable_proposer_value(row[0]):
            return row[0]
        raise TallyError(f"missing proposer map entry for neutralized item {item_id}")
    return reviewer


def reviewer_line_for_item(*, item_id: str, map_file: str | Path = "") -> str:
    if not map_file:
        return ""
    row = read_proposer_map(map_file).get(item_id)
    return row[1] if row else ""


def restore_reviewer_attribution(*, block_text: str, reviewer_line: str) -> str:
    if not reviewer_line:
        return block_text
    lines = block_text.splitlines(keepends=True)
    for idx, raw in enumerate(lines):
        line = raw.removesuffix("\n")
        newline = "\n" if raw.endswith("\n") else ""
        match = REVIEWER_ATTRIBUTION_RE.match(line)
        if match:
            if _is_neutral_reviewer(_normalize_reviewer_value(match.group("value"))):
                lines[idx] = reviewer_line + newline
            return "".join(lines)
    parsed = _parsed_ballot_blocks(block_text)
    if parsed:
        first = parsed[0]
        heading_end = block_text.find("\n", first.start)
        if heading_end >= 0:
            return block_text[: heading_end + 1] + reviewer_line + "\n" + block_text[heading_end + 1 :]
        return block_text + "\n" + reviewer_line + "\n"
    return reviewer_line + "\n" + block_text


def is_security_block(block_file: str | Path) -> bool:
    try:
        text = Path(block_file).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"is_security_block: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    return is_security_block_text(text)


def accept_finding(*, yes: int, no: int, exonerate: int, eligible: int) -> bool:
    _ = no, exonerate
    if eligible <= 0:
        return False
    if eligible == 1:
        return yes == 1
    if eligible == 2:  # noqa: PLR2004
        return yes == 2  # noqa: PLR2004
    return yes >= 2  # noqa: PLR2004



def accept_oos(*, yes: int, no: int, exonerate: int, eligible: int) -> bool:
    _ = no, exonerate
    if eligible <= 0:
        return False
    if eligible == 1:
        return yes == 1
    if eligible == 2:  # noqa: PLR2004
        return yes >= 1
    return yes >= 2  # noqa: PLR2004


def classify_oos_result(*, yes: int, no: int, exonerate: int, eligible: int) -> str:
    if eligible <= 0:
        return "rejected"
    if accept_oos(yes=yes, no=no, exonerate=exonerate, eligible=eligible):
        return "accepted"
    if yes > 0:
        return "neutral"
    return "rejected"

def classify_result(*, yes: int, no: int, exonerate: int, eligible: int) -> str:
    if eligible <= 0:
        return "rejected"
    if accept_finding(yes=yes, no=no, exonerate=exonerate, eligible=eligible):
        return "accepted"
    if yes > 0:
        return "neutral"
    return "rejected"


def panel_tier(eligible: int) -> str:
    if eligible >= 3:  # noqa: PLR2004
        return "full-3"
    if eligible == 2:  # noqa: PLR2004
        return "unanimous-2"
    if eligible == 1:
        return "single-judge"
    return "main-agent-required"


def split_ballot(*, ballot_file: str | Path, out_dir: str | Path) -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    text = Path(ballot_file).read_text(encoding="utf-8", errors="replace")
    try:
        blocks = _ballot_blocks(text)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    for item_id, block in blocks.items():
        (out_path / f"{item_id}.md").write_text(block, encoding="utf-8")


def _parse_judge_vote_from_lines(*, ballot_id: str, lines: Iterable[str]) -> tuple[str, str, str, str, str]:
    vote = correctness = severity = quality = uncertain_token = ""
    pattern = re.compile(rf"^{re.escape(ballot_id)}:\s*", re.IGNORECASE)
    for raw in lines:
        if not pattern.search(raw):
            continue
        vote = correctness = severity = quality = uncertain_token = ""
        scoped = pattern.sub("", raw, count=1)
        scoped = scoped.split(" -- ", 1)[0]
        match = re.match(r"^(YES|NO|EXONERATE)(?:[\s-]|$)", scoped, flags=re.IGNORECASE)
        if match:
            token = match.group(1).upper()
            vote = "NO" if token == "EXONERATE" else token
        for part in re.split(r"[\s]+", scoped.strip()):
            if part.startswith("CORRECTNESS="):
                value = part.removeprefix("CORRECTNESS=")
                correctness = value if value in _CORRECTNESS_VALUES else ""
            elif part.startswith("SEVERITY="):
                value = part.removeprefix("SEVERITY=")
                severity = value if value in _SEVERITY_VALUES else ""
            elif part.startswith("QUALITY="):
                value = part.removeprefix("QUALITY=")
                quality = value if value in _QUALITY_VALUES else ""
            elif part.startswith("UNCERTAIN="):
                value = part.removeprefix("UNCERTAIN=")
                uncertain_token = value if value in _UNCERTAIN_VALUES else ""
    uncertain = "true"
    if correctness and severity and quality and uncertain_token:
        uncertain = uncertain_token
    return vote, correctness, severity, quality, uncertain


def parse_judge_vote(*, voter_file: str | Path, ballot_id: str, alias_id: str = "") -> tuple[str, str, str, str, str]:
    try:
        raw_text = Path(voter_file).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise FileNotFoundError(str(exc)) from exc
    lines = _normalize_markdown_table_votes(raw_text).splitlines()
    parsed = _parse_judge_vote_from_lines(ballot_id=ballot_id, lines=lines)
    if parsed[0] or not alias_id:
        return parsed
    return _parse_judge_vote_from_lines(ballot_id=alias_id, lines=lines)


def ballot_parse(ballot_file: str | Path) -> list[str]:
    lines = Path(ballot_file).read_text(encoding="utf-8", errors="replace").splitlines()
    output: list[str] = []
    idx = 0
    title = concern = ""
    oos = "false"

    def emit() -> None:
        if idx > 0:
            output.append(f"FINDING_{idx}_TITLE={title}")
            output.append(f"FINDING_{idx}_CONCERN={concern.strip()}")
            output.append(f"FINDING_{idx}_OOS={oos}")

    for line in lines:
        match = re.match(r"^### FINDING_[0-9]+:\s*(.*)", line)
        if match:
            emit()
            idx += 1
            title = match.group(1)
            concern = ""
            oos = "true" if re.match(r"^\[(OUT_OF_SCOPE|OOS)\]", title) else "false"
            continue
        if idx > 0:
            if line.startswith("- **Concern**:"):
                concern = re.sub(r"^- \*\*Concern\*\*:\s*", "", line)
            elif concern and not line.startswith("- **"):
                concern += " " + line
            if "[OUT_OF_SCOPE]" in line or "[OOS]" in line:
                oos = "true"
    emit()
    output.append(f"FINDING_COUNT={idx}")
    return output


def format_score(score: float) -> str:
    value = float(score)
    if value.is_integer():
        return str(int(value))
    return f"{value:g}"


def _classification_row_is_oos(*, row: dict[str, str], header: list[str]) -> bool:
    if "scope" in header:
        return (row.get("scope") or "").strip().lower() == "oos"
    return (row.get("finding_id") or "").strip().startswith("OOS_")


def classification_row_is_oos(row: dict[str, str], *, header: list[str]) -> bool:
    """Public wrapper for header-aware classification OOS routing."""
    return _classification_row_is_oos(row=row, header=header)
