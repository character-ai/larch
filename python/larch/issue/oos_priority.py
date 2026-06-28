"""Priority helpers for high-risk public OOS issues."""

from __future__ import annotations

import re

OOS_CORRECTNESS_LABEL = "oos-correctness"
OOS_CORRECTNESS_LABEL_COLOR = "d73a4a"
OOS_CORRECTNESS_LABEL_DESCRIPTION = "High-risk correctness or regression OOS deferral"
HIGH_RISK_FOCUS_VALUES = frozenset({"correctness", "regression"})

_FOCUS_AREA_LINE_RE = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:\*\*)?focus[ -]area(?:\*\*)?\s*[:=]\s*([^\s,;.)]+)",
    re.IGNORECASE,
)
_ISSUE_NUMBER_RE = re.compile(r"/issues/(\d+)(?:\D*)$")


def is_high_risk_oos_block(text: str) -> bool:
    """Return True when an OOS block carries a high-risk focus area."""
    for line in text.splitlines():
        match = _FOCUS_AREA_LINE_RE.match(line)
        if not match:
            continue
        value = match.group(1).strip().strip("`*_[](){}.,;:").lower()
        if value in HIGH_RISK_FOCUS_VALUES:
            return True
    return False


def issue_number_from_url(url: str) -> str:
    """Extract a GitHub issue number from an issue URL."""
    match = _ISSUE_NUMBER_RE.search(url.strip())
    return match.group(1) if match else ""


def label_create_argv(*, repo: str = "") -> list[str]:
    """Return argv for idempotently provisioning the high-risk OOS label."""
    argv = [
        "gh",
        "label",
        "create",
        OOS_CORRECTNESS_LABEL,
        "--force",
        "--color",
        OOS_CORRECTNESS_LABEL_COLOR,
        "--description",
        OOS_CORRECTNESS_LABEL_DESCRIPTION,
    ]
    if repo:
        argv.extend(["--repo", repo])
    return argv


def label_edit_argv(issue_number: str, *, repo: str = "") -> list[str]:
    """Return argv for applying the high-risk OOS label to an issue."""
    argv = ["gh", "issue", "edit", issue_number, "--add-label", OOS_CORRECTNESS_LABEL]
    if repo:
        argv.extend(["--repo", repo])
    return argv
