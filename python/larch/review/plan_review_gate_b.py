"""Gate B finding classification, severity display, and preview for plan review."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from larch.review.plan_review_common import AcceptedFinding, GateBDisplayRow, GateBSeveritySummary

_STRUCTURED_GATE_B_SEVERITIES = {"blocking", "important", "latent", "nit"}
_GATE_B_LABELS_STRUCTURED = {
    "blocking": "High",
    "important": "High",
    "latent": "Medium",
    "nit": "Low",
}
_GATE_B_BUCKET_ORDER = ("Low", "Medium", "High", "Critical")


def _accepted_finding_field(block: str, *, label: str) -> str:
    pattern = re.compile(rf"(?mi)^-\s+(?:\*\*)?{re.escape(label)}(?:\*\*)?:\s*(.*)$")
    match = pattern.search(block)
    if not match:
        return ""
    lines = [match.group(1).strip()]
    tail = block[match.end() :].splitlines()
    for line in tail:
        if re.match(r"^(?:-\s+|###\s+)", line):
            break
        if line.strip():
            lines.append(line.strip())
    return "\n".join(lines).strip()


def _accepted_finding_reviewers(block: str) -> str:
    match = re.search(r"(?mi)^-\s+(?:\*\*)?Reviewer(?:\(s\))?(?:\*\*)?:\s*(.*)$", block)
    return match.group(1).strip() if match else ""


def _parse_accepted_findings(tmpdir: Path) -> list[AcceptedFinding]:
    path = tmpdir / "accepted-plan-findings.md"
    if not path.is_file() or path.is_symlink():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: list[AcceptedFinding] = []
    for block in re.findall(r"(?ms)^### FINDING_[0-9]+:.*?(?=^### |\Z)", text):
        id_match = re.search(r"(?m)^### FINDING_([0-9]+):", block)
        if not id_match:
            continue
        severity_match = re.search(r"(?mi)^-\s+\*\*Severity\*\*:\s*([A-Za-z_-]+)\s*$", block)
        severity_raw = severity_match.group(1).lower() if severity_match else ""
        findings.append(
            AcceptedFinding(
                finding_id=int(id_match.group(1), 10),
                block=block,
                severity_raw=severity_raw,
                concern=_accepted_finding_field(block=block, label="Concern"),
                reviewers=_accepted_finding_reviewers(block),
            )
        )
    return findings


def _gate_b_fallback_predicates(concern: str) -> set[str]:
    text = concern.lower()
    matches: set[str] = set()
    if re.search(r"\b(style|naming|future[- ]proofing|no functional change)\b", text):
        matches.add("Low")
    if re.search(r"\b(robustness|clarity|secondary path|recoverable edge case)\b", text):
        matches.add("Medium")
    if re.search(
        r"\b(functional incorrectness|primary code path|missing required documentation contract|"
        r"missing required[^.]*doc|violates?[^.]*invariant|stated invariant)\b",
        text,
    ):
        matches.add("High")
    if re.search(
        r"\b(data loss|security breach|build/ci breakage|build breakage|ci breakage|"
        r"breaks (?:the )?build|breaks ci|downstream[^.]*regression|regression[^.]*downstream)\b",
        text,
    ):
        matches.add("Critical")
    return matches


def _gate_b_fallback_label(concern: str) -> str:
    # Gate B fallback mirrors skills/design/references/approval-gates.md:
    # collect every Concern-text predicate that matches, choose the lowest
    # bucket (Low < Medium < High < Critical), and default no-match or empty
    # concerns to Low. This display bucketing is intentionally separate from
    # plan_review_continuation's legacy whole-block high predicate.
    matches = _gate_b_fallback_predicates(concern)
    if not matches:
        return "Low"
    return min(matches, key=_GATE_B_BUCKET_ORDER.index)


def _classify_gate_b_severity(findings: Sequence[AcceptedFinding]) -> GateBSeveritySummary:
    structured = all(finding.severity_raw in _STRUCTURED_GATE_B_SEVERITIES for finding in findings)
    mode = "structured" if structured else "fallback"
    labels: dict[int, str] = {}
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for finding in findings:
        label = (
            _GATE_B_LABELS_STRUCTURED[finding.severity_raw]
            if structured
            else _gate_b_fallback_label(finding.concern)
        )
        labels[finding.finding_id] = label
        counts[label] += 1
    return GateBSeveritySummary(
        mode=mode,
        critical_count=counts["Critical"],
        high_count=counts["High"],
        medium_count=counts["Medium"],
        low_count=counts["Low"],
        display_labels=labels,
        finding_ids=tuple(finding.finding_id for finding in findings),
    )


def _gate_b_display_label(finding: AcceptedFinding, *, summary: GateBSeveritySummary) -> str:
    return summary.display_labels.get(finding.finding_id, "Low")


def _gate_b_excerpt(concern: str) -> str:
    lines = [line.strip() for line in concern.splitlines() if line.strip()][:2]
    return " ".join(lines)[:200]


def _gate_b_display_rows(tmpdir: Path) -> list[GateBDisplayRow]:
    findings = _parse_accepted_findings(tmpdir)
    summary = _classify_gate_b_severity(findings)
    return [
        GateBDisplayRow(
            finding_id=finding.finding_id,
            display_severity_label=_gate_b_display_label(finding=finding, summary=summary),
            reviewer_text=finding.reviewers,
            excerpt=_gate_b_excerpt(finding.concern),
        )
        for finding in findings
    ]


def _emit_gate_b_preview(tmpdir: Path) -> int:
    print("## Plan Review Findings: Review")
    print()
    for row in _gate_b_display_rows(tmpdir):
        print(f"FINDING_{row.finding_id} | {row.display_severity_label} | {row.reviewer_text} | {row.excerpt}")
    for name, header in (
        ("rejected-findings.md", "## Rejected Findings: Context"),
        ("oos.md", "## Out-of-Scope Findings: Context"),
    ):
        path = tmpdir / name
        text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() and not path.is_symlink() else ""
        if text.strip():
            print()
            print(header)
            print()
            print(text, end="" if text.endswith("\n") else "\n")
    return 0


# pyright: reportUnusedFunction=false
