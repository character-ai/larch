"""Review finding aggregation CLI entry point."""

from __future__ import annotations

from review_pipeline import run_legacy


def aggregate_findings(argv: list[str]) -> int:
    return run_legacy("aggregate-findings.sh", argv)


def aggregate_findings_main(argv: list[str]) -> int:
    return aggregate_findings(argv)
