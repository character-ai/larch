#!/usr/bin/env python3
"""Analyze voter agreement, severity calibration, and chronic outliers from larch logs."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
import os

plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"]) if os.environ.get("CLAUDE_PLUGIN_ROOT") else Path(__file__).resolve().parents[3]
python_path = str(plugin_root / "python")
if python_path not in sys.path:
    sys.path.insert(0, python_path)

from voting import (  # noqa: E402
    classification_tsv_schema_supported,
    compute_voter_agreement,
    compute_voter_severity_distribution,
    render_voter_severity_scoreboard,
    voter_agreement_rows_from_tsv,
)


def _git_toplevel() -> Path | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return Path(value) if value else None


def _default_log_root() -> Path:
    top = _git_toplevel()
    if top is not None:
        return top / "larch-logs"
    return Path.cwd() / "larch-logs"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _discover(log_root: Path) -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []
    for path in sorted(log_root.glob("design/*/plan-review/round-*/findings-classification.tsv")):
        paths.append(("design", path))
    for path in sorted(log_root.glob("implement/*/round-*/findings-classification.tsv")):
        paths.append(("code-review", path))
    for path in sorted(log_root.glob("review/*/review-findings-classification-round-*.tsv")):
        paths.append(("code-review", path))
    return paths


def _rate(value: object) -> str:
    return "n/a" if value is None else f"{float(value):.3f}"


def _table(records: list[dict[str, object]]) -> str:
    lines = [
        "| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    if not records:
        lines.append("| n/a | n/a | 0 | 0 | 0 | 0 | n/a | false |")
        return "\n".join(lines)
    for record in records:
        lines.append(
            f"| {record['panel']} | {record['voter']} | {record['eligible']} | "
            f"{record['agree']} | {record['disagree']} | {record['missing']} | "
            f"{_rate(record['agreement_rate'])} | {str(bool(record['outlier'])).lower()} |"
        )
    return "\n".join(lines)


def _global_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        copied = dict(row)
        copied["panel"] = "global"
        out.append(copied)
    return out


def _render(
    *,
    log_root: Path,
    files_seen: int,
    skipped_files: int,
    malformed_rows: int,
    ineligible_rows: int,
    rows: list[dict[str, object]],
    min_votes: int,
    outlier_threshold: float,
    high_severity_threshold: float,
) -> str:
    records = compute_voter_agreement(rows, min_votes=min_votes, outlier_threshold=outlier_threshold)
    global_records = compute_voter_agreement(_global_rows(rows), min_votes=min_votes, outlier_threshold=outlier_threshold)
    severity_records = compute_voter_severity_distribution(rows, high_severity_threshold=high_severity_threshold)
    global_severity_records = compute_voter_severity_distribution(
        _global_rows(rows),
        high_severity_threshold=high_severity_threshold,
    )
    outliers = [record for record in records + global_records if bool(record["outlier"])]
    missing = sorted(records, key=lambda r: int(r["missing"]), reverse=True)

    lines = [
        "# Voter Calibration Report",
        "",
        "## Corpus",
        "",
        f"- Log root: `{log_root}`",
        f"- Classification TSV files scanned: {files_seen}",
        f"- Malformed or unsupported TSV files skipped: {skipped_files}",
        f"- Malformed data rows dropped: {malformed_rows}",
        f"- Ineligible panels excluded: {ineligible_rows}",
        f"- Qualifying accepted/rejected panels: {len(rows)}",
        "",
        "## Agreement Table",
        "",
        _table(records),
        "",
        render_voter_severity_scoreboard(severity_records),
        "",
        "## Global Voter Agreement",
        "",
        _table(global_records),
        "",
        render_voter_severity_scoreboard(global_severity_records),
        "",
        f"## Chronic Outliers (threshold < {outlier_threshold:.2f}, min votes {min_votes})",
        "",
        _table(outliers),
        "",
        "## Missing Vote Table",
        "",
        _table(missing),
        "",
        "## Notes",
        "",
        "- Neutral panel verdicts are excluded from agreement denominators.",
        "- Single-voter and zero-voter panels are excluded because agreement is undefined.",
        "- Empty, missing, and `JUDGE_ERROR` voter cells count as missing, not disagreement.",
        "- `agreement_rate` uses `agree / (agree + disagree)`; missing votes are excluded.",
        "- Severity calibration counts only YES votes with valid severity buckets; missing and invalid severities are reported separately.",
        "- The severity scoreboard emits a voter-side Calibration Score from the High Rate threshold excess.",
        "- This report is diagnostic only. Agreement and severity calibration do not affect reviewer/proposer points, spawning, thresholds, tokens, or live panel verdicts.",
    ]
    return "\n".join(lines) + "\n"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="voter-calibration")
    parser.add_argument("--log-root", default="")
    parser.add_argument("--min-votes", type=int, default=20)
    parser.add_argument("--outlier-threshold", type=float, default=0.50)
    parser.add_argument("--high-severity-threshold", type=float, default=0.90)
    parser.add_argument("--out", default="")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    log_root = Path(args.log_root).expanduser() if args.log_root else _default_log_root()
    log_root = log_root.resolve()
    if not log_root.is_dir():
        print(f"voter-calibration: resolved log root is missing: {log_root}", file=sys.stderr)
        return 2

    rows: list[dict[str, object]] = []
    skipped_files = 0
    malformed_rows = 0
    ineligible_rows = 0
    discovered = _discover(log_root)
    for panel, path in discovered:
        text = _read_text(path)
        parsed = voter_agreement_rows_from_tsv(text, panel_kind=panel)
        first_line = text.splitlines()[0] if text.splitlines() else ""
        if not parsed.rows and (
            "voting_result" not in first_line
            or not classification_tsv_schema_supported(text, panel_kind=panel)
        ):
            skipped_files += 1
        malformed_rows += parsed.malformed_rows
        ineligible_rows += parsed.ineligible_rows
        rows.extend(parsed.rows)

    report = _render(
        log_root=log_root,
        files_seen=len(discovered),
        skipped_files=skipped_files,
        malformed_rows=malformed_rows,
        ineligible_rows=ineligible_rows,
        rows=rows,
        min_votes=args.min_votes,
        outlier_threshold=args.outlier_threshold,
        high_severity_threshold=args.high_severity_threshold,
    )
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"REPORT_FILE={out}")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
