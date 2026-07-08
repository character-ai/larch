### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: External STATUS=complete disposition is ordered before post-dispatch. Scenario: The plan tells SKILL.md to prompt right after Step 2 envelope validation. On STATUS=complete that is before step-2-post-dispatch.sh. An operator can record proceed-partial and file a follow-up, then post-dispatch can bail on branch mismatch and leave a partial disposition on a run that never reached Step 3.
- **Proposed resolution**: For STATUS=complete only, run the disposition prompt and recording after POST_DISPATCH_NEXT=continue from step-2-post-dispatch.sh. Keep the pre-Step-3 fence for claude_fallback and recovery paths.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_prune.py:263-281
- **Concern**: Forced plan-fidelity prune exemption has no wire contract. Scenario: The plan adds a prune-exempt forced row but does not define how review_prune.py recognizes it. reviewer_prune_filter prunes combos with no ledger history and also prunes zero-productivity rows. A forced plan-fidelity reviewer with few or no findings will still drop in round 2 without an explicit skip.
- **Proposed resolution**: Define a manifest field such as prune_exempt=true on the forced row. In reviewer_prune_filter, skip productivity pruning for that field before the net_prunable and floor_prunable checks. Pin the field in review_dispatch_panel.py and test_review_prune.py.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py
- **Concern**: validate_disposition_for_ship may compare stale artifacts only. Scenario: The plan invalidates disposition when the fingerprint changes after later edits, but ship and PR gates are only listed as validators. If validate_disposition_for_ship only compares stored disposition and coverage files without recomputing coverage from the Step 0 plan and current touched paths, review fixes and checks-repair edits can leave a valid-looking proceed-partial record while the tree no longer matches.
- **Proposed resolution**: Make validate_disposition_for_ship recompute coverage from $IMPLEMENT_TMPDIR/plan.txt and the current git delta, then compare that live fingerprint to the recorded disposition. Fail closed when recompute fails on a required-disposition path. Add a stale-fingerprint test in test_ship_pre_driver.py or test_implement_dispatch.py.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/implement/test_ship_pre_driver.py
- **Concern**: Absent pre-driver test file is marked UPDATED. Scenario: The plan lists python/tests/implement/test_ship_pre_driver.py under UPDATED, but the repo has no such file. Pre-driver tests today live in python/tests/implement/test_implement_dispatch.py. An implementer may create a duplicate module or skip the planned cases.
- **Proposed resolution**: Change the heading to ### NEW: if splitting tests, or ### UPDATED: python/tests/implement/test_implement_dispatch.py if extending the existing pre-driver tests there. Keep the acceptance cases either way.

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/implement/test_implement_self_review.py
- **Concern**: Absent self-review test file is marked UPDATED. Scenario: The plan lists python/tests/implement/test_implement_self_review.py under UPDATED, but no such file exists. Acceptance criterion 3 self-review behavior has no pinned home.
- **Proposed resolution**: Change the heading to ### NEW: python/tests/implement/test_implement_self_review.py, or fold the forced self-review case into an existing Step 5 self-review test module and update that UPDATED path instead.

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/git/pr.py:55-85
- **Concern**: ensure_pr() still hardcodes `Closes #N` for existing-PR refreshes.. Scenario: Partial-scope runs can still stamp a closing keyword and close the tracking issue even after `Part of #N` support lands.
- **Proposed resolution**: Route the footer through a disposition-aware helper and emit `Part of #N` when the recorded scope disposition is partial.

### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/git/pr.py:384-449
- **Concern**: create_main() and body_update_main() still bypass the new validator.. Scenario: The live `python/cli.py pr create` and `pr body-update` commands can still mutate PR state when disposition is missing or stale, so the ship gate is bypassable.
- **Proposed resolution**: Wrap both entrypoints with `validate_disposition_for_ship()` or route them through the validated ship helper before `gh.pr_create` / `gh.pr_edit_body_file`.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/self-review.md:7-59
- **Concern**: Self-review never honors `PLAN_FIDELITY_FORCED`. Scenario: When `--self-review` or `STEP5_REVIEW_STATUS=self-review-required` takes the inline path, the reference still skips a bounded plan-fidelity pass, so middle-band runs can miss the reviewer the plan says must always run.
- **Proposed resolution**: Add a forced-flag branch in the self-review reference, or block self-review while `PLAN_FIDELITY_FORCED=true` is active.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr.py:434-446
- **Concern**: `pr body-update` bypasses the new disposition gate. Scenario: `python/cli.py pr body-update` still edits an open PR directly through `gh.pr_edit_body_file`, so a stale or missing scope-disposition can be bypassed outside the hardened ship path.
- **Proposed resolution**: Call the shared disposition validator before `gh.pr_edit_body_file`, or route body updates through the same helper as `ensure_pr`.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/git/pr.py:72-97
- **Concern**: ensure_pr still hardcodes link_pr_closes on create and update. Scenario: The plan adds Part-of linking in pr_body.py but pr.ensure_pr calls tracking_issue.link_pr_closes on both new and existing PR paths, so partial-scope runs can still get Closes #N on refresh/rebase even when compose_pr_body was fixed
- **Proposed resolution**: Route both create and update through a disposition-aware linker (or pass disposition into compose/link helpers) and add the planned existing-PR update test against ensure_pr not only compose_pr_body

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:Step 5-7
- **Concern**: Post-disposition fingerprint invalidation is not pinned for review or checks-repair edits. Scenario: The plan recomputes on claude_fallback/recovery and before Step 3 or ship, but Step 5-7 commits and checks-repair main-agent edits can change touched paths after proceed-partial without a named recompute site, leaving stale partial disposition through ship
- **Proposed resolution**: Extend the shared scope_disposition fence to Step 5 review commits, Step 7 commit-route success, and checks-repair re-entry; invalidate disposition when fingerprint changes and re-prompt before Step 8

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: code-quality
- **Location**: skills/implement/references/self-review.md:1-59
- **Concern**: Forced plan-fidelity is not wired into the authoritative self-review reference. Scenario: Round 1 accepted self-review bypass; the plan only documents behavior in SKILL.md while self-review.md remains the normative executable body for --self-review and self-review-required fallback
- **Proposed resolution**: Add MAY_UPDATE or UPDATED self-review.md with the forced inline plan-fidelity pass or explicit block when PLAN_FIDELITY_FORCED=true, and keep the planned self-review test

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/references/step2-dispatch.md:19-21
- **Concern**: Authoritative Step 2 stdout contract still forbids branching on coverage output. Scenario: The plan makes PLAN_COVERAGE_DISPOSITION_REQUIRED branch the orchestrator but leaves step2-dispatch.md saying WARN_* coverage KVs are advisory and Step 2 must not branch, which will drift implementers and harness readers away from the new gate
- **Proposed resolution**: Update step2-dispatch.md in the firm file list: document new coverage KVs, disposition-required semantics, and that Step 2 now branches on disposition-required output

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:Step 2
- **Concern**: Complete-path disposition can run before post-dispatch settlement. Scenario: The plan prompts after envelope validation; on STATUS=complete proceed-partial can file a follow-up and record disposition before step-2-post-dispatch.sh, so a later main-branch-post-dispatch bail leaves a dangling follow-up and blocked-by edge
- **Proposed resolution**: Pin ordering: on STATUS=complete run disposition only after POST_DISPATCH_NEXT=continue succeeds; keep the pre-Step-3 claude_fallback/recovery fence separate

### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:13-27
- **Concern**: Coverage source is not pinned to the Step 0 baseline. Scenario: The current dispatcher coverage helper uses dirty worktree paths before commit. The plan requires recompute before Step 3 and ship after commits; if the shared helper keeps a worktree-only source, committed plan paths disappear from the touched set and full-scope runs can look partial or stale valid dispositions.
- **Proposed resolution**: Specify that scope_disposition computes touched firm paths from the Step 0 or prelaunch baseline to HEAD plus current uncommitted and untracked paths, then add a focused committed-before-ship coverage test.

### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: plan.txt:65-77
- **Concern**: Proceed-partial durability is unpinned by tests. Scenario: The plan requires filing the follow-up issue and dependency before recording proceed-partial, but the listed tests only cover downstream gates. An implementation can write scope-disposition.env first, then a follow-up or dependency failure lets ship validation pass without the durable cross-linked follow-up required by acceptance criterion 1.
- **Proposed resolution**: Add focused scope_disposition tests that mock issue filing and dependency writes, assert no disposition or run-log batch is recorded until issue number, URL, cross-link, and block relation all succeed, and assert failures leave the run parked or routed to bail-rescope.

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_ship.py:230-306
- **Concern**: Post-driver scope-disposition halts are not routed by ship route-exit. Scenario: The plan adds direct PR mutation validation inside ship/pr paths, but it only specifies pre-driver NEXT_ACTION emission and SKILL routing. If a stale or missing disposition is detected inside the Step 8 ship driver before ensure_pr or PR body refresh, the driver will surface a needs-user result that route-exit currently classifies through _classify_ship_needs_user_reason; without a planned halt-scope-disposition mapping, Step 8 falls to operator-bail instead of re-entering the required disposition prompt.
- **Proposed resolution**: Add the route-exit part to the plan: define a scope-disposition needs-user reason constant, have the ship/direct-mutation validator return it, map it to NEXT_ACTION=halt-scope-disposition in _classify_ship_needs_user_reason, and add a route-exit test for that driver result.
