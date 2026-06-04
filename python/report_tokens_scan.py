"""Scan committed larch run logs for report-token records."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from collections.abc import Mapping

import config
import redact
from errors import ShipError
from proc import Runner
from report_tokens_models import PhaseRow, RunRecord, Skill, VendorName, VendorTotals, VENDORS, safe_int


_JSON_ERROR = object()


@dataclass(frozen=True)
class ScanResult:
    repo_root: Path
    repo_slug: str | None
    records: tuple[RunRecord, ...]


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
        result = runner.run(["git", "rev-parse", "--show-toplevel"])
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


def _repo_slug(runner: Runner, override: str | None) -> str | None:
    if override:
        if _valid_repo_slug(override):
            return override
        raise ShipError(f"ERROR: {config.ENV_LARCH_REPORT_TOKENS_REPO} must be a safe OWNER/REPO slug")
    try:
        result = runner.run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    except OSError as exc:
        print(f"ERROR: could not resolve GitHub repo owner/name: {redact.redact(str(exc))}", file=sys.stderr)
        return None
    if result.returncode == 0 and _valid_repo_slug(result.stdout.strip()):
        return result.stdout.strip()
    detail = (result.stderr or result.stdout).strip()
    suffix = f": {redact.redact(detail)}" if detail else ""
    print(f"ERROR: could not resolve GitHub repo owner/name{suffix}", file=sys.stderr)
    return None


def _token_basename(skill: Skill) -> str:
    return "token-report-final.json" if skill == "design" else "token-report.json"


def _timing_basename(skill: Skill) -> str:
    return "timing-report-final.json" if skill == "design" else "timing-report.json"


def _workflow_from(path: Path) -> str:
    data = _json_file(path)
    if data is _JSON_ERROR:
        return "unknown"
    mapping = _as_mapping(data)
    if not mapping:
        _warn(f"{path.name} at {path} is not a JSON object with workflow classification; using unknown")
        return "unknown"
    for key in ("workflow_path", "design_classification"):
        value = mapping.get(key)
        if value in ("SIMPLE", "HARD"):
            return str(value)
    _warn(f"{path.name} at {path} lacks SIMPLE/HARD workflow classification; using unknown")
    return "unknown"


def _workflow(run_dir: Path, skill: Skill) -> str:
    saw_artifact = False
    for name in (_timing_basename(skill), "run-params.json"):
        path = run_dir / name
        if not path.is_file():
            continue
        saw_artifact = True
        value = _workflow_from(path)
        if value != "unknown":
            return value
    if not saw_artifact:
        _warn(f"{run_dir} has no workflow artifacts; using unknown")
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
    bucket_keys = {
        "claude": ("input", "cache_read", "cache_create", "cache_create_5m", "cache_create_1h", "output"),
        "codex": ("input", "cached_input", "output"),
        "cursor": ("input", "cache_read", "output"),
    }
    for vendor in VENDORS:
        bucket = _as_mapping(report.get(f"BUCKETS_{vendor}"))
        if any(safe_int(bucket.get(key)) > 0 for key in bucket_keys[vendor]):
            return True
        totals = _totals(report, vendor)
        if any(
            value > 0
            for value in (
                totals.input,
                totals.cache_read,
                totals.cache_create,
                totals.cache_create_5m,
                totals.cache_create_1h,
                totals.cached_input,
                totals.output,
                totals.total,
            )
        ):
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
    if manifest_obj is _JSON_ERROR:
        return None
    manifest = _as_mapping(manifest_obj)
    if not isinstance(manifest_obj, dict):
        _warn(f"manifest for {run_dir} is not a JSON object; skipping")
        return None
    if not manifest:
        _warn(f"manifest for {run_dir} is empty and lacks numeric issue_number; skipping")
        return None
    number = safe_int(manifest.get("issue_number"))
    if number <= 0:
        _warn(f"manifest for {run_dir} lacks numeric issue_number; skipping")
        return None
    token_path = run_dir / _token_basename(skill)
    if token_path.is_symlink():
        _warn(f"{token_path} is a symlink; skipping")
        return None
    if not token_path.is_file():
        _warn(f"{run_dir} has no {_token_basename(skill)}; skipping")
        return None
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
    if not _has_numeric_tokens(report):
        _warn(f"{token_path} lacks vendor totals/BUCKETS with numeric token counts; skipping")
        return None
    url = f"https://github.com/{repo_slug}/issues/{number}" if repo_slug else ""
    return RunRecord(
        number=number,
        title=str(manifest.get("title") or f"Issue #{number}"),
        url=url,
        started_at=str(manifest.get("started_at") or ""),
        closed_at=str(manifest.get("updated_at") or manifest.get("started_at") or ""),
        workflow=_workflow(run_dir, skill),
        claude=_totals(report, "claude"),
        codex=_totals(report, "codex"),
        cursor=_totals(report, "cursor"),
        phase_rows=_phase_rows(report),
        raw_report=report,
    )


def _run_dirs(log_base: Path) -> list[Path]:
    dirs: list[Path] = []
    try:
        resolved_base = log_base.resolve(strict=True)
    except OSError as exc:
        _warn(f"log root {log_base} is missing or unreadable: {exc}; no run logs scanned")
        return []
    for path in sorted(log_base.glob("*")):
        if path.is_symlink():
            _warn(f"run directory {path} is a symlink; skipping")
            continue
        if not path.is_dir():
            continue
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            _warn(f"could not resolve run directory {path}: {exc}; skipping")
            continue
        if not (resolved == resolved_base or resolved_base in resolved.parents):
            _warn(f"run directory {path} resolves outside {log_base}; skipping")
            continue
        dirs.append(path)
    return dirs


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
    root = _repo_root(runner)
    slug = _repo_slug(runner, repo_override or os.environ.get("LARCH_REPORT_TOKENS_REPO")) if resolve_repo else None
    log_base = root / "larch-logs" / skill
    print(f"Scanning {log_base} for larch run logs (--skill={skill})...", file=sys.stderr)
    max_dirs = _limit_value(limit)
    records: list[RunRecord] = []
    for seen, run_dir in enumerate(_run_dirs(log_base), start=1):
        record = _record(run_dir, skill=skill, repo_slug=slug)
        if record is not None:
            records.append(record)
        if max_dirs is not None and seen >= max_dirs:
            break
    return ScanResult(repo_root=root, repo_slug=slug, records=tuple(records))
