# ruff: noqa: C901,PLR0911,PLC0415
"""retro_fix_cursor.py — retro-fix Cursor pricing in committed final-summary.md files.

Recomputes the Cursor dollar figure and TOTAL in each ``**Cost**`` line by
applying the Teams $0.25/M cache-read surcharge that was omitted when these
run logs were first written.  Only files with ``BUCKETS_cursor`` and a
non-zero ``cache_read`` count can be precisely repriced; all others are
skipped and logged.

Designed as a one-time sweep to correct larch-logs committed before the
pricing fix in issue #5854.  Safe to re-run: files whose Cursor figure
already matches the corrected rate are reported as
``skipped-already-correct``.

Old (wrong) rate for composer-2.5 cache_read: $0.20/M
Corrected rate (+ Teams surcharge):            $0.45/M

Input and output rates are unchanged at $0.50/M and $2.50/M.

Exit codes: 0 on success (including nothing-to-do).  Non-zero on hard I/O
errors.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Rate correction: Teams $0.25/M surcharge on cache reads only.
# Old rate (wrong): $0.20/M.  Corrected rate: $0.45/M.
_NEW_CACHE_READ_RATE = 0.45
_INPUT_RATE = 0.50
_OUTPUT_RATE = 2.50

# Cursor cost line regex (matches both old and new Cost-line formats).
_RE_CURSOR = re.compile(r"Cursor \$(\d+\.\d+)")
_RE_TOTAL = re.compile(r"TOTAL ~\$(\d+\.\d+)")


def _cost_bucket(tokens: int, rate: float) -> float:
    if tokens <= 0:
        return 0.0
    return round((tokens / 1_000_000) * rate, 6)


def _cursor_cost(buckets: dict[str, int], cache_read_rate: float) -> float:
    return round(
        _cost_bucket(buckets.get("input", 0), _INPUT_RATE)
        + _cost_bucket(buckets.get("cache_read", 0), cache_read_rate)
        + _cost_bucket(buckets.get("output", 0), _OUTPUT_RATE),
        2,
    )


def _find_token_report(run_dir: Path) -> Path | None:
    """Prefer token-report-final.json, fall back to token-report.json."""
    for name in ("token-report-final.json", "token-report.json"):
        p = run_dir / name
        if p.exists():
            return p
    return None


def transform_file(final_summary_path: Path, *, dry_run: bool = False) -> str:
    """Return one of: 'fixed', 'skipped-no-cursor', 'skipped-no-report',
    'skipped-no-buckets', 'skipped-no-cache-read', 'skipped-already-correct',
    or 'skipped-format-mismatch'.
    """
    text = final_summary_path.read_text(encoding="utf-8")

    m_cursor = _RE_CURSOR.search(text)
    if not m_cursor or float(m_cursor.group(1)) == 0.0:
        return "skipped-no-cursor"

    run_dir = final_summary_path.parent
    report_path = _find_token_report(run_dir)
    if report_path is None:
        return "skipped-no-report"

    try:
        report: object = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "skipped-no-report"
    if not isinstance(report, dict):
        return "skipped-no-report"

    raw_buckets = report.get("BUCKETS_cursor")
    if not raw_buckets or not isinstance(raw_buckets, dict):
        return "skipped-no-buckets"

    cache_read = int(raw_buckets.get("cache_read", 0))
    if cache_read == 0:
        return "skipped-no-cache-read"

    buckets: dict[str, int] = {
        "input": int(raw_buckets.get("input", 0)),
        "cache_read": cache_read,
        "output": int(raw_buckets.get("output", 0)),
    }

    new_cursor = _cursor_cost(buckets, _NEW_CACHE_READ_RATE)
    stored_cursor = float(m_cursor.group(1))

    if new_cursor == stored_cursor:
        return "skipped-already-correct"

    m_total = _RE_TOTAL.search(text)
    if not m_total:
        return "skipped-format-mismatch"

    stored_total = float(m_total.group(1))
    new_total = round(stored_total - stored_cursor + new_cursor, 2)

    updated = _RE_CURSOR.sub(f"Cursor ${new_cursor:.2f}", text, count=1)
    updated = _RE_TOTAL.sub(f"TOTAL ~${new_total:.2f}", updated, count=1)

    if updated == text:
        return "skipped-format-mismatch"

    if not dry_run:
        final_summary_path.write_text(updated, encoding="utf-8")
    return "fixed"


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    _ = p.add_argument("--root", default=".", help="Repo root (default: cwd)")
    _ = p.add_argument("--dry-run", action="store_true", help="Report without writing")
    _ = p.add_argument("--run-id", help="Fix only this specific run ID")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    root = Path(args.root)

    if args.run_id:
        candidates = [
            root / "larch-logs" / "implement" / args.run_id / "final-summary.md",
            root / "larch-logs" / "design" / args.run_id / "final-summary.md",
        ]
        files = [f for f in candidates if f.exists()]
    else:
        files = sorted(root.glob("larch-logs/*/*/final-summary.md"))

    if not files:
        print("retro-fix-cursor: no final-summary.md files found", file=sys.stderr)
        return 0

    counts: dict[str, int] = {}
    for f in files:
        status = transform_file(f, dry_run=args.dry_run)
        counts[status] = counts.get(status, 0) + 1

    verb = "would fix" if args.dry_run else "fixed"
    fixed = counts.get("fixed", 0)
    skipped_no_cursor = counts.get("skipped-no-cursor", 0)
    skipped_no_report = counts.get("skipped-no-report", 0)
    skipped_no_buckets = counts.get("skipped-no-buckets", 0)
    skipped_no_cr = counts.get("skipped-no-cache-read", 0)
    skipped_already = counts.get("skipped-already-correct", 0)
    skipped_fmt = counts.get("skipped-format-mismatch", 0)

    print(
        f"retro-fix-cursor: {verb} {fixed}, "
        f"skipped-no-cursor {skipped_no_cursor}, "
        f"skipped-no-report {skipped_no_report}, "
        f"skipped-no-buckets {skipped_no_buckets}, "
        f"skipped-no-cache-read {skipped_no_cr}, "
        f"skipped-already-correct {skipped_already}, "
        f"skipped-format-mismatch {skipped_fmt}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
