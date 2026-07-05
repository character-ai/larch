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
from collections.abc import Iterable, Mapping
from contextlib import suppress
from pathlib import Path
from typing import NoReturn

from larch import io as larch_io
from larch.core import logging_util
from larch.core import proc
from larch.core import redact
from larch.review.review_types import JudgeSeverity, ReviewVote

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

BACKTICKED_FOCUS_FILES = (
    "skills/shared/reviewer-templates.md",
    "agents/code-reviewer.md",
    "agents/reviewer-structure.md",
    "agents/reviewer-correctness.md",
    "agents/reviewer-testing.md",
    "agents/reviewer-security.md",
    "agents/reviewer-edge-cases.md",
    "agents/reviewer-plan-fidelity.md",
    "agents/reviewer-code-robustness.md",
    "docs/review-agents.md",
)
UNQUOTED_FOCUS_FILES = (
    "skills/review/SKILL.md",
    "python/larch/rendering/rendering.py",
    "skills/design/SKILL.md",
)

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

CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER = (
    "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv1_tool\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv2_tool\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain\tv3_tool\tscope"
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


def _bounded_prefix_text(*, path: Path, limit: int) -> str:
    try:
        with path.open("rb") as handle:
            return handle.read(limit).decode("utf-8", errors="replace")
    except OSError:
        return ""


def findings_classification_header_main(argv: list[str]) -> int:
    if argv:
        return _error("usage: findings-classification-header")
    print(findings_classification_header())
    return 0


def code_review_classification_header_main(argv: list[str]) -> int:
    if argv:
        return _error("usage: code-review-classification-header")
    print(code_review_classification_header())
    return 0


def _python_cli(plugin_root: str = "") -> Path:
    root = Path(plugin_root) if plugin_root else _plugin_root()
    return root / "python" / "cli.py"


def _run_log_cli_argv(*subcommand: str, plugin_root: str = "") -> list[str]:
    return ["python3", str(_python_cli(plugin_root)), "run-log", *subcommand]


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


def vote_for_id(*, ballot_id: str, voter_file: str | Path) -> str:
    result = "JUDGE_ERROR"
    try:
        raw = Path(voter_file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return result
    lines = _normalize_markdown_table_votes(raw).splitlines()
    pattern = re.compile(rf"^{re.escape(ballot_id)}:\s*(YES|NO|EXONERATE)(?:[\s-]|$)", re.IGNORECASE)
    for line in lines:
        match = pattern.search(line)
        if match:
            token = match.group(1).upper()
            result = "NO" if token == "EXONERATE" else token
    return result


def vote_for_id_main(argv: list[str]) -> int:
    if len(argv) != 2:  # noqa: PLR2004
        return _error("usage: vote-for-id <id> <voter-file>")
    print(vote_for_id(ballot_id=argv[0], voter_file=argv[1]))
    return 0


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


def reviewer_for_block_main(argv: list[str]) -> int:
    if len(argv) != 1:
        return _error("usage: reviewer-for-block <block-file>")
    sys.stdout.write(reviewer_for_block(argv[0]))
    return 0


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


def _ballot_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    current_id = ""
    current_lines: list[str] = []
    for raw in text.splitlines(keepends=True):
        match = BALLOT_HEADING_RE.match(raw.rstrip("\n"))
        if match:
            if current_id:
                blocks[current_id] = "".join(current_lines)
            current_id = match.group(1)
            if current_id in blocks:
                raise ValueError(f"duplicate ballot heading {current_id}")
            current_lines = [raw]
        elif current_id:
            current_lines.append(raw)
    if current_id:
        blocks[current_id] = "".join(current_lines)
    return blocks


def neutralize_reviewer_attribution(*, text: str, token: str = "anonymous") -> str:  # noqa: S107
    lines: list[str] = []
    in_block = False
    block_attribution_done = False
    for raw in text.splitlines(keepends=True):
        line = raw.removesuffix("\n")
        newline = "\n" if raw.endswith("\n") else ""
        if BALLOT_HEADING_RE.match(line):
            in_block = True
            block_attribution_done = False
            lines.append(raw)
            continue
        match = REVIEWER_ATTRIBUTION_RE.match(line)
        if in_block and match and not block_attribution_done:
            lines.append(f"{match.group('prefix')}{token}{match.group('trailing')}{newline}")
            block_attribution_done = True
        else:
            lines.append(raw)
    return "".join(lines)


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
    in_block = False
    for line in text.splitlines():
        if BALLOT_HEADING_RE.match(line):
            in_block = True
            continue
        if not in_block:
            continue
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
    for idx, raw in enumerate(lines):
        if BALLOT_HEADING_RE.match(raw.rstrip("\n")):
            lines.insert(idx + 1, reviewer_line + "\n")
            return "".join(lines)
    return reviewer_line + "\n" + block_text


def is_security_block_text(text: str) -> bool:
    text_no_fence = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text_no_backtick = re.sub(r"`[^`\n]*`", "", text_no_fence)
    canonical_token = re.compile(r"focus-area\s*=\s*security", re.IGNORECASE)
    explicit_header = re.compile(
        r"^###\s+(?:OOS_\d+:|FINDING_\d+:)\s*(?:\[(?:OUT_OF_SCOPE|OOS)\]\s*)?"
        r"`?(?:\[security\]|<security>)`?(?:\s|$|[:-])",
        re.IGNORECASE,
    )
    field_value = re.compile(
        r"^[ \t-]*focus[- ]area[ \t]*[:=][ \t]*security(?:[-a-z0-9 _]*)(?:[ \t]|$|\(|#|\.|,)",
        re.IGNORECASE,
    )
    lines = text_no_fence.splitlines()
    if canonical_token.search(text_no_backtick):
        return True
    if lines and explicit_header.search(lines[0]):
        return True
    for line in lines:
        normalized = line.replace("`", "").replace("*", "").strip()
        if field_value.search(normalized):
            return True
    return False


def is_security_block(block_file: str | Path) -> bool:
    try:
        text = Path(block_file).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"is_security_block: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    return is_security_block_text(text)


def is_security_block_main(argv: list[str]) -> int:
    if len(argv) != 1:
        return _error("usage: is-security-block <block-file>")
    return 0 if is_security_block(argv[0]) else 1


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

def accept_finding_main(argv: list[str]) -> int:
    if len(argv) != 4:  # noqa: PLR2004
        return _error("usage: accept-finding <yes> <no> <exonerate> <eligible>")
    yes, no, exonerate, eligible = (int(v) for v in argv)
    return 0 if accept_finding(yes=yes, no=no, exonerate=exonerate, eligible=eligible) else 1


def classify_result(*, yes: int, no: int, exonerate: int, eligible: int) -> str:
    if eligible <= 0:
        return "rejected"
    if accept_finding(yes=yes, no=no, exonerate=exonerate, eligible=eligible):
        return "accepted"
    if yes > 0:
        return "neutral"
    return "rejected"


def classify_result_main(argv: list[str]) -> int:
    if len(argv) != 4:  # noqa: PLR2004
        return _error("usage: classify-result <yes> <no> <exonerate> <eligible>")
    yes, no, exonerate, eligible = (int(v) for v in argv)
    sys.stdout.write(classify_result(yes=yes, no=no, exonerate=exonerate, eligible=eligible))
    return 0


def panel_tier(eligible: int) -> str:
    if eligible >= 3:  # noqa: PLR2004
        return "full-3"
    if eligible == 2:  # noqa: PLR2004
        return "unanimous-2"
    if eligible == 1:
        return "single-judge"
    return "main-agent-required"


def panel_tier_main(argv: list[str]) -> int:
    if len(argv) != 1:
        return _error("usage: panel-tier <eligible>")
    sys.stdout.write(panel_tier(int(argv[0])))
    return 0


def split_ballot(*, ballot_file: str | Path, out_dir: str | Path) -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    current: Path | None = None
    with Path(ballot_file).open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            match = BALLOT_HEADING_RE.match(line)
            if match:
                item_id = match.group(1)
                if item_id in seen:
                    print(f"duplicate ballot heading {item_id}", file=sys.stderr)
                    raise SystemExit(1)
                seen.add(item_id)
                current = out_path / f"{item_id}.md"
                current.write_text(raw, encoding="utf-8")
            elif current is not None:
                with current.open("a", encoding="utf-8") as output:
                    output.write(raw)


def split_ballot_main(argv: list[str]) -> int:
    if len(argv) != 2:  # noqa: PLR2004
        return _error("usage: split-ballot <ballot-file> <out-dir>")
    split_ballot(ballot_file=argv[0], out_dir=argv[1])
    return 0


def parse_judge_vote(*, voter_file: str | Path, ballot_id: str) -> tuple[str, str, str, str, str]:
    vote = correctness = severity = quality = uncertain_token = ""
    pattern = re.compile(rf"^{re.escape(ballot_id)}:\s*", re.IGNORECASE)
    try:
        raw_text = Path(voter_file).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise FileNotFoundError(str(exc)) from exc
    lines = _normalize_markdown_table_votes(raw_text).splitlines()
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


def parse_judge_vote_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="cli.py")
    if len(argv) != 2:  # noqa: PLR2004
        logging_util.BreadcrumbWriter().emit("usage: parse-judge-vote <voter_file> <ballot_id>")
        return 2
    voter_file, ballot_id = argv
    if not os.access(voter_file, os.R_OK) or not Path(voter_file).is_file():
        logging_util.BreadcrumbWriter().emit(
            f"parse-judge-vote: voter file is missing or unreadable: {voter_file}"
        )
        return 2
    vote, correctness, severity, quality, uncertain = parse_judge_vote(voter_file=voter_file, ballot_id=ballot_id)
    logging_util.emit_kv(key="PARSED_VOTE", value=vote)
    logging_util.emit_kv(key="PARSED_CORRECTNESS", value=correctness)
    logging_util.emit_kv(key="PARSED_SEVERITY", value=severity)
    logging_util.emit_kv(key="PARSED_QUALITY", value=quality)
    logging_util.emit_kv(key="PARSED_UNCERTAIN", value=uncertain)
    return 0


def voter_parse_rate_diag_path(voter_path: str | Path) -> Path:
    path = Path(voter_path)
    text = str(path)
    if text.endswith(".txt"):
        return Path(text[:-4] + "-parse-rate-diag.txt")
    return Path(text + "-parse-rate-diag.txt")


def voter_output_sha256(voter_path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(voter_path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _darwin_path_aliases(path: str | Path) -> set[str]:
    text = str(path)
    aliases = {text, str(Path(text))}
    for candidate in tuple(aliases):
        if candidate.startswith("/private/var/"):
            aliases.add(candidate.removeprefix("/private"))
        elif candidate.startswith("/var/"):
            aliases.add("/private" + candidate)
    return aliases


def voter_parse_rate_diag_matches_output(voter_path: str | Path) -> bool:
    # review_tally.py no longer reads this sidecar; it calls parse-rate-check directly.
    path = Path(voter_path)
    diag_file = voter_parse_rate_diag_path(path)
    if not diag_file.is_file() or not path.is_file():
        return False
    recorded_path = recorded_sha = ""
    for line in diag_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("voter_file=") and not recorded_path:
            recorded_path = line[len("voter_file=") :]
        elif line.startswith("voter_sha256=") and not recorded_sha:
            recorded_sha = line[len("voter_sha256=") :]
    path_matches = bool(_darwin_path_aliases(recorded_path) & _darwin_path_aliases(path))
    return bool(recorded_path and recorded_sha) and path_matches and recorded_sha == voter_output_sha256(path)


def parse_rate_diag_matches_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="parse-rate-diag-matches")
    parser.add_argument("--voter-file", required=True)
    args = parser.parse_args(argv)
    return 0 if voter_parse_rate_diag_matches_output(args.voter_file) else 1


def _ballot_ids(*, ballot_file: str | Path, grammar: str) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    if grammar == "finding-oos":
        pattern = re.compile(r"^(?:###\s+)?((?:FINDING|OOS)_[0-9]+):")
    else:
        pattern = re.compile(r"^(?:###\s+)?(FINDING_[0-9]+):")
    try:
        lines = Path(ballot_file).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        match = pattern.match(line)
        if match and match.group(1) not in seen:
            seen.add(match.group(1))
            ids.append(match.group(1))
    return ids


def voter_launcher_tool(voter_tool: str) -> str:
    if voter_tool.startswith("codex-"):
        return "codex"
    if voter_tool.startswith("cursor-"):
        return "cursor"
    return voter_tool


def parse_rate_check_tool_label(voter_tool: str) -> str:
    launcher_tool = voter_launcher_tool(voter_tool)
    if launcher_tool == "claude":
        return "agent launch-claude-review (voter parse-rate check)"
    if launcher_tool in {"codex", "cursor"}:
        return f"agent launch-review --tool {launcher_tool} (voter parse-rate check; label {voter_tool})"
    return f"voter parse-rate check ({voter_tool})"


def is_harness_review_path(path: str | Path) -> bool:
    text = str(path)
    patterns = (
        "test-dispatch-code-voters.",
        "test_agent_voters.",
        "test-dispatch-plan-voters.",
        "test-plan-review-loop.",
        "test-collect-",
        "test-check-",
        "test-tally-",
    )
    return any(token in text for token in patterns)


def should_suppress_parse_rate_issue_append(*, voter_path: str | Path, base_tmp: str | Path) -> bool:
    # Normalize via Path to collapse repeated slashes (e.g. $TMPDIR ending in /)
    voter = str(Path(voter_path))
    base = str(Path(base_tmp))
    return voter.startswith(base + "/") and (is_harness_review_path(base) or is_harness_review_path(voter))


def _issues_log(base_tmp: str) -> str:
    if os.environ.get("LARCH_EXECUTION_ISSUES_LOG"):
        return os.environ["LARCH_EXECUTION_ISSUES_LOG"]
    if os.environ.get("SESSION_ENV_PATH"):
        return str(Path(os.environ["SESSION_ENV_PATH"]).parent / "execution-issues.md")
    if os.environ.get("IMPLEMENT_TMPDIR"):
        return str(Path(os.environ["IMPLEMENT_TMPDIR"]) / "execution-issues.md")
    return str(Path(base_tmp) / "execution-issues.md")


# Issue #4880: per-voter JUDGE_ERROR rate at or above this fraction removes the voter slot from the
# effective quorum. Parameterized (default unchanged) so operators can tune how aggressively a
# partially-truncated voter is dropped without a code change.
_DEFAULT_JUDGE_ERROR_PARSE_THRESHOLD = 0.8


def _judge_error_parse_threshold() -> float:
    raw = os.environ.get("LARCH_VOTER_JUDGE_ERROR_PARSE_THRESHOLD", "")
    if not raw:
        return _DEFAULT_JUDGE_ERROR_PARSE_THRESHOLD
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_JUDGE_ERROR_PARSE_THRESHOLD
    if value <= 0 or value > 1:
        return _DEFAULT_JUDGE_ERROR_PARSE_THRESHOLD
    return value


def check_voter_parse_rate(
    *,
    voter_file: str,
    voter_tool: str,
    ballot_file: str,
    id_grammar: str,
    review_tmpdir: str,
    slot: str = "",
    log_mode: str = "log",
    plugin_root: str = "",
    dispatch_label: str = "agent dispatch-voters",
) -> str:
    voter_path = Path(voter_file)
    diag_file = voter_parse_rate_diag_path(voter_path)
    if not voter_path.is_file() or voter_path.stat().st_size == 0:
        return "OK"
    ids = _ballot_ids(ballot_file=ballot_file, grammar=id_grammar)
    if not ids:
        return "OK"
    judge_error_count = 0
    for item_id in ids:
        try:
            parsed_vote = parse_judge_vote(voter_file=voter_path, ballot_id=item_id)[0]
        except FileNotFoundError:
            parsed_vote = ""
        one = parsed_vote or "JUDGE_ERROR"
        if one == "JUDGE_ERROR":
            judge_error_count += 1
    if judge_error_count / len(ids) >= _judge_error_parse_threshold():
        first_bytes = _bounded_prefix_text(path=voter_path, limit=200)
        voter_file_aliases: list[str] = sorted(_darwin_path_aliases(voter_file), key=lambda alias: (alias.startswith("/private/var/"), alias))
        lines: list[str] = []
        if slot:
            lines.append(f"slot={slot}")
        lines.extend(
            [
                f"voter_tool={voter_tool}",
                f"judge_error_count={judge_error_count}",
                f"total_findings={len(ids)}",
                f"total_ballot_items={len(ids)}",
            ]
        )
        lines.extend(f"voter_file={alias}" for alias in voter_file_aliases)
        lines.extend(
            [
                f"voter_sha256={voter_output_sha256(voter_path)}",
                "--- first 200 bytes of voter output ---",
                first_bytes,
            ]
        )
        with suppress(OSError):
            diag_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        if log_mode == "log":
            _plain_diagnostic(
                f"**⚠ Voter {voter_tool}: {judge_error_count}/{len(ids)} ballot items returned JUDGE_ERROR: voter likely produced prose without FINDING_N:/OOS_N: VOTE lines. Check voter output at {voter_path}.**"
            )
            if not should_suppress_parse_rate_issue_append(voter_path=voter_path, base_tmp=review_tmpdir):
                proc.run(
                    [
                        *_run_log_cli_argv("append-failure", plugin_root=plugin_root),
                        "--log",
                        _issues_log(review_tmpdir),
                        "--site",
                        f"{dispatch_label} {voter_tool}",
                        "--tool",
                        parse_rate_check_tool_label(voter_tool),
                        "--exit-code",
                        "0",
                        "--status-label",
                        "warning",
                        "--category",
                        "Warnings",
                        "--output-file",
                        str(diag_file),
                        "--redact",
                    ]
                )
        return "NOT_SUBSTANTIVE"
    with suppress(FileNotFoundError):
        diag_file.unlink()
    return "OK"


def _parse_rate_common_parser(prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("--voter-file", required=True)
    parser.add_argument("--voter-tool", required=True)
    parser.add_argument("--ballot-file", required=True)
    parser.add_argument("--id-grammar", choices=("finding-only", "finding-oos"), required=True)
    parser.add_argument("--review-tmpdir", required=True)
    parser.add_argument("--slot", default="")
    parser.add_argument("--log-mode", default="log")
    parser.add_argument("--plugin-root", default="")
    parser.add_argument("--dispatch-label", default="agent dispatch-voters")
    return parser


def parse_rate_check_main(argv: list[str]) -> int:
    parser = _parse_rate_common_parser("parse-rate-check")
    args = parser.parse_args(argv)
    status = check_voter_parse_rate(
        voter_file=args.voter_file,
        voter_tool=args.voter_tool,
        ballot_file=args.ballot_file,
        id_grammar=args.id_grammar,
        review_tmpdir=args.review_tmpdir,
        slot=args.slot,
        log_mode=args.log_mode,
        plugin_root=args.plugin_root,
        dispatch_label=args.dispatch_label,
    )
    print(f"PARSE_RATE_STATUS={status}")
    return 0


def _extract_ctx(argv: list[str]) -> tuple[list[str], list[str]]:
    rest: list[str] = []
    ctx: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--ctx":
            if i + 1 >= len(argv):
                raise SystemExit(_error("parse-rate-retry: --ctx requires a value"))
            ctx.append(argv[i + 1])
            i += 2
        elif arg.startswith("--ctx="):
            ctx.append(arg[len("--ctx=") :])
            i += 1
        else:
            rest.append(arg)
            i += 1
    return rest, ctx


def parse_rate_retry_main(argv: list[str]) -> int:
    rest, _ctx = _extract_ctx(argv)
    parser = _parse_rate_common_parser("parse-rate-retry")
    parser.add_argument("--prompt-file", default="")
    parser.add_argument("--retry-prefix-kind", choices=("code", "plan"), default="code")
    parser.add_argument("--launch-mode", default="")
    args = parser.parse_args(rest)
    status = check_voter_parse_rate(
        voter_file=args.voter_file,
        voter_tool=args.voter_tool,
        ballot_file=args.ballot_file,
        id_grammar=args.id_grammar,
        review_tmpdir=args.review_tmpdir,
        slot=args.slot,
        log_mode="log",
        plugin_root=args.plugin_root,
        dispatch_label=args.dispatch_label,
    )
    print(status)
    return 0


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


def voter_status_block_main(argv: list[str]) -> int:
    if len(argv) != 13:  # noqa: PLR2004
        return _error("usage: voter-status-block <13 positional args>")
    (
        voter_1_path,
        voter_1_tool,
        voter_1_status,
        voter_1_parse_rate_status,
        voter_2_path,
        voter_2_tool,
        voter_2_status,
        voter_2_parse_rate_status,
        voter_3_path,
        voter_3_tool,
        voter_3_status,
        voter_3_parse_rate_status,
        plan_voter_paths_file,
    ) = argv
    rows = [
        ("VOTER_1_PATH", voter_1_path),
        ("VOTER_1_TOOL", voter_1_tool),
        ("VOTER_1_STATUS", voter_1_status),
        ("VOTER_1_PARSE_RATE_STATUS", voter_1_parse_rate_status),
        ("VOTER_2_PATH", voter_2_path),
        ("VOTER_3_PATH", voter_3_path),
    ]
    if Path(plan_voter_paths_file).is_file() and Path(plan_voter_paths_file).stat().st_size > 0:
        rows.append(("VOTER_PATHS_FILE", plan_voter_paths_file))
    rows.extend(
        [
            ("VOTER_2_TOOL", voter_2_tool),
            ("VOTER_3_TOOL", voter_3_tool),
            ("VOTER_2_STATUS", voter_2_status),
            ("VOTER_3_STATUS", voter_3_status),
            ("VOTER_2_PARSE_RATE_STATUS", voter_2_parse_rate_status),
            ("VOTER_3_PARSE_RATE_STATUS", voter_3_parse_rate_status),
        ]
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
                    *_run_log_cli_argv("write"),
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
                logging_util.emit_kv(key=line.split("=", 1)[0], value=line.split("=", 1)[1])
            else:
                logging_util.emit(line)
        return result.returncode
    except SystemExit as exc:
        return int(exc.code)


def false_positive_match(text: str) -> bool:
    negated = (
        r"(^|[^a-z])not\s+((a|an)\s+)?duplicate([^a-z]|$)",
        r"(^|[^a-z])not\s+((a|an)\s+)?false[- ]positive([^a-z]|$)",
    )
    positives = (
        r"(^|[^a-z])won[^\s]*t\s+fix([^a-z]|$)",
        r"(^|[^a-z])wontfix([^a-z]|$)",
        r"(^|[^a-z])superseded(\s+by\s+#[0-9]+)?([^a-z]|$)",
        r"(^|[^a-z])not\s+an\s+issue([^a-z]|$)",
        r"(^|[^a-z])not\s+a\s+bug([^a-z]|$)",
        r"(^|[^a-z])duplicate\s+of\s+#[0-9]+([^a-z]|$)",
        r"(^|[^a-z])false[- ]positive([^a-z]|$)",
    )
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in negated):
        return False
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in positives)


def false_positive_match_main(argv: list[str]) -> int:
    if len(argv) != 1:
        return _error("usage: false-positive-match <text>")
    return 0 if false_positive_match(argv[0]) else 1


def file_line_regex_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="file-line-regex")
    parser.add_argument("--name", required=True, choices=sorted(FILE_LINE_REGEXES))
    args = parser.parse_args(argv)
    print(FILE_LINE_REGEXES[args.name])
    return 0


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


def ballot_parse_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="ballot-parse")
    parser.add_argument("--ballot-file", required=True)
    args = parser.parse_args(argv)
    if not Path(args.ballot_file).is_file():
        return _error("ballot-parse: --ballot-file must name a file")
    print("\n".join(ballot_parse(args.ballot_file)))
    return 0


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
        accepted = "true" if len(args.voter_files) < 2 or yes >= 2 else "false"  # noqa: PLR2004
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

def lint_focus_area_enum_main(argv: list[str]) -> int:
    if argv:
        return _error("usage: lint focus-area-enum")
    exit_code = 0
    root = _plugin_root()
    hits_re = re.compile(r"`code-quality`.*`risk-integration`.*`correctness`.*`architecture`")
    unquoted_re = re.compile(r"code-quality / risk-integration / correctness / architecture")
    for rel in BACKTICKED_FOCUS_FILES:
        path = root / rel
        if not path.is_file():
            print(f"::error file={rel}::expected file is missing")
            exit_code = 1
            continue
        hits = [(i, line) for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1) if hits_re.search(line)]
        if not hits:
            print(f"::error file={rel}::no backticked focus-area enumeration found")
            exit_code = 1
        for line_no, line_text in hits:
            if "security" not in line_text:
                print(f"::error file={rel},line={line_no}::backticked focus-area enumeration does not include 'security': {line_text}")
                exit_code = 1
    for rel in UNQUOTED_FOCUS_FILES:
        path = root / rel
        if not path.is_file():
            print(f"::error file={rel}::expected file is missing")
            exit_code = 1
            continue
        hits = [(i, line) for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1) if unquoted_re.search(line)]
        if not hits:
            print(f"::error file={rel}::no unquoted focus-area enumeration found")
            exit_code = 1
        for line_no, line_text in hits:
            if "security" not in line_text:
                print(f"::error file={rel},line={line_no}::unquoted focus-area enumeration does not include 'security': {line_text}")
                exit_code = 1
    return exit_code
