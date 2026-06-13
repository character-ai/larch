## Proposed Design Outline

### Goals
- Move all raw `: >`, `rm`, `mkdir -p`, and KV-env writes from /design prose into script owners.
- Preserve pause/resume semantics for each moved sentinel.
- Extend `test-design-step3-state.sh` and pause-resume harnesses to cover new flag paths.

### Non-goals
- Do not change runtime behavior or sentinel ordering.
- Do not rename existing `design-step3-state.sh` modes.
- Do not touch unrelated scripts or non-sentinel `rm` calls (e.g., scout manifest cleanup).

### Approach sketch
- Add `--reentry` to `design-step3-entry.sh`; the flag writes `.step3-reentry` and clears `.step3-entry-plan-printed` before the existing `--direct-review-entry` state call.
- Add `--phase <value>` and `--findings-file <path>` to `design-step3-review.sh`; the wrapper writes `.step3-round-N.phase` and `.gate-b-per-round-approval-round-N.env` before launching the review.
- Update `design-step2b-postplan.sh` to write `.completed/step-2b.5` on its own rc=0 success path; add a `--write-completion-only` flag for Override and Split non-exiting returns that need the sentinel without re-running checks.
- Add `--clear-entry-plan-printed` mode to `design-step3-state.sh` for the legacy heuristic continuation path (only if not already handled by `--reentry`).
- Update SKILL.md, `approval-gates.md`, `discussion-rounds.md`, and `decompose-panel.md`: replace raw write instructions with wrapper flag invocations.

### Surfaces in scope
- `skills/design/SKILL.md`
- `skills/design/references/approval-gates.md`
- `skills/design/references/discussion-rounds.md`
- `skills/design/references/decompose-panel.md`
- `skills/design/scripts/design-step3-entry.sh` (and `design-step3-entry-state.sh`)
- `skills/design/scripts/design-step3-review.sh`
- `skills/design/scripts/design-step2b-postplan.sh` (and `design-step2b5.sh`)
- `skills/design/scripts/design-step3-state.sh`
- `skills/design/scripts/test-design-step3-state.sh`
- `skills/design/scripts/test-design-pause-resume.sh`

### Open questions
- None.
