# Review Round 2

- Mode: `diff`
- 7 accepted, 5 rejected (1 neutral)

## Accepted Findings

### FINDING_2: SKILL.md Step 2.4 prose contradicts implement Step 5 scout gate
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 2.4 claims skipping `normalize-coder-scout` reintroduces the separate Step 5 scout, contradicting `review_pipeline` implement gate and Step 5 prose. An orchestrator that skips the fence expects scout-round1 timing/cost to return; instead Step 5 runs static-only with `producer-missing` and no separate scout, confusing #4954 debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reword to: skipping the fence drops coder-produced dynamics and Step 5 runs static reviewers only; it does not relaunch scout dynamic-archetypes on /implement.


### FINDING_4: missing test for drafter absent scout block (SCOUT_FAIL_REASON=absent)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required test for drafter output missing the `LARCH_SCOUT` block is absent though `agents.py` implements absent-scout handling. Design Step 2b drafter absent-scout handling and `design_summary` static-only line depend on the absent reason; regressions in `parse_drafter_output` could ship without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add `test_parse_drafter_output_missing_scout_block_sets_absent_reason`.
  - From cursor-specialist-testing-output.txt: Add test with valid plan/summary and no `LARCH_SCOUT` block; assert `scout_fail_reason=absent` and `scout_candidate_written=False`.


### FINDING_5: missing test that docs-only diff classification skips producer-failure warnings
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test asserts that skipped-docs-only (or equivalent diff-classification skip) statuses skip producer-failure warnings. If `_append_producer_scout_warning_once` is broadened or `scout_status` handling changes, docs-only implement runs could get spurious Warnings and inflated warning counts in final summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add `dispatch_panel` test with docs-only classifier asserting no `.producer-scout-warning-logged`.
  - From cursor-specialist-testing-output.txt: Add `dispatch_panel` test with `DIFF_MODE=docs-only` on implement Step 5; assert no `.producer-scout-warning-logged` and no execution-issues append.


### FINDING_7: Step 5 pre-scouted manifest revalidation diverges from filter-manifest path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-scout-gate-output.txt
- **Severity**: important
- **Concern**: Pre-scouted manifests at Step 5 are re-validated with `_normalize_scout_manifest` / `_valid_dynamic_archetype` instead of `scout filter-manifest --mode review`, even though the plan requires implement-path filtering through `filter-manifest`. The validators diverge (for example `_valid_dynamic_archetype` requires `isinstance(weight, int)` while `validate_dynamic_manifest` accepts numeric weights and coerces them). A manifest that passed Step 2 normalization can be classified as `producer-invalid` / `pre_scouted_filtered_to_zero` at Step 5, emit a producer-failure warning, and run static-only despite a valid coder sidecar. `pre_scouted_filtered_to_zero` uses archetype count from normalized `scout-coder-manifest.json` rather than raw producer input, so normalization vs Step 5 `_valid_dynamic_archetype` mismatch may be reported as filtered-to-zero rather than producer validation failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document as stale-sidecar guard or persist raw count in `step2-scout-coder-status.env` for Step 5 comparison.
  - From dyn-dyn-scout-gate-output.txt: Replace the Step 5 pre-scouted copy path with `scout filter-manifest --mode review` (or shared `validate_dynamic_manifest`) and base `pre_scouted_filtered_to_zero` on filter input/output counts, not `_valid_dynamic_archetype` stripping.


### FINDING_10: missing test that producer-scout warning sentinel prevents duplicate Warnings
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test asserts that the `.producer-scout-warning-logged` sentinel prevents duplicate Warnings across repeated `dispatch_panel` calls. A second review round or redispatch could append duplicate producer-failure bullets, breaking the one-warning-per-run contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Pre-seed `.producer-scout-warning-logged` and assert `append-entry` is not called again on `producer-missing`/`producer-invalid`.


### FINDING_13: final_report mislabels self-review runs as pre-scouted-empty
- **Reviewer(s)**: dyn-dyn-summary-line-output.txt
- **Severity**: important
- **Concern**: `_dynamic_archetypes_line` can emit `static-only, pre-scouted-empty` from Step 2 producer artifacts alone (`SCOUT_CODER_STATUS=ok`, empty `scout-coder-manifest.json`) when no `round-*/scout-round*-status.env` exists. That happens on `--self-review` runs, which skip `review-and-fix step5` / `dispatch_panel` and never set round `SCOUT_STATUS=pre-scouted-empty`. The final summary then claims Step 5 consumed an intentional empty pre-scouted manifest when no panel scout path ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-summary-line-output.txt: Reserve `pre-scouted-empty` for round status `pre-scouted-empty` (or an equivalent round file). When `_first_round_scout_status` is empty, use producer-only wording (e.g. `static-only, producer empty` or `ok (0)`), or emit `N/A` / omit the line when `SELF_REVIEW_REQUESTED=true` in session env.


### FINDING_15: final_report lets stale Step 2 sidecar override round-1 pre-scouted truth
- **Reviewer(s)**: dyn-dyn-summary-line-output.txt
- **Severity**: important
- **Concern**: Round-1 truth is only preferred over Step 2 sidecar state when the status file is missing. If `step2-scout-coder-status.env` exists with empty or non-`ok` `SCOUT_CODER_STATUS`, the function returns `unknown` or `static-only, producer missing-or-invalid` before the `round_status == "pre-scouted"` branch. A stale or partial Step 2 sidecar can misreport a run whose round-1 status/env show successful `pre-scouted` consumption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-summary-line-output.txt: After loading round status, if round status is `pre-scouted` or `pre-scouted-empty`, derive the line from round manifest/count (and round token) first; use Step 2 sidecar only as fallback or for producer-missing/invalid when round status agrees.


