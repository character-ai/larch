"""Panel and voter dispatch entry points for /design plan review.

Topology anchor: round gated static plus dynamic.
"""

from __future__ import annotations

from collections.abc import Sequence

from plan_review import (
    DESIGN_PANEL_DISPATCH,
    ROOT_VOTER_DISPATCH,
    run_legacy_script,
)


def dispatch_panel(argv: Sequence[str]) -> int:
    return run_legacy_script(DESIGN_PANEL_DISPATCH, argv)


def dispatch_voters(argv: Sequence[str]) -> int:
    return run_legacy_script(ROOT_VOTER_DISPATCH, argv)


def dispatch_panel_main(argv: list[str] | None = None) -> int:
    return dispatch_panel(argv or [])


def dispatch_voters_main(argv: list[str] | None = None) -> int:
    return dispatch_voters(argv or [])
