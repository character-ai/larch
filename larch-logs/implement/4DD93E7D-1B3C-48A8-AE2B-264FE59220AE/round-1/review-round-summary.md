# Review Round 1

- Mode: `diff`
- 10 accepted, 3 rejected (3 neutral)

## Accepted Findings

### FINDING_1: correctness: skills/design/SKILL.md:550-554
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 3 entry prose requires --reentry for Gate A/C re-entry but the canonical bash fence omits it. Gate A Ready for review or Gate C Re-run review panel runs design-step3-entry.sh without --reentry; .step3-reentry is never created, design-step3-state.sh --direct-review-entry no-ops, and stale step-3/3.5/3b sentinels persist through re-review. Add --reentry to the re-entry fence variant or document that the orchestrator must append --reentry on Gate A/C paths while first-time entry must not.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: skills/design/SKILL.md:550-554
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] The prose says Gate A/Gate C re-entry uses design-step3-entry.sh --reentry, but the actual Step 3 entry fence omits --reentry. A Ready-for-review or Re-run-review-panel re-entry that follows the fenced command will not create .step3-reentry, causing design-step3-state.sh --direct-review-entry to no-op instead of restoring re-entry state. Make the executable Step 3 entry fence conditional or explicit for re-entry with --reentry, and add a structure test that checks the actual fence rather than only prose.
- **Suggested revision**: Address the concern above.


### FINDING_11: **correctness** `skills/design/SKILL.md:550-554` — The Step 3 entry prose requires Gate A / Gate C re-entry to call `design-step3-entry.sh --reentry` so `.step3-reentry` exists before `design-step3-state.sh --direct-review-entry` runs, but the canonical bash fence invokes `design-step3-entry.sh` with no `--reentry`. `design-step3-state.sh` no-ops direct-review hygiene when that marker is absent (`skills/design/scripts/design-step3-state.sh:96-98`), so an orchestrator that copies the fence literally on “Ready for review” or “Re-run review panel” will skip sentinel cleanup and bypass-package restore. This is worse after the migration because the marker write moved out of prompt-side shell. **Suggested fix:** Make the fence route-explicit, e.g. two templates or one fence with a documented re-entry branch: `design-step3-entry.sh --reentry` for Gate A / Gate C paths and bare `design-step3-entry.sh` for first entry; add a `test-design-structure.sh` pin that the re-entry fence includes `--reentry`.
- **Reviewer**: dyn-resume-state-boundary-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:550-554` — The Step 3 entry prose requires Gate A / Gate C re-entry to call `design-step3-entry.sh --reentry` so `.step3-reentry` exists before `design-step3-state.sh --direct-review-entry` runs, but the canonical bash fence invokes `design-step3-entry.sh` with no `--reentry`. `design-step3-state.sh` no-ops direct-review hygiene when that marker is absent (`skills/design/scripts/design-step3-state.sh:96-98`), so an orchestrator that copies the fence literally on “Ready for review” or “Re-run review panel” will skip sentinel cleanup and bypass-package restore. This is worse after the migration because the marker write moved out of prompt-side shell. **Suggested fix:** Make the fence route-explicit, e.g. two templates or one fence with a documented re-entry branch: `design-step3-entry.sh --reentry` for Gate A / Gate C paths and bare `design-step3-entry.sh` for first entry; add a `test-design-structure.sh` pin that the re-entry fence includes `--reentry`.
- **Suggested revision**: Address the concern above.


### FINDING_13: **correctness** `skills/design/scripts/test-design-pause-resume.sh:1497-1534` — The plan called for coverage that no-flag `design-step3-review.sh` preserves first-entry pause ordering (pause before review launch, no resume-state writes). The new pause/resume block only exercises flag-bearing paths. Without that case, a regression that writes resume state before pause on first entry, or pauses after spurious writes, would not be caught. **Suggested fix:** Add a case that sets `.pause-requested`, invokes `design-step3-review.sh` with no resume flags, asserts `PAUSE_OK=true`, and asserts no `.step3-round-*`, `.gate-b-per-round-approval-round-*`, or `.postplan-operator-continue-*` files were created in the snapshot.
- **Reviewer**: dyn-resume-state-boundary-output.txt
- **Concern**: - **correctness** `skills/design/scripts/test-design-pause-resume.sh:1497-1534` — The plan called for coverage that no-flag `design-step3-review.sh` preserves first-entry pause ordering (pause before review launch, no resume-state writes). The new pause/resume block only exercises flag-bearing paths. Without that case, a regression that writes resume state before pause on first entry, or pauses after spurious writes, would not be caught. **Suggested fix:** Add a case that sets `.pause-requested`, invokes `design-step3-review.sh` with no resume flags, asserts `PAUSE_OK=true`, and asserts no `.step3-round-*`, `.gate-b-per-round-approval-round-*`, or `.postplan-operator-continue-*` files were created in the snapshot.
- **Suggested revision**: Address the concern above.


### FINDING_16: **risk-integration** `skills/design/SKILL.md:550-554` — The Step 3 entry prose requires Gate A / Gate C re-entry to call `design-step3-entry.sh --reentry`, but the canonical Bash fence immediately below invokes `design-step3-entry.sh` without `--reentry`. An orchestrator that follows the fence literally will skip `.step3-reentry`, so `design-step3-state.sh --direct-review-entry` will not restore the direct-review bypass package or consume the re-entry marker. That breaks Gate A “Ready for review” and Gate C “Re-run review panel” re-entry semantics (failure mode #1/#2 in the plan). **Suggested fix:** Make the fence match the prose: pass `--reentry` on re-entry paths (conditional instruction plus example fence), or split into first-entry vs re-entry fences so the copy-paste template cannot omit the flag.
- **Reviewer**: dyn-prompt-contract-drift-output.txt
- **Concern**: - **risk-integration** `skills/design/SKILL.md:550-554` — The Step 3 entry prose requires Gate A / Gate C re-entry to call `design-step3-entry.sh --reentry`, but the canonical Bash fence immediately below invokes `design-step3-entry.sh` without `--reentry`. An orchestrator that follows the fence literally will skip `.step3-reentry`, so `design-step3-state.sh --direct-review-entry` will not restore the direct-review bypass package or consume the re-entry marker. That breaks Gate A “Ready for review” and Gate C “Re-run review panel” re-entry semantics (failure mode #1/#2 in the plan). **Suggested fix:** Make the fence match the prose: pass `--reentry` on re-entry paths (conditional instruction plus example fence), or split into first-entry vs re-entry fences so the copy-paste template cannot omit the flag.
- **Suggested revision**: Address the concern above.


### FINDING_18: **risk-integration** `skills/design/SKILL.md:601,669` and `skills/design/references/approval-gates.md:168` — Loop-mode Gate B post-apply already ends with a single `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` resume at Shared post-apply pipeline step 10. `SKILL.md` line 669 then instructs a second resume with the same flags “after Gate B settles,” and the post-loop matrix at line 601 also says “then resume” after the shared post-apply pipeline that step 10 already owns. On `main-agent-apply-required`, auto-apply, and similar loop-mode Gate B paths, an orchestrator can launch Step 3 review twice for one boundary (plan failure modes #17/#18). **Suggested fix:** Remove the redundant resume from `SKILL.md:669` (and the trailing “then resume” from matrix row 601); treat `approval-gates.md` step 10 as the sole loop-mode resume owner after post-apply, except for bail-outs that need `--findings-file`, `--postplan-operator-continue`, or `--phase awaiting-post-apply`.
- **Reviewer**: dyn-prompt-contract-drift-output.txt
- **Concern**: - **risk-integration** `skills/design/SKILL.md:601,669` and `skills/design/references/approval-gates.md:168` — Loop-mode Gate B post-apply already ends with a single `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` resume at Shared post-apply pipeline step 10. `SKILL.md` line 669 then instructs a second resume with the same flags “after Gate B settles,” and the post-loop matrix at line 601 also says “then resume” after the shared post-apply pipeline that step 10 already owns. On `main-agent-apply-required`, auto-apply, and similar loop-mode Gate B paths, an orchestrator can launch Step 3 review twice for one boundary (plan failure modes #17/#18). **Suggested fix:** Remove the redundant resume from `SKILL.md:669` (and the trailing “then resume” from matrix row 601); treat `approval-gates.md` step 10 as the sole loop-mode resume owner after post-apply, except for bail-outs that need `--findings-file`, `--postplan-operator-continue`, or `--phase awaiting-post-apply`.
- **Suggested revision**: Address the concern above.


### FINDING_19: **risk-integration** `skills/design/references/approval-gates.md:85,168` and `skills/design/SKILL.md:669` — Gate B’s zero-findings loop-mode short-circuit already resumes once with `--phase awaiting-continuation` at line 85. `SKILL.md:669` still adds another continuation resume after “Gate B settles,” so the zero-findings path can also double-launch review when `STEP3_REVIEW_LOOP_STATUS` is set. **Suggested fix:** Scope line 669’s post-settle resume to paths that did not already resume in the zero-findings short-circuit or Shared post-apply step 10, or delete the blanket resume sentence and point all loop-mode resumes to the post-loop matrix / `approval-gates.md` step 10 only.
- **Reviewer**: dyn-prompt-contract-drift-output.txt
- **Concern**: - **risk-integration** `skills/design/references/approval-gates.md:85,168` and `skills/design/SKILL.md:669` — Gate B’s zero-findings loop-mode short-circuit already resumes once with `--phase awaiting-continuation` at line 85. `SKILL.md:669` still adds another continuation resume after “Gate B settles,” so the zero-findings path can also double-launch review when `STEP3_REVIEW_LOOP_STATUS` is set. **Suggested fix:** Scope line 669’s post-settle resume to paths that did not already resume in the zero-findings short-circuit or Shared post-apply step 10, or delete the blanket resume sentence and point all loop-mode resumes to the post-loop matrix / `approval-gates.md` step 10 only.
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: skills/design/SKILL.md:552-554
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] The runnable Step 3 entry fence omits --reentry even though Gate A and Gate C route re-entry through that single fence. On Gate A Ready for review or Gate C Re-run review panel, following the fenced command does not create .step3-reentry, so direct-review-entry no-ops and stale downstream completion markers can survive. Make the runnable Step 3 entry fence pass --reentry for routed re-entry paths, using an explicit argument binding or separate first-entry and re-entry invocations at the same fence boundary.
- **Suggested revision**: Address the concern above.


### FINDING_4: risk-integration: skills/design/SKILL.md:550-554
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Canonical Step 3 entry bash fence omits --reentry while Gate A/Gate C prose requires it for backward review re-entry. Gate A Ready for review or Gate C Re-run review panel copies the fence without --reentry; .step3-reentry is never written; direct-review sentinel restore is skipped and stale review state persists. Add an explicit re-entry fence (design-step3-entry.sh --reentry) and state first-time entry uses the fence without that flag.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/design/SKILL.md:550-553
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] The routed re-entry path is documented, but the actual Step 3 entry fence still invokes design-step3-entry.sh without --reentry. Gate A/Gate C route through the single Step 3 fence, so following the fence can skip .step3-reentry; design-step3-state.sh --direct-review-entry then noops and stale Step 3/Gate B/Gate C sentinels may survive. Make the Step 3 fence pass --reentry when routed from Gate A/Gate C, for example via a bound args array, and add a structure pin that checks the fence.
- **Suggested revision**: Address the concern above.


