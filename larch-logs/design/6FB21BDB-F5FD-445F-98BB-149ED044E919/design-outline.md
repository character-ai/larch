## Proposed Design Outline

### Goals
- Fix the definite `step-5c-terminal` sentinel mismatch in `scripts/hook-bg-poll-guard.sh` so the `design-step5c` guard releases on the sentinel `design-step5c.sh` actually writes (`.completed/step-5c`).
- Give the orchestrator a sanctioned, guard-permitted foreground way to check `.completed/step-N` after a premature `<task-notification>`, so recovery stops spiraling into 180+ context-heavy `ps`/poll calls.
- Add regression tests proving the probe is allowed while real progress-polling stays denied.

### Non-goals
- The premature-notification harness root cause (Fix 4) — not reliably fixable in larch; candidate OOS / upstream report.
- Reworking review-loop control flow, the `.bg-wait-active` marker schema, or `design-step3-review.sh` fork behavior.
- Changing `design-step5c.sh` (align the hook to it, not the reverse).

### Approach sketch
- `hook-bg-poll-guard.sh`: change the `design-step5c)` case from `.completed/step-5c-terminal` to `.completed/step-5c`.
- `hook-bg-poll-guard.sh`: add a strict early-allow for a single non-sleeping foreground sentinel probe (`[ -f "$DESIGN_TMPDIR/.completed/step-N" ]` or `test -f …`, optional `&& echo … || echo …` echo-only tail) limited to the `.completed/step-{3,5c,final-summary}` sentinels — mirrors `bash_is_step3_recovery_waiter`, rejects sleep/loops/probe-verbs/result-artifacts.
- `skills/design/SKILL.md`: document that foreground probe as the sanctioned recovery after a premature notification or a killed recovery waiter (one check, then end the turn).

### Surfaces in scope
- `scripts/hook-bg-poll-guard.sh` (+ sibling `hook-bg-poll-guard.md`)
- `scripts/test-hook-bg-poll-guard.sh` (+ sibling `.md`)
- `skills/design/SKILL.md` recovery-guidance prose

### Open questions
- Cover the probe whitelist for all three guarded steps (step-3, step-5c, final-summary) or only step-3? (Lean: all three — identical failure mode.)
