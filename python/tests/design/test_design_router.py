"""Focused codec policy coverage for design router readers."""

from __future__ import annotations

from larch import io as larch_io
from larch.design import design_router


def test_router_stdout_codec_preserves_ordered_duplicates() -> None:
    parsed = design_router._parse_stdout_kv(  # pyright: ignore[reportPrivateUsage]
        "WARN=first\nSTEP=old\nWARN=second\nSTEP=latest\n"
    )
    assert parsed == {"WARN": ["first", "second"], "STEP": ["old", "latest"]}


def test_router_rename_stdout_uses_last_match() -> None:
    text = "RENAMED=false\nRENAMED=true\nOTHER=x\n"
    assert larch_io.kv_value(text=text, key="RENAMED", duplicate_policy="last") == "true"
