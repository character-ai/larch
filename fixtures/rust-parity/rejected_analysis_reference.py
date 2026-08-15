# ruff: noqa: PLR0913,PLR2004
"""Frozen Python behavior for the rejected-analysis command parity contract.

This is the pre-#8504 `rejected-analysis` command restricted to the hermetic
fixture paths exercised by `crates/larch-cli/tests/parity.rs`.
It deliberately remains a test oracle, not a runtime fallback or a second
production owner. The cases compare the command's exit code, stdout, stderr,
and captured work-directory and analyzer-state wire files. The prepare cases
pin repository-preflight ordering without reaching a live GitHub snapshot.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path


INGEST_STATUS_FILE = "ingest-status.jsonl"
LEDGER_COLUMNS = [
    "schema_version", "finding_hash", "concern_hash", "source_skill",
    "run_id", "round_num", "finding_id", "reviewer_slots",
    "dissenting_slots", "file_path", "line_hint", "yes_votes", "no_votes",
    "high_severity", "vote_split", "verdict", "disposition", "issue_number",
    "issue_url", "triaged_at", "alias_of",
]
SIDECAR_COLUMNS = [
    "schema_version", "finding_hash", "source_skill", "run_id", "round_num",
    "finding_id", "dissenting_slots", "verdict", "current_location", "evidence",
    "triaged_at",
]
STATUS_CLEAN_RE = re.compile(r"^STATUS=clean\b", re.MULTILINE)
FENCED_JSON_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)
PATH_RE = re.compile(r"(?P<path>[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)(?:[:#](?P<line>\d+))?")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def sanitize(value: str) -> str:
    text = re.sub(r"\s+", " ", value.replace("\t", " ").replace("\n", " ").replace("\r", " ")).strip()
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


def append_json_line(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_candidates(work_dir: Path) -> dict[str, dict[str, object]]:
    try:
        data = json.loads(read_text(work_dir / "candidates.json"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, list):
        return {}
    return {
        str(candidate.get("candidate_id") or ""): candidate
        for candidate in data
        if isinstance(candidate, dict) and str(candidate.get("candidate_id") or "")
    }


def extract_verdict(path: Path) -> tuple[str, str, str] | None:
    text = read_text(path)
    try:
        wrapper = json.loads(text)
    except json.JSONDecodeError:
        wrapper = None
    if isinstance(wrapper, dict) and isinstance(wrapper.get("result"), str):
        text = wrapper["result"]
    if text.strip() in {"CURSOR_EMPTY_RESPONSE", "CURSOR_DEGRADED_RESPONSE"}:
        return None
    stripped = text.strip()
    match = FENCED_JSON_RE.fullmatch(stripped)
    if match:
        stripped = match.group(1).strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    status = str(value.get("status") or "")
    location = sanitize(str(value.get("current_location") or ""))
    evidence = sanitize(str(value.get("evidence") or ""))
    if status not in {"confirmed", "stale", "already-fixed"} or not location or not evidence:
        return None
    return status, location, evidence


def location_matches(finding: dict[str, object], location: str) -> bool:
    match = PATH_RE.search(location)
    if match is None or match.group("path") != str(finding.get("file_path") or ""):
        return False
    expected = str(finding.get("line_hint") or "")
    if not expected:
        return True
    try:
        return int(expected) <= int(match.group("line") or "") <= int(expected) + 2
    except ValueError:
        return False


def status_row(
    candidate_id: str,
    finding_hash: str,
    status: str,
    disposition: str,
    launcher_exit: int,
    output: Path,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "disposition": disposition,
        "finding_hash": finding_hash,
        "launcher_exit": launcher_exit,
        "output_path": str(output),
        "schema_version": 1,
        "status": status,
    }


def ingest_verdict_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="rejected-analysis ingest-verdict")
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--launcher-exit", type=int, required=True)
    parser.add_argument("--dirty-sidecar", default="")
    args = parser.parse_args(argv)

    work_dir = Path(args.work_dir)
    candidates = load_candidates(work_dir)
    candidate = candidates.get(args.candidate_id)
    if candidate is None:
        print(f"rejected-analysis ingest-verdict: unknown candidate_id: {args.candidate_id}", file=sys.stderr)
        return 2
    finding = candidate.get("finding")
    if not isinstance(finding, dict):
        finding = {}
    finding_hash = str(candidate.get("finding_hash") or finding.get("finding_hash") or "")
    output = Path(args.output)
    status_path = work_dir / INGEST_STATUS_FILE

    if args.launcher_exit != 0:
        append_json_line(status_path, status_row(args.candidate_id, finding_hash, "launch-failed", "", args.launcher_exit, output))
        print("INGEST_STATUS=launch-failed")
        return 0

    dirty_path = Path(args.dirty_sidecar) if args.dirty_sidecar else Path(str(output) + ".dirty-tree")
    if not dirty_path.is_file() or not STATUS_CLEAN_RE.search(read_text(dirty_path)):
        disposition = "dismissed:dirty-tree"
        append_json_line(status_path, status_row(args.candidate_id, finding_hash, "dirty-tree", disposition, args.launcher_exit, output))
        print("INGEST_STATUS=dirty-tree")
        print(f"INGEST_DISPOSITION={disposition}")
        return 0

    verdict = extract_verdict(output)
    if verdict is None:
        disposition = "dismissed:verification-failed"
        append_json_line(status_path, status_row(args.candidate_id, finding_hash, "parse-failed", disposition, args.launcher_exit, output))
        print("INGEST_STATUS=parse-failed")
        print(f"INGEST_DISPOSITION={disposition}")
        return 0
    status, location, evidence = verdict
    if not location_matches(finding, location):
        disposition = "dismissed:verification-failed"
        append_json_line(status_path, status_row(args.candidate_id, finding_hash, "location-mismatch", disposition, args.launcher_exit, output))
        print("INGEST_STATUS=location-mismatch")
        print(f"INGEST_DISPOSITION={disposition}")
        return 0

    append_json_line(
        work_dir / "verdicts.jsonl",
        {
            "candidate_id": args.candidate_id,
            "current_location": location,
            "dirty_tree": False,
            "evidence": evidence,
            "finding_hash": finding_hash,
            "status": status,
        },
    )
    append_json_line(status_path, status_row(args.candidate_id, finding_hash, "ingested", status, args.launcher_exit, output))
    print("INGEST_STATUS=ingested")
    print(f"INGEST_DISPOSITION={status}")
    return 0


def prepare_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="rejected-analysis prepare")
    parser.add_argument("--days", "--n", dest="days", type=int, required=True)
    parser.add_argument(
        "--log-root",
        default="",
        help="offline fixture corpus override; default synchronizes the current repository cache",
    )
    parser.add_argument("--work-dir", default="")
    parser.add_argument("--verify-cap", type=int, default=100)
    _ = parser.parse_args(argv)
    # The historical command resolves repository and storage context before it
    # calls `prepare`, where numeric bounds are refused. The sandbox has no
    # repository, so this ordering remains observable without live services.
    print("rejected-analysis prepare: could not discover a Git repository root", file=sys.stderr)
    return 2


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _finding(candidate: dict[str, object]) -> dict[str, object]:
    value = candidate.get("finding")
    return value if isinstance(value, dict) else {}


def _field(value: object) -> str:
    return str(value or "")


def _vote_split(finding: dict[str, object]) -> str:
    value = finding.get("vote_split")
    split = value if isinstance(value, dict) else {}
    yes_slots = ",".join(str(item) for item in split.get("yes_slots") or []) or "none"
    no_slots = ",".join(str(item) for item in split.get("no_slots") or []) or "none"
    return f"YES={int(split.get('yes_votes') or 0)}({yes_slots}); NO={int(split.get('no_votes') or 0)}({no_slots})"


def _ledger_row(
    candidate: dict[str, object],
    *,
    verdict: str,
    disposition: str,
    issue_number: str = "",
    issue_url: str = "",
) -> dict[str, str]:
    finding = _finding(candidate)
    split_value = finding.get("vote_split")
    split = split_value if isinstance(split_value, dict) else {}
    return {
        "schema_version": "1",
        "finding_hash": _field(finding.get("finding_hash") or candidate.get("finding_hash")),
        "concern_hash": _field(finding.get("concern_hash") or candidate.get("concern_hash")),
        "source_skill": _field(finding.get("source_skill")),
        "run_id": _field(finding.get("run_id")),
        "round_num": _field(finding.get("round_num")),
        "finding_id": _field(finding.get("canonical_finding_id")),
        "reviewer_slots": ",".join(str(item) for item in finding.get("reviewer_slots") or []),
        "dissenting_slots": ",".join(str(item) for item in finding.get("dissenting_slots") or []),
        "file_path": _field(finding.get("file_path")),
        "line_hint": _field(finding.get("line_hint")),
        "yes_votes": _field(split.get("yes_votes")),
        "no_votes": _field(split.get("no_votes")),
        "high_severity": "true" if split.get("high_severity") else "false",
        "vote_split": _vote_split(finding),
        "verdict": verdict,
        "disposition": disposition,
        "issue_number": issue_number,
        "issue_url": issue_url,
        "triaged_at": _now_iso(),
        "alias_of": "",
    }


def _read_json_lines(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in read_text(path).splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _write_tsv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(columns)]
    for row in rows:
        lines.append("\t".join(sanitize(row.get(column, "")) for column in columns))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _cluster_key(candidate: dict[str, object]) -> str:
    path = _field(_finding(candidate).get("file_path"))
    parts = path.split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "general")


def _render_batch(clusters: list[tuple[str, list[dict[str, object]]]], verdicts: dict[str, dict[str, object]]) -> str:
    chunks: list[str] = []
    for key, candidates in clusters:
        finding = _finding(candidates[0])
        title = f"Recover rejected finding in {key or 'rejected finding'}: {_field(finding.get('concern'))[:80]}"
        chunks.append(f"### {title}\n")
        chunks.append("## Summary\n\nA rejected code-review finding was verified against current code and should be fixed.\n")
        chunks.append("## Findings\n")
        for candidate in candidates:
            finding = _finding(candidate)
            finding_hash = _field(finding.get("finding_hash") or candidate.get("finding_hash"))
            verdict = verdicts[finding_hash]
            chunks.append("\n")
            chunks.append(f"- Finding hash: `{finding_hash}`\n")
            chunks.append(f"  - File: `{_field(finding.get('file_path'))}`\n")
            chunks.append(f"  - Line hint: `{_field(finding.get('line_hint')) or 'none'}`\n")
            chunks.append(f"  - Concern: {sanitize(_field(finding.get('concern')))}\n")
            chunks.append(f"  - Provenance: {_field(finding.get('source_skill'))}/{_field(finding.get('run_id'))} round {_field(finding.get('round_num'))}, {_field(finding.get('canonical_finding_id'))}\n")
            chunks.append(f"  - Vote split: {sanitize(_vote_split(finding))}\n")
            dissenting = ", ".join(str(item) for item in finding.get("dissenting_slots") or []) or "none"
            chunks.append(f"  - Dissenting voter(s): `{dissenting}`\n")
            chunks.append(f"  - Verification verdict: `{_field(verdict.get('status'))}` at `{sanitize(_field(verdict.get('current_location')))}`\n")
            chunks.append(f"  - Verification evidence: {sanitize(_field(verdict.get('evidence')))}\n")
        chunks.append("\n## Suggested next step\n\nDesign and implement the smallest fix for the verified finding.\n\n")
    return "".join(chunks)


def finalize_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="rejected-analysis finalize")
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args(argv)
    work_dir = Path(args.work_dir)
    candidates = load_candidates(work_dir)
    statuses = {str(row.get("candidate_id") or ""): row for row in _read_json_lines(work_dir / INGEST_STATUS_FILE)}
    raw_verdicts = {str(row.get("candidate_id") or ""): row for row in _read_json_lines(work_dir / "verdicts.jsonl")}
    pending: list[dict[str, str]] = []
    confirmed: list[dict[str, object]] = []
    verdicts: dict[str, dict[str, object]] = {}
    launch_failures = 0
    for candidate_id, candidate in candidates.items():
        status = statuses.get(candidate_id)
        verdict = raw_verdicts.get(candidate_id)
        if status and status.get("status") == "launch-failed":
            launch_failures += 1
            continue
        if status and status.get("status") == "dirty-tree":
            pending.append(_ledger_row(candidate, verdict="dismissed", disposition="dismissed:dirty-tree"))
            continue
        if status and status.get("status") in {"parse-failed", "location-mismatch"}:
            pending.append(_ledger_row(candidate, verdict="dismissed", disposition="dismissed:verification-failed"))
            continue
        if status and status.get("status") == "ingested" and verdict and location_matches(_finding(candidate), _field(verdict.get("current_location"))):
            verdict_status = _field(verdict.get("status"))
            if verdict_status == "confirmed":
                finding_hash = _field(_finding(candidate).get("finding_hash") or candidate.get("finding_hash"))
                confirmed.append(candidate)
                verdicts[finding_hash] = verdict
            elif verdict_status == "stale":
                pending.append(_ledger_row(candidate, verdict="stale", disposition="dismissed:stale"))
            else:
                pending.append(_ledger_row(candidate, verdict="already-fixed", disposition="dismissed:already-fixed"))
            continue
        if status is None:
            launch_failures += 1
            pending.append(_ledger_row(candidate, verdict="dismissed", disposition="dismissed:verification-failed"))
        elif int(status.get("launcher_exit") or 0) == 0:
            pending.append(_ledger_row(candidate, verdict="dismissed", disposition="dismissed:verification-failed"))
    _write_tsv(work_dir / "ledger-pending.tsv", LEDGER_COLUMNS, pending)
    grouped: dict[str, list[dict[str, object]]] = {}
    for candidate in confirmed:
        grouped.setdefault(_cluster_key(candidate), []).append(candidate)
    clusters: list[tuple[str, list[dict[str, object]]]] = []
    for key in sorted(grouped):
        for offset in range(0, len(grouped[key]), 5):
            clusters.append((key, grouped[key][offset:offset + 5]))
    (work_dir / "issue-batch.md").write_text(_render_batch(clusters, verdicts), encoding="utf-8")
    (work_dir / "issue-cluster-map.json").write_text(
        json.dumps({"schema_version": 1, "clusters": [{"batch_index": index, "finding_hashes": [_field(_finding(candidate).get("finding_hash") or candidate.get("finding_hash")) for candidate in items]} for index, (_, items) in enumerate(clusters, 1)]}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    issue_output = work_dir / "issue.stdout.txt"
    if not issue_output.exists():
        issue_output.write_text("", encoding="utf-8")
    print(f"CONFIRMED_COUNT={sum(len(items) for _, items in clusters)}")
    print(f"ISSUE_BATCH_FILE={work_dir / 'issue-batch.md'}")
    print(f"ISSUE_CLUSTER_MAP_FILE={work_dir / 'issue-cluster-map.json'}")
    print(f"ISSUE_SENTINEL={work_dir / 'issue-completed.sentinel'}")
    print(f"LEDGER_PENDING_FILE={work_dir / 'ledger-pending.tsv'}")
    print(f"INGEST_STATUS_FILE={work_dir / INGEST_STATUS_FILE}")
    print(f"ISSUE_OUTPUT_STUB={issue_output}")
    print(f"LAUNCH_FAILURES={launch_failures}")
    return 0


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
    state_marker = read_text(work_dir / "state-root.txt").strip()
    state_root = Path(state_marker) if state_marker else (Path(args.repo_root) if args.repo_root else Path.cwd())
    candidates = load_candidates(work_dir)
    statuses = {str(row.get("candidate_id") or ""): row for row in _read_json_lines(work_dir / INGEST_STATUS_FILE)}
    launch_failed = {
        _field(row.get("finding_hash"))
        for row in statuses.values()
        if row.get("status") == "launch-failed"
    }
    pending_rows: list[dict[str, str]] = []
    pending_path = work_dir / "ledger-pending.tsv"
    pending_text = read_text(pending_path).splitlines()
    if pending_text:
        header = pending_text[0].split("\t")
        pending_rows = [dict(zip(header, line.split("\t"))) for line in pending_text[1:] if line]
    safe_rows = [row for row in pending_rows if row.get("finding_hash") not in launch_failed]
    issue_text = read_text(Path(args.issue_output)) if args.issue_output else ""
    values = {}
    for line in issue_text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    created = int(values.get("ISSUES_CREATED") or 0)
    failed = int(values.get("ISSUES_FAILED") or 0)
    deduplicated = int(values.get("ISSUES_DEDUPLICATED") or 0)
    if failed:
        args.issues_failed = failed
    cluster_value = json.loads(read_text(work_dir / "issue-cluster-map.json") or "{}")
    filed_rows: list[dict[str, str]] = []
    unmapped = False
    if args.issue_verified == "true":
        for cluster in cluster_value.get("clusters", []):
            index = int(cluster.get("batch_index") or 0)
            number = values.get(f"ISSUE_{index}_NUMBER")
            duplicate = False
            if not number:
                number = values.get(f"ISSUE_{index}_DUPLICATE_OF_NUMBER")
                duplicate = bool(number)
            hashes = cluster.get("finding_hashes") or []
            if not number:
                unmapped = unmapped or bool(hashes)
                continue
            url = values.get(f"ISSUE_{index}_{'DUPLICATE_OF_' if duplicate else ''}URL", "")
            for finding_hash in hashes:
                candidate = next((item for item in candidates.values() if _field(_finding(item).get("finding_hash") or item.get("finding_hash")) == finding_hash), None)
                if finding_hash in launch_failed:
                    continue
                if candidate is None:
                    unmapped = True
                    continue
                filed_rows.append(_ledger_row(candidate, verdict="confirmed", disposition="deduped-as" if duplicate else "filed-as", issue_number=number, issue_url=url))
    elif issue_text.strip() and (created > 0 or deduplicated > 0):
        unmapped = True
    ledger = state_root / "rejected-analysis" / "ledger.tsv"
    sidecar = state_root / "rejected-analysis" / "verdicts.tsv"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    (ledger.parent / ".ledger.tsv.lock").write_text("", encoding="utf-8")
    (ledger.parent / ".verdicts.tsv.lock").write_text("", encoding="utf-8")
    _write_tsv(ledger, LEDGER_COLUMNS, safe_rows + filed_rows)
    verdict_rows = {str(row.get("candidate_id") or ""): row for row in _read_json_lines(work_dir / "verdicts.jsonl")}
    sidecar_rows: list[dict[str, str]] = []
    for candidate_id, verdict in verdict_rows.items():
        if verdict.get("dirty_tree") or statuses.get(candidate_id, {}).get("status") == "dirty-tree":
            continue
        candidate = candidates.get(candidate_id)
        if candidate is None:
            continue
        finding = _finding(candidate)
        sidecar_rows.append({
            "schema_version": "1", "finding_hash": _field(finding.get("finding_hash") or candidate.get("finding_hash")),
            "source_skill": _field(finding.get("source_skill")), "run_id": _field(finding.get("run_id")),
            "round_num": _field(finding.get("round_num")), "finding_id": _field(finding.get("canonical_finding_id")),
            "dissenting_slots": ",".join(str(item) for item in finding.get("dissenting_slots") or []),
            "verdict": _field(verdict.get("status")), "current_location": sanitize(_field(verdict.get("current_location"))),
            "evidence": sanitize(_field(verdict.get("evidence"))), "triaged_at": _now_iso(),
        })
    if sidecar_rows:
        _write_tsv(sidecar, SIDECAR_COLUMNS, sidecar_rows)
    dismissed = sum(row.get("disposition", "").startswith("dismissed:") for row in safe_rows)
    rc = 1 if unmapped or args.issues_failed > 0 or args.issue_verified == "false" or max(args.launch_failures, len(launch_failed)) > 0 else 0
    print(f"LEDGER_APPENDED={len(safe_rows) + len(filed_rows)}")
    print(f"ISSUES_CREATED={created}")
    print(f"ISSUES_DEDUPLICATED={deduplicated}")
    print(f"DISMISSED_COUNT={dismissed}")
    print(f"UNMAPPED_CONFIRMED={'true' if unmapped else 'false'}")
    print(f"RECORD_EXIT_RC={rc}")
    return rc


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("missing rejected-analysis fixture command")
    command, *arguments = sys.argv[1:]
    if command == "ingest-verdict":
        raise SystemExit(ingest_verdict_main(arguments))
    if command == "prepare":
        raise SystemExit(prepare_main(arguments))
    if command == "finalize":
        raise SystemExit(finalize_main(arguments))
    if command == "record":
        raise SystemExit(record_main(arguments))
    raise SystemExit(f"unsupported rejected-analysis fixture command: {command}")
