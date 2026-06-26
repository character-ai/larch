# Review Round 1

- Mode: `diff`
- 6 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Committed manifest cohort is incomplete (single FINDING_10 row)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, codex-generalist-output.txt
- **Severity**: blocking
- **Concern**: The committed `manifest.tsv` has only one labeled row (`FINDING_10`) while the plan requires the full companion-issue labeled set as the replay denominator. `validate-manifest` and replay can pass on a trivial one-row cohort, so acceptance cannot verify before/after plan-fidelity YES-rate on the intended labeled set or exercise mixed fixture/reconstruction paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Add the full labeled cohort to the manifest, or fail validation when the committed denominator is incomplete.
  - From codex-specialist-testing-output.txt: add the full labeled cohort rows and their fixtures before merge, and make manifest validation fail if the committed set does not match that cohort denominator.
  - From codex-generalist-output.txt: Populate `manifest.tsv` with every labeled plan-mandated-deliverable finding from the companion issue, with frozen plan and required diff or ballot fixtures for each row.


### FINDING_2: No executable dispatch-voters calibration replay harness or PR evidence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no in-repo `dispatch-voters` calibration replay driver or committed before/after PR evidence. Prompt-shape and helper unit tests can pass while production voter YES-rate on plan-mandated findings remains unverified at merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add bounded replay driver that validates manifest rebuilds ballots runs agent dispatch-voters with tool parity guards and records per-row before/after votes in PR evidence.


### FINDING_3: Plan fixture is full document, not extracted Implementation Plan slice
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, codex-generalist-output.txt, dyn-dyn-calibration-replay-output.txt
- **Severity**: blocking
- **Concern**: `FINDING_10.plan.txt` is a full issue/plan document (wrapper, `## Plan`, `## Approach`, footer) rather than the `## Implementation Plan` body that production `dispatch-voters` receives via `extract_implementation_plan_from_plan_goals_test`. Replay uses different plan context than production, so before/after votes may not reflect real impact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Regenerate the fixture from extract_implementation_plan_from_plan_goals_test and reject fixtures that still contain the surrounding wrapper or footer.
  - From codex-specialist-edge-cases-output.txt: Regenerate the fixture from plan-goals-test.md and add a shape test that rejects full-document plan fixtures.
  - From codex-specialist-testing-output.txt: regenerate the file from `extract_implementation_plan_from_plan_goals_test(...)` and commit only the extracted body.
  - From codex-generalist-output.txt: Regenerate this fixture from the source run's `plan-goals-test.md` using `extract_implementation_plan_from_plan_goals_test`, and commit only the Implementation Plan body.
  - From dyn-dyn-calibration-replay-output.txt: Regenerate `FINDING_10.plan.txt` via `extract_implementation_plan_from_plan_goals_test` from the source run's `plan-goals-test.md`, and add a test that every committed plan fixture matches that extractor output.


### FINDING_4: `validate_manifest_row` fail-open on missing/invalid run metadata and non-reconstructible ballot sources
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, codex-generalist-output.txt, dyn-dyn-calibration-replay-output.txt
- **Severity**: blocking
- **Concern**: `validate_manifest_row` can return success when `run_id`/`round_num` are missing or invalid, or when no reconstructible ballot source exists (empty `fixture_ballot` with no usable `findings.md` or jsonl). `MANIFEST_STATUS=ok` can print for rows that `rebuild-ballot` fails on at runtime, defeating fail-closed validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Hard-fail on missing or invalid run metadata and on any row where fixture, findings.md, and jsonl reconstruction all fail.
  - From codex-specialist-edge-cases-output.txt: Hard-fail on missing or invalid run metadata and on any row without a reconstructible ballot source or committed ballot fixture.
  - From codex-specialist-testing-output.txt: validate the ballot source itself, not just the plan fixture, by checking that `rebuild_single_item_ballot` can succeed or by hard-failing when neither `findings.md` nor jsonl can provide the row.
  - From codex-generalist-output.txt: Require valid `run_id` and positive numeric `round_num`, then verify either a readable `fixture_ballot`, a matching `round-N/findings.md` block, or a matching non-truncated `review-findings-full.jsonl` record exists.
  - From dyn-dyn-calibration-replay-output.txt: Require a reconstructible ballot source for every row (committed fixture, readable `round-<N>/findings.md` block, or non-truncated jsonl record), and hard-fail when `run_id`/`round_num` are required but invalid.


### FINDING_5: `extract_implementation_plan_from_plan_goals_test` diverges from `run_logs._validate_plan_goals_payload`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, codex-generalist-output.txt, dyn-dyn-calibration-replay-output.txt
- **Severity**: important
- **Concern**: The plan-freeze helper diverges from the production plan-goals sanitizer on pointer-only first-line detection, `## Test plan` boundary handling, and repeated-heading rules. Fixtures accepted here may be rejected by the sanitizer (e.g. pointer-first line with trailing content, repeated `## Test plan` headings), producing non-parity replay fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Mirror run_logs._validate_plan_goals_payload by checking the first non-empty Implementation Plan line and rejecting pointer-only placeholders before any content is accepted.
  - From codex-specialist-testing-output.txt: mirror the sanitizer contract by rejecting any body whose first non-empty `Implementation Plan` line is a pointer placeholder, not just bodies that are pointer-only in full.
  - From codex-generalist-output.txt: Reuse the same section and first-nonempty-line logic as `_validate_plan_goals_payload`, or factor the shared extraction into one helper used by both paths.
  - From dyn-dyn-calibration-replay-output.txt: Reuse or factor shared extraction/validation from `run_logs._validate_plan_goals_payload`, including first-line pointer detection and exact heading matching.


### FINDING_6: `fixture_ballot` passthrough skips `neutralize_reviewer_attribution`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generalist-output.txt, dyn-dyn-calibration-replay-output.txt
- **Severity**: important
- **Concern**: When `fixture_ballot` is set, `rebuild_single_item_ballot` returns raw file text without calling `voting.neutralize_reviewer_attribution`. Tests assert named `Reviewer(s)` lines survive. Mis-authored fixtures replay attributed ballots and can change votes versus production-neutralized ballots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist-output.txt: Neutralize fixture ballot text before returning it, or fail validation when a fixture ballot is not already neutralized.
  - From dyn-dyn-calibration-replay-output.txt: Always run `neutralize_reviewer_attribution` on fixture text before return (or hard-fail when attribution is not already anonymous), and update the fixture test to expect `anonymous`.


