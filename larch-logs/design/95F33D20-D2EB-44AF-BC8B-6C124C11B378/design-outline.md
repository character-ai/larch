## Proposed Design Outline

### Goals
- Run the Step 3.6 plan-quality assessor on SIMPLE runs too (today HARD-only), so the anti-bloat brake covers the tier whose identity is "smallest change."
- Anchor the WORSE/BETTER/TIE verdict to `plan.txt-original` for both tiers, and fire it from review round 1.
- Remove `--design-classification` from the assessor lane entirely (Round 1 decision).

### Non-goals
- No new files, flags, or abstractions.
- Leave the #3512 numeric drift guard (Step 2b.5) and the review-only/Gate-B apply model unchanged.
- Do not change HARD behavior beyond the shared re-anchor and round-1 firing.

### Approach sketch
- Delete every HARD-only tier gate in the assessor lane: `design-postplan-emit.sh` snapshot, `run-step3-review.sh` round cursor, `design-plan-quality-assessor.sh` early skip, `assess-plan-round.sh` tier skip, and the `design-pause-load.sh` `3b`->`3.6` resume upgrade.
- Re-anchor comparison to current-vs-`plan.txt-original`; replace the `ROUND_NUM < 2` skip with round-1 anchoring (`plan_prev = plan.txt-original`).
- Remove the `--design-classification` flag, the orphaned `resolve_design_classification()`, the sole caller arg, and its validation tests; drop now-orphaned `WORKFLOW_PATH` resolution flagged by SC2034.
- Flip "HARD-only" -> tier-agnostic prose across SKILL.md, references, SECURITY.md, `.md` siblings, and structure-test pins.

### Surfaces in scope
- `skills/design/scripts/`: `design-postplan-emit.sh`, `run-step3-review.sh`, `design-plan-quality-assessor.sh`, `assess-plan-round.sh` (+ `.md` siblings)
- `skills/shared/scripts/render-assessor-prompt.sh`; `scripts/design-pause-load.sh`
- `skills/design/SKILL.md`; `references/{assessor,approval-gates,plan-review}.md`; `SECURITY.md`
- Harnesses: `test-design-postplan-emit.sh`, `test-run-step3-review.sh`, `test-design-plan-quality-assessor.sh`, `test-assess-plan-round.sh`, `test-render-assessor-prompt.sh`, `test-design-pause-resume.sh`, `scripts/test-design-structure.sh`

### Open questions
- None. Blockers verified resolved (#3512, #3421); compat-flag fate resolved in Round 1.
