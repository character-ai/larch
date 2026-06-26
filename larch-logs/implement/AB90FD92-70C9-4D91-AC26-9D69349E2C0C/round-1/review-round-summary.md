# Review Round 1

- Mode: `diff`
- 4 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Verdict mode accepts sub-capstone `--min-runs`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generalist-output.txt, dyn-dyn-verdict-docs-output.txt
- **Severity**: important
- **Concern**: Verdict mode enforces capstone floors for `--since-date` and `--min-larch-version` in `_enforce_ground_truth_verdict_capstone_minima`, but not for `--min-runs`. The CLI accepts `--min-runs` values from 1 through 149. With one qualifying incentivized-era run and healthy #5461/enrichment gates, `--ground-truth-verdict --min-runs 1` can exit 0 and print `Gate result: PASS`, certifying a corpus far below the 150-run capstone requirement. That conflicts with the capstone contract in `docs/ground-truth-verdict.md`, `.claude/skills/analyze-issues/SKILL.md`, and the plan’s enforce-150 requirement; an operator can treat a toy corpus PASS as capstone evidence for token allocation #4771 (`test_ground_truth_verdict_gate_passes_with_bulk_incentive_issue` currently expects this behavior).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reject --min-runs below GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS in _enforce_ground_truth_verdict_capstone_minima or _ground_truth_verdict_exit; reserve lower thresholds for direct calibration test calls only.
  - From codex-generalist-output.txt: Reject verdict `--min-runs` values below `GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS`, or coerce them to at least 150 before calling `ground_truth_voter_calibration`.
  - From dyn-dyn-verdict-docs-output.txt: Extend `_enforce_ground_truth_verdict_capstone_minima` (or equivalent verdict-only validation) to reject `--min-runs` below `GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS` (150), mirror the existing since-date/version errors, and add a regression test that `--min-runs 1` fails in verdict mode even when all other gates pass.


### FINDING_3: Missing verdict-mode gc-slimmed corpus gate regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Verdict-mode gc-slimmed corpus gating lacks a plan-required regression test. Diagnostic gc-slimmed coverage does not exercise `_ground_truth_verdict_run_qualifies`; a regression could count gc-slimmed runs toward `qualifying_runs` and emit a false PASS on the capstone corpus gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a verdict-mode fixture with a gc-slimmed post-date run and assert qualifying_runs stays 0 and excluded_gc_slimmed_runs is reported.


### FINDING_4: Missing cache filtered-rows-only regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required cache-insert filtered-rows-only test is missing. Without asserting `_GROUND_TRUTH_ROW_CACHE` stores only filtered rows, a cache regression could retain unfiltered rows under a verdict key and reuse stale evidence on later invocations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Mixed eligible/ineligible corpus test that inspects cached row count equals filtered qualifying rows only.


### FINDING_5: Missing `large_corpus_skip` filtered-subset regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required `large_corpus_skip` filtered-subset test is missing. Recomputing `large_corpus_skip` from an unfiltered superset would disable accepted-finding evidence in a small verdict slice without failing existing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a bounded test proving verdict mode leaves large_corpus_skip false for small filtered corpora and true only when filtered rows exceed 5000.


