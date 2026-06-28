# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false, reportGeneralTypeIssues=false
# ruff: noqa: F401, RET504, RUF100, S108, S607, UP035
# pylint: skip-file
"""Analyze GitHub issue JSON for backlog and process insight."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from larch.issue._ground_truth import (
    GroundTruthEvidence,
    GroundTruthMetric,
    GroundTruthOutcome,
    GroundTruthRow,
    GroundTruthSeverityMetric,
    GroundTruthStats,
    GroundTruthVoter,
    _GROUND_TRUTH_FILED_CACHE,
    _GROUND_TRUTH_ROW_CACHE,
    _candidate_evidence_for_row,
    _ground_truth_verdict_exit,
    _parse_ground_truth_min_runs,
    _parse_ground_truth_since_date,
    ground_truth_voter_calibration,
)
from larch.issue._oos import (
    _extract_legacy_stable_ids_from_ndjson_body,
    _fetch_filed_oos_issue_details,
    _ground_truth_calibration_incentive_shipped,
    _ground_truth_issue_enrichment_degraded,
    _ground_truth_run_dir_key,
    _ground_truth_targeted_fetch_degraded,
    _join_implement_run_records,
    _load_filed_issue_details_json,
    _merged_issue_index,
    _parse_oos_issues_created,
    _record_issue_urls,
    classify_oos_issue_fate,
    extract_filed_issue_number_from_text,
    extract_issue_number_from_url,
    extract_repo_from_url,
    fate_adjusted_oos_scoring,
    has_combined_away_marker,
    is_open_high_risk_oos_issue,
    issue_comments,
    issue_labels,
    iter_filed_oos_records,
    render_high_risk_oos_backlog,
)
from larch.issue._report import (
    category_breakdown,
    categorize,
    coverage_stats,
    executive_summary,
    fmt_days,
    growth_chart,
    issue_number,
    normalize_tool,
    pattern_observations,
    render_coverage,
    reviewer_effectiveness,
    title_tokens,
    wasteful_findings,
)
from larch.issue._util import (
    BODY_CAP,
    CATEGORY_PATTERNS,
    CATEGORY_RULES,
    GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS,
    GROUND_TRUTH_VERDICT_DEFAULT_SINCE_DATE,
    GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER,
    GROUND_TRUTH_VERDICT_MIN_LARCH_VERSION,
    _parse_issue_number,
    load_issues,
    parse_iso,
    pr_ref_id,
    strip_prefixes,
)

# Re-export _parse_issue_number for backward compatibility (also imported from _oos above)


def _build_analyze_report(
    issues: Sequence[Mapping[str, Any]],
    *,
    log_root: Path,
    filed_issue_details: dict[int, dict[str, Any]],
    repo: str | None = None,
    enrichment_degraded: str | None = None,
    top_k: int = 10,
    categories_mode: str = "default",
    span_days: int = 0,
) -> str:
    top_k = max(top_k, 1)
    stats = coverage_stats(issues)
    categories = categorize(issues=issues, mode=categories_mode, top_k=top_k)
    breakdown_text, category_counts = category_breakdown(issues=issues, categories=categories)
    chart_text = growth_chart(issues=issues, categories=categories, span_days=max(span_days, 0))
    patterns_text = pattern_observations(issues=issues, top_k=top_k, stats=stats)
    waste_text = wasteful_findings(issues=issues, top_k=top_k)
    reviewer_text, reviewer_stats = reviewer_effectiveness(issues)
    summary_text = executive_summary(stats=stats, category_counts=category_counts, reviewer_stats=reviewer_stats)
    sections = [
        summary_text,
        render_coverage(stats),
        breakdown_text,
        chart_text,
        patterns_text,
        waste_text,
        reviewer_text,
        render_high_risk_oos_backlog(issues, top_k=top_k),
    ]
    try:
        fate_text, _fate_stats = fate_adjusted_oos_scoring(
            issues=issues,
            log_root=log_root,
            filed_issue_details=filed_issue_details,
            repo=repo,
            enrichment_degraded=enrichment_degraded,
        )
        sections.append(fate_text)
    except Exception as exc:  # pragma: no cover - defensive live-report guard
        print(f"WARN fate-adjusted OOS scoring unavailable: {exc}", file=sys.stderr)
    try:
        ground_truth_text, _ground_truth_stats = ground_truth_voter_calibration(
            issues,
            log_root=log_root,
            filed_issue_details=filed_issue_details,
            repo=repo,
            enrichment_degraded=enrichment_degraded,
            top_k=top_k,
        )
        sections.append(ground_truth_text)
    except Exception as exc:  # pragma: no cover - defensive live-report guard
        print(f"WARN ground-truth voter calibration unavailable: {exc}", file=sys.stderr)
    return "\n\n".join(sections)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True)
    parser.add_argument("--span-days", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--categories", choices=("auto", "default"), default="default")
    parser.add_argument("--log-root", default="larch-logs")
    parser.add_argument("--repo", default="")
    parser.add_argument("--filed-issue-details-json", default="")
    parser.add_argument("--ground-truth-verdict", action="store_true")
    parser.add_argument("--since-date", default=GROUND_TRUTH_VERDICT_DEFAULT_SINCE_DATE)
    parser.add_argument("--min-runs", default=str(GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS))
    parser.add_argument("--min-larch-version", default=GROUND_TRUTH_VERDICT_MIN_LARCH_VERSION)
    parser.add_argument(
        "--lenient",
        action="store_true",
        help=(
            "Suppress the >5%% threshold abort in load_issues for non-dict, "
            "malformed-number, or duplicate-number elements. Per-element "
            "stderr warnings are still emitted; this flag only disables the "
            "threshold check."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    issues = load_issues(args.json, lenient=args.lenient)
    filed_details = _load_filed_issue_details_json(Path(args.filed_issue_details_json) if args.filed_issue_details_json else None)
    if args.ground_truth_verdict:
        return _ground_truth_verdict_exit(
            issues=issues,
            log_root=Path(args.log_root),
            filed_issue_details=filed_details,
            repo=args.repo or None,
            enrichment_degraded=_ground_truth_issue_enrichment_degraded(issues),
            targeted_fetch_degraded=_ground_truth_targeted_fetch_degraded(filed_details),
            since_date=_parse_ground_truth_since_date(args.since_date),
            min_larch_version=args.min_larch_version,
            min_runs=_parse_ground_truth_min_runs(args.min_runs),
            top_k=max(args.top_k, 1),
        )
    if not issues:
        print("No issues to analyze.")
        return 0
    print(_build_analyze_report(
        issues,
        log_root=Path(args.log_root),
        filed_issue_details=filed_details,
        repo=args.repo or None,
        top_k=max(args.top_k, 1),
        categories_mode=args.categories,
        span_days=max(args.span_days, 0),
    ))
    return 0


def analyze_main(argv: Sequence[str] | None = None) -> int:
    return main(argv)


def _write_issue_dump( *,path: Path, text: str, degraded_fields: Sequence[str] = ()) -> None:
    payload = text
    if degraded_fields:
        try:
            parsed = json.loads(text or "[]")
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        item.setdefault("_larch_degraded_fields", list(degraded_fields))
                payload = json.dumps(parsed)
        except json.JSONDecodeError:
            payload = text
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    tmp.write_text(payload, encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)
    path.chmod(0o600)


def fetch_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py analyze-issues fetch")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--limit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    output = Path(args.output)
    expanded_fields = "number,title,state,createdAt,closedAt,body,labels,closedByPullRequestsReferences,url,stateReason"
    fallback_fields = "number,title,state,createdAt,closedAt,body,labels,closedByPullRequestsReferences"
    tmp = output.with_name(output.name + f".tmp.{os.getpid()}")
    old_umask = os.umask(0o077)
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            tmp.chmod(0o600)
            expanded_cmd = [
                "gh", "issue", "list", "--repo", args.repo, "--state", "all", "--limit", args.limit,
                "--json", expanded_fields,
            ]
            result = subprocess.run(expanded_cmd, stdout=handle, text=True, check=False)
        degraded: tuple[str, ...] = ()
        if result.returncode != 0:
            with tmp.open("w", encoding="utf-8") as handle:
                tmp.chmod(0o600)
                result = subprocess.run([
                    "gh", "issue", "list", "--repo", args.repo, "--state", "all", "--limit", args.limit,
                    "--json", fallback_fields,
                ], stdout=handle, text=True, check=False)
            if result.returncode == 0:
                degraded = ("stateReason", "url")
        if result.returncode != 0:
            print(f"ERROR=gh issue list failed for repo {args.repo}", file=sys.stderr)
            tmp.unlink(missing_ok=True)
            return 1
        payload = tmp.read_text(encoding="utf-8")
        _write_issue_dump(path=output, text=payload, degraded_fields=degraded)
        return 0
    finally:
        os.umask(old_umask)
        tmp.unlink(missing_ok=True)


def _detect_repo() -> str:
    res = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], capture_output=True, text=True, check=False)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    remote = subprocess.run(["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True, check=False).stdout.strip()
    repo = re.sub(r"^git@[^:]+:", "", remote)
    repo = re.sub(r"^https?://[^/]+/", "", repo)
    repo = re.sub(r"\.git$", "", repo)
    return repo


def run_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py analyze-issues run")
    parser.add_argument("--limit", default="2000")
    parser.add_argument("--span-days", default="0")
    parser.add_argument("--top-K", "--top-k", dest="top_k", default="10")
    parser.add_argument("--categories", default="default", choices=["auto", "default"])
    parser.add_argument("--lenient", action="store_true")
    parser.add_argument("--log-root", default="larch-logs")
    parser.add_argument("--repo", default="")
    parser.add_argument("--ground-truth-verdict", action="store_true")
    parser.add_argument("--since-date", default=GROUND_TRUTH_VERDICT_DEFAULT_SINCE_DATE)
    parser.add_argument("--min-runs", default=str(GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS))
    parser.add_argument("--min-larch-version", default=GROUND_TRUTH_VERDICT_MIN_LARCH_VERSION)
    args = parser.parse_args(list(argv) if argv is not None else None)
    repo = args.repo or _detect_repo()
    repo_valid = bool(re.fullmatch(r"[^/]+/[^/]+", repo or ""))
    if not repo_valid:
        print("WARN targeted comment fetch unavailable: unable to detect GitHub repo owner/name", file=sys.stderr)
        repo = ""
    repo_resolved = repo_valid
    enrichment_degraded: str | None = "repo_unavailable" if not repo_resolved else None
    issues: list[dict[str, Any]] = []
    if repo_resolved:
        sanitized = re.sub(r"[^A-Za-z0-9_-]", "", repo.replace("/", "-"))
        if not sanitized:
            print(f"WARN bulk issue fetch skipped: sanitized repo name is empty (REPO='{repo}')", file=sys.stderr)
            repo_resolved = False
            repo = ""
        else:
            dump = Path(os.environ.get("TMPDIR", "/tmp")) / f"{sanitized}-issues.json"
            old_umask = os.umask(0o077)
            try:
                rc = fetch_main(["--repo", repo, "--limit", args.limit, "--output", str(dump)])
            finally:
                os.umask(old_umask)
            if rc != 0:
                print("WARN bulk gh issue list failed; continuing with log-only fate scoring", file=sys.stderr)
                enrichment_degraded = enrichment_degraded or "bulk_fetch_failed"
            else:
                try:
                    issues = load_issues(str(dump), lenient=args.lenient)
                except SystemExit:
                    print("WARN corrupt issue dump; continuing with log-only fate scoring", file=sys.stderr)
                    issues = []
                    enrichment_degraded = enrichment_degraded or "bulk_fetch_failed"
    if not repo_resolved:
        repo = ""
    issue_enrichment_degraded = _ground_truth_issue_enrichment_degraded(issues)
    if issue_enrichment_degraded:
        enrichment_degraded = enrichment_degraded or issue_enrichment_degraded
    log_root = Path(args.log_root)
    candidate_numbers: set[int] = set()
    for record in iter_filed_oos_records(log_root):
        parsed_number, _reason = _parse_issue_number(record.get("issue_number"))
        if parsed_number is None:
            continue
        issue_url = str(record.get("issue_url") or "")
        if repo and issue_url:
            url_repo = extract_repo_from_url(issue_url)
            if url_repo and url_repo.lower() != repo.lower():
                continue
        candidate_numbers.add(int(parsed_number))
    details: dict[int, dict[str, Any]] = {}
    if candidate_numbers and repo:
        details = _fetch_filed_oos_issue_details(repo=repo, issue_numbers=candidate_numbers)
    targeted_fetch_degraded = _ground_truth_targeted_fetch_degraded(details)
    top_k = max(int(args.top_k), 1) if str(args.top_k).isdigit() else 10
    span_days = max(int(args.span_days), 0) if str(args.span_days).isdigit() else 0
    if args.ground_truth_verdict:
        return _ground_truth_verdict_exit(
            issues=issues,
            log_root=log_root,
            filed_issue_details=details,
            repo=repo or None,
            enrichment_degraded=enrichment_degraded,
            targeted_fetch_degraded=targeted_fetch_degraded,
            since_date=_parse_ground_truth_since_date(args.since_date),
            min_larch_version=args.min_larch_version,
            min_runs=_parse_ground_truth_min_runs(args.min_runs),
            top_k=top_k,
        )
    print(_build_analyze_report(
        issues,
        log_root=log_root,
        filed_issue_details=details,
        repo=repo,
        enrichment_degraded=enrichment_degraded,
        top_k=top_k,
        categories_mode=args.categories,
        span_days=span_days,
    ))
    return 0
