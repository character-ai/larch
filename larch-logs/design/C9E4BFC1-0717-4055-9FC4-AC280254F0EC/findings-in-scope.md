### FINDING_1: Complete disposition must wait for post-dispatch
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `STATUS=complete` can be recorded before `step-2-post-dispatch.sh` settles the branch, which can leave a partial or follow-up disposition attached to a run that never actually reached Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: For STATUS=complete only, run the disposition prompt and recording after POST_DISPATCH_NEXT=continue from step-2-post-dispatch.sh. Keep the pre-Step-3 fence for claude_fallback and recovery paths.
  - From Cursor-Pragmatic: Pin ordering: on STATUS=complete run disposition only after POST_DISPATCH_NEXT=continue succeeds; keep the pre-Step-3 claude_fallback/recovery fence separate

### FINDING_2: Forced plan-fidelity prune exemption needs a wire contract
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The forced plan-fidelity reviewer can still be pruned because the plan does not define a wire-level exemption that `review_prune_filter` recognizes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define a manifest field such as prune_exempt=true on the forced row. In reviewer_prune_filter, skip productivity pruning for that field before the net_prunable and floor_prunable checks. Pin the field in review_dispatch_panel.py and test_review_prune.py.

### FINDING_3: Scope disposition fingerprints and coverage baselines go stale after later edits
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: major
- **Concern**: Disposition validity can drift after Step 5 review commits, Step 7 commit-route success, or checks-repair edits because the validator and coverage source are not clearly tied to a recomputed Step 0 baseline plus current git delta.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make validate_disposition_for_ship recompute coverage from $IMPLEMENT_TMPDIR/plan.txt and the current git delta, then compare that live fingerprint to the recorded disposition. Fail closed when recompute fails on a required-disposition path. Add a stale-fingerprint test in test_ship_pre_driver.py or test_implement_dispatch.py.
  - From Cursor-Pragmatic: Extend the shared scope_disposition fence to Step 5 review commits, Step 7 commit-route success, and checks-repair re-entry; invalidate disposition when fingerprint changes and re-prompt before Step 8
  - From Codex-Pragmatic: Specify that scope_disposition computes touched firm paths from the Step 0 or prelaunch baseline to HEAD plus current uncommitted and untracked paths, then add a focused committed-before-ship coverage test.

### FINDING_4: Missing ship pre-driver test module is misclassified
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The plan points to a test module that does not exist, so the pre-driver coverage cases have no real home.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Change the heading to ### NEW: if splitting tests, or ### UPDATED: python/tests/implement/test_implement_dispatch.py if extending the existing pre-driver tests there. Keep the acceptance cases either way.

### FINDING_5: Missing self-review test module is misclassified
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The plan points to a self-review test module that does not exist, so the forced self-review case has no real home.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Change the heading to ### NEW: python/tests/implement/test_implement_self_review.py, or fold the forced self-review case into an existing Step 5 self-review test module and update that UPDATED path instead.

### FINDING_6: PR footers still emit Closes #N on partial-scope refreshes
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: PR footers on create and refresh still hardcode `Closes #N`, so partial-scope runs can close the tracking issue instead of emitting `Part of #N`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Route the footer through a disposition-aware helper and emit `Part of #N` when the recorded scope disposition is partial.
  - From Cursor-Pragmatic: Route both create and update through a disposition-aware linker (or pass disposition into compose/link helpers) and add the planned existing-PR update test against ensure_pr not only compose_pr_body

### FINDING_7: PR create/body-update bypass disposition validation
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: The live PR create and body-update entrypoints can still mutate PR state without passing the new disposition validator, bypassing the hardened ship gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Wrap both entrypoints with `validate_disposition_for_ship()` or route them through the validated ship helper before `gh.pr_create` / `gh.pr_edit_body_file`.
  - From Codex-Innovation: Call the shared disposition validator before `gh.pr_edit_body_file`, or route body updates through the same helper as `ensure_pr`.

### FINDING_8: Forced plan-fidelity must be wired into self-review
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The authoritative self-review path can still skip the forced plan-fidelity pass when `PLAN_FIDELITY_FORCED` is active, because the normative self-review reference has no forced-flag branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a forced-flag branch in the self-review reference, or block self-review while `PLAN_FIDELITY_FORCED=true` is active.
  - From Cursor-Pragmatic: Add MAY_UPDATE or UPDATED self-review.md with the forced inline plan-fidelity pass or explicit block when PLAN_FIDELITY_FORCED=true, and keep the planned self-review test

### FINDING_9: Step 2 docs still forbid branching on coverage disposition
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The Step 2 stdout contract still says coverage KVs are advisory and must not drive branching, which conflicts with the new disposition gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Update step2-dispatch.md in the firm file list: document new coverage KVs, disposition-required semantics, and that Step 2 now branches on disposition-required output

### FINDING_10: Proceed-partial durability needs tests for follow-up and dependency writes
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: A proceed-partial record can be written before the follow-up issue and dependency links are durably created, so later failures can leave a superficially valid disposition without the required cross-links.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add focused scope_disposition tests that mock issue filing and dependency writes, assert no disposition or run-log batch is recorded until issue number, URL, cross-link, and block relation all succeed, and assert failures leave the run parked or routed to bail-rescope.

### FINDING_11: Ship route-exit needs a scope-disposition halt reason
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: When the ship driver detects a stale or missing disposition, route-exit has no dedicated halt reason to send the run back into the disposition prompt, so it can fall through to operator bail instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add the route-exit part to the plan: define a scope-disposition needs-user reason constant, have the ship/direct-mutation validator return it, map it to NEXT_ACTION=halt-scope-disposition in _classify_ship_needs_user_reason, and add a route-exit test for that driver result.

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:67-70
- **Concern**: [SCOPE-REDUCTION] Follow-up issue filing path does not require the existing issue surface. Scenario: The scope_disposition module is assigned to file the follow-up issue, but the spec requires filing via /issue and repo conventions route issue creation through the existing issue helper. A custom direct gh path can bypass existing redaction, dedup, and dependency semantics while adding new issue-filing logic.
- **Proposed resolution**: Require proceed-partial to call the existing issue creation CLI or module with a body file, then use the existing dependency helper for the block relation. Do not add a second direct issue-create implementation in scope_disposition.py.
