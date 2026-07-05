### FINDING_1: Ballot parse errors must fail closed
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-Security Sidecar Auditor
- **Severity**: important
- **Concern**: The ballot-count path conflates unreadable or corrupt ballots with legitimately empty ballots, so `_prepare_pruned_ballot` can skip voting instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Change _ballot_block_count to a tri-state (or raise) and branch in _prepare_pruned_ballot: read/parse errors return _post_gate_panel_failed_exit_from_context (for example threshold_reason=ballot-read-failed); only a successfully read zero-block ballot keeps _zero_findings_from_context
  - From Cursor-Innovation: Specify and implement an explicit contract (for example `None`/sentinel for error vs `0` for empty, or a raised error caught by `_prepare_pruned_ballot`) and route only the empty case to `_zero_findings_from_context`; route read or parse errors to the panel-failed hard-failure path with the planned tests
  - From Cursor-dyn-Security Sidecar Auditor: Change `_ballot_block_count` (or its caller) to a fail-closed contract: propagate read/parse errors to a hard review-core failure, and reserve the zero-findings branch for a readable ballot with zero headings; add the planned tests for both unreadable ballots and empty ballots


### FINDING_2: Security OOS can still leak into published design logs
- **Reviewer(s)**: Cursor-Arch, Codex-dyn-Security Sidecar Auditor
- **Severity**: important
- **Concern**: The design-log publish exclusion only covers the sidecar file path in one place, but security OOS content can also be copied into other published design-log artifacts or nested copies, so the private-sidecar guarantee is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add security-oos-observations.md to _PUBLISH_EXCLUDE_NAMES (depth-invariant), keep top-level writers unchanged, and extend test_design_log_publish_flow.py with a nested-copy negative case
  - From Codex-dyn-Security Sidecar Auditor: Extend the plan to keep security OOS out of every published design-log artifact that can contain the sidecar content, for example classify and split security OOS before writing findings-oos*.md/ballot.txt, or exclude/redact those artifacts when they contain security OOS; add the publish test for this path


### FINDING_8: Security-sidecar checkpoint handling needs rc=3 semantics and real mixed-case coverage
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Security Sidecar Auditor
- **Severity**: important
- **Concern**: The mixed security-sidecar path still treats non-zero checkpoint outcomes as a generic failure or only tests the stubbed success path, so `security_sidecar_present` can be masked, misrouted, or mislabeled instead of flowing through the intended `rc=3` stall path with public filing preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Update the plan to update this test (or fold it into the new mixed-case test) to drive the real checkpoint, assert public `issue create-one` filing, `status=security_sidecar_present`, non-zero rc, and `NEXT_ACTION=oos-pipeline` via pre-driver rather than `rc == 0`
  - From Cursor-Pragmatic: Update that test (or fold it into the new mixed-case test) to call real disposition_checkpoint_main assert public issue filing and security_sidecar_present with non-zero rc and filed URLs in the JSON payload instead of expecting rc==0 via a stubbed checkpoint success
  - From Cursor-Pragmatic: Add skills/implement/scripts/test-oos-disposition-gate.sh and skills/implement/scripts/oos-disposition-checkpoint.md to the plan with rc=3 semantics (security-sidecar-present stall not validation hard-fail) and update the security-sidecar case to expect rc=3 and the new stderr contract
  - From Cursor-Requirements: Special-case checkpoint.returncode==3: emit status security_sidecar_present, return rc 3, set step9a1_stamped=false, and still write run statistics when filed URLs exist; add mixed-case assertions in python/tests/issue/test_oos_filer.py
  - From Cursor-dyn-Security Sidecar Auditor: In `test_oos_filer.py` mixed-case coverage (plan items 9-10), assert `cmd_file` returns `3` (not `0`) with `status=security_sidecar_present` after public filing; keep `test_implement_dispatch.py` asserting `NEXT_ACTION=oos-pipeline` for that exit code
  - From Cursor-dyn-Security Sidecar Auditor: Update that test in the same change: drive the real `disposition-checkpoint` path (or stub `checkpoint_rc=3`) and assert public filing still succeeds while JSON status is `security_sidecar_present` and exit code is `3`


### FINDING_9: Agreement rows still use the pre-reclassification result for OOS items
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The agreement scoreboard still derives its row from the in-scope classification result even when the item is ultimately OOS, so accepted OOS items can appear neutral in diagnostics and misstate the ledger outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: When computing the agreement row use classify_oos_result (or equivalent accepted OOS result) whenever is_oos or neutral_rescued will mark the item OOS and add a focused regression in python/tests/review/test_review_tally.py on the Voter Agreement Scoreboard not only findings-classification.tsv


### FINDING_1: Oversized cap=1 test retargets the wrong module
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Item 3 is aimed at a `cap=1` rollup/summarization invariant, but the plan points the work at `python/tests/review/test_plan_review.py`, which has no oversized-filing coverage. The actual oversized/multi-part split and cap=1 rollup tests live in `python/tests/issue/test_oos_filer.py`, so the current retarget risks a no-op or unrelated churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Move the item 3 test work to python/tests/issue/test_oos_filer.py: tighten or rename the cap=1 rollup test (test_capped_oversized_rollup_files_one_summarized_issue / test_cap_one_oversized_single_item_is_summarized_without_split) and drop the unrelated multi-part split assertion from the misleading test; remove the test_plan_review.py oversized-filing bullet.
  - From Cursor-Innovation: Move item 3 to python/tests/issue/test_oos_filer.py: tighten/rename the cap=1 summarization test and keep multi-part split coverage explicitly scoped to OOS_ISSUES_PER_RUN_CAP=99 (or drop the misleading docstring). Remove the misplaced test_plan_review.py oversized retarget.
  - From Cursor-Pragmatic: Point Item 3 at python/tests/issue/test_oos_filer.py: rename or tighten test_body_files_for_item_oversized_body_is_split docstring/scope so it no longer reads like the cap=1 rollup invariant test, and reference the existing cap=1 rollup tests as the authoritative coverage. Drop the test_plan_review.py oversized retarget.


### FINDING_2: Missing design-side one-YES OOS acceptance assertion
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan lacks a focused test proving that a two-judge OOS tally with exactly one YES is accepted into `oos-accepted-design.md`. Existing tally coverage exercises OOS voting, but it does not assert the accepted design-side sink contents, so `accept_oos` regressions on the design path could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a focused plan-review tally test (2 voters, OOS item with YES/NO split, eligible=2) that asserts the item is accepted and its body appears in oos-accepted-design.md, not only in voting-tally.md or classification TSV.
  - From Cursor-Innovation: Add an explicit approach item and `test_plan_review.py` coverage: two-judge tally with `OOS_*` receiving exactly one YES, assert the block lands in `oos-accepted-design.md` (not only `oos.md` or the scoreboard).
  - From Cursor-Pragmatic: Add an explicit plan step and test_plan_review.py change: extend or add a two-judge OOS tally test that asserts the one-YES OOS block is written to oos-accepted-design.md (and classification Result=accepted), guarding accept_oos regressions on the design path.


### FINDING_4: Checkpoint harness still hard-codes rc=2 for the security sidecar case
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The bash regression harness for `skills/implement/scripts/test-oos-disposition-gate.sh` still asserts the old `rc=2` / validation-failure behavior for the security-sidecar-only case. If the checkpoint change returns `rc=3` with distinct logging, the harness will fail until it is updated in lockstep, and it will continue documenting the old contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update test-oos-disposition-gate.sh (and its .md contract if needed) for the rc=3 security-sidecar-present path: expect exit 3, keep mixed public-plus-sidecar cases on rc=2 when non-security disposition is unresolved, and align stderr/execution-issues assertions with the new distinct log entry from disposition_checkpoint_main.
  - From Cursor-Innovation: Add `skills/implement/scripts/test-oos-disposition-gate.sh` (and its `.md` sibling if present) to **Files to modify/create**, update the security-sidecar case to expect rc=3 with the new log text, and add a mixed public+security case that still returns rc=2 when non-security filing evidence is missing.
  - From Cursor-Pragmatic: Update the security-sidecar checkpoint case to expect rc=3 and the new log message, or add a parallel mixed-case case; list skills/implement/scripts/test-oos-disposition-gate.sh under Files to modify if residual bash stays authoritative.


