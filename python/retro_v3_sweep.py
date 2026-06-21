# ruff: noqa: TC006,SIM102,PLR2004,PLW2901,PLC0415
"""retro_v3_sweep.py — transform committed session-transcript.jsonl files to v3 format.

Walks larch-logs/implement/*/session-transcript.jsonl and applies the v3
prose-errors-only filter in-place. Safe to re-run: files already at v3 are
skipped. Designed for the one-time retroactive sweep introduced with issue #3718.

Transform rules (applied to rendered v1/v2 JSONL):
  - Header: bump "v" to 3, add "policy": "prose-errors-only".
  - Blocks: drop type=tool_call; drop type=tool_result lacking "error"/"warning".
  - Turns with no remaining blocks are dropped; header "turns" count is updated.

Exit codes: 0 success (including nothing-to-do). Non-zero on hard I/O errors.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast


def _filter_blocks(blocks: list[object]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for blk in blocks:
        if not isinstance(blk, dict):
            continue
        block = cast(dict[str, object], blk)
        t = block.get("type")
        if t == "tool_call":
            continue
        if t == "tool_result":
            if not (block.get("error") or block.get("warning")):
                continue
        out.append(block)
    return out


def transform_file(path: Path, *, dry_run: bool = False) -> str:
    """Return 'skipped', 'transformed', or 'empty'."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return "empty"
    try:
        parsed_header: object = json.loads(lines[0])
    except json.JSONDecodeError:
        return "empty"
    if not isinstance(parsed_header, dict):
        return "empty"
    header = cast(dict[str, object], parsed_header)
    if header.get("v") == 3:
        return "skipped"

    header["v"] = 3
    header["policy"] = "prose-errors-only"

    new_turns: list[str] = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        try:
            parsed_rec: object = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed_rec, dict):
            continue
        rec = cast(dict[str, object], parsed_rec)
        blocks = rec.get("blocks")
        if not isinstance(blocks, list):
            new_turns.append(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))
            continue
        filtered = _filter_blocks(cast(list[object], blocks))
        if not filtered:
            continue
        rec["blocks"] = filtered
        new_turns.append(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))

    header["turns"] = len(new_turns)
    out_lines = [json.dumps(header, ensure_ascii=False, separators=(",", ":"))]
    out_lines.extend(new_turns)
    content = "\n".join(out_lines) + "\n"
    if not dry_run:
        _ = path.write_text(content, encoding="utf-8")
    return "transformed"


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    _ = p.add_argument("--root", default=".", help="Repo root (default: cwd)")
    _ = p.add_argument("--dry-run", action="store_true", help="Report without writing")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    root = Path(args.root)
    pattern = "larch-logs/implement/*/session-transcript.jsonl"
    files = sorted(root.glob(pattern))
    if not files:
        print(f"retro-v3-sweep: no files matched {pattern} under {root}", file=sys.stderr)
        return 0

    counts: dict[str, int] = {"transformed": 0, "skipped": 0, "empty": 0}
    for f in files:
        status = transform_file(f, dry_run=args.dry_run)
        counts[status] = counts.get(status, 0) + 1

    verb = "would transform" if args.dry_run else "transformed"
    print(
        f"retro-v3-sweep: {verb} {counts['transformed']}, "
        f"skipped {counts['skipped']} (already v3), "
        f"empty/unparseable {counts['empty']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
