"""Characterize shared-codec behavior at migrated /design call sites."""
# These tests deliberately pin private migration seams.
# pyright: reportPrivateUsage=false

from __future__ import annotations

from pathlib import Path

from larch.design import design_core


def test_step0_env_readers_keep_allowlist_duplicate_and_empty_value_policy(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "cache.env"
    _ = cache.write_text("# ignored\r\nKEEP=old\r\nKEEP=\r\nDROP=value\n", newline="")

    assert design_core.load_bash_quoted_env(  # pyright: ignore[reportPrivateUsage] - characterize migration seam
        path=cache, allow_keys={"KEEP"}
    ) == {"KEEP": ""}

    source = tmp_path / "source.env"
    _ = source.write_text(" export KEEP=old\r\nexport KEEP=new\nKEEP=\n", newline="")
    assert design_core._load_source_env(  # pyright: ignore[reportPrivateUsage] - characterize migration seam
        path=source, allow_keys={"KEEP"}
    ) == {"KEEP": ""}
