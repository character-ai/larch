# python/retro_v3_sweep.py contract

`python3 python/cli.py run-log retro-v3-sweep` transforms historical Git-corpus transcripts to schema v3.

## CLI

```bash
python3 python/cli.py run-log retro-v3-sweep --root . --dry-run
python3 python/cli.py run-log retro-v3-sweep --root .
```

The command scans `larch-logs/implement/*/session-transcript.jsonl` under `--root`.

## Invariants

- Existing v3 transcripts are skipped.
- Earlier rendered transcripts are rewritten with `policy: prose-errors-only`.
- Tool-call blocks and non-error/non-warning tool results are removed.
- Turns with no remaining blocks are dropped and the header turn count is updated.

## Edit-in-sync

Update this contract with schema or sweep behavior changes.
