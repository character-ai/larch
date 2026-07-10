### FINDING_1: stale review.panel assertions in calibration tests
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, cursor-specialist-plan-fidelity-forced
- **Severity**: major
- **Concern**: `python/tests/calibration/test_difficulty.py` still asserts the removed `review.panel` HARD override behavior, so the calibration suite now fails against the new archetype routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Rewrite or drop the three review.panel assertions; keep design.plan_review_panel override tests
  - From cursor-specialist-testing: Rewrite or remove review.panel assertions
  - From cursor-specialist-plan-fidelity-forced: Remove review.panel assertions; keep design.plan_review_panel cases.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: [OUT_OF_SCOPE] stale external-reviewer matrix and CI-recovery docs
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-plan-fidelity-forced, dyn-dyn-model-routing
- **Severity**: major
- **Concern**: `docs/external-reviewers.md` and the related configuration note still describe the retired code-review HARD/default-role matrix and the old CI recovery order, so readers will expect reviewer rows and escalation paths that no longer exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Rewrite row to Cursor singles/pairs and gpt-5.6-luna/terra matrix
  - From cursor-specialist-edge-cases: Code-review row still documents HARD default-role Codex reviewers removed by this change. Operators expect correctness/edge-cases on gpt-5.6-sol default role while code launches review-role Luna/Terra pairs. Rewrite the row to the new tier matrix with no default-role Codex panel rows.
  - From codex-specialist-correctness: Update these doc rows to the new TRIVIAL/MODERATE/HARD panel matrix and the CI recovery order `Codex fix→Cursor auto→Claude Sonnet 4.6 1M`.
  - From codex-specialist-edge-cases: Update the row to Codex fix Terra, then Cursor auto, then Claude Sonnet 4.6 [1m].
  - From cursor-specialist-plan-fidelity-forced: Rewrite the row to the TRIVIAL/MODERATE/HARD Cursor+Codex matrix from the plan.
  - From dyn-dyn-model-routing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] forced plan-fidelity docs still claim an extra reviewer row
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-plan-fidelity-forced, dyn-dyn-model-routing
- **Severity**: major
- **Concern**: The forced plan-fidelity sections still describe an extra reviewer row/pass for `review.panel`, even though the implementation no longer appends one there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: State forced plan-fidelity no longer adds review.panel rows
  - From cursor-specialist-correctness: Update when sweeping workflow docs
  - From cursor-specialist-edge-cases: Replace with a note that forced plan-fidelity rows are disabled for review.panel.
  - From cursor-specialist-plan-fidelity-forced: State that plan-fidelity does not add reviewers outside the tier matrix.
  - From dyn-dyn-model-routing: The “Forced plan-fidelity reviewer” section still says Step 5 appends a forced row, but `review_dispatch_panel._append_forced_plan_fidelity_row` is a no-op for `review.panel` and Note A already says no extra row is emitted. The doc contradicts the implementation.
  - From dyn-dyn-model-routing: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_6: [OUT_OF_SCOPE] plan-mandated routing and pricing coverage is still missing
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing, cursor-specialist-plan-fidelity-forced, dyn-dyn-model-routing
- **Severity**: major
- **Concern**: Plan-mandated test coverage is still missing for the new routing and pricing matrix, so difficulty, tier, fallback, and pricing regressions can still ship without signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add TRIVIAL cursor-available=false codex-available=true static and dynamic manifest tests
  - From cursor-specialist-testing: Add static and dynamic TRIVIAL cursor-down cases
  - From cursor-specialist-testing: Add launcher argv tests for difficulty precedence
  - From cursor-specialist-testing: Add dispatch argv tests with --tier and --default-model
  - From cursor-specialist-testing: Add waterfall argv forwarding and registry order tests
  - From cursor-specialist-testing: Assert --tier and tier vote model on dispatch argv
  - From cursor-specialist-testing: Assert --model auto and claude-sonnet-4-6[1m] on coder launches
  - From codex-specialist-testing: Add the missing tests for --difficulty, --tier, TRIVIAL Codex fallback, and Terra pricing before merge.
  - From cursor-specialist-plan-fidelity-forced: Add the missing tests from the plan Testing strategy section.
  - From dyn-dyn-model-routing: The plan called for TRIVIAL Cursor-down panel coverage and launch-codex-implement --difficulty launcher assertions; those paths are not covered.
  - From dyn-dyn-model-routing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_11: [OUT_OF_SCOPE] workflow-lifecycle prose still describes a removed forced reviewer row
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Workflow-lifecycle prose still refers to a forced middle-band reviewer row that the current code path does not emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update when sweeping workflow docs


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] self-review docs still mention a plan-fidelity inline pass
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The implement self-review reference still describes a plan-fidelity inline pass, which can mislead readers about its scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Clarify self-review-only scope if still intended


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] planned Claude normalization is still missing at the external boundary
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `_run_external.py` still lacks the planned Claude `[1m]` model normalization at the boundary, so suffixed ids can leak into ledgers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Audit remaining Claude token writers or add shared normalizer at boundary


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_14: [OUT_OF_SCOPE] dead generic-Codex helper still remains
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `review_dispatch_panel._append_generic_codex_row` still keeps a dead lookup path for a deleted generalist slot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Remove dead helper or generic-codex path in a follow-up cleanup.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] progress reporting still misses explicit claude_sub normalization
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `progress_report` still does not normalize explicit `claude_sub` model values with a `[1m]` suffix, so progress output can diverge from normalized ledger models.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Apply normalize_claude_ledger_model when vendor is claude_sub and model is non-empty.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Cursor launcher still contains an unreachable try/except
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The Cursor launcher still wraps a literal argv list in an unreachable `try/except`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Delete the unreachable except block.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

