## Proposed Design Outline

### Goals
- Run the Step 3.6 plan-quality assessor on SIMPLE runs, not just HARD.
- Anchor the assessor verdict to `plan.txt-original` (cumulative drift), for both tiers.
- Fire the WORSE Continue/Stop gate from round 1, so the common single-round SIMPLE case is covered.

### Non-goals
- No new public flag; the assessor runs by tier (`design_classification`), unconditionally.
- No change to the #3512 numeric drift guard — it composes (pre-review, numeric) with the assessor (post-Gate-B, semantic).
- No change to the strict-majority WORSE tally, fail-open policy, or the rc=10 Continue/Stop trailer contract.

### Approach sketch
- Open the four HARD-only gates so SIMPLE flows the same path: `--snapshot-original` text snapshot, round-cursor advance, assessor driver, round orchestrator.
- Anchor the verdict to `plan.txt-original` in `render-assessor-prompt.sh` (unify both tiers).
- Relax the `ROUND_NUM < 2` skip; on round 1 use `plan.txt-original` as the previous-plan anchor (no `plan-after-round-0.txt` exists).
- Open the SKILL.md Step 3.6 tier gate; refresh `references/assessor.md` from "HARD-only" to both tiers.

### Surfaces in scope
- `skills/design/scripts/`: `design-postplan-emit.sh`, `run-step3-review.sh`, `design-plan-quality-assessor.sh`, `assess-plan-round.sh`
- `skills/shared/scripts/render-assessor-prompt.sh`
- `skills/design/SKILL.md` (Step 3.6 gate), `skills/design/references/assessor.md`
- Harnesses: `test-design-plan-quality-assessor.sh`, `test-assess-plan-round.sh`, `test-snapshot-plan-round.sh`, `test-design-postplan-emit.sh`, `test-run-step3-review.sh`, `scripts/test-design-structure.sh`

### Open questions
- None. Tier scope (both) and round-1 firing (yes) resolved in Round 1.
