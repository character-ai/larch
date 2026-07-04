# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Tests for retro_fix_cursor.py."""

from __future__ import annotations

import json
from pathlib import Path

from larch.report import report_tokens_cost
from larch.report import retro_fix_cursor as rfc


def _write_summary(run_dir: Path, cursor: str, total: str, *, extra: str = "") -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    content = (
        f"## /implement run: merged\n\n"
        f"- **Cost**: 💰 TOTAL ~${total} — Claude $10.00, Codex $1.00, "
        f"Cursor ${cursor}, Claude (subprocess) $0.00  |  Tokens: 10000k\n"
        f"{extra}"
    )
    p = run_dir / "final-summary.md"
    p.write_text(content)
    return p


def _write_report(run_dir: Path, input_t: int, cache_read: int, output_t: int) -> None:
    data = {
        "BUCKETS_cursor": {"input": input_t, "cache_read": cache_read, "output": output_t},
    }
    (run_dir / "token-report-final.json").write_text(json.dumps(data))


def _live_cursor_cost(*, input_t: int, cache_read: int, output_t: int) -> str:
    """Cursor $ figure per the going-forward pricer, for cross-checking retro-fixer output.

    Passes ``env={}`` so ambient rate-override env vars cannot make this
    comparison flaky; the retro-fixer itself has no env-override path.
    """
    lines = report_tokens_cost.token_cost_from_args(
        [
            "--cursor-input-tokens", str(input_t),
            "--cursor-cache-read-tokens", str(cache_read),
            "--cursor-output-tokens", str(output_t),
        ],
        env={},
    )
    for line in lines.splitlines():
        key, _, value = line.partition("=")
        if key == "CURSOR_COST":
            return value
    raise AssertionError("CURSOR_COST missing from token_cost_from_args output")


def test_transform_fixes_cost_line(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN1"
    # cursor=$2.66 is the fully-unsurcharged (pre-#5854) figure for these buckets.
    input_t, cache_read, output_t = 1030521, 9188853, 122940
    p = _write_summary(run_dir, cursor="2.66", total="20.97")
    _write_report(run_dir, input_t=input_t, cache_read=cache_read, output_t=output_t)

    result = rfc.transform_file(p)
    assert result == "fixed"
    text = p.read_text()
    # Cross-check against the going-forward pricer rather than a self-pinned
    # literal, so the two paths cannot silently drift apart again.
    expected_cursor = _live_cursor_cost(input_t=input_t, cache_read=cache_read, output_t=output_t)
    assert f"Cursor ${expected_cursor}" in text
    assert f"TOTAL ~${20.97 - 2.66 + float(expected_cursor):.2f}" in text
    assert "Claude $10.00" in text  # unchanged


def test_transform_skips_zero_cursor(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN2"
    p = _write_summary(run_dir, cursor="0.00", total="10.00")
    _write_report(run_dir, input_t=0, cache_read=0, output_t=0)

    result = rfc.transform_file(p)
    assert result == "skipped-no-cursor"


def test_transform_skips_no_report(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN3"
    run_dir.mkdir(parents=True)
    p = _write_summary(run_dir, cursor="1.00", total="5.00")
    # no token-report written

    result = rfc.transform_file(p)
    assert result == "skipped-no-report"


def test_transform_skips_no_buckets(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN4"
    run_dir.mkdir(parents=True)
    p = _write_summary(run_dir, cursor="1.00", total="5.00")
    (run_dir / "token-report-final.json").write_text(json.dumps({"cursor": {"totals": {"total": 5000000}}}))

    result = rfc.transform_file(p)
    assert result == "skipped-no-buckets"


def test_transform_skips_zero_cache_read(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN5"
    p = _write_summary(run_dir, cursor="0.50", total="5.50")
    _write_report(run_dir, input_t=1_000_000, cache_read=0, output_t=0)

    result = rfc.transform_file(p)
    assert result == "skipped-no-cache-read"


def test_transform_skips_already_correct(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN6"
    # cache_read=1_000_000 at new rate $0.45/M + input=0 + output=0 = $0.45
    p = _write_summary(run_dir, cursor="0.45", total="10.45")
    _write_report(run_dir, input_t=0, cache_read=1_000_000, output_t=0)

    result = rfc.transform_file(p)
    assert result == "skipped-already-correct"


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "RUN7"
    p = _write_summary(run_dir, cursor="2.66", total="20.97")
    _write_report(run_dir, input_t=1030521, cache_read=9188853, output_t=122940)
    original = p.read_text()

    result = rfc.transform_file(p, dry_run=True)
    assert result == "fixed"
    assert p.read_text() == original


def test_main_sweeps_root(tmp_path: Path) -> None:
    for i, cursor in enumerate(("2.66", "0.00", "1.20")):
        run_dir = tmp_path / "larch-logs" / "implement" / f"RUN{i}"
        _write_summary(run_dir, cursor=cursor, total="20.00")
        _write_report(run_dir, input_t=0, cache_read=1_000_000 if cursor != "0.00" else 0, output_t=0)

    rc = rfc.main(["--root", str(tmp_path)])
    assert rc == 0


def test_main_run_id_targets_single_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "MYRUN"
    p = _write_summary(run_dir, cursor="2.00", total="12.00")
    _write_report(run_dir, input_t=0, cache_read=2_000_000, output_t=0)

    rc = rfc.main(["--root", str(tmp_path), "--run-id", "MYRUN"])
    assert rc == 0
    text = p.read_text()
    # new cursor = 2_000_000 * 0.45 / 1e6 = $0.90
    assert "Cursor $0.90" in text
    assert "TOTAL ~$10.90" in text


def test_fallback_to_token_report_json(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "design" / "RUN8"
    run_dir.mkdir(parents=True)
    input_t, cache_read, output_t = 1030521, 9188853, 122940
    p = _write_summary(run_dir, cursor="2.66", total="20.97")
    # Use token-report.json (not -final)
    data = {"BUCKETS_cursor": {"input": input_t, "cache_read": cache_read, "output": output_t}}
    (run_dir / "token-report.json").write_text(json.dumps(data))

    result = rfc.transform_file(p)
    assert result == "fixed"
    expected_cursor = _live_cursor_cost(input_t=input_t, cache_read=cache_read, output_t=output_t)
    assert f"Cursor ${expected_cursor}" in p.read_text()
