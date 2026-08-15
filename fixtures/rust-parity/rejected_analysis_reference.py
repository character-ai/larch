# ruff: noqa: PLR0913,PLR2004
"""Frozen Python behavior for the rejected-analysis command parity contract.

This is the pre-#8503 `rejected-analysis` command restricted to the hermetic
fixture paths exercised by `crates/larch-cli/tests/parity.rs`.
It deliberately remains a test oracle, not a runtime fallback or a second
production owner. The cases compare the command's exit code, stdout, stderr,
and the `verdicts.jsonl` and `ingest-status.jsonl` wire files. The prepare
cases pin repository-preflight ordering without reaching a live GitHub snapshot.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


INGEST_STATUS_FILE = "ingest-status.jsonl"
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("missing rejected-analysis fixture command")
    command, *arguments = sys.argv[1:]
    if command == "ingest-verdict":
        raise SystemExit(ingest_verdict_main(arguments))
    if command == "prepare":
        raise SystemExit(prepare_main(arguments))
    raise SystemExit(f"unsupported rejected-analysis fixture command: {command}")
