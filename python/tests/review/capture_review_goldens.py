"""Developer-only capture/check helper for the dormant Rust review fixtures.

Run without ``--update`` to compare live Python model and ledger output with the
checked-in fixtures.  Updating requires an explicit flag so CI cannot refresh a
wire contract implicitly.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "python"))

from larch.review import findings_ledger  # noqa: E402 - developer helper bootstraps the checkout Python path
from larch.review.review_types import parse_blocks  # noqa: E402 - developer helper bootstraps the checkout Python path

_FIXTURES = _ROOT / "fixtures" / "rust-review"
_FINDINGS = (
    "préamble 😀\r\n"
    "### FINDING_0001: Unicode offsets\r\n"
    "- **Location**: src/lib.rs:12\r\n"
    "- **Concern**: spacing\r\n"
    "```md\r\n"
    "### FINDING_9: quoted\r\n"
    "```\r\n"
    "### OOS_2: [OOS] later\r\n"
    "- focus-area: correctness\r\n"
    "### FINDING_184467440737095516160: Large ordinal\r\n"
    "body\r\n"
)

_CODE_TABLE_HEADER = "## Per-finding vote breakdown\n\n| Item | YES | NO | JERR | Result |\n|---|---:|---:|---:|---|\n"
_PLAN_TABLE_HEADER = "## Findings\n\n| Item | YES | NO | JERR | Result |\n|---|---:|---:|---:|---|\n"


def _vote_table_row(item_id: str, yes: int, no: int, judge_error: int, result: str) -> str:
    return f"| {item_id} | {yes} | {no} | {judge_error} | {result} |\n"


def _capture() -> dict[str, bytes]:
    blocks = parse_blocks(_FINDINGS)
    assert blocks[0].start == len("préamble 😀\r\n")
    assert blocks[-1].item_id.endswith("184467440737095516160")
    with tempfile.TemporaryDirectory() as raw_tmp:
        root = Path(raw_tmp)
        secret = "sk-" + "a" * 26
        findings_ledger.write_round(
            root,
            1,
            [{"finding_id": "FINDING_1", "title": "Safe title", "file_line": "src/lib.rs:12", "outcome": "accepted", "vote_tally": "YES=2/3", "reason": secret}],
        )
        findings_ledger.write_round(
            root,
            2,
            [{"finding_id": "OOS_1", "title": "Later", "outcome": "neutral", "vote_tally": "YES=1/2", "reason": "Needs evidence"}],
        )
        ledger = (root / findings_ledger.LEDGER_BASENAME).read_bytes()
    assert b"sk-" not in ledger
    code_table = _CODE_TABLE_HEADER + "".join(
        _vote_table_row(item_id=item_id, yes=yes, no=no, judge_error=0, result=result)
        for item_id, yes, no, result in (
            ("FINDING_1", 3, 0, "accepted"),
            ("FINDING_2", 1, 2, "neutral"),
            ("FINDING_3", 0, 3, "rejected"),
        )
    )
    plan_table = _PLAN_TABLE_HEADER + "".join(
        _vote_table_row(item_id=item_id, yes=yes, no=no, judge_error=0, result=result)
        for item_id, yes, no, result in (
            ("OOS_1", 3, 0, "accepted"),
            ("OOS_2", 1, 2, "neutral"),
            ("OOS_3", 0, 3, "rejected"),
        )
    )
    return {
        "finding-blocks.golden.md": _FINDINGS.encode("utf-8"),
        "findings-ledger.golden.tsv": ledger,
        "code-vote-table.golden.md": code_table.encode("utf-8"),
        "plan-vote-table.golden.md": plan_table.encode("utf-8"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--update", action="store_true", help="replace checked-in live Python fixtures")
    args = parser.parse_args(argv)
    captures = _capture()
    failures: list[str] = []
    for name, data in captures.items():
        path = _FIXTURES / name
        if args.update:
            _ = path.write_bytes(data)
        elif not path.is_file() or path.read_bytes() != data:
            failures.append(name)
    if failures:
        raise SystemExit(f"review golden drift: {', '.join(failures)}; rerun with --update after review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
