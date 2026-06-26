### OOS_1: Harness should exercise `--out` on boundary-unavailable era runs
- **Description**: Harness should exercise `--out` on boundary-unavailable era runs. Scenario: The plan requires `--out` plus `REPORT_FILE=` on unavailable-boundary paths (lines 33, 181), but the new test bullets never cover that branch. A regression could stop writing the file while stdout-only tests still pass.
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:150-161
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: Fake-`gh` success test should assert single `gh issue view` invocation
- **Description**: Fake-`gh` success test should assert single `gh issue view` invocation. Scenario: Plan lines 152-156 stub shipped JSON but do not require counting `gh` calls. A second fetch via `_incentive_issue_from_gh` could return without failing current assertions, reviving the one-fetch regression already accepted in prior rounds.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:152-156
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: Failure mode closed-without-PR refs lacks fake-`gh` coverage
- **Description**: Failure mode closed-without-PR refs lacks fake-`gh` coverage. Scenario: Plan failure modes (line 189) require shipped-predicate degradation when `closedByPullRequestsReferences` is empty, but no harness case supplies closed JSON without PR refs. That branch can regress to using `closedAt` or traceback while other era tests stay green.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:157-160
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Add fake-`gh` closed-without-PR refs degradation case
- **Description**: [OUT_OF_SCOPE] Add fake-`gh` closed-without-PR refs degradation case. Scenario: Failure modes document that closed-without-PR refs must degrade to boundary unavailable, but the harness only covers shipped success and missing `closedAt`. A regression in the shipped predicate could ship undetected.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:157-160
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Harness does not exercise `--out` on boundary-unavailable era runs
- **Description**: [OUT_OF_SCOPE] Harness does not exercise `--out` on boundary-unavailable era runs. Scenario: Plan requires unavailable-boundary reports to honor `--out` and print `REPORT_FILE=`. No harness case covers that path, so a regression could stop writing the file while exit `0` and guidance tests still pass.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:151-161
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] Fake-`gh` harness omits closed-without-PR refs degradation
- **Description**: [OUT_OF_SCOPE] Fake-`gh` harness omits closed-without-PR refs degradation. Scenario: Failure modes document closed-without-PR as boundary unavailable via the shipped predicate, but fake-`gh` cases only cover shipped-with-`closedAt` and missing-`closedAt`. A broken predicate could mark shipped without PR refs and set a wrong boundary undetected.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:152-160
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Fake-`gh` closed-without-PR refs degradation harness
- **Description**: [OUT_OF_SCOPE] Fake-`gh` closed-without-PR refs degradation harness. Scenario: Failure modes document shipped predicate failure when closed without PR refs, but no fake-`gh` case supplies empty `closedByPullRequestsReferences`; regression stays untested though auto-boundary would degrade correctly if predicate works.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:152-160
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] `--out` on boundary-unavailable era runs
- **Description**: [OUT_OF_SCOPE] `--out` on boundary-unavailable era runs. Scenario: Plan requires `--out` on unavailable-boundary paths; no-`gh` test asserts guidance only on stdout, so report-file write/`REPORT_FILE=` regressions on that path stay unverified.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:151-152
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_9: [SCOPE-REDUCTION] Era slices should call `compute_*` + table builders directly, not `_render` extract
- **Description**: [SCOPE-REDUCTION] Era slices should call `compute_*` + table builders directly, not `_render` extract. Scenario: Plan prefers `_render` per slice then extract Agreement/Severity while also omitting Global/Chronic sections `_render` always emits; a thin era renderer reusing `_table` and `render_voter_severity_scoreboard` is smaller and matches scoped output.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:97-98
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

