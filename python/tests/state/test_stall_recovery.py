"""Tests for the remaining Python-owned stall-recovery lint command."""

import pytest

from larch.state import stall_recovery


def test_lint_subcommand_ok(capsys: pytest.CaptureFixture[str]) -> None:
    rc = stall_recovery.lint_main([])

    assert rc == 0
    assert "LINT_OK=true" in capsys.readouterr().out
