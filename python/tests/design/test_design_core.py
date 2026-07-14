"""Focused codec policy coverage for design core readers."""

from __future__ import annotations

from pathlib import Path

from larch.design import design_core
from larch.design import design_router


def test_env_readers_keep_last_non_empty_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "result.env"
    _ = path.write_text("SITE=first\nSITE=\nTRIGGER=one\nTRIGGER=\n", encoding="utf-8")

    assert design_core._read_env_value_last(path=path, key="SITE") == "first"  # pyright: ignore[reportPrivateUsage]
    assert design_core._read_env_values(  # pyright: ignore[reportPrivateUsage]
        path=path,
        defaults={"SITE": "", "TRIGGER": ""},
    ) == {"SITE": "first", "TRIGGER": "one"}


def test_router_stdout_codec_preserves_duplicate_order() -> None:
    assert design_router._parse_stdout_kv("STEP=old\nSTEP=latest\n") == {  # pyright: ignore[reportPrivateUsage]
        "STEP": ["old", "latest"]
    }
