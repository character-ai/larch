### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_plan_review.py
- **Concern**: MainAgent sole-voter adjudication path has no named harness contract. Scenario: The plan gates `voter_severities` when `tally_voter_file` is set (`plan_review_tally.py` sets `eligible=1` and `tally_voter_file` for sole `--voter MainAgent:<file>`), but `### UPDATED: python/test_plan_review.py` only says "Add or extend MainAgent-adjudication coverage." The repo has no `--voter MainAgent` tally test today; an implementer can satisfy zero-judge tests while still passing a three-slot `voter_severities` list and breaking degraded adjudication with `ValueError` (accepted R3 FINDING_4).
- **Proposed resolution**: Add a named test (new or explicit) that runs `plan-review tally` with sole `--voter MainAgent:<vote-file>`, asserts `TALLY_PLAN_REVIEW_STATUS=ok`, and asserts `voting-tally.md` includes `## Voter Severity Scoreboard` after agreement without raising from the length guard.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_plan_review.py:169-179
- **Concern**: Plan-review zero-path test targets are conflated and under-specified vs code-review. Scenario: `### UPDATED: python/test_review_tally.py` names `test_tally_zero_voters_main_agent_vote_required` for `eligible==0` severity assertions, but the plan-review section bundles "zero-findings / eligible == 0" without naming `test_tally_plan_review_zero_voters_requires_main_agent` (early `eligible==0` return in `plan_review_tally.py:575-587`) or `test_execute_round_zero_findings_clears_stale_tally_artifacts` (writer in `plan_review_round.py:579-595`). Step3 zero-findings tests in `test_plan_review.py` do not inspect `voting-tally.md`, so severity on those paths can regress while acceptance line 226 still fails.
- **Proposed resolution**: Split the plan-review test bullets: extend `test_tally_plan_review_zero_voters_requires_main_agent` for `eligible==0` severity-after-agreement; extend `test_execute_round_zero_findings_clears_stale_tally_artifacts` (or equivalent) to assert severity headings on the zero-findings `voting-tally.md` written by `_reset_zero_findings_tally_artifacts`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:67
- **Concern**: [SCOPE-REDUCTION] Optional local severity table helper reopens duplicate renderer drift. Scenario: `### UPDATED: skills/voter-calibration/scripts/voter-calibration.py` still allows a report-local table helper "mirroring `_table`" beside shared `render_voter_severity_scoreboard`. That pattern was rejected in prior rounds and can diverge on columns, empty-state text, and `_format_rate` handling while live tallies use the shared helper.
- **Proposed resolution**: Require `render_voter_severity_scoreboard` from `python/voting.py` only; delete the "or reuse a local table helper mirroring `_table`" option from the plan.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_plan_review_round.py:1461-1505
- **Concern**: Zero-findings severity coverage points at the wrong test module. Scenario: `### UPDATED: python/plan_review_round.py` changes `_reset_zero_findings_tally_artifacts`, but `### UPDATED: python/test_plan_review.py` only vaguely says to add a zero-findings assertion. The integration test that actually writes `voting-tally.md` on that path is `test_execute_round_zero_findings_clears_stale_tally_artifacts` in `test_plan_review_round.py`; it currently checks stale-artifact cleanup only, not scoreboard headings. An implementer can extend the wrong file or skip the round short-circuit path while acceptance still requires severity on zero-findings tallies.
- **Proposed resolution**: Add `### UPDATED: python/test_plan_review_round.py` extending `test_execute_round_zero_findings_clears_stale_tally_artifacts` to assert `## Voter Severity Scoreboard` immediately follows `## Voter Agreement Scoreboard` in the reset `voting-tally.md`. Drop the ambiguous zero-findings bullet from `test_plan_review.py` or cross-reference this named test.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_plan_review.py:1425-1445
- **Concern**: Plan-review `eligible == 0` lacks the explicit named-test contract code-review already has. Scenario: Code-review names `test_tally_zero_voters_main_agent_vote_required` in Files (lines 156-158) and acceptance (line 232). Plan-review only groups `eligible == 0` with zero-findings under a generic `test_plan_review.py` bullet (line 178), and acceptance pins only the code-review test. The existing `test_tally_plan_review_zero_voters_requires_main_agent` already exercises plan-review `eligible == 0` but asserts agreement only. Severity on that path can regress while `make py-test` stays green.
- **Proposed resolution**: Mirror the code-review contract: in `### UPDATED: python/test_plan_review.py`, explicitly extend `test_tally_plan_review_zero_voters_requires_main_agent` with severity heading/order assertions, and add the same named test to acceptance criteria alongside line 232.



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_plan_review.py:1425-1445
- **Concern**: Plan-review `eligible == 0` severity coverage lacks the explicit named-test contract given to code-review. Scenario: The plan extends `test_tally_zero_voters_main_agent_vote_required` with severity assertions (lines 156-158) and names it in acceptance (line 232), but plan-review only has a vague `test_plan_review.py` bullet (line 178). The existing `test_tally_plan_review_zero_voters_requires_main_agent` exercises `plan_review_tally.py` `eligible == 0` and already checks agreement scoreboard content; it can be updated for severity while the implementer never adds the required assertions
- **Proposed resolution**: Add under `### UPDATED: python/test_plan_review.py` an explicit extension of `test_tally_plan_review_zero_voters_requires_main_agent` mirroring the code-review test: assert `## Voter Severity Scoreboard` immediately follows `## Voter Agreement Scoreboard` in `voting-tally.md`. Add a matching acceptance bullet beside line 232.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_plan_review_round.py:1461-1505
- **Concern**: Zero-findings tally reset has no named severity test despite `plan_review_round.py` change. Scenario: The plan updates `_reset_zero_findings_tally_artifacts` (lines 127-131) and acceptance requires severity on zero-findings paths (line 226), but `### Files to modify/create` omits `python/test_plan_review_round.py`. `test_execute_round_zero_findings_clears_stale_tally_artifacts` is the integration test that exercises that reset and currently does not inspect scoreboard headings, so severity sections can be dropped on the zero-findings path while tests stay green
- **Proposed resolution**: List `### UPDATED: python/test_plan_review_round.py` and require extending `test_execute_round_zero_findings_clears_stale_tally_artifacts` to assert `## Voter Severity Scoreboard` follows `## Voter Agreement Scoreboard` in the rewritten `voting-tally.md`. Keep the separate `eligible == 0` contract on `test_tally_plan_review_zero_voters_requires_main_agent`.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:67
- **Concern**: [SCOPE-REDUCTION] Optional local severity table helper reopens duplicate-renderer drift. Scenario: The plan still allows `render_voter_severity_scoreboard` or a local table helper mirroring `_table` beside the shared `python/voting.py` renderer. Prior rounds rejected that duplicate path; a second renderer can diverge on columns, empty-state text, and rate formatting while live tallies use the shared helper
- **Proposed resolution**: Remove the `or reuse a local table helper mirroring _table` alternative. Require `render_voter_severity_scoreboard` from `python/voting.py` only, matching the agreement path pattern.



### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/voter-calibration/scripts/test-voter-calibration.sh:52-61
- **Concern**: Accepted harness fix remains incomplete because the proposed two-heading assertion can still pass with only one severity section. Scenario: `grep -c ... | awk '$1>=2'` exits 0 even when the count is 0 or 1, and an unbounded slice after `## Agreement Table` can match the later global severity block. `make test-voter-calibration` can pass while either the panel or global severity scoreboard is missing, violating the explicit acceptance gate.
- **Proposed resolution**: Use a failing shell count check and bounded section checks. For example assign the grep count and run `[[ "$count" -ge 2 ]]`, then use bounded awk ranges from `## Agreement Table` to `## Global Voter Agreement` and from `## Global Voter Agreement` to the next heading to require one severity heading in each range.



