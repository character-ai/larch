### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/state/stall_recovery.py:121-122,440-441
- **Concern**: Plan adds STALL_STEP merge-ci-not-ready but omits stall_recovery registration merge-loop-iteration-cap already has. Scenario: Step 18a classify sanitizes unknown steps; reports show STALL_STEP unknown and miss terminal-step parity with merge-loop-iteration-cap
- **Proposed resolution**: Add python/larch/state/stall_recovery.py to Files to modify/create: whitelist merge-ci-not-ready in _safe_step beside merge-loop-iteration-cap; classify it in _classify_text as unrecoverable/none/terminal-step; extend python/test_stall_recovery.py

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:751-766,python/larch/implement/ship.py:2162-2188
- **Concern**: Unchanged-detail stall guard needs deterministic pr_checks_not_ready_detail output. Scenario: Gh JSON row order can vary; blocking checks: lint=pending,test=pending vs reversed resets ci_not_ready_count each loop and the guard never trips; run still spins to SHIP_MERGE_LOOP_MAX_ITERATIONS
- **Proposed resolution**: Specify stable formatting in the gh.py plan: sort blocking rows by name before emitting name=bucket tokens; add a test that permuted JSON row order yields identical detail strings

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/git/gh.py:785-794,820-839
- **Concern**: Plan adds separate text matching for pr_checks_not_ready_detail alongside _CHECKS_TEXT_BAD_RE. Scenario: A second text policy in the diagnostic helper can drift from _pr_checks_text_all_pass; JSON/text disagreement the plan warns about can reappear inside gh.py alone
- **Proposed resolution**: Require the text fallback path in pr_checks_not_ready_detail to reuse _CHECKS_TEXT_BAD_RE or one shared helper; add a test that all-pass and detail agree on cancelled/skipping/in_progress samples

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:2162-2188
- **Concern**: CI-not-ready stall branch skips the normal terminal-path side effects. Scenario: The new threshold branch can return Outcome.STALLED without publishing the post-PR snapshot or populating pr_number/pr_url, so the run loses final log capture and the CLI result is less useful than the existing merge-loop cap stall
- **Proposed resolution**: Mirror the merge-loop-iteration-cap branch: write the terminal state, call _publish_post_pr_terminal_snapshot(...), and return ShipResult with the PR context fields filled in

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/state/stall_recovery.py:118-140,410-423,1992-1999
- **Concern**: New terminal step merge-ci-not-ready is not recognized by the existing step allowlist and sanitizers. Scenario: Downstream stall-recovery and reporting will collapse the new step to unknown, so the semantic CI-not-ready reason the plan adds is lost as soon as other tooling reads the state
- **Proposed resolution**: Either reuse the existing recognized step name, or extend _safe_step and any step-specific recovery mapping to accept merge-ci-not-ready

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/state/stall_recovery.py:118-125
- **Concern**: The plan introduces STALL_STEP=merge-ci-not-ready but does not update stall_recovery allowlist or classify routing.. Scenario: Step 18 classify runs _safe_step_value on the step; merge-ci-not-ready is not in the explicit set or numeric/substep regex, so it is sanitized to unknown and _classify_text falls through to unrecoverable/none. Operators lose the intended stall reason and get RESUME_HINT=none instead of a ship retry path.
- **Proposed resolution**: Add ### UPDATED: python/larch/state/stall_recovery.py: allowlist merge-ci-not-ready in _safe_step (or use a 12-* substep token that already matches _safe_step), add a _classify_text branch returning transient-infra/step8-shippr (pending CI may clear), and extend python/test_stall_recovery.py classify coverage for the new step.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:820-839
- **Concern**: pr_checks_not_ready_detail is not specified to mirror pr_checks_all_pass JSON gating on returncode==0.. Scenario: If pr_checks_read exits non-zero, the helper may still treat stdout as mergeable JSON while pr_checks_all_pass already fell through to text/transient-false, producing diagnostics that disagree with the merge gate and polluting the unchanged-detail stall counter.
- **Proposed resolution**: Specify that pr_checks_not_ready_detail uses JSON classification only when pr_checks_read.returncode==0 (same order as pr_checks_all_pass), then text fallback; add a test for non-zero JSON stdout with blocking buckets.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:2162-2188
- **Concern**: The unchanged-detail stall counter does not carve out the planned mergeable/race diagnostic.. Scenario: When merge_pr returns CI_NOT_READY but pr_checks_not_ready_detail reports no fail/pending rows (race path in Edge cases), three tight retries can return Outcome.STALLED even though checks are mergeable and a later attempt would succeed.
- **Proposed resolution**: Do not increment ci_not_ready_count (or reset it) when the detail is the mergeable-policy/race message; only count stable blocking diagnostics such as name=bucket for fail/pending. Add a ship regression test for repeated race details without stall.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:2162-2188
- **Concern**: Writes a new STALL_STEP value that the durable-stall validator/classifier does not accept.. Scenario: Ship will emit STALL_STEP=merge-ci-not-ready, but `python/larch/state/stall_recovery.py` still only recognizes `merge-loop-iteration-cap`, `rebase-failed`, `bump-branch-guard`, and numeric steps. Validation/classification will downgrade the state to unknown or fail validation, so the new CI-not-ready terminal reason is lost.
- **Proposed resolution**: Either keep the existing `merge-loop-iteration-cap` step and encode the CI bucket in the detail, or update `python/larch/state/stall_recovery.py` step validation/classification allowlists to accept `merge-ci-not-ready`.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship.py:1973-2214
- **Concern**: CI-not-ready guard reset only on non-merge monitor paths; head-changing continues skip reset. Scenario: The plan resets `ci_not_ready_count` only when `monitor.action` is not `merge`/`already_merged`. The merge loop also `continue`s without monitor on phase14 rebase (`:1973-1988`), after `MERGE_RESULT_MAIN_ADVANCED` rebase (`:2189-2214`), and after CI-fix / `goto_rebase` paths that change HEAD. A counter left at 2 from pre-rebase `CI_NOT_READY` retries can hit threshold=3 on the first post-rebase merge even though CI was reset.
- **Proposed resolution**: A reset guard whenever HEAD changes or before any path that skips monitor (phase14 rebase, MAIN_ADVANCED rebase, monitor `goto_rebase` / `did_fixing`). Pin the sites in the ship.py plan section or reset at loop top when `current_head != last_ci_not_ready_head`.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:820-839
- **Concern**: pending `pr_checks_not_ready_detail` read path may diverge from `pr_checks_all_pass`. Scenario: The diagnostic helper is specified as its own `pr_checks_read` + formatter flow. `pr_checks_all_pass` returns `False` on transient JSON read errors without trying text (`:832-833`). If the helper falls through to text or formats JSON differently, stall detail can disagree with why `merge_pr` returned `CI_NOT_READY`, and the unchanged-detail counter may not advance when the operator sees the same stuck bucket.
- **Proposed resolution**: Share one internal checks-read classifier used by both `pr_checks_all_pass` and `pr_checks_not_ready_detail` (same JSON-first, transient-net, text-fallback order). Have the detail helper derive its string from the same blocking rows the gate used.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship.py:2110-2125
- **Concern**: The new merge-ci-not-ready terminal stall omits the post-PR snapshot step that every other merge-loop STALLED exit performs. Scenario: Every other terminal stall in this loop (including merge-loop-iteration-cap at :2119 and merge errors at :2268/:2286) calls _publish_post_pr_terminal_snapshot before returning Outcome.STALLED; the plan only says write terminal state and return STALLED for the CI-not-ready threshold path, so an implementer following the plan may skip the flush/push and leave run logs and finalize artifacts inconsistent with the stall the issue is replacing
- **Proposed resolution**: In the CI_NOT_READY threshold branch, mirror merge-loop-iteration-cap: call _write_terminal_state with current iteration counters, call _publish_post_pr_terminal_snapshot(runner, ctx=working, cwd=repo_root), then return ShipResult(Outcome.STALLED, detail=...)

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:23-25,56-63,79-91
- **Concern**: Missing regression test for the CI_NOT_READY plus REVIEW_REQUIRED path.. Scenario: Without a test on the converted branch, the new guard could accidentally turn review-blocked PRs into STALLED instead of NEEDS_USER_INPUT.
- **Proposed resolution**: Add a ship regression test that stubs merge.merge_pr to CI_NOT_READY and gh.pr_review_decision to REVIEW_REQUIRED, and assert NEEDS_USER_INPUT with NEEDS_USER_REVIEW_REQUIRED.

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:35-43,74-77,87-89
- **Concern**: Missing validation that the new not-ready diagnostic is single-line and capped.. Scenario: If the helper returns multiline or overlong text, the new ship detail can break state-file or JSON parsing.
- **Proposed resolution**: Add a gh test that feeds multiline and long check output into the helper and asserts the returned diagnostic has no newline and is truncated to MERGE_DIAGNOSTIC_MAX_LEN.
