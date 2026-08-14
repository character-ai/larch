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


def _capture() -> dict[str, str]:
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
        ledger = (root / findings_ledger.LEDGER_BASENAME).read_text(encoding="utf-8")
    assert "sk-" not in ledger
    return {"finding-blocks.golden.md": _FINDINGS, "findings-ledger.golden.tsv": ledger}


def _read_exact(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--update", action="store_true", help="replace checked-in live Python fixtures")
    args = parser.parse_args(argv)
    captures = _capture()
    failures: list[str] = []
    for name, text in captures.items():
        path = _FIXTURES / name
        if args.update:
            _ = path.write_text(text, encoding="utf-8", newline="")
        elif not path.is_file() or _read_exact(path) != text:
            failures.append(name)
    if failures:
        raise SystemExit(f"review golden drift: {', '.join(failures)}; rerun with --update after review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
