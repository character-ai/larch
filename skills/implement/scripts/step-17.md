# step-17.sh

Step 17 final-report wrapper. It marks telemetry, runs `python/cli.py final-report write`, and appends Tool Failures on failure.

## Caller

`skills/implement/SKILL.md` reaches this wrapper through `step-16-17.sh` on the active Step 16-17 path. Direct callers and harnesses may still invoke `step-17.sh` without flags.

## Modes

Default mode preserves the direct-call contract: it runs `final-report write --print-stdout`, mirrors renderer stdout, appends Tool Failures on non-zero rc, and touches `$IMPLEMENT_TMPDIR/.step17-printed` after a successful non-empty `summary-final.md` render.

`--no-print-stdout` suppresses renderer stdout. Wrapper mode delegates marker printing and `.step17-printed` ownership to `step-16-17.sh`.

## Handoff exit semantics

`--no-print-stdout` snapshots `summary-final.md` before the render and leaves `python/pr_body.py` rc semantics unchanged. It exits `0` when Python exits `0`. When Python exits non-zero, it always logs the failure to Tool Failures before evaluating handoff. It then exits `0` only when `summary-final.md` is non-empty and its bytes changed from the pre-call snapshot, covering post-persist stamp or tracking-upsert failures. It exits non-zero when render/write did not produce a fresh summary body.

## KV grammar

The wrapper relays the underlying helper stdout unchanged unless this file names explicit keys. Explicit keys are newline-delimited `KEY=value` records and must be token-scannable by the orchestrator.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Telemetry consumers read `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` from `$IMPLEMENT_TMPDIR/session-env.sh` internally instead of relying on inline SKILL.md triplets.
- Marker emission in `step-16-17.sh` keys on the captured Step 17 exit code and a non-empty `summary-final.md`, not file presence alone.
- Python final-report rc semantics are unchanged; wrapper handoff is shell snapshot-based only.

## Edit-in-sync

Update `skills/implement/SKILL.md`, `step-16-17.sh`, and the implement structure/timing harnesses when this contract or argv changes.
