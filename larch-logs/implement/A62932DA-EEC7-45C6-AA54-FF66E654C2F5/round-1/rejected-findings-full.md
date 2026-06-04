### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: **Nit** `code-quality` `skills/design/scripts/design-postplan-emit.sh:185-192` — `_postplan_resolve_repo` duplicates the 120-character awk one-liner (including the `BEGIN{q=sprintf("%c",39)}` quote-stripping logic) verbatim from `_postplan_resolve_issue` at line 176–183; only the variable name and the matched key differ. If the extraction pattern ever needs to change (e.g., to handle a third quoting form), both copies must be updated in sync. **Suggested fix:** Factor out a single `_postplan_extract_source_env_key` helper taking the key name as `$1`, and replace both callers with `_issue="$(_postplan_extract_source_env_key ISSUE_NUMBER)"` / `_repo="$(_postplan_extract_source_env_key REPO)"`.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Nit** `code-quality` `skills/design/scripts/design-postplan-emit.sh:185-192` — `_postplan_resolve_repo` duplicates the 120-character awk one-liner (including the `BEGIN{q=sprintf("%c",39)}` quote-stripping logic) verbatim from `_postplan_resolve_issue` at line 176–183; only the variable name and the matched key differ. If the extraction pattern ever needs to change (e.g., to handle a third quoting form), both copies must be updated in sync. **Suggested fix:** Factor out a single `_postplan_extract_source_env_key` helper taking the key name as `$1`, and replace both callers with `_issue="$(_postplan_extract_source_env_key ISSUE_NUMBER)"` / `_repo="$(_postplan_extract_source_env_key REPO)"`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: **Latent** · `risk-integration` · `scripts/test-design-structure.sh:211-246` — `run_gate_b_bypass_branch_sentinel_self_tests` cannot produce negative fixtures for the `cap-reached` / `skipped-cap-reached` pair. The `write_gate_b_bypass_fixture` helper hard-codes the cap-pair line as an always-complete `printf` (no missing-sentinel variant for `$2`/`$3`), so removing a sentinel from that combined line in SKILL.md would not be caught by CI self-tests. The plan explicitly allows "at least two non-`plan-size-trigger` branches," so this is within spec, but it leaves the only two-token combined line unguarded by negative self-test. **Suggested fix:** add a `cap_reached_missing` fixture variant that writes the combined cap line without `step-3.5` and asserts `assert_gate_b_bypass_branch_sentinels` fails; or note the gap in the self-test function comment.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Latent** · `risk-integration` · `scripts/test-design-structure.sh:211-246` — `run_gate_b_bypass_branch_sentinel_self_tests` cannot produce negative fixtures for the `cap-reached` / `skipped-cap-reached` pair. The `write_gate_b_bypass_fixture` helper hard-codes the cap-pair line as an always-complete `printf` (no missing-sentinel variant for `$2`/`$3`), so removing a sentinel from that combined line in SKILL.md would not be caught by CI self-tests. The plan explicitly allows "at least two non-`plan-size-trigger` branches," so this is within spec, but it leaves the only two-token combined line unguarded by negative self-test. **Suggested fix:** add a `cap_reached_missing` fixture variant that writes the combined cap line without `step-3.5` and asserts `assert_gate_b_bypass_branch_sentinels` fails; or note the gap in the self-test function comment.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: **Nit** · `risk-integration` · `scripts/test-design-structure.sh:133-143` — `assert_step3b_entry_guard_threads_repo` is invoked in the main harness body (line 643) but has no self-test proving it fails when the Step 3b guard lacks `${REPO:+--repo "$REPO"}`. Every other structural assertion in this harness (`assert_thin_fence`, `assert_gate_b_bypass_branch_sentinels`) has a corresponding negative fixture via `run_*_self_tests`. **Suggested fix:** add a `run_step3b_entry_guard_threads_repo_self_tests` that builds a fixture with the guard missing REPO and verifies the assertion returns non-zero.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **Nit** · `risk-integration` · `scripts/test-design-structure.sh:133-143` — `assert_step3b_entry_guard_threads_repo` is invoked in the main harness body (line 643) but has no self-test proving it fails when the Step 3b guard lacks `${REPO:+--repo "$REPO"}`. Every other structural assertion in this harness (`assert_thin_fence`, `assert_gate_b_bypass_branch_sentinels`) has a corresponding negative fixture via `run_*_self_tests`. **Suggested fix:** add a `run_step3b_entry_guard_threads_repo_self_tests` that builds a fixture with the guard missing REPO and verifies the assertion returns non-zero.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: **Nit** · `risk-integration` · `skills/design/scripts/test-design-postplan-emit.sh:622-638` — the `D2d_silent_nonzero` test verifies the HARD default indirectly via `SNAPSHOT_STATUS=taken` rather than directly asserting `WORKFLOW_PATH=HARD` in the result env (the result env doesn't surface `WORKFLOW_PATH`). The indirect check is sound since snapshot=taken ↔ HARD+snapshot-original, but a future refactor that adds `WORKFLOW_PATH` to the result-env allowlist would make the assertion more explicit. **Suggested fix:** no action required; note left here for future strengthening.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **Nit** · `risk-integration` · `skills/design/scripts/test-design-postplan-emit.sh:622-638` — the `D2d_silent_nonzero` test verifies the HARD default indirectly via `SNAPSHOT_STATUS=taken` rather than directly asserting `WORKFLOW_PATH=HARD` in the result env (the result env doesn't surface `WORKFLOW_PATH`). The indirect check is sound since snapshot=taken ↔ HARD+snapshot-original, but a future refactor that adds `WORKFLOW_PATH` to the result-env allowlist would make the assertion more explicit. **Suggested fix:** no action required; note left here for future strengthening.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: **security** `skills/design/scripts/design-postplan-emit.sh:205` — **Nit** — The `${_repo:+--repo "$_repo"}` expansion is unquoted in the `exec` call, meaning the result undergoes word splitting before exec receives the arguments. A REPO value containing whitespace (e.g., `owner/repo name`) would be split into multiple arguments, potentially injecting unexpected flags into `design-pause-save.sh`. In practice this is safe because `write-design-current-env.sh:114–117` validates REPO against `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$` at write time; and the same unquoted pattern was already present in `skills/design/SKILL.md` Step 3.6 and Step 3b. However, the read site (`_postplan_resolve_repo`) carries no matching validation, so a source-env.sh written outside the normal write path could inject extra arguments. **Suggested fix:** Either add a read-side guard (`[[ "$_repo" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]` before use, bailing on mismatch) to enforce the same invariant the write side assumes, or quote the expansion using an array: `set -- "$@" ${_repo:+--repo "$_repo"}` with proper quoting — this is consistent with the `${REPO:+--repo "$REPO"}` idiom already audited in SKILL.md and needs no structural change to the established pattern.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/design/scripts/design-postplan-emit.sh:205` — **Nit** — The `${_repo:+--repo "$_repo"}` expansion is unquoted in the `exec` call, meaning the result undergoes word splitting before exec receives the arguments. A REPO value containing whitespace (e.g., `owner/repo name`) would be split into multiple arguments, potentially injecting unexpected flags into `design-pause-save.sh`. In practice this is safe because `write-design-current-env.sh:114–117` validates REPO against `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$` at write time; and the same unquoted pattern was already present in `skills/design/SKILL.md` Step 3.6 and Step 3b. However, the read site (`_postplan_resolve_repo`) carries no matching validation, so a source-env.sh written outside the normal write path could inject extra arguments. **Suggested fix:** Either add a read-side guard (`[[ "$_repo" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]` before use, bailing on mismatch) to enforce the same invariant the write side assumes, or quote the expansion using an array: `set -- "$@" ${_repo:+--repo "$_repo"}` with proper quoting — this is consistent with the `${REPO:+--repo "$REPO"}` idiom already audited in SKILL.md and needs no structural change to the established pattern. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: **correctness** `scripts/test-design-structure.sh:162-176` (`write_gate_b_bypass_fixture`) — The fixture helper can only produce missing-step-3.5 negative cases for the five branches in its `for` loop. Branches `cap-reached` and `skipped-cap-reached` are written as a single hard-coded combined line with no parameterized sentinel omission, making it impossible to construct a negative self-test for those two branches via this helper. The plan explicitly scoped negative tests to "at least two non-plan-size-trigger branches", so this is intentional, but the fixture silently enforces a coverage ceiling: if the combined `cap-reached`/`skipped-cap-reached` line ever loses a sentinel, no self-test will catch it before `assert_gate_b_bypass_branch_sentinels "$SKILL_MD"` runs on the real file. **Suggested fix:** add a `missing_sentinel` code-path for the combined line (controlled by `missing_branch=cap-reached` or `missing_branch=skipped-cap-reached`) and add one negative control for `cap-reached` in `run_gate_b_bypass_branch_sentinel_self_tests`. This extends the self-test coverage to all branches and closes the gap.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **correctness** `scripts/test-design-structure.sh:162-176` (`write_gate_b_bypass_fixture`) — The fixture helper can only produce missing-step-3.5 negative cases for the five branches in its `for` loop. Branches `cap-reached` and `skipped-cap-reached` are written as a single hard-coded combined line with no parameterized sentinel omission, making it impossible to construct a negative self-test for those two branches via this helper. The plan explicitly scoped negative tests to "at least two non-plan-size-trigger branches", so this is intentional, but the fixture silently enforces a coverage ceiling: if the combined `cap-reached`/`skipped-cap-reached` line ever loses a sentinel, no self-test will catch it before `assert_gate_b_bypass_branch_sentinels "$SKILL_MD"` runs on the real file. **Suggested fix:** add a `missing_sentinel` code-path for the combined line (controlled by `missing_branch=cap-reached` or `missing_branch=skipped-cap-reached`) and add one negative control for `cap-reached` in `run_gate_b_bypass_branch_sentinel_self_tests`. This extends the self-test coverage to all branches and closes the gap. No out-of-scope observations. ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	latent	correctness	scripts/test-design-structure.sh:133-143	assert_step3b_entry_guard_threads_repo does not verify the <!-- step:4  end-marker was found	If the file lacks <!-- step:4 , awk scans to EOF and silently matches a pause-save line from a later step, giving a false pass — no fail() is ever called for the missing end boundary	Add an end_marker_seen flag and emit fail "SKILL Step 3b missing end marker" if it was never set, mirroring assert_thin_fence's explicit marker-presence guards 1	in_scope	nit	correctness	scripts/test-design-structure.sh:162-176	write_gate_b_bypass_fixture cannot produce negative fixtures for cap-reached or skipped-cap-reached	If the combined cap-reached/skipped-cap-reached line ever drops a sentinel, no self-test detects it before the real SKILL.md check fires; the per-branch coverage is asymmetric	Add a missing_branch code-path for the combined line and one additional negative control in run_gate_b_bypass_branch_sentinel_self_tests ```
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **Part A**: `assert_gate_b_bypass_branch_sentinels` rewrites iterates all 7 branches with the correct `TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached` token for `skipped-cap-reached`, keys on the literal `: >` sentinel-write form, and asserts all four literals on the matched line.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **Part A**: `assert_gate_b_bypass_branch_sentinels` rewrites iterates all 7 branches with the correct `TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached` token for `skipped-cap-reached`, keys on the literal `: >` sentinel-write form, and asserts all four literals on the matched line.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **Part A negative self-tests**: `run_gate_b_bypass_branch_sentinel_self_tests` + `write_gate_b_bypass_fixture` implement a positive control plus negative controls for `tally-error` and `panel-failed`; invoked immediately after `run_thin_fence_self_tests`.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **Part A negative self-tests**: `run_gate_b_bypass_branch_sentinel_self_tests` + `write_gate_b_bypass_fixture` implement a positive control plus negative controls for `tally-error` and `panel-failed`; invoked immediately after `run_thin_fence_self_tests`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **Part B.1 SKILL.md**: Single-line `${REPO:+--repo "$REPO"}` addition to the Step 3b entry guard. Confirmed against live SKILL.md line 1263.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **Part B.1 SKILL.md**: Single-line `${REPO:+--repo "$REPO"}` addition to the Step 3b entry guard. Confirmed against live SKILL.md line 1263.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **Part B.1 test pin**: `assert_step3b_entry_guard_threads_repo` slices the `<!-- step:3b` / `<!-- step:4 ` region correctly; called on `$SKILL_MD`.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **Part B.1 test pin**: `assert_step3b_entry_guard_threads_repo` slices the `<!-- step:3b` / `<!-- step:4 ` region correctly; called on `$SKILL_MD`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: **Nit** `code-quality` `scripts/test-design-structure.sh:114-128` — The `case "$required" in` block inside the inner `for required in` loop derives a human-readable `label` from the `$required` value in ~10 lines, but `$required` (e.g., `: > "$DESIGN_TMPDIR/.completed/step-3.5"`) is already self-describing in an error message. The mapping adds no information a reader couldn't recover from the sentinel string itself. **Suggested fix:** Remove the `case` block and use `$required` directly in the failure message: `[[ "$line" == *"$required"* ]] || fail "$branch branch missing: $required"`.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **Nit** `code-quality` `scripts/test-design-structure.sh:114-128` — The `case "$required" in` block inside the inner `for required in` loop derives a human-readable `label` from the `$required` value in ~10 lines, but `$required` (e.g., `: > "$DESIGN_TMPDIR/.completed/step-3.5"`) is already self-describing in an error message. The mapping adds no information a reader couldn't recover from the sentinel string itself. **Suggested fix:** Remove the `case` block and use `$required` directly in the failure message: `[[ "$line" == *"$required"* ]] || fail "$branch branch missing: $required"`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **Part B.2**: `_postplan_resolve_repo()` mirrors `_postplan_resolve_issue()` with awk-only extraction; `_postplan_pause_checkpoint` threads `${_repo:+--repo "$_repo"}`.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **Part B.2**: `_postplan_resolve_repo()` mirrors `_postplan_resolve_issue()` with awk-only extraction; `_postplan_pause_checkpoint` threads `${_repo:+--repo "$_repo"}`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: **Part B.3**: `_classification_warn_count_before` captured before classification; synthetic `WARN_LINES` entry appended only when no new warns were added in the non-zero-exit arm; `else` arm (non-executable) left unchanged as required.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **Part B.3**: `_classification_warn_count_before` captured before classification; synthetic `WARN_LINES` entry appended only when no new warns were added in the non-zero-exit arm; `else` arm (non-executable) left unchanged as required.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: **`design-postplan-emit.md`**: Both `_postplan_resolve_repo` and the synthetic WARN guarantee documented.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **`design-postplan-emit.md`**: Both `_postplan_resolve_repo` and the synthetic WARN guarantee documented.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: **`test-design-postplan-emit.sh`**: Tests D11/D11b cover `--repo` threading and omission; `D2d_silent_nonzero` covers the synthetic WARN path; `reset_env` unsets `REPO` correctly.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **`test-design-postplan-emit.sh`**: Tests D11/D11b cover `--repo` threading and omission; `D2d_silent_nonzero` covers the synthetic WARN path; `reset_env` unsets `REPO` correctly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: **`scripts/test-design-structure.md`**: Updated to document both the all-branches pin and the Step 3b region check.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **`scripts/test-design-structure.md`**: Updated to document both the all-branches pin and the Step 3b region check.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: **Latent** `correctness` `scripts/test-design-structure.sh:162-198` — `write_gate_b_bypass_fixture` only supports injecting a missing `step-3.5` sentinel (the `missing_sentinel` parameter is only acted on when its value is exactly `step-3.5`). The negative self-tests exclusively verify that a `step-3.5` drop is caught; no self-test verifies that omitting `step-3` or `step-3.6` from a branch also fires the assertion. A future refactoring that drops the `step-3` or `step-3.6` write from a branch in SKILL.md would not be caught by `run_gate_b_bypass_branch_sentinel_self_tests`. **Suggested fix:** Extend `write_gate_b_bypass_fixture` to accept `step-3` and `step-3.6` as `missing_sentinel` values, and add at least one additional negative self-test covering a different sentinel (e.g., `step-3.6` removed from `degraded-empty-collector`).
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Latent** `correctness` `scripts/test-design-structure.sh:162-198` — `write_gate_b_bypass_fixture` only supports injecting a missing `step-3.5` sentinel (the `missing_sentinel` parameter is only acted on when its value is exactly `step-3.5`). The negative self-tests exclusively verify that a `step-3.5` drop is caught; no self-test verifies that omitting `step-3` or `step-3.6` from a branch also fires the assertion. A future refactoring that drops the `step-3` or `step-3.6` write from a branch in SKILL.md would not be caught by `run_gate_b_bypass_branch_sentinel_self_tests`. **Suggested fix:** Extend `write_gate_b_bypass_fixture` to accept `step-3` and `step-3.6` as `missing_sentinel` values, and add at least one additional negative self-test covering a different sentinel (e.g., `step-3.6` removed from `degraded-empty-collector`). ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: **correctness** `scripts/test-design-structure.sh:211-224` — `write_gate_b_bypass_fixture` generates the Step 3.5 placeholder string without a leading comma (`step35=', and `: > "$DESIGN_TMPDIR/.completed/step-3.5"`'`), which when interpolated creates double "and" connectors in the prose (`plus `: > ".../step-3"`, and `: > ".../step-3.5"`, and `: > ".../step-3.6"`). This is a cosmetic fixture prose irregularity only — the assertions use substring matching and don't care about the surrounding grammar — so it has no runtime impact. The fixture still correctly exercises the positive and negative paths. **Suggested fix:** Change `step35` to `, `: > "$DESIGN_TMPDIR/.completed/step-3.5"`'` (no leading "and", mirrors the real SKILL.md style: `` `: > "step-3"`, `: > "step-3.5"`, and `: > "step-3.6"` ``). This is a nit only.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **correctness** `scripts/test-design-structure.sh:211-224` — `write_gate_b_bypass_fixture` generates the Step 3.5 placeholder string without a leading comma (`step35=', and `: > "$DESIGN_TMPDIR/.completed/step-3.5"`'`), which when interpolated creates double "and" connectors in the prose (`plus `: > ".../step-3"`, and `: > ".../step-3.5"`, and `: > ".../step-3.6"`). This is a cosmetic fixture prose irregularity only — the assertions use substring matching and don't care about the surrounding grammar — so it has no runtime impact. The fixture still correctly exercises the positive and negative paths. **Suggested fix:** Change `step35` to `, `: > "$DESIGN_TMPDIR/.completed/step-3.5"`'` (no leading "and", mirrors the real SKILL.md style: `` `: > "step-3"`, `: > "step-3.5"`, and `: > "step-3.6"` ``). This is a nit only. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

