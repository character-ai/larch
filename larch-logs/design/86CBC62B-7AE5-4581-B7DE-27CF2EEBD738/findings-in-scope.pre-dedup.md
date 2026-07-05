### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py
- **Concern**: Oversized cap=1 filing retarget is aimed at the wrong test module. Scenario: Issue item 3 targets the cap=1 rollup invariant, but the only oversized/multi-part filing tests live in python/tests/issue/test_oos_filer.py (for example test_body_files_for_item_oversized_body_is_split). test_plan_review.py has no oversized-filing test to retarget, so item 3 can ship as a no-op or unrelated churn.
- **Proposed resolution**: Move the item 3 test work to python/tests/issue/test_oos_filer.py: tighten or rename the cap=1 rollup test (test_capped_oversized_rollup_files_one_summarized_issue / test_cap_one_oversized_single_item_is_summarized_without_split) and drop the unrelated multi-part split assertion from the misleading test; remove the test_plan_review.py oversized-filing bullet.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py
- **Concern**: Plan omits the explicit two-judge one-YES OOS acceptance assertion on oos-accepted-design.md. Scenario: Issue item 6 requires proving design-side accept_oos at eligible=2 with one YES lands in oos-accepted-design.md. Existing plan-review tally tests exercise OOS votes but do not assert that a 2-judge 1-YES accepted OOS block is written to oos-accepted-design.md, so accept_oos can regress with only implement-side coverage.
- **Proposed resolution**: Add a focused plan-review tally test (2 voters, OOS item with YES/NO split, eligible=2) that asserts the item is accepted and its body appears in oos-accepted-design.md, not only in voting-tally.md or classification TSV.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-oos-disposition-gate.sh:979-997
- **Concern**: rc=3 security-sidecar checkpoint contract is not reflected in the bash regression harness. Scenario: Item 6 changes security-only sidecar checkpoints from rc=2 to rc=3 with distinct logging. The harness still asserts exit 2 and the old validation-failure message, so the implementation will fail make test-oos-disposition-gate unless the script is updated in the same change.
- **Proposed resolution**: Update test-oos-disposition-gate.sh (and its .md contract if needed) for the rc=3 security-sidecar-present path: expect exit 3, keep mixed public-plus-sidecar cases on rc=2 when non-security disposition is unresolved, and align stderr/execution-issues assertions with the new distinct log entry from disposition_checkpoint_main.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py
- **Concern**: Issue item 6 (two-judge one-YES OOS acceptance) is absent from the plan. Scenario: The binding scope requires asserting that a design tally with two eligible judges and one YES accepts OOS into `oos-accepted-design.md`. The plan never adds this step or test, so an `accept_oos` regression on the design path can ship while implement-only coverage still passes.
- **Proposed resolution**: Add an explicit approach item and `test_plan_review.py` coverage: two-judge tally with `OOS_*` receiving exactly one YES, assert the block lands in `oos-accepted-design.md` (not only `oos.md` or the scoreboard).



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py
- **Concern**: Oversized cap=1 test retarget is aimed at the wrong module. Scenario: Item 3 targets the `cap=1` rollup/summarization invariant, but the plan places that work under `test_plan_review.py`, which has no oversized-filing tests. The real `cap=1` and multi-part split surfaces live in `python/tests/issue/test_oos_filer.py` (`test_capped_oversized_rollup_files_one_summarized_issue`, `test_body_files_for_item_oversized_body_is_split`). Implementing the plan as written risks a no-op or wrong-file edit and leaves item 3 undelivered.
- **Proposed resolution**: Move item 3 to `python/tests/issue/test_oos_filer.py`: tighten/rename the `cap=1` summarization test and keep multi-part split coverage explicitly scoped to `OOS_ISSUES_PER_RUN_CAP=99` (or drop the misleading docstring). Remove the misplaced `test_plan_review.py` oversized-filing bullet.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-oos-disposition-gate.sh
- **Concern**: Checkpoint rc=3 contract change is missing from the bash regression harness. Scenario: `disposition_checkpoint_main` will return rc=3 when only the security sidecar remains, but `test-oos-disposition-gate.sh` still asserts rc=2 for the security-sidecar case (lines 979-990). CI will fail after the Python change, and the harness will keep documenting the old halt semantics.
- **Proposed resolution**: Add `skills/implement/scripts/test-oos-disposition-gate.sh` (and its `.md` sibling if present) to **Files to modify/create**, update the security-sidecar case to expect rc=3 with the new log text, and add a mixed public+security case that still returns rc=2 when non-security filing evidence is missing.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/oos_filer.py
- **Concern**: `_after_checkpoint` still treats any non-zero checkpoint as hard failure. Scenario: Today `_after_checkpoint` maps every `checkpoint.returncode != 0` to `status=disposition_checkpoint_failed` (lines 414-427). Without the planned rc=3 branch, `cmd_file` cannot emit `status=security_sidecar_present` even after `disposition_checkpoint_main` is fixed, and `dispatch_ship.py` will keep routing mixed runs to `halt-oos`.
- **Proposed resolution**: The plan item 7 intent is right; make the `_after_checkpoint` rc=3 mapping an explicit approach sub-step (distinct stderr message, `step9a1_stamped=False`, run statistics when URLs exist) so it is not lost during implementation.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py
- **Concern**: Feature Item 6 (two-judge OOS one-YES acceptance on oos-accepted-design.md) is absent from the plan. Scenario: The binding scope requires asserting that a degraded two-judge panel accepts OOS with a single YES into oos-accepted-design.md (accept_oos with eligible=2). The plan renumbers items and never adds this assertion; test_tally_plan_review_degraded_two_judge_voter_agreement_parity already drives OOS_1 YES/NO on two judges but checks only scoreboard parity, not oos-accepted-design.md content.
- **Proposed resolution**: Add an explicit plan step and test_plan_review.py change: extend or add a two-judge OOS tally test that asserts the one-YES OOS block is written to oos-accepted-design.md (and classification Result=accepted), guarding accept_oos regressions on the design path.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/issue/test_oos_filer.py:865-880
- **Concern**: Feature Item 3 oversized-filing cleanup targets the wrong test module. Scenario: The plan retargets an oversized cap=1 test in test_plan_review.py, but that file has no oversized or cap=1 filing tests. The misleading multi-part split coverage lives in test_oos_filer.py (test_body_files_for_item_oversized_body_is_split); cap=1 rollup invariants are already in test_capped_oversized_rollup_files_one_summarized_issue and test_cap_one_oversized_single_item_is_summarized_without_split. Retargeting test_plan_review.py is a no-op for Item 3.
- **Proposed resolution**: Point Item 3 at python/tests/issue/test_oos_filer.py: rename or tighten test_body_files_for_item_oversized_body_is_split docstring/scope so it no longer reads like the cap=1 rollup invariant test, and reference the existing cap=1 rollup tests as the authoritative coverage. Drop the test_plan_review.py oversized retarget.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/issue/test_oos.py:252-260
- **Concern**: Plan omits required updates to serialization fixtures that assume no-tally eligibility. Scenario: Item 3 changes _is_vote_tally_eligible to require Vote tally: with Result=accepted. test_oos_serialize_prose_result_not_rejected and test_oos_serialize_result_token_boundaries still expect blocks without an accepted Vote tally line to serialize. Implementing without updating these fixtures will fail pytest or silently miss the tightened contract.
- **Proposed resolution**: Expand the test_oos.py update step to explicitly revise test_oos_serialize_prose_result_not_rejected, test_oos_serialize_result_token_boundaries, and any similar fixtures, plus add the planned no-tally regression.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-oos-disposition-gate.sh:979-997
- **Concern**: Residual checkpoint harness still hard-codes security-sidecar rc=2. Scenario: The bash harness (still listed in scripts/residual-bash-paths.txt) asserts disposition-checkpoint exits 2 when only security-oos-observations.md is present. After Item 6 introduces rc=3 for cleared non-security with a remaining sidecar, this case becomes rc=3 with new stderr semantics; the script will fail if run even though Makefile now delegates test-oos-disposition-gate to pytest.
- **Proposed resolution**: Update the security-sidecar checkpoint case to expect rc=3 and the new log message, or add a parallel mixed-case case; list skills/implement/scripts/test-oos-disposition-gate.sh under Files to modify if residual bash stays authoritative. schema_version scope severity focus_area location what scenario_or_breakage suggested_fix



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py
- **Concern**: Feature Item 6 (two-judge OOS one-YES acceptance on oos-accepted-design.md) is absent from the plan. Scenario: The binding scope requires asserting that a degraded two-judge panel accepts OOS with a single YES into oos-accepted-design.md (accept_oos with eligible=2). The plan renumbers items and never adds this assertion; test_tally_plan_review_degraded_two_judge_voter_agreement_parity already drives OOS_1 YES/NO on two judges but checks only scoreboard parity, not oos-accepted-design.md content.
- **Proposed resolution**: Add an explicit plan step and test_plan_review.py change: extend or add a two-judge OOS tally test that asserts the one-YES OOS block is written to oos-accepted-design.md (and classification Result=accepted), guarding accept_oos regressions on the design path.



### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/issue/test_oos_filer.py:865-880
- **Concern**: Feature Item 3 oversized-filing cleanup targets the wrong test module. Scenario: The plan retargets an oversized cap=1 test in test_plan_review.py, but that file has no oversized or cap=1 filing tests. The misleading multi-part split coverage lives in test_oos_filer.py (test_body_files_for_item_oversized_body_is_split); cap=1 rollup invariants are already in test_capped_oversized_rollup_files_one_summarized_issue and test_cap_one_oversized_single_item_is_summarized_without_split. Retargeting test_plan_review.py is a no-op for Item 3.
- **Proposed resolution**: Point Item 3 at python/tests/issue/test_oos_filer.py: rename or tighten test_body_files_for_item_oversized_body_is_split docstring/scope so it no longer reads like the cap=1 rollup invariant test, and reference the existing cap=1 rollup tests as the authoritative coverage. Drop the test_plan_review.py oversized retarget.



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/issue/test_oos.py:252-260
- **Concern**: Plan omits required updates to serialization fixtures that assume no-tally eligibility. Scenario: Item 3 changes _is_vote_tally_eligible to require Vote tally: with Result=accepted. test_oos_serialize_prose_result_not_rejected and test_oos_serialize_result_token_boundaries still expect blocks without an accepted Vote tally line to serialize. Implementing without updating these fixtures will fail pytest or silently miss the tightened contract.
- **Proposed resolution**: Expand the test_oos.py update step to explicitly revise test_oos_serialize_prose_result_not_rejected, test_oos_serialize_result_token_boundaries, and any similar fixtures, plus add the planned no-tally regression.



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-oos-disposition-gate.sh:979-997
- **Concern**: Residual checkpoint harness still hard-codes security-sidecar rc=2. Scenario: The bash harness (still listed in scripts/residual-bash-paths.txt) asserts disposition-checkpoint exits 2 when only security-oos-observations.md is present. After Item 6 introduces rc=3 for cleared non-security with a remaining sidecar, this case becomes rc=3 with new stderr semantics; the script will fail if run even though Makefile now delegates test-oos-disposition-gate to pytest.
- **Proposed resolution**: Update the security-sidecar checkpoint case to expect rc=3 and the new log message, or add a parallel mixed-case case; list skills/implement/scripts/test-oos-disposition-gate.sh under Files to modify if residual bash stays authoritative.



