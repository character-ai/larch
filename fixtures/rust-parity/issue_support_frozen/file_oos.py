"""Retained in-process OOS helpers for Python workflow consumers.

The six OOS commands migrated by #8178 and #8179 are Rust-owned behind
``scripts/larch.sh``. This module is not a command implementation or fallback.
Surviving callers use its block parsing, counting, and title-normalization
helpers. The issue-domain migration ledger assigns this remaining Python
library to receiving umbrella #7680.
"""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from larch.core import config
from larch.core.findings import count_non_security_blocks, parse_blocks
from larch.core.redact import redact


# ---------------------------------------------------------------------------
# Constants (moved from config to keep OOS-specific tunables here)
# ---------------------------------------------------------------------------
INLINE_TRIAGE_MARKER: str = config.INLINE_TRIAGE_MARKER
OOS_FILED_URL_FIELD: str = config.OOS_FILED_URL_FIELD


# ---------------------------------------------------------------------------
# Regexes (ported from oos.py)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# GitHub URL helper
# ---------------------------------------------------------------------------
def _github_issue_url_pattern() -> re.Pattern[str]:
    gh_host = os.environ.get("GH_HOST", "github.com")
    if gh_host and gh_host != "github.com":
        esc = re.escape(gh_host)
        host = f"(?:{esc}|github\\.com)"
    else:
        host = r"github\.com"
    return re.compile(
        rf"https://{host}/[^/\s]+/[^/\s]+/issues/\d+",
    )


# ---------------------------------------------------------------------------
# Block-counting (ported from oos.py; includes #3550 legacy-header support)
# ---------------------------------------------------------------------------
def _count_non_security_markdown(text: str) -> int:
    """Count accepted non-security OOS blocks with shared policy."""
    return count_non_security_blocks(text)


def count_non_security(accepted_paths: tuple[str, ...]) -> int:
    """Count non-security accepted OOS blocks across markdown files."""
    total = 0
    for path in accepted_paths:
        file_path = Path(path)
        if not file_path.is_file():
            continue
        text = file_path.read_text(encoding="utf-8")
        total += _count_non_security_markdown(text)
    return total


# ---------------------------------------------------------------------------
# Idempotency: sentinel-based URL recovery
# ---------------------------------------------------------------------------
def read_filed_urls_from_sentinel(sentinel_path: str | None) -> list[str]:
    """Return GitHub issue URLs already recorded in the sentinel file."""
    if not sentinel_path or not Path(sentinel_path).is_file():
        return []
    url_re = _github_issue_url_pattern()
    text = Path(sentinel_path).read_text(encoding="utf-8")
    return url_re.findall(text)


# ---------------------------------------------------------------------------
# Accepted-OOS path resolution (bash checkpoint order)
# ---------------------------------------------------------------------------
def resolve_design_oos_path(tmpdir: Path) -> Path:
    """Resolve accepted design OOS path in bash checkpoint order."""
    design_tmpdir = os.environ.get("DESIGN_TMPDIR", "")
    if design_tmpdir:
        design_path = Path(design_tmpdir) / "oos-accepted-design.md"
        if design_path.is_file():
            return design_path
    exported = tmpdir / "design-export" / "oos-accepted-design.md"
    if exported.is_file():
        return exported
    return tmpdir / "oos-accepted-design.md"


def accepted_oos_paths(tmpdir: Path) -> tuple[str, ...]:
    """Return the canonical accepted-OOS file paths for the given tmpdir."""
    design_path = resolve_design_oos_path(tmpdir)
    return tuple(
        str(p)
        for p in (
            tmpdir / "oos-accepted-review.md",
            tmpdir / "oos-accepted-main-agent.md",
            design_path,
        )
    )


# ---------------------------------------------------------------------------
# Detection result
# ---------------------------------------------------------------------------
class OosStatus(NamedTuple):
    non_security_count: int
    already_filed: bool
    carve_out: bool
    security_present: bool


def detect(
    tmpdir: Path,
    *,
    forked: bool = False,
    repo_unavailable: bool = False,
) -> OosStatus:
    """Return OOS detection status for the current run."""
    if forked or repo_unavailable:
        return OosStatus(
            non_security_count=0,
            already_filed=False,
            carve_out=True,
            security_present=False,
        )

    sentinel = tmpdir / "oos-issues-created.md"
    already_filed = bool(read_filed_urls_from_sentinel(str(sentinel)))

    security_oos = tmpdir / "security-oos-observations.md"
    security_present = security_oos.is_file() and security_oos.stat().st_size > 0

    paths = accepted_oos_paths(tmpdir)
    non_sec = count_non_security(paths)

    return OosStatus(
        non_security_count=non_sec,
        already_filed=already_filed,
        carve_out=False,
        security_present=security_present,
    )



# ---------------------------------------------------------------------------
# C4c OOS helper ports
# ---------------------------------------------------------------------------

_INTERNAL_URL_RE = re.compile(
    r"https?://(?:localhost|127\.0\.0\.1|10\.[0-9.]+|192\.168\.[0-9.]+|"
    r"172\.(?:1[6-9]|2[0-9]|3[0-1])\.[0-9.]+|169\.254\.[0-9.]+|"
    r"\[?(?:fc[0-9a-f]{2}:|fd[0-9a-f]{2}:|fe80:)|"
    r"[^\s/]+\.(?:internal|local|corp|lan|intranet|test|example|invalid))[^\s]*"
    r"|\b(?:localhost|127\.0\.0\.1|10\.[0-9.]+|192\.168\.[0-9.]+|"
    r"172\.(?:1[6-9]|2[0-9]|3[0-1])\.[0-9.]+|169\.254\.[0-9.]+|"
    r"[^\s/]+\.(?:internal|local|corp|lan|intranet))\b",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?1[ .-]?)?\(?[0-9]{3}\)?[ .-]?[0-9]{3}[ .-]?[0-9]{4}")
_SSN_RE = re.compile(r"[0-9]{3}-[0-9]{2}-[0-9]{4}")
_ACCOUNT_RE = re.compile(r"\b(?:account|user|customer|employee|tenant|org)[_-]?[A-Za-z0-9]{8,}\b", re.IGNORECASE)


_FILE_REF_RE = re.compile(
    r"(?P<path>(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?:\.[A-Za-z0-9_.-]+)?)"
    r"(?::(?P<start>\d+)(?:-(?P<end>\d+))?)?"
)


def _sanitize_public_text(text: str) -> str:
    text = redact(text)
    text = _INTERNAL_URL_RE.sub("<INTERNAL-URL>", text)
    text = _EMAIL_RE.sub("<REDACTED-PII>", text)
    text = _SSN_RE.sub("<REDACTED-PII>", text)
    text = _PHONE_RE.sub("<REDACTED-PII>", text)
    return _ACCOUNT_RE.sub("<REDACTED-PII>", text)


def normalize_title(text: object) -> str:
    cleaned = _sanitize_public_text(str(text or ""))
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


@dataclass(frozen=True)
class OosItem:
    number: int
    title: str
    body: str


def parse_oos_blocks(text: str) -> list[OosItem]:
    return [
        OosItem(int(block.item_id.removeprefix("OOS_")), block.title, block.block.rstrip())
        for block in parse_blocks(text, boundary="item-heading")
        if block.kind == "OOS"
    ]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="file_oos.py",
        description="Detect accepted non-security OOS blocks for post-ship filing.",
    )
    _ = p.add_argument("--tmpdir", required=True, help="IMPLEMENT_TMPDIR path")
    _ = p.add_argument("--forked", action="store_true", default=False)
    _ = p.add_argument("--repo-unavailable", action="store_true", default=False)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    raw_tmpdir = str(args.tmpdir)
    tmpdir = Path(raw_tmpdir)
    status = detect(tmpdir, forked=args.forked, repo_unavailable=args.repo_unavailable)
    result = {
        "non_security_count": status.non_security_count,
        "already_filed": status.already_filed,
        "carve_out": status.carve_out,
        "security_present": status.security_present,
    }
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
