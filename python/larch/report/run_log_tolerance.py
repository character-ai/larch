"""Shared stale-bail tolerance for audit-runs and verify-completeness."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

_STALE_BAIL_HEADING_RE = re.compile(r"bailed(-needs-user-input)?$")
_TERMINAL_OUTCOME_SUFFIX = re.compile(
    r"(bailed(-needs-user-input)?|stalled|design-only|forked-dry-run|pr-created(-draft)?|shipping)$",
)


def first_nonempty_line(path: Path) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            return line.strip()
    return ""


def manifest_pr_evidence_matches(*, manifest: object | None, pr: int) -> bool:
    if not isinstance(manifest, dict):
        return False
    data = cast("dict[str, object]", manifest)
    raw = str(data.get("pr_number") or "").strip()
    if not raw or raw == "0" or not raw.isdigit():
        return False
    value = int(raw)
    if pr > 0:
        return value == pr
    return value > 0


def stale_bail_heading_with_pr_evidence(*, run_dir: Path, manifest: object | None, pr: int) -> bool:
    heading = first_nonempty_line(run_dir / "final-summary.md")
    return bool(_STALE_BAIL_HEADING_RE.search(heading) and manifest_pr_evidence_matches(manifest=manifest, pr=pr))


def final_summary_terminal_heading(run_dir: Path) -> bool:
    summary = run_dir / "final-summary.md"
    if not summary.is_file():
        return False
    for line in summary.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            return bool(_TERMINAL_OUTCOME_SUFFIX.search(line.rstrip("\r\n")))
    return False


def terminal_bail_skip_signal(*, run_dir: Path, manifest: object | None, pr: int = 0) -> bool:
    """True when verify/audit should apply bail-time required-file skip."""
    if stale_bail_heading_with_pr_evidence(run_dir=run_dir, manifest=manifest, pr=pr):
        return False
    return final_summary_terminal_heading(run_dir)
