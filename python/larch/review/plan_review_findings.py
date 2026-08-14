"""Finding dedup, cross-round applied-finding ledger, and rejected-findings emit."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from larch.review.plan_review_common import _write_atomic
from larch.review.review_types import finding_dedup_key, parse_blocks


_finding_dedup_key = finding_dedup_key


def _read_applied_finding_keys(tmpdir: Path, *, before_round: int) -> set[str]:
    """Finding keys recorded in rounds strictly before ``before_round``."""
    path = tmpdir / ".step3-applied-finding-keys.tsv"
    if not path.is_file() or path.is_symlink():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "\t" not in line:
            continue
        round_field, key = line.split("\t", 1)
        if key and re.fullmatch(r"[0-9]+", round_field) and int(round_field, 10) < before_round:
            keys.add(key)
    return keys


def _record_applied_finding_keys(*, tmpdir: Path, round_num: int, keys: Sequence[str]) -> None:
    """Record this round's accepted finding keys in the applied-finding ledger,
    idempotently (rows for ``round_num`` are rewritten, not duplicated).
    """
    path = tmpdir / ".step3-applied-finding-keys.tsv"
    rows: list[str] = []
    if path.is_file() and not path.is_symlink():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "\t" not in line:
                continue
            round_field = line.split("\t", 1)[0]
            if re.fullmatch(r"[0-9]+", round_field) and int(round_field, 10) != round_num:
                rows.append(line)
    seen: set[str] = set()
    for key in keys:
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(f"{round_num}\t{key}")
    _write_atomic(path=path, content="".join(f"{row}\n" for row in rows))


# A finding tagged ``[ALREADY_ADDRESSED]`` by a reviewer is one the current plan
# already satisfies (issue #4920). Such findings are suppressed from the Step 4
# not-adopted report, and their concern key is laddered across rounds so the same
# already-satisfied concern does not recur once any round flags it.
_ALREADY_ADDRESSED_RE = re.compile(r"\[ALREADY_ADDRESSED\]", re.IGNORECASE)
_ALREADY_ADDRESSED_LEDGER = ".step3-already-addressed-finding-keys.tsv"


def _read_already_addressed_finding_keys(tmpdir: Path) -> set[str]:
    """Cumulative concern keys flagged ``[ALREADY_ADDRESSED]`` in any round."""
    path = tmpdir / _ALREADY_ADDRESSED_LEDGER
    if not path.is_file() or path.is_symlink():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key = line.strip()
        if key:
            keys.add(key)
    return keys


def _record_already_addressed_finding_keys(*, tmpdir: Path, keys: Sequence[str]) -> None:
    """Merge ``keys`` into the already-addressed ledger, idempotently and sorted."""
    existing = _read_already_addressed_finding_keys(tmpdir)
    merged = existing | {key for key in keys if key}
    if merged == existing:
        return
    _write_atomic(
        path=tmpdir / _ALREADY_ADDRESSED_LEDGER,
        content="".join(f"{key}\n" for key in sorted(merged)),
    )


def _keys_from_blocks(blocks: list[str]) -> list[str]:
    keys: list[str] = []
    for block in blocks:
        if _ALREADY_ADDRESSED_RE.search(block):
            key = _finding_dedup_key(_ALREADY_ADDRESSED_RE.sub("", block))
            if key:
                keys.append(key)
    return keys


def _plan_review_finding_blocks(text: str) -> list[str]:
    """Return each Plan Review wrapper through its immediate FINDING block."""
    matches = list(re.finditer(r"(?m)^### \[Plan Review\] ", text))
    blocks: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        segment = text[match.start():end]
        items = parse_blocks(segment, boundary="item-heading")
        finding = next((item for item in items if item.kind == "FINDING"), None)
        if finding is not None:
            blocks.append(segment[: finding.end])
    return blocks


def _already_addressed_keys_in_rejected(tmpdir: Path) -> list[str]:
    """Concern keys of rejected blocks tagged ``[ALREADY_ADDRESSED]`` this round."""
    path = tmpdir / "rejected-findings.md"
    if not path.is_file() or path.is_symlink():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    # Try distinct Plan-Review heading grammar first.
    blocks = _plan_review_finding_blocks(text)
    if blocks:
        return _keys_from_blocks(blocks)
    # Fall back to canonical FINDING blocks via shared parser.
    finding_blocks = [pb.block for pb in parse_blocks(text, boundary="item-heading") if pb.kind == "FINDING"]
    if finding_blocks:
        return _keys_from_blocks(finding_blocks)
    return []


REJECTED_FINDINGS_REPORT_HEADING = "## Considered Plan Review Suggestions (Not Adopted)"
REJECTED_FINDINGS_REPORT_ANNOTATION = (
    "These reviewer suggestions were considered but not adopted. Some may already "
    "be addressed by the current plan; they are not automatically unimplemented gaps."
)
# pyright: reportPrivateUsage=false, reportUnusedFunction=false
