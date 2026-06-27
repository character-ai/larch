### FINDING_1: `merge-ci-not-ready` STALL_STEP not registered in stall_recovery
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation
- **Severity**: blocking
- **Concern**: The plan introduces `STALL_STEP=merge-ci-not-ready`, but `stall_recovery.py` only recognizes steps such as `merge-loop-iteration-cap`, numeric steps, and related allowlist entries. Downstream validation, sanitization (`_safe_step`), and classification will collapse the new step to `unknown`, so operators lose the intended CI-not-ready stall reason and recovery routing parity with existing terminal steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add python/larch/state/stall_recovery.py to Files to modify/create: whitelist merge-ci-not-ready in _safe_step beside merge-loop-iteration-cap; classify it in _classify_text as unrecoverable/none/terminal-step; extend python/test_stall_recovery.py
  - From Codex-Arch: Either reuse the existing recognized step name, or extend _safe_step and any step-specific recovery mapping to accept merge-ci-not-ready
  - From Cursor-Innovation: Add ### UPDATED: python/larch/state/stall_recovery.py: allowlist merge-ci-not-ready in _safe_step (or use a 12-* substep token that already matches _safe_step), add a _classify_text branch returning transient-infra/step8-shippr (pending CI may clear), and extend python/test_stall_recovery.py classify coverage for the new step.
  - From Codex-Innovation: Either keep the existing `merge-loop-iteration-cap` step and encode the CI bucket in the detail, or update `python/larch/state/stall_recovery.py` step validation/classification allowlists to accept `merge-ci-not-ready`.

### FINDING_2: `pr_checks_not_ready_detail` output must be order-stable
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: GitHub JSON row order can vary. If blocking-check detail strings depend on row order, the unchanged-detail stall guard can reset `ci_not_ready_count` each loop (e.g. `lint=pending,test=pending` vs reversed) and never trip, letting the run spin to `SHIP_MERGE_LOOP_MAX_ITERATIONS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify stable formatting in the gh.py plan: sort blocking rows by name before emitting name=bucket tokens; add a test that permuted JSON row order yields identical detail strings

### FINDING_3: `pr_checks_not_ready_detail` must stay aligned with `pr_checks_all_pass`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds a separate checks-read and formatting path for `pr_checks_not_ready_detail` alongside `pr_checks_all_pass`. JSON gating, transient-error handling, text fallback, and blocking-row selection can drift, so stall diagnostics may disagree with why `merge_pr` returned `CI_NOT_READY` and the unchanged-detail counter may not advance reliably.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require the text fallback path in pr_checks_not_ready_detail to reuse _CHECKS_TEXT_BAD_RE or one shared helper; add a test that all-pass and detail agree on cancelled/skipping/in_progress samples
  - From Cursor-Innovation: Specify that pr_checks_not_ready_detail uses JSON classification only when pr_checks_read.returncode==0 (same order as pr_checks_all_pass), then text fallback; add a test for non-zero JSON stdout with blocking buckets.
  - From Cursor-Pragmatic: Share one internal checks-read classifier used by both `pr_checks_all_pass` and `pr_checks_not_ready_detail` (same JSON-first, transient-net, text-fallback order). Have the detail helper derive its string from the same blocking rows the gate used.

### FINDING_4: CI-not-ready terminal stall omits post-PR snapshot and PR context
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The new CI-not-ready threshold branch can return `Outcome.STALLED` without the terminal-path side effects other merge-loop stalls perform. The run may skip `_publish_post_pr_terminal_snapshot`, lose final log capture, and return a less useful CLI result than the existing `merge-loop-iteration-cap` stall path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Mirror the merge-loop-iteration-cap branch: write the terminal state, call _publish_post_pr_terminal_snapshot(...), and return ShipResult with the PR context fields filled in
  - From Cursor-Requirements: In the CI_NOT_READY threshold branch, mirror merge-loop-iteration-cap: call _write_terminal_state with current iteration counters, call _publish_post_pr_terminal_snapshot(runner, ctx=working, cwd=repo_root), then return ShipResult(Outcome.STALLED, detail=...)

### FINDING_5: Mergeable/race diagnostic must not count toward unchanged-detail stall threshold
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: When `merge_pr` returns `CI_NOT_READY` but `pr_checks_not_ready_detail` reports no fail/pending rows (mergeable-policy/race path), the unchanged-detail counter can still increment. Three tight retries may return `Outcome.STALLED` even though checks are mergeable and a later attempt would succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Do not increment ci_not_ready_count (or reset it) when the detail is the mergeable-policy/race message; only count stable blocking diagnostics such as name=bucket for fail/pending. Add a ship regression test for repeated race details without stall.

### FINDING_6: `ci_not_ready_count` must reset when HEAD changes or monitor is skipped
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan resets `ci_not_ready_count` only when `monitor.action` is not `merge`/`already_merged`. The merge loop also continues without monitor on phase14 rebase, `MERGE_RESULT_MAIN_ADVANCED` rebase, and CI-fix / `goto_rebase` paths that change HEAD. A counter left at 2 from pre-rebase `CI_NOT_READY` retries can hit threshold=3 on the first post-rebase merge even though CI was reset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: A reset guard whenever HEAD changes or before any path that skips monitor (phase14 rebase, MAIN_ADVANCED rebase, monitor `goto_rebase` / `did_fixing`). Pin the sites in the ship.py plan section or reset at loop top when `current_head != last_ci_not_ready_head`.

### FINDING_7: Missing regression test for `CI_NOT_READY` plus `REVIEW_REQUIRED`
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Without a test on the converted branch, the new guard could accidentally turn review-blocked PRs into `STALLED` instead of `NEEDS_USER_INPUT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a ship regression test that stubs merge.merge_pr to CI_NOT_READY and gh.pr_review_decision to REVIEW_REQUIRED, and assert NEEDS_USER_INPUT with NEEDS_USER_REVIEW_REQUIRED.

### FINDING_8: Missing validation that not-ready diagnostic is single-line and capped
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: If the helper returns multiline or overlong text, the new ship detail can break state-file or JSON parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a gh test that feeds multiline and long check output into the helper and asserts the returned diagnostic has no newline and is truncated to MERGE_DIAGNOSTIC_MAX_LEN.

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17-22,45-63
- **Concern**: [SCOPE-REDUCTION] The new 3-attempt CI_NOT_READY stall guard adds a new early-fail contract that the bug report does not require.. Scenario: Slow or eventually-consistent PRs can now stop as STALLED after three identical not-ready reads even though the current loop would have progressed.
- **Proposed resolution**: Remove the threshold and guard, and keep only the mergeability-policy fix so ship preserves its existing retry contract.

### FINDING_10:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/git/gh.py:751-839; python/larch/implement/ship.py:2161-2188; python/larch/core/config.py:492
- **Concern**: [SCOPE-REDUCTION] The plan adds a new diagnostic helper, config threshold, and early merge-ci-not-ready stall path even though the chosen policy already fixes the specified skipped/cancelled/neutral/unknown loop by aligning pr_checks_all_pass with ci_monitor.. Scenario: The extra guard creates a new terminal STALLED path for racy or generic CI_NOT_READY reads and expands the patch beyond the minimum required feature path.
- **Proposed resolution**: Drop the new helper, threshold, ship guard, and related tests unless the plan switches to a non-mergeable policy for skipped or neutral checks. Limit the firm change to the gh.py mergeability policy alignment and focused regression coverage.

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-Ci Merge Semantics Reviewer
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:17-22,50-63; python/larch/state/stall_recovery.py:1402-1410,1434-1464,434-441
- **Concern**: [SCOPE-REDUCTION] Emitting `STALL_STEP=merge-ci-not-ready` adds a new terminal label that the repo's stall-recovery validator does not accept. `validate_terminal_state` will reject the state, and `_safe_step_value` will round-trip it as `unknown`, so the new stall reason cannot be validated or recovered through the existing tooling.. Scenario: Ship will write the planned terminal state, but downstream stall recovery and reporting will lose the new reason or fail validation, so the new stall path is not round-trippable.
- **Proposed resolution**: Either reuse the already-recognized `merge-loop-iteration-cap` step, or add `merge-ci-not-ready` to the stall-recovery allowlist/classifier and tests before shipping it.
