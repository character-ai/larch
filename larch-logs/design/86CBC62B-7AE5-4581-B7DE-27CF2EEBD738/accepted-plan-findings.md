### FINDING_1: Oversized cap=1 test retargets the wrong module
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Item 3 is aimed at a `cap=1` rollup/summarization invariant, but the plan points the work at `python/tests/review/test_plan_review.py`, which has no oversized-filing coverage. The actual oversized/multi-part split and cap=1 rollup tests live in `python/tests/issue/test_oos_filer.py`, so the current retarget risks a no-op or unrelated churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Move the item 3 test work to python/tests/issue/test_oos_filer.py: tighten or rename the cap=1 rollup test (test_capped_oversized_rollup_files_one_summarized_issue / test_cap_one_oversized_single_item_is_summarized_without_split) and drop the unrelated multi-part split assertion from the misleading test; remove the test_plan_review.py oversized-filing bullet.
  - From Cursor-Innovation: Move item 3 to python/tests/issue/test_oos_filer.py: tighten/rename the cap=1 summarization test and keep multi-part split coverage explicitly scoped to OOS_ISSUES_PER_RUN_CAP=99 (or drop the misleading docstring). Remove the misplaced test_plan_review.py oversized retarget.
  - From Cursor-Pragmatic: Point Item 3 at python/tests/issue/test_oos_filer.py: rename or tighten test_body_files_for_item_oversized_body_is_split docstring/scope so it no longer reads like the cap=1 rollup invariant test, and reference the existing cap=1 rollup tests as the authoritative coverage. Drop the test_plan_review.py oversized retarget.


### FINDING_2: Missing design-side one-YES OOS acceptance assertion
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan lacks a focused test proving that a two-judge OOS tally with exactly one YES is accepted into `oos-accepted-design.md`. Existing tally coverage exercises OOS voting, but it does not assert the accepted design-side sink contents, so `accept_oos` regressions on the design path could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a focused plan-review tally test (2 voters, OOS item with YES/NO split, eligible=2) that asserts the item is accepted and its body appears in oos-accepted-design.md, not only in voting-tally.md or classification TSV.
  - From Cursor-Innovation: Add an explicit approach item and `test_plan_review.py` coverage: two-judge tally with `OOS_*` receiving exactly one YES, assert the block lands in `oos-accepted-design.md` (not only `oos.md` or the scoreboard).
  - From Cursor-Pragmatic: Add an explicit plan step and test_plan_review.py change: extend or add a two-judge OOS tally test that asserts the one-YES OOS block is written to oos-accepted-design.md (and classification Result=accepted), guarding accept_oos regressions on the design path.


### FINDING_4: Checkpoint harness still hard-codes rc=2 for the security sidecar case
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The bash regression harness for `skills/implement/scripts/test-oos-disposition-gate.sh` still asserts the old `rc=2` / validation-failure behavior for the security-sidecar-only case. If the checkpoint change returns `rc=3` with distinct logging, the harness will fail until it is updated in lockstep, and it will continue documenting the old contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update test-oos-disposition-gate.sh (and its .md contract if needed) for the rc=3 security-sidecar-present path: expect exit 3, keep mixed public-plus-sidecar cases on rc=2 when non-security disposition is unresolved, and align stderr/execution-issues assertions with the new distinct log entry from disposition_checkpoint_main.
  - From Cursor-Innovation: Add `skills/implement/scripts/test-oos-disposition-gate.sh` (and its `.md` sibling if present) to **Files to modify/create**, update the security-sidecar case to expect rc=3 with the new log text, and add a mixed public+security case that still returns rc=2 when non-security filing evidence is missing.
  - From Cursor-Pragmatic: Update the security-sidecar checkpoint case to expect rc=3 and the new log message, or add a parallel mixed-case case; list skills/implement/scripts/test-oos-disposition-gate.sh under Files to modify if residual bash stays authoritative.


