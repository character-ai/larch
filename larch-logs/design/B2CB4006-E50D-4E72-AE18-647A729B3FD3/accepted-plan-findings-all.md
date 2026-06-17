### FINDING_1: `test-classify-bump` evades partition guard via `files[0]` attribution
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-partition-guard-auditor, Cursor-dyn-shard-membership-auditor
- **Severity**: blocking
- **Concern**: `test-classify-bump` still runs full `python/test_release.py` outside the partition guard. `extract_pytest()` only attributes multi-file recipes to `files[0]` (`scripts/lint-harness-pytest-partition.py:128`), so adding `test_release.py` to `ENFORCED` can pass while `test-classify-bump` still re-runs the entire file (5th full-file payment), defeating the Bucket-1 CI win and creating a false ENFORCED sign-off.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Before adding `python/test_release.py` to `ENFORCED`, change `test-classify-bump` to invoke only `python/test_version_bump.py` (or a version_bump-only `-k` slice); do not extend the guard for multi-file recipes
  - From Cursor-Innovation: Change test-classify-bump to pytest python/test_version_bump.py only; route any still-needed verify_main coverage into sliced test_release.py targets; do not extend the guard for multi-file recipes
  - From Cursor-Pragmatic: Make the recipe change mandatory acceptance criteria: `test-classify-bump` runs only `python/test_version_bump.py` (or an explicit disjoint `-k` slice), never the whole `python/test_release.py`; re-run `python3 scripts/lint-harness-pytest-partition.py` and grep the Makefile for any remaining full-file `python/test_release.py` invocations outside the partitioned target set before adding it to `ENFORCED`
  - From Cursor-dyn-partition-guard-auditor: Make the classify-bump fix mandatory before `ENFORCED`: change the recipe to `python3 -m pytest python/test_version_bump.py -q -k classify` (or equivalent version_bump-only slice). Do not rely on extending the guard for multi-file recipes unless that extension is implemented and tested in the same PR
  - From Cursor-dyn-shard-membership-auditor: Add an explicit acceptance step: grep or inspect test-classify-bump recipe confirms python/test_release.py is absent (or split into a version_bump-only target); do not rely on scripts/lint-harness-pytest-partition.py alone to catch a leftover second file


### FINDING_5: Retirement instructions omit deleting retired Makefile recipe blocks
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Retirement instructions omit deleting retired Makefile recipe blocks. A retired target removed only from shards and `.PHONY` remains a `test-*` recipe, so coverage reports missing from shards and the partition guard can still count its pytest selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: State that retiring a target means deleting its recipe block, or keep the target sliced and shard-bound


### FINDING_6: Retirement instructions omit `python/checks.py` direct callers
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Retirement instructions do not cover existing non-Makefile target callers. Several Bucket-1 targets are referenced by `python/checks.py` direct relevant-check rules (for example `test-step0b-router-flag-recovery`, `test-design-driver`, `test-render-final-summary`, `test-plan-review-panel`, `test-dispatch-plan-voters`, decompose targets, and plan-scout targets). If the implementation retires any referenced target but only removes it from shard lines and `.PHONY`, `python/cli.py checks relevant` can later run `make` with a deleted target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Pin the retirement rule: before deleting any target, update or preserve references in python/checks.py, or do not retire targets named there.


### FINDING_9: `python/test_design_lifecycle.py` plan slices use nonexistent keyword families
- **Reviewer(s)**: Cursor-dyn-partition-guard-auditor
- **Severity**: important
- **Concern**: `python/test_design_lifecycle.py` plan slices reference `reentry` and `step0b`, but the file has only five tests: `test_phase_driver_*`, `test_design_read_result_env_cli_*`, `test_design_route_*`, `test_design_driver_*` (no `step0b` or `reentry` name families). Target names `test-design-reentry-guard` and `test-step0b-router-flag-recovery` are legacy labels for full-file reruns; slicing by nonexistent keywords risks uncovered tests or guard failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-partition-guard-auditor: Slice by actual test-name prefixes (`phase_driver`, `design_route`, `design_driver`, `design_read_result_env`) and retire/rename mislabeled targets; treat all four current targets as duplicates until sliced


### FINDING_12:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-harness-pytest-partition.py:95-131; Makefile:353-354; plan.txt:141
- **Concern**: [SCOPE-REDUCTION] Plan treats splitting test-classify-bump as a way to avoid a guard update, but the current extractor returns only the first pytest file selection. Scenario: The PR can split python/test_version_bump.py and python/test_release.py into separate commands under one target and still have the guard ignore the release selection, so python/test_release.py can be paid outside the enforced partition
- **Proposed resolution**: Remove the plain splitting option. Require either removing python/test_release.py from test-classify-bump, or updating the guard to enumerate all pytest file selections from a recipe


### FINDING_13:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: Makefile:926-927
- **Concern**: [SCOPE-REDUCTION] test-verify-run-log-completeness must not stay full-file once other test_run_logs.py targets are sliced. Scenario: Keeping env -u LARCH_VERIFY_MANIFEST on a full-file pytest while sibling targets use -k slices double-covers every node ID; lint-harness-pytest-partition.py will report overlap and block ENFORCED
- **Proposed resolution**: Narrow that target to the verify_completeness tests only (node IDs or -k verify_completeness) while preserving env -u LARCH_VERIFY_MANIFEST


### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: Makefile:test-classify-bump
- **Concern**: [SCOPE-REDUCTION] Plan allows slicing or a guard extension for test-classify-bump's test_release.py leg instead of requiring its removal. Scenario: extract_pytest() attributes multi-file recipes only to files[0], so test_release.py can keep paying duplicate runtime while ENFORCED reports a clean partition for dedicated test_release targets
- **Proposed resolution**: Classify-bump should invoke only python/test_version_bump.py; classify/idempotency coverage lives there and test_release.py only mocks classify_bump in release_prepare helpers


### FINDING_17:
- **Reviewer(s)**: Codex-dyn-partition-guard-auditor
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:129-141; Makefile:353-354; scripts/lint-harness-pytest-partition.py:95-131
- **Concern**: [SCOPE-REDUCTION] Plan leaves an optional guard parser change for test-classify-bump multi-file pytest even though the only Bucket-1 multi-file invocation is the existing test-classify-bump command. Scenario: Implementer may broaden extract_pytest to handle multi-file targets or split one target into multiple pytest commands, adding parser behavior beyond the Bucket-1 ENFORCED/docstring change and still risking hidden second-file coverage because current extract_pytest returns only files[0]
- **Proposed resolution**: Require the minimum path: remove python/test_release.py from test-classify-bump, or move any needed release selection to an existing release target. Update scripts/lint-harness-pytest-partition.py only for docstring and ENFORCED.




### FINDING_1: Retiring `test-render-final-summary-bash32` drops `issue_counts` / `plan_review_line` coverage
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan tells implementers to retire `test-render-final-summary-bash32` even though `python/test_render_final_summary.py` has three disjoint families (`render_final_summary`, `issue_counts`, `plan_review_line`) but only two Makefile targets. Slicing `test-render-final-summary` to `render_final_summary` and retiring `bash32` would leave eight `issue_counts` / `plan_review_line` tests uncovered, `ENFORCED` would fail, and shard 11 would lose that coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Slice in place: test-render-final-summary uses -k render_final_summary; test-render-final-summary-bash32 uses -k "issue_counts or plan_review_line" (or equivalent node IDs). Do not retire bash32 unless shard 11 gains another target that owns those tests


### FINDING_2: `verify_main` tests have no Makefile target owner
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan lists `verify_main` as its own slicing family, but there is no `verify_main` Makefile target; only `prepare`, `set-version`, `finish`, and `promote` exist. Six `test_verify_main_*` tests would have no named owner, and a partition that only slices the four obvious families would leave them uncovered and block `ENFORCED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add verify_main to the test-release-finish -k expression (for example release_finish or verify_main) and state that explicitly in the per-file audit


### FINDING_4: Per-file audit omits `test-capture-session-transcript` for `python/test_run_logs.py`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Generic
- **Severity**: blocking
- **Concern**: The per-file Makefile audit omits `test-capture-session-transcript` for `python/test_run_logs.py`. The issue scope and Makefile have eight full-file `test_run_logs.py` targets, but the plan lists only seven. If sibling targets are sliced but this one stays full-file, the partition guard reports overlap and blocks `ENFORCED`, or the target keeps paying full-file CI runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `test-capture-session-transcript` to the Bucket-1 audit list and slice it to the `capture_transcript` family (or absorb it into the catch-all with an explicit `-k`, not an unchanged full-file recipe)
  - From Cursor-Pragmatic: Add test-capture-session-transcript to the run_logs partition or retirement checklist, then slice it to the capture_transcript node(s) or retire it only after its coverage is absorbed
  - From Cursor-Requirements: Add `test-capture-session-transcript` to the `python/test_run_logs.py` target audit in the Makefile section and slice it per the existing `capture_transcript` family guidance (disjoint `-k` or node IDs plus catch-all)
  - From Codex-Generic: Add test-capture-session-transcript to the python/test_run_logs.py audit and slice or retire it, updating .PHONY and shard membership if retired


### FINDING_5: `make py-lint` / `make py-test` marked optional despite Python file change
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan marks `py-lint` and `py-test` optional even though it updates a Python file (`scripts/lint-harness-pytest-partition.py`). An implementer could ship without the repo’s required validation for a Python change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Make make py-lint and make py-test required final checks when scripts/lint-harness-pytest-partition.py changes, or document the actual failure if they cannot run


### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:353-354
- **Concern**: [SCOPE-REDUCTION] test-classify-bump narrows python/test_version_bump.py outside Bucket 1. Scenario: make lint currently gets python/test_version_bump.py coverage only through test-classify-bump; the planned -k classify drops non-classify version_bump tests while fixing an unrelated hidden python/test_release.py payment
- **Proposed resolution**: Remove python/test_release.py from the recipe, but keep python/test_version_bump.py as a full-file pytest invocation for this PR


### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:353-354; docs/linting.md:222
- **Concern**: [SCOPE-REDUCTION] Required test-classify-bump recipe narrows python/test_version_bump.py to -k classify. Scenario: Dropping non-classify version_bump tests from the only Makefile target that runs test_version_bump.py reduces existing make lint harness coverage while fixing release.py duplication
- **Proposed resolution**: Remove only python/test_release.py from the recipe; keep python/test_version_bump.py full-file or add an explicit replacement for excluded tests before narrowing




### FINDING_2: `test_design_lifecycle.py` slicing/retirement leaves coverage gaps
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan's `test_design_lifecycle.py` partition strategy has two coupled gaps. `python/checks.py` routes both `python/design_lifecycle.py` and `python/plan_quality.py` edits to `test-design-driver`, but the plan maps that target only to the `design_driver` family; slicing it down to one `design_driver` test would shrink `/implement` relevant-checks coverage for `plan_quality.py` changes from five lifecycle tests today to one, without any `checks.py` update. Separately, the plan allows retiring `test-lib-phase-driver` after "absorbing" tests, but `python/test_design_lifecycle.py` has only five tests across four Makefile targets; retiring `test-lib-phase-driver` without moving its two `phase_driver` tests leaves them uncovered and the partition guard fails before `ENFORCED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Slice `test-design-driver` to all `python/test_design_lifecycle.py` tests not owned by `test-step0b-router-flag-recovery`, not just `design_driver`; retire only the two non-checks duplicate targets (`test-design-reentry-guard`, `test-lib-phase-driver`)
  - From Cursor-Pragmatic: Prefer slice-in-place: keep `test-lib-phase-driver` with `-k phase_driver`. If retiring, assign `-k phase_driver` to a surviving target and update shards before deleting the recipe


### FINDING_5: `ENFORCED` update vs partition-guard validation order contradicts
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan's `ENFORCED` update step and partition-guard validation order contradict each other. The guard only checks files already listed in `ENFORCED` (`scripts/lint-harness-pytest-partition.py:192`). Testing step 2 says run the guard for all nine Bucket-1 files, but the Files section says add them to `ENFORCED` only after acceptance checks pass. Running the guard before the `ENFORCED` edit validates the prior 15-file list only and can look green while the nine new files are still unvalidated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Reorder the workflow explicitly: finish Makefile slicing (including classify-bump and verify-completeness fixes), add all nine paths to `ENFORCED` and refresh the docstring, then run `python3 scripts/lint-harness-pytest-partition.py` and `make test-harness-shards-coverage`; drop the "only after acceptance checks pass" wording or redefine it as "after Makefile partitions are correct, before merge"




### FINDING_2: `python/checks.py` may not be updated for sliced-in-place targets
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan audits `python/checks.py` only before deleting targets, but several sliced-in-place targets are existing relevant-check targets. After the PR, checks run-relevant for `design_lifecycle.py`, `design_summary.py`, `plan_review_panel.py`, or `rendering.py` can run only one new slice and miss tests those same targets ran before.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Extend the plan to update python/checks.py for affected sliced files, for example route design_lifecycle to both lifecycle targets, design_summary to both summary targets, and plan_review_panel/rendering rules to include the panel dispatch slice or assign slices so listed targets still cover those paths


### FINDING_3: Deferred shard rebalance lacks a tracked follow-up issue
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan defers shard rebalancing but never creates or links the required tracked follow-up. Retiring and moving Bucket-1 targets changes shard timing; without a tracked `/rebalance-tests` issue, the approved deferred acceptance item can be lost after merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add an implementation step to create or link a GitHub issue for /rebalance-tests --kind harness after this lands, and record the issue number in the PR notes



### FINDING_5: `plan_quality.py` relevant-check mapping gap after `test-design-driver` partition
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan omits the `plan_quality` relevant-check expansion after partitioning `test-design-driver`. After `test-design-driver` becomes the non-`design_route` slice, a `python/plan_quality.py` edit still maps only to `test-design-driver` and no longer runs `test_design_route_merges_flags_for_already_planned`, despite the plan stating `plan_quality` keeps the former full-file lifecycle breadth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add `test-step0b-router-flag-recovery` to the `python/plan_quality.py` and `python/test_plan_quality.py` `_DIRECT_TARGET_RULES` entry, and update `python/test_checks.py` expectations for that mapping.



