"""Shared best-effort review phase detail rendering for final reports."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import os
from pathlib import Path

import progress_report
from larch.core import redact

RENDER_PHASE_DETAIL_TIMEOUT_SECONDS = 15


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
    return _invoke_renderer(
        rounds_root,
        skill="implement",
        timing_ledger=timing_ledger if timing_ledger.is_file() else None,
        token_ledger=token_ledger,
        findings_file=findings_file if findings_file.is_file() else None,
    )


def append_review_phase_detail(*, body: str, detail: str) -> str:
    if not detail:
        return body
    return body.rstrip("\n") + "\n\n" + detail.strip("\n") + "\n"
