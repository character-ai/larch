#!/usr/bin/env python3
"""Frozen retired-bgjob wire oracle used only by Rust black-box parity tests.

This is deliberately a fixture, not a runtime command owner. It captures the
unchanged no-launch behavior and completed-result envelope that the Rust
`bgjob` commands must continue to expose after the Python implementation was
retired.
"""

from __future__ import annotations

from pathlib import Path
import sys


def _value(arguments: list[str], name: str) -> str:
    index = arguments.index(name)
    return arguments[index + 1]


def _wait(arguments: list[str]) -> int:
    step = _value(arguments, "--step")
    tmpdir = Path(_value(arguments, "--tmpdir"))
    rows = (tmpdir / "bgjob" / f"{step}.result.env").read_text(encoding="utf-8")
    sys.stdout.write("BGJOB_STATUS=DONE\n")
    sys.stdout.write(rows)
    return 0


def main(arguments: list[str]) -> int:
    if not arguments:
        raise ValueError("missing fixture verb")
    verb = arguments[0]
    if verb in {"start", "adapt"}:
        sys.stdout.write("BGJOB_ERROR=missing-command\n")
        return 2
    if verb == "wait":
        return _wait(arguments[1:])
    if verb == "status":
        return 0
    if verb == "reap":
        sys.stdout.write("BGJOB_REAPED=0\n")
        return 0
    raise ValueError(f"unknown fixture verb: {verb}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
