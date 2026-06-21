# design-step3b-entry.sh

## Purpose

Wrapper for `/design` Step 3b finalize mode and Step 5b.5 diagram entry mode. Finalize mode marks Step 3.5 complete, runs FINALIZE, and writes `.completed/step-3b`. Diagram mode runs only after Gate C approval and Step 5b; it classifies `plan.txt`, emits `DIAGRAM_REQUIRED=true|false`, clears stale diagram artifacts, and completes the no-diagram path with `.completed/step-5b.5`.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Keeps `--mode entry` as a deprecated alias for `--mode finalize`.
- Classifies `### NEW:`, `### UPDATED:`, `### REWRITTEN:`, and `### MAY_UPDATE:` plan headings only in diagram mode.
- Treats `### MAY_UPDATE:` docs-only paths as non-architectural the same way as `### UPDATED:` docs-only paths.
- Treats missing, empty, heading-free, script, Python, `SKILL.md`, extensionless, and unrecognized paths as architectural.
- Never writes diagram artifacts or emits `DIAGRAM_REQUIRED` in finalize mode.
- Never runs FINALIZE in diagram mode.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
