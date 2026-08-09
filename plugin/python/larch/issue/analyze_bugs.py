# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportPossiblyUnboundVariable=false, reportMissingParameterType=false, reportArgumentType=false, reportUnknownLambdaType=false
# ruff: noqa: C901, FB504, PLR0911, PLR0912, PLR0913, PLR0915
# pylint: skip-file
"""Residual sweep support for ``/analyze-bugs`` and ``/validate-merged``.

The Rust CLI owns all analyze-bugs commands. This module remains only because
the separately owned validate-merged workflow reuses its sweep state helpers.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Final, cast

from larch.core import proc
from larch.core.proc import Runner
from larch.git import gh
from larch.issue.issue_blocks import strip_named_block

DEFAULT_DIFF_CAP: Final = 60_000
SCAN_OK: Final = "ok"
HISTORICAL_MARKER_BACKFILL_LIMIT: Final = 50
PYTHON_ZONE_PARTS: Final = 3
GENERAL_ZONE_PARTS: Final = 2
NUMSTAT_FIELDS: Final = 3
CHURN_COMMIT_THRESHOLD: Final = 3
CHRONIC_BUG_THRESHOLD: Final = 3
CHAIN_MEMBER_THRESHOLD: Final = 2
ANALYTICS_METADATA_VERSION: Final = 1
DAY_SECONDS: Final = 86_400
MARKER_PHRASE_RE: Final = re.compile(
    r"(?i)(?:incomplete|persists\s+after|residual|regression\s+from|after\s+the)"
)
ISSUE_REFERENCE_RE: Final = re.compile(r"(?<![A-Za-z0-9])#([1-9][0-9]*)")
BASELINE_PATH_RE: Final = re.compile(r"^python/[^/]+-baseline\.json$")
SWEEP_SCHEMA_VERSION: Final = 1
SWEEP_DEFAULT_MAX: Final = 20
SWEEP_INITIAL_WINDOW_SECONDS: Final = 48 * 60 * 60
SWEEP_DIFF_CAP: Final = DEFAULT_DIFF_CAP
SWEEP_SYMBOL_CAP: Final = 40
SWEEP_CONSUMER_CAP: Final = 40
CONSUMER_EXCLUDED_PATHS: Final = ("larch-logs",)
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


def workflow_runner() -> Runner:
    """Return the runner shared by independent issue-analysis workflows."""
    return _runner()


def _fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _positive_int(value: str, *, name: str) -> int:
    if not value.isdecimal() or int(value) <= 0:
        raise argparse.ArgumentTypeError(f"{name} must be a positive integer")
    return int(value)


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


def resolve_repo(runner: Runner, explicit: str = "") -> str:
    if explicit:
        return explicit
    resolved = gh.resolve_repo(runner)
    if not resolved:
        raise AnalyzeBugsError("could not resolve GitHub repo; pass --repo OWNER/REPO")
    return resolved


def _strip_plan(body: str) -> tuple[str, str]:
    stripped, malformed = strip_named_block(body=body, marker="plan")
    if malformed:
        return "", malformed
    return stripped, ""


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


def _excluded_consumer_path(path: str) -> bool:
    return any(path == excluded or path.startswith(f"{excluded}/") for excluded in CONSUMER_EXCLUDED_PATHS)


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


def _capped(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    return text[:cap] + f"\n\n[content truncated to {cap} characters]\n"


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


def validated_merge_artifact(*, run_dir: Path) -> tuple[SweepValidatedArtifact, dict[str, Any]] | None:
    """Validate the shared finder/refuter artifact for merge validation."""
    return _validated_sweep_artifact(run_dir=run_dir)


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
