from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from gantt import GanttRow, format_mss, render_gantt


def _lines() -> list[str]:
    chart = render_gantt(
        window_start_s=100,
        window_end_s=220,
        rows=[
            GanttRow("alpha/one", 100, 130),
            GanttRow("beta two, raw", 130, 180),
            GanttRow("long-label-with-punctuation:kept", 219, 240),
            GanttRow("outside", 1, 99),
        ],
        width=24,
    )
    return chart.splitlines()


def _border_cols(lines: list[str]) -> tuple[int, int]:
    top = next(line for line in lines if "┌" in line)
    return top.index("┌"), top.index("┐")


def _track(row_line: str) -> str:
    left = row_line.index("│")
    right = row_line.rindex("│")
    return row_line[left + 1 : right]


def test_edges_align() -> None:
    lines = _lines()
    left, right = _border_cols(lines)
    for line in lines:
        if "┌" in line:
            assert line.index("┌") == left
            assert line.index("┐") == right
        if "└" in line:
            assert line.index("└") == left
            assert line.index("┘") == right
        if "│" in line:
            assert line.index("│") == left
            assert line.rindex("│") == right


def test_axis_uses_relative_span_and_aligns_to_track() -> None:
    lines = _lines()
    left, right = _border_cols(lines)
    axis = lines[0]
    assert axis.index("0:00") == left + 1
    assert "2:00" in axis
    assert axis.index("2:00") + len("2:00") - 1 == right - 1
    assert "100" not in axis


def test_format_mss_is_not_table_style() -> None:
    assert format_mss(0) == "0:00"
    assert format_mss(1020) == "17:00"
    assert format_mss(-5) == "0:00"
    assert format_mss(300) == "5:00"
    assert format_mss(300) != "5m 00s"


def test_tracks_use_whole_blocks_only_and_contiguous_bars() -> None:
    for line in _lines():
        if "│" not in line:
            continue
        track = _track(line)
        assert set(track) <= {" ", "█"}
        assert not re.search(r"█+ +█+", track)
        assert not any(glyph in track for glyph in "▏▎▍▌▋▊▉")


def test_scaling_clamping_and_filtering() -> None:
    chart = render_gantt(
        window_start_s=1000,
        window_end_s=1100,
        rows=[
            GanttRow("offset", 1025, 1050),
            GanttRow("short", 1050, 1051),
            GanttRow("right", 1099, 1105),
            GanttRow("left", 990, 1005),
            GanttRow("outside", 1100, 1110),
        ],
        width=20,
    )
    assert "outside" not in chart
    rows = [line for line in chart.splitlines() if "│" in line]
    assert _track(rows[0]).startswith("     ")
    assert "█" in _track(rows[1])
    assert _track(rows[2]).endswith("█")
    assert _track(rows[3]).startswith("█")


def test_labels_are_not_truncated_or_sanitized() -> None:
    chart = "\n".join(_lines())
    assert "long-label-with-punctuation:kept" in chart
    assert "beta two, raw" in chart


def test_cli_matches_direct_render_and_reports_malformed_rows(tmp_path: Path) -> None:
    rows = tmp_path / "rows.tsv"
    _ = rows.write_text("a\t100\t120\n", encoding="utf-8")
    expected = render_gantt(window_start_s=100, window_end_s=140, rows=[GanttRow("a", 100, 120)], width=12) + "\n"
    cli = str(Path(__file__).with_name("cli.py"))
    result = subprocess.run(
        [
            sys.executable,
            cli,
            "gantt",
            "render",
            "--window-start-s",
            "100",
            "--window-end-s",
            "140",
            "--rows-tsv",
            str(rows),
            "--width",
            "12",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == expected
    bad = tmp_path / "bad.tsv"
    _ = bad.write_text("a\tbad\t120\n", encoding="utf-8")
    bad_result = subprocess.run(
        [
            sys.executable,
            cli,
            "gantt",
            "render",
            "--window-start-s",
            "100",
            "--window-end-s",
            "140",
            "--rows-tsv",
            str(bad),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert bad_result.returncode != 0
    assert "Traceback" not in bad_result.stderr


def test_cli_empty_stdout_when_all_rows_filtered_outside_window(tmp_path: Path) -> None:
    rows = tmp_path / "rows.tsv"
    _ = rows.write_text("a\t50\t90\nb\t200\t250\n", encoding="utf-8")
    cli = str(Path(__file__).with_name("cli.py"))
    result = subprocess.run(
        [
            sys.executable,
            cli,
            "gantt",
            "render",
            "--window-start-s",
            "100",
            "--window-end-s",
            "140",
            "--rows-tsv",
            str(rows),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == ""
