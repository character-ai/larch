"""Characterize shared-codec behavior at a migrated orchestration call site."""
# These tests deliberately pin private migration seams.
# pyright: reportPrivateUsage=false

from __future__ import annotations

from larch.agents import _vendor


def test_vendor_cap_status_uses_first_whitespace_token() -> None:
    result = _vendor.check_token_budget_cap(
        cap="10",
        step="step",
        runner=lambda _argv: type("R", (), {"stdout": "OTHER=1 STATUS=cap_hit STATUS=under_cap\n"})(),
    )
    assert result.hit is True

    miss = _vendor.check_token_budget_cap(
        cap="10",
        step="step",
        runner=lambda _argv: type("R", (), {"stdout": "STATUS=under_cap TOTAL=1\n"})(),
    )
    assert miss.hit is False
