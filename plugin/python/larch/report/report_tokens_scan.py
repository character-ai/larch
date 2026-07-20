"""Scan synchronized larch run logs for report-token records."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from collections.abc import Mapping

from larch.core import config
from larch.core import redact
from larch.core.repo_roots import repo_root_probe
from larch.report import tokens
from larch.report import run_log_corpus
from larch.errors import ShipError
from larch.git import gh
from larch.core.proc import Runner
from larch.report.report_tokens_models import (
    PhaseRow,
    RunRecord,
    Skill,
    VENDOR_COMPONENTS,
    VENDORS,
    effective_vendor_total,
    safe_int,
    vendor_totals_from_report,
)

_JSON_ERROR = object()

@dataclass(frozen=True)
class ScanResult:
    repo_root: Path
    repo_slug: str | None
    records: tuple[RunRecord, ...]


@dataclass(frozen=True)
class ScanRequest:
    skill: Skill
    repo_override: str | None
    limit: int | None
    resolve_repo: bool
    corpus_root: Path | None = None

def _warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)

def _json_file(path: Path) -> object:
    if path.is_symlink():
        _warn(f"{path.name} at {path} is a symlink; skipping")
        return _JSON_ERROR
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _warn(f"invalid {path.name} at {path}: {exc}; skipping")
        return _JSON_ERROR

def _as_mapping(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", value) if isinstance(value, dict) else {}

def _repo_root(runner: Runner) -> Path:
    try:
        result = repo_root_probe(runner=runner)
    except OSError as exc:
        raise ShipError(f"ERROR: could not resolve git repository root: {exc}") from exc
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    detail = (result.stderr or result.stdout).strip()
    suffix = f": {detail}" if detail else ""
    raise ShipError(f"ERROR: could not resolve git repository root{suffix}")

_REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

def _valid_repo_slug(value: str) -> bool:
    return bool(_REPO_SLUG_RE.fullmatch(value)) and not any(part in {".", ".."} for part in value.split("/"))

def _repo_slug(*, runner: Runner, override: str | None) -> str | None:
    if override:
        if _valid_repo_slug(override):
            return override
        raise ShipError(f"ERROR: {config.ENV_LARCH_REPORT_TOKENS_REPO} must be a safe OWNER/REPO slug")
    detailed = gh.resolve_repo_detailed(runner)
    if detailed.status == "valid":
        return detailed.candidate
    failure = detailed.primary_failure
    if failure is not None and failure.kind == "oserror":
        print(
            f"ERROR: could not resolve GitHub repo owner/name: {redact.redact(failure.detail)}",
            file=sys.stderr,
        )
        return None
    if failure is not None and failure.kind == "nonzero":
        detail = (failure.stderr or failure.stdout).strip()
        suffix = f": {redact.redact(detail)}" if detail else ""
        print(f"ERROR: could not resolve GitHub repo owner/name{suffix}", file=sys.stderr)
        return None
    print("ERROR: could not resolve GitHub repo owner/name", file=sys.stderr)
    return None

def _token_basename(skill: Skill) -> str:
    return "token-report-final.json" if skill == "design" else "token-report.json"

def _workflow(*, _run_dir: Path, _skill: Skill) -> str:
    return ""

def _has_numeric_tokens(report: Mapping[str, object]) -> bool:
    for vendor in VENDORS:
        bucket = _as_mapping(report.get(f"BUCKETS_{vendor}"))
        if any(safe_int(value=bucket.get(key)) > 0 for key in VENDOR_COMPONENTS[vendor]):
            return True
        totals = vendor_totals_from_report(report=report, vendor=vendor)
        if effective_vendor_total(totals=totals, vendor=vendor) > 0:
            return True
    return False

def _phase_rows(report: Mapping[str, object]) -> tuple[PhaseRow, ...]:
    rows: list[PhaseRow] = []
    for vendor in VENDORS:
        vendor_obj = _as_mapping(report.get(vendor))
        per_step = vendor_obj.get("per_step")
        if not isinstance(per_step, list):
            continue
        step_items = cast("list[object]", per_step)
        for item in step_items:
            item_map = _as_mapping(item)
            totals = _as_mapping(item_map.get("totals"))
            rows.append(PhaseRow(
                vendor=vendor,
                step=str(item_map.get("step") or "unknown"),
                input=safe_int(value=totals.get("input")),
                cache_read=safe_int(value=totals.get("cache_read")),
                cache_create=safe_int(value=totals.get("cache_create")),
                output=safe_int(value=totals.get("output")),
                total=safe_int(value=totals.get("total")),
            ))
    return tuple(rows)

def _session_scoped_ledger_path(run_dir: Path) -> Path | None:
    """Resolve the durable ledger for a run dir using session-id when present."""
    return tokens.run_log_ledger_path(run_dir)


def _ledger_fallback_report(run_dir: Path) -> Mapping[str, object] | None:
    """Recover a token report from the durable session ledger when the canonical
    token-report{,-final}.json is absent or unusable (issue #5133). Returns None
    when no usable ledger exists. Symlinked ledgers are skipped for safety.
    """
    ledger = _session_scoped_ledger_path(run_dir)
    if ledger is None:
        return None
    try:
        return tokens.build_report_from_ledgers([ledger])
    except ValueError:
        return None
    except OSError as exc:
        _warn(f"could not read token ledger for {run_dir}: {exc}")
        return None


def _load_canonical_report(token_path: Path) -> Mapping[str, object] | None:
    """Parse and validate the canonical token-report JSON file. Returns None on a
    parse error (already logged by _json_file) or after a warning for a non-object
    or empty report.
    """
    report_obj = _json_file(token_path)
    if report_obj is _JSON_ERROR:
        return None
    report = _as_mapping(report_obj)
    if not isinstance(report_obj, dict):
        _warn(f"{token_path} is not a JSON object; skipping")
        return None
    if not report:
        _warn(f"{token_path} is empty; skipping")
        return None
    return report


def _enrich_model_buckets(report: Mapping[str, object], *, run_dir: Path) -> Mapping[str, object]:
    enriched: Mapping[str, object] = report
    if not _as_mapping(enriched.get("BUCKETS_codex_by_model")):
        enriched = tokens.enrich_codex_by_model(dict(enriched), run_dir=run_dir)
        if enriched.get("BUCKETS_codex_by_model"):
            _warn(f"merging per-model Codex buckets from committed ledger for {run_dir}")
    if not _as_mapping(enriched.get("BUCKETS_claude_sub_by_model")):
        enriched = tokens.enrich_claude_sub_by_model(dict(enriched), run_dir=run_dir)
        if enriched.get("BUCKETS_claude_sub_by_model"):
            _warn(f"merging per-model Claude subprocess buckets from committed ledger for {run_dir}")
    return enriched


def _resolve_report(run_dir: Path, *, skill: Skill) -> Mapping[str, object] | None:
    """Load and validate a run's token report, falling back to the durable
    ledger when the canonical token-report{,-final}.json is absent or unusable
    (issue #5133). Returns None (after a warning) when no priceable report exists.
    """
    token_path = run_dir / _token_basename(skill)
    if token_path.is_symlink():
        _warn(f"{token_path} is a symlink; skipping")
        return None
    canonical: Mapping[str, object] | None = None
    if token_path.is_file():
        canonical = _load_canonical_report(token_path)
        if canonical is not None and _has_numeric_tokens(canonical):
            return _enrich_model_buckets(canonical, run_dir=run_dir)
    ledger_report = _ledger_fallback_report(run_dir)
    if ledger_report is not None and _has_numeric_tokens(ledger_report):
        _warn(f"recovering token report from committed ledger for {run_dir}")
        return ledger_report
    if token_path.is_file():
        if canonical is not None:
            _warn(f"{token_path} lacks vendor totals/BUCKETS with numeric token counts; skipping")
    else:
        _warn(f"{run_dir} has no {_token_basename(skill)}; skipping")
    return None


def _record(run_dir: Path, *, skill: Skill, repo_slug: str | None) -> RunRecord | None:
    manifest = run_log_corpus.load_run_manifest(run_dir)
    if manifest is None:
        return None
    number = safe_int(value=manifest.get("issue_number"))
    report = _resolve_report(run_dir, skill=skill)
    if report is None:
        return None
    url = f"https://github.com/{repo_slug}/issues/{number}" if repo_slug else ""
    roster = _as_mapping(manifest.get("model_roster"))
    return RunRecord(
        number=number,
        title=str(manifest.get("title") or f"Issue #{number}"),
        url=url,
        started_at=str(manifest.get("started_at") or ""),
        closed_at=str(manifest.get("updated_at") or manifest.get("started_at") or ""),
        workflow=_workflow(_run_dir=run_dir, _skill=skill),
        claude=vendor_totals_from_report(report=report, vendor="claude"),
        codex=vendor_totals_from_report(report=report, vendor="codex"),
        cursor=vendor_totals_from_report(report=report, vendor="cursor"),
        claude_sub=vendor_totals_from_report(report=report, vendor="claude_sub"),
        phase_rows=_phase_rows(report),
        raw_report=report,
        main_model=str(roster.get("main") or ""),
    )

def _run_dirs(log_base: Path) -> list[Path]:
    return run_log_corpus.run_dirs(log_base, warn=_warn)

def _limit_value(limit: int | None) -> int | None:
    if limit is not None:
        return limit if limit > 0 else None
    raw = os.environ.get(config.ENV_LARCH_REPORT_TOKENS_LIMIT, "").strip()
    if not raw:
        return None
    if raw.isdigit():
        value = int(raw)
        return value if value > 0 else None
    raise ShipError(f"ERROR: {config.ENV_LARCH_REPORT_TOKENS_LIMIT} must be a non-negative integer")

def scan(
    runner: Runner,
    *,
    skill: Skill,
    repo_override: str | None = None,
    limit: int | None = None,
    resolve_repo: bool = True,
) -> ScanResult:
    return _scan_request(
        runner,
        request=ScanRequest(
            skill=skill,
            repo_override=repo_override,
            limit=limit,
            resolve_repo=resolve_repo,
        ),
    )


def scan_prepared_corpus(
    runner: Runner,
    *,
    skill: Skill,
    corpus_root: Path,
) -> ScanResult:
    """Scan one skill from an already synchronized invocation corpus."""
    return _scan_request(
        runner,
        request=ScanRequest(
            skill=skill,
            repo_override=None,
            limit=None,
            resolve_repo=False,
            corpus_root=corpus_root,
        ),
    )


def _scan_request(runner: Runner, *, request: ScanRequest) -> ScanResult:
    root = _repo_root(runner)
    if request.corpus_root is None:
        try:
            log_root: Path = run_log_corpus.synchronized_repository_log_root(repo_root=root)
        except run_log_corpus.RunLogCorpusError as exc:
            raise ShipError(f"ERROR: {exc}") from exc
    else:
        log_root = request.corpus_root
    slug: str | None = (
        _repo_slug(
            runner=runner,
            override=request.repo_override
            or os.environ.get(config.ENV_LARCH_REPORT_TOKENS_REPO),
        )
        if request.resolve_repo
        else None
    )
    log_base = log_root / request.skill
    print(f"Scanning {log_base} for larch run logs (--skill={request.skill})...", file=sys.stderr)
    max_dirs: int | None = _limit_value(request.limit)
    records: list[RunRecord] = []
    for seen, run_dir in enumerate(_run_dirs(log_base), start=1):
        record: RunRecord | None = _record(run_dir, skill=request.skill, repo_slug=slug)
        if record is not None:
            records.append(record)
        if max_dirs is not None and seen >= max_dirs:
            break
    return ScanResult(repo_root=root, repo_slug=slug, records=tuple(records))
