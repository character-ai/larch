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
    deep_verdict: str = ""
    deep_reason: str = ""
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


@dataclass(frozen=True)
class DeepIngest:
    issue: int
    verdict: str
    reason: str


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
        "gh",
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
        result = runner.run(_issue_pr_refs_argv(repo, issue_number=issue.number))
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


def _later_history(runner: Runner, *, fix_sha: str, evidence_ref: str, files: Sequence[str]) -> str:
    if not fix_sha or not files:
        return ""
    return _git_stdout(runner, ["git", "log", f"{fix_sha}..{evidence_ref}", "--format=%H:%s", "--", *files])


def _later_history_hash(*, fix_sha: str, evidence_ref: str, files: Sequence[str], later_history: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(f"fix={fix_sha}\nref={evidence_ref}\n".encode())
    for path in files:
        hasher.update(f"file={path}\n".encode())
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
    later = _later_history(runner, fix_sha=fix.fix_sha, evidence_ref=evidence_ref, files=touched)
    later_hash = _later_history_hash(fix_sha=fix.fix_sha, evidence_ref=evidence_ref, files=touched, later_history=later)
    cache_key = _cache_key(
        issue_number=issue.number,
        fix_sha=fix.fix_sha,
        later_history_hash=later_hash,
        state=issue.state,
        state_reason=issue.state_reason,
    )

    body_path = run_dir / f"issue-{issue.number}-body.md"
    bundle_path = run_dir / f"issue-{issue.number}-bundle.md"
    diff = _git_stdout(runner, ["git", "show", "--unified=1", "--format=medium", fix.fix_sha]) if fix.fix_sha else ""
    revert_scan = _git_stdout(runner, ["git", "log", f"{fix.fix_sha}..{evidence_ref}", "--regexp-ignore-case", "--grep", "revert", "--format=%H:%s", "--", *touched]) if fix.fix_sha and touched else ""
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
            "## Later commits touching those files",
            later or "(none)",
            "",
            "## Revert scan",
            revert_scan or "(none)",
            "",
            "## Capped fix diff",
            _capped(diff, diff_cap),
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
        deep_verdict=str(raw.get("deep_verdict") or ""),
        deep_reason=str(raw.get("deep_reason") or ""),
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
    deep_verdict = base.deep_verdict if base else ""
    deep_reason = base.deep_reason if base else ""
    sampled_value = base.sampled if base else False
    if triage:
        stages.add("triage")
        triage_verdict = triage.verdict
        triage_reason = triage.reason
        triage_missing = triage.missing_items
        triage_needs_deep = triage.needs_deep
        triage_evidence_verified = True
        stages.discard("deep")
        deep_verdict = ""
        deep_reason = ""
    if deep:
        stages.add("deep")
        deep_verdict = deep.verdict
        deep_reason = deep.reason
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
        deep_verdict=deep_verdict,
        deep_reason=deep_reason,
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


def _parse_triage_row(raw: Mapping[str, Any]) -> TriageIngest | str:
    if not _strict_keys(raw, {"issue", "verdict", "missing_items", "reason", "needs_deep", "evidence_token"}):
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
    return TriageIngest(issue=issue, verdict=verdict, missing_items=tuple(missing), reason=reason, needs_deep=needs_deep, evidence_token=evidence_token)


def _parse_deep_row(raw: Mapping[str, Any]) -> DeepIngest | str:
    if not _strict_keys(raw, {"issue", "verdict", "reason"}):
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
    return DeepIngest(issue=issue, verdict=verdict, reason=reason)


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


def render_report(*, manifest_path: Path, ledger_path: Path, run_dir: Path) -> str:
    manifest, bundles = _load_manifest(manifest_path)
    ledger, corrupt_count = load_ledger(ledger_path)
    analytics = build_analytics_view(manifest=manifest, bundles=bundles, ledger_path=ledger_path, runner=_runner())
    summary_path = run_dir / "ledger-summary.json"
    summary = _load_json(summary_path) if summary_path.exists() else {}
    truncated = {int(item) for item in summary.get("DEEP_TRUNCATED_ISSUES", []) if isinstance(item, int)}
    rows: list[tuple[BundleRecord, str, str, str, tuple[str, ...], bool]] = []
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
    sampled_rows = [(bundle, verdict) for bundle, verdict, _tier, _reason, _missing, sampled in rows if sampled]
    sampled_failures = sum(1 for _bundle, verdict in sampled_rows if verdict in {"INCOMPLETE", "REGRESSED", "NOT_FIXED", "UNVERIFIABLE"})
    sample_rate = (sampled_failures / len(sampled_rows)) if sampled_rows else 0.0
    followups = [(bundle, verdict, reason) for bundle, verdict, _tier, reason, _missing, _sampled in rows if verdict in TERMINAL_FOLLOWUP_VERDICTS]
    followup_path = run_dir / "follow-up-issue.md"
    if followups:
        body_lines = ["# Analyze-bugs follow-up", "", f"Repo: {manifest.get('repo', '')}", "", "Findings:"]
        for bundle, verdict, reason in followups:
            body_lines.append(f"- #{bundle.issue_number}: {verdict}. {reason}")
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
    if corrupt_count:
        parts.extend([f"Ledger corrupt lines quarantined: {corrupt_count}", ""])
    if followups:
        parts.extend(["## Follow-up issue body", "", f"Follow-up body file: {followup_path}", ""])
    if analytics.chronic_zones:
        parts.extend([f"Suggestion: run /learn-from-bugs scoped to {', '.join(zone.zone for zone in analytics.chronic_zones)}.", ""])
    parts.append(f"ANALYZE_BUGS_COST_ESTIMATE={cost}")
    report = "\n".join(parts) + "\n"
    _atomic_write_text(run_dir / "report.md", report)
    if analytics.hydrated_records:
        _append_private_jsonl(ledger_path, (_record_json(record) for record in analytics.hydrated_records))
    _write_json(run_dir / "run-state.json", asdict(snapshot))
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
