### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:623-628
- **Concern**: The plan only updates `scripts/test-implement-fence-shape.sh` for slice ordering, but ci-fix branch ordering is enforced in `test-implement-structure.sh` via `ci_fix_slice` / `skill_ci_fix_slice` checks.. Scenario: After SKILL adds `ship pre-fix-rebase` fences, fence-shape can pass while structure checks still only require `FORKED_TARGET` before `ship-pr-ci-fix.md`, so an implementer could load the ci-fix reference or write sentinels before the pre-fix gate and CI would not catch it.
- **Proposed resolution**: Add `### UPDATED: scripts/test-implement-structure.sh` with `require_text` / `require_near` pins that `ship pre-fix-rebase` appears in the ci-fix and reship SKILL slices before `ship-pr-ci-fix.md` and before the stale-handoff clear / `step-8-ship.sh` relaunch.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:reship
- **Concern**: The reship phase14 carve-out only skips pre-fix when `.ship-route-exit-handoff.env` already has `RESUME_PHASE` + `CALLER_KIND`, but `test_ship_route_exit_reships_no_checks_when_phase14_flag_pending` shows the no-checks phase14 reship handoff has only `NEXT_ACTION=reship` while `ship-pr-rrr-after-phase14.flag` carries the pending rebase.. Scenario: That reship path would still run `ship pre-fix-rebase` and fetch/rebase again immediately before the driver’s `_ship_phase14_rebase`, duplicating work and adding conflict surface on infra retries with no edit benefit; it also weakens the accepted phase14 continuation carve-out.
- **Proposed resolution**: Also skip pre-fix when `ship-pr-rrr-after-phase14.flag` is present (mirror `_ship_route_phase14_reship_pending`) or when `ship-pr-state.sh` matches `_ship_route_conflict_handoff_fields`; document the same rule in `ship-pr-exit-matrix.md` and pin it in tests.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_ship.py:386-397
- **Concern**: Prior fix incomplete: route-exit still exposes ci-fix and reship before the Python gate runs. Scenario: ship route-exit can emit NEXT_ACTION=ci-fix or NEXT_ACTION=reship, leaving the required rebase ordering dependent on Step 8 prose instead of the Python handoff boundary
- **Proposed resolution**: Have ship_route_exit_main route ci-fix and non-phase14 reship through the pre-fix rebase helper before emitting the final autonomous action, or emit only a Python-owned intermediate action that cannot reach repair until PRE_FIX_REBASE_STATUS=ok



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-ci-fix.md:12
- **Concern**: Pre-fix rebase defers push but leaves the post-fix push as plain push branch. Scenario: When latest main advances, the local pre-fix rebase rewrites the already-pushed PR branch; after the fix commit, git push is non-fast-forward and the ci-fix path cannot reship
- **Proposed resolution**: Either let the pre-fix rebase use the existing force-push path before the fix, or change the post-fix push to a force-with-lease flow with the expected remote OID captured before the rebase



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_ship.py:340-397
- **Concern**: Prior fix incomplete: the in-progress rebase guard ignores unmerged paths when persisted metadata is absent. Scenario: A live rebase with unmerged files but missing RESUME_PHASE/CALLER_KIND metadata routes to stall instead of conflict-fix, so the required conflict-resolution path is skipped
- **Proposed resolution**: Check git unmerged paths when rebase_in_progress is true; if any exist, write phase=rebase conflict handoff fields with CONFLICT_FILES and NEXT_ACTION=conflict-fix, and stall only when neither metadata nor unmerged paths exist



### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:683-685
- **Concern**: Prior launcher-fence fix is incomplete: the planned reship fence targets ship instead of python/cli.py, and the ci-fix branch has no one-line command. Scenario: The fence-shape harness requires the implement-run target to be a repo-relative .sh or .py path; the planned ship pre-fix-rebase fence would fail, and ci-fix still lacks an executable pre-fix gate before loading the repair reference
- **Proposed resolution**: Use a closed one-line fence for each retained prompt-side call: "$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"; or remove those fences if route-exit owns the gate fully



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Pre-fix launcher fences use an unsupported `ship pre-fix-rebase` target. Scenario: `larch-run.sh` only accepts repo-relative `*.py` or `*.sh` targets (`python/larch/state/bootstrap.py`); existing Step 8+ fences use `python/cli.py ship route-exit`, and `scripts/test-implement-fence-shape.sh` rejects other targets. The proposed `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" ship pre-fix-rebase ...` fences would exit 2 at runtime and fail the new-shape fence harness.
- **Proposed resolution**: Use `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"` in both ci-fix and reship branches; pin that string in `scripts/test-implement-fence-shape.sh` ordering slices.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Phase14 reship carve-out is incomplete for flag-based reships. Scenario: `test_ship_route_exit_reships_no_checks_when_phase14_flag_pending` shows exit-6 `no-ci-checks` reships with only `ship-pr-rrr-after-phase14.flag` present emit `NEXT_ACTION=reship` without `RESUME_PHASE` / `CALLER_KIND` in `.ship-route-exit-handoff.env`. The plan skips pre-fix only when those keys are already in the handoff file, so this path would still run a redundant pre-fix rebase before the driver’s `_ship_phase14_rebase` continuation.
- **Proposed resolution**: Also skip pre-fix when `$IMPLEMENT_TMPDIR/ship-pr-rrr-after-phase14.flag` exists (mirror `_ship_route_phase14_reship_pending`), or have `route-exit` copy flag metadata into the handoff before SKILL branches; add a reship regression test for the flag-only handoff.



### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-ci-fix.md:23
- **Concern**: `defer_push=True` leaves the later CI-fix push as a plain non-fast-forward push after a rebase. Scenario: The pre-fix rebase rewrites feature commits, the main agent commits the CI repair, then `python/cli.py push branch` runs plain `git push`; the remote branch still has the old pre-rebase history, so the fix push can reject and the required handoff cannot ship
- **Proposed resolution**: Do not pair a deferred rebase with the unchanged plain push. Either let the pre-fix rebase force-push with lease before editing, or change the post-fix push path to force-with-lease when the pre-fix rebase rebased



### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:77-93
- **Concern**: The pre-fix launcher fence is still incomplete and has the wrong argv shape. Scenario: The reship command targets `ship` instead of repo-relative `python/cli.py`, the shown fence is not closed, and the ci-fix branch has no launcher fence at all; the fence-shape harness requires one physical line whose target ends in `.sh` or `.py`, so Step 8 may not deterministically invoke the new Python gate
- **Proposed resolution**: Add two closed one-line bash fences with `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"`, one before reship stale-handoff clear and one before ci-fix loads `ship-pr-ci-fix.md`; keep the harness count and slices in sync



### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_ship.py:215-306
- **Concern**: The phase14 reship carve-out is documented but not made routable in the handoff. Scenario: The existing phase14 no-checks path maps to `NEXT_ACTION=reship` without writing `RESUME_PHASE` or `CALLER_KIND` into `.ship-route-exit-handoff.env`; the plan then marks every reship `PRE_FIX_REBASE_REQUIRED=true`, so the SKILL check misses the carve-out and can run the new pre-fix rebase over an existing phase14 continuation
- **Proposed resolution**: When `_ship_route_phase14_reship_pending` selects reship, propagate a phase14 skip signal into the handoff and do not write `PRE_FIX_REBASE_REQUIRED=true` for that carved-out reship; pin this with route-exit coverage



### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/dispatch_ship.py:11-37
- **Concern**: The pre-fix helper can mutate the wrong checkout before the existing ship checkout guard runs. Scenario: After a durable handoff or turn break, the operator may be on `main` or another branch; today the ship driver detects checkout mismatch and bails, but the new pre-fix command would call `rebase_and_push()` on the current branch first
- **Proposed resolution**: Add a non-mutating guard before `rebase_and_push()`: read `BRANCH_NAME` from `ship-pr-state.sh`, compare it to `git.try_current_branch()`, and route to a safe stall or documented operator-bail outcome without rebasing on mismatch



### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Launcher fences use bare `ship pre-fix-rebase` instead of `python/cli.py ship pre-fix-rebase`. Scenario: `larch-run.sh` only accepts repo-relative `*.py` or `*.sh` targets; `ship pre-fix-rebase` hits `unsupported script target` and `test-implement-fence-shape.sh` rejects non-.py/.sh targets, so Step 8+ never runs the gate
- **Proposed resolution**: Use `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"` in both ci-fix and reship fences; pin that exact string in the fence-shape harness



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Phase14 reship carve-out checks only handoff env keys, not the phase14 flag path. Scenario: `route-exit` can emit `NEXT_ACTION=reship` with an empty handoff for `no-ci-checks-observed` while `ship-pr-rrr-after-phase14.flag` is present; unconditional pre-fix then starts a second rebase before `_ship_phase14_rebase` on relaunch
- **Proposed resolution**: Skip pre-fix when `ship-pr-rrr-after-phase14.flag` exists (mirror `_ship_route_phase14_reship_pending`) or when scoped `ship-pr-state.sh` already has phase14 resume metadata; add a focused test for flag-pending reship



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/test-implement-structure.sh
- **Concern**: Structure harness pins and branch-order checks are omitted from the plan. Scenario: `test-implement-fence-shape.sh` has no `branch_slice` logic; `test-implement-structure.sh` already pins ship registry entries and ci-fix/reship ordering, so pre-fix ordering and `("ship", "pre-fix-rebase")` registration can ship without CI enforcement
- **Proposed resolution**: Add `### UPDATED: scripts/test-implement-structure.sh` with pins for the new CLI registry, machine-stdout membership, and ci-fix/reship slices requiring `python/cli.py ship pre-fix-rebase` before stale-handoff clear and before loading `ship-pr-ci-fix.md` ## Findings ### 1. [correctness] `skills/implement/SKILL.md` — invalid launcher fence target The plan’s ci-fix and reship fences use: "$HOME/.cache/larch/sessions/implement-run-$PPID.sh" ship pre-fix-rebase ... Existing Step 8+ ship calls use the `python/cli.py` prefix (for example `python/cli.py ship route-exit`). `larch-run.sh` only routes `*.py` and `*.sh` paths; anything else exits 2 with `unsupported script target`. `scripts/test-implement-fence-shape.sh` enforces the same rule for new-shape fences. This is an incomplete fix for prior accepted FINDING_1: fences are present, but the argv shape cannot work. ### 2. [correctness] `skills/implement/SKILL.md` — phase14 reship carve-out is too narrow The plan skips pre-fix only when `.ship-route-exit-handoff.env` contains `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push`. That misses the common phase14 continuation path: exit 4 with `detail=no-ci-checks-observed` and a pending `ship-pr-rrr-after-phase14.flag` routes to `reship` without those keys in the handoff (see `test_ship_route_exit_reships_no_checks_when_phase14_flag_pending`). On relaunch, the driver runs `_ship_phase14_rebase` when the flag exists. Running pre-fix first can start a competing rebase and break the existing phase14 continuation. Prior accepted FINDING_3 is not fully closed until the flag path (and/or state-file resume metadata) is covered, with a test. ### 3. [architecture] `scripts/test-implement-structure.sh` — missing harness surface in the plan The plan bumps `scripts/test-implement-fence-shape.sh` and mentions “slices” there, but that harness only counts fence shapes and validates launcher targets. Branch-order and CLI registry pins for Step 8+ live in `scripts/test-implement-structure.sh` (for example explicit `("ship", "route-exit")` / `("ship", "pre-driver")` requires, ci-fix `branch_slice` ordering). Without updating the structure harness, the orchestrator can run stale-handoff clear or load `ship-pr-ci-fix.md` before pre-fix with no CI failure, even though the issue requires Python-enforced ordering before autonomous edits.



### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-ci-fix.md:23
- **Concern**: `defer_push=True` leaves the existing normal `push branch` path broken after any real pre-fix rebase. Scenario: A pre-fix rebase rewrites local feature commits without updating the remote. The later CI-fix commit then runs `python/cli.py push branch`, which uses plain `git push`; that can fail non-fast-forward instead of reshipping the fixed branch.
- **Proposed resolution**: Either let `rebase_and_push()` push the rebased branch before the fix, or change the post-fix push path to a force-with-lease push and add focused coverage for the rewritten-history case.



### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:74-80
- **Concern**: Prior accepted launcher-fence fix remains incomplete: the reship fence omits `python/cli.py`, and the ci-fix fence is missing. Scenario: Following the plan leaves one malformed launcher command and no concrete ci-fix command, so the Step 8+ orchestrator can skip or misinvoke the required Python gate, and the fence-shape harness cannot reliably pin the two new one-line fences.
- **Proposed resolution**: Add two closed one-line Bash launcher fences in `skills/implement/SKILL.md`, both using `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"`, then update the harness slices against those exact fences.



### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:39
- **Concern**: Phase14 reship carve-out is contradicted by marking every `reship` as `PRE_FIX_REBASE_REQUIRED=true`. Scenario: The existing phase14 continuation is detected by `ship-pr-rrr-after-phase14.flag`; its `reship` handoff need not carry `RESUME_PHASE` keys. The planned handoff flag can therefore tell Step 8+ to run a new pre-fix rebase before the driver resumes phase14.
- **Proposed resolution**: Do not set `PRE_FIX_REBASE_REQUIRED=true` for phase14-continuation reships, or add an explicit phase14 marker and make the Step 8+ predicate skip the pre-fix gate when that marker or flag is present.



### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Reship/ci-fix launcher fences use bare `ship pre-fix-rebase` instead of a `.py` launcher target. Scenario: `scripts/test-implement-fence-shape.sh` `validate_new` rejects any new-shape fence whose launcher target does not end in `.sh` or `.py`; implementing the plan verbatim fails the harness the plan requires running
- **Proposed resolution**: Use `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"` in both ci-fix and reship fences, matching existing `ship route-exit` / `ship pre-driver` fences



### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:683-697, python/larch/implement/dispatch_ship.py
- **Concern**: Phase14 reship carve-out is incomplete and prose-only; it keys only on `.ship-route-exit-handoff.env`. Scenario: `ship route-exit` maps no-checks stall plus `ship-pr-rrr-after-phase14.flag` to bare `reship` with empty `route_fields`, so handoff often lacks `RESUME_PHASE`/`CALLER_KIND` while state/flag still mean live phase14 continuation; unconditional pre-fix can start a second rebase before `step-8-ship.sh` resumes `_ship_phase14_rebase`
- **Proposed resolution**: Encode the skip in `ship_pre_fix_rebase_main` (emit `PRE_FIX_REBASE_STATUS=skipped` + `NEXT_ACTION=continue` when phase14 flag exists or `ship-pr-state.sh` has active pre-push handoff, mirroring `_ship_route_phase14_reship_pending` / `_is_active_pre_push_handoff`); align SKILL/reship branch to the same signals, not handoff-only



### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:683-685
- **Concern**: Prior round fix remains incomplete: the planned pre-fix launcher omits `python/cli.py`, leaves the reship fence unclosed, and does not add the ci-fix launcher fence. Scenario: The Step 8+ orchestrator cannot reliably invoke the Python gate. The fence-shape harness also rejects launcher targets that do not end in `.sh` or `.py`, so a literal `implement-run... ship pre-fix-rebase` fence fails validation or tries to execute the wrong target
- **Proposed resolution**: Use two closed one-line fences with `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"`, one in reship and one in ci-fix, and make the harness assert that exact shape



### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:683
- **Concern**: The phase14 carve-out only checks handoff env keys, but the existing no-checks phase14 reship path is flag-based and writes no `RESUME_PHASE` or `CALLER_KIND` into `.ship-route-exit-handoff.env`. Scenario: `ship route-exit` can return `NEXT_ACTION=reship` for `ship-pr-rrr-after-phase14.flag` with only `DETAIL=no-ci-checks-observed`. The planned reship branch treats that as "all other reship entries" and runs the new pre-fix rebase before `step-8-ship.sh`, bypassing the driver's `_ship_phase14_rebase` continuation and risking a double rebase
- **Proposed resolution**: Add the phase14 flag to the skip condition, or have route-exit project an explicit phase14 continuation marker into the handoff for that reship. Pin the test with the existing no-checks phase14 flag scenario



### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_ship.py:183-198
- **Concern**: Prior round fix remains incomplete: an in-progress rebase with unmerged paths but missing persisted conflict metadata still routes to stall. Scenario: The accepted guard required conflict-fix when persisted metadata or unmerged paths are present. With the current plan, a live conflicted rebase whose state lost `CONFLICT_FILES` emits `NEXT_ACTION=stall` instead of using the existing conflict-resolution procedure
- **Proposed resolution**: Check `git.unmerged_paths()` when `git.rebase_in_progress()` is true and `_ship_route_conflict_handoff_fields()` is empty. If paths exist, synthesize `RESUME_PHASE=ship-pr-rrr-phase14`, `CALLER_KIND=ship_pr_pre_push`, and `CONFLICT_FILES`, patch state and handoff, then emit `NEXT_ACTION=conflict-fix`



### FINDING_24:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship_merge.py:206-217
- **Concern**: The planned `PrePushConflictHandoff` state write omits `resume_phase=exc.resume_phase` and `caller_kind=exc.caller_kind` even though it claims to mirror `_ship_rebase_phase`. Scenario: The immediate handoff env may contain the continuation keys, but `ship-pr-state.sh` would not. On turn recovery or later route-exit, the driver cannot identify the paused rebase as `ship_pr_pre_push` conflict-resolution state, so the continuation can stall or misroute
- **Proposed resolution**: Pass `resume_phase=exc.resume_phase` and `caller_kind=exc.caller_kind` to `_write_ship_state` along with `phase="rebase"`, counters, and `CONFLICT_FILES`, and add this assertion to the conflict-path test



