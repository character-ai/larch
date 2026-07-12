"""Finding dedup, cross-round applied-finding ledger, and rejected-findings emit."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from larch.review.plan_review_common import _require_tmpdir, _write_atomic
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


def _read_all_applied_finding_keys(tmpdir: Path) -> set[str]:
    """Every finding key in the applied-finding ledger, across all rounds."""
    path = tmpdir / ".step3-applied-finding-keys.tsv"
    if not path.is_file() or path.is_symlink():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "\t" not in line:
            continue
        round_field, key = line.split("\t", 1)
        if key and re.fullmatch(r"[0-9]+", round_field):
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


def _filter_rejected_findings_body(*, text: str, applied: set[str], marker_re: str) -> tuple[str, bool]:
    """Filter ``text`` blocks starting with ``marker_re``, dropping suppressed keys.

    A block is dropped when its finding key is in ``applied`` (applied in a prior
    round, or flagged already-addressed) or when the block itself carries the
    ``[ALREADY_ADDRESSED]`` tag. Returns ``(filtered_body, had_blocks)`` where
    ``had_blocks`` is true when at least one block header matched ``marker_re``.
    """
    matches = list(re.finditer(marker_re, text))
    if not matches:
        return "", False
    kept: list[str] = []
    prefix = text[: matches[0].start()]
    if prefix:
        kept.append(prefix)
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[match.start():end]
        items = parse_blocks(block, boundary="item-heading")
        finding = next((item for item in items if item.kind == "FINDING"), None)
        candidate = block[: finding.end] if finding is not None else block
        key = _finding_dedup_key(candidate)
        if (key and key in applied) or _ALREADY_ADDRESSED_RE.search(block):
            kept.append(block[len(candidate) :])
            continue
        kept.append(block)
    return "".join(kept), True


def _filter_rejected_findings_body_canonical(*, text: str, applied: set[str]) -> tuple[str, bool]:
    """Filter canonical FINDING blocks from ``text``, dropping suppressed keys."""
    parsed = parse_blocks(text, boundary="item-heading")
    finding_blocks = [b for b in parsed if b.kind == "FINDING"]
    if not finding_blocks:
        return "", False
    kept: list[str] = []
    preamble = text[: finding_blocks[0].start]
    if preamble:
        kept.append(preamble)
    for parsed_block in finding_blocks:
        block = parsed_block.block
        key = _finding_dedup_key(block)
        if (key and key in applied) or _ALREADY_ADDRESSED_RE.search(block):
            continue
        kept.append(block)
    return "".join(kept), True


REJECTED_FINDINGS_REPORT_HEADING = "## Considered Plan Review Suggestions (Not Adopted)"
REJECTED_FINDINGS_REPORT_ANNOTATION = (
    "These reviewer suggestions were considered but not adopted. Some may already "
    "be addressed by the current plan; they are not automatically unimplemented gaps."
)


def _format_rejected_findings_report(body: str, *, report_framing: bool) -> str:
    if not report_framing or not body:
        return body
    return (
        f"{REJECTED_FINDINGS_REPORT_HEADING}\n\n"
        f"{REJECTED_FINDINGS_REPORT_ANNOTATION}\n\n"
        f"{body}"
    )


def emit_rejected_findings(argv: Sequence[str]) -> int:
    """Emit the Step 4 rejected-findings body with already-applied findings removed."""
    parser = argparse.ArgumentParser(prog="cli.py plan-review emit-rejected")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--report-framing", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    path = tmpdir / "rejected-findings.md"
    if path.is_symlink() or not path.is_file():
        return 0
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return 0
    applied = _read_all_applied_finding_keys(tmpdir) | _read_already_addressed_finding_keys(tmpdir)
    if not applied and not _ALREADY_ADDRESSED_RE.search(text):
        print(_format_rejected_findings_report(body=text, report_framing=ns.report_framing), end="")
        return 0
    filtered, had_blocks = _filter_rejected_findings_body(
        text=text, applied=applied, marker_re=r"(?m)^### \[Plan Review\] "
    )
    if had_blocks:
        print(_format_rejected_findings_report(body=filtered, report_framing=ns.report_framing), end="")
        return 0
    filtered, had_blocks = _filter_rejected_findings_body_canonical(text=text, applied=applied)
    if had_blocks:
        print(_format_rejected_findings_report(body=filtered, report_framing=ns.report_framing), end="")
        return 0
    print(
        "WARN=emit-rejected: applied-finding ledger present but rejected-findings.md "
        "has no recognizable blocks; emitting empty body",
        file=sys.stderr,
    )
    print(end="")
    return 0


# pyright: reportPrivateUsage=false, reportUnusedFunction=false
