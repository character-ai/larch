"""Shared best-effort review phase detail rendering for final reports."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import os
import re
from pathlib import Path

from larch.core import redact
from larch.report import progress_report
from larch.review import voting

RENDER_PHASE_DETAIL_TIMEOUT_SECONDS = 15
REJECTED_OOS_AUDIT_LIMIT = 10
_REJECTED_OOS_REASON_LIMIT = 260
_REJECTED_OOS_BLOCK_RE = re.compile(
    r"(?ms)^###\s+((?:OOS|FINDING)_[0-9A-Za-z_]+):[ \t]*(.*?)\n(.*?)(?=^###\s+(?:OOS|FINDING)_[0-9A-Za-z_]+:|\Z)"
)
_REJECTED_OOS_FIELD_RE_TEMPLATE = (
    r"(?ms)^[ \t]*-[ \t]+\*\*{label}\*\*:[ \t]*(.*?)(?=\n[ \t]*-[ \t]+\*\*[^*]+\*\*:|\n###\s+|\Z)"
)


def _path_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _latest_token_ledger(tmpdir: Path) -> Path | None:
    try:
        token_ledgers = sorted(tmpdir.glob("larch-tokens-*.jsonl"), key=_path_mtime)
    except OSError:
        return None
    return token_ledgers[-1] if token_ledgers else None


def _readable_dir(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.R_OK | os.X_OK)


def _invoke_renderer(
    rounds_root: Path,
    *,
    skill: str,
    timing_ledger: Path | None = None,
    token_ledger: Path | None = None,
    findings_file: Path | None = None,
) -> str:
    if not _readable_dir(rounds_root):
        return ""
    try:
        stdout = progress_report._render_phase_detail_best_effort(  # noqa: SLF001 - shared best-effort renderer.
            rounds_root,
            skill=skill,
            timing_ledger=timing_ledger if timing_ledger is not None and timing_ledger.is_file() else None,
            token_ledger=token_ledger if token_ledger is not None and token_ledger.is_file() else None,
            findings_file=findings_file if findings_file is not None and findings_file.is_file() else None,
        )
    except Exception:  # pylint: disable=broad-except
        return ""
    if not stdout.strip():
        return ""
    text = redact.redact_outbound(stdout)
    if "[content truncated" in text:
        return ""
    return text


def _join_markdown_sections(*sections: str) -> str:
    parts = [section.strip("\n") for section in sections if section.strip()]
    if not parts:
        return ""
    return "\n\n".join(parts) + "\n"


def _field_value(block: str, label: str) -> str:
    pattern = re.compile(_REJECTED_OOS_FIELD_RE_TEMPLATE.format(label=re.escape(label)))
    match = pattern.search(block)
    return _flatten_text(match.group(1)) if match else ""


def _flatten_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _clean_oos_title(title: str, fallback: str) -> str:
    cleaned = _flatten_text(title)
    cleaned = re.sub(r"^(?:\[(?:OUT_OF_SCOPE|OOS)\]\s*)+", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned or fallback


def _round_label(path: Path) -> str:
    match = re.search(r"round-([0-9]+)", path.parent.name)
    return match.group(1) if match else "?"


def _vote_result(block: str) -> str:
    match = re.search(r"(?mi)^Vote tally:.*\bResult=([a-z-]+)", block)
    return match.group(1).lower() if match else "unknown"


def _rejected_oos_audit_from_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    candidates: list[str] = []
    for match in _REJECTED_OOS_BLOCK_RE.finditer(text):
        oos_id = match.group(1)
        title = _clean_oos_title(match.group(2), oos_id)
        block = match.group(0)
        if oos_id.startswith("FINDING_") and not re.search(r"\[(OUT_OF_SCOPE|OOS)\]", match.group(2), re.IGNORECASE):
            continue
        result = _vote_result(block)
        if result == "accepted" or voting.is_security_block_text(block):
            continue
        severity = _field_value(block, "Severity") or "unknown"
        concern = _field_value(block, "Concern")
        rationale = f"{title}."
        if concern:
            rationale += f" Concern: {_truncate_text(concern, _REJECTED_OOS_REASON_LIMIT)}"
        candidates.append(f"- **Round {_round_label(path)} {oos_id}** ({result}, {severity}): {rationale}")
    return candidates


def render_rejected_oos_audit_section(rounds_root: Path) -> str:
    try:
        audit_files = sorted(rounds_root.glob("round-*/oos.md"))
    except OSError:
        return ""
    candidates: list[str] = []
    for audit_file in audit_files:
        if len(candidates) >= REJECTED_OOS_AUDIT_LIMIT:
            break
        remaining = REJECTED_OOS_AUDIT_LIMIT - len(candidates)
        candidates.extend(_rejected_oos_audit_from_file(audit_file)[:remaining])
    if not candidates:
        return ""
    total_candidates = sum(len(_rejected_oos_audit_from_file(audit_file)) for audit_file in audit_files)
    lines = [
        "## Rejected OOS audit",
        "",
        "These OOS observations reached the vote but were not accepted for filing.",
        "",
        *candidates,
    ]
    omitted = total_candidates - len(candidates)
    if omitted > 0:
        lines.append(f"- **Additional audit rows**: {omitted} omitted by the final-summary cap.")
    text = "\n".join(lines).rstrip() + "\n"
    redacted = redact.redact_outbound(text)
    return "" if "[content truncated" in redacted else redacted


def render_design_review_detail(design_tmpdir: Path) -> str:
    timing_ledger = design_tmpdir / "timing-ledger.tsv"
    findings_file = design_tmpdir / "review-findings-full.jsonl"
    return _invoke_renderer(
        design_tmpdir / "plan-review",
        skill="design",
        timing_ledger=timing_ledger if timing_ledger.is_file() else None,
        token_ledger=_latest_token_ledger(design_tmpdir),
        findings_file=findings_file if findings_file.is_file() else None,
    )


def render_implement_review_detail(*, implement_tmpdir: Path, run_id: str) -> str:
    run_dir = implement_tmpdir / "larch-logs" / "implement" / run_id
    rounds_root = run_dir if run_dir.is_dir() else implement_tmpdir
    timing_ledger = implement_tmpdir / "timing-ledger.tsv"
    token_ledger = _latest_token_ledger(implement_tmpdir)
    findings_file = run_dir / "review-findings-full.jsonl"
    if not findings_file.is_file():
        findings_file = implement_tmpdir / "review-findings-full.jsonl"
    detail = _invoke_renderer(
        rounds_root,
        skill="implement",
        timing_ledger=timing_ledger if timing_ledger.is_file() else None,
        token_ledger=token_ledger,
        findings_file=findings_file if findings_file.is_file() else None,
    )
    rejected_oos = render_rejected_oos_audit_section(rounds_root)
    return _join_markdown_sections(detail, rejected_oos)


def append_review_phase_detail(*, body: str, detail: str) -> str:
    if not detail:
        return body
    return body.rstrip("\n") + "\n\n" + detail.strip("\n") + "\n"
