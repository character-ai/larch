### FINDING_1: Duplicate bootstrap harness cases
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-dyn-harness-stub-reuse, Codex-dyn-harness-stub-reuse
- **Severity**: important
- **Concern**: The plan asks to add bootstrap harness cases and sibling documentation rows for non-OPEN issue state and resume-without-issue-number, but those cases already exist as B7-non-open-state and B-issue-required-for-resume. Implementing Item C literally would duplicate coverage and expand a SIMPLE-tier change without adding a new invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Drop Item C from this PR; keep docs/linting.md pointer to test-implement-bootstrap.md as the case index (Item E).
  - From Codex-Arch: Drop the duplicate case additions from the plan, or revise Item C to only verify the existing cases still pass
  - From Cursor-Innovation: Re-landing duplicate cases inflates the harness (~30 lines) and the sibling .md table without new behavioral coverage. Drop Item C from the implementation plan; keep the existing B6/B7/B-issue-required-for-resume cases and limit Item C to docs/linting.md freshness if needed.
  - From Codex-Innovation: Revise Item C to verification-only for these two cases and skip edits to the harness/doc rows unless the existing assertions are insufficient
  - From Codex-Pragmatic: Drop this proposed new case and keep the existing B7-non-open-state coverage
  - From Codex-Pragmatic: Drop this proposed new case and keep the existing B-issue-required-for-resume coverage
  - From Cursor-dyn-harness-stub-reuse, Codex-dyn-harness-stub-reuse: Drop Item C's add-test/add-doc-row work from the plan, or rewrite it as a verification-only note that these cases already satisfy the requested coverage.

### FINDING_2: Step 0 tracking marks would be duplicated and break bootstrap assertions
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements, Codex-Requirements, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-ledger-call-contract, Codex-dyn-ledger-call-contract
- **Severity**: important
- **Concern**: The plan moves Step 0 tracking ledger marks into bootstrap but leaves existing prompt-side SKILL.md marks and/or harness assertions that bootstrap emits no marks. Successful adopt/resume paths would record duplicate same-name Step 0 tracking boundaries, and `make test-implement-bootstrap` would fail on stale negative assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch, Cursor-Requirements, Codex-Requirements: Migrate ownership atomically: add the bootstrap marks, remove or gate the SKILL.md prompt-side mark block, and update the GP-adopt assertions to expect the bootstrap-owned mark exactly once
  - From Codex-Innovation: Update those assertions to expect the new marks, or remove the obsolete negative checks
  - From Cursor-Pragmatic: Emit the two marks only on repo-unavailable/forked skip paths, or drop the SKILL.md:683-686 block once bootstrap owns tracking attribution; do not land both unconditional top-of-phase_tracking marks and the existing orchestrator marks
  - From Codex-Pragmatic: Revise the GP-adopt assertions to expect the new Step 0 tracking issue marks, and optionally add skip-branch assertions only if needed
  - From Cursor-dyn-ledger-call-contract, Codex-dyn-ledger-call-contract: Extend the plan to update skills/implement/SKILL.md so bootstrap owns this mark exactly once: remove or disable the prompt-side token/timing mark calls and adjust the surrounding ownership prose/comments accordingly

### FINDING_3: Corrupt-zero token warning conflicts with current Cost: N/A rendering
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan says corrupt all-zero token data should report `$0.00`, but current `write-final-report.sh` treats zero totals and zero buckets as unavailable token data and renders `Cost: N/A`. A warning or test expecting `$0.00` would contradict the existing missing-token-data contract unless the rendering path changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Change the warning text to match the preserved behavior, or explicitly plan the broader rendering/test/doc changes needed to make $0.00 the intended output
  - From Cursor-Edge, Codex-Edge: Align the plan to one contract: either change the warning/test to N/A and keep rendering unchanged, or explicitly set TOKEN_DATA_AVAILABLE=true for schema-present all-zero reports if Round 1 requires $0.00
  - From Codex-Innovation: Choose one contract: either change the warning to match N/A, or explicitly keep TOKEN_DATA_AVAILABLE true for this corrupt-zero path and add a focused test that proves the summary reports $0.00
  - From Codex-Pragmatic: Align the plan with the existing contract by warning about Cost: N/A, or explicitly set TOKEN_DATA_AVAILABLE=true for the corrupt-zero branch if $0.00 is the required output

### FINDING_4: Docs freshness plan preserves a drift-prone Step 0 range
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Requirements, Codex-Requirements
- **Severity**: latent
- **Concern**: The plan replaces one hardcoded Step 0 call range in `docs/linting.md` with another, so the documentation can drift again as Step 0 changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge, Cursor-Requirements, Codex-Requirements: Remove the parenthetical range entirely or replace it with a non-counted phrase, then keep the harness doc as the source of truth

### FINDING_5: Proposed PATH stub would not affect get-issue-state invocation
- **Reviewer(s)**: Cursor-dyn-harness-stub-reuse, Codex-dyn-harness-stub-reuse
- **Severity**: important
- **Concern**: The plan says to provide a PATH stub for `get-issue-state.sh`, but `implement-bootstrap.sh` invokes it through `$SCRIPT_DIR/get-issue-state.sh`. A PATH-only stub would not affect the call and would keep seeing the existing sandbox script default state instead of the intended LOCKED/non-OPEN state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-stub-reuse, Codex-dyn-harness-stub-reuse: Revise Case 1 to reuse the existing $SANDBOX/scripts/get-issue-state.sh stub by setting LARCH_TEST_ISSUE_STATE=LOCKED or another non-OPEN/non-CLOSED value; do not add a PATH-only stub.

### FINDING_6: Stderr-only corrupt-zero warning may not reach operators
- **Reviewer(s)**: Cursor-dyn-stderr-reach, Codex-dyn-stderr-reach
- **Severity**: important
- **Concern**: The plan relies on `write-final-report.sh` stderr for the corrupt-zero warning, but current callers may quiet, capture, or discard stderr, while Step 17 chat emission replays `summary-final.md`. Operators may never see a warning emitted only to stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stderr-reach, Codex-dyn-stderr-reach: Make the warning part of the rendered final-summary body as the primary path, not a contingency; use notes_tmp or explicit render-run-summary support, with stderr only as secondary diagnostic output.

### FINDING_7: All-three-zero jq logic may warn for absent vendor sections
- **Reviewer(s)**: Cursor-dyn-stderr-reach, Codex-dyn-stderr-reach
- **Severity**: important
- **Concern**: The proposed all-three-zero jq logic collapses absent Codex/Cursor totals to zero. A valid single-agent report with only Claude totals at zero could satisfy the corrupt-zero condition even though the other vendors did not structurally run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stderr-reach, Codex-dyn-stderr-reach: Gate the corrupt-zero warning on explicit vendor-section presence for any vendor counted as zero, or explicitly exempt absent codex/cursor sections before evaluating all-three-zero.
