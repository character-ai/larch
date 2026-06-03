## Proposed Design Outline

### Goals
- Extract the Step 2b post-plan emit sequence (`ACTION=EMIT_PLAN` + HARD `plan.txt-original` snapshot + plan-command validator + KV parse) into one phase-driver script, `design-postplan-emit.sh`.
- Reuse that driver at the three prompt-side re-emit sites (Gate A re-entry, Gate B, discussion-round2), with the HARD snapshot suppressed there.
- Collapse 3 inline SKILL.md fences (~40 lines) into 1 call and centralize the combined-status contract.

### Non-goals
- Do not touch the loop-internal EMIT_PLAN sites (`plan-review-loop.sh`, `revise-plan-with-waterfall.sh`).
- Do not change `defects-found` semantics, the validator / snapshot / emit helpers themselves, or the Step 2b.5 and AskUserQuestion boundaries.
- No behavior change — preserve the exact machine-output contract and control flow.

### Approach sketch
- New `skills/design/scripts/design-postplan-emit.sh` on `lib-phase-driver.sh`: runs EMIT_PLAN (via `design-driver.sh`), a conditional HARD `write-original` snapshot, and a conditional validator (skipped when `review_budget=quick`); emits one combined status (result-env + stdout KV).
- A flag gates the HARD snapshot: initial Step 2b takes it; re-emit sites suppress it. Polarity decided in the plan.
- Orchestrator keeps the gating it cannot delegate: `defects-found` → shared AskUserQuestion, `missing-diff-lines` → repair `plan.txt`; the re-emit dedup pass stays outside the driver.
- Replace each migrated fence with one driver call + a KV parse.

### Surfaces in scope
- `skills/design/SKILL.md` (Step 2b fences; Gate A re-entry guard prose).
- `skills/design/references/approval-gates.md` (Gate B / Shared post-apply pipeline) and `references/discussion-rounds.md` (round-2 re-emit).
- New siblings: `design-postplan-emit.sh` + `.md`, `test-design-postplan-emit.sh` + `.md` stub; `Makefile` target; `scripts/test-design-structure.sh` fence/anchor pins.

### Open questions
- None.
