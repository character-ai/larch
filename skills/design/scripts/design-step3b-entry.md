# design-step3b-entry.sh

## Purpose

Wrapper for `/design` Step 3b entry. It marks Step 3.5 complete, classifies `plan.txt`, emits `DIAGRAM_REQUIRED=true|false`, and completes the no-diagram path inline.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Classifies `### NEW:`, `### UPDATED:`, `### REWRITTEN:`, and `### MAY_UPDATE:` plan headings.
- Treats `### MAY_UPDATE:` docs-only paths as non-architectural the same way as `### UPDATED:` docs-only paths.
- Treats missing, empty, heading-free, script, Python, `SKILL.md`, extensionless, and unrecognized paths as architectural.
- Runs FINALIZE and writes `.completed/step-3b` inside the non-architectural branch only after the driver succeeds.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
