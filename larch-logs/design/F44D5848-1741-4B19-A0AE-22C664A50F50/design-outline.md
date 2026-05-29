## Proposed Design Outline

### Goals
- Drop the two-option `AskUserQuestion` in Gate B passive-summary mode (`LOOP_STATUS=converged|cap-hit`, `manual_gate_b=false`).
- Make that mode print-and-continue: keep the `## Multi-round loop result` table + the "auto-applied across N rounds" line, then auto-continue with no prompt.
- Keep Gate C (Step 4b) as the single binding decision point.

### Non-goals
- Do not change which findings are applied (the loop's between-round auto-apply is untouched).
- Do not change other Gate B modes: `manual_gate_b=true` (3-option), `revision-failed`/`emit-plan-failed` (warning + manual), zero-findings short-circuit, legacy non-loop auto-apply.
- Do not weaken any approval gate.

### Approach sketch
- Edit the `approval-gates.md` "Gate B passive-summary mode" section: remove the prompt; print the table + line, then auto-continue to Step 3.6. Add an explicit "do NOT halt" note.
- Update `SKILL.md` Step 3.5 prose and the `converged|cap-hit` post-loop branch-matrix bullet to drop "prompt".
- Reword `plan-review.md` references to the passive-summary chooser.
- Scan anti-halt / progress-reporting notes for prompt mentions.
- Verify harness pins; update any test that asserts the two-option prompt.

### Surfaces in scope
- `skills/design/references/approval-gates.md`
- `skills/design/SKILL.md`
- `skills/design/references/plan-review.md`
- Harnesses: `scripts/test-design-structure.sh`, `scripts/test-design-multi-round-integration.sh`, `skills/design/scripts/test-step3-review-cap.sh`

### Open questions
- None. Output shape confirmed in Step 1c: keep the full table.
