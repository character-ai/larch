#!/usr/bin/env python3
"""Emit a bounded UTF-8-safe excerpt for oos-issue-cap.sh."""

from __future__ import annotations

import re
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: oos-issue-cap-excerpt.py BODY_FILE MAX_CHARS", file=sys.stderr)
        return 1

    path = sys.argv[1]
    max_chars = int(sys.argv[2])
    with open(path, "r", encoding="utf-8", errors="replace") as body_file:
        text = body_file.read()

    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "…"
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
