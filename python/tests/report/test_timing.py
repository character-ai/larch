"""Tests for the bounded read-only Python timing compatibility surface."""

from __future__ import annotations

from pathlib import Path

import pytest

from larch.report import timing


def test_resolve_timing_ledger_path_prefers_session_roots_in_order(tmp_path: Path) -> None:
    implement = tmp_path / "implement"
    design = tmp_path / "design"
    implement.mkdir()
    design.mkdir()
    env = {
        "TMPDIR": str(tmp_path),
        "IMPLEMENT_TMPDIR": str(implement),
        "DESIGN_TMPDIR": str(design),
    }

    assert timing.resolve_timing_ledger_path(env=env) == implement / "timing-ledger.tsv"
    assert timing.resolve_timing_ledger_path(
        env={key: value for key, value in env.items() if key != "IMPLEMENT_TMPDIR"}
    ) == design / "timing-ledger.tsv"
    assert timing.resolve_timing_ledger_path(env={"TMPDIR": str(tmp_path)}) is None


def test_resolve_timing_ledger_path_rejects_symlink_and_never_creates_parent(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    link = allowed / "escape"
    link.symlink_to(outside)
    env = {"TMPDIR": str(allowed)}

    with pytest.raises(ValueError, match="not under an allowed root"):
        _ = timing.resolve_timing_ledger_path(
            ledger=str(link / "nested" / "timing-ledger.tsv"),
            env=env,
        )
    assert not (outside / "nested").exists()


def test_resolve_timing_ledger_path_ignores_unusable_declared_ledger(tmp_path: Path) -> None:
    implement = tmp_path / "implement"
    implement.mkdir()
    assert timing.resolve_timing_ledger_path(
        env={
            "TMPDIR": str(tmp_path),
            "IMPLEMENT_TMPDIR": str(implement),
            "LARCH_TIMING_LEDGER": "/etc/timing-ledger.tsv",
        }
    ) == implement / "timing-ledger.tsv"
