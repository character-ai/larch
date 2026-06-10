# step-8-ship.sh

Step 8+ ship-driver selector. Derives CLONE_TAG_FULL, enforces the Python 3.11 JSON fallback, and invokes either python/cli.py ship pr or scripts/ship-pr.sh with the canonical argv.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from the named `/implement` step so the prompt-side Bash fence remains a plugin-root source guard plus one script call.

## KV grammar

The wrapper relays the underlying helper stdout unchanged unless this file names explicit keys. Explicit keys are newline-delimited `KEY=value` records and must be token-scannable by the orchestrator.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Telemetry consumers read `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` from `$IMPLEMENT_TMPDIR/session-env.sh` internally instead of relying on inline SKILL.md triplets.

## Edit-in-sync

Update `skills/implement/SKILL.md` and the implement structure/timing harnesses when this contract or argv changes.
