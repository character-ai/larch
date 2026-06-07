"""Post-ship OOS detection and idempotency support.

Responsibilities:
1. Detect accepted, non-security OOS blocks across upstream inputs.
2. Enforce idempotency via the oos-issues-created.md sentinel.
3. Classify carve-outs (forked, repo_unavailable, security).

The actual GitHub issue creation and semantic dedup remain with the /issue
pipeline (LLM) invoked by the orchestrator.  This module prepares the
to-file set and exposes the sentinel-based idempotency check so the
orchestrator can avoid re-filing across same-session retries.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

import config


# ---------------------------------------------------------------------------
# Constants (moved from config to keep OOS-specific tunables here)
# ---------------------------------------------------------------------------
INLINE_TRIAGE_MARKER: str = config.INLINE_TRIAGE_MARKER
OOS_FILED_URL_FIELD: str = config.OOS_FILED_URL_FIELD

# ---------------------------------------------------------------------------
# Regexes (ported from oos.py)
# ---------------------------------------------------------------------------
_OOS_HEADER_RE = re.compile(
    r"^###\s+(?:OOS_|FINDING_\d+:.*\[(?:OUT_OF_SCOPE|OOS)\])",
    re.MULTILINE,
)
_SECURITY_FOCUS_RE = re.compile(
    r"^[ \t-]*focus-area[ \t]*[:=][ \t]*"
    r"security([-a-zA-Z0-9 _]*)(\s|$|\(|#|\.|,)",
    re.IGNORECASE | re.MULTILINE,
)
_SECURITY_HEADER_RE = re.compile(
    r"^###\s+(?:OOS_\d+:|FINDING_\d+:)\s*"
    r"(?:\[(?:OUT_OF_SCOPE|OOS)\]\s*)?"
    r"`?(?:\[security\]|<security>)`?(?:\s|$|[:-])",
    re.IGNORECASE,
)


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
    """Count non-security accepted OOS blocks in markdown text.

    Blocks start on canonical ``### OOS_`` headers and on legacy tagged
    ``### FINDING_N: [OUT_OF_SCOPE]`` headers (tag required — bare
    ``### FINDING_N:`` stays in-scope; #3550).
    """
    count = 0
    in_block = False
    security = False
    for line in text.splitlines():
        if _OOS_HEADER_RE.match(line):
            if in_block and not security:
                count += 1
            in_block = True
            security = bool(_SECURITY_HEADER_RE.match(line))
            continue
        normalized = line.replace("`", "").replace("*", "")
        if in_block and _SECURITY_FOCUS_RE.match(normalized):
            security = True
    if in_block and not security:
        count += 1
    return count


def count_non_security(accepted_paths: tuple[str, ...]) -> int:
    """Count non-security accepted OOS blocks across markdown files."""
    total = 0
    for path in accepted_paths:
        file_path = Path(path)
        if not file_path.is_file():
            continue
        text = file_path.read_text(encoding="utf-8")
        if _OOS_HEADER_RE.search(text):
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
    tmpdir = Path(args.tmpdir)
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
