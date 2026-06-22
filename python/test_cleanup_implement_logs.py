# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Tests for cleanup_implement_logs.py — the --run-dir containment guard."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import cleanup_implement_logs as cil

if TYPE_CHECKING:
    import pytest


def _make_impl_root(tmp_path: Path) -> Path:
    impl_root = tmp_path / "larch-logs" / "implement"
    impl_root.mkdir(parents=True)
    return impl_root


def test_resolve_single_run_dir_accepts_child(tmp_path: Path) -> None:
    impl_root = _make_impl_root(tmp_path)
    run_dir = impl_root / "0199-RUN-UUID"
    run_dir.mkdir()
    resolved = cil._resolve_single_run_dir(str(run_dir), impl_root)  # pyright: ignore[reportPrivateUsage]
    assert resolved == run_dir.resolve()


def test_resolve_single_run_dir_accepts_impl_root_itself(tmp_path: Path) -> None:
    impl_root = _make_impl_root(tmp_path)
    resolved = cil._resolve_single_run_dir(str(impl_root), impl_root)  # pyright: ignore[reportPrivateUsage]
    assert resolved == impl_root.resolve()


def test_resolve_single_run_dir_rejects_sibling_outside(tmp_path: Path) -> None:
    impl_root = _make_impl_root(tmp_path)
    outside = tmp_path / "not-implement"
    outside.mkdir()
    assert cil._resolve_single_run_dir(str(outside), impl_root) is None  # pyright: ignore[reportPrivateUsage]


def test_resolve_single_run_dir_rejects_parent_traversal(tmp_path: Path) -> None:
    impl_root = _make_impl_root(tmp_path)
    sneaky = str(impl_root / ".." / ".." / "etc")
    assert cil._resolve_single_run_dir(sneaky, impl_root) is None  # pyright: ignore[reportPrivateUsage]


def test_resolve_single_run_dir_rejects_symlink_escape(tmp_path: Path) -> None:
    impl_root = _make_impl_root(tmp_path)
    outside = tmp_path / "outside-target"
    outside.mkdir()
    link = impl_root / "escape-link"
    link.symlink_to(outside, target_is_directory=True)
    # The symlink lives inside impl_root but resolves outside it.
    assert cil._resolve_single_run_dir(str(link), impl_root) is None  # pyright: ignore[reportPrivateUsage]


def test_main_rejects_run_dir_outside_impl_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A dyn-*-prompt.md outside the real larch-logs/implement/ tree would be
    # deleted by the unguarded rglob. The guard must refuse and leave it intact.
    victim = tmp_path / "round-1" / "dyn-evil-prompt.md"
    victim.parent.mkdir(parents=True)
    victim.write_text("do not delete me\n", encoding="utf-8")

    rc = cil.main(["--run-dir", str(tmp_path), "--execute"])

    assert rc == 1
    assert victim.exists(), "guard must block deletion outside larch-logs/implement/"
    assert "--run-dir must resolve to a path inside" in capsys.readouterr().err
