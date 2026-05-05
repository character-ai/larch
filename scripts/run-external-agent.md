# scripts/run-external-agent.sh — contract

Monitored wrapper for external agents. It launches a command, writes `<output>.meta`, writes `<output>.done` on exit, enforces a timeout, and emits human-readable progress.

## Output capture modes

- Default: the child manages its own output path; wrapper stdout/stderr are not captured into `--output`.
- `--capture-stdout`: redirects child stdout and stderr to `--output`. Cursor uses this mode.
- `--capture-stdout-only`: redirects child stdout to `--output` and child stderr to `<output>.diag`. Gemini review uses this mode so JSON stdout is not corrupted by diagnostic noise; Gemini implementation uses `--capture-stdout` because the dispatcher consumes the on-disk manifest rather than stdout JSON.

The capture flags are mutually exclusive. Metadata includes both `CAPTURE_STDOUT` and `CAPTURE_STDOUT_ONLY`; retry callers must preserve the original mode.

## Invariants

- Always remove stale `<output>`, `<output>.done`, `<output>.meta`, and `<output>.diag` before launch.
- Always write `<output>.done` via the exit trap.
- Keep `set -euo pipefail`; child exit codes are captured via guarded `wait`.
- Diagnostic text is appended to `<output>.diag` so stdout-only capture can retain child stderr.

## Poll interval (`RUN_EXTERNAL_AGENT_POLL_INTERVAL`)

The wrapper polls the child PID with `kill -0` in a loop and `sleep`s `$RUN_EXTERNAL_AGENT_POLL_INTERVAL` seconds (default `10`) between checks. Production callers wrapping real agents leave the default — 10s polling keeps progress chatter human-readable and bounds time-to-notice-timeout. Test harnesses that wrap stub binaries which exit in microseconds (e.g. `skills/implement/scripts/test-cursor-implementer.sh`, `skills/implement/scripts/test-gemini-implementer.sh`, `scripts/test-launch-gemini-review.sh`, `scripts/test-check-reviewers.sh`) export `RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05` so each stub invocation does not pay a full 10s sleep cycle. The variable accepts integer or decimal seconds; values that are not strictly positive are rejected with exit 1. Progress messages still fire once per elapsed minute regardless of poll cadence (driven by bash's `$SECONDS` builtin).

## Call sites

- `scripts/launch-gemini-review.sh` — Gemini reviewer JSON stdout capture.
- `scripts/launch-gemini-implement.sh` — Gemini implementer transcript capture.

## Test harness

Covered indirectly by `scripts/test-launch-gemini-review.sh`, `scripts/test-check-reviewers.sh`, and collector harnesses.

## Edit-in-sync

Update `scripts/collect-agent-results.sh` retry metadata parsing, launch wrappers, and this contract when adding capture modes or metadata keys.
