# read-claude-model.sh contract

## Purpose

Read the active Claude model from the resolved Claude transcript and emit a single `CLAUDE_MODEL=<value>` line for run metadata.

The helper is best-effort by design: missing `jq`, unavailable transcript source, unreadable JSONL, malformed records, or a missing assistant model all produce `CLAUDE_MODEL=unknown`.

## Interface

```
read-claude-model.sh
```

No flags are accepted. The helper delegates transcript resolution to `python3 python/cli.py token claude-source`, including that helper's `LARCH_CLAUDE_SOURCE_FILE`, `LARCH_CLAUDE_SESSION_ID`, `LARCH_TOKEN_SESSION_ID`, and newest-transcript fallback behavior.

## Output contract

```
CLAUDE_MODEL=<value>
```

The helper always exits 0. Callers must treat the value as display metadata only.

## Invariants

- Do not fail callers because Claude-model metadata is unavailable.
- Emit exactly one stdout line so shell callers can parse it without `eval`.
- Read only the first assistant JSONL record with a non-empty `.message.model` field.

## Known limitations

`python3 python/cli.py token claude-source` falls back to the newest transcript in the repo's Claude project directory when no durable session snapshot is available. On machines with concurrent sessions in the same checkout, that mtime fallback can select a different session's transcript.

`read-claude-model.sh` is retained for diagnostic use; committed run manifests do not depend on transcript fallback metadata.

## Edit-in-sync pointers

| File | Relationship |
|---|---|
| `python3 python/cli.py run-log` | Runtime log writer; manifests may carry model metadata. |
| `python3 python/cli.py token claude-source` | Transcript resolver used by this helper. |
| `python/test_run_logs.py` | Regression harness for runtime log writes. |
| `docs/run-logs.md` | Human-readable log contract. |

## Test harness

Covered by `python/test_run_logs.py`, which is wired into `make py-test`.
