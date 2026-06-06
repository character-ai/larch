### FINDING_1:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-assessor.sh:160-166, skills/design/scripts/design-plan-quality-assessor.sh:232-243
- **Concern**: WORSE gate fallback text remains previous-round anchored after the proposed current-vs-plan.txt-original re-anchor. Scenario: On round 2+, assessors can correctly vote WORSE versus plan.txt-original while the operator-facing fallback headline says the plan is worse than the prior round; that can be false and mislead the Continue/Stop decision
- **Proposed resolution**: Update both fallback strings to name the original anchor or plan.txt-original, and adjust/add the corresponding assessor-display regression assertions.

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-baseline-contract
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-assessor.sh:161; skills/design/scripts/design-plan-quality-assessor.sh:242
- **Concern**: The plan re-anchors assessor prompts to plan.txt-original but misses fallback WORSE headline text that still says previous/prior round. Scenario: If assessors produce a WORSE majority with empty reasoning, the Continue/Stop gate can tell the operator the plan is worse than the previous round even though the verdict is now current-vs-original, which is misleading on round 2+
- **Proposed resolution**: Update both fallback strings to say plan.txt-original/original plan, and add/update the existing tally/driver assertions rather than adding new surfaces

### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-assessor.sh:160-166; skills/design/scripts/design-plan-quality-assessor.sh:232-243
- **Concern**: Re-anchor plan misses WORSE fallback text that still says previous/prior round. Scenario: If assessors omit reasoning or the verdict file is empty, the Continue/Stop gate can explain a WORSE result as worse than the prior round even though the required comparator is plan.txt-original.
- **Proposed resolution**: Add the tiny string updates so fallback WORSE text says current plan is worse than plan.txt-original/the original anchor, with existing tally/driver assertions adjusted if they pin the text.

### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-plan-quality-assessor.sh:197-277; <TMPDIR>/plan.txt:71-75
- **Concern**: Regression coverage stops below the Continue/Stop handoff for SIMPLE WORSE. Scenario: A SIMPLE assess-plan-round WORSE test proves the child can tally, but does not prove the SIMPLE Step 3.6 driver/handoff returns rc 10, filters trusted trailers, and reaches the Continue/Stop branch.
- **Proposed resolution**: Extend test-design-plan-quality-assessor.sh with a SIMPLE worse-majority driver/handoff case, or run the existing rc10 handoff fixture once as SIMPLE, and make that the acceptance anchor.

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-contract-drift
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:974
- **Concern**: skills/design/SKILL.md:1687. Scenario: Plan updates Step 3.6 HARD-only prose but omits Step 2b snapshot wording that still says initial HARD snapshot / optional HARD snapshot
- **Proposed resolution**: After tier-agnostic snapshot lands, orchestrator Step 2b prose and the helper catalog still tell operators the plan.txt-original write is HARD-only, contradicting design-postplan-emit.sh and assessor behavior on SIMPLE Add skills/design/SKILL.md Step 2b post-plan bullet (~974) and design-postplan-emit helper-catalog entry (~1687) to the plan: replace HARD-only snapshot language with tier-agnostic write-once snapshot wording

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:974,1687; skills/design/scripts/test-design-plan-quality-assessor.md:5-11; skills/design/scripts/test-assess-plan-round.md:5; skills/design/scripts/test-design-postplan-emit.md:20-23,30-32
- **Concern**: Plan's doc/test-doc checklist misses non-Step-3.6 hard-gate prose that becomes false under the proposed SIMPLE assessor flow.. Scenario: After implementation, SIMPLE writes plan.txt-original and dispatches the assessor, but the SKILL still says the initial snapshot is HARD/optional HARD and harness docs still pin non-HARD/SIMPLE cheap-skip, HARD gate, and classification warning behavior; future edits can preserve or reintroduce the retired gates.
- **Proposed resolution**: Add these sibling docs and SKILL Step 2b/helper-catalog lines to the planned doc updates; make them tier-agnostic and remove obsolete cheap-skip/classification-warning coverage claims.

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-regression-harness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1245-1320; skills/design/scripts/test-design-plan-quality-assessor.sh:197-280,484-516
- **Concern**: Missing direct SIMPLE rc=10 handoff coverage for the Continue/Stop gate. Scenario: The assess-plan-round SIMPLE WORSE test can pass while prompt-side Step 3.6 still skips SIMPLE or writes step-3.6 as completed, so a degraded SIMPLE plan would not actually stop at the operator Continue/Stop gate
- **Proposed resolution**: Add or convert a SIMPLE handoff case to return worse-majority with ROUND_NUM=1 and trusted trailers, then assert ASSESSOR_RC=10, ASSESSOR_ROUND_NUM=1, no skip breadcrumb, and no .completed/step-3.6 sentinel before operator confirmation

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-regression-harness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-assess-plan-round.sh:37-53,378-394
- **Concern**: The proposed SIMPLE round-1 assessor regression needs the dispatch mock to verify round-1 original anchoring, not just emit canned WORSE/TIE files. Scenario: A buggy implementation could dispatch round 1 with --plan-prev pointing at plan-after-round-1.txt or another non-original file; a mock that ignores --round-num and --plan-prev would still write WORSE and let the test pass
- **Proposed resolution**: Make the new round-1 dispatch mock parse --round-num, --plan-original, --plan-prev, and --plan-current; fail unless round-num is 1 and plan-prev equals plan-original, and write round-1 assessor artifacts

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-regression-harness
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-plan-quality-assessor.sh:408-413; skills/design/scripts/test-design-plan-quality-assessor.sh:107-130
- **Concern**: The testing plan drops the old --design-classification assertion but does not require the stub to reject or assert absence of the removed flag. Scenario: If design-plan-quality-assessor.sh keeps passing --design-classification after assess-plan-round.sh removes it, the current fake child ignores unknown args and the driver tests can pass while production settles as assess-failed instead of dispatching
- **Proposed resolution**: Make the fake assess-plan-round.sh parser strict for allowed args, or add an explicit call-log assertion that --design-classification is absent on the driver dispatch path

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-operator-flow
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-assessor.sh:160-166; skills/design/scripts/design-plan-quality-assessor.sh:232-243
- **Concern**: WORSE display fallbacks remain previous-round anchored even though the proposed assessor verdict is current-vs-plan.txt-original. Scenario: If WORSE assessors omit reasoning, or the verdict headline cannot be read, the Continue/Stop prompt can tell the operator the plan is worse than the previous/prior round instead of worse than the original anchor, weakening the SIMPLE anti-bloat brake
- **Proposed resolution**: Include these existing fallback strings in the plan and change them to current-vs-original wording; update any affected tests

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-operator-flow
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/design-pause-load.sh:282-288
- **Concern**: The plan drops the STEP=3b HARD condition but does not remove the now-unused RESTORED_DESIGN_CLASSIFICATION read/case block. Scenario: After the condition is made tier-agnostic, RESTORED_DESIGN_CLASSIFICATION has no remaining consumer and ShellCheck SC2034 can fail make lint
- **Proposed resolution**: Revise the plan to delete the RESTORED_DESIGN_CLASSIFICATION extraction and normalization when removing the HARD guard, or otherwise keep it with an explicit consumer
