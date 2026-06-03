"""Scan committed larch run logs for report-token records."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from collections.abc import Mapping

from proc import Runner
from report_tokens_models import PhaseRow, RunRecord, Skill, VendorName, VendorTotals, VENDORS, safe_int


@dataclass(frozen=True)
class ScanResult:
    repo_root: Path
    repo_slug: str | None
    records: tuple[RunRecord, ...]


def _warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def _json_file(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _warn(f"invalid {path.name} at {path}: {exc}; skipping")
        return None


def _as_mapping(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", value) if isinstance(value, dict) else {}


def _repo_root(runner: Runner) -> Path:
    try:
        result = runner.run(["git", "rev-parse", "--show-toplevel"])
    except OSError:
        _warn("git rev-parse failed; using current working directory as scan root")
        return Path.cwd().resolve()
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    _warn("git rev-parse failed; using current working directory as scan root")
    return Path.cwd().resolve()


def _repo_slug(runner: Runner, override: str | None) -> str | None:
    if override:
        return override if "/" in override else None
    try:
        result = runner.run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    except OSError as exc:
        print(f"ERROR: could not resolve GitHub repo owner/name: {exc}", file=sys.stderr)
        return None
    if result.returncode == 0 and "/" in result.stdout.strip():
        return result.stdout.strip()
    detail = (result.stderr or result.stdout).strip()
    suffix = f": {detail}" if detail else ""
    print(f"ERROR: could not resolve GitHub repo owner/name{suffix}", file=sys.stderr)
    return None


def _token_basename(skill: Skill) -> str:
    return "token-report-final.json" if skill == "design" else "token-report.json"


def _timing_basename(skill: Skill) -> str:
    return "timing-report-final.json" if skill == "design" else "timing-report.json"


def _workflow_from(path: Path) -> str:
    data = _json_file(path)
    mapping = _as_mapping(data)
    for key in ("workflow_path", "design_classification"):
        value = mapping.get(key)
        if value in ("SIMPLE", "HARD"):
            return str(value)
    return "unknown"


def _workflow(run_dir: Path, skill: Skill) -> str:
    for name in (_timing_basename(skill), "run-params.json"):
        path = run_dir / name
        if not path.is_file():
            continue
        value = _workflow_from(path)
        if value != "unknown":
            return value
    return "unknown"


def _totals(report: Mapping[str, object], vendor: VendorName) -> VendorTotals:
    vendor_obj = _as_mapping(report.get(vendor))
    totals = _as_mapping(vendor_obj.get("totals"))
    return VendorTotals(
        input=safe_int(totals.get("input")),
        cache_read=safe_int(totals.get("cache_read")),
        cache_create=safe_int(totals.get("cache_create")),
        cache_create_5m=safe_int(totals.get("cache_create_5m")),
        cache_create_1h=safe_int(totals.get("cache_create_1h")),
        cached_input=safe_int(totals.get("cached_input")),
        output=safe_int(totals.get("output")),
        total=safe_int(totals.get("total")),
    )


def _has_numeric_tokens(report: Mapping[str, object]) -> bool:
    for vendor in VENDORS:
        bucket = _as_mapping(report.get(f"BUCKETS_{vendor}"))
        if any(safe_int(value) > 0 for value in bucket.values()):
            return True
        if _totals(report, vendor).total > 0:
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
                input=safe_int(totals.get("input")),
                cache_read=safe_int(totals.get("cache_read")),
                cache_create=safe_int(totals.get("cache_create")),
                output=safe_int(totals.get("output")),
                total=safe_int(totals.get("total")),
            ))
    return tuple(rows)


def _record(run_dir: Path, *, skill: Skill, repo_slug: str | None) -> RunRecord | None:
    manifest_obj = _json_file(run_dir / "manifest.json")
    manifest = _as_mapping(manifest_obj)
    if not manifest:
        return None
    number = safe_int(manifest.get("issue_number"))
    if number <= 0:
        _warn(f"manifest for {run_dir} lacks numeric issue_number; skipping")
        return None
    token_path = run_dir / _token_basename(skill)
    if not token_path.is_file():
        return None
    report_obj = _json_file(token_path)
    report = _as_mapping(report_obj)
    if not report:
        return None
    if not _has_numeric_tokens(report):
        _warn(f"{token_path} lacks vendor totals/BUCKETS with numeric token counts; skipping")
        return None
    slug = repo_slug or "unknown/unknown"
    return RunRecord(
        number=number,
        title=str(manifest.get("title") or f"Issue #{number}"),
        url=f"https://github.com/{slug}/issues/{number}",
        started_at=str(manifest.get("started_at") or ""),
        closed_at=str(manifest.get("updated_at") or manifest.get("started_at") or ""),
        workflow=_workflow(run_dir, skill),
        claude=_totals(report, "claude"),
        codex=_totals(report, "codex"),
        cursor=_totals(report, "cursor"),
        phase_rows=_phase_rows(report),
        raw_report=report,
    )


def _limit_value(limit: int | None) -> int | None:
    if limit is not None:
        return limit if limit > 0 else None
    raw = os.environ.get("LARCH_REPORT_TOKENS_LIMIT", "").strip()
    if not raw:
        return None
    if raw.isdigit():
        value = int(raw)
        return value if value > 0 else None
    _warn("LARCH_REPORT_TOKENS_LIMIT must be a non-negative integer; ignoring")
    return None


def scan(
    runner: Runner,
    *,
    skill: Skill,
    repo_override: str | None = None,
    limit: int | None = None,
) -> ScanResult:
    root = _repo_root(runner)
    slug = _repo_slug(runner, repo_override or os.environ.get("LARCH_REPORT_TOKENS_REPO"))
    log_base = root / "larch-logs" / skill
    print(f"Scanning {log_base} for larch run logs (--skill={skill})...", file=sys.stderr)
    max_dirs = _limit_value(limit)
    records: list[RunRecord] = []
    for seen, run_dir in enumerate(sorted(path for path in log_base.glob("*") if path.is_dir()), start=1):
        record = _record(run_dir, skill=skill, repo_slug=slug)
        if record is not None:
            records.append(record)
        if max_dirs is not None and seen >= max_dirs:
            break
    return ScanResult(repo_root=root, repo_slug=slug, records=tuple(records))
