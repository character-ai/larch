# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Compose review finding JSONL records."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from contextlib import suppress
from pathlib import Path
from larch.core import logging_util
from larch.core import redact
import voting

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_CANONICAL_CATEGORIES = {"code-quality", "risk-integration", "correctness", "architecture", "security"}
_CATEGORY_LOCATION_PARTS = 3
_TSV_MIN_FIELDS = 2


def _fail(message: str) -> int:
    logging_util.emit_kv(key="FAILED", value="true")
    logging_util.emit_kv(key="ERROR", value=message)
    return 2


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _redact_field(value: str) -> str:
    return redact.redact_outbound(redact.redact_tmpdir_paths(value))


def _extract_body_severity(body: str) -> str:
    for line in body.splitlines():
        match = re.match(r"^[\s-]*\*\*Severity\*\*:\s*(.*?)\s*$", line)
        if match:
            return match.group(1)
    return ""


def _extract_focus_area(body: str) -> str:
    for line in body.splitlines():
        match = re.match(r"^[\s-]*\*\*Focus area\*\*:\s*(.*?)\s*$", line, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _extract_reviewer(body: str) -> str:
    patterns = (
        r"^[\s-]*\*\*Reviewer\(s\)\*\*:\s*(.+)$",
        r"^[\s-]*\*\*Reviewers?\*\*:\s*(.+)$",
        r"^[\s-]*Reviewer\(s\):\s*(.+)$",
        r"^[\s-]*Reviewers?:\s*(.+)$",
    )
    for line in body.splitlines():
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                return match.group(1).replace("*", "").strip()
    return ""


def _extract_category(body: str, *, strict: bool = False) -> str:
    def canonical(value: str) -> bool:
        return value in _CANONICAL_CATEGORIES

    for line in body.splitlines():
        if line.startswith("### FINDING_"):
            rest = re.sub(r"^###\s+FINDING_[0-9A-Za-z_]+:\s*", "", line)
            parts = [part.strip() for part in rest.split(":")]
            if parts and (len(parts) >= _CATEGORY_LOCATION_PARTS or canonical(parts[0])):
                candidate = parts[0]
            else:
                continue
            if candidate and ((not strict) or canonical(candidate)):
                return candidate
        if line.startswith("## "):
            candidate = line[3:].strip()
            if candidate.startswith("**"):
                match = re.match(r"^\*\*(.*?)\*\*", candidate)
                candidate = match.group(1) if match else candidate.strip("*")
            else:
                candidate = candidate.split(":", 1)[0].strip()
            if not candidate:
                continue
            if strict and not canonical(candidate):
                continue
            return candidate
    return ""


def _human_label(slot: str) -> str:
    pairs = (
        ("dyn-cursor-plan-", "Cursor-dyn-", True),
        ("dyn-codex-plan-", "Codex-dyn-", True),
        ("cursor-plan-", "Cursor-", False),
        ("codex-plan-", "Codex-", False),
        ("claude-plan-", "Claude-", False),
    )
    for prefix, label, dynamic in pairs:
        if slot.startswith(prefix):
            rest = slot[len(prefix) :]
            return label + (rest if dynamic else re.sub(r"[_ ]+", " ", rest).title().replace(" ", ""))
    return slot


def _build_design_reviewer_map(design_dir: Path | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not design_dir:
        return mapping
    manifest_paths: list[Path] = []
    rounds = design_dir / "plan-review"
    if rounds.is_dir():
        round_paths: list[tuple[int, Path]] = []
        for child in rounds.iterdir():
            match = re.match(r"round-([0-9]+)$", child.name)
            if match and child.is_dir():
                round_paths.append((int(match.group(1)), child / "plan-review-slots.ndjson"))
        manifest_paths.extend(path for _idx, path in sorted(round_paths))
    manifest_paths.append(design_dir / "plan-review-slots.ndjson")
    for path in manifest_paths:
        if not path.is_file():
            continue
        for line in _read(path).splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            output = str(row.get("output") or "")
            base = Path(output).name
            slot = str(row.get("slot") or "")
            if base:
                if slot and slot not in mapping:
                    mapping[slot] = base
                human = _human_label(slot)
                if human and human not in mapping:
                    mapping[human] = base
    label_maps = [design_dir / "plan-review-prune-label-map.tsv"]
    if rounds.is_dir():
        label_maps.extend(child / "plan-review-prune-label-map.tsv" for child in sorted(rounds.iterdir(), key=lambda p: p.name) if child.is_dir())
    for path in label_maps:
        if not path.is_file():
            continue
        for line in _read(path).splitlines():
            parts = line.split("\t")
            if len(parts) < _TSV_MIN_FIELDS:
                continue
            slot, label = parts[0].strip(), parts[1].strip()
            if slot in mapping and label and label not in mapping:
                mapping[label] = mapping[slot]
    return mapping


def _normalize_design_reviewer(*, reviewer: str, mapping: dict[str, str]) -> str:
    if not mapping:
        return reviewer
    out = [mapping.get(part.strip(), part.strip()) for part in reviewer.split(",") if part.strip()]
    return ",".join(out) if out else reviewer


def _is_security_text(body: str) -> bool:
    fd, tmp_name = tempfile.mkstemp()
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(body)
        return voting.is_security_block(tmp)
    finally:
        with suppress(OSError):
            tmp.unlink()


def _emit_record(*, records: list[dict[str, object]], item_id: str, phase: str, outcome: str, reviewer: str, body: str, round_num: str, issue: str, design_map: dict[str, str]) -> None:
    if phase == "plan-review":
        reviewer = _normalize_design_reviewer(reviewer=reviewer, mapping=design_map)
    reviewer_redacted = _redact_field(reviewer)
    body_redacted = _redact_field(body)
    body_severity = _extract_body_severity(body_redacted)
    focus_area = _extract_focus_area(body_redacted)
    strict = outcome == "out_of_scope" or (phase == "plan-review" and outcome == "accepted")
    category = _extract_category(body_redacted, strict=strict)
    reviewer_slots = [part.strip() for part in reviewer_redacted.split(",") if part.strip()] or ["panel"]
    records.append(
        {
            "id": item_id,
            "issue_number": issue,
            "phase": phase,
            "outcome": outcome,
            "schema_version": "2",
            "reviewer_slots": reviewer_slots,
            "round_num": round_num,
            "category": category,
            "body_severity": body_severity,
            "focus_area": focus_area,
            "prose_body": body_redacted[:2000],
        }
    )


def _synthetic_id(*, prefix: str, counter: int, round_num: str) -> str:
    return f"{prefix}R{round_num}_{counter}" if round_num else f"{prefix}{counter}"


def _parse_artifact(*, path: Path, kind: str, round_num: str, issue: str, design_map: dict[str, str], records: list[dict[str, object]]) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        return
    phase = "plan-review" if kind.startswith("plan-review") else "code-review"
    outcome = "accepted" if kind.endswith("accepted") else "rejected" if kind.endswith("rejected") else "out_of_scope"
    id_prefix = {"plan-review-rejected": "REJ_P", "code-review-rejected": "REJ_C", "code-review-oos": "OOS_C"}.get(kind, "")
    pending_id = pending_title = pending_reviewer = ""
    pending_lines: list[str] = []
    counter = 0

    def flush() -> None:
        nonlocal pending_id, pending_title, pending_reviewer, pending_lines
        if not pending_id:
            return
        body = "\n".join(pending_lines)
        if pending_title:
            body = f"## {pending_title}\n\n{body}"
        reviewer = pending_reviewer or _extract_reviewer(body) or "panel"
        if kind == "code-review-oos" and _is_security_text(body):
            pending_id = pending_title = pending_reviewer = ""
            pending_lines = []
            return
        _emit_record(records=records, item_id=pending_id, phase=phase, outcome=outcome, reviewer=reviewer, body=body, round_num=round_num, issue=issue, design_map=design_map)
        pending_id = pending_title = pending_reviewer = ""
        pending_lines = []

    for line in _read(path).splitlines():
        if kind in {"plan-review-accepted", "code-review-accepted"}:
            match = re.match(r"^###\s+(FINDING_[0-9A-Za-z_]+):\s*(.*)$", line)
            if match:
                flush()
                pending_id = match.group(1)
                pending_title = match.group(2)
                continue
        elif kind == "plan-review-rejected":
            match = re.match(r"^###\s+\[Plan\s+Review\]\s+(.+)$", line)
            if match:
                flush()
                counter += 1
                pending_id = _synthetic_id(prefix=id_prefix, counter=counter, round_num=round_num)
                pending_reviewer = match.group(1)
                continue
        elif kind == "code-review-rejected":
            match = re.match(r"^###\s+\[(rejected|Code\s+Review)\]\s+(.+)$", line)
            if match:
                flush()
                counter += 1
                pending_id = _synthetic_id(prefix=id_prefix, counter=counter, round_num=round_num)
                if match.group(1) == "Code Review":
                    pending_reviewer = match.group(2)
                continue
            if pending_id and line.startswith("### "):
                pending_lines.append(line)
                continue
        elif kind == "code-review-oos":
            match = re.match(r"^###\s+OOS_[0-9A-Za-z_]+:\s*(.*)$", line)
            match2 = re.match(r"^###\s+FINDING_[0-9A-Za-z_]+:\s*\[OUT_OF_SCOPE\]\s*(.*)$", line)
            if match or match2:
                flush()
                counter += 1
                pending_id = _synthetic_id(prefix=id_prefix, counter=counter, round_num=round_num)
                pending_title = (match or match2).group(1)  # type: ignore[union-attr]
                continue
            if pending_id and line.startswith("### "):
                pending_lines.append(line)
                continue
        if line.startswith("### "):
            flush()
            continue
        if pending_id:
            pending_lines.append(line)
    flush()


def _filter_gate_b(*, accepted: Path, rejected: Path) -> str:
    reason = "rejected by user during one-by-one review"
    rejected_text = _read(rejected) if rejected.is_file() else ""
    def normalize(block: str) -> str:
        return "\n".join(line.rstrip() for line in block.strip().splitlines() if reason not in line).strip()

    skipped = {
        normalize(block)
        for block in re.findall(r"(?ms)^### FINDING_[0-9A-Za-z_]+:.*?(?=^### |\Z)", rejected_text)
        if reason in block
    }
    kept = []
    for block in re.findall(r"(?ms)^### FINDING_[0-9A-Za-z_]+:.*?(?=^### |\Z)", _read(accepted)):
        norm = normalize(block)
        if norm not in skipped:
            kept.append(block.strip())
    return "\n\n".join(kept) + ("\n\n" if kept else "")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="compose-findings")
    parser.add_argument("--design-artifacts-dir", default="")
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--issue", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--archive-dir", default="")
    parser.add_argument("--archive-threshold", default="")
    return parser.parse_args(argv)


def compose_findings(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="compose-findings")
    try:
        args = _parse_args(argv=argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    if not args.issue.isdigit():
        return _fail(f"invalid value for --issue: '{args.issue}' (expected non-negative integer)")
    output = Path(args.output)
    design_dir = Path(args.design_artifacts_dir) if args.design_artifacts_dir else None
    implement_tmpdir = Path(args.implement_tmpdir) if args.implement_tmpdir else None
    records: list[dict[str, object]] = []
    design_map = _build_design_reviewer_map(design_dir)
    if design_dir:
        accepted = design_dir / "accepted-plan-findings-all.md"
        if not accepted.is_file() or accepted.stat().st_size == 0:
            accepted = design_dir / "accepted-plan-findings.md"
        if accepted.is_file() and (design_dir / "rejected-findings.md").is_file() and "rejected by user during one-by-one review" in _read(design_dir / "rejected-findings.md"):
            fd, tmp_name = tempfile.mkstemp(prefix="review-findings-design-accepted.")
            os.close(fd)
            tmp = Path(tmp_name)
            _ = tmp.write_text(_filter_gate_b(accepted=accepted, rejected=design_dir / "rejected-findings.md"), encoding="utf-8")
            _parse_artifact(path=tmp, kind="plan-review-accepted", round_num="", issue=args.issue, design_map=design_map, records=records)
            with suppress(OSError):
                tmp.unlink()
        else:
            _parse_artifact(path=accepted, kind="plan-review-accepted", round_num="", issue=args.issue, design_map=design_map, records=records)
        _parse_artifact(path=design_dir / "rejected-findings.md", kind="plan-review-rejected", round_num="", issue=args.issue, design_map=design_map, records=records)
    if implement_tmpdir:
        round_dirs = sorted([p for p in implement_tmpdir.glob("round-*") if p.is_dir()], key=lambda p: p.name)
        rejected_found = False
        for round_dir in round_dirs:
            round_num = round_dir.name.removeprefix("round-")
            _parse_artifact(path=round_dir / "accepted-findings.md", kind="code-review-accepted", round_num=round_num, issue=args.issue, design_map=design_map, records=records)
            _parse_artifact(path=round_dir / "oos.md", kind="code-review-oos", round_num=round_num, issue=args.issue, design_map=design_map, records=records)
            if (round_dir / "rejected-findings-full.md").is_file() and (round_dir / "rejected-findings-full.md").stat().st_size > 0:
                rejected_found = True
                _parse_artifact(path=round_dir / "rejected-findings-full.md", kind="code-review-rejected", round_num=round_num, issue=args.issue, design_map=design_map, records=records)
            elif (round_dir / "rejected-findings.md").is_file() and (round_dir / "rejected-findings.md").stat().st_size > 0:
                rejected_found = True
                _parse_artifact(path=round_dir / "rejected-findings.md", kind="code-review-rejected", round_num=round_num, issue=args.issue, design_map=design_map, records=records)
        if not rejected_found:
            full = implement_tmpdir / "rejected-findings-full.md"
            _parse_artifact(path=full if full.is_file() and full.stat().st_size > 0 else implement_tmpdir / "rejected-findings.md", kind="code-review-rejected", round_num="", issue=args.issue, design_map=design_map, records=records)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n" for record in records), encoding="utf-8")
    logging_util.emit_kv(key="COMPOSED", value="true")
    logging_util.emit_kv(key="OUTPUT", value=str(output))
    logging_util.emit_kv(key="FINDINGS_TOTAL", value=str(len(records)))
    logging_util.emit_kv(key="MODE", value="jsonl")
    return 0


def compose_findings_main(argv: list[str]) -> int:
    return compose_findings(argv)
