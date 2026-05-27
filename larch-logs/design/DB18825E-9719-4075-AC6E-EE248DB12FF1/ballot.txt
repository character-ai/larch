### FINDING_1: Branch 2 contract docs still describe old rename ordering
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-contract-table-drift, Codex-dyn-contract-table-drift
- **Severity**: important
- **Concern**: The runtime contract documentation still says Branch 2 performs log/posting work before the implementing rename and that `POSTED=false` means no rename, but the proposed behavior moves the rename earlier and allows `POSTED=false` after the title has already changed. This leaves `skills/implement/SKILL.md` and related bootstrap docs misleading for operators, reviewers, and future maintainers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add skills/implement/SKILL.md to Files to modify: row 701 should list rename immediately after OPEN validation (before RUN_ID derivation / larch-log init / post-tracking); row 702 should state rename runs, no sentinel, DEFERRED=true
  - From Cursor-Edge: Update rows 701–702 in the same PR (rename before init/post; `POSTED=false` → rename occurred, `DEFERRED=true`, no sentinel) per the plan’s own failure-mode #1—two-line doc fix, no new logic
  - From Codex-Edge: Update the Bootstrap behavior map in skills/implement/SKILL.md to match the new ordering and the POSTED=false behavior, or keep the implementation consistent with the existing documented contract.
  - From Cursor-Innovation: Add the smallest SKILL.md table edit: Branch 2 open issue should state rename happens after OPEN/non-PR validation before RUN_ID/log/post, and the POSTED=false row should say no sentinel, rename already attempted, DEFERRED=true
  - From Cursor-Pragmatic: Update the Branch 2 open issue row to place best-effort implementing rename immediately after OPEN/non-PR validation, and update the POSTED=false row to state no sentinel but rename already attempted
  - From Codex-Requirements: Add skills/implement/SKILL.md to the updated files and revise rows 701-702 so Branch 2 shows the implementing rename immediately after OPEN/non-PR validation and removes the POSTED=false "no rename" claim.
  - From Cursor-dyn-contract-table-drift: Add skills/implement/SKILL.md and scripts/implement-bootstrap.md to Files to modify/create, update the Branch 2 behavior rows to show rename immediately after OPEN/non-PR validation and before RUN_ID/log/post, remove the POSTED=false "no rename" claim, and replace the grep mitigation with terms that catch "no rename", "post-tracking-issue", and "stalled rename".

### FINDING_2: Early POSTED=false rename can block fresh implement retry
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Requirements
- **Severity**: important
- **Concern**: Moving the Branch 2 rename before `post-tracking-issue.sh` can leave an issue titled `[IMPLEMENTING]` without `parent-issue.md` when `POSTED=false` defers metadata adoption. A later fresh `/implement` session then hits the managed-prefix admission guard and exits 5, regressing the current retryable `[DESIGNED]` defer path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add an explicit plan step: either a minimal admission carve-out for this defer recovery (e.g. pass when `larch:plan` is present and metadata was never adopted), or document that operators must preserve `IMPLEMENT_TMPDIR` and re-enter via `--resume-plan-tail` / manual title revert—do not rely on a fresh `/implement` alone
  - From Codex-Edge: Revise the Branch 2 failure contract before moving the rename: either keep the POSTED=false path retryable by not renaming before successful sentinel publication, or add a narrow recovery-preserving contract for this adopted-deferred state and cover it with a regression test.
  - From Cursor-Requirements: Document in plan Edge cases; gate rename until POSTED=true, or add minimal title rollback on POSTED=false defer (feature-description reset AC)
  - From Cursor-Requirements: Either gate rename until posted=true (keeps defer path at [DESIGNED]), or add the feature-description reset on defer/failure paths; at minimum document the admission break in Edge cases

### FINDING_3: B4 POSTED=false variants lack positive rename coverage
- **Reviewer(s)**: Cursor-dyn-b4-variant-coverage, Codex-dyn-b4-variant-coverage
- **Severity**: latent
- **Concern**: The B4-plan and B4-all tests do not currently assert that the early implementing rename was invoked. If Branch 2 adoption is changed so the main B4 path passes but these POSTED=false variants miss the rename, the tests can still pass because they only verify issue view and persisted flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-b4-variant-coverage: Add assert_contains "tracking-issue-write rename --issue 123 --state implementing" checks after the invoke reads in B4-plan and B4-all, keeping the existing gh/persist assertions.
