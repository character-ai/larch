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

## Call sites

- `scripts/launch-gemini-review.sh` — Gemini reviewer JSON stdout capture.
- `scripts/launch-gemini-implement.sh` — Gemini implementer transcript capture.

## Test harness

Covered indirectly by `scripts/test-launch-gemini-review.sh`, `scripts/test-check-reviewers.sh`, and collector harnesses.

## Edit-in-sync

Update `scripts/collect-agent-results.sh` retry metadata parsing, launch wrappers, and this contract when adding capture modes or metadata keys.
