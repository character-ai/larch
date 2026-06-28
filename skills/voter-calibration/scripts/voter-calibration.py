#!/usr/bin/env python3
"""Analyze voter agreement, severity calibration, and chronic outliers from larch logs."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

plugin_root = (
    Path(os.environ["CLAUDE_PLUGIN_ROOT"])
    if os.environ.get("CLAUDE_PLUGIN_ROOT")
    else Path(__file__).resolve().parents[3]
)
python_path = str(plugin_root / "python")
if python_path not in sys.path:
    sys.path.insert(0, python_path)

from larch.issue.analyze_issues import (  # noqa: E402
    GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER,
    _fetch_filed_oos_issue_details,
    _ground_truth_calibration_incentive_shipped,
    _ground_truth_run_dir,
    _ground_truth_run_started_at_strict,
    _load_filed_issue_details_json,
    extract_repo_from_url,
    fetch_main,
    ground_truth_voter_calibration,
    iter_filed_oos_records,
    load_issues,
    parse_iso,
)
from larch.review import voting  # noqa: E402
from larch.review.voting import (  # noqa: E402
    classification_tsv_schema_supported,
    compute_voter_agreement,
    compute_voter_severity_distribution,
    render_voter_severity_scoreboard,
    voter_agreement_rows_from_tsv,
)


@dataclass(frozen=True)
class BoundaryResult:
    boundary: datetime | None
    source: str
    repo: str | None = None
    unavailable_reason: str = ""


@dataclass
class CorpusStats:
    files_seen: int = 0
    skipped_files: int = 0
    malformed_rows: int = 0
    ineligible_rows: int = 0
    rows: list[dict[str, object]] = field(default_factory=list)
    false_negative_rows: list[dict[str, object]] = field(default_factory=list)


def _git_toplevel() -> Path | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return Path(value) if value else None


def _default_log_root() -> Path:
    top = _git_toplevel()
    if top is not None:
        return top / "larch-logs"
    return Path.cwd() / "larch-logs"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _discover(log_root: Path) -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []
    for path in sorted(log_root.glob("design/*/plan-review/round-*/findings-classification.tsv")):
        paths.append(("design", path))
    for path in sorted(log_root.glob("implement/*/round-*/findings-classification.tsv")):
        paths.append(("code-review", path))
    for path in sorted(log_root.glob("review/*/review-findings-classification-round-*.tsv")):
        paths.append(("code-review", path))
    return paths


def _rate(value: object) -> str:
    return "n/a" if value is None else f"{float(value):.3f}"


def _table(records: list[dict[str, object]]) -> str:
    lines = [
        "| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    if not records:
        lines.append("| n/a | n/a | 0 | 0 | 0 | 0 | n/a | false |")
        return "\n".join(lines)
    for record in records:
        lines.append(
            f"| {record['panel']} | {record['voter']} | {record['eligible']} | "
            f"{record['agree']} | {record['disagree']} | {record['missing']} | "
            f"{_rate(record['agreement_rate'])} | {str(bool(record['outlier'])).lower()} |"
        )
    return "\n".join(lines)


def _global_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        copied = dict(row)
        copied["panel"] = "global"
        out.append(copied)
    return out


def _parse_era_since_date(value: str) -> datetime:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        print("voter-calibration: --era-since-date must be YYYY-MM-DD", file=sys.stderr)
        raise SystemExit(2)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        print("voter-calibration: --era-since-date must be a valid YYYY-MM-DD date", file=sys.stderr)
        raise SystemExit(2) from None
    return parsed.replace(tzinfo=timezone.utc)


def _slug_owner_repo_from_remote_url(url: str) -> str | None:
    repo = (url or "").strip()
    if not repo:
        return None
    repo = re.sub(r"^git@[^:]+:", "", repo)
    repo = re.sub(r"^https?://[^/]+/", "", repo)
    repo = re.sub(r"\.git$", "", repo)
    if not re.fullmatch(r"[^/]+/[^/]+", repo):
        return None
    return repo


def _resolve_incentive_repo(plugin_root_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(plugin_root_path), "config", "--get", "remote.origin.url"],
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return _slug_owner_repo_from_remote_url(result.stdout.strip())


def _run_gh_json(args: list[str]) -> tuple[int, object | None]:
    try:
        result = subprocess.run(args, text=True, capture_output=True, check=False)
    except FileNotFoundError:
        return 127, None
    if result.returncode != 0:
        return result.returncode, None
    if not (result.stdout or "").strip():
        return result.returncode, None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.returncode, None
    if not isinstance(payload, Mapping) or not payload:
        return result.returncode, None
    return result.returncode, payload


def _resolve_era_boundary_auto(plugin_root_path: Path) -> BoundaryResult:
    repo = _resolve_incentive_repo(plugin_root_path)
    if repo is None:
        return BoundaryResult(None, "gh-issue-closedAt", unavailable_reason="repo_unresolved")

    issue_fields = "number,state,stateReason,labels,body,closedAt,closedByPullRequestsReferences"
    code, payload = _run_gh_json(
        [
            "gh",
            "issue",
            "view",
            str(GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER),
            "--repo",
            repo,
            "--json",
            issue_fields,
        ]
    )
    if code != 0 or not isinstance(payload, Mapping):
        return BoundaryResult(None, "gh-issue-closedAt", repo=repo, unavailable_reason="gh_issue_view_unavailable")

    normalized = {**payload, "number": GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER}
    shipped, reason = _ground_truth_calibration_incentive_shipped(issues=[normalized], repo=None)
    if not shipped:
        return BoundaryResult(None, "gh-issue-closedAt", repo=repo, unavailable_reason=reason)

    boundary = parse_iso(str(normalized.get("closedAt") or ""))
    if boundary is None:
        return BoundaryResult(None, "gh-issue-closedAt", repo=repo, unavailable_reason="closedAt_unavailable")
    return BoundaryResult(boundary, "gh-issue-closedAt", repo=repo)


def _resolve_era_boundary(args: argparse.Namespace) -> BoundaryResult:
    if args.era_since_date:
        return BoundaryResult(_parse_era_since_date(args.era_since_date), "explicit-date")
    return _resolve_era_boundary_auto(plugin_root)



_FALSE_NEGATIVE_COUNTABLE_VERDICTS = {"accepted", "neutral", "rejected"}
_FALSE_NEGATIVE_OOS_SCOPES = {"oos", "out_of_scope", "out-of-scope"}


def _false_negative_scope_is_oos(row: Mapping[str, str]) -> bool:
    scope = (row.get("scope") or "").strip().lower()
    finding_id = (row.get("finding_id") or "").strip().upper()
    return scope in _FALSE_NEGATIVE_OOS_SCOPES or finding_id.startswith("OOS_")


def _false_negative_rows_from_tsv(text: str, *, panel_kind: str) -> tuple[list[dict[str, object]], int, int]:
    rows: list[dict[str, object]] = []
    malformed_rows = 0
    ineligible_rows = 0
    for prep in voting.classification_row_panel_inputs(text, panel_kind=panel_kind):
        row = prep.raw_row
        result = (row.get("voting_result") or "").strip().lower()
        voter_votes = [
            (label, voting._normalize_vote_cell(raw_vote))
            for label, raw_vote in prep.voter_votes
            if label
        ]
        parseable = [(label, vote) for label, vote in voter_votes if vote]
        if result not in _FALSE_NEGATIVE_COUNTABLE_VERDICTS:
            malformed_rows += 1
            continue
        if _false_negative_scope_is_oos(row):
            continue
        if len(parseable) < 2:  # noqa: PLR2004
            ineligible_rows += 1
            continue
        voters = [{"voter": label, "vote": vote} for label, vote in parseable]
        rows.append({"panel": prep.panel, "voting_result": result, "voters": voters})
    return rows, malformed_rows, ineligible_rows


def _compute_false_negative_yes_rates(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    aggregate: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        panel = str(row.get("panel") or "unknown")
        result = str(row.get("voting_result") or "").strip().lower()
        voters_obj = row.get("voters")
        if not isinstance(voters_obj, list):
            continue
        for voter_obj in voters_obj:
            if not isinstance(voter_obj, dict):
                continue
            voter = str(voter_obj.get("voter") or "").strip()
            vote = str(voter_obj.get("vote") or "").upper()
            if not voter:
                continue
            record = aggregate.setdefault(
                (panel, voter),
                {
                    "panel": panel,
                    "voter": voter,
                    "yes_votes": 0,
                    "neutral_yes": 0,
                    "rejected_yes": 0,
                    "false_negative_yes": 0,
                    "false_negative_yes_rate": None,
                },
            )
            if vote != "YES":
                continue
            record["yes_votes"] = int(record["yes_votes"]) + 1
            if result == "neutral":
                record["neutral_yes"] = int(record["neutral_yes"]) + 1
            elif result == "rejected":
                record["rejected_yes"] = int(record["rejected_yes"]) + 1
    for record in aggregate.values():
        false_negative_yes = int(record["neutral_yes"]) + int(record["rejected_yes"])
        yes_votes = int(record["yes_votes"])
        record["false_negative_yes"] = false_negative_yes
        record["false_negative_yes_rate"] = false_negative_yes / yes_votes if yes_votes else None
    return sorted(aggregate.values(), key=lambda r: (str(r["panel"]), str(r["voter"])))


def _false_negative_yes_table(rows: list[dict[str, object]]) -> str:
    lines = [
        "| Panel | Voter | YES Votes | Neutral YES | Rejected YES | False-negative YES | False-negative YES Rate |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    records = _compute_false_negative_yes_rates(rows)
    if not records:
        lines.append("| n/a | n/a | 0 | 0 | 0 | 0 | n/a |")
        return "\n".join(lines)
    for record in records:
        lines.append(
            f"| {record['panel']} | {record['voter']} | {record['yes_votes']} | "
            f"{record['neutral_yes']} | {record['rejected_yes']} | {record['false_negative_yes']} | "
            f"{_rate(record['false_negative_yes_rate'])} |"
        )
    return "\n".join(lines)

def _parse_file_into_stats(stats: CorpusStats, *, panel: str, path: Path) -> None:
    stats.files_seen += 1
    text = _read_text(path)
    parsed = voter_agreement_rows_from_tsv(text, panel_kind=panel)
    first_line = text.splitlines()[0] if text.splitlines() else ""
    if not parsed.rows and (
        "voting_result" not in first_line
        or not classification_tsv_schema_supported(text, panel_kind=panel)
    ):
        stats.skipped_files += 1
    stats.malformed_rows += parsed.malformed_rows
    stats.ineligible_rows += parsed.ineligible_rows
    stats.rows.extend(parsed.rows)
    fn_rows, _fn_malformed, _fn_ineligible = _false_negative_rows_from_tsv(text, panel_kind=panel)
    stats.false_negative_rows.extend(fn_rows)


def _collect_era_corpora(
    *,
    boundary: datetime,
    discovered: list[tuple[str, Path]],
) -> tuple[dict[str, CorpusStats], int]:
    corpora = {"pre": CorpusStats(), "post": CorpusStats()}
    excluded_run_dirs: set[Path] = set()
    for panel, path in discovered:
        run_dir = _ground_truth_run_dir(path, panel_kind=panel)
        started_at = _ground_truth_run_started_at_strict(run_dir)
        if started_at is None:
            excluded_run_dirs.add(run_dir)
            continue
        era = "pre" if started_at < boundary else "post"
        _parse_file_into_stats(corpora[era], panel=panel, path=path)
    return corpora, len(excluded_run_dirs)


def _render_boundary_unavailable(*, log_root: Path, result: BoundaryResult) -> str:
    lines = [
        "# Voter Calibration Report",
        "",
        "## Era Boundary Unavailable",
        "",
        "- Era segmentation needs an incentive boundary timestamp.",
        f"- Log root: `{log_root}`",
        f"- Boundary source attempted: `{result.source}`",
        f"- Resolved repo: `{result.repo or 'n/a'}`",
        f"- Reason: `{result.unavailable_reason or 'unknown'}`",
        "- Pass `--era-since-date YYYY-MM-DD` to choose a manual UTC midnight cutoff.",
        "- This report is diagnostic only.",
    ]
    return "\n".join(lines) + "\n"


def _render_era_slice(
    *,
    title: str,
    stats: CorpusStats,
    min_votes: int,
    outlier_threshold: float,
    high_severity_threshold: float,
) -> str:
    records = compute_voter_agreement(
        stats.rows,
        min_votes=min_votes,
        outlier_threshold=outlier_threshold,
    )
    severity_records = compute_voter_severity_distribution(
        stats.rows,
        high_severity_threshold=high_severity_threshold,
    )
    false_negative_rows = stats.false_negative_rows + _global_rows(stats.false_negative_rows)
    lines = [
        f"## {title}",
        "",
        f"- Classification TSV files scanned: {stats.files_seen}",
        f"- Malformed or unsupported TSV files skipped: {stats.skipped_files}",
        f"- Malformed data rows dropped: {stats.malformed_rows}",
        f"- Ineligible panels excluded: {stats.ineligible_rows}",
        f"- Qualifying accepted/rejected panels: {len(stats.rows)}",
        "",
        "## Agreement Table",
        "",
        _table(records),
        "",
        render_voter_severity_scoreboard(severity_records),
        "",
        "## Per-voter False-negative YES Rate",
        "",
        _false_negative_yes_table(false_negative_rows),
    ]
    return "\n".join(lines)


def _render_era_report(
    *,
    log_root: Path,
    era: str,
    boundary_result: BoundaryResult,
    corpora: dict[str, CorpusStats],
    discovered_count: int,
    excluded_missing_started_at_runs: int,
    min_votes: int,
    outlier_threshold: float,
    high_severity_threshold: float,
    realized_outcomes_markdown: str = "",
) -> str:
    boundary = boundary_result.boundary
    boundary_text = boundary.isoformat().replace("+00:00", "Z") if boundary else "n/a"
    lines = [
        "# Voter Calibration Report",
        "",
        "## Era Boundary",
        "",
        f"- Log root: `{log_root}`",
        f"- Boundary source: `{boundary_result.source}`",
        f"- Boundary timestamp: `{boundary_text}`",
        f"- Resolved repo: `{boundary_result.repo or 'n/a'}`",
        f"- Classification TSV files discovered: {discovered_count}",
        f"- Runs excluded for missing or invalid `started_at`: {excluded_missing_started_at_runs}",
        "- Runs before the boundary are pre-incentive. Runs at or after it are post-incentive.",
        "",
    ]
    if era in {"all", "pre"}:
        lines.append(
            _render_era_slice(
                title="Pre-incentive era",
                stats=corpora["pre"],
                min_votes=min_votes,
                outlier_threshold=outlier_threshold,
                high_severity_threshold=high_severity_threshold,
            )
        )
    if era in {"all", "post"}:
        if era == "all":
            lines.append("")
        lines.append(
            _render_era_slice(
                title="Post-incentive era",
                stats=corpora["post"],
                min_votes=min_votes,
                outlier_threshold=outlier_threshold,
                high_severity_threshold=high_severity_threshold,
            )
        )
    if realized_outcomes_markdown:
        lines.extend(["", realized_outcomes_markdown.rstrip()])
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Era segmentation is diagnostic only.",
            "- Empty, missing, and `JUDGE_ERROR` voter cells count as missing, not disagreement.",
            "- Severity calibration counts only YES votes with valid severity buckets.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render(
    *,
    log_root: Path,
    files_seen: int,
    skipped_files: int,
    malformed_rows: int,
    ineligible_rows: int,
    rows: list[dict[str, object]],
    false_negative_rows: list[dict[str, object]],
    min_votes: int,
    outlier_threshold: float,
    high_severity_threshold: float,
    realized_outcomes_markdown: str = "",
) -> str:
    records = compute_voter_agreement(rows, min_votes=min_votes, outlier_threshold=outlier_threshold)
    global_records = compute_voter_agreement(_global_rows(rows), min_votes=min_votes, outlier_threshold=outlier_threshold)
    severity_records = compute_voter_severity_distribution(rows, high_severity_threshold=high_severity_threshold)
    global_severity_records = compute_voter_severity_distribution(
        _global_rows(rows),
        high_severity_threshold=high_severity_threshold,
    )
    false_negative_records = false_negative_rows + _global_rows(false_negative_rows)
    outliers = [record for record in records + global_records if bool(record["outlier"])]
    missing = sorted(records, key=lambda r: int(r["missing"]), reverse=True)

    lines = [
        "# Voter Calibration Report",
        "",
        "## Corpus",
        "",
        f"- Log root: `{log_root}`",
        f"- Classification TSV files scanned: {files_seen}",
        f"- Malformed or unsupported TSV files skipped: {skipped_files}",
        f"- Malformed data rows dropped: {malformed_rows}",
        f"- Ineligible panels excluded: {ineligible_rows}",
        f"- Qualifying accepted/rejected panels: {len(rows)}",
        "",
        "## Agreement Table",
        "",
        _table(records),
        "",
        render_voter_severity_scoreboard(severity_records),
        "",
        "## Global Voter Agreement",
        "",
        _table(global_records),
        "",
        render_voter_severity_scoreboard(global_severity_records),
        "",
        f"## Chronic Outliers (threshold < {outlier_threshold:.2f}, min votes {min_votes})",
        "",
        _table(outliers),
        "",
        "## Missing Vote Table",
        "",
        _table(missing),
        "",
        "## Per-voter False-negative YES Rate",
        "",
        _false_negative_yes_table(false_negative_records),
        "",
    ]
    if realized_outcomes_markdown:
        lines.extend([realized_outcomes_markdown.rstrip(), ""])
    lines.extend([
        "## Notes",
        "",
        "- Neutral panel verdicts are excluded from agreement denominators.",
        "- Single-voter and zero-voter panels are excluded because agreement is undefined.",
        "- Empty, missing, and `JUDGE_ERROR` voter cells count as missing, not disagreement.",
        "- `agreement_rate` uses `agree / (agree + disagree)`; missing votes are excluded.",
        "- Severity calibration counts only YES votes with valid severity buckets; missing and invalid severities are reported separately.",
        "- The severity scoreboard emits a voter-side Calibration Score from the High Rate threshold excess.",
        "- False-negative YES totals include neutral and rejected eligible panels, while agreement denominators still exclude neutral panels.",
        "- This report is diagnostic only. Agreement, severity calibration, and false-negative diagnostics do not affect reviewer/proposer points, spawning, thresholds, tokens, or live panel verdicts.",
    ])
    return "\n".join(lines) + "\n"



def _resolve_realized_repo(repo_override: str) -> tuple[str, str]:
    if repo_override:
        return repo_override, ""
    repo = _resolve_incentive_repo(plugin_root)
    if repo:
        return repo, ""
    return "", "repo_unresolved"


def _repo_filtered_filed_issue_numbers(*, log_root: Path, repo: str) -> set[int]:
    numbers: set[int] = set()
    for record in iter_filed_oos_records(log_root):
        raw_number = record.get("issue_number")
        try:
            number = int(str(raw_number)) if raw_number not in (None, "") else 0
        except ValueError:
            number = 0
        issue_url = str(record.get("issue_url") or "")
        if issue_url:
            url_repo = extract_repo_from_url(issue_url)
            if url_repo and url_repo.lower() != repo.lower():
                continue
            if not number:
                match = re.search(r"/issues/(\d+)", issue_url)
                number = int(match.group(1)) if match else 0
        if number:
            numbers.add(number)
    return numbers


def _realized_outcomes_skip(reason: str) -> str:
    return "\n".join(["## Realized-outcome voter calibration", "", f"- Skipped: `{reason}`.", "- Core voter calibration metrics are still available."])


def _load_realized_outcomes_section(*, log_root: Path, repo_override: str, filed_issue_details_json: str) -> str:
    repo, repo_error = _resolve_realized_repo(repo_override)
    if repo_error:
        return _realized_outcomes_skip(repo_error)
    candidate_numbers = _repo_filtered_filed_issue_numbers(log_root=log_root, repo=repo)
    if not candidate_numbers and not filed_issue_details_json:
        return _realized_outcomes_skip("no_repo_filtered_filed_oos_candidates")
    issues: list[dict[str, object]] = []
    details: dict[int, dict[str, object]] = {}
    enrichment_degraded: str | None = None
    targeted_fetch_degraded: str | None = None
    if filed_issue_details_json:
        try:
            details = _load_filed_issue_details_json(Path(filed_issue_details_json))
        except (OSError, json.JSONDecodeError, SystemExit, ValueError) as exc:
            return _realized_outcomes_skip(f"filed_issue_details_unavailable:{type(exc).__name__}")
        issues = [dict(value) for value in details.values() if isinstance(value, Mapping)]
    else:
        dump_path = ""
        try:
            with tempfile.NamedTemporaryFile(prefix="voter-calibration-issues-", suffix=".json", delete=False) as handle:
                dump_path = handle.name
            rc = fetch_main(["--repo", repo, "--limit", "2000", "--output", dump_path])
        except FileNotFoundError:
            return _realized_outcomes_skip("gh_unavailable")
        try:
            if rc != 0:
                enrichment_degraded = "bulk_fetch_failed"
            else:
                try:
                    issues = load_issues(dump_path, lenient=False)
                except SystemExit:
                    enrichment_degraded = "bulk_load_failed"
                    issues = []
        finally:
            if dump_path:
                Path(dump_path).unlink(missing_ok=True)
        if candidate_numbers:
            try:
                details = _fetch_filed_oos_issue_details(repo=repo, issue_numbers=candidate_numbers)
            except FileNotFoundError:
                targeted_fetch_degraded = "gh_unavailable"
                details = {}
    if not issues and details:
        issues = [dict(value) for value in details.values() if isinstance(value, Mapping)]
    if not issues and not details:
        return _realized_outcomes_skip(enrichment_degraded or targeted_fetch_degraded or "insufficient_corpus")
    if details and any(value.get("__fetch_failed__") for value in details.values()):
        targeted_fetch_degraded = targeted_fetch_degraded or "targeted_fetch_failed"
    try:
        markdown, _stats = ground_truth_voter_calibration(
            issues,
            log_root=log_root,
            filed_issue_details=details,
            repo=repo,
            enrichment_degraded=enrichment_degraded,
            targeted_fetch_degraded=targeted_fetch_degraded,
            verdict_mode=False,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        return _realized_outcomes_skip(f"ground_truth_unavailable:{type(exc).__name__}")
    return markdown

def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="voter-calibration")
    parser.add_argument("--log-root", default="")
    parser.add_argument("--min-votes", type=int, default=20)
    parser.add_argument("--outlier-threshold", type=float, default=0.50)
    parser.add_argument("--high-severity-threshold", type=float, default=0.90)
    parser.add_argument("--out", default="")
    parser.add_argument("--era", choices=["all", "pre", "post"], default="")
    parser.add_argument("--era-since-date", default="")
    parser.add_argument("--realized-outcomes", action="store_true")
    parser.add_argument("--repo", default="")
    parser.add_argument("--filed-issue-details-json", default="")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    if args.era_since_date and not args.era:
        print("voter-calibration: --era-since-date requires --era", file=sys.stderr)
        return 2
    log_root = Path(args.log_root).expanduser() if args.log_root else _default_log_root()
    log_root = log_root.resolve()
    if not log_root.is_dir():
        print(f"voter-calibration: resolved log root is missing: {log_root}", file=sys.stderr)
        return 2

    discovered = _discover(log_root)
    if args.era:
        boundary_result = _resolve_era_boundary(args)
        if boundary_result.boundary is None:
            report = _render_boundary_unavailable(log_root=log_root, result=boundary_result)
        else:
            corpora, excluded_missing_started_at_runs = _collect_era_corpora(
                boundary=boundary_result.boundary,
                discovered=discovered,
            )
            realized = ""
            if args.realized_outcomes:
                realized = _load_realized_outcomes_section(
                    log_root=log_root,
                    repo_override=args.repo,
                    filed_issue_details_json=args.filed_issue_details_json,
                )
            report = _render_era_report(
                log_root=log_root,
                era=args.era,
                boundary_result=boundary_result,
                corpora=corpora,
                discovered_count=len(discovered),
                excluded_missing_started_at_runs=excluded_missing_started_at_runs,
                min_votes=args.min_votes,
                outlier_threshold=args.outlier_threshold,
                high_severity_threshold=args.high_severity_threshold,
                realized_outcomes_markdown=realized,
            )
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report, encoding="utf-8")
            print(f"REPORT_FILE={out}")
        else:
            sys.stdout.write(report)
        return 0

    stats = CorpusStats()
    for panel, path in discovered:
        _parse_file_into_stats(stats, panel=panel, path=path)

    realized = ""
    if args.realized_outcomes:
        realized = _load_realized_outcomes_section(
            log_root=log_root,
            repo_override=args.repo,
            filed_issue_details_json=args.filed_issue_details_json,
        )
    report = _render(
        log_root=log_root,
        files_seen=stats.files_seen,
        skipped_files=stats.skipped_files,
        malformed_rows=stats.malformed_rows,
        ineligible_rows=stats.ineligible_rows,
        rows=stats.rows,
        false_negative_rows=stats.false_negative_rows,
        min_votes=args.min_votes,
        outlier_threshold=args.outlier_threshold,
        high_severity_threshold=args.high_severity_threshold,
        realized_outcomes_markdown=realized,
    )
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"REPORT_FILE={out}")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
