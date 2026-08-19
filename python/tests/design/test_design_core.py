"""Focused codec policy coverage for design core readers."""

from __future__ import annotations

from pathlib import Path

import pytest

from larch.design import design_core


def test_env_readers_keep_last_non_empty_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "result.env"
    _ = path.write_text("SITE=first\nSITE=\nTRIGGER=one\nTRIGGER=\n", encoding="utf-8")

    assert design_core._read_env_value_last(path=path, key="SITE") == "first"  # pyright: ignore[reportPrivateUsage]
    assert design_core._read_env_values(  # pyright: ignore[reportPrivateUsage]
        path=path,
        defaults={"SITE": "", "TRIGGER": ""},
    ) == {"SITE": "first", "TRIGGER": "one"}


def test_router_stdout_codec_preserves_duplicate_order() -> None:
    assert design_core._parse_stdout_kv("STEP=old\nSTEP=latest\n") == {  # pyright: ignore[reportPrivateUsage]
        "STEP": ["old", "latest"]
    }


def test_router_stdout_codec_preserves_first_occurrence_order() -> None:
    result = design_core._parse_stdout_kv("B=1\nA=2\nB=3\nA=4\n")  # pyright: ignore[reportPrivateUsage]
    assert list(result.keys()) == ["B", "A"]
    assert result["B"] == ["1", "3"]
    assert result["A"] == ["2", "4"]


def test_router_stdout_codec_skips_lines_without_equals() -> None:
    assert design_core._parse_stdout_kv("NOEQUALS\nKEY=val\n\n") == {"KEY": ["val"]}  # pyright: ignore[reportPrivateUsage]


def test_router_stdout_codec_handles_embedded_equals() -> None:
    result = design_core._parse_stdout_kv("URL=https://example.com/?a=1\n")  # pyright: ignore[reportPrivateUsage]
    assert result["URL"] == ["https://example.com/?a=1"]


def test_relocated_decode_bash_percent_q_handles_utf8_byte_escapes() -> None:
    assert design_core._decode_bash_percent_q("$'\\360\\237\\230\\200'") == "😀"  # pyright: ignore[reportPrivateUsage]
    assert design_core._decode_bash_percent_q("$'caf\\303\\251'") == "café"  # pyright: ignore[reportPrivateUsage]
    assert design_core._decode_bash_percent_q("''") == ""  # pyright: ignore[reportPrivateUsage]


def test_relocated_parse_wrapper_args_binds_value_flags_and_public_argv() -> None:
    ns = design_core._parse_wrapper_args(  # pyright: ignore[reportPrivateUsage]
        ["--claude-pid", "123", "--plugin-root", "/plugin", "--", "--brainstorm", "hello"]
    )
    assert ns.claude_pid == "123"
    assert ns.plugin_root == "/plugin"
    assert ns.public_argv == ["--brainstorm", "hello"]


def test_relocated_require_plugin_root_rejects_template_literal() -> None:
    with pytest.raises(SystemExit) as exc:
        design_core.require_plugin_root("${CLAUDE_PLUGIN_ROOT}")
    assert exc.value.code == 1
