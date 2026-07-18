#!/usr/bin/env python3
"""Reference program used to prove the Rust parity harness contract."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: reference-command <mode> <root>", file=sys.stderr)
        return 2

    mode = sys.argv[1]
    root = Path(sys.argv[2])
    if mode == "malformed":
        print("malformed input", file=sys.stderr)
        return 65
    if mode == "environment":
        if "FIXTURE_REQUIRED" not in os.environ:
            print("required environment value is unavailable", file=sys.stderr)
            return 69
        return 0
    if mode == "isolation":
        print(f"GH_TOKEN={'present' if 'GH_TOKEN' in os.environ else 'absent'}")
        for key in (
            "GITHUB_API_URL",
            "CLOUDSDK_CONFIG",
            "PATH",
            "LARCH_PARITY_LIVE_SERVICES",
        ):
            print(f"{key}={os.environ[key]}")
        return 0
    if mode != "clean":
        print(f"unknown mode: {mode}", file=sys.stderr)
        return 64

    timestamp = os.environ["FIXTURE_TIMESTAMP"]
    seed = (root / "input" / "seed.txt").read_text(encoding="utf-8").strip()
    output = root / "output"
    output.mkdir()
    rendered = f"root={root}\ntimestamp={timestamp}\nseed={seed}\n"
    (output / "result.txt").write_text(rendered, encoding="utf-8")
    (output / "data.bin").write_bytes(bytes((0, 255)))
    (root / "effects.ndjson").write_text(
        f'{{"action":"write","root":"{root}","at":"{timestamp}"}}\n',
        encoding="utf-8",
    )
    print(f"wrote {root / 'output' / 'result.txt'} at {timestamp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
