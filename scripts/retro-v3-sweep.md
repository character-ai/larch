# retro-v3-sweep.py contract

## Purpose

One-time retroactive sweep script that transforms committed
`larch-logs/implement/*/session-transcript.jsonl` files from v1/v2 format to
v3 prose-errors-only format in-place. Introduced alongside issue #3718 (Phase 4
of the logs-size-reduction series). Safe to re-run: files already at v3 are
skipped without modification.

## Interface

```text
retro-v3-sweep.py [--root <dir>] [--dry-run]
```

`--root` defaults to the current directory. `--dry-run` reports what would be
transformed without writing any files.

## Transform rules

Applied to each file's rendered JSONL:

1. Header: set `"v": 3`, add `"policy": "prose-errors-only"`, update `"turns"` count.
2. Blocks: drop `type=tool_call`; drop `type=tool_result` blocks lacking an
   `"error"` or `"warning"` key.
3. Turns with no blocks remaining after filtering are dropped.

Files already at `v3` (header `"v" == 3`) are skipped.

## Callers

Invoked manually once after the renderer is upgraded to v3 policy. Not wired
into any hook or CI pipeline.

## Edit-in-sync

If the v3 block-filtering logic changes, update this script and
`scripts/render-session-transcript.py` together.
