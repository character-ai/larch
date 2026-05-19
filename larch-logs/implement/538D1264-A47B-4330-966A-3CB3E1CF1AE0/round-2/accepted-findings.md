### FINDING_1: **Nit** `code-quality` `skills/review/scripts/dispatch-panel.md:13`, `skills/review/scripts/dispatch-panel.sh:279-280`: the contract says suppression happens when `REVIEW_TMPDIR` “or the manifest path” is under a harness ancestor, but the implementation now only checks `REVIEW_TMPDIR`. Update the doc to remove “or the manifest path,” or restore the manifest-path check if that behavior is still intended.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `skills/review/scripts/dispatch-panel.md:13`, `skills/review/scripts/dispatch-panel.sh:279-280`: the contract says suppression happens when `REVIEW_TMPDIR` “or the manifest path” is under a harness ancestor, but the implementation now only checks `REVIEW_TMPDIR`. Update the doc to remove “or the manifest path,” or restore the manifest-path check if that behavior is still intended.
- **Suggested revision**: Address the concern above.


### FINDING_10: code-quality: skills/review/scripts/dispatch-panel.md:18-19
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc says suppression applies when REVIEW_TMPDIR or manifest path is under harness patterns; code only checks REVIEW_TMPDIR. Readers may rely on manifest-path gating that never happens. Update contract to match code or implement manifest-path check if required.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/review/scripts/dispatch-panel.md:13;skills/review/scripts/dispatch-panel.sh:267-281
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Doc claims manifest path triggers suppression; code only checks REVIEW_TMPDIR REVIEW_TMPDIR outside harness patterns but SCOUT_MANIFEST path under harness would still append per code while operators expect suppression per doc Align doc to code or extend should_suppress to consider SCOUT_MANIFEST path
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/review/scripts/dispatch-panel.md:13;skills/review/scripts/dispatch-panel.sh:267-281
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Contract claims append is suppressed when REVIEW_TMPDIR or manifest path is under harness patterns but code only tests REVIEW_TMPDIR. A maintainer or test author relying on the documented manifest-path branch expects suppression when only SCOUT_MANIFEST matches harness patterns; implementation would still append to the parent execution-issues log. Align the contract with the code or extend should_suppress to OR is_harness_scout_path on the resolved manifest path when non-empty.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/review/scripts/dispatch-panel.sh:267-275
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Path heuristic may treat non-harness dirs as harness Production REVIEW_TMPDIR containing a segment like test-scout-experiment matches */test-scout-* and suppresses real parse-failed warnings Tighten detection or use explicit harness env from test scripts
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/review/scripts/dispatch-panel.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] dispatch-panel_contract_mentions_manifest_path_guard_but_code_only_checks_REVIEW_TMPDIR readers_expect_manifest-based_suppression_that_never_happens Align_doc_to_code_or_implement_manifest_path_check
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: skills/review/scripts/dispatch-panel.md:13
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc says guard uses REVIEW_TMPDIR or manifest path; code only checks REVIEW_TMPDIR Readers may assume manifest-only paths trigger suppression when they do not Align documentation with should_suppress implementation or add manifest check if required
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/review/scripts/test-dispatch-panel.sh:212-232
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] dynamic-parse-failed-warn no longer exercises append failure WARN path No test asserts WARN=append-execution-issue failed after harness suppression; append failure handling can regress undetected Add prod-tmpdir (non-harness) case with read-only LARCH_EXECUTION_ISSUES_LOG to assert WARN line still emitted
- **Suggested revision**: Address the concern above.


### FINDING_2: **Nit** `code-quality` `skills/review/scripts/test-dispatch-panel.sh:203-216`, `skills/review/scripts/test-dispatch-panel.sh:551-575`: the old append-failure warning assertion now only verifies harness suppression, while the production-shaped regression covers only successful issue-log append. Add a production-shaped append-failure case so `dispatch-panel.sh:309-317` stays covered.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `skills/review/scripts/test-dispatch-panel.sh:203-216`, `skills/review/scripts/test-dispatch-panel.sh:551-575`: the old append-failure warning assertion now only verifies harness suppression, while the production-shaped regression covers only successful issue-log append. Add a production-shaped append-failure case so `dispatch-panel.sh:309-317` stays covered.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: skills/review/scripts/test-dispatch-panel.sh:455-494;Makefile:490-497
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] assert_emit_tally_panel moved inside second section_runs core so reuse and limits Makefile shards skip emit-tally assertions that ran unconditionally on main. make test-dispatch-panel-reuse and make test-dispatch-panel-limits no longer exercise emit-tally panel JSON invariants; regressions in emit-tally integration can ship undetected. Keep assert_emit_tally_panel unconditional after section blocks; wrap only the three new scout regressions in section_runs core.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: skills/review/scripts/test-dispatch-panel.sh:457-578
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] emit-tally regression checks gated behind section core only Makefile targets test-dispatch-panel-reuse and test-dispatch-panel-limits run --section reuse or limits and no longer execute assert_emit_tally_panel; shard can pass without emit-tally or review-summary.json coverage that main still ran Move assert_emit_tally_panel definition and three calls after all section blocks; keep only the three new scout regressions inside section core
- **Suggested revision**: Address the concern above.


### FINDING_22: risk-integration: skills/review/scripts/test-dispatch-panel.sh:457-578
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] emit_tally_panel_and_new_regressions_wrapped_in_second_section_runs_core Makefile_shards_test-dispatch-panel-reuse_and_test-dispatch-panel-limits_no_longer_run_emit-tally_assertions_that_ran_unconditionally_on_main emit-tally_regression_can_miss_CI_until_core_shard_Move_emit-tally_outside_section_gates_match_main
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: skills/review/scripts/test-dispatch-panel.sh:457-578
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] emit-tally checks moved inside section_runs core make test-dispatch-panel-reuse and make test-dispatch-panel-limits skip emit-tally assertions that ran unconditionally on main; emit-tally regressions can miss CI until full harness runs Move assert_emit_tally_panel block outside section guards or add per-shard emit-tally smoke
- **Suggested revision**: Address the concern above.


### FINDING_24: security: skills/review/scripts/dispatch-panel.sh:267-281
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Path-pattern suppression of scout parse-failed execution-issues append based only on REVIEW_TMPDIR string. A production or shared-environment review tmpdir whose path includes a matching segment (e.g. a checkout or workdir named like test-scout-* or test-dispatch-panel.*) would not record the parse-failed warning in execution-issues.md, hiding scout failures from the normal issues log. Use an explicit harness-only flag or marker file written by test entrypoints; avoid inferring harness from path substrings.
- **Suggested revision**: Address the concern above.


### FINDING_3: **correctness** — [`skills/review/scripts/dispatch-panel.md:13`](skills/review/scripts/dispatch-panel.md) vs [`skills/review/scripts/dispatch-panel.sh:279-281`](skills/review/scripts/dispatch-panel.sh): The contract text says suppression applies when `REVIEW_TMPDIR` **or the manifest path** is under a harness ancestor, but `should_suppress_scout_parse_issue_append` only passes `REVIEW_TMPDIR` into `is_harness_scout_path`. If `SCOUT_MANIFEST` could ever point outside `REVIEW_TMPDIR` while `REVIEW_TMPDIR` did not match the harness pattern, behavior would not match the doc (and the doc’s “manifest path” branch is unimplemented). **Suggested fix:** Either drop “manifest path” from the doc or also test `SCOUT_MANIFEST` (and any resolved path you care about) with the same guard.
- **Reviewer**: dyn-harness-isolation-output.txt
- **Concern**: - **correctness** — [`skills/review/scripts/dispatch-panel.md:13`](skills/review/scripts/dispatch-panel.md) vs [`skills/review/scripts/dispatch-panel.sh:279-281`](skills/review/scripts/dispatch-panel.sh): The contract text says suppression applies when `REVIEW_TMPDIR` **or the manifest path** is under a harness ancestor, but `should_suppress_scout_parse_issue_append` only passes `REVIEW_TMPDIR` into `is_harness_scout_path`. If `SCOUT_MANIFEST` could ever point outside `REVIEW_TMPDIR` while `REVIEW_TMPDIR` did not match the harness pattern, behavior would not match the doc (and the doc’s “manifest path” branch is unimplemented). **Suggested fix:** Either drop “manifest path” from the doc or also test `SCOUT_MANIFEST` (and any resolved path you care about) with the same guard.
- **Suggested revision**: Address the concern above.


### FINDING_4: **correctness** — [`skills/review/scripts/dispatch-panel.sh:267-276`](skills/review/scripts/dispatch-panel.sh): `case "$path" in */test-scout-*|…)` matches any path **segment** whose name begins with `test-scout-` after a `/` (e.g. a real checkout path such as `.../test-scout-smoke/review`). That would incorrectly suppress `append-execution-issue` for genuine `parse-failed` scouts in such a tree. **Suggested fix:** tie the pattern to known harness tmp prefixes only (e.g. `test-scout-dynamic-archetypes.*`) or use an explicit env sentinel set only by harnesses instead of substring path heuristics.
- **Reviewer**: dyn-harness-isolation-output.txt
- **Concern**: - **correctness** — [`skills/review/scripts/dispatch-panel.sh:267-276`](skills/review/scripts/dispatch-panel.sh): `case "$path" in */test-scout-*|…)` matches any path **segment** whose name begins with `test-scout-` after a `/` (e.g. a real checkout path such as `.../test-scout-smoke/review`). That would incorrectly suppress `append-execution-issue` for genuine `parse-failed` scouts in such a tree. **Suggested fix:** tie the pattern to known harness tmp prefixes only (e.g. `test-scout-dynamic-archetypes.*`) or use an explicit env sentinel set only by harnesses instead of substring path heuristics.
- **Suggested revision**: Address the concern above.


### FINDING_5: **correctness** — [`skills/review/scripts/test-dispatch-panel.sh:457-578`](skills/review/scripts/test-dispatch-panel.sh): `assert_emit_tally_panel` and the three new scout regressions are wrapped in a second `if section_runs core; then` … `fi`. On `main`, those `assert_emit_tally_panel` calls lived **after** all section `fi` blocks and ran on **every** shard (including `make test-dispatch-panel-limits` and `test-dispatch-panel-reuse`). With this branch, `test-dispatch-panel-limits` / `test-dispatch-panel-reuse` no longer run `emit-tally` JSON assertions or the new prod/env/path regressions, so CI coverage regresses relative to `main`. **Suggested fix:** keep the new regressions under `core` if you want, but leave `assert_emit_tally_panel` (and any checks that must hold for all shards) in an unconditional tail like `main`, or mirror the old “always run after sections” structure.
- **Reviewer**: dyn-harness-isolation-output.txt
- **Concern**: - **correctness** — [`skills/review/scripts/test-dispatch-panel.sh:457-578`](skills/review/scripts/test-dispatch-panel.sh): `assert_emit_tally_panel` and the three new scout regressions are wrapped in a second `if section_runs core; then` … `fi`. On `main`, those `assert_emit_tally_panel` calls lived **after** all section `fi` blocks and ran on **every** shard (including `make test-dispatch-panel-limits` and `test-dispatch-panel-reuse`). With this branch, `test-dispatch-panel-limits` / `test-dispatch-panel-reuse` no longer run `emit-tally` JSON assertions or the new prod/env/path regressions, so CI coverage regresses relative to `main`. **Suggested fix:** keep the new regressions under `core` if you want, but leave `assert_emit_tally_panel` (and any checks that must hold for all shards) in an unconditional tail like `main`, or mirror the old “always run after sections” structure.
- **Suggested revision**: Address the concern above.


### FINDING_9: architecture: skills/review/scripts/dispatch-panel.sh:267-281
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] path_substring_heuristic_for_harness_detection legitimate_REVIEW_TMPDIR_under_matching_dirnames_suppresses_real_parse-failed_execution-issues Use_explicit_env_sentinel_or_narrow_patterns_with_documented_risk
- **Suggested revision**: Address the concern above.


