### FINDING_1: WORSE fallback text still describes previous-round comparison
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-dyn-baseline-contract, Codex-Requirements, Codex-dyn-operator-flow
- **Severity**: important
- **Concern**: The assessor comparison is proposed to be re-anchored to `plan.txt-original`, but WORSE fallback/headline text in the tally and driver paths still says the current plan is worse than the previous/prior round. On round 2+ or when assessor reasoning/headlines are absent, the Continue/Stop prompt can misstate the comparator and mislead the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update both fallback strings to name the original anchor or plan.txt-original, and adjust/add the corresponding assessor-display regression assertions.
  - From Codex-Innovation, Codex-dyn-baseline-contract: Update both fallback strings to say plan.txt-original/original plan, and add/update the existing tally/driver assertions rather than adding new surfaces
  - From Codex-Requirements: Add the tiny string updates so fallback WORSE text says current plan is worse than plan.txt-original/the original anchor, with existing tally/driver assertions adjusted if they pin the text.
  - From Codex-dyn-operator-flow: Include these existing fallback strings in the plan and change them to current-vs-original wording; update any affected tests

### FINDING_2: Missing direct SIMPLE rc=10 Continue/Stop handoff coverage
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-regression-harness
- **Severity**: important
- **Concern**: Planned regression coverage proves SIMPLE assess-plan-round can tally a WORSE result, but does not directly prove the Step 3.6 driver/handoff path stops SIMPLE runs at the Continue/Stop gate with rc 10, trusted trailer filtering, round metadata, and no completed sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Extend test-design-plan-quality-assessor.sh with a SIMPLE worse-majority driver/handoff case, or run the existing rc10 handoff fixture once as SIMPLE, and make that the acceptance anchor.
  - From Codex-dyn-regression-harness: Add or convert a SIMPLE handoff case to return worse-majority with ROUND_NUM=1 and trusted trailers, then assert ASSESSOR_RC=10, ASSESSOR_ROUND_NUM=1, no skip breadcrumb, and no .completed/step-3.6 sentinel before operator confirmation

### FINDING_3: Tier-agnostic SIMPLE assessor plan misses sibling HARD-only docs and harness pins
- **Reviewer(s)**: Cursor-dyn-contract-drift, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The plan updates Step 3.6 but misses other documentation and test-documentation surfaces that still describe the original snapshot or assessor path as HARD-only. After SIMPLE starts writing `plan.txt-original` and running the assessor, those stale docs/harness claims would contradict runtime behavior and could preserve or reintroduce retired gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-drift: After tier-agnostic snapshot lands, orchestrator Step 2b prose and the helper catalog still tell operators the plan.txt-original write is HARD-only, contradicting design-postplan-emit.sh and assessor behavior on SIMPLE Add skills/design/SKILL.md Step 2b post-plan bullet (~974) and design-postplan-emit helper-catalog entry (~1687) to the plan: replace HARD-only snapshot language with tier-agnostic write-once snapshot wording
  - From Codex-dyn-contract-drift: Add these sibling docs and SKILL Step 2b/helper-catalog lines to the planned doc updates; make them tier-agnostic and remove obsolete cheap-skip/classification-warning coverage claims.

### FINDING_4: SIMPLE round-1 assessor mock must verify original anchoring
- **Reviewer(s)**: Codex-dyn-regression-harness
- **Severity**: important
- **Concern**: The proposed SIMPLE round-1 assessor regression can pass with canned WORSE/TIE files even if the implementation dispatches with the wrong `--plan-prev`. Without strict mock validation, the test may not prove round 1 compares current plan to `plan.txt-original`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-regression-harness: Make the new round-1 dispatch mock parse --round-num, --plan-original, --plan-prev, and --plan-current; fail unless round-num is 1 and plan-prev equals plan-original, and write round-1 assessor artifacts

### FINDING_5: Driver tests may miss stale --design-classification dispatch flag
- **Reviewer(s)**: Codex-dyn-regression-harness
- **Severity**: important
- **Concern**: The testing plan removes the old `--design-classification` assertion but does not require the fake child/parser to reject or assert absence of that removed flag. If the driver continues passing it after the child removes support, tests could pass while production falls into assess-failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-regression-harness: Make the fake assess-plan-round.sh parser strict for allowed args, or add an explicit call-log assertion that --design-classification is absent on the driver dispatch path

### FINDING_6: Removing HARD pause condition can leave unused RESTORED_DESIGN_CLASSIFICATION
- **Reviewer(s)**: Codex-dyn-operator-flow
- **Severity**: important
- **Concern**: The plan removes the `STEP=3b` HARD condition in `design-pause-load.sh`, but does not remove the now-unused `RESTORED_DESIGN_CLASSIFICATION` extraction/normalization. If it has no remaining consumer, ShellCheck SC2034 can fail lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-operator-flow: Revise the plan to delete the RESTORED_DESIGN_CLASSIFICATION extraction and normalization when removing the HARD guard, or otherwise keep it with an explicit consumer
