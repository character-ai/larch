### FINDING_1: Since-tag gap test is underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Ledger Gap Invariants
- **Severity**: important
- **Concern**: The new since-tag gap regression test is too qualitative: it does not pin the concrete `panel-tier`/`design` row dicts or a clearly failing pre-fix scenario, so an unfixed `_summarize` can still pass and the intended restart-vs-tag-boundary semantics remain ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Match test_summary_ledger_restarts_target_after_gap: assert panel-tier has raises=0 and empty largest_raise_commit/largest_raise_delta, not only start/end/delta`
  - From Cursor-Innovation: `Pin exact rows["panel-tier"] and rows["design"] dicts (matching the style of test_since_tag_summary_aggregates_after_tag) and state whether since-tag gap semantics are restart-at-reappear (45000/45000/0) or range-span aggregation; require a pre-fix pytest failure or the strengthened fixture the plan already allows`
  - From Cursor-Pragmatic: `Pin the full panel-tier and design dicts in the plan (restart vs window-continuous must be explicit); require red-green verification before merge; if restart dicts are chosen, state that test_since_tag_summary_reflects_removed_target_in_final_snapshot is the primary regression guard and strengthen the fixture or expectations until the new test fails on current code`
  - From Cursor-dyn-Ledger Gap Invariants: `In the plan's \`test_since_tag_summary_with_gap_and_reappear\` section, require the full \`panel-tier\` row to match python/tests/lint/test_skill_closure_ledger.py:257-265 (\`start=45000\`, \`end=45000\`, \`delta=0\`, \`raises=0\`, empty raise fields) and keep the \`design\` row aligned with python/tests/lint/test_skill_closure_ledger.py:266-274. State explicitly that reappear restart overrides tag-boundary \`start\` semantics from python/tests/lint/test_skill_closure_ledger.py:311-318.`


### FINDING_2: Empty-selection guard is missing around the post-loop pass
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: latent
- **Concern**: The post-loop final-removal advance needs an explicit empty-revisions guard. Without it, the implementation can read an undefined final snapshot/commit or advance incorrectly when `--window` or `--since-tag` selects no revisions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `After the revision loop, return () immediately when no revision was seen; run the final-removal advance only when final_snapshot_values and final_commit_sha were set in that loop`
  - From Cursor-Pragmatic: `Track final snapshot and commit inside the loop only; run the post-loop pass only when at least one revision was visited; keep returning an empty tuple when order is empty`


### FINDING_1: Gap/removal regression still needs a guaranteed pre-fix failure
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The proposed skip-absent-target fix and the new since-tag regression are not yet a reliable red-green boundary. Current `_summarize` can still mask the gap behavior through `reappearing_targets`, so a partial fix or the full skip-plus-post-loop change may pass without proving the intended absent-target handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one explicit plan bullet under Testing strategy: after implementing only the in-loop skip (post-loop stubbed), `test_since_tag_summary_reflects_removed_target_in_final_snapshot` must fail; full fix must restore green. No extra integration test required beyond that check.
  - From Cursor-Pragmatic: Require a test that fails on unfixed `_summarize` without relying on reappear reset masking. Options that fit minimum-change scope: a private `_summarize` test on a revision prefix ending at removal (before reappear) that pins non-zero `end` until post-loop runs, or a fixture/expectation pair that fails if gap advances fabricate `current=0` before reset. Make that mandatory, not conditional on implementer discovery.


### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/lint/test_skill_closure_ledger.py:245-360
- **Concern**: [SCOPE-REDUCTION] Planned since-tag gap test cannot be red-green for the gap-skip fix. Scenario: The pinned `panel-tier` row (`start`/`end`/`delta`/`raises` all `45000`/`45000`/`0`/`0`) is already produced by unfixed `_summarize` because `reappearing_targets` resets the accumulator on reappear (`skill_closure_ledger.py:307-310`) after any interim `advance(..., 0)` during absence; `test_summary_ledger_restarts_target_after_gap` already asserts the same dicts without `--since-tag`. An extra absent commit between removal and reappearance cannot change that final row, so the plan's conditional fixture tweak still leaves the mandated test green on unfixed code and unable to prove the gap-skip change.
- **Proposed resolution**: Drop `test_since_tag_summary_with_gap_and_reappear` as redundant, or replace it with an assertion that differs today (e.g. a `--window` slice whose selected revisions end on the removal commit and expect `end=0`, which unfixed in-loop advance already satisfies) or a focused `_summarize` unit test built from hand-crafted `BaselineRevision` tuples that exercises skip-without-post-loop and expects `test_since_tag_summary_reflects_removed_target_in_final_snapshot` to fail until the post-loop pass lands.

### FINDING_1: Planned gap regression test still can pass without the skip fix
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The proposed direct `_summarize` regression test does not yet force a failure on the current implementation: the reappearing-target reset and the final-removal `0` advance already satisfy the stated assertions, so the test can still pass while the in-loop absent-target advance remains in place. The plan needs one assertion or fixture that specifically fails when an absent target is advanced to `0` during an intermediate gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a mandatory assertion or hand-crafted `_summarize` case that fails while `accumulator.advance(..., current=snapshot_values.get(target, 0))` remains, such as an accumulated target absent from an intermediate snapshot and present later without a reappearing reset, then pin `raises` or `largest_raise_delta` so the synthetic 0-to-current raise is caught; keep the existing partial-skip/no-post-loop check too
  - From Codex-Innovation: Revise the planned direct _summarize test so one assertion fails on current code and passes only when absent targets are skipped. Pin a full SummaryRow for a hand-crafted gap case where the synthetic 0 changes raises, largest_raise_delta, or delta, and keep the final-removal assertion for the post-loop.
  - From Codex-Pragmatic: Add a red-green assertion that fails with the current absent-target advance, such as instrumenting `_SummaryAccumulator.advance` in the focused unit test and asserting the gap target is not advanced at the absent intermediate revision, while still asserting the final-removal post-loop advances the permanently removed target to `0`.
  - From Codex-Requirements: Require the new focused _summarize test to fail on current code by observing that no advance to current=0 happens on an intermediate gap, for example with a small spy around _SummaryAccumulator.advance, while keeping the final-removal post-loop assertion

