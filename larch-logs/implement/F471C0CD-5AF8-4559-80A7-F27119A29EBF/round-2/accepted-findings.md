### FINDING_10: Combine-issues jq filter omits legacy `[IN PROGRESS]` exclusion; conflicts with “busy prefixes filtered” posture
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The jq combinable filter’s excluded-prefix alternation no longer covers legacy `[IN PROGRESS] ` titles, so open issues with legacy in-flight prefixes can become combinable candidates again. That can route combine workflows at still-active legacy-titled tracking issues and violates the skill’s expectation that busy prefixes are filtered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Extend jq to exclude legacy IN PROGRESS/PLANNED prefixes or add fixtures/docs that encode the intended legacy posture.
  - From cursor-specialist-edge-cases-output.txt: Extend jq exclusion for legacy IN PROGRESS (and align SKILL prose + hermetic jq fixture tests).


### FINDING_13: Stale `RUN_ID` implement-admission test may not assert `ADMISSION_RESULT=managed-prefix` on exit 5
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The stale `RUN_ID` fall-through path checks exit 5 and `TITLE=` but not managed-prefix expectations, so an incorrect `ADMISSION_RESULT` on exit 5 could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert ADMISSION_RESULT=managed-prefix for the IMPLEMENTING stale-tmpdir scenario.


### FINDING_2: Unreleased changelog audit-scope bullet contradicts branch reality
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The Unreleased audit-scope bullet claims `CHANGELOG.md` and `larch-logs/` were left unchanged even though the branch adds or edits Unreleased changelog content and run-log paths. Readers may treat the bullet as forbidding any edits there and argue the PR contradicts its own changelog story.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rewrite the bullet to distinguish bulk rewrite of historical prefix literals from normal new Unreleased entries and intentional new run-log commits.


### FINDING_3: “Zero-hit” acceptance grep conflicts with deliberate legacy literals in tree
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-testing-output.txt
- **Concern**: A literal “zero hits” `git grep` acceptance check cannot hold on a correct implementation that still carries deliberate legacy bracket tokens in tests, migration docs, `SECURITY.md`, admission recovery prose, and hermetic fixtures; CI or operators following the plan verbatim would false-fail. Tighten acceptance to path-scoped grep, explicit allow-lists, or otherwise match the mitigation strategy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Tighten the acceptance criterion to path-scoped grep and/or an explicit allow-list matching the plan mitigation.
  - From cursor-specialist-plan-fidelity-output.txt: Narrow grep scope or revise acceptance to allow migration docs, admission recovery text, and hermetic legacy fixtures.
  - From cursor-specialist-testing-output.txt: Clarify acceptance to allow-list migration literals or scope grep to prose-only paths.


### FINDING_7: `test-tracking-issue-write.sh` lacks symmetric negative coverage for `--state planned`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Only invalid `--state in-progress` is asserted; `planned` is not covered despite symmetric rejection requirements, so a regression could drop `planned` from the rejection set or garble the error string without harness signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Mirror the existing in-progress negative test for --state planned with the same exit and envelope assertions.


### FINDING_8: No hermetic coverage for rename `--state implementing` (critical Step 0 writer)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: There is no stubbed-`gh` fixture coverage for rename flows with `--state implementing`, so regressions in strip order, truncation, or prefix mapping for implementing could ship while `make test-tracking-issue-write` still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stubbed gh fixtures for implementing from [DESIGNED] and optionally from legacy [IN PROGRESS].


### FINDING_9: Duplicated jq filter between harness and `fetch-combinable-issues.sh` risks silent drift
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The combinable-issue jq filter is copy-pasted between `scripts/test-fetch-combinable-issues-filter.sh` and `.claude/skills/combine-issues/scripts/fetch-combinable-issues.sh`, so production filtering can drift from CI without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a sync check or shared jq fragment and assert identity.


