"""Characterize shared-codec behavior at migrated orchestration call sites."""
# These tests deliberately pin private migration seams.
# pyright: reportPrivateUsage=false

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

from larch.agents import _vendor
from larch.implement import (
    dispatch_commit_route,
    dispatch_manifest,
)

if TYPE_CHECKING:
    import pytest


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


def test_whitespace_kv_first_wins_and_skips_trailing_prose() -> None:
    line = "STATUS=fail FAILURE_REASON=x STATUS=ok trailing prose bad=1"
    assert dispatch_commit_route._parse_whitespace_kv_line(line) == {
        "STATUS": "fail",
        "FAILURE_REASON": "x",
    }


def test_relay_commit_kvs_filters_allowed_keys(capsys: pytest.CaptureFixture[str]) -> None:
    dispatch_commit_route._relay_commit_kvs(
        "NEXT_ACTION=stall\nCOMMIT_OUTCOME=failed\nIGNORED=1\nNEXT_ACTION=again\n"
    )
    assert capsys.readouterr().out == (
        "NEXT_ACTION=stall\nCOMMIT_OUTCOME=failed\nNEXT_ACTION=again\n"
    )


def test_prelaunch_index_reader_uses_first_value(tmp_path: Path) -> None:
    flag = tmp_path / "prelaunch.env"
    _ = flag.write_text(
        "PRELAUNCH_INDEX_NONEMPTY=true\nPRELAUNCH_INDEX_NONEMPTY=false\n",
        encoding="utf-8",
    )
    st = SimpleNamespace(prelaunch_index_flag=flag)
    assert dispatch_manifest._read_prelaunch_index_nonempty(st) == "true"  # type: ignore[arg-type]  # stub state for private reader
    missing = SimpleNamespace(prelaunch_index_flag=tmp_path / "absent.env")
    assert dispatch_manifest._read_prelaunch_index_nonempty(missing) == "false"  # type: ignore[arg-type]  # stub state for private reader
