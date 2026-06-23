### [Plan Review] FINDING_2

### FINDING_2: Plan-review `eligible == 0` path lacks explicit named-test severity contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Code-review already names `test_tally_zero_voters_main_agent_vote_required` in Files and acceptance, but plan-review only groups `eligible == 0` with zero-findings under a generic `test_plan_review.py` bullet. The existing `test_tally_plan_review_zero_voters_requires_main_agent` exercises plan-review `eligible == 0` and checks agreement scoreboard content only. Severity headings on that path can regress while `make py-test` stays green and acceptance line 232 (code-review pin) still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Split the plan-review test bullets: extend `test_tally_plan_review_zero_voters_requires_main_agent` for `eligible==0` severity-after-agreement; extend `test_execute_round_zero_findings_clears_stale_tally_artifacts` (or equivalent) to assert severity headings on the zero-findings `voting-tally.md` written by `_reset_zero_findings_tally_artifacts`.
  - From Cursor-Innovation: Mirror the code-review contract: in `### UPDATED: python/test_plan_review.py`, explicitly extend `test_tally_plan_review_zero_voters_requires_main_agent` with severity heading/order assertions, and add the same named test to acceptance criteria alongside line 232.
  - From Cursor-Requirements: Add under `### UPDATED: python/test_plan_review.py` an explicit extension of `test_tally_plan_review_zero_voters_requires_main_agent` mirroring the code-review test: assert `## Voter Severity Scoreboard` immediately follows `## Voter Agreement Scoreboard` in `voting-tally.md`. Add a matching acceptance bullet beside line 232.


### [Plan Review] FINDING_3

### FINDING_3: Zero-findings tally reset path targets wrong or missing test module
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: `_reset_zero_findings_tally_artifacts` in `plan_review_round.py` writes `voting-tally.md` on the zero-findings short-circuit path, but the plan omits or vaguely references `python/test_plan_review_round.py`. The integration test `test_execute_round_zero_findings_clears_stale_tally_artifacts` exercises that reset and currently checks stale-artifact cleanup only, not scoreboard headings. An implementer can extend the wrong file or skip the round path while acceptance still requires severity on zero-findings tallies (line 226).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Split the plan-review test bullets: extend `test_tally_plan_review_zero_voters_requires_main_agent` for `eligible==0` severity-after-agreement; extend `test_execute_round_zero_findings_clears_stale_tally_artifacts` (or equivalent) to assert severity headings on the zero-findings `voting-tally.md` written by `_reset_zero_findings_tally_artifacts`.
  - From Cursor-Innovation: Add `### UPDATED: python/test_plan_review_round.py` extending `test_execute_round_zero_findings_clears_stale_tally_artifacts` to assert `## Voter Severity Scoreboard` immediately follows `## Voter Agreement Scoreboard` in the reset `voting-tally.md`. Drop the ambiguous zero-findings bullet from `test_plan_review.py` or cross-reference this named test.
  - From Cursor-Requirements: List `### UPDATED: python/test_plan_review_round.py` and require extending `test_execute_round_zero_findings_clears_stale_tally_artifacts` to assert `## Voter Severity Scoreboard` follows `## Voter Agreement Scoreboard` in the rewritten `voting-tally.md`. Keep the separate `eligible == 0` contract on `test_tally_plan_review_zero_voters_requires_main_agent`.


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:67
- **Concern**: [SCOPE-REDUCTION] Optional local severity table helper reopens duplicate renderer drift. Scenario: `### UPDATED: skills/voter-calibration/scripts/voter-calibration.py` still allows a report-local table helper "mirroring `_table`" beside shared `render_voter_severity_scoreboard`. That pattern was rejected in prior rounds and can diverge on columns, empty-state text, and `_format_rate` handling while live tallies use the shared helper.
- **Proposed resolution**: Require `render_voter_severity_scoreboard` from `python/voting.py` only; delete the "or reuse a local table helper mirroring `_table`" option from the plan.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:67
- **Concern**: [SCOPE-REDUCTION] Optional local severity table helper reopens duplicate-renderer drift. Scenario: The plan still allows `render_voter_severity_scoreboard` or a local table helper mirroring `_table` beside the shared `python/voting.py` renderer. Prior rounds rejected that duplicate path; a second renderer can diverge on columns, empty-state text, and rate formatting while live tallies use the shared helper
- **Proposed resolution**: Remove the `or reuse a local table helper mirroring _table` alternative. Require `render_voter_severity_scoreboard` from `python/voting.py` only, matching the agreement path pattern.

