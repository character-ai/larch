# design-step2b-drafter.sh

## Purpose

Wrapper for a `/design` Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Removes `step2b-drafter-status.txt.token-record` before launch so retries
  cannot ingest stale Codex usage.
- For the Codex drafter path only, best-effort appends the stable sidecar to
  `$DESIGN_TMPDIR/token-report.ndjson` and records it into the active design
  token ledger with `DESIGN_TMPDIR` exported. Missing, empty, or malformed
  sidecars are non-blocking no-ops.
- Active-ledger ingestion is required for live `/design` cost lines. NDJSON
  append is required for committed run-log accounting.

## Harness

Covered by `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-step2b-drafter.sh`, and relevant `/design` script checks.
