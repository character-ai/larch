# run-step-checks.sh

Captured relevant-checks wrapper retained for legacy/helper-only call sites. Active Step 3, Step 5 self-review, Step 5 MAV, and Step 6 paths use Python composites. The wrapper rehydrates telemetry keys before invoking python/cli.py checks run-relevant.

## Caller

`skills/implement/SKILL.md` no longer invokes this wrapper for active Step 3. Keep it available for offline harnesses and any legacy helper-only paths until all callers are removed.

## KV grammar

The wrapper relays the underlying helper stdout unchanged unless this file names explicit keys. Explicit keys are newline-delimited `KEY=value` records and must be token-scannable by the orchestrator.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Telemetry consumers read `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` from `$IMPLEMENT_TMPDIR/session-env.sh` internally instead of relying on inline SKILL.md triplets.

## Edit-in-sync

Update `skills/implement/SKILL.md` and the implement structure/timing harnesses when this contract or argv changes.
