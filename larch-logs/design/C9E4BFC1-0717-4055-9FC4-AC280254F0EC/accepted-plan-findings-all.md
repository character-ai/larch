### FINDING_1: Coverage gate misses non-complete paths and later edits
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Workflow Gate Integrator
- **Severity**: major
- **Concern**: Coverage/disposition are only computed on external STATUS=complete, so claude_fallback, recovery, and post-disposition edits can reach Step 8 with a missing or stale plan-coverage.env/disposition record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Main-agent or recovery commits can leave most firm headings untouched with no todos_left manifest field yet still reach ship pre-driver because only the Codex/Cursor complete envelope sets PLAN_COVERAGE_DISPOSITION_REQUIRED Extract coverage into scope_disposition.py and invoke it from dispatch_step2 on external complete and from the Step 4 commit leg in dispatch_commit_route.py or checks-commit-route after claude_fallback or recovery commits; add SKILL.md disposition prompt after post-dispatch on complete and after Step 4 on claude paths before Step 5
  - From Cursor-Innovation: Add a shared implement scope-disposition compute fence after main-agent implementation (before Step 3) on the claude_fallback and recovery paths; persist plan-coverage.env and branch on PLAN_COVERAGE_DISPOSITION_REQUIRED the same as the external complete path.
  - From Cursor-Pragmatic: Add a shared implement scope-disposition compute/write used by `dispatch_step2.py` on `STATUS=complete` and by a new post-2.4 launcher fence (after `normalize-coder-scout` / recovery-path capture) for `claude_fallback` and recovery. Persist `plan-coverage.env` and surface `PLAN_COVERAGE_*` / `PLAN_COVERAGE_DISPOSITION_REQUIRED` to the Step 2 orchestrator before Step 3 on every implementation path.
  - From Cursor-Requirements: Add a shared scope_disposition coverage entry point and invoke it from Step 2.4 after main-agent edits (and emit the same KVs/artifacts) before the disposition prompt; keep dispatch_step2 integration for external complete only.
  - From Cursor-Requirements: After recovery scope-check succeeds, run the same coverage summary against Step 0 plan.txt and recovered touched paths; require disposition when high band or todos_left would have tripped on a normal complete dispatch.
  - From Cursor-dyn-Workflow Gate Integrator: Add one shared implement scope-disposition compute step (same module as dispatch) invoked after Step 2.4 edits and before Step 3, comparing Step 0 plan.txt to post-commit touched paths. Persist plan-coverage.env and reuse the same Step 2 disposition prompt and recording flow. Pin with a claude_fallback or self-implement dispatch test.
  - From Cursor-dyn-Workflow Gate Integrator: After step2-impl (and any post-disposition implementation edits), rerun scope-disposition compute before Step 3 continuation or before ship. If fingerprint differs from scope-disposition.env, invalidate disposition and require a fresh operator choice. Add a stall-recovery test that edits after proceed-partial and asserts ship refuses until recomputed.


### FINDING_2: halt-scope-disposition recovery routing is missing
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-Workflow Gate Integrator
- **Severity**: major
- **Concern**: halt-scope-disposition has no recovery branch back to the Step 2 disposition prompt, so missing scope-disposition.env is treated as terminal failure instead of a re-prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add halt-scope-disposition to the pre-driver branch table: when plan-coverage.env requires disposition and scope-disposition.env is absent or invalid re-enter the Step 2 disposition AskUserQuestion and recording CLI instead of halting as Tool Failure; reserve Tool Failure for artifact tampering mismatch only
  - From Cursor-Innovation: Add halt-scope-disposition handling that re-invokes the Step 2 disposition AskUserQuestion plus implement scope-disposition record when plan-coverage.env requires disposition and scope-disposition.env is absent; only hard-fail when the operator declines bail-rescope.
  - From Cursor-dyn-Workflow Gate Integrator: When pre-driver or ship driver emits halt-scope-disposition and plan-coverage.env shows disposition required with no valid scope-disposition.env, route back to the Step 2 disposition sub-step (read artifacts from disk, not stdout KVs). Document the branch in SKILL.md Step 8 and ship-pr-exit-matrix.md. Tool Failure only when coverage artifacts themselves are missing or invalid.


### FINDING_3: Forced plan-fidelity drops on degraded/TRIVIAL panels
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-dyn-Workflow Gate Integrator
- **Severity**: major
- **Concern**: The forced plan-fidelity reviewer is still Cursor-only, so degraded or TRIVIAL panels can lose it when Cursor is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify forced slot dispatch in review_dispatch_panel.py: append a prune-exempt plan-fidelity-forced row using first-available Codex then Cursor from agents/reviewer-plan-fidelity.md independent of tier pruning; pin a TRIVIAL Codex-only panel test
  - From Codex-Arch: Inject the forced reviewer independently of cursor availability, or add an equivalent fallback slot so every tier always carries it
  - From Cursor-Innovation: When PLAN_FIDELITY_FORCED=true, append a Codex plan-fidelity row from agents/reviewer-plan-fidelity.md when Cursor is absent; keep the existing Cursor lane when present; pin degraded-panel tests.
  - From Codex-Innovation: Add a vendor-neutral fallback for the forced reviewer, or explicitly emit a non-Cursor forced row when Cursor is absent, and cover cursor-unavailable Step 5 cases in tests
  - From Cursor-Pragmatic: Specify forced slot dispatch: inject a dedicated prune-exempt row (e.g. `plan-fidelity-forced`) for the first eligible external tool per tier (Codex on TRIVIAL codex-only, Cursor when present). Pin a `test_review_dispatch_panel.py` case for TRIVIAL+codex-only with `PLAN_FIDELITY_FORCED=true`.
  - From Cursor-dyn-Workflow Gate Integrator: Define a forced prune-exempt row that selects an available tool (Codex and/or Cursor) or duplicates the agent on Codex when Cursor is absent. Mark the row prune-exempt in review_prune.py. Pin TRIVIAL MODERATE HARD tests with Cursor unavailable and middle band tripped.


### FINDING_4: `--self-review` bypasses forced plan-fidelity
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Supported self-review paths skip Step 5 entirely, so middle-band runs never get the forced plan-fidelity check there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Either document an explicit self-review carve-out in docs/workflow-lifecycle.md and drop criterion 3 for that mode or add a bounded inline plan-fidelity pass to self-review.md when plan-coverage.env sets PLAN_FIDELITY_FORCED=true
  - From Cursor-Innovation: When plan-coverage.env has PLAN_FIDELITY_FORCED=true, either block --self-review for that run or extend self-review.md with a mandatory plan-fidelity pass (full plan + untouched inventory) before Step 6; pin the branch in tests.
  - From Cursor-Requirements: Either wire PLAN_FIDELITY_FORCED into self-review.md as a mandatory inline plan-fidelity pass when plan-coverage.env requires it, or document and test an explicit carve-out that middle-band runs with --self-review cannot satisfy acceptance 3.


### FINDING_6: Follow-up issue/dependency handling can deadlock or record too early
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Partial-scope follow-up issues can deadlock or be recorded in the wrong order, because the dependency points at the still-open parent and disposition may be written before the durable follow-up exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Write the disposition only after the follow-up issue and dependency link succeed, or fail closed into bail-rescope/tool-failure when filing fails
  - From Codex-Pragmatic: Cross-link both issues, but make the tracking issue blocked by the follow-up or omit the dependency until the parent can close; do not block the deferred follow-up on a parent issue that remains open.
  - From Codex-Requirements: Make the current tracking issue blocked by the follow-up issue, or specify a temporary current-blocks-follow-up relation plus the later step that removes it after the partial PR lands


### FINDING_7: Coverage read/parse failures stay advisory
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: major
- **Concern**: Unreadable or malformed Step 0 plan/coverage input is still advisory, letting complete dispatch continue without a validated disposition gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Fail closed on plan-coverage read/parse failure, or mark disposition-required and halt ship until the plan can be reread
  - From Codex-Pragmatic: For STATUS=complete with coverage unavailable, fail closed by requiring disposition or routing to Step 12d, and have ship pre-driver reject missing or invalid coverage artifacts before PR creation.


### FINDING_9: `todos_left` is omitted from the final summary
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: The mandatory final summary omits todos_left, so partial scope can disappear from the end-of-run report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Include the todos_left count and bounded detail or artifact reference in the plan-coverage line or an adjacent final-summary line, and test that non-empty todos_left appears there.


### FINDING_12: PR mutation paths bypass disposition gating
- **Reviewer(s)**: Cursor-dyn-Workflow Gate Integrator, Codex-dyn-Workflow Gate Integrator
- **Severity**: major
- **Concern**: The ship PR mutation surface is only gated in pre-driver, so direct PR creation/refresh paths can bypass scope disposition checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Workflow Gate Integrator: Extract validate_disposition_for_ship() and call it from ship_pre_driver_main and from ship.py immediately before every ensure_pr / PR body refresh (pr-create phase and rebase refresh). On failure return NEEDS_USER_INPUT or halt-scope-disposition with non-zero rc. Add a ship.py test where PR_NUMBER is already set and disposition is required but missing.
  - From Codex-dyn-Workflow Gate Integrator: Validate scope disposition inside ship.py before calling `pr.ensure_pr`, and inside `pr.ensure_pr` before `_push_existing_pr` and `push.push_branch`, so every PR create/update path is gated, not just the pre-driver wrapper.


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


