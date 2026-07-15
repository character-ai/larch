# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportPossiblyUnboundVariable=false, reportMissingParameterType=false, reportArgumentType=false, reportUnknownLambdaType=false
# ruff: noqa: C901, FB504, PLR0911, PLR0912, PLR0913, PLR0915
# pylint: skip-file
"""Tiered low-cost verification of closed ``[BUG]`` fixes.

This module backs the dev-only ``/analyze-bugs`` skill. It deliberately keeps
GitHub and git access behind the ``larch.core.proc.Runner`` seam so unit tests
can exercise the workflow offline.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import json
import os
import random
import re
import secrets
import sys
import time
from collections import OrderedDict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Final, cast

from larch.core import config, proc
from larch.core.proc import Runner
from larch.errors import ShipError
from larch.git import gh
from larch.issue.title_match import bug_title_match
from larch.issue.issue_wire import strip_named_block
from larch.report.report_tokens_cost import rate_row

DEFAULT_DIFF_CAP: Final = 60_000
DEFAULT_BODY_CAP: Final = 8_000
GIT_LOG_SCAN_LIMITS: Final = (100, 200, 400, 800, 1600, 3200)
TRIAGE_VERDICTS: Final = set(config.ANALYZE_BUGS_TRIAGE_VERDICTS)
DEEP_VERDICTS: Final = set(config.ANALYZE_BUGS_DEEP_VERDICTS)
MECHANICAL_VERDICTS: Final = {"NOT_FIXED", "WONTFIX", "NEEDS_DEEP"}
TERMINAL_FOLLOWUP_VERDICTS: Final = {"NOT_FIXED", "INCOMPLETE", "REGRESSED"}
PLAN_MALFORMED_REASON: Final = "malformed larch:plan block"
EVIDENCE_TOKEN_LABEL: Final = "evidence_token"
EVIDENCE_TOKEN_PATTERN: Final = re.compile(r"^evidence_token: (\S+)$")
EVIDENCE_TOKEN_SCAN_LINES: Final = 20
NO_INTRODUCED_RISK: Final = "none found"
SIBLING_SITE_RE: Final = re.compile(r"^[^:\s]+:[A-Za-z_][A-Za-z0-9_]*$")
SCAN_REASON_CAP: Final = 500
SCAN_OK: Final = "ok"
SCAN_FAILED: Final = "failed"
SCAN_NOT_RUN: Final = "not-run"
GREP_LINE_FIELDS: Final = 3
GREP_LINE_WITH_REF_FIELDS: Final = 4
LEGACY_TRIAGE_WARN_LIMIT: Final = 20
HISTORICAL_MARKER_BACKFILL_LIMIT: Final = 50
PYTHON_ZONE_PARTS: Final = 3
GENERAL_ZONE_PARTS: Final = 2
NUMSTAT_FIELDS: Final = 3
CHURN_COMMIT_THRESHOLD: Final = 3
CHRONIC_BUG_THRESHOLD: Final = 3
CHAIN_MEMBER_THRESHOLD: Final = 2
LARGE_FIX_ADDED_LINES: Final = 300
ANALYTICS_METADATA_VERSION: Final = 1
DAY_SECONDS: Final = 86_400
MARKER_PHRASE_RE: Final = re.compile(
    r"(?i)(?:incomplete|persists\s+after|residual|regression\s+from|after\s+the)"
)
ISSUE_REFERENCE_RE: Final = re.compile(r"(?<![A-Za-z0-9])#([1-9][0-9]*)")
BASELINE_PATH_RE: Final = re.compile(r"^python/[^/]+-baseline\.json$")
VERIFIED_PREDICATE_VERSION: Final = "final-tier-non-pending-v1"
SWEEP_SCHEMA_VERSION: Final = 1
SWEEP_DEFAULT_MAX: Final = 20
SWEEP_INITIAL_WINDOW_SECONDS: Final = 48 * 60 * 60
SWEEP_DIFF_CAP: Final = DEFAULT_DIFF_CAP
SWEEP_SYMBOL_CAP: Final = 40
SWEEP_CONSUMER_CAP: Final = 40
PREFETCH_CONSUMER_CAP: Final = SWEEP_CONSUMER_CAP
CONSUMER_EXCLUDED_PATHS: Final = ("larch-logs",)
GIT_LOG_PATHSPEC_BYTES_CAP: Final = 32_768
SWEEP_STATE_FILENAME: Final = "sweep-state.json"
SWEEP_FINDER_RAW_NAME: Final = "sweep-finder.jsonl"
SWEEP_REFUTER_RAW_NAME: Final = "sweep-refuter.jsonl"
SWEEP_REFUTER_QUEUE_NAME: Final = "sweep-refuter-queue.jsonl"
SWEEP_VALIDATED_NAME: Final = "sweep-validated.json"
SWEEP_SELECTED_MANIFEST_NAME: Final = "sweep-selected-merges.json"
SWEEP_BUNDLE_MANIFEST_NAME: Final = "sweep-bundle-paths.json"
SWEEP_PREPARE_SUMMARY_NAME: Final = "sweep-prepare.json"
SWEEP_SEVERITIES: Final = ("high", "medium", "low")
SWEEP_CONFIDENCES: Final = ("high", "medium", "low")
SWEEP_REFUTER_VERDICTS: Final = ("survives", "refuted")
SWEEP_FINDINGS_PER_MERGE_CAP: Final = 10
SWEEP_FINDING_FILE_CAP: Final = 512
SWEEP_FINDING_SYMBOL_CAP: Final = 200
SWEEP_FINDING_DESC_CAP: Final = 2000
SWEEP_PRINTABLE_MIN: Final = 0x20
SWEEP_LOG_FIELDS: Final = 3
SWEEP_FINDER_OUTPUT_TOKENS: Final = 400
SWEEP_REFUTER_OUTPUT_TOKENS: Final = 80
FULL_SHA_RE: Final = re.compile(r"^[0-9a-f]{40}$")
SWEEP_TIMESTAMP_RE: Final = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SWEEP_FLUSH_SUBJECT_RE: Final = re.compile(r"^chore\(larch-logs\)")
SWEEP_RELEASE_SUBJECT_RE: Final = re.compile(r"^Release v")
SWEEP_PY_DEF_RE: Final = re.compile(r"^\+\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
SWEEP_PY_CLASS_RE: Final = re.compile(r"^\+\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*[:(]")
SWEEP_PY_CONST_RE: Final = re.compile(r"^\+\s*([A-Z][A-Z0-9_]{2,})\s*=")
DIFF_FUNCTION_SYMBOL_RE: Final = re.compile(r"^[+-]\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
DIFF_FIELD_SYMBOL_RE: Final = re.compile(r"^[+-]\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?!=)")
DIFF_DICT_SUBSCRIPT_SYMBOL_RE: Final = re.compile(r"\[\s*(['\"])([A-Za-z_][A-Za-z0-9_-]*)\1\s*\]")
DIFF_DICT_LITERAL_SYMBOL_RE: Final = re.compile(r"(?:^|[,{]\s*)(['\"])([A-Za-z_][A-Za-z0-9_-]*)\1\s*:")


@dataclass(frozen=True)
class IssueRecord:
    number: int
    title: str
    state: str
    state_reason: str
    body: str
    url: str
    closed_at: str
    closed_by_pull_requests: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class FixEvidence:
    issue_number: int
    fix_sha: str
    source: str
    ambiguous: bool = False
    reason: str = ""


@dataclass(frozen=True)
class ScanResult:
    """Outcome of a required local evidence scan."""

    status: str
    stdout: str = ""
    reason: str = ""

    @property
    def complete(self) -> bool:
        return self.status == SCAN_OK


@dataclass(frozen=True)
class BundleRecord:
    issue_number: int
    title: str
    state: str
    state_reason: str
    url: str
    body_path: str
    bundle_path: str
    fix_sha: str
    fix_source: str
    touched_files: tuple[str, ...]
    later_history_hash: str
    mechanical_verdict: str
    mechanical_reason: str
    cache_key: str
    sampled: bool = False
    fix_time: int = 0
    added_lines: int = 0
    marker_references: tuple[int, ...] = ()
    marker_fingerprint: str = ""
    zones: tuple[str, ...] = ()
    baseline_extended: bool = False
    changed_symbols: tuple[str, ...] = ()
    consumer_paths: tuple[str, ...] = ()
    consumer_references: tuple[str, ...] = ()
    consumers_truncated: bool = False
    scan_files: tuple[str, ...] = ()
    diff_scan_status: str = SCAN_OK
    diff_scan_reason: str = ""
    consumer_scan_status: str = SCAN_OK
    consumer_scan_reason: str = ""
    later_history_scan_status: str = SCAN_OK
    later_history_scan_reason: str = ""
    revert_scan_status: str = SCAN_OK
    revert_scan_reason: str = ""

    @property
    def required_evidence_complete(self) -> bool:
        return all(
            status == SCAN_OK
            for status in (
                self.diff_scan_status,
                self.consumer_scan_status,
                self.later_history_scan_status,
                self.revert_scan_status,
            )
        )


@dataclass(frozen=True)
class RunManifest:
    schema_version: str
    repo: str
    run_id: str
    run_dir: str
    evidence_ref: str
    bugs_requested: int
    bugs_selected: int
    generated_at: int
    ledger_path: str
    triage_batch_paths: tuple[str, ...]
    deep_queue_path: str
    issues: tuple[BundleRecord, ...]


@dataclass(frozen=True)
class LedgerRecord:
    cache_key: str
    issue: int
    fix_sha: str
    later_history_hash: str
    triage_verdict: str = ""
    triage_reason: str = ""
    triage_missing_items: tuple[str, ...] = ()
    triage_needs_deep: bool = False
    triage_evidence_verified: bool = False
    triage_introduced_risk: str = ""
    triage_introduced_risk_reason: str = ""
    deep_verdict: str = ""
    deep_reason: str = ""
    deep_introduced_risk: str = ""
    deep_introduced_risk_reason: str = ""
    class_complete: bool = False
    sibling_sites: tuple[str, ...] = ()
    legacy_schema: bool = True
    sampled: bool = False
    stages_complete: tuple[str, ...] = ()
    updated_at: int = 0
    touched_files: tuple[str, ...] = ()
    fix_time: int = 0
    added_lines: int = 0
    marker_references: tuple[int, ...] = ()
    marker_fingerprint: str = ""
    zones: tuple[str, ...] = ()
    baseline_extended: bool = False
    metadata_version: int = 0


@dataclass(frozen=True)
class TriageIngest:
    issue: int
    verdict: str
    missing_items: tuple[str, ...]
    reason: str
    needs_deep: bool
    evidence_token: str
    introduced_risk: str = ""
    introduced_risk_reason: str = ""
    legacy_schema: bool = True


@dataclass(frozen=True)
class DeepIngest:
    issue: int
    verdict: str
    reason: str
    introduced_risk: str = ""
    introduced_risk_reason: str = ""
    class_complete: bool = False
    sibling_sites: tuple[str, ...] = ()
    legacy_schema: bool = True


@dataclass(frozen=True)
class EvidenceTokenLookup:
    token: str = ""
    error: str = ""


@dataclass(frozen=True)
class ReportCounts:
    total: int = 0
    confirmed_fixed: int = 0
    needs_deep: int = 0
    not_fixed: int = 0
    incomplete: int = 0
    regressed: int = 0
    wontfix: int = 0
    unverifiable: int = 0


@dataclass(frozen=True)
class AnalyticsCorpusRecord:
    record: LedgerRecord
    append_ordinal: int


@dataclass(frozen=True)
class ChainEdge:
    from_issue: int
    to_issue: int
    detector_kind: str

    @property
    def identity(self) -> str:
        return f"{self.from_issue}>{self.to_issue}:{self.detector_kind}"


@dataclass(frozen=True)
class AnalyticsRecord:
    issue: int
    cache_key: str
    fix_sha: str
    touched_files: tuple[str, ...]
    fix_time: int
    added_lines: int
    marker_references: tuple[int, ...]
    marker_fingerprint: str
    zones: tuple[str, ...]
    baseline_extended: bool
    ledger_record: LedgerRecord | None = None
    bundle: BundleRecord | None = None


@dataclass(frozen=True)
class ChronicZone:
    zone: str
    issues: tuple[int, ...]
    churned_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnalyticsView:
    records: tuple[AnalyticsRecord, ...]
    chain_edges: tuple[ChainEdge, ...]
    chronic_zones: tuple[ChronicZone, ...]
    churned_files: tuple[str, ...]
    baseline_issues: tuple[int, ...]
    hydrated_records: tuple[LedgerRecord, ...] = ()


@dataclass(frozen=True)
class RunSnapshot:
    schema_version: str
    repo: str
    run_id: str
    generated_at: int
    selected_issues: tuple[int, ...]
    verified_issues: tuple[int, ...]
    chronic_zones: tuple[str, ...]
    chain_edges: tuple[str, ...]
    verified_predicate: str = VERIFIED_PREDICATE_VERSION


@dataclass(frozen=True)
class SweepState:
    last_sweep_sha: str
    last_sweep_at: str
    schema_version: int
    pending_shas: tuple[str, ...]


@dataclass(frozen=True)
class SweepPendingEntry:
    sha: str


@dataclass(frozen=True)
class SweepCommit:
    merge_sha: str
    base_sha: str
    subject: str
    touched_paths: tuple[str, ...]
    diff_size: int
    capped_diff: str
    diff_truncated: bool
    changed_symbols: tuple[str, ...]
    symbols_truncated: bool
    chronic_zones: tuple[str, ...]
    is_chronic: bool
    history_order: int
    commit_time: int


@dataclass(frozen=True)
class SweepConsumerHit:
    path: str
    line: int
    text: str


@dataclass(frozen=True)
class SweepBundle:
    pinned_tip: str
    merge_sha: str
    base_sha: str
    subject: str
    touched_files: tuple[str, ...]
    chronic_tags: tuple[str, ...]
    capped_diff: str
    truncation_notices: tuple[str, ...]
    changed_symbols: tuple[str, ...]
    consumers: tuple[SweepConsumerHit, ...]
    consumers_truncated: bool
    bundle_path: str


@dataclass(frozen=True)
class SweepFinding:
    file: str
    symbol: str
    description: str
    severity: str
    confidence: str


@dataclass(frozen=True)
class SweepFinderRow:
    merge_sha: str
    findings: tuple[SweepFinding, ...]


@dataclass(frozen=True)
class SweepRefutationResult:
    merge_sha: str
    finding_index: int
    verdict: str


@dataclass(frozen=True)
class SweepRefuterQueueRow:
    merge_sha: str
    finding_index: int
    file: str
    symbol: str
    description: str
    severity: str
    confidence: str


@dataclass(frozen=True)
class SweepCandidate:
    merge_sha: str
    file: str
    symbol: str
    description: str
    severity: str
    confidence: str


@dataclass(frozen=True)
class SweepValidatedArtifact:
    pinned_tip: str
    selected_manifest_path: str
    selected_count: int
    skipped_count: int
    pending_shas: tuple[str, ...]
    coverage_incomplete: bool
    candidates: tuple[SweepCandidate, ...]


@dataclass(frozen=True)
class SweepEnumerationResult:
    pinned_tip: str
    selected: tuple[SweepCommit, ...]
    pending_shas: tuple[str, ...]
    skipped_count: int
    coverage_incomplete: bool
    state_path: Path
    chronic_zone_names: tuple[str, ...]


class AnalyzeBugsError(RuntimeError):
    """Raised for operator-visible analyze-bugs failures."""


def _runner() -> Runner:
    return proc.ProcRunner()


def _fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _positive_int(value: str, *, name: str) -> int:
    if not value.isdecimal() or int(value) <= 0:
        raise argparse.ArgumentTypeError(f"{name} must be a positive integer")
    return int(value)


def _sanitize_repo_slug(repo: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", repo.strip().replace("/", "-"))
    return slug.strip(".-") or "unknown-repo"


def _cache_root(explicit: str = "") -> Path:
    if explicit:
        return Path(explicit).expanduser()
    base = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
    return base / "larch" / config.ANALYZE_BUGS_CACHE_DIR_NAME


def _private_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        path.chmod(0o700)


def _atomic_write_text(path: Path, text: str, *, mode: int = 0o600) -> None:
    _private_mkdir(path.parent)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    old_umask = os.umask(0o177)
    try:
        tmp.write_text(text, encoding="utf-8")
        with contextlib.suppress(OSError):
            tmp.chmod(mode)
        tmp.replace(path)
    finally:
        os.umask(old_umask)
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _append_private_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    _private_mkdir(path.parent)
    old_umask = os.umask(0o177)
    try:
        with path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(dict(row), sort_keys=True) + "\n")
    finally:
        os.umask(old_umask)
    with contextlib.suppress(OSError):
        path.chmod(0o600)


def _json_default(value: object) -> object:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, default=_json_default, indent=2, sort_keys=True) + "\n")


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AnalyzeBugsError(f"expected JSON object in {path}")
    return cast("dict[str, Any]", data)


def _emit_kvs(kvs: Mapping[str, object]) -> None:
    for key, value in kvs.items():
        if isinstance(value, (list, tuple)):
            rendered = ",".join(str(item) for item in value)
        else:
            rendered = str(value)
        print(f"{key}={rendered}")


def _parse_json_object(stdout: str, *, desc: str) -> dict[str, Any]:
    try:
        data = json.loads(stdout or "{}")
    except json.JSONDecodeError as exc:
        raise AnalyzeBugsError(f"{desc}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AnalyzeBugsError(f"{desc}: JSON was not an object")
    return cast("dict[str, Any]", data)


def resolve_repo(runner: Runner, explicit: str = "") -> str:
    if explicit:
        return explicit
    resolved = gh.resolve_repo(runner)
    if not resolved:
        raise AnalyzeBugsError("could not resolve GitHub repo; pass --repo OWNER/REPO")
    return resolved


def resolve_evidence_ref(runner: Runner) -> str:
    fetch = runner.run(["git", "fetch", "origin", "main"])
    origin = runner.run(["git", "rev-parse", "--verify", "origin/main"])
    if fetch.returncode == 0 and origin.returncode == 0:
        return "origin/main"
    local = runner.run(["git", "rev-parse", "--verify", "main"])
    if local.returncode == 0:
        print("WARN: using local main as evidence ref because origin/main could not be refreshed", file=sys.stderr)
        return "main"
    raise AnalyzeBugsError("could not resolve evidence ref from origin/main or local main")


def _issue_from_raw(raw: Mapping[str, Any]) -> IssueRecord | None:
    if raw.get("pull_request") is not None:
        return None
    number_raw = raw.get("number")
    if isinstance(number_raw, bool):
        return None
    try:
        number = int(number_raw)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    pr_refs = _closed_pr_refs_from_raw(raw)
    return IssueRecord(
        number=number,
        title=str(raw.get("title") or ""),
        state=str(raw.get("state") or ""),
        state_reason=str(raw.get("stateReason") or raw.get("state_reason") or ""),
        body=str(raw.get("body") or ""),
        url=str(raw.get("url") or raw.get("html_url") or ""),
        closed_at=str(raw.get("closedAt") or raw.get("closed_at") or ""),
        closed_by_pull_requests=pr_refs,
    )


def _closed_pr_refs_from_raw(raw: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    pr_refs_raw = raw.get("closedByPullRequestsReferences")
    if isinstance(pr_refs_raw, list):
        return tuple(cast("dict[str, Any]", item) for item in pr_refs_raw if isinstance(item, dict))
    if isinstance(pr_refs_raw, dict) and isinstance(pr_refs_raw.get("nodes"), list):
        return tuple(cast("dict[str, Any]", item) for item in pr_refs_raw["nodes"] if isinstance(item, dict))
    return ()


_BUG_ISSUE_LIST_FIELDS: Final = (
    "number",
    "title",
    "state",
    "stateReason",
    "body",
    "url",
    "closedAt",
    "closedByPullRequestsReferences",
)


def _issue_pr_refs_argv(repo: str, *, issue_number: int) -> list[str]:
    return [
        "issue",
        "view",
        str(issue_number),
        "--repo",
        repo,
        "--json",
        "closedByPullRequestsReferences",
    ]


def fetch_bug_issues(runner: Runner, *, repo: str, count: int) -> tuple[list[IssueRecord], int]:
    if count <= 0:
        return [], 0
    selected: list[IssueRecord] = []
    last_corpus_len = 0
    try:
        listed = gh.issue_list_read(
            runner,
            repo=repo,
            state="all",
            fields=_BUG_ISSUE_LIST_FIELDS,
            limit=100000,
        )
    except ShipError as exc:
        raise AnalyzeBugsError(f"gh issue list failed: {exc}") from exc
    raw_rows = [row for row in listed if isinstance(row, dict)]
    last_corpus_len = len(raw_rows)
    for row in raw_rows:
        issue = _issue_from_raw(cast("Mapping[str, Any]", row))
        if issue is None:
            continue
        if bug_title_match(issue.title):
            selected.append(issue)
            if len(selected) >= count:
                return selected[:count], last_corpus_len
    return selected[:count], last_corpus_len


def _exact_issue_reference_re(issue: int) -> re.Pattern[str]:
    return re.compile(rf"(?<!\d)#{issue}(?!\d)")


def _records_from_git_log(stdout: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    if "\x1e" in stdout or "\x1f" in stdout:
        for raw_record in stdout.split("\x1e"):
            record = raw_record.strip("\n")
            if not record:
                continue
            parts = record.split("\x1f", 1)
            sha = parts[0].strip().splitlines()[0] if parts else ""
            message = parts[1] if len(parts) > 1 else record
            if sha:
                records.append((sha, message))
        return records
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(maxsplit=1)
        sha = parts[0]
        message = parts[1] if len(parts) > 1 else stripped
        records.append((sha, message))
    return records


def find_fix_by_git_log(runner: Runner, *, issue: int, evidence_ref: str) -> FixEvidence:
    # git log returns newest reachable commits first. The cache key therefore
    # pins the newest exact `Fixes #N` commit, plus later touched-file history,
    # so a newer refix or regression changes `fix_sha` or `later_history_hash`.
    result = runner.run([
        "git",
        "log",
        evidence_ref,
        "--regexp-ignore-case",
        "--grep",
        f"Fixes #{issue}",
        "--format=%H%x1f%B%x1e",
    ])
    if result.returncode != 0:
        return FixEvidence(issue, "", "git-log", reason="git log failed")
    exact = _exact_issue_reference_re(issue)
    for sha, message in _records_from_git_log(result.stdout):
        if exact.search(message):
            return FixEvidence(issue, sha, "git-log")
    return FixEvidence(issue, "", "git-log", reason="no exact Fixes reference")


def _pr_number_from_ref(ref: Mapping[str, Any]) -> str:
    for key in ("number", "id"):
        value = ref.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value > 0:
            return str(value)
        if isinstance(value, str) and value.isdecimal() and int(value) > 0:
            return value
    url = str(ref.get("url") or "")
    match = re.search(r"/pull/(\d+)(?:\D*)$", url)
    return match.group(1) if match else ""


def _merge_commit_sha(data: Mapping[str, Any]) -> str:
    merge = data.get("mergeCommit")
    if isinstance(merge, dict):
        oid = merge.get("oid") or merge.get("sha")
        return str(oid or "")
    if isinstance(merge, str):
        return merge
    return ""


def find_fix_by_pr_refs(runner: Runner, *, issue: IssueRecord, repo: str) -> FixEvidence:
    shas: list[str] = []
    refs = issue.closed_by_pull_requests
    if not refs and repo and issue.number > 0:
        result = gh.command(runner, _issue_pr_refs_argv(repo, issue_number=issue.number))
        if result.returncode == 0:
            try:
                refs = _closed_pr_refs_from_raw(_parse_json_object(result.stdout, desc="gh issue view"))
            except AnalyzeBugsError:
                refs = ()
    for ref in refs:
        pr_number = _pr_number_from_ref(ref)
        if not pr_number:
            continue
        result = gh.pr_view_field_read(runner, pr_number, "mergeCommit", repo=repo)
        if result.returncode != 0:
            continue
        try:
            data = _parse_json_object(result.stdout, desc="gh pr view")
        except AnalyzeBugsError:
            continue
        sha = _merge_commit_sha(data)
        if sha:
            shas.append(sha)
    unique = list(OrderedDict((sha, None) for sha in shas).keys())
    if len(unique) == 1:
        return FixEvidence(issue.number, unique[0], "closedByPullRequestsReferences")
    if len(unique) > 1:
        return FixEvidence(issue.number, "", "closedByPullRequestsReferences", ambiguous=True, reason="multiple PR merge commits")
    return FixEvidence(issue.number, "", "closedByPullRequestsReferences", reason="no PR merge commit")


def _validate_local_fix_sha(runner: Runner, fix: FixEvidence, *, evidence_ref: str) -> FixEvidence:
    if not fix.fix_sha:
        return fix
    result = runner.run(["git", "cat-file", "-e", f"{fix.fix_sha}^{{commit}}"])
    if result.returncode == 0:
        reachability = runner.run(["git", "merge-base", "--is-ancestor", fix.fix_sha, evidence_ref])
        if reachability.returncode == 0:
            return fix
        detail = (reachability.stderr or reachability.stdout or f"commit {fix.fix_sha} is not reachable from {evidence_ref}").strip()
        reason = f"{fix.source}: {detail}" if detail else fix.source
        return FixEvidence(fix.issue_number, "", fix.source, ambiguous=fix.ambiguous, reason=reason)
    detail = (result.stderr or result.stdout or f"commit {fix.fix_sha} is unavailable locally").strip()
    reason = f"{fix.source}: {detail}" if detail else fix.source
    return FixEvidence(fix.issue_number, "", fix.source, ambiguous=fix.ambiguous, reason=reason)


def resolve_fix_evidence(runner: Runner, *, issue: IssueRecord, repo: str, evidence_ref: str) -> FixEvidence:
    fix = find_fix_by_git_log(runner, issue=issue.number, evidence_ref=evidence_ref)
    if fix.fix_sha:
        return _validate_local_fix_sha(runner, fix, evidence_ref=evidence_ref)
    if issue.state.upper() == "OPEN":
        return fix
    pr_fix = find_fix_by_pr_refs(runner, issue=issue, repo=repo)
    if pr_fix.fix_sha:
        return _validate_local_fix_sha(runner, pr_fix, evidence_ref=evidence_ref)
    if pr_fix.ambiguous:
        return pr_fix
    return fix


def _strip_plan(body: str) -> tuple[str, str]:
    stripped, malformed = strip_named_block(body=body, marker="plan")
    if malformed:
        return "", malformed
    return stripped, ""


def _mechanical_verdict(issue: IssueRecord, *, fix: FixEvidence, strip_malformed: str) -> tuple[str, str]:
    if issue.state.upper() == "OPEN":
        return "NOT_FIXED", "issue is still open"
    if issue.state_reason.upper() == "NOT_PLANNED":
        return "WONTFIX", "issue was closed as not planned"
    if strip_malformed:
        return "NEEDS_DEEP", f"{PLAN_MALFORMED_REASON}: {strip_malformed}"
    if not fix.fix_sha:
        reason = fix.reason or "closed issue has no traceable unique fix commit"
        return "NEEDS_DEEP", reason
    return "", ""


def _git_stdout(runner: Runner, argv: Sequence[str]) -> str:
    result = runner.run(argv)
    if result.returncode != 0:
        return ""
    return result.stdout


def _scan_failure_reason(*, description: str, stdout: str, stderr: str) -> str:
    detail = stderr.strip() or stdout.strip() or "command returned a non-zero exit status"
    normalized = re.sub(r"\s+", " ", detail)
    return f"{description}: {normalized[:SCAN_REASON_CAP]}"


def _required_git_scan(runner: Runner, argv: Sequence[str], *, description: str, no_match_ok: bool = False) -> ScanResult:
    """Run a required evidence command without collapsing failures into absence."""
    result = runner.run(argv)
    if result.returncode == 0 or (no_match_ok and result.returncode == 1):
        return ScanResult(status=SCAN_OK, stdout=result.stdout)
    return ScanResult(
        status=SCAN_FAILED,
        stdout=result.stdout,
        reason=_scan_failure_reason(description=description, stdout=result.stdout, stderr=result.stderr),
    )


def zone_for_path(path: str) -> str:
    """Map a repository-relative path to its stable analytics zone."""
    parts = [part for part in Path(path).parts if part not in {"", "."}]
    if not parts:
        return ""
    first = parts[0]
    if len(parts) >= PYTHON_ZONE_PARTS and parts[:GENERAL_ZONE_PARTS] == ["python", "larch"]:
        return "/".join(parts[:PYTHON_ZONE_PARTS])
    if first in {"scripts", "docs"}:
        return first
    if len(parts) >= GENERAL_ZONE_PARTS:
        return "/".join(parts[:GENERAL_ZONE_PARTS])
    return first


def _zones_for_files(files: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({zone for path in files if (zone := zone_for_path(path))}))


def _marker_evidence(title: str, body: str) -> tuple[tuple[int, ...], str]:
    text = f"{title}\n{body}"
    fingerprint = hashlib.sha256(text.encode()).hexdigest()
    if not MARKER_PHRASE_RE.search(text):
        return (), ""
    references = tuple(sorted({int(match.group(1)) for match in ISSUE_REFERENCE_RE.finditer(text)}))
    return (references, fingerprint) if references else ((), "")


def _fix_metadata(runner: Runner, *, fix_sha: str) -> tuple[int, int]:
    if not fix_sha:
        return 0, 0
    timestamp = _git_stdout(runner, ["git", "show", "-s", "--format=%ct", fix_sha]).strip()
    try:
        fix_time = int(timestamp)
    except ValueError:
        fix_time = 0
    numstat = _git_stdout(runner, ["git", "show", "--numstat", "--format=", fix_sha])
    added_lines = 0
    for line in numstat.splitlines():
        fields = line.split("	", 2)
        if len(fields) == NUMSTAT_FIELDS and fields[0].isdecimal():
            added_lines += int(fields[0])
    return fix_time, added_lines


def _baseline_extended(files: Sequence[str]) -> bool:
    return any(BASELINE_PATH_RE.fullmatch(path) for path in files)


def _touched_files(runner: Runner, *, fix_sha: str) -> tuple[str, ...]:
    if not fix_sha:
        return ()
    out = _git_stdout(runner, ["git", "show", "--name-only", "--format=", fix_sha])
    files = []
    for line in out.splitlines():
        stripped = line.strip()
        if stripped and stripped not in files:
            files.append(stripped)
    return tuple(files)


def _pathspec_batches(files: Sequence[str]) -> tuple[tuple[str, ...], ...]:
    """Split pathspecs into argv-safe batches without losing input order."""
    batches: list[tuple[str, ...]] = []
    batch: list[str] = []
    batch_bytes = 0
    for path in dict.fromkeys(files):
        path_bytes = len(path.encode()) + 1
        if batch and batch_bytes + path_bytes > GIT_LOG_PATHSPEC_BYTES_CAP:
            batches.append(tuple(batch))
            batch = []
            batch_bytes = 0
        batch.append(path)
        batch_bytes += path_bytes
    if batch:
        batches.append(tuple(batch))
    return tuple(batches)


def _history_scan(
    runner: Runner,
    *,
    fix_sha: str,
    evidence_ref: str,
    files: Sequence[str],
    description: str,
    revert_only: bool = False,
) -> ScanResult:
    if not fix_sha:
        return ScanResult(status=SCAN_NOT_RUN, reason="fix SHA is unavailable")
    if not files:
        return ScanResult(status=SCAN_OK)
    batches = _pathspec_batches(files)
    if len(batches) == 1:
        argv = ["git", "log", f"{fix_sha}..{evidence_ref}"]
        if revert_only:
            argv.extend(("--regexp-ignore-case", "--grep", "revert"))
        argv.extend(("--format=%H:%s", "--", *batches[0]))
        return _required_git_scan(runner, argv, description=description)
    output_lines: list[str] = []
    seen_lines: set[str] = set()
    for batch in batches:
        argv = ["git", "log", f"{fix_sha}..{evidence_ref}"]
        if revert_only:
            argv.extend(("--regexp-ignore-case", "--grep", "revert"))
        argv.extend(("--format=%H:%s", "--", *batch))
        scan = _required_git_scan(runner, argv, description=description)
        if not scan.complete:
            return scan
        for line in scan.stdout.splitlines():
            if line not in seen_lines:
                seen_lines.add(line)
                output_lines.append(line)
    return ScanResult(status=SCAN_OK, stdout="\n".join(output_lines) + ("\n" if output_lines else ""))


def _later_history(runner: Runner, *, fix_sha: str, evidence_ref: str, files: Sequence[str]) -> ScanResult:
    return _history_scan(
        runner,
        fix_sha=fix_sha,
        evidence_ref=evidence_ref,
        files=files,
        description="later-history scan failed",
    )


def _revert_scan(runner: Runner, *, fix_sha: str, evidence_ref: str, files: Sequence[str]) -> ScanResult:
    return _history_scan(
        runner,
        fix_sha=fix_sha,
        evidence_ref=evidence_ref,
        files=files,
        description="revert scan failed",
        revert_only=True,
    )


def _changed_symbols(diff: str) -> tuple[str, ...]:
    symbols: set[str] = set()
    for line in diff.splitlines():
        if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
            continue
        for pattern in (DIFF_FUNCTION_SYMBOL_RE, DIFF_FIELD_SYMBOL_RE):
            match = pattern.match(line)
            if match:
                symbols.add(match.group(1))
        for pattern in (DIFF_DICT_SUBSCRIPT_SYMBOL_RE, DIFF_DICT_LITERAL_SYMBOL_RE):
            for match in pattern.finditer(line):
                symbols.add(match.group(2))
    return tuple(sorted(symbols))


def _consumer_line(line: str) -> tuple[str, int] | None:
    fields = line.split(":", 3)
    if len(fields) >= GREP_LINE_FIELDS and fields[1].isdecimal():
        return fields[0], int(fields[1])
    if len(fields) >= GREP_LINE_WITH_REF_FIELDS and fields[2].isdecimal():
        return fields[1], int(fields[2])
    return None


def _cross_language_consumer(path: str) -> bool:
    return path.endswith((".sh", "SKILL.md")) or path.startswith("hooks/")


def _excluded_consumer_path(path: str) -> bool:
    return any(path == excluded or path.startswith(f"{excluded}/") for excluded in CONSUMER_EXCLUDED_PATHS)


def _find_consumers(
    runner: Runner, *, evidence_ref: str, symbols: Sequence[str], touched_files: Sequence[str]
) -> tuple[ScanResult, tuple[str, ...], tuple[str, ...], bool]:
    if not symbols:
        return ScanResult(status=SCAN_OK), (), (), False
    touched = set(touched_files)
    references: set[tuple[str, int, str]] = set()
    excluded_pathspecs = [f":(exclude){path}" for path in CONSUMER_EXCLUDED_PATHS]
    for symbol in symbols:
        scan = _required_git_scan(
            runner,
            ["git", "grep", "-n", "-F", "-e", symbol, evidence_ref, "--", ".", *excluded_pathspecs],
            description=f"consumer scan failed for symbol {symbol}",
            no_match_ok=True,
        )
        if not scan.complete:
            return scan, (), (), False
        for line in scan.stdout.splitlines():
            parsed = _consumer_line(line)
            if parsed is None:
                continue
            path, line_number = parsed
            if path not in touched and not _excluded_consumer_path(path):
                references.add((path, line_number, symbol))
    ordered = tuple(sorted(references))
    all_paths = tuple(sorted({path for path, _line_number, _symbol in ordered}))
    paths = all_paths[:PREFETCH_CONSUMER_CAP]
    retained_paths = set(paths)
    rendered = tuple(
        f"{path}:{line_number}: `{symbol}`" + (" [cross-language]" if _cross_language_consumer(path) else "")
        for path, line_number, symbol in ordered
        if path in retained_paths
    )
    return ScanResult(status=SCAN_OK), paths, rendered, len(all_paths) > len(paths)


def _later_history_hash(
    *,
    fix_sha: str,
    evidence_ref: str,
    files: Sequence[str],
    later_history: str,
    scan_states: Sequence[tuple[str, str, str]] = (),
) -> str:
    hasher = hashlib.sha256()
    hasher.update(f"fix={fix_sha}\nref={evidence_ref}\n".encode())
    for path in files:
        hasher.update(f"file={path}\n".encode())
    for name, status, reason in scan_states:
        hasher.update(f"scan={name}\0{status}\0{reason}\n".encode())
    hasher.update(later_history.encode())
    return hasher.hexdigest()


def _cache_key(*, issue_number: int, fix_sha: str, later_history_hash: str, state: str, state_reason: str) -> str:
    norm_state = state.strip().upper()
    norm_reason = state_reason.strip().upper()
    return hashlib.sha256(f"{issue_number}\0{fix_sha}\0{later_history_hash}\0{norm_state}\0{norm_reason}".encode()).hexdigest()


def _capped(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    return text[:cap] + f"\n\n[content truncated to {cap} characters]\n"


def _extract_evidence_token(bundle_text: str) -> str | None:
    """Return the canonical bundle evidence token when present near the top."""
    for line in bundle_text.splitlines()[:EVIDENCE_TOKEN_SCAN_LINES]:
        match = EVIDENCE_TOKEN_PATTERN.fullmatch(line)
        if match:
            return match.group(1)
    return None


def _scan_status_lines(*, name: str, scan: ScanResult) -> list[str]:
    lines = [f"Status: {scan.status}"]
    if scan.reason:
        lines.append(f"Failure: {scan.reason}")
    return [f"## {name}", *lines]


def _incomplete_evidence_reason(*, scans: Sequence[tuple[str, ScanResult]]) -> str:
    incomplete = [f"{name} ({scan.reason or scan.status})" for name, scan in scans if not scan.complete]
    return "required evidence incomplete: " + "; ".join(incomplete)


def build_bundle_record(
    *,
    runner: Runner,
    issue: IssueRecord,
    repo: str,
    evidence_ref: str,
    run_dir: Path,
    diff_cap: int,
    body_cap: int,
) -> BundleRecord:
    stripped_body, malformed = _strip_plan(issue.body)
    fix = resolve_fix_evidence(runner, issue=issue, repo=repo, evidence_ref=evidence_ref)
    mechanical, reason = _mechanical_verdict(issue, fix=fix, strip_malformed=malformed)
    touched = _touched_files(runner, fix_sha=fix.fix_sha)
    fix_time, added_lines = _fix_metadata(runner, fix_sha=fix.fix_sha)
    marker_references, marker_fingerprint = _marker_evidence(issue.title, stripped_body)
    zones = _zones_for_files(touched)
    baseline_extended = _baseline_extended(touched)
    if fix.fix_sha:
        diff_scan = _required_git_scan(
            runner,
            ["git", "show", "--unified=1", "--format=medium", fix.fix_sha],
            description="fix-diff scan failed",
        )
        symbols = _changed_symbols(diff_scan.stdout) if diff_scan.complete else ()
        if diff_scan.complete:
            consumer_scan, consumer_paths, consumer_references, consumers_truncated = _find_consumers(
                runner,
                evidence_ref=evidence_ref,
                symbols=symbols,
                touched_files=touched,
            )
        else:
            consumer_scan = ScanResult(status=SCAN_FAILED, reason="consumer scan skipped because fix-diff scan failed")
            consumer_paths = ()
            consumer_references = ()
            consumers_truncated = False
    else:
        diff_scan = ScanResult(status=SCAN_NOT_RUN, reason="fix SHA is unavailable")
        consumer_scan = ScanResult(status=SCAN_NOT_RUN, reason="fix SHA is unavailable")
        symbols = ()
        consumer_paths = ()
        consumer_references = ()
        consumers_truncated = False
    scan_files = tuple(dict.fromkeys((*touched, *consumer_paths)))
    later_scan = _later_history(runner, fix_sha=fix.fix_sha, evidence_ref=evidence_ref, files=scan_files)
    revert_scan = _revert_scan(runner, fix_sha=fix.fix_sha, evidence_ref=evidence_ref, files=scan_files)
    scans = (
        ("fix-diff", diff_scan),
        ("consumer", consumer_scan),
        ("later-history", later_scan),
        ("revert", revert_scan),
    )
    if fix.fix_sha and any(not scan.complete for _name, scan in scans):
        incomplete_reason = _incomplete_evidence_reason(scans=scans)
        mechanical = "NEEDS_DEEP"
        reason = f"{reason}; {incomplete_reason}" if reason else incomplete_reason
    later_hash = _later_history_hash(
        fix_sha=fix.fix_sha,
        evidence_ref=evidence_ref,
        files=scan_files,
        later_history=later_scan.stdout,
        scan_states=tuple((name, scan.status, scan.reason) for name, scan in scans),
    )
    cache_key = _cache_key(
        issue_number=issue.number,
        fix_sha=fix.fix_sha,
        later_history_hash=later_hash,
        state=issue.state,
        state_reason=issue.state_reason,
    )

    body_path = run_dir / f"issue-{issue.number}-body.md"
    bundle_path = run_dir / f"issue-{issue.number}-bundle.md"
    evidence_token = secrets.token_hex(16)
    _atomic_write_text(body_path, _capped(stripped_body, body_cap))
    bundle = "\n".join(
        [
            f"# Bug #{issue.number}: {issue.title}",
            f"{EVIDENCE_TOKEN_LABEL}: {evidence_token}",
            "",
            f"URL: {issue.url}",
            f"State: {issue.state} {issue.state_reason}".rstrip(),
            f"Fix SHA: {fix.fix_sha or '(none)'}",
            f"Fix source: {fix.source}",
            f"Mechanical verdict: {mechanical or '(requires triage)'}",
            f"Mechanical reason: {reason}",
            "",
            "## Stripped issue body",
            _capped(stripped_body, body_cap),
            "",
            "## Touched files",
            "\n".join(touched) or "(none)",
            "",
            "## Changed symbols",
            "\n".join(symbols) or "(none)",
            "",
            *_scan_status_lines(name="Consumers of changed symbols", scan=consumer_scan),
            f"Notice: consumers truncated to {PREFETCH_CONSUMER_CAP} paths" if consumers_truncated else "",
            "\n".join(consumer_references) or "(none)",
            "",
            "## Later commits touching evidence files",
            f"Status: {later_scan.status}",
            f"Failure: {later_scan.reason}" if later_scan.reason else "",
            later_scan.stdout or "(none)",
            "",
            "## Revert scan",
            f"Status: {revert_scan.status}",
            f"Failure: {revert_scan.reason}" if revert_scan.reason else "",
            revert_scan.stdout or "(none)",
            "",
            "## Capped fix diff",
            f"Status: {diff_scan.status}",
            f"Failure: {diff_scan.reason}" if diff_scan.reason else "",
            _capped(diff_scan.stdout, diff_cap),
            "",
        ]
    )
    _atomic_write_text(bundle_path, bundle)
    return BundleRecord(
        issue_number=issue.number,
        title=issue.title,
        state=issue.state,
        state_reason=issue.state_reason,
        url=issue.url,
        body_path=str(body_path),
        bundle_path=str(bundle_path),
        fix_sha=fix.fix_sha,
        fix_source=fix.source,
        touched_files=touched,
        later_history_hash=later_hash,
        mechanical_verdict=mechanical,
        mechanical_reason=reason,
        cache_key=cache_key,
        fix_time=fix_time,
        added_lines=added_lines,
        marker_references=marker_references,
        marker_fingerprint=marker_fingerprint,
        zones=zones,
        baseline_extended=baseline_extended,
        changed_symbols=symbols,
        consumer_paths=consumer_paths,
        consumer_references=consumer_references,
        consumers_truncated=consumers_truncated,
        scan_files=scan_files,
        diff_scan_status=diff_scan.status,
        diff_scan_reason=diff_scan.reason,
        consumer_scan_status=consumer_scan.status,
        consumer_scan_reason=consumer_scan.reason,
        later_history_scan_status=later_scan.status,
        later_history_scan_reason=later_scan.reason,
        revert_scan_status=revert_scan.status,
        revert_scan_reason=revert_scan.reason,
    )


def _write_initial_batches(run_dir: Path, rows: Sequence[BundleRecord], *, batch_size: int) -> tuple[str, ...]:
    triage_rows = [row for row in rows if row.fix_sha and not row.mechanical_verdict]
    paths: list[str] = []
    for index in range(0, len(triage_rows), batch_size):
        batch = triage_rows[index : index + batch_size]
        path = run_dir / f"triage-batch-{len(paths) + 1}.jsonl"
        text = "".join(json.dumps({"issue": row.issue_number, "cache_key": row.cache_key, "bundle_path": row.bundle_path}, sort_keys=True) + "\n" for row in batch)
        _atomic_write_text(path, text)
        paths.append(str(path))
    return tuple(paths)


def prefetch(
    *,
    runner: Runner,
    repo_arg: str = "",
    count: int = config.ANALYZE_BUGS_DEFAULT_COUNT,
    cache_root_arg: str = "",
    batch_size: int = config.ANALYZE_BUGS_DEFAULT_BATCH_SIZE,
    diff_cap: int = DEFAULT_DIFF_CAP,
    body_cap: int = DEFAULT_BODY_CAP,
) -> RunManifest:
    repo = resolve_repo(runner, repo_arg)
    evidence_ref = resolve_evidence_ref(runner)
    issues, _corpus_count = fetch_bug_issues(runner, repo=repo, count=count)
    repo_root = _cache_root(cache_root_arg) / _sanitize_repo_slug(repo)
    run_id = str(int(time.time()))
    run_dir = repo_root / "runs" / run_id
    _private_mkdir(run_dir)
    ledger_path = repo_root / "ledger.jsonl"
    rows = [
        build_bundle_record(runner=runner, issue=issue, repo=repo, evidence_ref=evidence_ref, run_dir=run_dir, diff_cap=diff_cap, body_cap=body_cap)
        for issue in issues
    ]
    deep_queue_path = run_dir / "deep-queue.jsonl"
    _atomic_write_text(deep_queue_path, "")
    triage_paths = _write_initial_batches(run_dir, rows, batch_size=batch_size)
    manifest = RunManifest(
        schema_version="1",
        repo=repo,
        run_id=run_id,
        run_dir=str(run_dir),
        evidence_ref=evidence_ref,
        bugs_requested=count,
        bugs_selected=len(rows),
        generated_at=int(time.time()),
        ledger_path=str(ledger_path),
        triage_batch_paths=triage_paths,
        deep_queue_path=str(deep_queue_path),
        issues=tuple(rows),
    )
    _write_json(run_dir / "manifest.json", asdict(manifest))
    return manifest


def prefetch_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python/cli.py analyze-bugs prefetch")
    parser.add_argument("--repo", default="")
    parser.add_argument("-n", "--count", type=lambda value: _positive_int(value, name="--count"), default=config.ANALYZE_BUGS_DEFAULT_COUNT)
    parser.add_argument("--cache-root", default="")
    parser.add_argument("--batch-size", type=lambda value: _positive_int(value, name="--batch-size"), default=config.ANALYZE_BUGS_DEFAULT_BATCH_SIZE)
    parser.add_argument("--diff-cap", type=lambda value: _positive_int(value, name="--diff-cap"), default=DEFAULT_DIFF_CAP)
    args = parser.parse_args(argv)
    try:
        manifest = prefetch(runner=_runner(), repo_arg=args.repo, count=args.count, cache_root_arg=args.cache_root, batch_size=args.batch_size, diff_cap=args.diff_cap)
    except AnalyzeBugsError as exc:
        return _fail(str(exc))
    _emit_kvs(
        {
            "EVIDENCE_REF": manifest.evidence_ref,
            "BUGS_REQUESTED": manifest.bugs_requested,
            "BUGS_SELECTED": manifest.bugs_selected,
            "RUN_DIR": manifest.run_dir,
            "MANIFEST_PATH": str(Path(manifest.run_dir) / "manifest.json"),
            "LEDGER_PATH": manifest.ledger_path,
            "TRIAGE_BATCH_PATHS": manifest.triage_batch_paths,
            "DEEP_QUEUE_PATH": manifest.deep_queue_path,
        }
    )
    return 0


def _bundle_from_mapping(row: Mapping[str, Any]) -> BundleRecord:
    return BundleRecord(
        issue_number=int(row.get("issue_number", 0)),
        title=str(row.get("title") or ""),
        state=str(row.get("state") or ""),
        state_reason=str(row.get("state_reason") or ""),
        url=str(row.get("url") or ""),
        body_path=str(row.get("body_path") or ""),
        bundle_path=str(row.get("bundle_path") or ""),
        fix_sha=str(row.get("fix_sha") or ""),
        fix_source=str(row.get("fix_source") or ""),
        touched_files=tuple(str(item) for item in row.get("touched_files", []) if isinstance(item, str)),
        later_history_hash=str(row.get("later_history_hash") or ""),
        mechanical_verdict=str(row.get("mechanical_verdict") or ""),
        mechanical_reason=str(row.get("mechanical_reason") or ""),
        cache_key=str(row.get("cache_key") or ""),
        sampled=bool(row.get("sampled", False)),
        fix_time=int(row.get("fix_time", 0) or 0),
        added_lines=int(row.get("added_lines", 0) or 0),
        marker_references=tuple(sorted({int(item) for item in row.get("marker_references", []) if isinstance(item, int) and not isinstance(item, bool) and item > 0})),
        marker_fingerprint=str(row.get("marker_fingerprint") or ""),
        zones=tuple(str(item) for item in row.get("zones", []) if isinstance(item, str)),
        baseline_extended=bool(row.get("baseline_extended", False)),
        changed_symbols=tuple(str(item) for item in row.get("changed_symbols", []) if isinstance(item, str)),
        consumer_paths=tuple(str(item) for item in row.get("consumer_paths", []) if isinstance(item, str)),
        consumer_references=tuple(str(item) for item in row.get("consumer_references", []) if isinstance(item, str)),
        consumers_truncated=bool(row.get("consumers_truncated", False)),
        scan_files=tuple(str(item) for item in row.get("scan_files", []) if isinstance(item, str)),
        diff_scan_status=str(row.get("diff_scan_status") or SCAN_OK),
        diff_scan_reason=str(row.get("diff_scan_reason") or ""),
        consumer_scan_status=str(row.get("consumer_scan_status") or SCAN_OK),
        consumer_scan_reason=str(row.get("consumer_scan_reason") or ""),
        later_history_scan_status=str(row.get("later_history_scan_status") or SCAN_OK),
        later_history_scan_reason=str(row.get("later_history_scan_reason") or ""),
        revert_scan_status=str(row.get("revert_scan_status") or SCAN_OK),
        revert_scan_reason=str(row.get("revert_scan_reason") or ""),
    )


def _load_manifest(path: Path) -> tuple[dict[str, Any], list[BundleRecord]]:
    data = _load_json(path)
    raw_issues = data.get("issues")
    if not isinstance(raw_issues, list):
        raise AnalyzeBugsError(f"manifest lacks issues array: {path}")
    rows = [_bundle_from_mapping(cast("Mapping[str, Any]", item)) for item in raw_issues if isinstance(item, dict)]
    return data, rows


def _ledger_record_from_mapping(raw: Mapping[str, Any]) -> LedgerRecord | None:
    try:
        issue = int(raw.get("issue", 0))
    except (TypeError, ValueError):
        return None
    if issue <= 0:
        return None
    stages_raw = raw.get("stages_complete", [])
    stages = tuple(str(item) for item in stages_raw if isinstance(item, str)) if isinstance(stages_raw, list) else ()
    missing_raw = raw.get("triage_missing_items", [])
    missing = tuple(str(item) for item in missing_raw if isinstance(item, str)) if isinstance(missing_raw, list) else ()
    sibling_sites_raw = raw.get("sibling_sites", [])
    sibling_sites = tuple(str(item) for item in sibling_sites_raw if isinstance(item, str)) if isinstance(sibling_sites_raw, list) else ()
    current_fields = {
        "triage_introduced_risk",
        "triage_introduced_risk_reason",
        "deep_introduced_risk",
        "deep_introduced_risk_reason",
        "class_complete",
        "sibling_sites",
        "legacy_schema",
    }
    current_schema = current_fields <= set(raw)
    return LedgerRecord(
        cache_key=str(raw.get("cache_key") or ""),
        issue=issue,
        fix_sha=str(raw.get("fix_sha") or ""),
        later_history_hash=str(raw.get("later_history_hash") or ""),
        triage_verdict=str(raw.get("triage_verdict") or ""),
        triage_reason=str(raw.get("triage_reason") or ""),
        triage_missing_items=missing,
        triage_needs_deep=bool(raw.get("triage_needs_deep", False)),
        triage_evidence_verified=bool(raw.get("triage_evidence_verified", False)),
        triage_introduced_risk=str(raw.get("triage_introduced_risk") or ""),
        triage_introduced_risk_reason=str(raw.get("triage_introduced_risk_reason") or ""),
        deep_verdict=str(raw.get("deep_verdict") or ""),
        deep_reason=str(raw.get("deep_reason") or ""),
        deep_introduced_risk=str(raw.get("deep_introduced_risk") or ""),
        deep_introduced_risk_reason=str(raw.get("deep_introduced_risk_reason") or ""),
        class_complete=raw.get("class_complete") is True,
        sibling_sites=sibling_sites,
        legacy_schema=True if not current_schema else raw.get("legacy_schema") is True,
        sampled=bool(raw.get("sampled", False)),
        stages_complete=stages,
        updated_at=int(raw.get("updated_at", 0) or 0) if str(raw.get("updated_at", 0) or 0).lstrip("-").isdigit() else 0,
        touched_files=tuple(str(item) for item in raw.get("touched_files", []) if isinstance(item, str)),
        fix_time=int(raw.get("fix_time", 0) or 0) if str(raw.get("fix_time", 0) or 0).lstrip("-").isdigit() else 0,
        added_lines=int(raw.get("added_lines", 0) or 0) if str(raw.get("added_lines", 0) or 0).lstrip("-").isdigit() else 0,
        marker_references=tuple(sorted({int(item) for item in raw.get("marker_references", []) if isinstance(item, int) and not isinstance(item, bool) and item > 0})),
        marker_fingerprint=str(raw.get("marker_fingerprint") or ""),
        zones=tuple(str(item) for item in raw.get("zones", []) if isinstance(item, str)),
        baseline_extended=bool(raw.get("baseline_extended", False)),
        metadata_version=int(raw.get("metadata_version", 0) or 0) if str(raw.get("metadata_version", 0) or 0).isdigit() else 0,
    )


def load_analytics_corpus(path: Path) -> tuple[list[AnalyticsCorpusRecord], int]:
    records: list[AnalyticsCorpusRecord] = []
    corrupt: list[str] = []
    if not path.exists():
        return records, 0
    ordinal = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            corrupt.append(line)
            continue
        if not isinstance(raw, dict):
            corrupt.append(line)
            continue
        record = _ledger_record_from_mapping(cast("Mapping[str, Any]", raw))
        if record is None or not record.cache_key:
            corrupt.append(line)
            continue
        ordinal += 1
        records.append(AnalyticsCorpusRecord(record=record, append_ordinal=ordinal))
    if corrupt:
        quarantine = path.with_name(f"{path.name}.corrupt-{int(time.time())}")
        _atomic_write_text(quarantine, "\n".join(corrupt) + "\n")
    return records, len(corrupt)


def load_ledger(path: Path) -> tuple[dict[str, LedgerRecord], int]:
    records: dict[str, LedgerRecord] = {}
    corrupt: list[str] = []
    if not path.exists():
        return records, 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            corrupt.append(line)
            continue
        if not isinstance(raw, dict):
            corrupt.append(line)
            continue
        rec = _ledger_record_from_mapping(cast("Mapping[str, Any]", raw))
        if rec is None or not rec.cache_key:
            corrupt.append(line)
            continue
        records[rec.cache_key] = rec
    if corrupt:
        quarantine = path.with_name(f"{path.name}.corrupt-{int(time.time())}")
        _atomic_write_text(quarantine, "\n".join(corrupt) + "\n")
    return records, len(corrupt)


def _record_for_bundle(ledger: Mapping[str, LedgerRecord], bundle: BundleRecord) -> LedgerRecord | None:
    if not bundle.required_evidence_complete:
        return None
    record = ledger.get(bundle.cache_key)
    if record and record.fix_sha == bundle.fix_sha and record.later_history_hash == bundle.later_history_hash:
        return record
    return None


def _complete(record: LedgerRecord | None, stage: str, *, refresh: bool) -> bool:
    if refresh or record is None:
        return False
    return stage in record.stages_complete


def _triage_complete(record: LedgerRecord | None, *, refresh: bool) -> bool:
    if refresh or record is None:
        return False
    return "triage" in record.stages_complete and record.triage_evidence_verified


def _unverified_legacy_triage_issues(*, bundles: Sequence[BundleRecord], ledger: Mapping[str, LedgerRecord]) -> list[int]:
    issues: list[int] = []
    for bundle in bundles:
        if not bundle.required_evidence_complete:
            continue
        record = _record_for_bundle(ledger, bundle)
        if record and "triage" in record.stages_complete and not record.triage_evidence_verified:
            issues.append(bundle.issue_number)
    return sorted(set(issues))


def _warn_unverified_legacy_triage(issues: Sequence[int]) -> None:
    if not issues:
        return
    shown = ",".join(str(issue) for issue in issues[:LEGACY_TRIAGE_WARN_LIMIT])
    suffix = f" (+{len(issues) - LEGACY_TRIAGE_WARN_LIMIT} more)" if len(issues) > LEGACY_TRIAGE_WARN_LIMIT else ""
    print(f"WARN: ignoring unverified legacy triage rows for issues: {shown}{suffix}", file=sys.stderr)


def _write_triage_batches(run_dir: Path, bundles: Sequence[BundleRecord], *, batch_size: int) -> tuple[str, ...]:
    for path in run_dir.glob("triage-pending-*.jsonl"):
        with contextlib.suppress(OSError):
            path.unlink()
    paths: list[str] = []
    for index in range(0, len(bundles), batch_size):
        batch = bundles[index : index + batch_size]
        path = run_dir / f"triage-pending-{len(paths) + 1}.jsonl"
        text = "".join(json.dumps({"issue": row.issue_number, "cache_key": row.cache_key, "bundle_path": row.bundle_path}, sort_keys=True) + "\n" for row in batch)
        _atomic_write_text(path, text)
        paths.append(str(path))
    return tuple(paths)


def _analytics_record_from_bundle(bundle: BundleRecord, record: LedgerRecord | None) -> AnalyticsRecord:
    return AnalyticsRecord(
        issue=bundle.issue_number,
        cache_key=bundle.cache_key,
        fix_sha=bundle.fix_sha,
        touched_files=bundle.touched_files or (record.touched_files if record else ()),
        fix_time=bundle.fix_time or (record.fix_time if record else 0),
        added_lines=bundle.added_lines if bundle.fix_time or bundle.added_lines else (record.added_lines if record else 0),
        marker_references=bundle.marker_references or (record.marker_references if record else ()),
        marker_fingerprint=bundle.marker_fingerprint or (record.marker_fingerprint if record else ""),
        zones=bundle.zones or (record.zones if record else _zones_for_files(bundle.touched_files)),
        baseline_extended=bundle.baseline_extended or (record.baseline_extended if record else False),
        ledger_record=record,
        bundle=bundle,
    )


def _analytics_record_from_ledger(record: LedgerRecord) -> AnalyticsRecord:
    return AnalyticsRecord(
        issue=record.issue,
        cache_key=record.cache_key,
        fix_sha=record.fix_sha,
        touched_files=record.touched_files,
        fix_time=record.fix_time,
        added_lines=record.added_lines,
        marker_references=record.marker_references,
        marker_fingerprint=record.marker_fingerprint,
        zones=record.zones or _zones_for_files(record.touched_files),
        baseline_extended=record.baseline_extended or _baseline_extended(record.touched_files),
        ledger_record=record,
    )


def _chain_components(edges: Sequence[ChainEdge]) -> dict[int, frozenset[int]]:
    adjacency: dict[int, set[int]] = {}
    for edge in edges:
        adjacency.setdefault(edge.from_issue, set()).add(edge.to_issue)
        adjacency.setdefault(edge.to_issue, set()).add(edge.from_issue)
    components: dict[int, frozenset[int]] = {}
    for issue in adjacency:
        if issue in components:
            continue
        pending = [issue]
        members: set[int] = set()
        while pending:
            current = pending.pop()
            if current in members:
                continue
            members.add(current)
            pending.extend(adjacency.get(current, ()))
        frozen = frozenset(members)
        for member in members:
            components[member] = frozen
    return components


def _historical_marker_backfill(runner: Runner, *, repo: str, issue: int) -> tuple[tuple[int, ...], str]:
    result = gh.api_read(runner, [f"/repos/{repo}/issues/{issue}", "--jq", '{title: .title, body: (.body // "")}'])
    if result.returncode != 0:
        return (), ""
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError:
        return (), ""
    if not isinstance(raw, dict):
        return (), ""
    title = raw.get("title")
    body = raw.get("body")
    if not isinstance(title, str) or not isinstance(body, str):
        return (), ""
    stripped_body, malformed = _strip_plan(body)
    if malformed:
        return (), ""
    return _marker_evidence(title, stripped_body)


def build_analytics_view(
    *,
    manifest: Mapping[str, Any],
    bundles: Sequence[BundleRecord],
    ledger_path: Path,
    runner: Runner | None = None,
) -> AnalyticsView:
    generated_at = int(manifest.get("generated_at", 0) or 0)
    window_start = generated_at - (14 * DAY_SECONDS)
    corpus, _corrupt = load_analytics_corpus(ledger_path)
    chosen: dict[int, AnalyticsCorpusRecord] = {}
    for row in corpus:
        record = row.record
        if not record.fix_sha and not (window_start < record.fix_time <= generated_at):
            continue
        previous = chosen.get(record.issue)
        key = (max(0, record.updated_at), row.append_ordinal)
        previous_key = ((previous.record.updated_at if previous and previous.record.updated_at > 0 else 0), previous.append_ordinal if previous else 0)
        if previous is None or key > previous_key:
            chosen[record.issue] = row
    records: dict[int, AnalyticsRecord] = {issue: _analytics_record_from_ledger(row.record) for issue, row in chosen.items()}
    for bundle in bundles:
        matching = next((row.record for row in reversed(corpus) if row.record.cache_key == bundle.cache_key), None)
        records[bundle.issue_number] = _analytics_record_from_bundle(bundle, matching)

    hydrated: dict[str, LedgerRecord] = {}
    if runner is not None:
        for issue, record in tuple(records.items()):
            persisted = record.ledger_record
            complete_metadata = (
                persisted is not None
                and persisted.metadata_version >= ANALYTICS_METADATA_VERSION
                and persisted.fix_time > 0
                and bool(persisted.touched_files)
                and persisted.added_lines > 0
            )
            if not record.fix_sha or complete_metadata:
                continue
            touched = record.touched_files or _touched_files(runner, fix_sha=record.fix_sha)
            fix_time, added_lines = _fix_metadata(runner, fix_sha=record.fix_sha)
            if fix_time <= 0:
                continue
            updated = AnalyticsRecord(
                issue=record.issue,
                cache_key=record.cache_key,
                fix_sha=record.fix_sha,
                touched_files=touched,
                fix_time=fix_time or record.fix_time,
                added_lines=added_lines if fix_time or added_lines else record.added_lines,
                marker_references=record.marker_references,
                marker_fingerprint=record.marker_fingerprint,
                zones=_zones_for_files(touched),
                baseline_extended=_baseline_extended(touched),
                ledger_record=record.ledger_record,
                bundle=record.bundle,
            )
            records[issue] = updated
            if persisted is not None:
                hydrated[persisted.cache_key] = replace(
                    persisted,
                    touched_files=touched,
                    fix_time=fix_time,
                    added_lines=added_lines,
                    zones=_zones_for_files(touched),
                    baseline_extended=_baseline_extended(touched),
                    metadata_version=ANALYTICS_METADATA_VERSION,
                )

        repo = str(manifest.get("repo") or "")
        backfill_count = 0
        for issue, record in tuple(sorted(records.items())):
            if backfill_count >= HISTORICAL_MARKER_BACKFILL_LIMIT:
                break
            if record.bundle is not None or record.marker_fingerprint or not repo:
                continue
            references, fingerprint = _historical_marker_backfill(runner, repo=repo, issue=issue)
            if not references or not fingerprint:
                continue
            backfill_count += 1
            updated = replace(record, marker_references=references, marker_fingerprint=fingerprint)
            records[issue] = updated
            if record.ledger_record is not None:
                hydrated[record.ledger_record.cache_key] = replace(
                    hydrated.get(record.ledger_record.cache_key, record.ledger_record),
                    marker_references=references,
                    marker_fingerprint=fingerprint,
                    metadata_version=ANALYTICS_METADATA_VERSION,
                )

    records = {
        issue: record
        for issue, record in records.items()
        if record.bundle is not None or window_start < record.fix_time <= generated_at
    }

    marker_edges = {
        ChainEdge(record.issue, reference, "marker")
        for record in records.values()
        for reference in record.marker_references
        if reference != record.issue
    }
    ordered = sorted((record for record in records.values() if record.fix_time), key=lambda item: (item.fix_time, item.issue))
    file_edges: set[ChainEdge] = set()
    for index, newer in enumerate(ordered):
        newer_files = set(newer.touched_files)
        if not newer_files:
            continue
        for prior in ordered[:index]:
            if newer.issue == prior.issue or newer.fix_sha == prior.fix_sha:
                continue
            if newer.fix_time - prior.fix_time >= 14 * DAY_SECONDS:
                continue
            if newer_files.intersection(prior.touched_files):
                file_edges.add(ChainEdge(newer.issue, prior.issue, "file_intersection"))
    edges = tuple(sorted(marker_edges | file_edges, key=lambda edge: (edge.from_issue, edge.to_issue, edge.detector_kind)))

    seven_day_start = generated_at - (7 * DAY_SECONDS)
    commits_by_file: dict[str, set[str]] = {}
    for record in records.values():
        if not record.fix_sha or not (seven_day_start < record.fix_time <= generated_at):
            continue
        for path in record.touched_files:
            commits_by_file.setdefault(path, set()).add(record.fix_sha)
    churned_files = tuple(sorted(path for path, commits in commits_by_file.items() if len(commits) >= CHURN_COMMIT_THRESHOLD))

    zone_members: dict[str, set[int]] = {}
    for record in records.values():
        if not record.fix_time or not (window_start < record.fix_time <= generated_at):
            continue
        for zone in record.zones:
            zone_members.setdefault(zone, set()).add(record.issue)
    analytics_issues = set(records)
    components = _chain_components(
        tuple(edge for edge in edges if edge.from_issue in analytics_issues and edge.to_issue in analytics_issues)
    )
    chronic: list[ChronicZone] = []
    for zone, members in sorted(zone_members.items()):
        connected = any(len(component.intersection(members)) >= CHAIN_MEMBER_THRESHOLD for component in set(components.values()))
        if len(members) >= CHRONIC_BUG_THRESHOLD or connected:
            zone_churn = tuple(path for path in churned_files if zone_for_path(path) == zone)
            chronic.append(ChronicZone(zone=zone, issues=tuple(sorted(members)), churned_files=zone_churn))
    baseline_issues = tuple(sorted(record.issue for record in records.values() if record.baseline_extended))
    return AnalyticsView(
        records=tuple(sorted(records.values(), key=lambda item: item.issue)),
        chain_edges=edges,
        chronic_zones=tuple(chronic),
        churned_files=churned_files,
        baseline_issues=baseline_issues,
        hydrated_records=tuple(hydrated.values()),
    )


def _risk_reason(issue: int, view: AnalyticsView) -> str:
    record = next((item for item in view.records if item.issue == issue), None)
    if record is None:
        return ""
    if any(issue in {edge.from_issue, edge.to_issue} for edge in view.chain_edges):
        return "chain-linked"
    chronic_names = {zone.zone for zone in view.chronic_zones}
    if chronic_names.intersection(record.zones):
        return "chronic-zone"
    has_python = any(path.startswith("python/") for path in record.touched_files)
    has_contract = any(path.startswith(("scripts/", "skills/")) for path in record.touched_files)
    if has_python and has_contract:
        return "cross-language"
    if record.added_lines > LARGE_FIX_ADDED_LINES:
        return "size"
    return ""


def _priority_deep_candidates(
    *,
    bundles: Sequence[BundleRecord],
    ledger: Mapping[str, LedgerRecord],
    sample: int,
    refresh: bool,
    analytics: AnalyticsView | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    by_priority: list[tuple[int, BundleRecord, LedgerRecord | None, str]] = []
    risk_priorities = {"chain-linked": 3, "chronic-zone": 4, "cross-language": 5, "size": 6}
    for bundle in bundles:
        if not bundle.required_evidence_complete:
            continue
        record = _record_for_bundle(ledger, bundle)
        if bundle.fix_sha and _complete(record, "deep", refresh=refresh):
            continue
        if bundle.mechanical_verdict == "NEEDS_DEEP":
            by_priority.append((0, bundle, record, "mechanical"))
            continue
        if _triage_complete(record, refresh=refresh) and record and record.triage_verdict == "SUSPECT":
            by_priority.append((1, bundle, record, "triage"))
            continue
        if _triage_complete(record, refresh=refresh) and record and (record.triage_verdict == "NEEDS_DEEP" or record.triage_needs_deep):
            by_priority.append((2, bundle, record, "triage"))
            continue
        if _triage_complete(record, refresh=refresh) and record and record.triage_verdict in {"FIXED_CLEAR", "FIXED_LIKELY"} and analytics:
            reason = _risk_reason(bundle.issue_number, analytics)
            if reason:
                by_priority.append((risk_priorities[reason], bundle, record, reason))
    seen: set[int] = set()
    for _priority, bundle, record, source in sorted(by_priority, key=lambda item: (item[0], item[1].issue_number)):
        if bundle.issue_number in seen:
            continue
        seen.add(bundle.issue_number)
        candidates.append({"issue": bundle.issue_number, "cache_key": bundle.cache_key, "bundle_path": bundle.bundle_path, "source": source, "sampled": bool(record.sampled if record else False)})

    if sample > 0:
        pool: list[BundleRecord] = []
        for bundle in bundles:
            if bundle.issue_number in seen:
                continue
            record = _record_for_bundle(ledger, bundle)
            if not _triage_complete(record, refresh=refresh) or not record or record.triage_verdict not in {"FIXED_CLEAR", "FIXED_LIKELY"}:
                continue
            if bundle.fix_sha and _complete(record, "deep", refresh=refresh):
                continue
            pool.append(bundle)
        rng = random.Random("analyze-bugs-sample")
        rng.shuffle(pool)
        for bundle in sorted(pool[:sample], key=lambda item: item.issue_number):
            seen.add(bundle.issue_number)
            candidates.append({"issue": bundle.issue_number, "cache_key": bundle.cache_key, "bundle_path": bundle.bundle_path, "source": "sample", "sampled": True})
    return candidates


def _write_deep_queue(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    text = "".join(json.dumps(dict(row), sort_keys=True) + "\n" for row in rows)
    _atomic_write_text(path, text)


def _stage_issue_numbers(run_dir: Path, *, stage: str) -> set[int]:
    if stage == "deep":
        paths = (run_dir / "deep-queue.jsonl",)
    else:
        paths = tuple(sorted(run_dir.glob("triage-pending-*.jsonl")))
    issue_numbers: set[int] = set()
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(raw, dict):
                continue
            issue = raw.get("issue")
            if isinstance(issue, bool):
                continue
            with contextlib.suppress(TypeError, ValueError):
                value = int(issue)
                if value > 0:
                    issue_numbers.add(value)
    return issue_numbers


def _validate_deep_model(alias: str) -> tuple[str, str]:
    pair = config.ANALYZE_BUGS_DEEP_MODEL_ALIASES.get(alias)
    if not pair:
        allowed = "|".join(config.ANALYZE_BUGS_DEEP_MODEL_ALIASES)
        raise AnalyzeBugsError(f"unsupported --deep-model {alias!r}; expected {allowed}")
    return pair


def _upsert_record(
    base: LedgerRecord | None,
    bundle: BundleRecord,
    *,
    triage: TriageIngest | None = None,
    deep: DeepIngest | None = None,
    sampled: bool | None = None,
    updated_at: int | None = None,
) -> LedgerRecord:
    stages = set(base.stages_complete if base else ())
    triage_verdict = base.triage_verdict if base else ""
    triage_reason = base.triage_reason if base else ""
    triage_missing = base.triage_missing_items if base else ()
    triage_needs_deep = base.triage_needs_deep if base else False
    triage_evidence_verified = base.triage_evidence_verified if base else False
    triage_introduced_risk = base.triage_introduced_risk if base else ""
    triage_introduced_risk_reason = base.triage_introduced_risk_reason if base else ""
    deep_verdict = base.deep_verdict if base else ""
    deep_reason = base.deep_reason if base else ""
    deep_introduced_risk = base.deep_introduced_risk if base else ""
    deep_introduced_risk_reason = base.deep_introduced_risk_reason if base else ""
    class_complete = base.class_complete if base else False
    sibling_sites = base.sibling_sites if base else ()
    legacy_schema = base.legacy_schema if base else True
    sampled_value = base.sampled if base else False
    if triage:
        stages.add("triage")
        triage_verdict = triage.verdict
        triage_reason = triage.reason
        triage_missing = triage.missing_items
        triage_needs_deep = triage.needs_deep
        triage_evidence_verified = True
        triage_introduced_risk = triage.introduced_risk
        triage_introduced_risk_reason = triage.introduced_risk_reason
        stages.discard("deep")
        deep_verdict = ""
        deep_reason = ""
        deep_introduced_risk = ""
        deep_introduced_risk_reason = ""
        class_complete = False
        sibling_sites = ()
        legacy_schema = triage.legacy_schema
    if deep:
        stages.add("deep")
        deep_verdict = deep.verdict
        deep_reason = deep.reason
        deep_introduced_risk = deep.introduced_risk
        deep_introduced_risk_reason = deep.introduced_risk_reason
        class_complete = deep.class_complete
        sibling_sites = deep.sibling_sites
        legacy_schema = deep.legacy_schema
    if sampled is not None:
        sampled_value = sampled
    return LedgerRecord(
        cache_key=bundle.cache_key,
        issue=bundle.issue_number,
        fix_sha=bundle.fix_sha,
        later_history_hash=bundle.later_history_hash,
        triage_verdict=triage_verdict,
        triage_reason=triage_reason,
        triage_missing_items=triage_missing,
        triage_needs_deep=triage_needs_deep,
        triage_evidence_verified=triage_evidence_verified,
        triage_introduced_risk=triage_introduced_risk,
        triage_introduced_risk_reason=triage_introduced_risk_reason,
        deep_verdict=deep_verdict,
        deep_reason=deep_reason,
        deep_introduced_risk=deep_introduced_risk,
        deep_introduced_risk_reason=deep_introduced_risk_reason,
        class_complete=class_complete,
        sibling_sites=sibling_sites,
        legacy_schema=legacy_schema,
        sampled=sampled_value,
        stages_complete=tuple(sorted(stages)),
        updated_at=int(time.time()) if updated_at is None else updated_at,
        touched_files=bundle.touched_files or (base.touched_files if base else ()),
        fix_time=bundle.fix_time or (base.fix_time if base else 0),
        added_lines=bundle.added_lines if bundle.fix_time or bundle.added_lines else (base.added_lines if base else 0),
        marker_references=bundle.marker_references or (base.marker_references if base else ()),
        marker_fingerprint=bundle.marker_fingerprint or (base.marker_fingerprint if base else ""),
        zones=bundle.zones or (base.zones if base else ()),
        baseline_extended=bundle.baseline_extended or (base.baseline_extended if base else False),
        metadata_version=ANALYTICS_METADATA_VERSION,
    )


def _record_json(record: LedgerRecord) -> dict[str, Any]:
    return asdict(record)


def ledger_compute(
    *,
    run_dir: Path,
    ledger_path: Path,
    manifest_path: Path,
    refresh: bool,
    sample: int,
    deep_max: int,
    deep_model: str,
    batch_size: int,
) -> dict[str, Any]:
    manifest, bundles = _load_manifest(manifest_path)
    ledger, corrupt_count = load_ledger(ledger_path)
    analytics = build_analytics_view(manifest=manifest, bundles=bundles, ledger_path=ledger_path, runner=_runner())
    metadata_records: list[LedgerRecord] = list(analytics.hydrated_records)
    for record in analytics.hydrated_records:
        ledger[record.cache_key] = record
    for bundle in bundles:
        base = ledger.get(bundle.cache_key)
        updated = _upsert_record(base, bundle, updated_at=int(manifest.get("generated_at", 0) or 0))
        if base is None or any(
            getattr(base, field) != getattr(updated, field)
            for field in ("touched_files", "fix_time", "added_lines", "marker_references", "marker_fingerprint", "zones", "baseline_extended", "metadata_version")
        ):
            ledger[bundle.cache_key] = updated
            metadata_records.append(updated)
    if metadata_records:
        _append_private_jsonl(ledger_path, (_record_json(record) for record in metadata_records))
    task_model, rate_model = _validate_deep_model(deep_model)
    unverified_legacy_issues = _unverified_legacy_triage_issues(bundles=bundles, ledger=ledger)
    _warn_unverified_legacy_triage(unverified_legacy_issues)
    pending_triage = [bundle for bundle in bundles if bundle.fix_sha and not bundle.mechanical_verdict and not _triage_complete(_record_for_bundle(ledger, bundle), refresh=refresh)]
    triage_paths = _write_triage_batches(run_dir, pending_triage, batch_size=batch_size)
    candidates = _priority_deep_candidates(bundles=bundles, ledger=ledger, sample=sample, refresh=refresh, analytics=analytics)
    truncated = candidates[deep_max:] if deep_max >= 0 else []
    selected = candidates[:deep_max] if deep_max >= 0 else candidates
    deep_queue = run_dir / "deep-queue.jsonl"
    _write_deep_queue(deep_queue, selected)
    summary = {
        "TRIAGE_BATCH_PATHS": triage_paths,
        "TRIAGE_PENDING": len(pending_triage),
        "DEEP_QUEUE_PATH": str(deep_queue),
        "DEEP_PENDING": len(selected),
        "DEEP_CAP_TRUNCATED": "true" if truncated else "false",
        "DEEP_TRUNCATED_ISSUES": [row["issue"] for row in truncated],
        "DEEP_TRUNCATED_CANDIDATES": [{"issue": row["issue"], "reason": row["source"]} for row in truncated],
        "DEEP_MODEL": task_model,
        "DEEP_RATE_MODEL": rate_model,
        "LEDGER_CORRUPT_LINES": corrupt_count,
    }
    _write_json(run_dir / "ledger-summary.json", summary)
    if truncated:
        print("WARN: deep cap truncated issues: " + ",".join(str(row["issue"]) for row in truncated), file=sys.stderr)
    return summary


def _strict_keys(raw: Mapping[str, Any], allowed: set[str]) -> bool:
    return set(raw.keys()) == allowed


def _introduced_risk_fields(raw: Mapping[str, Any], *, stage: str) -> tuple[str, str] | str:
    risk = raw.get("introduced_risk")
    reason = raw.get("introduced_risk_reason")
    if not isinstance(risk, str) or not risk:
        return f"{stage} introduced_risk must be a non-empty string"
    if not isinstance(reason, str) or not reason:
        return f"{stage} introduced_risk_reason must be a non-empty string"
    return risk, reason


def _parse_triage_row(raw: Mapping[str, Any]) -> TriageIngest | str:
    legacy_keys = {"issue", "verdict", "missing_items", "reason", "needs_deep", "evidence_token"}
    current_keys = legacy_keys | {"introduced_risk", "introduced_risk_reason"}
    if not (_strict_keys(raw, legacy_keys) or _strict_keys(raw, current_keys)):
        return "triage row has unexpected or missing fields"
    issue = raw.get("issue")
    if isinstance(issue, bool) or not isinstance(issue, int) or issue <= 0:
        return "triage issue must be a positive integer"
    verdict = str(raw.get("verdict") or "")
    if verdict not in TRIAGE_VERDICTS:
        return "triage verdict is unknown"
    missing = raw.get("missing_items")
    if not isinstance(missing, list) or not all(isinstance(item, str) for item in missing):
        return "triage missing_items must be strings"
    reason = raw.get("reason")
    if not isinstance(reason, str):
        return "triage reason must be a string"
    needs_deep = raw.get("needs_deep")
    if not isinstance(needs_deep, bool):
        return "triage needs_deep must be boolean"
    evidence_token = raw.get("evidence_token")
    if not isinstance(evidence_token, str) or not evidence_token:
        return "triage evidence_token must be a non-empty string"
    legacy_schema = _strict_keys(raw, legacy_keys)
    introduced_risk = ""
    introduced_risk_reason = ""
    if not legacy_schema:
        risk_fields = _introduced_risk_fields(raw, stage="triage")
        if isinstance(risk_fields, str):
            return risk_fields
        introduced_risk, introduced_risk_reason = risk_fields
    return TriageIngest(
        issue=issue,
        verdict=verdict,
        missing_items=tuple(missing),
        reason=reason,
        needs_deep=needs_deep,
        evidence_token=evidence_token,
        introduced_risk=introduced_risk,
        introduced_risk_reason=introduced_risk_reason,
        legacy_schema=legacy_schema,
    )


def _parse_deep_row(raw: Mapping[str, Any]) -> DeepIngest | str:
    legacy_keys = {"issue", "verdict", "reason"}
    current_keys = legacy_keys | {"introduced_risk", "introduced_risk_reason", "class_complete", "sibling_sites"}
    if not (_strict_keys(raw, legacy_keys) or _strict_keys(raw, current_keys)):
        return "deep row has unexpected or missing fields"
    issue = raw.get("issue")
    if isinstance(issue, bool) or not isinstance(issue, int) or issue <= 0:
        return "deep issue must be a positive integer"
    verdict = str(raw.get("verdict") or "")
    if verdict not in DEEP_VERDICTS:
        return "deep verdict is unknown"
    reason = raw.get("reason")
    if not isinstance(reason, str):
        return "deep reason must be a string"
    legacy_schema = _strict_keys(raw, legacy_keys)
    if legacy_schema:
        return DeepIngest(issue=issue, verdict=verdict, reason=reason)
    risk_fields = _introduced_risk_fields(raw, stage="deep")
    if isinstance(risk_fields, str):
        return risk_fields
    class_complete = raw.get("class_complete")
    if not isinstance(class_complete, bool):
        return "deep class_complete must be boolean"
    sibling_sites_raw = raw.get("sibling_sites")
    if not isinstance(sibling_sites_raw, list) or not all(isinstance(site, str) and SIBLING_SITE_RE.fullmatch(site) for site in sibling_sites_raw):
        return "deep sibling_sites must be valid path:symbol strings"
    sibling_sites = tuple(sibling_sites_raw)
    if class_complete and sibling_sites:
        return "deep class_complete requires an empty sibling_sites list"
    if verdict == "CONFIRMED_FIXED" and not class_complete and not sibling_sites:
        return "deep confirmed-fixed class-open row requires sibling_sites"
    return DeepIngest(
        issue=issue,
        verdict=verdict,
        reason=reason,
        introduced_risk=risk_fields[0],
        introduced_risk_reason=risk_fields[1],
        class_complete=class_complete,
        sibling_sites=sibling_sites,
        legacy_schema=False,
    )


def _triage_evidence_token_for_bundle(bundle: BundleRecord) -> EvidenceTokenLookup:
    try:
        bundle_text = Path(bundle.bundle_path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return EvidenceTokenLookup(error=f"bundle unreadable: {exc}")
    token = _extract_evidence_token(bundle_text)
    if token is None:
        return EvidenceTokenLookup(error="bundle lacks evidence_token line")
    return EvidenceTokenLookup(token=token)


def _validate_triage_evidence_token(parsed: TriageIngest, bundle: BundleRecord) -> str:
    expected = _triage_evidence_token_for_bundle(bundle)
    if expected.error:
        return expected.error
    if parsed.evidence_token != expected.token:
        return "triage evidence_token did not match bundle"
    return ""


def _sampled_lookup(run_dir: Path) -> set[int]:
    queue = run_dir / "deep-queue.jsonl"
    sampled: set[int] = set()
    if not queue.exists():
        return sampled
    for line in queue.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict) and raw.get("sampled") is True:
            with contextlib.suppress(TypeError, ValueError):
                sampled.add(int(raw.get("issue", 0)))
    return sampled


def ledger_ingest(*, run_dir: Path, ledger_path: Path, manifest_path: Path, triage_path: Path | None, deep_path: Path | None) -> dict[str, Any]:
    _manifest, bundles = _load_manifest(manifest_path)
    by_issue = {bundle.issue_number: bundle for bundle in bundles}
    ledger, corrupt_count = load_ledger(ledger_path)
    sampled_issues = _sampled_lookup(run_dir)
    accepted: list[LedgerRecord] = []
    rejected = 0
    seen: set[int] = set()
    stage = ""
    path = triage_path or deep_path
    if path is None:
        raise AnalyzeBugsError("ingest path missing")
    if deep_path is not None and not deep_path.is_file():
        return {"INGEST_STAGE": "deep", "INGEST_ACCEPTED": 0, "INGEST_REJECTED": 0, "LEDGER_CORRUPT_LINES": corrupt_count}
    if not path.is_file():
        raise AnalyzeBugsError(f"ingest file not found: {path}")
    expected_issues = _stage_issue_numbers(run_dir, stage=stage or ("deep" if deep_path is not None else "triage"))
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            print(f"WARN: rejected line {lineno}: not JSON", file=sys.stderr)
            rejected += 1
            continue
        if not isinstance(raw, dict):
            print(f"WARN: rejected line {lineno}: row is not object", file=sys.stderr)
            rejected += 1
            continue
        parsed: TriageIngest | DeepIngest | str
        if triage_path:
            stage = "triage"
            parsed = _parse_triage_row(cast("Mapping[str, Any]", raw))
        else:
            stage = "deep"
            parsed = _parse_deep_row(cast("Mapping[str, Any]", raw))
        if isinstance(parsed, str):
            print(f"WARN: rejected line {lineno}: {parsed}", file=sys.stderr)
            rejected += 1
            continue
        if parsed.issue in seen:
            print(f"WARN: rejected line {lineno}: duplicate issue in batch", file=sys.stderr)
            rejected += 1
            continue
        seen.add(parsed.issue)
        if expected_issues and parsed.issue not in expected_issues:
            print(f"WARN: rejected line {lineno}: issue not in active {stage or 'ingest'} batch", file=sys.stderr)
            rejected += 1
            continue
        bundle = by_issue.get(parsed.issue)
        if bundle is None:
            print(f"WARN: rejected line {lineno}: issue not in current manifest", file=sys.stderr)
            rejected += 1
            continue
        if not bundle.required_evidence_complete:
            print(f"WARN: rejected line {lineno}: required evidence is incomplete", file=sys.stderr)
            rejected += 1
            continue
        base = ledger.get(bundle.cache_key)
        if isinstance(parsed, TriageIngest):
            evidence_error = _validate_triage_evidence_token(parsed, bundle)
            if evidence_error:
                print(f"WARN: rejected line {lineno}: {evidence_error}", file=sys.stderr)
                rejected += 1
                continue
            record = _upsert_record(base, bundle, triage=parsed)
        else:
            record = _upsert_record(base, bundle, deep=parsed, sampled=parsed.issue in sampled_issues)
        ledger[bundle.cache_key] = record
        accepted.append(record)
    if accepted:
        _append_private_jsonl(ledger_path, [_record_json(record) for record in accepted])
    return {"INGEST_STAGE": stage, "INGEST_ACCEPTED": len(accepted), "INGEST_REJECTED": rejected, "LEDGER_CORRUPT_LINES": corrupt_count}


def ledger_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python/cli.py analyze-bugs ledger")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--ledger-path", required=True)
    parser.add_argument("--manifest", default="")
    parser.add_argument("--ingest-triage", default="")
    parser.add_argument("--ingest-deep", default="")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--sample", type=int, default=3)
    parser.add_argument("--deep-max", type=int, default=config.ANALYZE_BUGS_DEFAULT_DEEP_MAX)
    parser.add_argument("--deep-model", default="sonnet")
    parser.add_argument("--batch-size", type=int, default=config.ANALYZE_BUGS_DEFAULT_BATCH_SIZE)
    args = parser.parse_args(argv)
    run_dir = Path(args.run_dir)
    ledger_path = Path(args.ledger_path)
    manifest_path = Path(args.manifest) if args.manifest else run_dir / "manifest.json"
    try:
        if args.ingest_triage and args.ingest_deep:
            raise AnalyzeBugsError("pass only one of --ingest-triage or --ingest-deep")
        if args.ingest_triage or args.ingest_deep:
            payload = ledger_ingest(run_dir=run_dir, ledger_path=ledger_path, manifest_path=manifest_path, triage_path=Path(args.ingest_triage) if args.ingest_triage else None, deep_path=Path(args.ingest_deep) if args.ingest_deep else None)
        else:
            payload = ledger_compute(run_dir=run_dir, ledger_path=ledger_path, manifest_path=manifest_path, refresh=args.refresh, sample=max(args.sample, 0), deep_max=max(args.deep_max, 0), deep_model=args.deep_model, batch_size=max(args.batch_size, 1))
    except AnalyzeBugsError as exc:
        return _fail(str(exc))
    _emit_kvs(payload)
    return 0


def _final_verdict_with_tier(bundle: BundleRecord, record: LedgerRecord | None) -> tuple[str, str, str, tuple[str, ...], bool]:
    if not bundle.required_evidence_complete:
        scans = (
            ("fix-diff", ScanResult(bundle.diff_scan_status, reason=bundle.diff_scan_reason)),
            ("consumer", ScanResult(bundle.consumer_scan_status, reason=bundle.consumer_scan_reason)),
            ("later-history", ScanResult(bundle.later_history_scan_status, reason=bundle.later_history_scan_reason)),
            ("revert", ScanResult(bundle.revert_scan_status, reason=bundle.revert_scan_reason)),
        )
        return "NEEDS_DEEP", "MECH", _incomplete_evidence_reason(scans=scans), (), False
    if record and record.deep_verdict:
        return record.deep_verdict, "DEEP", record.deep_reason, (), record.sampled
    if bundle.mechanical_verdict and bundle.mechanical_verdict != "NEEDS_DEEP":
        return bundle.mechanical_verdict, "MECH", bundle.mechanical_reason, (), False
    if _triage_complete(record, refresh=False) and record and record.triage_verdict:
        if record.triage_verdict in {"SUSPECT", "NEEDS_DEEP"} or record.triage_needs_deep:
            return "NEEDS_DEEP", "TRIAGE", record.triage_reason, record.triage_missing_items, record.sampled
        return record.triage_verdict, "TRIAGE", record.triage_reason, record.triage_missing_items, record.sampled
    if bundle.mechanical_verdict:
        return bundle.mechanical_verdict, "MECH", bundle.mechanical_reason, (), False
    return "NEEDS_DEEP", "", "not yet triaged", (), False


def _verified_issue(verdict: str, tier: str) -> bool:
    return bool(tier) and verdict != "NEEDS_DEEP"


def _valid_introduced_risk(risk: str, reason: str) -> bool:
    return bool(risk) and bool(reason)


def _selected_introduced_risk(record: LedgerRecord | None) -> tuple[str, str, str] | None:
    if record is None or record.legacy_schema:
        return None
    if "deep" in record.stages_complete and _valid_introduced_risk(record.deep_introduced_risk, record.deep_introduced_risk_reason):
        return "DEEP", record.deep_introduced_risk, record.deep_introduced_risk_reason
    if "triage" in record.stages_complete and _valid_introduced_risk(record.triage_introduced_risk, record.triage_introduced_risk_reason):
        return "TRIAGE", record.triage_introduced_risk, record.triage_introduced_risk_reason
    return None


def _class_open_siblings(record: LedgerRecord | None) -> tuple[str, ...]:
    if record is None or record.legacy_schema or "deep" not in record.stages_complete:
        return ()
    if record.deep_verdict != "CONFIRMED_FIXED" or record.class_complete or not record.sibling_sites:
        return ()
    if not all(SIBLING_SITE_RE.fullmatch(site) for site in record.sibling_sites):
        return ()
    return record.sibling_sites


def _snapshot_from_mapping(raw: Mapping[str, Any], *, path: Path) -> RunSnapshot:
    required = {"schema_version", "repo", "run_id", "generated_at", "selected_issues", "verified_issues", "chronic_zones", "chain_edges", "verified_predicate"}
    if set(raw) != required or str(raw.get("schema_version")) != "1" or raw.get("verified_predicate") != VERIFIED_PREDICATE_VERSION:
        raise AnalyzeBugsError(f"malformed analyze-bugs run snapshot: {path}")
    try:
        generated_at = int(raw["generated_at"])
        selected = tuple(sorted(int(item) for item in cast("list[Any]", raw["selected_issues"])))
        verified = tuple(sorted(int(item) for item in cast("list[Any]", raw["verified_issues"])))
        zones = tuple(sorted(str(item) for item in cast("list[Any]", raw["chronic_zones"])))
        edges = tuple(sorted(str(item) for item in cast("list[Any]", raw["chain_edges"])))
    except (TypeError, ValueError) as exc:
        raise AnalyzeBugsError(f"malformed analyze-bugs run snapshot: {path}") from exc
    if any(not re.fullmatch(r"[1-9][0-9]*>[1-9][0-9]*:(?:marker|file_intersection)", edge) for edge in edges):
        raise AnalyzeBugsError(f"malformed analyze-bugs run snapshot edge: {path}")
    return RunSnapshot("1", str(raw["repo"]), str(raw["run_id"]), generated_at, selected, verified, zones, edges)


def _previous_snapshot(run_dir: Path, *, repo: str, generated_at: int) -> RunSnapshot | None:
    candidates: list[RunSnapshot] = []
    runs_root = run_dir.parent
    if not runs_root.is_dir():
        return None
    for path in sorted(runs_root.glob("*/run-state.json")):
        try:
            raw = _load_json(path)
            snapshot = _snapshot_from_mapping(raw, path=path)
        except (AnalyzeBugsError, OSError, json.JSONDecodeError):
            continue
        if snapshot.repo == repo and snapshot.generated_at < generated_at:
            candidates.append(snapshot)
    return max(candidates, key=lambda item: (item.generated_at, item.run_id), default=None)


def _format_issues(values: Sequence[int]) -> str:
    return ", ".join(f"#{item}" for item in values) or "None"


def _counts(verdicts: Sequence[str]) -> ReportCounts:
    return ReportCounts(
        total=len(verdicts),
        confirmed_fixed=sum(1 for v in verdicts if v in {"CONFIRMED_FIXED", "FIXED_CLEAR", "FIXED_LIKELY"}),
        needs_deep=sum(1 for v in verdicts if v == "NEEDS_DEEP"),
        not_fixed=sum(1 for v in verdicts if v == "NOT_FIXED"),
        incomplete=sum(1 for v in verdicts if v == "INCOMPLETE"),
        regressed=sum(1 for v in verdicts if v == "REGRESSED"),
        wontfix=sum(1 for v in verdicts if v == "WONTFIX"),
        unverifiable=sum(1 for v in verdicts if v == "UNVERIFIABLE"),
    )


def _markdown_table(rows: Sequence[Sequence[str]]) -> str:
    if not rows:
        return ""
    header = rows[0]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines.extend("| " + " | ".join(cell.replace("\n", " ").replace("|", "\\|") for cell in row) + " |" for row in rows[1:])
    return "\n".join(lines)


def _short_sha(sha: str) -> str:
    return sha[:12] if sha else ""


def _estimate_cost(*, bundles: Sequence[BundleRecord], deep_rate_model: str) -> str:
    # Task token ledgers are unavailable to this offline coordinator, so estimate
    # from capped bundle characters and one small verifier output per deep item.
    chars = 0
    for bundle in bundles:
        try:
            chars += len(Path(bundle.bundle_path).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            chars += 0
    input_tokens = chars / 4
    output_tokens = len(bundles) * 400
    row = rate_row("claude", model=deep_rate_model)
    cost = (input_tokens / 1_000_000 * row["input"]) + (output_tokens / 1_000_000 * row["output"])
    return f"${cost:.2f} estimated"


def _sweep_cost_estimate(*, run_dir: Path, selected_manifest: Mapping[str, Any]) -> str:
    """Estimate bounded finder and refuter Task usage at the Sonnet rate."""
    selected_raw = selected_manifest.get("selected")
    if not isinstance(selected_raw, list):
        raise AnalyzeBugsError("selected sweep manifest lacks selected array for cost estimate")
    finder_chars = 0
    for item in selected_raw:
        if not isinstance(item, dict):
            raise AnalyzeBugsError("selected sweep manifest has non-object entry for cost estimate")
        bundle_path = item.get("bundle_path")
        if not isinstance(bundle_path, str):
            raise AnalyzeBugsError("selected sweep manifest lacks bundle path for cost estimate")
        path = Path(bundle_path)
        if path.resolve().parent != run_dir.resolve():
            raise AnalyzeBugsError("selected sweep manifest has a bundle outside the active run directory")
        try:
            finder_chars += len(path.read_text(encoding="utf-8", errors="replace"))
        except OSError as exc:
            raise AnalyzeBugsError(f"could not read sweep bundle for cost estimate: {path}") from exc
    queue_path = run_dir / SWEEP_REFUTER_QUEUE_NAME
    try:
        refuter_rows = _read_strict_jsonl(queue_path, desc="sweep refuter queue") if queue_path.exists() else []
        refuter_chars = len(queue_path.read_text(encoding="utf-8", errors="replace")) if queue_path.exists() else 0
    except OSError as exc:
        raise AnalyzeBugsError(f"could not read sweep refuter queue for cost estimate: {queue_path}") from exc
    row = rate_row("claude", model=config.CLAUDE_SONNET_4_6_MODEL)
    input_tokens = (finder_chars + refuter_chars) / 4
    output_tokens = (len(selected_raw) * SWEEP_FINDER_OUTPUT_TOKENS) + (len(refuter_rows) * SWEEP_REFUTER_OUTPUT_TOKENS)
    cost = (input_tokens / 1_000_000 * row["input"]) + (output_tokens / 1_000_000 * row["output"])
    return f"${cost:.2f} estimated"


def _validated_sweep_artifact(*, run_dir: Path) -> tuple[SweepValidatedArtifact, dict[str, Any]] | None:
    """Load a strict validated artifact and prove it matches this run's selection."""
    artifact_path = run_dir / SWEEP_VALIDATED_NAME
    if not artifact_path.exists():
        return None
    raw = _load_json(artifact_path)
    required = {
        "pinned_tip",
        "selected_manifest_path",
        "selected_count",
        "skipped_count",
        "pending_shas",
        "coverage_incomplete",
        "candidates",
    }
    if set(raw) != required:
        raise AnalyzeBugsError(f"malformed validated sweep artifact keys: {artifact_path}")
    expected_manifest = (run_dir / SWEEP_SELECTED_MANIFEST_NAME).resolve()
    selected_path = raw.get("selected_manifest_path")
    if not isinstance(selected_path, str) or Path(selected_path).resolve() != expected_manifest:
        raise AnalyzeBugsError("validated sweep artifact has a foreign selected manifest path")
    selected_manifest = _load_json(expected_manifest)
    selected_required = {"pinned_tip", "selected_count", "skipped_count", "coverage_incomplete", "pending_shas", "selected"}
    if set(selected_manifest) != selected_required:
        raise AnalyzeBugsError("selected sweep manifest has unexpected keys")
    pinned_tip = _full_sha(raw.get("pinned_tip"), label="validated sweep pinned_tip")
    selected_tip, selected_shas, selected_summary = _load_selected_manifest(run_dir)
    manifest_selected_count = selected_manifest.get("selected_count")
    manifest_skipped_count = selected_manifest.get("skipped_count")
    manifest_pending_raw = selected_manifest.get("pending_shas")
    manifest_coverage = selected_manifest.get("coverage_incomplete")
    if (
        isinstance(manifest_selected_count, bool)
        or not isinstance(manifest_selected_count, int)
        or manifest_selected_count != len(selected_shas)
        or isinstance(manifest_skipped_count, bool)
        or not isinstance(manifest_skipped_count, int)
        or manifest_skipped_count < 0
        or not isinstance(manifest_pending_raw, list)
        or not isinstance(manifest_coverage, bool)
    ):
        raise AnalyzeBugsError("selected sweep manifest has malformed coverage fields")
    manifest_pending = tuple(_full_sha(item, label="selected sweep pending SHA") for item in manifest_pending_raw)
    if len(set(manifest_pending)) != len(manifest_pending) or manifest_skipped_count != len(manifest_pending):
        raise AnalyzeBugsError("selected sweep manifest has inconsistent pending coverage")
    if manifest_coverage != bool(manifest_pending):
        raise AnalyzeBugsError("selected sweep manifest has inconsistent coverage status")
    if pinned_tip != selected_tip:
        raise AnalyzeBugsError("validated sweep artifact pinned tip does not match selected manifest")
    selected_count = raw.get("selected_count")
    skipped_count = raw.get("skipped_count")
    coverage_incomplete = raw.get("coverage_incomplete")
    pending_raw = raw.get("pending_shas")
    if (
        isinstance(selected_count, bool)
        or not isinstance(selected_count, int)
        or selected_count != len(selected_shas)
        or isinstance(skipped_count, bool)
        or not isinstance(skipped_count, int)
        or skipped_count < 0
        or not isinstance(coverage_incomplete, bool)
        or not isinstance(pending_raw, list)
    ):
        raise AnalyzeBugsError("malformed validated sweep artifact coverage fields")
    pending_shas = tuple(_full_sha(item, label="validated sweep pending SHA") for item in pending_raw)
    if len(set(pending_shas)) != len(pending_shas):
        raise AnalyzeBugsError("validated sweep artifact has duplicate pending SHAs")
    if (
        skipped_count != int(selected_summary["skipped_count"])
        or coverage_incomplete != bool(selected_summary["coverage_incomplete"])
        or pending_shas != cast("tuple[str, ...]", selected_summary["pending_shas"])
    ):
        raise AnalyzeBugsError("validated sweep artifact coverage does not match selected manifest")
    candidates_raw = raw.get("candidates")
    if not isinstance(candidates_raw, list):
        raise AnalyzeBugsError("validated sweep artifact candidates must be an array")
    candidates: list[SweepCandidate] = []
    for item in candidates_raw:
        if not isinstance(item, dict):
            raise AnalyzeBugsError("validated sweep artifact candidate is not an object")
        if set(item) != {"merge_sha", "file", "symbol", "description", "severity", "confidence"}:
            raise AnalyzeBugsError("validated sweep artifact candidate has unexpected or missing fields")
        finding_raw = {key: item.get(key) for key in ("file", "symbol", "description", "severity", "confidence")}
        finding = _parse_finder_finding(finding_raw)
        if isinstance(finding, str):
            raise AnalyzeBugsError(f"validated sweep artifact candidate: {finding}")
        merge_sha = _full_sha(item.get("merge_sha"), label="validated sweep candidate merge_sha")
        if merge_sha not in selected_shas:
            raise AnalyzeBugsError("validated sweep artifact candidate belongs to an unselected merge")
        candidates.append(
            SweepCandidate(
                merge_sha=merge_sha,
                file=finding.file,
                symbol=finding.symbol,
                description=finding.description,
                severity=finding.severity,
                confidence=finding.confidence,
            )
        )
    current_tip = _full_sha(
        _git_required(_runner(), ["git", "rev-parse", "--verify", "origin/main"], desc="sweep report tip verification").strip(),
        label="current origin/main tip",
    )
    if current_tip != pinned_tip:
        raise AnalyzeBugsError("validated sweep artifact is stale for the current origin/main tip")
    return (
        SweepValidatedArtifact(
            pinned_tip=pinned_tip,
            selected_manifest_path=str(expected_manifest),
            selected_count=selected_count,
            skipped_count=skipped_count,
            pending_shas=pending_shas,
            coverage_incomplete=coverage_incomplete,
            candidates=tuple(candidates),
        ),
        selected_manifest,
    )


def _sweep_state_timestamp() -> str:
    return datetime.datetime.now(tz=datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_report(*, manifest_path: Path, ledger_path: Path, run_dir: Path) -> str:
    manifest, bundles = _load_manifest(manifest_path)
    ledger, corrupt_count = load_ledger(ledger_path)
    sweep = _validated_sweep_artifact(run_dir=run_dir)
    sweep_artifact = sweep[0] if sweep else None
    selected_sweep_manifest = sweep[1] if sweep else None
    analytics = build_analytics_view(manifest=manifest, bundles=bundles, ledger_path=ledger_path, runner=_runner())
    summary_path = run_dir / "ledger-summary.json"
    summary = _load_json(summary_path) if summary_path.exists() else {}
    truncated = {int(item) for item in summary.get("DEEP_TRUNCATED_ISSUES", []) if isinstance(item, int)}
    rows: list[tuple[BundleRecord, str, str, str, tuple[str, ...], bool]] = []
    introduced_risk_rows: list[tuple[BundleRecord, str, str, str]] = []
    class_open_rows: list[tuple[BundleRecord, tuple[str, ...], str]] = []
    verdict_values: list[str] = []
    verified_issues: list[int] = []
    for bundle in bundles:
        record = _record_for_bundle(ledger, bundle)
        verdict, tier, reason, missing, sampled = _final_verdict_with_tier(bundle, record)
        if bundle.issue_number in truncated:
            verdict = "NEEDS_DEEP"
            tier = ""
            reason = "deep cap truncated this candidate"
        rows.append((bundle, verdict, tier, reason, missing, sampled))
        selected_risk = _selected_introduced_risk(record)
        if selected_risk and selected_risk[1] != NO_INTRODUCED_RISK:
            introduced_risk_rows.append((bundle, *selected_risk))
        sibling_sites = _class_open_siblings(record)
        if sibling_sites:
            class_open_rows.append((bundle, sibling_sites, record.deep_reason))
        verdict_values.append(verdict)
        if _verified_issue(verdict, tier):
            verified_issues.append(bundle.issue_number)
    counts = _counts(verdict_values)
    count_table = _markdown_table(
        [
            ["Metric", "Count"],
            ["Total", str(counts.total)],
            ["Confirmed or likely fixed", str(counts.confirmed_fixed)],
            ["Needs deep", str(counts.needs_deep)],
            ["Not fixed", str(counts.not_fixed)],
            ["Incomplete", str(counts.incomplete)],
            ["Regressed", str(counts.regressed)],
            ["Won't fix", str(counts.wontfix)],
            ["Unverifiable", str(counts.unverifiable)],
        ]
    )
    detail_rows = [["Issue", "Fix", "Tier", "Verdict", "Reason", "Missing items"]]
    for bundle, verdict, tier, reason, missing, _sampled in rows:
        issue_link = f"#{bundle.issue_number}" if not bundle.url else f"[#{bundle.issue_number}]({bundle.url})"
        detail_rows.append([issue_link, _short_sha(bundle.fix_sha), tier or "PENDING", verdict, reason, "; ".join(missing)])
    introduced_risk_table = [["Issue", "Stage", "Risk", "Evidence"]]
    introduced_risk_table.extend(
        [
            f"[#{bundle.issue_number}]({bundle.url})" if bundle.url else f"#{bundle.issue_number}",
            stage,
            risk,
            risk_reason,
        ]
        for bundle, stage, risk, risk_reason in introduced_risk_rows
    )
    class_open_table = [["Issue", "Fix", "Sibling sites", "Verification"]]
    class_open_table.extend(
        [
            f"[#{bundle.issue_number}]({bundle.url})" if bundle.url else f"#{bundle.issue_number}",
            _short_sha(bundle.fix_sha),
            ", ".join(sibling_sites),
            deep_reason,
        ]
        for bundle, sibling_sites, deep_reason in class_open_rows
    )
    sampled_rows = [(bundle, verdict) for bundle, verdict, _tier, _reason, _missing, sampled in rows if sampled]
    sampled_failures = sum(1 for _bundle, verdict in sampled_rows if verdict in {"INCOMPLETE", "REGRESSED", "NOT_FIXED", "UNVERIFIABLE"})
    sample_rate = (sampled_failures / len(sampled_rows)) if sampled_rows else 0.0
    followups = [(bundle, verdict, reason) for bundle, verdict, _tier, reason, _missing, _sampled in rows if verdict in TERMINAL_FOLLOWUP_VERDICTS]
    followup_path = run_dir / "follow-up-issue.md"
    if followups or class_open_rows or (sweep_artifact and sweep_artifact.candidates):
        body_lines = ["# Analyze-bugs follow-up", "", f"Repo: {manifest.get('repo', '')}", "", "Findings:"]
        for bundle, verdict, reason in followups:
            body_lines.append(f"- #{bundle.issue_number}: {verdict}. {reason}")
        for bundle, sibling_sites, deep_reason in class_open_rows:
            body_lines.append(
                f"- #{bundle.issue_number}: Instance fixed, class open. "
                f"Sibling sites: {', '.join(sibling_sites)}. {deep_reason}"
            )
        if sweep_artifact and sweep_artifact.candidates:
            body_lines.extend(["", "Sweep candidates:"])
            body_lines.extend(
                f"- {_short_sha(candidate.merge_sha)} {candidate.file} `{candidate.symbol}`: "
                f"{candidate.severity}/{candidate.confidence}. {candidate.description}"
                for candidate in sweep_artifact.candidates
            )
        _atomic_write_text(followup_path, "\n".join(body_lines) + "\n")

    snapshot = RunSnapshot(
        schema_version="1",
        repo=str(manifest.get("repo", "")),
        run_id=str(manifest.get("run_id", run_dir.name)),
        generated_at=int(manifest.get("generated_at", 0) or 0),
        selected_issues=tuple(sorted(bundle.issue_number for bundle in bundles)),
        verified_issues=tuple(sorted(verified_issues)),
        chronic_zones=tuple(zone.zone for zone in analytics.chronic_zones),
        chain_edges=tuple(edge.identity for edge in analytics.chain_edges),
    )
    predecessor = _previous_snapshot(run_dir, repo=snapshot.repo, generated_at=snapshot.generated_at)
    prior_selected = set(predecessor.selected_issues if predecessor else ())
    prior_verified = set(predecessor.verified_issues if predecessor else ())
    prior_edges = set(predecessor.chain_edges if predecessor else ())
    prior_zones = set(predecessor.chronic_zones if predecessor else ())
    current_zones = set(snapshot.chronic_zones)

    zone_rows = [["Zone", "Bug count", "Member issues", "Churned files"]]
    zone_rows.extend([zone.zone, str(len(zone.issues)), _format_issues(zone.issues), ", ".join(zone.churned_files) or "None"] for zone in analytics.chronic_zones)
    chain_rows = [["From", "To", "Detector"]]
    chain_rows.extend([f"#{edge.from_issue}", f"#{edge.to_issue}", edge.detector_kind] for edge in analytics.chain_edges)
    baseline_rows = [["Issue", "Fix"]]
    by_issue = {bundle.issue_number: bundle for bundle in bundles}
    baseline_rows.extend([f"#{issue}", _short_sha(by_issue[issue].fix_sha) if issue in by_issue else "historical"] for issue in analytics.baseline_issues)

    rate_model = str(summary.get("DEEP_RATE_MODEL") or config.ANALYZE_BUGS_DEEP_MODEL_ALIASES["sonnet"][1])
    cost = _estimate_cost(bundles=bundles, deep_rate_model=rate_model)
    parts = [
        "# Analyze Bugs Report", "", f"Repo: {snapshot.repo}", f"Evidence ref: {manifest.get('evidence_ref', '')}",
        f"Requested: {manifest.get('bugs_requested', '')}", f"Selected: {manifest.get('bugs_selected', '')}", "",
        "## Counts", "", count_table, "", "## Issues", "", _markdown_table(detail_rows), "",
        "## Chronic zones", "", _markdown_table(zone_rows) if analytics.chronic_zones else "None.", "",
        "## Fix chains", "", _markdown_table(chain_rows) if analytics.chain_edges else "None.", "",
        "## Baseline-extending fixes", "", _markdown_table(baseline_rows) if analytics.baseline_issues else "None.", "",
        "## Since last run", "", "First run: yes" if predecessor is None else "First run: no",
        f"Newly selected: {_format_issues(sorted(set(snapshot.selected_issues) - prior_selected))}",
        f"Newly verified: {_format_issues(sorted(set(snapshot.verified_issues) - prior_verified))}",
        f"New chain edges: {', '.join(sorted(set(snapshot.chain_edges) - prior_edges)) or 'None'}",
        f"Zones entering chronic status: {', '.join(sorted(current_zones - prior_zones)) or 'None'}",
        f"Zones leaving chronic status: {', '.join(sorted(prior_zones - current_zones)) or 'None'}", "",
        "## Sample calibration", "", f"Sample size: {len(sampled_rows)}", f"Sampled failures: {sampled_failures}",
        f"Triage false-pass rate: {sample_rate:.2%}", "",
    ]
    if class_open_rows:
        parts[10:10] = ["## Instance fixed, class open", "", _markdown_table(class_open_table), ""]
    if introduced_risk_rows:
        parts[10:10] = ["## Introduced risk", "", _markdown_table(introduced_risk_table), ""]
    if sweep_artifact and selected_sweep_manifest is not None:
        sweep_rows = [["Merge", "File", "Symbol", "Severity", "Confidence", "Description"]]
        sweep_rows.extend(
            [
                _short_sha(candidate.merge_sha),
                candidate.file,
                candidate.symbol,
                candidate.severity,
                candidate.confidence,
                candidate.description,
            ]
            for candidate in sweep_artifact.candidates
        )
        parts.extend(
            [
                "## Sweep candidates",
                "",
                _markdown_table(sweep_rows) if sweep_artifact.candidates else "None.",
                "",
                f"Sweep selected merges: {sweep_artifact.selected_count}",
                f"Sweep skipped merges: {sweep_artifact.skipped_count}",
                f"Sweep pending frontier: {len(sweep_artifact.pending_shas)}",
            ]
        )
        if sweep_artifact.coverage_incomplete:
            parts.extend(["Sweep coverage incomplete: pending eligible merges will be retried.", ""])
        else:
            parts.append("")
    if corrupt_count:
        parts.extend([f"Ledger corrupt lines quarantined: {corrupt_count}", ""])
    if followups or class_open_rows or (sweep_artifact and sweep_artifact.candidates):
        parts.extend(["## Follow-up issue body", "", f"Follow-up body file: {followup_path}", ""])
    if analytics.chronic_zones:
        parts.extend([f"Suggestion: run /learn-from-bugs scoped to {', '.join(zone.zone for zone in analytics.chronic_zones)}.", ""])
    parts.append(f"ANALYZE_BUGS_COST_ESTIMATE={cost}")
    if sweep_artifact and selected_sweep_manifest is not None:
        parts.append(
            "ANALYZE_BUGS_SWEEP_COST_ESTIMATE="
            + _sweep_cost_estimate(
                run_dir=run_dir,
                selected_manifest=selected_sweep_manifest,
            )
        )
    report = "\n".join(parts) + "\n"
    _atomic_write_text(run_dir / "report.md", report)
    if analytics.hydrated_records:
        _append_private_jsonl(ledger_path, (_record_json(record) for record in analytics.hydrated_records))
    _write_json(run_dir / "run-state.json", asdict(snapshot))
    if sweep_artifact:
        write_sweep_state(
            sweep_state_path(ledger_path),
            SweepState(
                last_sweep_sha=sweep_artifact.pinned_tip,
                last_sweep_at=_sweep_state_timestamp(),
                schema_version=SWEEP_SCHEMA_VERSION,
                pending_shas=sweep_artifact.pending_shas,
            ),
        )
    return report


def report_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python/cli.py analyze-bugs report")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--ledger-path", required=True)
    args = parser.parse_args(argv)
    try:
        report = render_report(manifest_path=Path(args.manifest), ledger_path=Path(args.ledger_path), run_dir=Path(args.run_dir))
    except AnalyzeBugsError as exc:
        return _fail(str(exc))
    print(report, end="")
    return 0


def _full_sha(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not FULL_SHA_RE.fullmatch(value):
        raise AnalyzeBugsError(f"{label} must be a full 40-character lowercase SHA")
    return value


def _sweep_timestamp(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not SWEEP_TIMESTAMP_RE.fullmatch(value):
        raise AnalyzeBugsError(f"{label} must be an ISO-8601 UTC timestamp ending in Z")
    return value


def sweep_state_path(ledger_path: Path) -> Path:
    return ledger_path.expanduser().resolve().parent / SWEEP_STATE_FILENAME


def load_sweep_state(path: Path) -> SweepState | None:
    """Load strict sweep state; absent file means first sweep."""
    if not path.exists():
        return None
    try:
        raw = _load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalyzeBugsError(f"malformed sweep state: {path}: {exc}") from exc
    required = {"last_sweep_sha", "last_sweep_at", "schema_version", "pending_shas"}
    if set(raw) != required:
        raise AnalyzeBugsError(f"malformed sweep state keys: {path}")
    try:
        schema_version = int(raw["schema_version"])
    except (TypeError, ValueError) as exc:
        raise AnalyzeBugsError(f"malformed sweep state schema_version: {path}") from exc
    if schema_version != SWEEP_SCHEMA_VERSION:
        raise AnalyzeBugsError(f"unsupported sweep state schema_version={schema_version}: {path}")
    pending_raw = raw["pending_shas"]
    if not isinstance(pending_raw, list):
        raise AnalyzeBugsError(f"malformed sweep state pending_shas: {path}")
    pending: list[str] = []
    seen: set[str] = set()
    for item in pending_raw:
        sha = _full_sha(item, label="pending_shas entry")
        if sha in seen:
            raise AnalyzeBugsError(f"duplicate pending SHA in sweep state: {sha}")
        seen.add(sha)
        pending.append(sha)
    return SweepState(
        last_sweep_sha=_full_sha(raw["last_sweep_sha"], label="last_sweep_sha"),
        last_sweep_at=_sweep_timestamp(raw["last_sweep_at"], label="last_sweep_at"),
        schema_version=schema_version,
        pending_shas=tuple(pending),
    )


def write_sweep_state(path: Path, state: SweepState) -> None:
    """Atomically write validated sweep state beside the ledger."""
    if state.schema_version != SWEEP_SCHEMA_VERSION:
        raise AnalyzeBugsError(f"refusing to write unsupported sweep schema_version={state.schema_version}")
    _full_sha(state.last_sweep_sha, label="last_sweep_sha")
    _sweep_timestamp(state.last_sweep_at, label="last_sweep_at")
    seen: set[str] = set()
    pending: list[str] = []
    for sha in state.pending_shas:
        normalized = _full_sha(sha, label="pending_shas entry")
        if normalized in seen:
            raise AnalyzeBugsError(f"duplicate pending SHA: {normalized}")
        seen.add(normalized)
        pending.append(normalized)
    payload = {
        "last_sweep_sha": state.last_sweep_sha,
        "last_sweep_at": state.last_sweep_at,
        "schema_version": state.schema_version,
        "pending_shas": pending,
    }
    _write_json(path, payload)


def _git_required(runner: Runner, argv: Sequence[str], *, desc: str) -> str:
    result = runner.run(list(argv))
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        raise AnalyzeBugsError(f"{desc} failed{suffix}")
    return result.stdout


def _pin_origin_main(runner: Runner) -> str:
    fetch = runner.run(["git", "fetch", "origin", "main"])
    tip = runner.run(["git", "rev-parse", "--verify", "origin/main"])
    if tip.returncode != 0 or not tip.stdout.strip():
        detail = (tip.stderr or tip.stdout or fetch.stderr or "").strip()
        suffix = f": {detail}" if detail else ""
        raise AnalyzeBugsError(f"could not pin origin/main{suffix}")
    return _full_sha(tip.stdout.strip(), label="origin/main tip")


def _is_ancestor(runner: Runner, *, ancestor: str, descendant: str) -> bool:
    result = runner.run(["git", "merge-base", "--is-ancestor", ancestor, descendant])
    return result.returncode == 0


def _require_reachable(runner: Runner, *, sha: str, tip: str, label: str) -> None:
    if not _is_ancestor(runner, ancestor=sha, descendant=tip):
        raise AnalyzeBugsError(f"{label} {sha} is not reachable from pinned tip {tip}")


def _excluded_subject(subject: str) -> bool:
    return bool(SWEEP_FLUSH_SUBJECT_RE.match(subject) or SWEEP_RELEASE_SUBJECT_RE.match(subject))


def _larch_logs_only(paths: Sequence[str]) -> bool:
    return bool(paths) and all(path == "larch-logs" or path.startswith("larch-logs/") for path in paths)


def _extract_changed_symbols(diff_text: str) -> tuple[tuple[str, ...], bool]:
    symbols: list[str] = []
    seen: set[str] = set()
    truncated = False
    for line in diff_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        match = SWEEP_PY_DEF_RE.match(line) or SWEEP_PY_CLASS_RE.match(line) or SWEEP_PY_CONST_RE.match(line)
        if match is None:
            continue
        name = match.group(1)
        if name in seen:
            continue
        if len(symbols) >= SWEEP_SYMBOL_CAP:
            truncated = True
            break
        seen.add(name)
        symbols.append(name)
    return tuple(symbols), truncated


def _first_parent_evidence(runner: Runner, *, merge_sha: str, diff_cap: int) -> tuple[str, tuple[str, ...], int, str, bool, tuple[str, ...], bool]:
    base = _git_required(runner, ["git", "rev-parse", "--verify", f"{merge_sha}^1"], desc=f"first-parent base for {merge_sha}").strip()
    base_sha = _full_sha(base, label=f"first-parent base for {merge_sha}")
    names = _git_required(
        runner,
        ["git", "diff", "--name-only", f"{base_sha}..{merge_sha}"],
        desc=f"touched paths for {merge_sha}",
    )
    touched = tuple(line.strip() for line in names.splitlines() if line.strip())
    full_diff = _git_required(
        runner,
        ["git", "diff", "--unified=1", f"{base_sha}..{merge_sha}"],
        desc=f"first-parent diff for {merge_sha}",
    )
    diff_size = len(full_diff)
    truncated = len(full_diff) > diff_cap
    capped = _capped(full_diff, diff_cap)
    symbols, symbols_truncated = _extract_changed_symbols(full_diff)
    return base_sha, touched, diff_size, capped, truncated, symbols, symbols_truncated


def _discover_consumers(runner: Runner, *, symbols: Sequence[str], defining_paths: Sequence[str]) -> tuple[tuple[SweepConsumerHit, ...], bool]:
    hits: list[SweepConsumerHit] = []
    truncated = False
    exclude_args = [f":(exclude){path}" for path in (*defining_paths, *CONSUMER_EXCLUDED_PATHS)]
    for symbol in symbols:
        argv = ["git", "grep", "-n", "-F", "-e", symbol, "--", ".", *exclude_args]
        result = runner.run(argv)
        if result.returncode not in {0, 1}:
            detail = (result.stderr or result.stdout or "").strip()
            suffix = f": {detail}" if detail else ""
            raise AnalyzeBugsError(f"consumer scan for {symbol} failed{suffix}")
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            path_part, sep, rest = line.partition(":")
            if not sep:
                continue
            line_part, sep2, text = rest.partition(":")
            if not sep2 or not line_part.isdecimal():
                continue
            path = path_part.strip()
            if path in defining_paths or _excluded_consumer_path(path):
                continue
            if len(hits) >= SWEEP_CONSUMER_CAP:
                truncated = True
                return tuple(hits), truncated
            hits.append(SweepConsumerHit(path=path, line=int(line_part), text=text.strip()))
    return tuple(hits), truncated


def _build_sweep_commit(
    runner: Runner,
    *,
    merge_sha: str,
    subject: str,
    commit_time: int,
    history_order: int,
    chronic_names: set[str],
    diff_cap: int,
) -> SweepCommit:
    base_sha, touched, diff_size, capped, truncated, symbols, symbols_truncated = _first_parent_evidence(
        runner, merge_sha=merge_sha, diff_cap=diff_cap
    )
    zones = _zones_for_files(touched)
    chronic_hit = tuple(zone for zone in zones if zone in chronic_names)
    return SweepCommit(
        merge_sha=merge_sha,
        base_sha=base_sha,
        subject=subject,
        touched_paths=touched,
        diff_size=diff_size,
        capped_diff=capped,
        diff_truncated=truncated,
        changed_symbols=symbols,
        symbols_truncated=symbols_truncated,
        chronic_zones=chronic_hit,
        is_chronic=bool(chronic_hit),
        history_order=history_order,
        commit_time=commit_time,
    )


def _enumerate_window_rows(runner: Runner, *, tip: str, state: SweepState | None, now: int) -> list[tuple[str, str, int]]:
    if state is None:
        since = max(0, now - SWEEP_INITIAL_WINDOW_SECONDS)
        out = _git_required(
            runner,
            ["git", "log", "--first-parent", "--merges", f"--since={since}", "--format=%H%x00%s%x00%ct", tip],
            desc="first-run sweep enumeration",
        )
    else:
        out = _git_required(
            runner,
            ["git", "log", "--first-parent", "--merges", "--format=%H%x00%s%x00%ct", tip, "--not", state.last_sweep_sha],
            desc="watermark sweep enumeration",
        )
    rows: list[tuple[str, str, int]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\0")
        if len(parts) != SWEEP_LOG_FIELDS:
            raise AnalyzeBugsError(f"malformed git log sweep row: {line!r}")
        sha = _full_sha(parts[0], label="enumerated commit")
        subject = parts[1]
        try:
            commit_time = int(parts[2])
        except ValueError as exc:
            raise AnalyzeBugsError(f"malformed commit timestamp for {sha}") from exc
        rows.append((sha, subject, commit_time))
    # git log is newest-first; history_order should be older-first for deterministic ties.
    rows.reverse()
    return rows


def _subject_and_time(runner: Runner, *, sha: str) -> tuple[str, int]:
    out = _git_required(runner, ["git", "show", "-s", "--format=%s%x00%ct", sha], desc=f"commit metadata for {sha}").strip()
    subject, sep, rest = out.partition("\0")
    if not sep:
        raise AnalyzeBugsError(f"malformed commit metadata for {sha}")
    try:
        commit_time = int(rest.strip())
    except ValueError as exc:
        raise AnalyzeBugsError(f"malformed commit timestamp for {sha}") from exc
    return subject, commit_time


def _chronic_zone_names(*, runner: Runner, repo: str, ledger_path: Path, pinned_tip: str, run_dir: Path) -> tuple[str, ...]:
    manifest = {
        "schema_version": "1",
        "repo": repo,
        "run_id": "sweep-prepare",
        "run_dir": str(run_dir),
        "evidence_ref": pinned_tip,
        "bugs_requested": 0,
        "bugs_selected": 0,
        "generated_at": int(time.time()),
        "ledger_path": str(ledger_path),
        "triage_batch_paths": [],
        "deep_queue_path": "",
        "issues": [],
    }
    analytics = build_analytics_view(manifest=manifest, bundles=[], ledger_path=ledger_path, runner=runner)
    return tuple(zone.zone for zone in analytics.chronic_zones)


def _rank_key(commit: SweepCommit) -> tuple[int, int, int, str]:
    # Chronic first, then larger diffs, then older history order, then SHA.
    return (0 if commit.is_chronic else 1, -commit.diff_size, commit.history_order, commit.merge_sha)


def sweep_enumeration(
    *,
    runner: Runner,
    ledger_path: Path,
    run_dir: Path,
    repo: str,
    sweep_max: int,
    diff_cap: int = SWEEP_DIFF_CAP,
    now: int | None = None,
    pinned_tip: str | None = None,
) -> SweepEnumerationResult:
    if sweep_max <= 0:
        raise AnalyzeBugsError("--sweep-max must be a positive integer")
    tip = pinned_tip or _pin_origin_main(runner)
    tip = _full_sha(tip, label="pinned tip")
    state_path = sweep_state_path(ledger_path)
    state = load_sweep_state(state_path)
    if state is not None:
        _require_reachable(runner, sha=state.last_sweep_sha, tip=tip, label="last_sweep_sha")
        for pending in state.pending_shas:
            _require_reachable(runner, sha=pending, tip=tip, label="pending SHA")

    chronic_names = set(_chronic_zone_names(runner=runner, repo=repo, ledger_path=ledger_path, pinned_tip=tip, run_dir=run_dir))
    clock = int(time.time()) if now is None else now
    window_rows = _enumerate_window_rows(runner, tip=tip, state=state, now=clock)

    eligible: dict[str, SweepCommit] = {}
    history_order = 0
    for sha, subject, commit_time in window_rows:
        if _excluded_subject(subject):
            continue
        base_sha, touched, diff_size, capped, truncated, symbols, symbols_truncated = _first_parent_evidence(
            runner, merge_sha=sha, diff_cap=diff_cap
        )
        if _larch_logs_only(touched):
            continue
        zones = _zones_for_files(touched)
        chronic_hit = tuple(zone for zone in zones if zone in chronic_names)
        eligible[sha] = SweepCommit(
            merge_sha=sha,
            base_sha=base_sha,
            subject=subject,
            touched_paths=touched,
            diff_size=diff_size,
            capped_diff=capped,
            diff_truncated=truncated,
            changed_symbols=symbols,
            symbols_truncated=symbols_truncated,
            chronic_zones=chronic_hit,
            is_chronic=bool(chronic_hit),
            history_order=history_order,
            commit_time=commit_time,
        )
        history_order += 1

    if state is not None:
        for pending in state.pending_shas:
            if pending in eligible:
                continue
            subject, commit_time = _subject_and_time(runner, sha=pending)
            if _excluded_subject(subject):
                continue
            commit = _build_sweep_commit(
                runner,
                merge_sha=pending,
                subject=subject,
                commit_time=commit_time,
                history_order=history_order,
                chronic_names=chronic_names,
                diff_cap=diff_cap,
            )
            if _larch_logs_only(commit.touched_paths):
                continue
            eligible[pending] = commit
            history_order += 1

    ranked = sorted(eligible.values(), key=_rank_key)
    selected = tuple(ranked[:sweep_max])
    pending = tuple(commit.merge_sha for commit in ranked[sweep_max:])
    skipped = len(pending)
    return SweepEnumerationResult(
        pinned_tip=tip,
        selected=selected,
        pending_shas=pending,
        skipped_count=skipped,
        coverage_incomplete=skipped > 0,
        state_path=state_path,
        chronic_zone_names=tuple(sorted(chronic_names)),
    )


def _render_sweep_bundle(bundle: SweepBundle) -> str:
    notices = "\n".join(f"- {item}" for item in bundle.truncation_notices) or "- none"
    consumers = "\n".join(f"- {hit.path}:{hit.line}: {hit.text}" for hit in bundle.consumers) or "- none"
    symbols = ", ".join(bundle.changed_symbols) or "none"
    chronic = ", ".join(bundle.chronic_tags) or "none"
    touched = "\n".join(f"- {path}" for path in bundle.touched_files) or "- none"
    return "\n".join(
        [
            "# Sweep evidence bundle",
            "",
            f"pinned_tip: {bundle.pinned_tip}",
            f"merge_sha: {bundle.merge_sha}",
            f"base_sha: {bundle.base_sha}",
            f"subject: {bundle.subject}",
            f"chronic_tags: {chronic}",
            f"changed_symbols: {symbols}",
            "",
            "## Touched files",
            touched,
            "",
            "## Truncation notices",
            notices,
            "",
            "## Consumers",
            consumers,
            "",
            "## First-parent diff",
            "```diff",
            bundle.capped_diff.rstrip("\n"),
            "```",
            "",
        ]
    )


def build_sweep_bundles(
    *,
    runner: Runner,
    enumeration: SweepEnumerationResult,
    run_dir: Path,
    diff_cap: int = SWEEP_DIFF_CAP,
) -> tuple[SweepBundle, ...]:
    _private_mkdir(run_dir)
    bundles: list[SweepBundle] = []
    for commit in enumeration.selected:
        consumers, consumers_truncated = _discover_consumers(
            runner, symbols=commit.changed_symbols, defining_paths=commit.touched_paths
        )
        notices: list[str] = []
        if commit.diff_truncated:
            notices.append(f"diff truncated to {diff_cap} characters")
        if commit.symbols_truncated:
            notices.append(f"changed symbols truncated to {SWEEP_SYMBOL_CAP}")
        if consumers_truncated:
            notices.append(f"consumers truncated to {SWEEP_CONSUMER_CAP}")
        bundle_path = run_dir / f"sweep-{commit.merge_sha}-bundle.md"
        bundle = SweepBundle(
            pinned_tip=enumeration.pinned_tip,
            merge_sha=commit.merge_sha,
            base_sha=commit.base_sha,
            subject=commit.subject,
            touched_files=commit.touched_paths,
            chronic_tags=commit.chronic_zones,
            capped_diff=commit.capped_diff,
            truncation_notices=tuple(notices),
            changed_symbols=commit.changed_symbols,
            consumers=consumers,
            consumers_truncated=consumers_truncated,
            bundle_path=str(bundle_path),
        )
        _atomic_write_text(bundle_path, _render_sweep_bundle(bundle))
        bundles.append(bundle)
    return tuple(bundles)


def _write_sweep_prepare_artifacts(
    *,
    enumeration: SweepEnumerationResult,
    bundles: Sequence[SweepBundle],
    run_dir: Path,
) -> dict[str, object]:
    selected_path = run_dir / SWEEP_SELECTED_MANIFEST_NAME
    bundle_manifest_path = run_dir / SWEEP_BUNDLE_MANIFEST_NAME
    summary_path = run_dir / SWEEP_PREPARE_SUMMARY_NAME
    selected_payload = {
        "pinned_tip": enumeration.pinned_tip,
        "selected_count": len(enumeration.selected),
        "skipped_count": enumeration.skipped_count,
        "coverage_incomplete": enumeration.coverage_incomplete,
        "pending_shas": list(enumeration.pending_shas),
        "selected": [
            {
                "merge_sha": commit.merge_sha,
                "base_sha": commit.base_sha,
                "subject": commit.subject,
                "diff_size": commit.diff_size,
                "is_chronic": commit.is_chronic,
                "chronic_zones": list(commit.chronic_zones),
                "touched_paths": list(commit.touched_paths),
                "bundle_path": next(bundle.bundle_path for bundle in bundles if bundle.merge_sha == commit.merge_sha),
            }
            for commit in enumeration.selected
        ],
    }
    bundle_payload = {
        "pinned_tip": enumeration.pinned_tip,
        "bundles": [{"merge_sha": bundle.merge_sha, "path": bundle.bundle_path} for bundle in bundles],
    }
    summary_payload = {
        "pinned_tip": enumeration.pinned_tip,
        "selected_merge_manifest": str(selected_path),
        "bundle_path_manifest": str(bundle_manifest_path),
        "selected_count": len(enumeration.selected),
        "skipped_count": enumeration.skipped_count,
        "pending_shas": list(enumeration.pending_shas),
        "coverage_incomplete": enumeration.coverage_incomplete,
        "state_path": str(enumeration.state_path),
        "finder_raw_path": str(run_dir / SWEEP_FINDER_RAW_NAME),
        "refuter_raw_path": str(run_dir / SWEEP_REFUTER_RAW_NAME),
        "chronic_zone_names": list(enumeration.chronic_zone_names),
    }
    _write_json(selected_path, selected_payload)
    _write_json(bundle_manifest_path, bundle_payload)
    _write_json(summary_path, summary_payload)
    return cast("dict[str, object]", summary_payload)


def sweep_prepare(
    *,
    runner: Runner,
    run_dir: Path,
    ledger_path: Path,
    repo: str,
    sweep_max: int,
    diff_cap: int = SWEEP_DIFF_CAP,
    now: int | None = None,
    pinned_tip: str | None = None,
) -> dict[str, object]:
    _private_mkdir(run_dir)
    enumeration = sweep_enumeration(
        runner=runner,
        ledger_path=ledger_path,
        run_dir=run_dir,
        repo=repo,
        sweep_max=sweep_max,
        diff_cap=diff_cap,
        now=now,
        pinned_tip=pinned_tip,
    )
    bundles = build_sweep_bundles(runner=runner, enumeration=enumeration, run_dir=run_dir, diff_cap=diff_cap)
    if len(bundles) != len(enumeration.selected):
        raise AnalyzeBugsError("partial sweep bundle coverage")
    summary = _write_sweep_prepare_artifacts(enumeration=enumeration, bundles=bundles, run_dir=run_dir)
    return {
        "PINNED_TIP": enumeration.pinned_tip,
        "SELECTED_MERGE_MANIFEST": summary["selected_merge_manifest"],
        "BUNDLE_PATH_MANIFEST": summary["bundle_path_manifest"],
        "SELECTED_COUNT": len(enumeration.selected),
        "SKIPPED_COUNT": enumeration.skipped_count,
        "PENDING_SHAS": enumeration.pending_shas,
        "COVERAGE_INCOMPLETE": "true" if enumeration.coverage_incomplete else "false",
        "STATE_PATH": str(enumeration.state_path),
        "RUN_DIR": str(run_dir),
        "SWEEP_FINDER_RAW_PATH": str(run_dir / SWEEP_FINDER_RAW_NAME),
        "SWEEP_REFUTER_RAW_PATH": str(run_dir / SWEEP_REFUTER_RAW_NAME),
        "SWEEP_PREPARE_SUMMARY": str(run_dir / SWEEP_PREPARE_SUMMARY_NAME),
    }


def _read_strict_jsonl(path: Path, *, desc: str) -> list[dict[str, Any]]:
    """Read a line-oriented JSONL capture, rejecting blank-only and malformed rows."""
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AnalyzeBugsError(f"{desc} line {lineno}: not JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise AnalyzeBugsError(f"{desc} line {lineno}: row is not an object")
        rows.append(cast("dict[str, Any]", raw))
    return rows


def _valid_repo_relative_path(value: str) -> bool:
    """Return True for a non-empty, bounded, in-repo relative path with no traversal escapes."""
    if not value or len(value) > SWEEP_FINDING_FILE_CAP:
        return False
    if value[0] in ("/", "~") or "\x00" in value or "\\" in value:
        return False
    parts = [part for part in value.split("/") if part]
    if not parts:
        return False
    for part in parts:
        if part in {".", ".."} or any(ord(ch) < SWEEP_PRINTABLE_MIN for ch in part):
            return False
    return True


def _normalize_agent_text(value: str) -> str:
    """Strip C0 control chars (except tab/newline) and surrounding whitespace from agent text."""
    cleaned = "".join(ch for ch in value if ch in "\t\n" or ord(ch) >= SWEEP_PRINTABLE_MIN)
    return cleaned.strip()


def _parse_finder_finding(raw: Mapping[str, Any]) -> SweepFinding | str:
    if set(raw.keys()) != {"file", "symbol", "description", "severity", "confidence"}:
        return "finder finding has unexpected or missing fields"
    file_value = raw.get("file")
    if not isinstance(file_value, str) or not _valid_repo_relative_path(file_value):
        return "finder finding file must be a repository-relative path"
    symbol = raw.get("symbol")
    if not isinstance(symbol, str) or len(symbol) > SWEEP_FINDING_SYMBOL_CAP or "\x00" in symbol:
        return "finder finding symbol must be a bounded string"
    description = raw.get("description")
    if not isinstance(description, str) or len(description) > SWEEP_FINDING_DESC_CAP or "\x00" in description:
        return "finder finding description must be a bounded string"
    severity = raw.get("severity")
    if not isinstance(severity, str) or severity not in SWEEP_SEVERITIES:
        return "finder finding severity is unknown"
    confidence = raw.get("confidence")
    if not isinstance(confidence, str) or confidence not in SWEEP_CONFIDENCES:
        return "finder finding confidence is unknown"
    return SweepFinding(
        file=file_value,
        symbol=_normalize_agent_text(symbol),
        description=_normalize_agent_text(description),
        severity=severity,
        confidence=confidence,
    )


def _parse_finder_row(raw: Mapping[str, Any]) -> SweepFinderRow | str:
    if set(raw.keys()) != {"merge_sha", "findings"}:
        return "finder row has unexpected or missing fields"
    merge_sha = raw.get("merge_sha")
    if not isinstance(merge_sha, str) or not FULL_SHA_RE.fullmatch(merge_sha):
        return "finder merge_sha must be a full 40-character SHA"
    findings_raw = raw.get("findings")
    if not isinstance(findings_raw, list):
        return "finder findings must be a list"
    if len(findings_raw) > SWEEP_FINDINGS_PER_MERGE_CAP:
        return f"finder findings exceed per-merge cap {SWEEP_FINDINGS_PER_MERGE_CAP}"
    findings: list[SweepFinding] = []
    for item in findings_raw:
        if not isinstance(item, dict):
            return "finder finding must be an object"
        parsed = _parse_finder_finding(cast("Mapping[str, Any]", item))
        if isinstance(parsed, str):
            return parsed
        findings.append(parsed)
    return SweepFinderRow(merge_sha=merge_sha, findings=tuple(findings))


def _parse_refuter_queue_row(raw: Mapping[str, Any]) -> SweepRefuterQueueRow | str:
    required = {"merge_sha", "finding_index", "file", "symbol", "description", "severity", "confidence"}
    if set(raw.keys()) != required:
        return "refuter queue row has unexpected or missing fields"
    merge_sha = raw.get("merge_sha")
    if not isinstance(merge_sha, str) or not FULL_SHA_RE.fullmatch(merge_sha):
        return "queue merge_sha must be a full 40-character SHA"
    finding_index = raw.get("finding_index")
    if isinstance(finding_index, bool) or not isinstance(finding_index, int) or finding_index < 0:
        return "queue finding_index must be a non-negative integer"
    return SweepRefuterQueueRow(
        merge_sha=merge_sha,
        finding_index=finding_index,
        file=str(raw.get("file") or ""),
        symbol=str(raw.get("symbol") or ""),
        description=str(raw.get("description") or ""),
        severity=str(raw.get("severity") or ""),
        confidence=str(raw.get("confidence") or ""),
    )


def _parse_refuter_result(raw: Mapping[str, Any]) -> SweepRefutationResult | str:
    if set(raw.keys()) != {"merge_sha", "finding_index", "verdict"}:
        return "refuter row has unexpected or missing fields"
    merge_sha = raw.get("merge_sha")
    if not isinstance(merge_sha, str) or not FULL_SHA_RE.fullmatch(merge_sha):
        return "refuter merge_sha must be a full 40-character SHA"
    finding_index = raw.get("finding_index")
    if isinstance(finding_index, bool) or not isinstance(finding_index, int) or finding_index < 0:
        return "refuter finding_index must be a non-negative integer"
    verdict = raw.get("verdict")
    if not isinstance(verdict, str) or verdict not in SWEEP_REFUTER_VERDICTS:
        return "refuter verdict is unknown"
    return SweepRefutationResult(merge_sha=merge_sha, finding_index=finding_index, verdict=verdict)


def _load_selected_manifest(run_dir: Path) -> tuple[str, tuple[str, ...], dict[str, object]]:
    """Load the prepared selected-merge manifest and return (pinned_tip, ordered SHAs, raw summary)."""
    manifest_path = run_dir / SWEEP_SELECTED_MANIFEST_NAME
    if not manifest_path.is_file():
        raise AnalyzeBugsError(f"selected-merge manifest missing: {manifest_path}")
    manifest = _load_json(manifest_path)
    pinned_tip = _full_sha(manifest.get("pinned_tip"), label="selected manifest pinned_tip")
    selected_raw = manifest.get("selected")
    if not isinstance(selected_raw, list):
        raise AnalyzeBugsError(f"selected manifest lacks selected array: {manifest_path}")
    selected_shas: list[str] = []
    for item in selected_raw:
        if not isinstance(item, dict):
            raise AnalyzeBugsError(f"selected manifest entry is not an object: {manifest_path}")
        selected_shas.append(_full_sha(item.get("merge_sha"), label="selected merge_sha"))
    summary: dict[str, object] = {
        "manifest_path": str(manifest_path),
        "pinned_tip": pinned_tip,
        "selected_count": len(selected_shas),
        "skipped_count": int(manifest.get("skipped_count", 0) or 0) if str(manifest.get("skipped_count", 0) or 0).lstrip("-").isdigit() else 0,
        "coverage_incomplete": bool(manifest.get("coverage_incomplete", False)),
        "pending_shas": _manifest_pending_shas(manifest),
    }
    return pinned_tip, tuple(selected_shas), summary


def _manifest_pending_shas(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    pending_raw = manifest.get("pending_shas")
    if not isinstance(pending_raw, list):
        return ()
    return tuple(_full_sha(item, label="pending_shas entry") for item in pending_raw)


def _write_sweep_refuter_queue(path: Path, rows: Sequence[SweepRefuterQueueRow]) -> None:
    text = "".join(json.dumps(asdict(row), sort_keys=True) + "\n" for row in rows)
    _atomic_write_text(path, text)


def sweep_ingest_finder(*, run_dir: Path) -> dict[str, object]:
    """Validate raw finder JSONL against the prepared manifest; write the deterministic refuter queue."""
    pinned_tip, selected_shas, summary = _load_selected_manifest(run_dir)
    queue_path = run_dir / SWEEP_REFUTER_QUEUE_NAME
    finder_raw_path = run_dir / SWEEP_FINDER_RAW_NAME
    selected_set = set(selected_shas)

    if not selected_shas:
        # Zero selected merges: bypass finder-file parsing and dispatch.
        _atomic_write_text(queue_path, "")
        return {
            "PINNED_TIP": pinned_tip,
            "SELECTED_MERGE_MANIFEST": summary["manifest_path"],
            "INGEST_ACCEPTED": 0,
            "REFUTER_QUEUE_PATH": str(queue_path),
            "REFUTER_QUEUE_COUNT": 0,
        }

    if not finder_raw_path.is_file():
        raise AnalyzeBugsError(f"finder raw capture missing: {finder_raw_path}")
    raw_rows = _read_strict_jsonl(finder_raw_path, desc="finder raw")
    if not raw_rows:
        raise AnalyzeBugsError(f"finder raw capture is empty: {finder_raw_path}")

    accepted: dict[str, SweepFinderRow] = {}
    for lineno, raw in enumerate(raw_rows, 1):
        parsed = _parse_finder_row(cast("Mapping[str, Any]", raw))
        if isinstance(parsed, str):
            raise AnalyzeBugsError(f"finder raw line {lineno}: {parsed}")
        if parsed.merge_sha in accepted:
            raise AnalyzeBugsError(f"finder raw line {lineno}: duplicate merge_sha {parsed.merge_sha}")
        if parsed.merge_sha not in selected_set:
            raise AnalyzeBugsError(f"finder raw line {lineno}: foreign merge_sha {parsed.merge_sha}")
        accepted[parsed.merge_sha] = parsed

    missing = [sha for sha in selected_shas if sha not in accepted]
    if missing:
        raise AnalyzeBugsError(f"finder raw missing selected merges: {', '.join(missing)}")

    queue_rows: list[SweepRefuterQueueRow] = []
    for sha in selected_shas:
        for index, finding in enumerate(accepted[sha].findings):
            queue_rows.append(
                SweepRefuterQueueRow(
                    merge_sha=sha,
                    finding_index=index,
                    file=finding.file,
                    symbol=finding.symbol,
                    description=finding.description,
                    severity=finding.severity,
                    confidence=finding.confidence,
                )
            )
    _write_sweep_refuter_queue(queue_path, queue_rows)
    return {
        "PINNED_TIP": pinned_tip,
        "SELECTED_MERGE_MANIFEST": summary["manifest_path"],
        "INGEST_ACCEPTED": len(accepted),
        "REFUTER_QUEUE_PATH": str(queue_path),
        "REFUTER_QUEUE_COUNT": len(queue_rows),
    }


def _write_sweep_validated(path: Path, artifact: SweepValidatedArtifact) -> None:
    _write_json(path, asdict(artifact))


def sweep_ingest_refuter(*, run_dir: Path) -> dict[str, object]:
    """Validate raw refuter JSONL against the prepared queue; write the validated sweep-result artifact."""
    pinned_tip, _selected_shas, summary = _load_selected_manifest(run_dir)
    queue_path = run_dir / SWEEP_REFUTER_QUEUE_NAME
    refuter_raw_path = run_dir / SWEEP_REFUTER_RAW_NAME
    if not queue_path.is_file():
        raise AnalyzeBugsError(f"refuter queue missing: {queue_path}")
    queue_raw = _read_strict_jsonl(queue_path, desc="refuter queue")

    queue_order: list[tuple[str, int]] = []
    queue_by_key: dict[tuple[str, int], SweepRefuterQueueRow] = {}
    for lineno, raw in enumerate(queue_raw, 1):
        parsed = _parse_refuter_queue_row(cast("Mapping[str, Any]", raw))
        if isinstance(parsed, str):
            raise AnalyzeBugsError(f"refuter queue line {lineno}: {parsed}")
        key = (parsed.merge_sha, parsed.finding_index)
        if key in queue_by_key:
            raise AnalyzeBugsError(f"refuter queue line {lineno}: duplicate queue key")
        queue_by_key[key] = parsed
        queue_order.append(key)
    expected_keys = set(queue_by_key)

    def _empty_artifact() -> SweepValidatedArtifact:
        return SweepValidatedArtifact(
            pinned_tip=pinned_tip,
            selected_manifest_path=str(summary["manifest_path"]),
            selected_count=int(summary["selected_count"]),
            skipped_count=int(summary["skipped_count"]),
            pending_shas=cast("tuple[str, ...]", summary["pending_shas"]),
            coverage_incomplete=bool(summary["coverage_incomplete"]),
            candidates=(),
        )

    if not expected_keys:
        # Empty queue: a successful zero-candidate result; no refuter file required.
        validated_path = run_dir / SWEEP_VALIDATED_NAME
        _write_sweep_validated(validated_path, _empty_artifact())
        return {
            "PINNED_TIP": pinned_tip,
            "SELECTED_MERGE_MANIFEST": summary["manifest_path"],
            "SWEEP_VALIDATED_PATH": str(validated_path),
            "CANDIDATE_COUNT": 0,
            "REFUTER_QUEUE_COUNT": 0,
        }

    if not refuter_raw_path.is_file():
        raise AnalyzeBugsError(f"refuter raw capture missing: {refuter_raw_path}")
    result_rows = _read_strict_jsonl(refuter_raw_path, desc="refuter raw")
    if not result_rows:
        raise AnalyzeBugsError(f"refuter raw capture is empty: {refuter_raw_path}")

    verdict_by_key: dict[tuple[str, int], str] = {}
    seen_keys: set[tuple[str, int]] = set()
    for lineno, raw in enumerate(result_rows, 1):
        parsed = _parse_refuter_result(cast("Mapping[str, Any]", raw))
        if isinstance(parsed, str):
            raise AnalyzeBugsError(f"refuter raw line {lineno}: {parsed}")
        key = (parsed.merge_sha, parsed.finding_index)
        if key in seen_keys:
            raise AnalyzeBugsError(f"refuter raw line {lineno}: duplicate verdict for key")
        if key not in expected_keys:
            raise AnalyzeBugsError(f"refuter raw line {lineno}: foreign verdict key")
        seen_keys.add(key)
        verdict_by_key[key] = parsed.verdict

    missing_keys = expected_keys - seen_keys
    if missing_keys:
        raise AnalyzeBugsError(f"refuter raw missing {len(missing_keys)} queued verdict(s)")

    candidates: list[SweepCandidate] = []
    for key in queue_order:
        if verdict_by_key[key] != "survives":
            continue
        row = queue_by_key[key]
        candidates.append(
            SweepCandidate(
                merge_sha=row.merge_sha,
                file=row.file,
                symbol=row.symbol,
                description=row.description,
                severity=row.severity,
                confidence=row.confidence,
            )
        )
    artifact = SweepValidatedArtifact(
        pinned_tip=pinned_tip,
        selected_manifest_path=str(summary["manifest_path"]),
        selected_count=int(summary["selected_count"]),
        skipped_count=int(summary["skipped_count"]),
        pending_shas=cast("tuple[str, ...]", summary["pending_shas"]),
        coverage_incomplete=bool(summary["coverage_incomplete"]),
        candidates=tuple(candidates),
    )
    validated_path = run_dir / SWEEP_VALIDATED_NAME
    _write_sweep_validated(validated_path, artifact)
    return {
        "PINNED_TIP": pinned_tip,
        "SELECTED_MERGE_MANIFEST": summary["manifest_path"],
        "SWEEP_VALIDATED_PATH": str(validated_path),
        "CANDIDATE_COUNT": len(candidates),
        "REFUTED_COUNT": len(expected_keys) - len(candidates),
        "REFUTER_QUEUE_COUNT": len(expected_keys),
    }


def sweep_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python/cli.py analyze-bugs sweep")
    sub = parser.add_subparsers(dest="subphase", required=True)
    prepare = sub.add_parser("prepare", help="enumerate merges and write sweep evidence bundles")
    prepare.add_argument("--run-dir", required=True)
    prepare.add_argument("--ledger-path", required=True)
    prepare.add_argument("--repo", default="")
    prepare.add_argument(
        "--sweep-max",
        type=lambda value: _positive_int(value, name="--sweep-max"),
        default=SWEEP_DEFAULT_MAX,
    )
    prepare.add_argument(
        "--diff-cap",
        type=lambda value: _positive_int(value, name="--diff-cap"),
        default=SWEEP_DIFF_CAP,
    )
    ingest_finder = sub.add_parser(
        "ingest-finder",
        help="validate raw finder JSONL against the prepared manifest and write the refuter queue",
    )
    ingest_finder.add_argument("--run-dir", required=True)
    ingest_refuter = sub.add_parser(
        "ingest-refuter",
        help="validate raw refuter JSONL against the prepared queue and write the sweep-result artifact",
    )
    ingest_refuter.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)
    if args.subphase == "prepare":
        try:
            runner = _runner()
            repo = resolve_repo(runner, args.repo)
            payload = sweep_prepare(
                runner=runner,
                run_dir=Path(args.run_dir),
                ledger_path=Path(args.ledger_path),
                repo=repo,
                sweep_max=args.sweep_max,
                diff_cap=args.diff_cap,
            )
        except AnalyzeBugsError as exc:
            return _fail(str(exc))
        _emit_kvs(
            {
                "PINNED_TIP": payload["PINNED_TIP"],
                "SELECTED_MERGE_MANIFEST": payload["SELECTED_MERGE_MANIFEST"],
                "BUNDLE_PATH_MANIFEST": payload["BUNDLE_PATH_MANIFEST"],
                "SELECTED_COUNT": payload["SELECTED_COUNT"],
                "SKIPPED_COUNT": payload["SKIPPED_COUNT"],
                "PENDING_SHAS": payload["PENDING_SHAS"],
                "COVERAGE_INCOMPLETE": payload["COVERAGE_INCOMPLETE"],
                "STATE_PATH": payload["STATE_PATH"],
                "RUN_DIR": payload["RUN_DIR"],
                "SWEEP_FINDER_RAW_PATH": payload["SWEEP_FINDER_RAW_PATH"],
                "SWEEP_REFUTER_RAW_PATH": payload["SWEEP_REFUTER_RAW_PATH"],
            }
        )
        return 0
    if args.subphase == "ingest-finder":
        try:
            payload = sweep_ingest_finder(run_dir=Path(args.run_dir))
        except AnalyzeBugsError as exc:
            return _fail(str(exc))
        _emit_kvs(payload)
        return 0
    if args.subphase == "ingest-refuter":
        try:
            payload = sweep_ingest_refuter(run_dir=Path(args.run_dir))
        except AnalyzeBugsError as exc:
            return _fail(str(exc))
        _emit_kvs(payload)
        return 0
    return _fail(f"unknown sweep subphase: {args.subphase}")
