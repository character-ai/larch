# python/render_session_transcript.py contract

`python3 python/cli.py run-log render-session-transcript` converts a raw Claude Code session JSONL into the committed filtered `session-transcript.jsonl` format.

## CLI

```bash
python3 python/cli.py run-log render-session-transcript --input <raw.jsonl> --output <session-transcript.jsonl>
```

Without `--output`, the rendered JSONL is written to stdout.

## Schema

Output uses schema v3 with policy `prose-errors-only`.

The first line is a header record with `v`, `source_basename`, `turns`, and `policy`. Subsequent lines are per-turn records with `turn`, `role`, and `blocks`.

Kept blocks are slash-command records, user or assistant text, adjacent assistant thinking for errored tool results, and errored or warned tool results. Tool-call blocks and non-error/non-warning tool results are omitted.

## Caller surface

`python/run_logs.py` calls this command in a subprocess and captures renderer stderr separately so transcript rendering failures remain non-fatal run-log warnings.

## Edit-in-sync

Update this contract and run-log docs with schema or CLI changes.
