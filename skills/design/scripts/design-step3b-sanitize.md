# design-step3b-sanitize.sh

## Purpose

Legacy/manual compatibility wrapper for `/design` Step 5b.5 architecture-diagram sanitizer handling. Normal Step 5c Python now validates the post-approval candidate, silently promotes accepted diagrams, handles sanitizer rejection cleanup, appends bounded warning logs, writes `architecture-diagram.skipped` on fail-closed paths, and completes `.completed/step-5b.5`.

## Primary callers

- Legacy/manual repair runs that need the old standalone sanitizer wrapper.

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Never emits diagram body markers or diagram Markdown to chat.
- Deletes rejected or unreadable candidates instead of promoting them.
- Writes `architecture-diagram.skipped` on missing-candidate and sanitizer-rejection paths.
- Appends bounded `Warnings` entries through `design_diagram_log.py`; raw candidate and sanitizer output are not passed to committed run logs.
- Never runs plan-review FINALIZE.
- Step 5c Python owns normal sanitizer execution before publish.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
