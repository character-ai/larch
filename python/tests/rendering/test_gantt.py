from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from larch.rendering.gantt import DEFAULT_WIDTH, GanttRow, format_mss, render_gantt


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


def test_minimal_overlapping_row_renders_visible_relative_chart() -> None:
    chart = render_gantt(
        window_start_s=100,
        window_end_s=200,
        rows=[GanttRow("codex/reviewer", 120, 150)],
        width=20,
    )

    assert chart.strip()
    assert "codex/reviewer" in chart
    assert "█" in chart
    assert "│ 30s" in chart
    assert "0:00" in chart
    assert "1:40" in chart
    assert "100" not in chart
    assert all(line.strip() for line in chart.splitlines())


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


def test_label_width_uses_all_rows_not_just_filtered() -> None:
    # An out-of-window row with a longer label than any in-window row must still
    # anchor the left column so the border and all data-row │ glyphs line up.
    long_label = "this-label-is-longer-than-any-visible-row"
    chart = render_gantt(
        window_start_s=100,
        window_end_s=200,
        rows=[
            GanttRow("short", 100, 150),
            GanttRow(long_label, 1, 99),  # outside window, not rendered
        ],
        width=20,
    )
    lines = chart.splitlines()
    left, _ = _border_cols(lines)
    assert left == len(long_label) + 1
    for line in lines:
        if "│" in line:
            assert line.index("│") == left


def test_labels_are_not_truncated_or_sanitized() -> None:
    chart = "\n".join(_lines())
    assert "long-label-with-punctuation:kept" in chart
    assert "beta two, raw" in chart


def test_default_width_caps_long_reviewer_label_without_truncating() -> None:
    label = "codex/dyn-dyn-skill-contract-codex"
    chart = render_gantt(
        window_start_s=0,
        window_end_s=245,
        rows=[GanttRow(label, 0, 69)],
    )
    lines = chart.splitlines()
    assert all(len(line) <= 90 for line in lines)
    assert label in chart
    row_line = next(line for line in lines if line.startswith(label))
    assert len(_track(row_line)) < DEFAULT_WIDTH


def test_explicit_large_width_is_preserved() -> None:
    chart = render_gantt(
        window_start_s=0,
        window_end_s=100,
        rows=[GanttRow("a", 0, 20)],
        width=80,
    )
    row_line = next(line for line in chart.splitlines() if line.startswith("a"))
    assert len(_track(row_line)) == 80


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


def test_cli_omitted_width_uses_default_path(tmp_path: Path) -> None:
    label = "codex/dyn-dyn-skill-contract-codex"
    rows = tmp_path / "rows.tsv"
    _ = rows.write_text(f"{label}\t0\t69\n", encoding="utf-8")
    cli = str(Path(__file__).with_name("cli.py"))
    result = subprocess.run(
        [
            sys.executable,
            cli,
            "gantt",
            "render",
            "--window-start-s",
            "0",
            "--window-end-s",
            "245",
            "--rows-tsv",
            str(rows),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert label in result.stdout
    assert all(len(line) <= 90 for line in result.stdout.splitlines())


def test_cli_explicit_width_forms_are_preserved(tmp_path: Path) -> None:
    rows = tmp_path / "rows.tsv"
    _ = rows.write_text("a\t0\t20\n", encoding="utf-8")
    cli = str(Path(__file__).with_name("cli.py"))
    width_forms = [("--width", "80"), ("--width=80",)]
    for width_form in width_forms:
        result = subprocess.run(
            [
                sys.executable,
                cli,
                "gantt",
                "render",
                "--window-start-s",
                "0",
                "--window-end-s",
                "100",
                "--rows-tsv",
                str(rows),
                *width_form,
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0
        row_line = next(line for line in result.stdout.splitlines() if line.startswith("a"))
        assert len(_track(row_line)) == 80


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
