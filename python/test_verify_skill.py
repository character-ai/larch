"""Tests for verify_skill.py."""

from __future__ import annotations

from pathlib import Path

import verify_skill


def test_sentinel_file_passes(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    marker = tmp_path / "marker"
    marker.write_text("ok", encoding="utf-8")
    assert verify_skill.main(["--sentinel-file", str(marker)]) == 0
    out = capsys.readouterr().out
    assert "VERIFIED=true" in out
    assert "REASON=ok" in out


def test_stdout_line_no_match(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    output = tmp_path / "stdout.txt"
    output.write_text("alpha\n", encoding="utf-8")
    assert verify_skill.main(["--stdout-line", "beta", "--stdout-file", str(output)]) == 0
    out = capsys.readouterr().out
    assert "VERIFIED=false" in out
    assert "REASON=no_match" in out
