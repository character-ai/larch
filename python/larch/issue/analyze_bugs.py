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
import sys
import time
from collections import OrderedDict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final, cast

from larch.core import config, proc
from larch.git import gh
from larch.core.proc import Runner
from larch.issue.issue_wire import strip_named_block
from larch.report.report_tokens_cost import rate_row

BUG_PREFIX: Final = "[BUG]"
DEFAULT_DIFF_CAP: Final = 60_000
DEFAULT_BODY_CAP: Final = 8_000
GIT_LOG_SCAN_LIMITS: Final = (100, 200, 400, 800, 1600, 3200)
TRIAGE_VERDICTS: Final = set(config.ANALYZE_BUGS_TRIAGE_VERDICTS)
DEEP_VERDICTS: Final = set(config.ANALYZE_BUGS_DEEP_VERDICTS)
MECHANICAL_VERDICTS: Final = {"NOT_FIXED", "WONTFIX", "NEEDS_DEEP"}
TERMINAL_FOLLOWUP_VERDICTS: Final = {"NOT_FIXED", "INCOMPLETE", "REGRESSED"}
PLAN_MALFORMED_REASON: Final = "malformed larch:plan block"


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
    deep_verdict: str = ""
    deep_reason: str = ""
    sampled: bool = False
    stages_complete: tuple[str, ...] = ()
    updated_at: int = 0


@dataclass(frozen=True)
class TriageIngest:
    issue: int
    verdict: str
    missing_items: tuple[str, ...]
    reason: str
    needs_deep: bool


@dataclass(frozen=True)
class DeepIngest:
    issue: int
    verdict: str
    reason: str


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


def _parse_json_array(stdout: str, *, desc: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(stdout or "[]")
    except json.JSONDecodeError as exc:
        raise AnalyzeBugsError(f"{desc}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise AnalyzeBugsError(f"{desc}: JSON was not an array")
    return [cast("dict[str, Any]", item) for item in data if isinstance(item, dict)]


def resolve_repo(runner: Runner, explicit: str = "") -> str:
    if explicit:
        return explicit
    result = runner.run(["gh", "repo", "view", "--json", "nameWithOwner"])
    if result.returncode != 0:
        raise AnalyzeBugsError("could not resolve GitHub repo; pass --repo OWNER/REPO")
    data = _parse_json_object(result.stdout, desc="gh repo view")
    repo = data.get("nameWithOwner")
    if not isinstance(repo, str) or "/" not in repo:
        raise AnalyzeBugsError("gh repo view did not return nameWithOwner")
    return repo


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


def _bug_title(title: str) -> bool:
    return title.lstrip().startswith(BUG_PREFIX)


def _issue_list_argv(repo: str) -> list[str]:
    return [
        "gh",
        "api",
        "--paginate",
        f"repos/{repo}/issues?state=all&per_page=100",
    ]


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
    result = runner.run(_issue_list_argv(repo))
    if result.returncode != 0:
        raise AnalyzeBugsError(f"gh issue list failed: {(result.stderr or result.stdout).strip()}")
    raw_rows = [row for row in gh.loads_json_paginated_list(result.stdout) if isinstance(row, dict)]
    last_corpus_len = len(raw_rows)
    for row in raw_rows:
        issue = _issue_from_raw(cast("Mapping[str, Any]", row))
        if issue is None:
            continue
        if _bug_title(issue.title):
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
        result = runner.run(["gh", "pr", "view", pr_number, "--repo", repo, "--json", "mergeCommit"])
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
    _atomic_write_text(body_path, _capped(stripped_body, body_cap))
    bundle = "\n".join(
        [
            f"# Bug #{issue.number}: {issue.title}",
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
        deep_verdict=str(raw.get("deep_verdict") or ""),
        deep_reason=str(raw.get("deep_reason") or ""),
        sampled=bool(raw.get("sampled", False)),
        stages_complete=stages,
        updated_at=int(raw.get("updated_at", 0) or 0),
    )


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


def _priority_deep_candidates(
    *,
    bundles: Sequence[BundleRecord],
    ledger: Mapping[str, LedgerRecord],
    sample: int,
    refresh: bool,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    by_priority: list[tuple[int, BundleRecord, LedgerRecord | None, str]] = []
    for bundle in bundles:
        record = _record_for_bundle(ledger, bundle)
        if bundle.fix_sha and _complete(record, "deep", refresh=refresh):
            continue
        if bundle.mechanical_verdict == "NEEDS_DEEP":
            by_priority.append((0, bundle, record, "mechanical"))
            continue
        if record and record.triage_verdict == "SUSPECT":
            by_priority.append((1, bundle, record, "triage"))
        elif record and (record.triage_verdict == "NEEDS_DEEP" or record.triage_needs_deep):
            by_priority.append((2, bundle, record, "triage"))
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
            if not record or record.triage_verdict not in {"FIXED_CLEAR", "FIXED_LIKELY"}:
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


def _upsert_record(base: LedgerRecord | None, bundle: BundleRecord, *, triage: TriageIngest | None = None, deep: DeepIngest | None = None, sampled: bool | None = None) -> LedgerRecord:
    stages = set(base.stages_complete if base else ())
    triage_verdict = base.triage_verdict if base else ""
    triage_reason = base.triage_reason if base else ""
    triage_missing = base.triage_missing_items if base else ()
    triage_needs_deep = base.triage_needs_deep if base else False
    deep_verdict = base.deep_verdict if base else ""
    deep_reason = base.deep_reason if base else ""
    sampled_value = base.sampled if base else False
    if triage:
        stages.add("triage")
        triage_verdict = triage.verdict
        triage_reason = triage.reason
        triage_missing = triage.missing_items
        triage_needs_deep = triage.needs_deep
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
        deep_verdict=deep_verdict,
        deep_reason=deep_reason,
        sampled=sampled_value,
        stages_complete=tuple(sorted(stages)),
        updated_at=int(time.time()),
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
    _manifest, bundles = _load_manifest(manifest_path)
    ledger, corrupt_count = load_ledger(ledger_path)
    task_model, rate_model = _validate_deep_model(deep_model)
    pending_triage = [bundle for bundle in bundles if bundle.fix_sha and not bundle.mechanical_verdict and not _complete(_record_for_bundle(ledger, bundle), "triage", refresh=refresh)]
    triage_paths = _write_triage_batches(run_dir, pending_triage, batch_size=batch_size)
    candidates = _priority_deep_candidates(bundles=bundles, ledger=ledger, sample=sample, refresh=refresh)
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
    if not _strict_keys(raw, {"issue", "verdict", "missing_items", "reason", "needs_deep"}):
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
    return TriageIngest(issue=issue, verdict=verdict, missing_items=tuple(missing), reason=reason, needs_deep=needs_deep)


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
    parser.add_argument("--sample", type=int, default=0)
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


def _final_verdict(bundle: BundleRecord, record: LedgerRecord | None) -> tuple[str, str, tuple[str, ...], bool]:
    if bundle.mechanical_verdict:
        return bundle.mechanical_verdict, bundle.mechanical_reason, (), False
    if record and record.deep_verdict:
        return record.deep_verdict, record.deep_reason, (), record.sampled
    if record and record.triage_verdict:
        if record.triage_verdict in {"SUSPECT", "NEEDS_DEEP"} or record.triage_needs_deep:
            return "NEEDS_DEEP", record.triage_reason, record.triage_missing_items, record.sampled
        return record.triage_verdict, record.triage_reason, record.triage_missing_items, record.sampled
    if bundle.mechanical_verdict:
        return bundle.mechanical_verdict, bundle.mechanical_reason, (), False
    return "NEEDS_DEEP", "not yet triaged", (), False


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
    summary_path = run_dir / "ledger-summary.json"
    summary = _load_json(summary_path) if summary_path.exists() else {}
    truncated = {int(item) for item in summary.get("DEEP_TRUNCATED_ISSUES", []) if isinstance(item, int)}
    rows: list[tuple[BundleRecord, str, str, tuple[str, ...], bool]] = []
    verdict_values: list[str] = []
    for bundle in bundles:
        record = _record_for_bundle(ledger, bundle)
        verdict, reason, missing, sampled = _final_verdict(bundle, record)
        if bundle.issue_number in truncated:
            verdict = "NEEDS_DEEP"
            reason = "deep cap truncated this candidate"
        rows.append((bundle, verdict, reason, missing, sampled))
        verdict_values.append(verdict)
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
    detail_rows = [["Issue", "Fix", "Verdict", "Reason", "Missing items"]]
    for bundle, verdict, reason, missing, _sampled in rows:
        issue_link = f"#{bundle.issue_number}" if not bundle.url else f"[#{bundle.issue_number}]({bundle.url})"
        detail_rows.append([issue_link, _short_sha(bundle.fix_sha), verdict, reason, "; ".join(missing)])
    sampled_rows = [(bundle, verdict) for bundle, verdict, _reason, _missing, sampled in rows if sampled]
    sampled_failures = sum(1 for _bundle, verdict in sampled_rows if verdict in {"INCOMPLETE", "REGRESSED", "NOT_FIXED", "UNVERIFIABLE"})
    sample_rate = (sampled_failures / len(sampled_rows)) if sampled_rows else 0.0
    followups = [(bundle, verdict, reason) for bundle, verdict, reason, _missing, _sampled in rows if verdict in TERMINAL_FOLLOWUP_VERDICTS]
    followup_path = run_dir / "follow-up-issue.md"
    if followups:
        body_lines = ["# Analyze-bugs follow-up", "", f"Repo: {manifest.get('repo', '')}", "", "Findings:"]
        for bundle, verdict, reason in followups:
            body_lines.append(f"- #{bundle.issue_number}: {verdict}. {reason}")
        _atomic_write_text(followup_path, "\n".join(body_lines) + "\n")
    rate_model = str(summary.get("DEEP_RATE_MODEL") or config.ANALYZE_BUGS_DEEP_MODEL_ALIASES["sonnet"][1])
    cost = _estimate_cost(bundles=bundles, deep_rate_model=rate_model)
    parts = [
        "# Analyze Bugs Report",
        "",
        f"Repo: {manifest.get('repo', '')}",
        f"Evidence ref: {manifest.get('evidence_ref', '')}",
        f"Requested: {manifest.get('bugs_requested', '')}",
        f"Selected: {manifest.get('bugs_selected', '')}",
        "",
        "## Counts",
        "",
        count_table,
        "",
        "## Issues",
        "",
        _markdown_table(detail_rows),
        "",
        "## Sample calibration",
        "",
        f"Sample size: {len(sampled_rows)}",
        f"Sampled failures: {sampled_failures}",
        f"Triage false-pass rate: {sample_rate:.2%}",
        "",
    ]
    if corrupt_count:
        parts.extend([f"Ledger corrupt lines quarantined: {corrupt_count}", ""])
    if followups:
        parts.extend(["## Follow-up issue body", "", f"Follow-up body file: {followup_path}", ""])
    parts.append(f"ANALYZE_BUGS_COST_ESTIMATE={cost}")
    report = "\n".join(parts) + "\n"
    _atomic_write_text(run_dir / "report.md", report)
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
