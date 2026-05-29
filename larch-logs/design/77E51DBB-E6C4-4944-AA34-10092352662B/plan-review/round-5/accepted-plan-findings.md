### FINDING_2: Plan review loop dedup can undo waterfall trailer preservation
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `revise-plan-with-waterfall.sh` may validate optional trailers before emitting, but `plan-review-loop.sh` then runs post-apply dedup before `check-plan-size`. An adjacent duplicate trailer-shaped body line can cause the authoritative final trailer to be removed or mis-parsed, restoring legacy hard gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add plan-review-loop.sh to the change set: snapshot strict optional trailer keys before dedup and re-validate (or restore from pre-dedup snapshot) after dedup, reusing the same contract as revise-plan-with-waterfall; document failure mode #10 and extend test-plan-review-loop (non-stub revise or fixture plan with adjacent duplicate trailer-shaped body line) so LOOP_STATUS=plan-size-trigger cannot regress silently


### FINDING_3: Files-to-modify heading is not a concrete path
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan’s files-to-modify section uses a vague combined heading instead of exactly one concrete path per `NEW`/`UPDATED`/`REWRITTEN` heading, which can make downstream scoping malformed or cause an implementer to miss the docs update.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Split it into exact headings, e.g. skills/design/scripts/revise-plan-with-waterfall.sh and skills/design/scripts/revise-plan-with-waterfall.md, and remove the "sibling docs/prompts if present" wording


### FINDING_4: Legacy byte-for-byte wording conflicts with additive output keys
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan says legacy plans reproduce current behavior byte-for-byte, but the proposed helper always emits four new keys on exit 0. That can lead an implementer to omit `DIFF_ADDED`, `DIFF_DELETED`, `MECHANICAL_CHURN`, and `SOFT_ADVISORY` for legacy plans, contradicting the output contract and tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Change the summary to say legacy trigger decisions and existing keys remain unchanged, while exit-0 output gains additive keys
  - From Codex-Requirements: Change the summary to say legacy trigger decisions and existing keys remain unchanged, while exit-0 output gains additive keys


### FINDING_5: Mechanical churn acceptance criterion is overbroad
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The acceptance text says `mechanical_churn: true` yields `HARD_TRIGGER_FIRED=false` and `SOFT_ADVISORY=true` without limiting that behavior to downgraded diff-side triggers. This conflicts with the plan’s rule that plan-body crossings still hard-trigger and under-threshold mechanical churn has no advisory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Qualify the acceptance criterion: mechanical_churn true downgrades only a diff-side hard trigger; plan-body hard triggers remain hard, and SOFT_ADVISORY is true only when a diff trigger was actually downgraded
  - From Codex-Requirements: Qualify the acceptance criterion: mechanical_churn true downgrades only a diff-side hard trigger; plan-body hard triggers remain hard, and SOFT_ADVISORY is true only when a diff trigger was actually downgraded


### FINDING_10: Spoof-resistance fixture does not pin the winning metadata block
- **Reviewer(s)**: Cursor-dyn-harness-completeness, Codex-dyn-harness-completeness
- **Severity**: important
- **Concern**: The proposed spoof-resistance test says prose or fenced `mechanical_churn: true` and `diff_added: 0` are ignored, but does not specify conflicting real final metadata values or assert which block wins. A parser that incorrectly scans body text could still pass a weak fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-completeness: Make the case fixture explicit: put mechanical_churn: true and diff_added: 0 in body prose or a fenced block, then put conflicting strict trailers in the final metadata block, and assert DIFF_ADDED, MECHANICAL_CHURN, HARD_TRIGGER_FIRED, TRIGGER_REASONS, and SOFT_ADVISORY from the final block.
  - From Codex-dyn-harness-completeness: Make the case fixture explicit: put mechanical_churn: true and diff_added: 0 in body prose or a fenced block, then put conflicting strict trailers in the final metadata block, and assert DIFF_ADDED, MECHANICAL_CHURN, HARD_TRIGGER_FIRED, TRIGGER_REASONS, and SOFT_ADVISORY from the final block.


### FINDING_11: Plan review loop test may not prove revision path ran
- **Reviewer(s)**: Cursor-dyn-harness-completeness, Codex-dyn-harness-completeness
- **Severity**: important
- **Concern**: The proposed `plan-review-loop` extension can pass by only asserting the loop does not emit `LOOP_STATUS=plan-size-trigger`. If the fixture skips accepted findings or skips revision, a converged or skipped path could satisfy the negative assertion without exercising post-revision size validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-completeness: Require the test to use an accepted-finding multi-round fixture like the existing plan-size test, assert REVISE_STATUS=ok or a sentinel written by the revise stub, assert the final plan contains the optional trailers, then assert LOOP_STATUS is not plan-size-trigger.
  - From Codex-dyn-harness-completeness: Require the test to use an accepted-finding multi-round fixture like the existing plan-size test, assert REVISE_STATUS=ok or a sentinel written by the revise stub, assert the final plan contains the optional trailers, then assert LOOP_STATUS is not plan-size-trigger.

