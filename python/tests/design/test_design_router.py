"""Tests for /design router KV parsing helpers."""

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


def test_parse_stdout_kv_collects_repeated_keys_in_order() -> None:
    result = design_router._parse_stdout_kv("WARN=first\nWARN=second\nROUTE=ok\n")  # pyright: ignore[reportPrivateUsage]
    assert result["WARN"] == ["first", "second"]
    assert result["ROUTE"] == ["ok"]


def test_parse_stdout_kv_preserves_first_occurrence_order() -> None:
    result = design_router._parse_stdout_kv("B=1\nA=2\nB=3\nA=4\n")  # pyright: ignore[reportPrivateUsage]
    assert list(result.keys()) == ["B", "A"]
    assert result["B"] == ["1", "3"]
    assert result["A"] == ["2", "4"]


def test_parse_stdout_kv_skips_lines_without_equals() -> None:
    result = design_router._parse_stdout_kv("NOEQUALS\nKEY=val\n\n")  # pyright: ignore[reportPrivateUsage]
    assert result == {"KEY": ["val"]}


def test_parse_stdout_kv_handles_embedded_equals() -> None:
    result = design_router._parse_stdout_kv("URL=https://example.com/?a=1\n")  # pyright: ignore[reportPrivateUsage]
    assert result["URL"] == ["https://example.com/?a=1"]
