# design-step3b-entry.sh

## Purpose

Wrapper for `/design` Step 3b finalize mode and Step 5b.5 diagram entry mode. Finalize mode marks Step 3.5 complete, runs FINALIZE, probes Gate C dialectic eligibility, emits and persists `STEP4_MODE=foreground|background`, and writes `.completed/step-3b` only after that handoff succeeds. Diagram mode runs only after Gate C approval and Step 5b; it classifies `plan.txt`, emits `DIAGRAM_REQUIRED=true|false`, clears stale diagram artifacts, and completes the no-diagram path with `.completed/step-5b.5`.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Keeps `--mode entry` as a deprecated alias for `--mode finalize`.
- Finalize mode uses `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design dialectic-gatec --probe-only` internally.
- Finalize-mode stdout exposes exactly one whole-line `STEP4_MODE=foreground|background` on success.
- Finalize-mode stdout does not forward `DIALECTIC_GATEC_DEBATE_REQUIRED`, driver timing rows, or other probe diagnostics.
- Finalize mode writes `$DESIGN_TMPDIR/.step4-mode.env` with exactly one `STEP4_MODE=foreground|background` row for `resume@4` when fresh finalize stdout is unavailable.
- `run_step3b_finalize` no longer writes `.completed/step-3b`; marker ownership lives in finalize mode after the probe handoff.
- `.completed/step-3b` is written only after successful probe capture, KV validation, stdout emit, and sidecar write.
- Driver success alone does not complete Step 3b.
- Finalize mode does not run the Gate C debate and does not write `.completed/dialectic-gatec-terminal`.
- Classifies `### NEW:`, `### UPDATED:`, `### REWRITTEN:`, and `### MAY_UPDATE:` plan headings only in diagram mode.
- Treats `### MAY_UPDATE:` docs-only paths as non-architectural the same way as `### UPDATED:` docs-only paths.
- Treats missing, empty, heading-free, script, Python, `SKILL.md`, extensionless, and unrecognized paths as architectural.
- Never writes diagram artifacts or emits `DIAGRAM_REQUIRED` in finalize mode.
- Never runs FINALIZE in diagram mode.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
