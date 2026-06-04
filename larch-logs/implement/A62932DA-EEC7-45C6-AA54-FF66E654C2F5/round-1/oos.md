### FINDING_5: [OUT_OF_SCOPE] **Part A** — `assert_gate_b_bypass_branch_sentinels` now iterates all 7 branches; per-branch awk finds a single line containing both the token and the literal `: > "$DESIGN_TMPDIR/.completed/step-3"` sentinel write; all four literals are checked via glob. Confirmed against real SKILL.md lines 1114–1132: all branches embed the full quad on one line. ✓
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Part A** — `assert_gate_b_bypass_branch_sentinels` now iterates all 7 branches; per-branch awk finds a single line containing both the token and the literal `: > "$DESIGN_TMPDIR/.completed/step-3"` sentinel write; all four literals are checked via glob. Confirmed against real SKILL.md lines 1114–1132: all branches embed the full quad on one line. ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] **Part A negative self-tests** — `run_gate_b_bypass_branch_sentinel_self_tests` runs before the live `assert_gate_b_bypass_branch_sentinels "$SKILL_MD"` call; fixture covers all 7 branches; tally-error and panel-failed have step-3.5 excised; subshell isolation correctly exercises `fail()` = `exit 1`. ✓
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Part A negative self-tests** — `run_gate_b_bypass_branch_sentinel_self_tests` runs before the live `assert_gate_b_bypass_branch_sentinels "$SKILL_MD"` call; fixture covers all 7 branches; tally-error and panel-failed have step-3.5 excised; subshell isolation correctly exercises `fail()` = `exit 1`. ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] **Part B.1** — SKILL.md Step 3b bash fence gets `${REPO:+--repo "$REPO"}`; `assert_step3b_entry_guard_threads_repo` correctly slices the `<!-- step:3b` … `<!-- step:4 ` region and finds the first pause-save guard line. ✓
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Part B.1** — SKILL.md Step 3b bash fence gets `${REPO:+--repo "$REPO"}`; `assert_step3b_entry_guard_threads_repo` correctly slices the `<!-- step:3b` … `<!-- step:4 ` region and finds the first pause-save guard line. ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] **Part B.2** — `_postplan_resolve_repo` uses identical safe awk-only extraction pattern as `_postplan_resolve_issue`; `_postplan_pause_checkpoint` threads `${_repo:+--repo "$_repo"}`. ✓
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Part B.2** — `_postplan_resolve_repo` uses identical safe awk-only extraction pattern as `_postplan_resolve_issue`; `_postplan_pause_checkpoint` threads `${_repo:+--repo "$_repo"}`. ✓
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] **Part B.3** — `_classification_warn_count_before` captured before the stderr-read loop; synthetic WARN appended only when count is unchanged after loop; test D2d_silent_nonzero stubs the helper to `exit 9` with empty stderr and asserts WARN= present and SNAPSHOT_STATUS=taken (HARD). ✓
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Part B.3** — `_classification_warn_count_before` captured before the stderr-read loop; synthetic WARN appended only when count is unchanged after loop; test D2d_silent_nonzero stubs the helper to `exit 9` with empty stderr and asserts WARN= present and SNAPSHOT_STATUS=taken (HARD). ✓ ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	nit	correctness	scripts/test-design-structure.sh:216	write_gate_b_bypass_fixture step35 value starts with ", and " producing double-and connector in fixture prose	Cosmetic only — fixture line reads "plus `: > step-3"`, and `: > step-3.5"`, and `: > step-3.6"`. Assertions use substring matching so no test failure, but the generated prose is grammatically irregular vs real SKILL.md format	Change step35 to ', `: > "$DESIGN_TMPDIR/.completed/step-3.5"`' (leading comma, no "and") to match SKILL.md list style ```
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

