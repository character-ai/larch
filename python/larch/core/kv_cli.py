"""CLI helpers for extracting values from ``KEY=value`` streams."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from larch.io import kv_value, read_kv

_MATCH_CHOICES = ("first", "last")
_CR_STRIP_CHOICES = ("none", "suffix", "rstrip", "strip")


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py kv get",
        description="Extract one value from KEY=value input.",
    )
    _ = parser.add_argument("--key", required=True)
    _ = parser.add_argument("--file", type=Path)
    _ = parser.add_argument("--match", choices=_MATCH_CHOICES, default="first")
    _ = parser.add_argument("--default", default="")
    _ = parser.add_argument("--cr-strip", choices=_CR_STRIP_CHOICES, default="none")
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def get_main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args is None:
        return 2

    first_match = args.match == "first"
    if args.file is None:
        value = kv_value(
            text=sys.stdin.read(),
            key=args.key,
            default=args.default,
            first_match=first_match,
            cr_strip=args.cr_strip,
        )
    else:
        value = read_kv(
            path=args.file,
            key=args.key,
            default=args.default,
            first_match=first_match,
            cr_strip=args.cr_strip,
        )
    print(value)
    return 0
