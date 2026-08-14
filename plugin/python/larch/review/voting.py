"""Voting, tally, parse-rate, and scoreboard helpers for larch."""
# ruff: noqa: E402, F401
# pylint: disable=unused-import
# pyright: reportPrivateUsage=false, reportUnusedImport=false

from __future__ import annotations

# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from typing import NoReturn

from larch import io as larch_io
from larch.core import logging_util
from larch.core import proc
from larch.core import redact
from larch.core.repo_roots import larch_entrypoint
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


def _finding_reviewers_segment_fully_tokenized(*, segment: str, labels: Iterable[str]) -> bool:
    label_set = {label for label in labels if label}
    if not label_set:
        return False
    sorted_labels = sorted(label_set, key=lambda label: (-len(label), label))
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
            return False
        pos += len(matched)
    return True


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


def raw_sole_finder_attribution(
    reviewer_cell: str,
    *,
    column: str,
    corpus_labels: Iterable[str],
) -> list[str]:
    """Return raw attribution tokens for sole-finder bonus eligibility."""
    cell = reviewer_cell.strip()
    if not cell:
        return []
    if column != "finding_reviewers":
        return split_classification_attribution(cell, column=column)
    comma_parts = [part.strip() for part in cell.split(",") if part.strip()]
    if len(comma_parts) > 1:
        return []
    if not comma_parts:
        return []
    segment = comma_parts[0]
    tokens = tokenize_finding_reviewers(cell=segment, labels=corpus_labels)
    if tokens:
        if _finding_reviewers_segment_fully_tokenized(segment=segment, labels=corpus_labels):
            return tokens
        return []
    return comma_parts


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


def _larch_argv(plugin_root: str = "") -> list[str]:
    """Return the verified-bootstrap prefix for a Rust-owned command."""
    return [str(larch_entrypoint(plugin_root or None))]


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


def _plain_diagnostic(message: str) -> None:
    line = redact.redact_outbound(logging_util.sanitize_diagnostic_line(message)).rstrip("\n") + "\n"
    if (
        _truthy("LARCH_QUIET_ACTIVE")
        and os.environ.get("LARCH_QUIET_PID")
        and not _truthy("LARCH_QUIET_DISABLE")
    ):
        try:
            os.write(4, line.encode("utf-8"))
            return
        except OSError:
            pass
    _ = sys.stderr.write(line)
    sys.stderr.flush()


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def _die(message: str) -> NoReturn:
    print(f"ERROR={message}", file=sys.stderr)
    raise SystemExit(2)


def _require_non_negative(*, name: str, value: str) -> int:
    if not value.isdigit():
        _die(f"{name} must be a non-negative integer: {value}")
    return int(value)


def _parse_kv(*, output: str, key: str) -> str:
    return larch_io.kv_value(text=output, key=key, default="")


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


def effective_judges(records: Iterable[str]) -> int:
    count = 0
    for record in records:
        if not record:
            continue
        parts = record.split("\t")
        status = parts[0] if len(parts) > 0 else ""
        path = parts[1] if len(parts) > 1 else ""
        parse_rate_status = parts[2] if len(parts) > 2 else ""  # noqa: PLR2004
        if status != "failed" and parse_rate_status != "NOT_SUBSTANTIVE" and path and Path(path).is_file() and Path(path).stat().st_size > 0:
            count += 1
    return count


def effective_judges_main(argv: list[str]) -> int:
    records = argv or sys.stdin.read().splitlines()
    print(effective_judges(records))
    return 0


def degraded_warning_main(argv: list[str]) -> int:
    if len(argv) not in {2, 3}:
        return _error("usage: degraded-warning <effective> <expected> [reason]")
    effective = int(argv[0])
    expected = int(argv[1])
    reason = argv[2] if len(argv) == 3 else ""  # noqa: PLR2004
    if effective < expected:
        warn_msg = f"**⚠ Degraded plan-review panel: {effective}/{expected} effective judges produced substantive vote output.**"
        if reason:
            warn_msg += f" {reason}"
        _plain_diagnostic(warn_msg)
        print(f"DEGRADED_PANEL_WARNING={warn_msg}")
    return 0


def build_voter_status_rows(
    *,
    voters: Sequence[tuple[str, str, str, str]],
    voter_paths_file: str,
    row_layout: str,
    paths_file_policy: str,
) -> list[tuple[str, str]]:
    """Build voter status rows in one of the two established wire orders."""
    if len(voters) != 3:  # noqa: PLR2004
        raise ValueError("exactly three voter records are required")
    if row_layout not in {"code_review_sequential", "plan_review_interleaved"}:
        raise ValueError(f"unknown voter row layout: {row_layout}")
    if paths_file_policy not in {"always", "nonempty"}:
        raise ValueError(f"unknown voter paths-file policy: {paths_file_policy}")
    suffixes = ("PATH", "TOOL", "STATUS", "PARSE_RATE_STATUS")
    sequential_order = tuple((voter, field) for voter in range(3) for field in range(4))
    interleaved_order = ((0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (2, 0), (1, 1), (2, 1), (1, 2), (2, 2), (1, 3), (2, 3))
    order = sequential_order if row_layout == "code_review_sequential" else interleaved_order
    rows = [(f"VOTER_{voter + 1}_{suffixes[field]}", voters[voter][field]) for voter, field in order]
    paths_file_index = len(rows) if row_layout == "code_review_sequential" else 6
    paths_file_present = paths_file_policy == "always" or (
        bool(voter_paths_file) and Path(voter_paths_file).is_file() and Path(voter_paths_file).stat().st_size > 0
    )
    if paths_file_present:
        rows.insert(paths_file_index, ("VOTER_PATHS_FILE", voter_paths_file))
    return rows


def voter_status_block_main(argv: list[str]) -> int:
    if len(argv) != 13:  # noqa: PLR2004
        return _error("usage: voter-status-block <13 positional args>")
    rows = build_voter_status_rows(
        voters=(tuple(argv[0:4]), tuple(argv[4:8]), tuple(argv[8:12])),  # type: ignore[arg-type]  # argv slices are exactly 4-wide, matching the fixed-arity voter tuple
        voter_paths_file=argv[12],
        row_layout="plan_review_interleaved",
        paths_file_policy="nonempty",
    )
    for key, value in rows:
        print(f"{key}={value}")
    return 0


def _compose_args(argv: list[str], *, require_log: bool = False) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    if require_log:
        parser.add_argument("--log-root", required=True)
        parser.add_argument("--skill", required=True)
        parser.add_argument("--run-id", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--rounds", default="0")
    parser.add_argument("--accepted", default="0")
    parser.add_argument("--rejected", default="0")
    parser.add_argument("--exonerated", default="0")
    parser.add_argument("--neutral", default="0")
    parser.add_argument("--body-file", default="")
    return parser.parse_args(argv)


def _validate_tally_args(args: argparse.Namespace) -> tuple[str, int, int, int, int]:
    if args.phase == "plan-review":
        batch = "plan-review-tally"
        allowed_modes = {"simple", "hard"}
        if not args.body_file:
            _die("--body-file is required for --phase plan-review")
    elif args.phase == "code-review":
        batch = "code-review-tally"
        allowed_modes = {"simple", "hard", "self-review"}
    else:
        _die(f"--phase must be plan-review or code-review: {args.phase}")
    if args.mode not in allowed_modes:
        _die(f"--mode must be one of {', '.join(sorted(allowed_modes))} for --phase {args.phase}: {args.mode}")
    rounds = _require_non_negative(name="--rounds", value=args.rounds)
    accepted = _require_non_negative(name="--accepted", value=args.accepted)
    rejected = _require_non_negative(name="--rejected", value=args.rejected)
    exonerated = _require_non_negative(name="--exonerated", value=args.exonerated)
    _require_non_negative(name="--neutral", value=args.neutral)
    if args.body_file:
        body_path = Path(args.body_file)
        if not body_path.is_file():
            _die(f"body file not found: {args.body_file}")
        if body_path.is_symlink():
            _die(f"body file must not be a symlink: {args.body_file}")
    return batch, rounds, accepted, rejected, exonerated


def compose_tally_record(args: argparse.Namespace) -> str:
    batch, rounds, accepted, rejected, exonerated = _validate_tally_args(args)
    record: dict[str, object] = {
        "schema_version": 2,
        "phase": args.phase,
        "batch": batch,
        "mode": args.mode,
        "rounds": rounds,
        "accepted_count": accepted,
        "rejected_count": rejected,
        "exonerated_count": exonerated,
    }
    # code-review body files are validation input only; their prose is intentionally
    # excluded from code-review-tally records.
    if args.body_file and args.phase != "code-review":
        record["body"] = Path(args.body_file).read_text(encoding="utf-8")
    return json.dumps(record, separators=(",", ":"))


def compose_tally_record_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="cli.py")
    try:
        args = _compose_args(argv)
        logging_util.emit(compose_tally_record(args))
        return 0
    except SystemExit as exc:
        return int(exc.code)


def _write_tally_stage_dir(log_root: str) -> Path:
    # write_tally stages beside larch-logs so redaction and rebasing stay under the implement tmpdir.
    parent = Path(log_root).parent
    if str(parent) in {"", "."} or not parent.is_absolute() or parent == Path(parent.anchor):
        _die(f"unsafe write-tally staging parent: {parent}")
    current = parent
    while True:
        if current.is_symlink():
            _die(f"write-tally staging parent must not have symlinked ancestors: {current}")
        if current == current.parent:
            break
        current = current.parent
    if not parent.exists():
        _die(f"write-tally staging parent does not exist: {parent}")
    if not parent.is_dir():
        _die(f"write-tally staging parent is not a directory: {parent}")
    if parent.is_symlink():
        _die(f"write-tally staging parent must not be a symlink: {parent}")
    return parent


def _validate_code_review_headers(body_file: str) -> tuple[int, str]:
    in_fence = False
    try:
        lines = Path(body_file).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return 3, str(exc)
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.match(r"^# Review Round [0-9]+$", line):
            continue
        if line.startswith("### [Code Review] "):
            continue
        if re.match(r"^### \[rejected\] FINDING_[0-9]+$", line):
            continue
        if re.match(r"^### FINDING_[0-9]+: ", line):
            continue
        if re.match(r"^#{1,6}\s", line) and line in _ALLOWED_CODE_REVIEW_HEADERS:
            continue
        if re.match(r"^#{1,6}\s", line):
            return 4, line
    return 0, ""


def write_tally_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="cli.py")
    try:
        args = _compose_args(argv, require_log=True)
        batch, *_ = _validate_tally_args(args)
        if args.phase == "code-review" and args.body_file:
            rc, output = _validate_code_review_headers(args.body_file)
            if rc == 3:  # noqa: PLR2004
                _die(f"code-review body header validation failed: {output or 'python3 validation error'}")
            if rc == 4:  # noqa: PLR2004
                _plain_diagnostic(
                    "WARNING=code-review body header validation ignored: "
                    f"unrecognized section header: {output}"
                )
            if rc not in (0, 4):
                _die("code-review body header validation failed")
        record = compose_tally_record(args)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            prefix="write-tally-record.",
            dir=_write_tally_stage_dir(args.log_root),
        ) as handle:
            handle.write(record + "\n")
            record_file = handle.name
        try:
            result = proc.run(
                [
                    *_larch_argv(),
                    "run-log",
                    "write",
                    "--log-root",
                    args.log_root,
                    "--skill",
                    args.skill,
                    "--run-id",
                    args.run_id,
                    "--batch",
                    batch,
                    "--input-file",
                    record_file,
                ]
            )
        finally:
            with suppress(FileNotFoundError):
                Path(record_file).unlink()
        for line in result.stdout.splitlines():
            if not line:
                continue
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", line):
                parsed = larch_io.parse_kv(line, duplicate_policy="first")
                if not parsed:
                    logging_util.emit(line)
                    continue
                key, value = next(iter(parsed.items()))
                logging_util.emit_kv(key=key, value=value)
            else:
                logging_util.emit(line)
        return result.returncode
    except SystemExit as exc:
        return int(exc.code)


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


def tally_vote_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="tally-vote")
    parser.add_argument("--ballot-file", required=True)
    parser.add_argument("--voter-files", nargs="*", default=[])
    args = parser.parse_args(argv)
    if not Path(args.ballot_file).is_file():
        return _error("tally-vote: --ballot-file must name a file")
    count = int(_parse_kv(output="\n".join(ballot_parse(args.ballot_file)), key="FINDING_COUNT") or "0")
    output: list[str] = []
    for idx in range(1, count + 1):
        yes = no = 0
        for voter_file in args.voter_files:
            path = Path(voter_file)
            if not path.is_file():
                continue
            vote = ""
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if re.search(rf"^FINDING_{idx}([^0-9]|$)", line):
                    if "YES" in line:
                        vote = "YES"
                    elif "NO" in line or "EXONERATE" in line:
                        vote = "NO"
            if vote == "YES":
                yes += 1
            elif vote == "NO":
                no += 1
        accepted = "true" if len(args.voter_files) < 2 or yes >= 2 else "false"  # noqa: PLR2004 - two-vote acceptance quorum threshold
        output.extend(
            [
                f"FINDING_{idx}_ACCEPTED={accepted}",
                f"FINDING_{idx}_VOTES_YES={yes}",
                f"FINDING_{idx}_VOTES_NO={no}",
            ]
        )
    output.append(f"FINDING_COUNT={count}")
    print("\n".join(output))
    return 0


def bash_printf_q(value: str) -> str:
    """Return the common bash ``printf '%q'`` backslash form for scoreboard parity."""
    if value == "":
        return "''"
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-")
    return "".join(ch if ch in safe else "\\" + ch for ch in value)


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


def _scoreboard_points_from_classification(
    *, classification_file: Path,
    reviewer_labels: list[str],
) -> dict[str, float]:
    scores: dict[str, float] = dict.fromkeys(reviewer_labels, 0.0)
    if not classification_file.is_file():
        return scores
    with classification_file.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = list(reader.fieldnames or [])
        rows = list(reader)
        reviewer_column = "finding_reviewers" if "finding_reviewers" in header else "reviewer_slots"
        label_set = reviewer_labels if reviewer_column == "finding_reviewers" else None
        corpus_labels = list(reviewer_labels)
        corpus_seen = set(corpus_labels)
        if reviewer_column == "finding_reviewers":
            for row in rows:
                grow_attribution_labels(corpus_labels, corpus_seen, row.get(reviewer_column, ""))
        active_bonus = unique_finder_bonus_from_env()
        for row in rows:
            result = (row.get("voting_result") or "").strip()
            if result not in {"accepted", "rejected", "neutral"}:
                continue
            raw_reviewers = raw_sole_finder_attribution(
                row.get(reviewer_column, ""),
                column=reviewer_column,
                corpus_labels=corpus_labels,
            )
            reviewers = split_classification_attribution(
                row.get(reviewer_column, ""),
                column=reviewer_column,
                labels=label_set,
            )
            if result == "accepted":
                delta = accepted_points_from_classification_row(cols=row, header=header)
                if active_bonus > 0 and not _classification_row_is_oos(row=row, header=header) and len(raw_reviewers) == 1:
                    delta += active_bonus
            elif result == "rejected":
                delta = -1
            elif _classification_row_is_oos(row=row, header=header):
                delta = 0
            else:
                delta = -NEUTRAL_FINDING_COST
            for reviewer in reviewers:
                if reviewer in scores:
                    scores[reviewer] += delta
    return scores


def scoreboard_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scoreboard")
    parser.add_argument("--tally-file", default="")
    parser.add_argument("--findings-classification-file", default="")
    parser.add_argument("--reviewer-labels", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args(argv)
    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    reviewer_labels = [label.strip() for label in args.reviewer_labels.split(",") if label.strip()]
    classification_file = Path(args.findings_classification_file) if args.findings_classification_file else None
    classification_scores = (
        _scoreboard_points_from_classification(classification_file=classification_file, reviewer_labels=reviewer_labels)
        if classification_file is not None and classification_file.is_file()
        else None
    )
    tally_text = Path(args.tally_file).read_text(encoding="utf-8", errors="replace") if args.tally_file and Path(args.tally_file).is_file() else ""
    rows = ["| Reviewer | Score |", "|---|---:|"]
    for label in reviewer_labels:
        score = 0.0
        if classification_scores is not None:
            score = classification_scores.get(label, 0.0)
        else:
            for line in tally_text.splitlines():
                if f"REVIEWER={label} " in line and "ACCEPTED=true" in line:
                    score += 1
        rows.append(f"| {label} | {format_score(score)} |")
    output_file.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"SCOREBOARD_FILE={bash_printf_q(str(output_file))}")
    return 0
