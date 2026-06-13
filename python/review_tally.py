"""Review vote tally, tally emission, and log-phase CLI entry points."""

from __future__ import annotations

from review_pipeline import run_legacy


def tally_code_votes(argv: list[str]) -> int:
    return run_legacy("tally-code-votes.sh", argv)


def emit_tally(argv: list[str]) -> int:
    return run_legacy("emit-tally.sh", argv)


def log_phase(argv: list[str]) -> int:
    return run_legacy("log-phase.sh", argv)


def tally_code_votes_main(argv: list[str]) -> int:
    return tally_code_votes(argv)


def emit_tally_main(argv: list[str]) -> int:
    return emit_tally(argv)


def log_phase_main(argv: list[str]) -> int:
    return log_phase(argv)
