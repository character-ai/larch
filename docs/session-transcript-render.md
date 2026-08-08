# `run-log render-session-transcript` contract

`scripts/larch.sh run-log render-session-transcript` converts a raw Claude Code session JSONL into the committed filtered `session-transcript.jsonl` format. The Rust owner is `larch_core::report::session_transcript`; issue #8091 retired the Python implementation.

## CLI

```bash
scripts/larch.sh run-log render-session-transcript --input <raw.jsonl> --output <session-transcript.jsonl>
```

Without `--output`, the rendered JSONL is written to stdout.

Exit codes: `0` on success, `2` for a missing or unreadable input, `3` for an input that held no parseable record, `4` for an input past the size bound, and `1` for a failed write.

## Schema

Output uses schema v3 with policy `prose-errors-and-reference-reads`.

The first line is a header record with `v`, `source_basename`, `turns`, and `policy`. Subsequent lines are per-turn records with `turn`, `role`, and `blocks`.

Kept blocks are slash-command records, user or assistant text, adjacent assistant thinking for errored tool results, errored or warned tool results, and sanitized reference `Read` stubs carrying only a normalized repository-relative `file_path`. Other tool-call blocks and non-error, non-warning tool results are omitted.

## Untrusted content

Transcript content is untrusted. Every rendered string is escaped so no code point in the content can end a document line. That includes `U+0085`, `U+2028`, and `U+2029`, which JSON leaves bare but Python's `str.splitlines` treats as record breaks. A reader may therefore rely on one JSON object per line and on the header's `turns` count.

## Bounds

An input larger than 512 MiB is refused rather than rendered in part. A single JSONL record larger than 8 MiB is skipped and counted. Records whose bytes are not valid UTF-8 are decoded with replacement and counted. Both counts are reported on stderr, and the transcript capture in `run-log checkpoint` and `run-log refresh` records them as a `render-bounded` execution-issue warning.

## Caller surface

`run-log capture-transcript`, `run-log checkpoint`, and `run-log refresh` render in process through the same core owner and stage the result as the `session-transcript` batch artifact.

## Edit-in-sync

Update this contract and `docs/run-logs.md` with schema or CLI changes.
