### OOS_1: **risk-integration** `skills/design/references/plan-review.md:59` — This normative Step 3 reference still tells bail-outs to resume via bare `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND"` and a “durable `.step3-round-N.phase` marker,” without any collapsed `--phase`, `--findings-file`, or `--postplan-operator-continue` flag. That contradicts the migrated single-call contract in `SKILL.md`, `approval-gates.md`, and `review-design-step3-loop.md`, and reintroduces the pre-migration write-then-resume pattern the branch removed (plan failure modes #12/#13). **Suggested fix:** Replace line 59 with the launcher-owned resume matrix from `review-design-step3-loop.md` (one wrapper call with the appropriate state flag) and drop prompt-side phase-marker wording.
- **Reviewer**: dyn-prompt-contract-drift-output.txt
- **Concern**: - **risk-integration** `skills/design/references/plan-review.md:59` — This normative Step 3 reference still tells bail-outs to resume via bare `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND"` and a “durable `.step3-round-N.phase` marker,” without any collapsed `--phase`, `--findings-file`, or `--postplan-operator-continue` flag. That contradicts the migrated single-call contract in `SKILL.md`, `approval-gates.md`, and `review-design-step3-loop.md`, and reintroduces the pre-migration write-then-resume pattern the branch removed (plan failure modes #12/#13). **Suggested fix:** Replace line 59 with the launcher-owned resume matrix from `review-design-step3-loop.md` (one wrapper call with the appropriate state flag) and drop prompt-side phase-marker wording.
- **Suggested revision**: Address the concern above.


### OOS_2: risk-integration: skills/design/references/plan-review.md:59
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] plan-review.md still documents bare --starting-round resume with a durable .step3-round-N.phase marker instead of collapsed wrapper flags. SKILL.md mandates reading plan-review.md before Step 3; orchestrator may resume without --phase/--findings-file/--postplan-operator-continue and skip required resume state. Update plan-review.md to the wrapper-owned resume matrix matching review-design-step3-loop.md and SKILL.md.
- **Suggested revision**: Address the concern above.


