"""Helpers for Gate C accepted plan-review finding audits."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from larch import io as larch_io
from larch.state.session_env import validate_design_tmpdir

PRE_REVIEW_PLAN = "plan-before-review.txt"
ACCEPTED_AUDIT = "accepted-plan-findings-audit.md"
ONE_BY_ONE_SKIP_MARKER = "rejected by user during one-by-one review"

_FINDING_BLOCK_RE = re.compile(r"(?ms)^### FINDING_[0-9A-Za-z_]+:.*?(?=^### |\Z)")


class AcceptedAuditError(ValueError):
    """Raised when accepted-audit helper inputs are invalid."""


def _parse_design_tmpdir(value: str) -> Path:
    ok, message = validate_design_tmpdir(value)
    if not ok:
        raise AcceptedAuditError(message)
    design_tmpdir = Path(value).resolve()
    if not design_tmpdir.is_dir():
        raise AcceptedAuditError("design-tmpdir: path must name a directory")
    return design_tmpdir


def _is_under(child: Path, parent: Path) -> bool:
    try:
        _ = child.relative_to(parent)
    except ValueError:
        return False
    return True


def _resolve_existing_file_under_design(*, path: Path, design_tmpdir: Path, label: str) -> Path:
    if path.is_symlink():
        raise AcceptedAuditError(f"{label}: refusing symlink file")
    if not path.is_file():
        raise AcceptedAuditError(f"{label}: file is required")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise AcceptedAuditError(f"{label}: file resolution failed") from exc
    if not _is_under(resolved, design_tmpdir):
        raise AcceptedAuditError(f"{label}: path must stay under design-tmpdir")
    return resolved


def _resolve_optional_file_under_design(*, path: Path, design_tmpdir: Path, label: str) -> Path:
    if path.is_symlink():
        raise AcceptedAuditError(f"{label}: refusing symlink file")
    if path.exists():
        return _resolve_existing_file_under_design(path=path, design_tmpdir=design_tmpdir, label=label)
    try:
        resolved_parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise AcceptedAuditError(f"{label}: parent resolution failed") from exc
    resolved = resolved_parent / path.name
    if not _is_under(resolved, design_tmpdir):
        raise AcceptedAuditError(f"{label}: path must stay under design-tmpdir")
    return resolved


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _normalize_finding_block(block: str) -> str:
    return "\n".join(line.rstrip() for line in block.strip().splitlines() if ONE_BY_ONE_SKIP_MARKER not in line).strip()


def filter_gate_b_skipped_text(*, accepted_text: str, rejected_text: str) -> str:
    """Return accepted findings with one-by-one user-skipped blocks removed."""
    skipped: set[str] = {
        _normalize_finding_block(block)
        for block in _FINDING_BLOCK_RE.findall(rejected_text)
        if ONE_BY_ONE_SKIP_MARKER in block
    }
    kept: list[str] = []
    for block in _FINDING_BLOCK_RE.findall(accepted_text):
        normalized = _normalize_finding_block(block)
        if normalized not in skipped:
            kept.append(block.strip())
    return "\n\n".join(kept) + ("\n\n" if kept else "")


def filter_gate_b_skipped_files(*, accepted: Path, rejected: Path) -> str:
    """Read and filter accepted findings using a rejected-findings marker file."""
    rejected_text = _read_file(rejected) if rejected.is_file() else ""
    if ONE_BY_ONE_SKIP_MARKER not in rejected_text:
        return _read_file(accepted)
    return filter_gate_b_skipped_text(accepted_text=_read_file(accepted), rejected_text=rejected_text)


def snapshot_pre_review_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Snapshot plan.txt before a /design Step 3 review entry")
    _ = parser.add_argument("--design-tmpdir", required=True)
    args = parser.parse_args(argv)
    try:
        design_tmpdir = _parse_design_tmpdir(args.design_tmpdir)
        plan_path = _resolve_existing_file_under_design(
            path=design_tmpdir / "plan.txt",
            design_tmpdir=design_tmpdir,
            label="plan.txt",
        )
        larch_io.atomic_write(
            design_tmpdir / PRE_REVIEW_PLAN,
            _read_file(plan_path),
            prefix="plan-before-review.",
            nofollow=True,
        )
    except AcceptedAuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: snapshot-pre-review failed: {exc}", file=sys.stderr)
        return 1
    return 0


def filter_gate_b_skipped_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Filter Gate B one-by-one skipped findings from accepted findings")
    _ = parser.add_argument("--design-tmpdir", required=True)
    _ = parser.add_argument("--accepted", required=True)
    _ = parser.add_argument("--rejected", required=True)
    args = parser.parse_args(argv)
    try:
        design_tmpdir = _parse_design_tmpdir(args.design_tmpdir)
        accepted = _resolve_existing_file_under_design(
            path=Path(args.accepted),
            design_tmpdir=design_tmpdir,
            label="accepted",
        )
        rejected = _resolve_optional_file_under_design(
            path=Path(args.rejected),
            design_tmpdir=design_tmpdir,
            label="rejected",
        )
        _ = sys.stdout.write(filter_gate_b_skipped_files(accepted=accepted, rejected=rejected))
    except AcceptedAuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: filter-gate-b-skipped failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _normalize_assessment_file(path: Path) -> str:
    text = _read_file(path).strip()
    if not text:
        raise AcceptedAuditError("assessment-file: content is required")
    return f"{text}\n"


def persist_accepted_audit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Persist the Gate C accepted-findings audit")
    _ = parser.add_argument("--design-tmpdir", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    _ = group.add_argument("--assessment", choices=("clean",))
    _ = group.add_argument("--assessment-file")
    args = parser.parse_args(argv)
    try:
        design_tmpdir = _parse_design_tmpdir(args.design_tmpdir)
        if args.assessment == "clean":
            text = "Accepted plan-review audit: no concerns.\n"
        else:
            assessment_file = _resolve_existing_file_under_design(
                path=Path(args.assessment_file),
                design_tmpdir=design_tmpdir,
                label="assessment-file",
            )
            text = _normalize_assessment_file(assessment_file)
        larch_io.atomic_write(
            design_tmpdir / ACCEPTED_AUDIT,
            text,
            prefix="accepted-plan-findings-audit.",
            nofollow=True,
        )
    except AcceptedAuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: persist-accepted-audit failed: {exc}", file=sys.stderr)
        return 1
    print("ACCEPTED_AUDIT_STATUS=ok")
    return 0
