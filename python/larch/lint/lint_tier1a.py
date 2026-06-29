"""Check Tier-1a Claude root imports against line-count caps."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Final

TIER1A_LINE_CAPS: Final[dict[str, int]] = {
    "AGENTS.md": 89,
    "KARPATHY_CLAUDE.md": 54,
    "BASH_AUTHORING.md": 97,
}


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint tier1a-size", description=__doc__)
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def _validate_caps(caps: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    if not caps:
        errors.append("tier1a-size: malformed cap configuration: no caps configured")
        return errors
    for relpath, cap in caps.items():
        path = Path(relpath)
        if not relpath or path.is_absolute() or ".." in path.parts:
            errors.append(f"tier1a-size: malformed cap path: {relpath!r}")
        if not isinstance(cap, int) or isinstance(cap, bool) or cap < 0:
            errors.append(f"tier1a-size: malformed cap for {relpath}: {cap!r}")
    return errors


def check_root(root: Path, caps: Mapping[str, int] | None = None) -> tuple[int, list[str]]:
    """Return ``(exit_code, stderr_rows)`` for the Tier-1a size check."""
    caps = TIER1A_LINE_CAPS if caps is None else caps
    errors = _validate_caps(caps)
    if errors:
        return 2, errors
    if not root.is_dir():
        return 2, [f"tier1a-size: --root is not a directory: {root}"]

    internal_rows: list[str] = []
    over_cap_rows: list[str] = []
    for relpath, cap in caps.items():
        path = root / relpath
        if not path.exists():
            internal_rows.append(f"{relpath}: missing")
            continue
        if not path.is_file():
            internal_rows.append(f"{relpath}: not a file")
            continue
        try:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError) as exc:
            internal_rows.append(f"{relpath}: unreadable: {exc}")
            continue
        if line_count > cap:
            over_cap_rows.append(f"{relpath}: {line_count} lines exceeds cap {cap}")
    if internal_rows:
        return 2, [*internal_rows, *over_cap_rows]
    return (1 if over_cap_rows else 0), over_cap_rows


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args is None:
        return 2
    code, rows = check_root(Path(args.root).resolve())
    for row in rows:
        print(row, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
