"""Compose review finding JSONL records."""

from __future__ import annotations

from review_pipeline import run_legacy


def compose_findings(argv: list[str]) -> int:
    return run_legacy("compose-review-findings.sh", argv)


def compose_findings_main(argv: list[str]) -> int:
    return compose_findings(argv)
