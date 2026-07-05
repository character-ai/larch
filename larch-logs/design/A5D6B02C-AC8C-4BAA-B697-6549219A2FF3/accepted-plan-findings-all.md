### FINDING_1: Missing launcher fences and fence-shape harness bumps
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Codex-dyn-Ship Handoff State Machine
- **Severity**: important
- **Concern**: Step 8+ adds pre-fix-rebase prose, but it does not yet supply the required one-line launcher fences or the matching fence/structure harness updates, so orchestrators may improvise the argv shape and CI may fail when the fence count changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a foreground one-line fence mirroring route-exit, for example `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"`, on both ci-fix and reship paths before stale-handoff clear or ci-fix load. List `scripts/test-implement-fence-shape.sh` under `### UPDATED:` when the fence is added; the plan's claim that no fence-shape harness run is needed conflicts with AGENTS.md when a new fence is introduced.
  - From Cursor-Innovation: Add an explicit foreground fence for python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR" in ci-fix and reship branches, list ### UPDATED: scripts/test-implement-structure.sh, and require pre-fix-rebase before stale-handoff clear / ci-fix load in the harness slices.
  - From Codex-dyn-Ship Handoff State Machine: List ### UPDATED: scripts/test-implement-fence-shape.sh and bump EXPECTED_NEW for each new one-line launcher fence.


### FINDING_2: Forked runs need the driver's base remote
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Ship Handoff State Machine
- **Severity**: important
- **Concern**: The new pre-fix rebase must use the same fork-aware remote selection as the ship driver; hardcoding `origin/main` can leave forked reship paths rebased onto the wrong base.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Read `FORKED_TARGET` / `FORKED` from `ship-pr-state.sh` and pass the same remote selection as `ship.py` (upstream when forked, else origin). Add a focused test with forked state asserting `rebase_and_push` receives `base_remote="upstream"`.
  - From Cursor-Innovation: Read FORKED_TARGET (and forked when present) from ship-pr-state.sh and pass base_remote=upstream when true, else origin, matching the driver.
  - From Cursor-Pragmatic: ship_pre_fix_rebase_main hardcodes base_remote=origin while fork runs use upstream. Scenario: FORKED_TARGET=true is stored in ship-pr-state.sh and ship.py selects upstream for rebases (ship.py:622). The plan still hardcodes origin/main for all pre-fix calls. Fork-mode reship still runs pre-fix (ci-fix skips edits but reship does not), so the feature branch can rebase onto origin/main instead of upstream/main and diverge from the CI base used elsewhere.
  - From Codex-Pragmatic: Derive base_remote from the same forked/repo-unavailable state the ship driver uses, then pass that remote into rebase.rebase_and_push()
  - From Cursor-Requirements: Read FORKED_TARGET from ship-pr-state.sh and set base_remote to upstream when true, matching the ship driver. Add a fork reship monkeypatch test asserting upstream/main is used.
  - From Cursor-dyn-Ship Handoff State Machine: Read FORKED_TARGET from ship-pr-state.sh and pass base_remote=upstream when true, matching ship_merge.py:201-202 / ship.py:622.


### FINDING_3: Reship must preserve the phase14 continuation carve-out
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation
- **Severity**: blocking
- **Concern**: Unconditionally pre-rebasing reship must not break the existing phase14 rebase-continuation path or drop the resumption keys that keep that handoff alive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Current reship prose requires relaunching `step-8-ship.sh` while preserving `RESUME_PHASE`, `CALLER_KIND`, and `CONFLICT_FILES` during the `ship-pr-rrr-phase14` / `ship_pr_pre_push` handoff until conflict-resolution Phase 4 completes. The plan only says pre-fix then stale-handoff clear and relaunch, which risks dropping that invariant when editing the reship bullets. Explicitly retain the existing carve-out in both SKILL.md and ship-pr-exit-matrix.md reship semantics: after `NEXT_ACTION=continue` from pre-fix-rebase, stale-handoff clear and relaunch must still preserve those keys until Phase 4 completes.
  - From Codex-Innovation: Carve out `RESUME_PHASE=ship-pr-rrr-phase14` / `CALLER_KIND=ship_pr_pre_push` from the new gate and keep that path on the existing conflict-resolution continuation.


### FINDING_4: Active rebases need a guarded conflict-or-stall path
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Ship Handoff State Machine, Codex-dyn-Ship Handoff State Machine
- **Severity**: blocking
- **Concern**: Before starting a pre-fix rebase, the helper must detect an existing rebase and either continue into conflict-fix when persisted conflict metadata or unmerged paths are present, or stall safely; it must never launch a second rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use git.rebase_in_progress() before calling rebase.rebase_and_push(), return PRE_FIX_REBASE_STATUS=stall and NEXT_ACTION=stall when true, and add a regression test for that branch plus TransientNetworkError
  - From Cursor-Pragmatic: Before calling rebase_and_push, if git.rebase_in_progress is true, reuse _ship_route_conflict_handoff_fields and/or enumerate unmerged paths; when conflict metadata exists, patch state, write .ship-route-exit-handoff.env, and emit PRE_FIX_REBASE_STATUS=conflict and NEXT_ACTION=conflict-fix. Otherwise stall. Add a monkeypatch test for the in-progress plus CONFLICT_FILES path.
  - From Cursor-Requirements: Before calling rebase_and_push, if git.rebase_in_progress is true, reuse _ship_route_conflict_handoff_fields (or unmerged paths) and emit PRE_FIX_REBASE_STATUS=conflict with NEXT_ACTION=conflict-fix when metadata is present; reserve stall for in-progress rebase without resolvable conflict metadata.
  - From Codex-Requirements: Add one focused regression test that forces `git.rebase_in_progress()` true, asserts `PRE_FIX_REBASE_STATUS=stall` and `NEXT_ACTION=stall`, and verifies `rebase.rebase_and_push()` is not called.
  - From Cursor-dyn-Ship Handoff State Machine: At entry, if git.rebase_in_progress or _ship_route_conflict_handoff_fields is non-empty, populate handoff/state and emit NEXT_ACTION=conflict-fix instead of clobbering with a new rebase.
  - From Codex-dyn-Ship Handoff State Machine: Check git.rebase_in_progress before invoking rebase.rebase_and_push, and emit PRE_FIX_REBASE_STATUS=stall/NEXT_ACTION=stall without starting a new fetch/rebase when one is already active.


### FINDING_5: Conflict handoffs must patch existing state and keep PHASE=rebase
- **Reviewer(s)**: Cursor-Innovation, Codex-Pragmatic, Cursor-dyn-Ship Handoff State Machine, Codex-dyn-Ship Handoff State Machine
- **Severity**: blocking
- **Concern**: If the pre-fix rebase conflicts, the handoff must merge into the existing route-exit env rather than overwriting it, and it must preserve the driver-style rebase phase and counters so ci-fix can resume correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: On PrePushConflictHandoff, mirror ship_merge: read counters from ship-pr-state.sh, call ship._write_ship_state with phase=rebase and the same extra_fields, rely on rebase._write_handoff_flag via enable_pre_push_handoff=True, and write .ship-route-exit-handoff.env for conflict-resolution.md.
  - From Codex-Pragmatic: Merge the conflict trio into the existing handoff file, or preserve the existing keys alongside the new conflict fields so ci-fix can resume with FAILED_RUN_ID intact
  - From Cursor-dyn-Ship Handoff State Machine: Mirror ship_merge PrePushConflictHandoff handling: patch PHASE=rebase (via validated state writer) alongside resume metadata; rely on enable_pre_push_handoff for the phase14 flag (python/larch/git/rebase.py:254-260).
  - From Codex-dyn-Ship Handoff State Machine: Patch the existing env file in place, preserve all preexisting keys, and append the new RESUME_PHASE, CALLER_KIND, and CONFLICT_FILES fields rather than rewriting the handoff from scratch.


### FINDING_7: Routable pre-fix outcomes should exit 0
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Ship Handoff State Machine, Codex-dyn-Ship Handoff State Machine
- **Severity**: important
- **Concern**: The new verb needs the same zero-exit contract as route-exit: when stdout emits a parseable NEXT_ACTION or PRE_FIX_REBASE_STATUS, the orchestrator should keep going instead of treating the command as a failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document and test that conflict, stall, and continue paths exit 0 once KVs are emitted; reserve non-zero for missing tmpdir/state or handoff write failures only.
  - From Cursor-dyn-Ship Handoff State Machine: Return 0 whenever stdout emits NEXT_ACTION; reserve non-zero for missing tmpdir/argv failures with no NEXT_ACTION, mirroring ship route-exit.


### FINDING_10: Python routing must invoke the pre-fix rebase
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Concern**: The new pre-fix rebase exists only as a CLI/doc pair, so the Python handoff boundary still does not enforce it before ci-fix or reship work starts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Invoke `ship pre-fix-rebase` from the Step 8+ Python routing layer before branching into ci-fix or reship, and keep the markdown as a thin pointer only.


### FINDING_2: Phase14 reship carve-out is too narrow
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: The skip logic only keys off handoff-env metadata, so the flag-based phase14 no-checks reship path can still look like a normal reship and run a redundant pre-fix rebase before the driver's phase14 continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Also skip pre-fix when `ship-pr-rrr-after-phase14.flag` is present (mirror `_ship_route_phase14_reship_pending`) or when `ship-pr-state.sh` matches `_ship_route_conflict_handoff_fields`; document the same rule in `ship-pr-exit-matrix.md` and pin it in tests.
  - From Cursor-Innovation: Also skip pre-fix when `$IMPLEMENT_TMPDIR/ship-pr-rrr-after-phase14.flag` exists (mirror `_ship_route_phase14_reship_pending`), or have `route-exit` copy flag metadata into the handoff before SKILL branches; add a reship regression test for the flag-only handoff.
  - From Codex-Innovation: When `_ship_route_phase14_reship_pending` selects reship, propagate a phase14 skip signal into the handoff and do not write `PRE_FIX_REBASE_REQUIRED=true` for that carved-out reship; pin this with route-exit coverage
  - From Cursor-Pragmatic: Skip pre-fix when `ship-pr-rrr-after-phase14.flag` exists (mirror `_ship_route_phase14_reship_pending`) or when scoped `ship-pr-state.sh` already has phase14 resume metadata; add a focused test for flag-pending reship
  - From Codex-Pragmatic: Do not set `PRE_FIX_REBASE_REQUIRED=true` for phase14-continuation reships, or add an explicit phase14 marker and make the Step 8+ predicate skip the pre-fix gate when that marker or flag is present.
  - From Cursor-Requirements: Encode the skip in `ship_pre_fix_rebase_main` (emit `PRE_FIX_REBASE_STATUS=skipped` + `NEXT_ACTION=continue` when phase14 flag exists or `ship-pr-state.sh` has active pre-push handoff, mirroring `_ship_route_phase14_reship_pending` / `_is_active_pre_push_handoff`); align SKILL/reship branch to the same signals, not handoff-only
  - From Codex-Requirements: Add the phase14 flag to the skip condition, or have route-exit project an explicit phase14 continuation marker into the handoff for that reship. Pin the test with the existing no-checks phase14 flag scenario


### FINDING_4: Post-fix push still uses plain push after a rebase
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: A deferred pre-fix rebase rewrites the branch, but the later CI-fix push path still looks like a plain `git push`, so it can fail non-fast-forward instead of reshipping the fixed branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Either let the pre-fix rebase use the existing force-push path before the fix, or change the post-fix push to a force-with-lease flow with the expected remote OID captured before the rebase
  - From Codex-Innovation: Do not pair a deferred rebase with the unchanged plain push. Either let the pre-fix rebase force-push with lease before editing, or change the post-fix push path to force-with-lease when the pre-fix rebase rebased
  - From Codex-Pragmatic: Either let `rebase_and_push()` push the rebased branch before the fix, or change the post-fix push path to a force-with-lease push and add focused coverage for the rewritten-history case.


### FINDING_6: Pre-fix launcher fences still use an unsupported target shape
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: The new pre-fix launcher fences still have the wrong argv shape or an incomplete command, so the launcher and fence-shape harness can reject them before the Python gate runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use a closed one-line fence for each retained prompt-side call: "$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"; or remove those fences if route-exit owns the gate fully
  - From Cursor-Innovation: Use `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"` in both ci-fix and reship branches; pin that string in `scripts/test-implement-fence-shape.sh` ordering slices.
  - From Codex-Innovation: Add two closed one-line bash fences with `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"`, one before reship stale-handoff clear and one before ci-fix loads `ship-pr-ci-fix.md`; keep the harness count and slices in sync
  - From Cursor-Pragmatic: Use `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"` in both ci-fix and reship fences; pin that exact string in the fence-shape harness
  - From Codex-Pragmatic: Add two closed one-line Bash launcher fences in `skills/implement/SKILL.md`, both using `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"`, then update the harness slices against those exact fences.
  - From Cursor-Requirements: Use `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"` in both ci-fix and reship fences, matching existing `ship route-exit` / `ship pre-driver` fences
  - From Codex-Requirements: Use two closed one-line fences with `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"`, one in reship and one in ci-fix, and make the harness assert that exact shape


### FINDING_8: Conflict handoff state write omits resume metadata
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The conflict handoff write does not persist the resume metadata into `ship-pr-state.sh`, so later recovery cannot reliably recognize the paused rebase as conflict-resolution state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Pass `resume_phase=exc.resume_phase` and `caller_kind=exc.caller_kind` to `_write_ship_state` along with `phase="rebase"`, counters, and `CONFLICT_FILES`, and add this assertion to the conflict-path test


