from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING

from larch.core import kv_cli

if TYPE_CHECKING:
    import pytest


def run_get(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    *,
    stdin: str = "",
) -> tuple[int, str, str]:
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    rc = kv_cli.get_main(argv)
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def test_stdin_first_match(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    rc, out, err = run_get(["--key", "KEY"], capsys, monkeypatch, stdin="KEY=one\nKEY=two\n")

    assert rc == 0
    assert out == "one\n"
    assert err == ""


def test_stdin_last_match(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    rc, out, err = run_get(
        ["--key", "KEY", "--match", "last"],
        capsys,
        monkeypatch,
        stdin="KEY=one\nKEY=two\n",
    )

    assert rc == 0
    assert out == "two\n"
    assert err == ""


def test_file_input(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "values.env"
    _ = source.write_text("OTHER=x\nKEY=file-value\n", encoding="utf-8")

    rc, out, err = run_get(["--key", "KEY", "--file", str(source)], capsys, monkeypatch)

    assert rc == 0
    assert out == "file-value\n"
    assert err == ""


def test_values_may_contain_equals(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    rc, out, err = run_get(["--key", "KEY"], capsys, monkeypatch, stdin="KEY=a=b=c\n")

    assert rc == 0
    assert out == "a=b=c\n"
    assert err == ""


def test_missing_key_emits_default(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    rc, out, err = run_get(
        ["--key", "MISSING", "--default", "fallback"],
        capsys,
        monkeypatch,
        stdin="KEY=value\n",
    )

    assert rc == 0
    assert out == "fallback\n"
    assert err == ""


def test_invalid_match_exits_2(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    rc, out, err = run_get(["--key", "KEY", "--match", "middle"], capsys, monkeypatch)

    assert rc == 2
    assert out == ""
    assert "invalid choice" in err


def test_file_last_match_forwards_duplicate_policy(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "values.env"
    _ = source.write_text("KEY=one\nKEY=two\n", encoding="utf-8")

    rc, out, err = run_get(
        ["--key", "KEY", "--file", str(source), "--match", "last"],
        capsys,
        monkeypatch,
    )

    assert rc == 0
    assert out == "two\n"
    assert err == ""


def test_stdin_last_non_empty_forwards_policy(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc, out, _ = run_get(
        ["--key", "KEY", "--match", "last-non-empty"],
        capsys,
        monkeypatch,
        stdin="KEY=one\nKEY=\n",
    )

    assert rc == 0
    assert out == "one\n"


def test_file_duplicate_first_vs_last(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "values.env"
    _ = source.write_text("KEY=first\nKEY=second\n", encoding="utf-8")

    rc_first, out_first, _ = run_get(["--key", "KEY", "--file", str(source)], capsys, monkeypatch)
    assert rc_first == 0
    assert out_first == "first\n"

    rc_last, out_last, _ = run_get(
        ["--key", "KEY", "--file", str(source), "--match", "last"], capsys, monkeypatch
    )
    assert rc_last == 0
    assert out_last == "second\n"


def test_cr_strip_strips_crlf_line_endings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "values.env"
    _ = source.write_text("KEY=value\r\n", encoding="utf-8")

    rc, out, _ = run_get(
        ["--key", "KEY", "--file", str(source), "--cr-strip", "strip"], capsys, monkeypatch
    )
    assert rc == 0
    assert out == "value\n"


def test_stdin_byte_compatible_embedded_equals(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    rc, out, err = run_get(
        ["--key", "URL", "--match", "first"], capsys, monkeypatch, stdin="URL=https://example.com/?a=1&b=2\n"
    )
    assert rc == 0
    assert out == "https://example.com/?a=1&b=2\n"
    assert err == ""
