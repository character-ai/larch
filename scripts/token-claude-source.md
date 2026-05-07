# token-claude-source.sh

**Purpose**: Resolve the most recently modified Claude transcript for the current git repository. `/implement` token reporting uses it to find the main transcript and the sibling session directory that may contain subagent transcripts.

## Relationship to scripts/token-tally.md

`scripts/token-tally.sh` does not inspect Claude transcript files; `/research` writes explicit lane sidecars. `token-claude-source.sh` is part of the separate `/implement` PoC that passively tails Claude transcript JSONL files.

## Output

On success, stdout is key/value lines:

```
TRANSCRIPT_PATH=<path>
SESSION_DIR=<path-without-.jsonl>
SESSION_UUID=<uuid>
```

`SESSION_DIR` is the sibling directory matching the transcript basename. Subagent files live under `$SESSION_DIR/subagents/agent-*.jsonl` when present.

## Failure Contract

Resolver failures print:

```
STATUS=unavailable
REASON=<message>
```

Then exit 1. This is intentionally different from `token-report.sh`, which prints `Token report unavailable: <reason>` to stdout and exits 0, and from `token-ledger.sh`, which warns on stderr and exits 0.

## Test Harness

`scripts/test-token-claude-source.sh` is the dedicated offline harness covering the `LARCH_CLAUDE_SOURCE_FILE` snapshot replay short-circuit, snapshot fall-through paths, the live mtime / `LARCH_CLAUDE_SESSION_ID` resolver, and concurrent-session attribution (snapshot pinning beats newer transcripts in the project dir).

`scripts/test-token-report.sh` additionally exercises the resolver indirectly through reporter failure-mode cases and uses `--transcript` for deterministic fixtures.
