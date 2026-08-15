# ruff: noqa: C901,PLR0912,PLR0913,PLR2004,PERF401
# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportCallIssue=false
"""Finalize and record Rust-generated rejected-analysis work artifacts.

Rust owns preparation, corpus scanning, and verifier-result ingestion. This
module retains the downstream ``finalize`` and ``record`` readers, together
with the finding-id lookup helpers consumed by fluff-analysis.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from larch import io as larch_io
from larch.core import logging_util
from larch.report import analysis_state
from larch.review.review_types import parse_canonical_heading

LEDGER_PATH = Path("rejected-analysis/ledger.tsv")
VERDICT_SIDECAR = Path("rejected-analysis/verdicts.tsv")
INGEST_STATUS_FILE = "ingest-status.jsonl"
LEDGER_SCHEMA_VERSION = "1"
INGEST_STATUS_SCHEMA_VERSION = 1
ISSUE_CLUSTER_SCHEMA_VERSION = 1

LEDGER_COLUMNS = [
    "schema_version",
    "finding_hash",
    "concern_hash",
    "source_skill",
    "run_id",
    "round_num",
    "finding_id",
    "reviewer_slots",
    "dissenting_slots",
    "file_path",
    "line_hint",
    "yes_votes",
    "no_votes",
    "high_severity",
    "vote_split",
    "verdict",
    "disposition",
    "issue_number",
    "issue_url",
    "triaged_at",
    "alias_of",
]

SIDECAR_COLUMNS = [
    "schema_version",
    "finding_hash",
    "source_skill",
    "run_id",
    "round_num",
    "finding_id",
    "dissenting_slots",
    "verdict",
    "current_location",
    "evidence",
    "triaged_at",
]

SECURITY_RE = re.compile(
    r"\b(security|vulnerab|injection|auth(?:entication|orization)?\s*bypass|credential|secret|token|password|rce|remote code execution|ssrf|xss|csrf|path traversal|privilege escalation|crypto)\b",
    re.IGNORECASE,
)
PATH_TOKEN_RE = re.compile(
    r"(?P<path>(?:\./)?(?:[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+|[A-Za-z0-9_.-]+/?)|(?:Makefile|Dockerfile|GNUmakefile))(?:[:#](?P<line>\d+)(?:-\d+)?)?"
)
FILED_DISPOSITIONS = frozenset({"filed-as", "deduped-as"})


def _first_canonical_heading(text: str) -> tuple[str, str] | None:
    """Return (item_id, title) from the first canonical heading in text, or None."""
    for line in text.splitlines():
        heading = parse_canonical_heading(line)
        if heading is not None:
            return (heading.item_id, heading.title)
    return None


def _finding_tokens(value: str, prose_body: str = "") -> set[str]:
    """Return the shared finding-id aliases used by fluff-analysis joins."""
    heading = _first_canonical_heading(prose_body or "")
    tokens: set[str] = set()
    for raw in (value, heading[0] if heading is not None else ""):
        text = (raw or "").strip().upper()
        if not text:
            continue
        tokens.add(text)
        match = re.match(r"REJ_CR\d+_(\d+)$", text)
        if match:
            tokens.add(f"FINDING_{match.group(1)}")
        match = re.match(r"FINDING_(\d+)$", text)
        if match:
            tokens.add(f"REJ_CR1_{match.group(1)}")
    return tokens


VerdictStatus = Literal["confirmed", "stale", "already-fixed"]
IngestStatus = Literal["ingested", "launch-failed", "dirty-tree", "parse-failed", "location-mismatch"]


@dataclass(frozen=True)
class VoteSplit:
    yes_votes: int
    no_votes: int
    yes_slots: tuple[str, ...] = ()
    no_slots: tuple[str, ...] = ()
    high_severity: bool = False

    def format(self) -> str:
        yes = ",".join(self.yes_slots) or "none"
        no = ",".join(self.no_slots) or "none"
        return f"YES={self.yes_votes}({yes}); NO={self.no_votes}({no})"


@dataclass(frozen=True)
class RejectedFinding:
    finding_hash: str
    concern_hash: str
    source_skill: str
    run_id: str
    round_num: str
    canonical_finding_id: str
    synthetic_id: str
    reviewer_slots: tuple[str, ...]
    dissenting_slots: tuple[str, ...]
    file_path: str
    line_hint: str
    concern: str
    prose_body: str
    classification_row: dict[str, str]
    vote_split: VoteSplit
    started_at: str
    demoted_later_touched: bool = False


@dataclass(frozen=True)
class LedgerEntry:
    finding_hash: str
    concern_hash: str
    source_skill: str
    run_id: str
    round_num: str
    finding_id: str
    reviewer_slots: str
    dissenting_slots: str
    file_path: str
    line_hint: str
    yes_votes: str
    no_votes: str
    high_severity: str
    vote_split: str
    verdict: str
    disposition: str
    issue_number: str = ""
    issue_url: str = ""
    triaged_at: str = ""
    alias_of: str = ""
    schema_version: str = LEDGER_SCHEMA_VERSION

    def to_row(self) -> dict[str, str]:
        raw = asdict(self)
        return {name: _sanitize_verdict_field(str(raw.get(name, ""))) for name in LEDGER_COLUMNS}


@dataclass(frozen=True)
class PreparedCandidate:
    candidate_id: str
    finding_hash: str
    concern_hash: str
    finding: RejectedFinding
    prompt_path: str


@dataclass(frozen=True)
class VerificationVerdict:
    status: VerdictStatus
    current_location: str
    evidence: str
    dirty_tree: bool = False


@dataclass(frozen=True)
class IngestStatusRow:
    candidate_id: str
    finding_hash: str
    status: IngestStatus
    disposition: str = ""
    launcher_exit: int = 0
    output_path: str = ""
    schema_version: int = INGEST_STATUS_SCHEMA_VERSION


@dataclass(frozen=True)
class IssueCluster:
    batch_index: int
    title: str
    finding_hashes: tuple[str, ...]


@dataclass(frozen=True)
class FinalizeResult:
    confirmed_count: int
    issue_batch_file: Path
    issue_cluster_map_file: Path
    issue_sentinel: Path
    ledger_pending_file: Path
    ingest_status_file: Path
    issue_output_stub: Path
    launch_failures: int
    clusters: tuple[IssueCluster, ...]


@dataclass(frozen=True)
class RecordResult:
    ledger_appended: int
    issues_created: int
    issues_deduplicated: int
    dismissed_count: int
    unmapped_confirmed: bool
    rc: int


class RejectedAnalysisError(RuntimeError):
    """Raised for fail-closed prepare/finalize/record errors."""


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _strip_md_value(value: str) -> str:
    text = value.strip()
    text = re.sub(r"^[-*+]\s+", "", text)
    text = re.sub(r"^\*\*([^*]+)\*\*\s*:\s*", "", text)
    return text.strip("` ")


def _disposition_priority(disposition: str) -> int:
    disp = disposition or ""
    if disp in FILED_DISPOSITIONS:
        return 4
    if disp.startswith("dismissed:"):
        return 1
    if disp:
        return 2
    return 0


def _merge_ledger_rows(rows: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    by_hash: dict[str, dict[str, str]] = {}
    for row in rows:
        finding_hash = str(row.get("finding_hash") or "")
        if not finding_hash:
            continue
        existing = by_hash.get(finding_hash)
        if existing is None or _disposition_priority(str(row.get("disposition") or "")) > _disposition_priority(str(existing.get("disposition") or "")):
            by_hash[finding_hash] = row
    return list(by_hash.values())


def _normalize_path_token(value: str) -> tuple[str, str]:
    text = _strip_md_value(value)
    match = PATH_TOKEN_RE.search(text)
    if not match:
        return "", ""
    path = match.group("path").replace("\\", "/")
    path = path.removeprefix("./")
    while "//" in path:
        path = path.replace("//", "/")
    if path != "/":
        path = path.rstrip("/")
    if path.startswith("/") or ".." in Path(path).parts:
        return "", ""
    return path, match.group("line") or ""


def is_security_sensitive_candidate(finding: RejectedFinding) -> bool:
    try:
        row = finding.classification_row
        focus = _collapse_ws(str(row.get("focus_area") or row.get("focus") or "")).lower()
        severity_text = " ".join(str(row.get(key) or "") for key in ("body_severity", "severity", "v1_severity", "v2_severity", "v3_severity"))
        prose_severity = " ".join(re.findall(r"(?i)\*\*Severity\*\*\s*:\s*([^\n]+)", finding.prose_body))
        haystack = f"{focus}\n{severity_text}\n{prose_severity}\n{finding.concern}\n{finding.prose_body}"
        return focus.replace(" ", "-") == "security" or SECURITY_RE.search(haystack) is not None
    except Exception:
        return True


def _ledger_entry(finding: RejectedFinding, *, verdict: str, disposition: str, issue_number: str = "", issue_url: str = "", alias_of: str = "") -> LedgerEntry:
    return LedgerEntry(
        finding_hash=finding.finding_hash,
        concern_hash=finding.concern_hash,
        source_skill=finding.source_skill,
        run_id=finding.run_id,
        round_num=finding.round_num,
        finding_id=finding.canonical_finding_id,
        reviewer_slots=",".join(finding.reviewer_slots),
        dissenting_slots=",".join(finding.dissenting_slots),
        file_path=finding.file_path,
        line_hint=finding.line_hint,
        yes_votes=str(finding.vote_split.yes_votes),
        no_votes=str(finding.vote_split.no_votes),
        high_severity="true" if finding.vote_split.high_severity else "false",
        vote_split=finding.vote_split.format(),
        verdict=verdict,
        disposition=disposition,
        issue_number=issue_number,
        issue_url=issue_url,
        triaged_at=_now_iso(),
        alias_of=alias_of,
    )


def _read_ledger_entries(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter="\t")]


def _write_pending_tsv(path: Path, entries: Iterable[LedgerEntry]) -> None:  # lint-keyword-only: ok stable helper API
    existing = _read_ledger_entries(path)
    merged = _merge_ledger_rows(existing + [entry.to_row() for entry in entries])
    lines: list[str] = ["\t".join(LEDGER_COLUMNS)]
    for row in merged:
        normalized = {name: _sanitize_verdict_field(str(row.get(name, ""))) for name in LEDGER_COLUMNS}
        lines.append("\t".join(normalized.get(name, "") for name in LEDGER_COLUMNS))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_ledger_atomic(path: Path, rows: list[dict[str, str]]) -> None:  # lint-keyword-only: ok stable helper API
    normalized: list[dict[str, str]] = []
    for row in _merge_ledger_rows(rows):
        finding_hash = str(row.get("finding_hash") or "")
        if not finding_hash:
            continue
        normalized.append({name: _sanitize_verdict_field(str(row.get(name, ""))) for name in LEDGER_COLUMNS})
    lines: list[str] = ["\t".join(LEDGER_COLUMNS)]
    for row in normalized:
        lines.append("\t".join(row.get(name, "") for name in LEDGER_COLUMNS))
    larch_io.atomic_write(path, "\n".join(lines) + "\n", create_parent=True)
    readback = _read_ledger_entries(path)
    if len(readback) != len(normalized):
        raise RejectedAnalysisError("ledger readback mismatch after atomic write")


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in _read_text(path).splitlines():
        if not line.strip():
            continue
        obj = _json_loads(line)
        if isinstance(obj, dict):
            out.append(dict(obj))
    return out


def _lookup_jsonl_record(
    *,
    by_token: Mapping[tuple[str, str], Mapping[str, Any]],
    round_num: str,
    row_id: str,
    allow_unscoped: bool,
) -> Mapping[str, Any] | None | Literal["ambiguous"]:
    matches: list[Mapping[str, Any]] = []
    for token in _finding_tokens(row_id):
        keyed = by_token.get((round_num, token))
        if keyed is not None:
            matches.append(keyed)
        elif allow_unscoped:
            unscoped = by_token.get(("", token))
            if unscoped is not None:
                matches.append(unscoped)
    unique: dict[int, Mapping[str, Any]] = {id(item): item for item in matches}
    if len(unique) > 1:
        return "ambiguous"
    return next(iter(unique.values()), None) if unique else None


def _records_by_round_and_token(records: Iterable[Mapping[str, Any]], *, default_round: str = "") -> dict[tuple[str, str], Mapping[str, Any]]:
    out: dict[tuple[str, str], Mapping[str, Any]] = {}
    for record in records:
        prose = str(record.get("prose_body") or record.get("body") or record.get("text") or "")
        round_num = str(record.get("round_num") or default_round or "")
        for token in _finding_tokens(str(record.get("id") or ""), prose):
            out[(round_num, token)] = record
    return out


def _write_json(path: Path, data: Any) -> None:  # lint-keyword-only: ok stable helper API
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _candidate_from_json(data: Mapping[str, Any]) -> PreparedCandidate:
    finding_data = dict(data.get("finding") if isinstance(data.get("finding"), Mapping) else {})
    split_data = dict(finding_data.get("vote_split") if isinstance(finding_data.get("vote_split"), Mapping) else {})
    split = VoteSplit(
        yes_votes=int(split_data.get("yes_votes") or 0),
        no_votes=int(split_data.get("no_votes") or 0),
        yes_slots=tuple(str(item) for item in split_data.get("yes_slots") or ()),
        no_slots=tuple(str(item) for item in split_data.get("no_slots") or ()),
        high_severity=bool(split_data.get("high_severity")),
    )
    finding = RejectedFinding(
        finding_hash=str(finding_data.get("finding_hash") or data.get("finding_hash") or ""),
        concern_hash=str(finding_data.get("concern_hash") or data.get("concern_hash") or ""),
        source_skill=str(finding_data.get("source_skill") or ""),
        run_id=str(finding_data.get("run_id") or ""),
        round_num=str(finding_data.get("round_num") or ""),
        canonical_finding_id=str(finding_data.get("canonical_finding_id") or ""),
        synthetic_id=str(finding_data.get("synthetic_id") or ""),
        reviewer_slots=tuple(str(item) for item in finding_data.get("reviewer_slots") or ()),
        dissenting_slots=tuple(str(item) for item in finding_data.get("dissenting_slots") or ()),
        file_path=str(finding_data.get("file_path") or ""),
        line_hint=str(finding_data.get("line_hint") or ""),
        concern=str(finding_data.get("concern") or ""),
        prose_body=str(finding_data.get("prose_body") or ""),
        classification_row=dict(finding_data.get("classification_row") if isinstance(finding_data.get("classification_row"), Mapping) else {}),
        vote_split=split,
        started_at=str(finding_data.get("started_at") or ""),
        demoted_later_touched=bool(finding_data.get("demoted_later_touched")),
    )
    return PreparedCandidate(
        candidate_id=str(data.get("candidate_id") or ""),
        finding_hash=str(data.get("finding_hash") or finding.finding_hash),
        concern_hash=str(data.get("concern_hash") or finding.concern_hash),
        finding=finding,
        prompt_path=str(data.get("prompt_path") or ""),
    )


def _load_candidates(work_dir: Path) -> list[PreparedCandidate]:
    data = _json_loads(_read_text(work_dir / "candidates.json"))
    if not isinstance(data, list):
        return []
    return [_candidate_from_json(item) for item in data if isinstance(item, Mapping)]


def _load_ingest_status_map(work_dir: Path) -> dict[str, IngestStatusRow]:
    out: dict[str, IngestStatusRow] = {}
    for obj in _iter_jsonl(work_dir / INGEST_STATUS_FILE):
        status = str(obj.get("status") or "")
        if status not in {"ingested", "launch-failed", "dirty-tree", "parse-failed", "location-mismatch"}:
            continue
        row = IngestStatusRow(
            candidate_id=str(obj.get("candidate_id") or ""),
            finding_hash=str(obj.get("finding_hash") or ""),
            status=status,  # type: ignore[arg-type]
            disposition=str(obj.get("disposition") or ""),
            launcher_exit=int(obj.get("launcher_exit") or 0),
            output_path=str(obj.get("output_path") or ""),
            schema_version=int(obj.get("schema_version") or INGEST_STATUS_SCHEMA_VERSION),
        )
        if row.candidate_id:
            out[row.candidate_id] = row
    return out


def _load_verdicts(work_dir: Path) -> dict[str, VerificationVerdict]:
    out: dict[str, VerificationVerdict] = {}
    for obj in _iter_jsonl(work_dir / "verdicts.jsonl"):
        status = str(obj.get("status") or "")
        if status not in {"confirmed", "stale", "already-fixed"}:
            continue
        cid = str(obj.get("candidate_id") or "")
        if cid:
            out[cid] = VerificationVerdict(
                status=status,  # type: ignore[arg-type]
                current_location=str(obj.get("current_location") or ""),
                evidence=str(obj.get("evidence") or ""),
                dirty_tree=bool(obj.get("dirty_tree")),
            )
    return out


def _sanitize_verdict_field(value: str) -> str:
    text = _collapse_ws((value or "").replace("\t", " ").replace("\n", " ").replace("\r", " "))
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def bind_verifier_location(candidate: PreparedCandidate, verdict: VerificationVerdict) -> bool:  # lint-keyword-only: ok stable helper API
    path, line = _normalize_path_token(verdict.current_location)
    if path != candidate.finding.file_path:
        return False
    if candidate.finding.line_hint:
        if not line:
            return False
        try:
            expected = int(candidate.finding.line_hint)
            actual = int(line)
        except ValueError:
            return False
        return expected <= actual <= expected + 2
    return True


def _cluster_key(finding: RejectedFinding) -> str:
    parts = finding.file_path.split("/")
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return parts[0] if parts else "general"


def _cluster_title(key: str, findings: Sequence[RejectedFinding]) -> str:  # lint-keyword-only: ok stable helper API
    area = key or "rejected finding"
    concern = findings[0].concern if findings else "rejected finding"
    return f"Recover rejected finding in {area}: {concern[:80]}"


def _render_issue_batch(clusters: Sequence[IssueCluster], by_hash: Mapping[str, tuple[PreparedCandidate, VerificationVerdict]]) -> str:  # lint-keyword-only: ok stable helper API
    if not clusters:
        return ""
    chunks: list[str] = []
    for cluster in clusters:
        chunks.append(f"### {cluster.title}\n")
        chunks.append("## Summary\n\nA rejected code-review finding was verified against current code and should be fixed.\n")
        chunks.append("## Findings\n")
        for finding_hash in cluster.finding_hashes:
            candidate, verdict = by_hash[finding_hash]
            finding = candidate.finding
            chunks.append(
                "\n"
                f"- Finding hash: `{finding.finding_hash}`\n"
                f"  - File: `{finding.file_path}`\n"
                f"  - Line hint: `{finding.line_hint or 'none'}`\n"
                f"  - Concern: {_sanitize_verdict_field(finding.concern)}\n"
                f"  - Provenance: {finding.source_skill}/{finding.run_id} round {finding.round_num}, {finding.canonical_finding_id}\n"
                f"  - Vote split: {_sanitize_verdict_field(finding.vote_split.format())}\n"
                f"  - Dissenting voter(s): `{', '.join(finding.dissenting_slots) or 'none'}`\n"
                f"  - Verification verdict: `{verdict.status}` at `{_sanitize_verdict_field(verdict.current_location)}`\n"
                f"  - Verification evidence: {_sanitize_verdict_field(verdict.evidence)}\n"
            )
        chunks.append("\n## Suggested next step\n\nDesign and implement the smallest fix for the verified finding.\n\n")
    return "".join(chunks)


def finalize(*, work_dir: Path | str) -> FinalizeResult:
    wd = Path(work_dir)
    candidates = _load_candidates(wd)
    status_map = _load_ingest_status_map(wd)
    verdicts = _load_verdicts(wd)
    ledger_entries: list[LedgerEntry] = []
    confirmed: dict[str, tuple[PreparedCandidate, VerificationVerdict]] = {}
    launch_failures = 0
    for candidate in candidates:
        status = status_map.get(candidate.candidate_id)
        verdict = verdicts.get(candidate.candidate_id)
        if status and status.status == "launch-failed":
            launch_failures += 1
            continue
        if status and status.status == "dirty-tree":
            ledger_entries.append(_ledger_entry(candidate.finding, verdict="dismissed", disposition="dismissed:dirty-tree"))
            continue
        if status and status.status in {"parse-failed", "location-mismatch"}:
            ledger_entries.append(_ledger_entry(candidate.finding, verdict="dismissed", disposition="dismissed:verification-failed"))
            continue
        if status and status.status == "ingested" and verdict and bind_verifier_location(candidate, verdict):
            if verdict.status == "confirmed":
                evidence_finding = _finding_with_extra_evidence(candidate.finding, verdict.evidence)
                if is_security_sensitive_candidate(evidence_finding):
                    ledger_entries.append(_ledger_entry(candidate.finding, verdict="dismissed", disposition="dismissed:security-sensitive"))
                else:
                    confirmed[candidate.finding_hash] = (candidate, verdict)
            elif verdict.status == "stale":
                ledger_entries.append(_ledger_entry(candidate.finding, verdict="stale", disposition="dismissed:stale"))
            else:
                ledger_entries.append(_ledger_entry(candidate.finding, verdict="already-fixed", disposition="dismissed:already-fixed"))
            continue
        if status is None:
            launch_failures += 1
            ledger_entries.append(_ledger_entry(candidate.finding, verdict="dismissed", disposition="dismissed:verification-failed"))
            continue
        if status.launcher_exit == 0:
            ledger_entries.append(_ledger_entry(candidate.finding, verdict="dismissed", disposition="dismissed:verification-failed"))
    ledger_pending = wd / "ledger-pending.tsv"
    _write_pending_tsv(ledger_pending, ledger_entries)
    clusters = _build_clusters([pair[0] for pair in confirmed.values()])
    issue_batch = wd / "issue-batch.md"
    issue_batch.write_text(_render_issue_batch(clusters, confirmed), encoding="utf-8")
    cluster_map = wd / "issue-cluster-map.json"
    _write_json(
        cluster_map,
        {
            "schema_version": ISSUE_CLUSTER_SCHEMA_VERSION,
            "clusters": [{"batch_index": c.batch_index, "finding_hashes": list(c.finding_hashes)} for c in clusters],
        },
    )
    issue_stub = wd / "issue.stdout.txt"
    if not issue_stub.exists():
        issue_stub.write_text("", encoding="utf-8")
    return FinalizeResult(
        confirmed_count=sum(len(c.finding_hashes) for c in clusters),
        issue_batch_file=issue_batch,
        issue_cluster_map_file=cluster_map,
        issue_sentinel=wd / "issue-completed.sentinel",
        ledger_pending_file=ledger_pending,
        ingest_status_file=wd / INGEST_STATUS_FILE,
        issue_output_stub=issue_stub,
        launch_failures=launch_failures,
        clusters=tuple(clusters),
    )


def _finding_with_extra_evidence(finding: RejectedFinding, evidence: str) -> RejectedFinding:  # lint-keyword-only: ok stable helper API
    return replace(finding, prose_body=f"{finding.prose_body}\n{evidence}")


def _build_clusters(candidates: Sequence[PreparedCandidate], *, size_cap: int = 5) -> tuple[IssueCluster, ...]:
    by_key: dict[str, list[PreparedCandidate]] = defaultdict(list)
    for candidate in candidates:
        by_key[_cluster_key(candidate.finding)].append(candidate)
    clusters: list[IssueCluster] = []
    idx = 1
    for key in sorted(by_key):
        items = by_key[key]
        for offset in range(0, len(items), size_cap):
            batch = items[offset : offset + size_cap]
            clusters.append(IssueCluster(idx, _cluster_title(key, [item.finding for item in batch]), tuple(item.finding_hash for item in batch)))
            idx += 1
    return tuple(clusters)


def _parse_issue_output(text: str) -> tuple[dict[int, tuple[str, str, bool]], int, int, int]:
    kv = larch_io.parse_kv(text)
    created = int(kv.get("ISSUES_CREATED") or 0)
    failed = int(kv.get("ISSUES_FAILED") or 0)
    deduped = int(kv.get("ISSUES_DEDUPLICATED") or 0)
    mapping: dict[int, tuple[str, str, bool]] = {}
    for key, value in kv.items():
        match = re.fullmatch(r"ISSUE_(\d+)_NUMBER", key)
        if match and value:
            idx = int(match.group(1))
            mapping[idx] = (value, kv.get(f"ISSUE_{idx}_URL", ""), False)
        match = re.fullmatch(r"ISSUE_(\d+)_DUPLICATE_OF_NUMBER", key)
        if match and value:
            idx = int(match.group(1))
            mapping[idx] = (value, kv.get(f"ISSUE_{idx}_DUPLICATE_OF_URL", ""), True)
    return mapping, created, failed, deduped


def _load_cluster_hashes(work_dir: Path) -> dict[int, list[str]]:
    data = _json_loads(_read_text(work_dir / "issue-cluster-map.json"))
    out: dict[int, list[str]] = {}
    if isinstance(data, Mapping):
        clusters = data.get("clusters")
        if isinstance(clusters, list):
            for item in clusters:
                if isinstance(item, Mapping):
                    out[int(item.get("batch_index") or 0)] = [str(h) for h in item.get("finding_hashes") or []]
    return out


def record(
    *,
    work_dir: Path | str,
    issue_output: Path | str | None = None,
    issue_verified: bool | None = None,
    issues_failed: int = 0,
    launch_failures: int = 0,
    repo_root: Path | str | None = None,
    state_root: Path | str | None = None,
) -> RecordResult:
    wd = Path(work_dir)
    root = Path(repo_root or Path.cwd()).resolve()
    mutable_root = Path(state_root).resolve() if state_root is not None else root
    ledger_path = mutable_root / LEDGER_PATH
    pending_rows = _merge_ledger_rows(_read_ledger_entries(wd / "ledger-pending.tsv"))
    status_map = _load_ingest_status_map(wd)
    candidate_list = _load_candidates(wd)
    candidates = {candidate.finding_hash: candidate for candidate in candidate_list}
    candidate_hashes = set(candidates)
    launch_failed_hashes = {row.finding_hash for row in status_map.values() if row.status == "launch-failed" and row.finding_hash in candidate_hashes}
    derived_launch_failures = len(launch_failed_hashes)
    launch_failures = max(launch_failures, derived_launch_failures)
    safe_rows = [row for row in pending_rows if row.get("finding_hash") not in launch_failed_hashes]
    issue_text = _read_text(Path(issue_output)) if issue_output is not None and Path(issue_output).is_file() else ""
    issue_map, created, parsed_failed, deduped = _parse_issue_output(issue_text) if issue_text.strip() else ({}, 0, 0, 0)
    if parsed_failed:
        issues_failed = parsed_failed
    clusters = _load_cluster_hashes(wd)
    unmapped = False
    filed_rows: list[dict[str, str]] = []
    if issue_verified is True:
        for batch_idx, hashes in clusters.items():
            resolved = issue_map.get(batch_idx)
            if not resolved:
                if hashes:
                    unmapped = True
                continue
            number, url, duplicate = resolved
            disposition = "deduped-as" if duplicate else "filed-as"
            for finding_hash in hashes:
                if finding_hash in launch_failed_hashes:
                    continue
                candidate = candidates.get(finding_hash)
                if candidate is None:
                    unmapped = True
                    continue
                filed_rows.append(_ledger_entry(candidate.finding, verdict="confirmed", disposition=disposition, issue_number=number, issue_url=url).to_row())
    elif issue_text.strip() and (created > 0 or deduped > 0):
        unmapped = True
    sidecar_path = mutable_root / VERDICT_SIDECAR
    try:
        with analysis_state.state_lock(ledger_path):
            all_rows = _merge_ledger_rows(_read_ledger_entries(ledger_path) + safe_rows + filed_rows)
            _write_ledger_atomic(ledger_path, all_rows)
        with analysis_state.state_lock(sidecar_path):
            _write_sidecar_atomic(sidecar_path, wd, candidates)
    except analysis_state.AnalysisStateError as exc:
        raise RejectedAnalysisError(str(exc)) from exc
    rc = 0
    if unmapped or issues_failed > 0 or issue_verified is False or launch_failures > 0:
        rc = 1
    dismissed = sum(1 for row in safe_rows if str(row.get("disposition") or "").startswith("dismissed:"))
    return RecordResult(len(safe_rows) + len(filed_rows), created, deduped, dismissed, unmapped, rc)


def _read_sidecar_entries(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter="\t")]


def _write_sidecar_atomic(path: Path, work_dir: Path, candidates: Mapping[str, PreparedCandidate]) -> None:  # lint-keyword-only: ok stable helper API
    verdicts = _load_verdicts(work_dir)
    status_map = _load_ingest_status_map(work_dir)
    new_rows: list[dict[str, str]] = []
    for cid, verdict in verdicts.items():
        if verdict.dirty_tree:
            continue
        status = status_map.get(cid)
        if status and status.status == "dirty-tree":
            continue
        candidate = next((item for item in candidates.values() if item.candidate_id == cid), None)
        if candidate is None:
            continue
        finding = candidate.finding
        new_rows.append(
            {
                "schema_version": LEDGER_SCHEMA_VERSION,
                "finding_hash": finding.finding_hash,
                "source_skill": finding.source_skill,
                "run_id": finding.run_id,
                "round_num": finding.round_num,
                "finding_id": finding.canonical_finding_id,
                "dissenting_slots": ",".join(finding.dissenting_slots),
                "verdict": verdict.status,
                "current_location": _sanitize_verdict_field(verdict.current_location),
                "evidence": _sanitize_verdict_field(verdict.evidence),
                "triaged_at": _now_iso(),
            }
        )
    if not new_rows and not path.is_file():
        return
    by_hash: dict[str, dict[str, str]] = {}
    for row in _read_sidecar_entries(path) + new_rows:
        finding_hash = str(row.get("finding_hash") or "")
        if finding_hash:
            by_hash[finding_hash] = row
    if not by_hash:
        return
    lines: list[str] = ["\t".join(SIDECAR_COLUMNS)]
    for row in by_hash.values():
        normalized = {name: _sanitize_verdict_field(str(row.get(name, ""))) for name in SIDECAR_COLUMNS}
        lines.append("\t".join(normalized.get(name, "") for name in SIDECAR_COLUMNS))
    larch_io.atomic_write(path, "\n".join(lines) + "\n", create_parent=True)


def finalize_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="rejected-analysis finalize")
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args(argv)
    result = finalize(work_dir=args.work_dir)
    logging_util.emit_kv(key="CONFIRMED_COUNT", value=str(result.confirmed_count))
    logging_util.emit_kv(key="ISSUE_BATCH_FILE", value=str(result.issue_batch_file))
    logging_util.emit_kv(key="ISSUE_CLUSTER_MAP_FILE", value=str(result.issue_cluster_map_file))
    logging_util.emit_kv(key="ISSUE_SENTINEL", value=str(result.issue_sentinel))
    logging_util.emit_kv(key="LEDGER_PENDING_FILE", value=str(result.ledger_pending_file))
    logging_util.emit_kv(key="INGEST_STATUS_FILE", value=str(result.ingest_status_file))
    logging_util.emit_kv(key="ISSUE_OUTPUT_STUB", value=str(result.issue_output_stub))
    logging_util.emit_kv(key="LAUNCH_FAILURES", value=str(result.launch_failures))
    return 0


def _repo_root_from_work_dir(work_dir: Path) -> Path | None:
    path = work_dir / "repo-root.txt"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return Path(text).resolve() if text else None


def _state_root_from_work_dir(work_dir: Path) -> Path | None:
    path = work_dir / "state-root.txt"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return Path(text).resolve() if text else None


def record_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="rejected-analysis record")
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--issue-output", default="")
    parser.add_argument("--issue-verified", choices=("true", "false"), default="")
    parser.add_argument("--issues-failed", type=int, default=0)
    parser.add_argument("--launch-failures", type=int, default=0)
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)
    work_dir = Path(args.work_dir)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else _repo_root_from_work_dir(work_dir)
    state_root = _state_root_from_work_dir(work_dir)
    try:
        result = record(
            work_dir=args.work_dir,
            issue_output=args.issue_output or None,
            issue_verified=None if not args.issue_verified else args.issue_verified == "true",
            issues_failed=args.issues_failed,
            launch_failures=args.launch_failures,
            repo_root=repo_root,
            state_root=state_root,
        )
    except RejectedAnalysisError as exc:
        logging_util.diagnostic(f"rejected-analysis record: {exc}")
        return 2
    logging_util.emit_kv(key="LEDGER_APPENDED", value=str(result.ledger_appended))
    logging_util.emit_kv(key="ISSUES_CREATED", value=str(result.issues_created))
    logging_util.emit_kv(key="ISSUES_DEDUPLICATED", value=str(result.issues_deduplicated))
    logging_util.emit_kv(key="DISMISSED_COUNT", value=str(result.dismissed_count))
    logging_util.emit_kv(key="UNMAPPED_CONFIRMED", value="true" if result.unmapped_confirmed else "false")
    logging_util.emit_kv(key="RECORD_EXIT_RC", value=str(result.rc))
    return result.rc
