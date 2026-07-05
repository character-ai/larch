## Plan

## Scope

Implement the approved outline. Apply the pre-fix rebase only to autonomous paths: `ci-fix` and `reship`. Exclude `operator-bail`, `conflict-fix`, OOS routing, and the ship driver's internal phase 14 rebase code.

`approach-synthesis.txt` is `NO_SKETCHES`, so this plan comes from direct repo inspection. The approved outline is present and `.outline-approved` exists.

## Files to modify/create

### UPDATED: python/larch/implement/dispatch_ship.py

Add a `ship_pre_fix_rebase_main()` CLI entrypoint.

Implementation shape:

- Parse `--implement-tmpdir`, defaulting to `IMPLEMENT_TMPDIR`.
- Parse optional `--cwd`, defaulting to the current repo root.
- Read `ship-pr-state.sh` for `REPO`, `RUN_ID`, `FORKED_TARGET`, and current branch context.
- **Fork-aware remote selection**: if `FORKED_TARGET=true`, use `base_remote="upstream"`, else `base_remote="origin"`. Pass `base_ref="main"`.
- **Phase14 skip guard**: if `implement_tmpdir / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME` exists (phase14 pending rebase flag), skip the new rebase entirely, emit `PRE_FIX_REBASE_STATUS=skip` + `NEXT_ACTION=continue`, and exit 0. This prevents a double-rebase on the no-checks-observed phase14 reship path, which the driver handles internally.
- **In-progress rebase guard**: before calling `rebase_and_push()`, call `git.rebase_in_progress(runner, cwd=cwd)`.
  - If true and `_ship_route_conflict_handoff_fields(implement_tmpdir)` is non-empty: patch `ship-pr-state.sh` with those fields, write `.ship-route-exit-handoff.env` preserving existing keys, and emit `PRE_FIX_REBASE_STATUS=conflict` + `NEXT_ACTION=conflict-fix`. Exit 0.
  - If true and no conflict metadata: emit `PRE_FIX_REBASE_STATUS=stall` + `NEXT_ACTION=stall`. Exit 0.
- Call `rebase.rebase_and_push()` with:
  - `runner=proc`
  - `repo=<state repo>`
  - `run_id=<state run id>`
  - `cwd=<cwd>`
  - `tmpdir=<implement tmpdir>`
  - `base_remote=<fork-aware remote>`
  - `base_ref="main"`
  - `defer_push=False` — force-push the rebased branch immediately so the remote matches local before the fix is applied. This ensures the subsequent ci-fix commit push is a fast-forward.
  - `allow_conflict_fix=True`
  - `enable_pre_push_handoff=True`
- On success, emit `PRE_FIX_REBASE_STATUS=ok` + `NEXT_ACTION=continue`. Exit 0.
- On `PrePushConflictHandoff`: mirror `ship_merge._ship_rebase_phase` — read counters from `ship-pr-state.sh`, call `_write_ship_state` with `phase="rebase"`, `resume_phase=exc.resume_phase`, `caller_kind=exc.caller_kind`, and `extra_fields={"CONFLICT_FILES": exc.conflict_csv}` so all three fields land in `ship-pr-state.sh`; then patch `.ship-route-exit-handoff.env` by reading existing keys and appending (not overwriting) `RESUME_PHASE`, `CALLER_KIND`, `CONFLICT_FILES`, `PRE_FIX_REBASE_STATUS=conflict`, and `NEXT_ACTION=conflict-fix`. Exit 0.
- On `Stalled` or `TransientNetworkError`: emit `PRE_FIX_REBASE_STATUS=stall` + `NEXT_ACTION=stall` + a safe single-line `DETAIL=...`. Exit 0.
- **Exit-code contract**: exit 0 whenever stdout emits a parseable `NEXT_ACTION`; reserve non-zero for missing `--implement-tmpdir`, unreadable state, or handoff write failures where no `NEXT_ACTION` was emitted.

Also update `_write_ship_route_handoff()` so `PRE_FIX_REBASE_REQUIRED=true` is written when `action` is `ci-fix` or `reship`.

Keep output machine-readable. Do not emit prose on stdout.

### UPDATED: python/larch/implement/implement_dispatch.py

Re-export `ship_pre_fix_rebase_main` from `dispatch_ship.py`. If tests import private helpers for this path, re-export only the minimum needed symbols.

### UPDATED: python/larch/cli.py

Register `("ship", "pre-fix-rebase")` → `larch.implement.implement_dispatch.ship_pre_fix_rebase_main`. Add the new command to the machine-stdout quiet-disable set.

### UPDATED: python/tests/test_cli.py

Add CLI registry coverage for `ship pre-fix-rebase`. Add it to the inherited-quiet machine stdout test case.

### UPDATED: python/tests/implement/test_implement_dispatch.py

Add focused tests:

- `route-exit` writes `PRE_FIX_REBASE_REQUIRED=true` for `ci-fix` and `reship`; does not write it for `operator-bail`, `conflict-fix`, `stall`, or `complete`.
- `ship_pre_fix_rebase_main()` ok path: calls `rebase.rebase_and_push()` with `defer_push=False` and fork-aware `base_remote`; emits `PRE_FIX_REBASE_STATUS=ok` + `NEXT_ACTION=continue`; exits 0.
- Fork path: `FORKED_TARGET=true` in state causes `base_remote="upstream"`.
- Phase14 skip path: phase14 flag file exists → emits `PRE_FIX_REBASE_STATUS=skip` + `NEXT_ACTION=continue`; does not call `rebase.rebase_and_push()`. Exits 0.
- In-progress rebase with conflict metadata: `git.rebase_in_progress()=True` + non-empty `_ship_route_conflict_handoff_fields` → `NEXT_ACTION=conflict-fix`; does not call `rebase.rebase_and_push()`. Exits 0.
- In-progress rebase without conflict metadata: `git.rebase_in_progress()=True` + empty fields → `NEXT_ACTION=stall`. Exits 0.
- Conflict path: `PrePushConflictHandoff` caught → calls `_write_ship_state` with `resume_phase`, `caller_kind`, and `CONFLICT_FILES`; patches existing handoff env keys, preserves prior fields, emits `NEXT_ACTION=conflict-fix`. Exits 0.
- Stall path: `Stalled` raised → emits `PRE_FIX_REBASE_STATUS=stall` + `NEXT_ACTION=stall`. Exits 0.
- Missing state: blank `REPO` or missing tmpdir → non-zero exit, no `NEXT_ACTION`.

Use monkeypatches for `rebase.rebase_and_push()`, `git.rebase_in_progress()`, and state files. Do not run real git.

### UPDATED: skills/implement/SKILL.md

Update Step 8+ branch semantics.

For `reship`:

- **Phase14 carve-out**: when `.ship-route-exit-handoff.env` contains `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push`, skip the pre-fix rebase and proceed directly to stale-handoff clear and step-8-ship.sh relaunch preserving those keys until conflict-resolution Phase 4 completes. This is an existing conflict-resolution continuation, not a new rebase opportunity.
- For all other reship entries: before the stale-handoff clear and before `step-8-ship.sh`, run the foreground pre-fix rebase fence:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pre-fix-rebase --implement-tmpdir "$IMPLEMENT_TMPDIR"
  ```

  Branch on `NEXT_ACTION`:
  - `continue` or `skip`: proceed to stale-handoff clear and relaunch.
  - `conflict-fix`: load the existing conflict-resolution reference and follow that path.
  - `stall`: route like post-driver stall.

For `ci-fix`:

- After fork and repo-unavailable skips, run the foreground pre-fix rebase fence:


  - `continue` or `skip`: load `ship-pr-ci-fix.md` and continue.
  - `conflict-fix`: route to the existing conflict-resolution path.
  - `stall`: route to the existing post-driver stall path.

Keep the Python command as the deterministic authority. Do not restate fetch and rebase shell steps in prose.

### UPDATED: scripts/test-implement-fence-shape.sh

Bump `EXPECTED_NEW` for the two new foreground one-line launcher fences added in ci-fix and reship (one each). Ensure the harness test slices require `ship pre-fix-rebase` before stale-handoff clear and ci-fix load.

### UPDATED: skills/implement/references/ship-pr-ci-fix.md

Remove the conditional step 6 carve-out for merge-ref-sensitive generated artifacts.

Add a precondition near the top: the Step 8+ orchestrator must have run `python/cli.py ship pre-fix-rebase` and received `NEXT_ACTION=continue` before this procedure performs sentinel writes, CI log capture, repairs, commits, or pushes.

Revise step 6 to say only: make the minimal repo edit from the redacted CI log and optional detail file.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md

Document that `.ship-route-exit-handoff.env` includes `PRE_FIX_REBASE_REQUIRED=true` for `ci-fix` and `reship`.

Update branch semantics:

- `reship`: skip pre-fix rebase when `RESUME_PHASE=ship-pr-rrr-phase14` and `CALLER_KIND=ship_pr_pre_push` (existing conflict-resolution continuation); run it for all other reship entries.
- `ci-fix`: run `ship pre-fix-rebase` before autonomous repair.
- `operator-bail`: remains operator-owned; no pre-fix rebase.
- `conflict-fix`: already mid-rebase; must not run the pre-fix rebase again.

## Approach

1. Add the Python rebase gate in `dispatch_ship.py` at the handoff boundary.
2. Reuse `python/larch/git/rebase.py` instead of adding shell git logic.
3. Use `defer_push=False` (force-push immediately after rebase) so the remote branch matches local before the fix is applied; the subsequent ci-fix commit push is then a fast-forward.
4. Guard against an in-progress rebase before starting a new one.
5. Patch existing handoff env on conflict (preserve prior keys); write ship state with `phase=rebase`.
6. Use fork-aware remote selection matching the ship driver.
7. Exit 0 for all routable outcomes; non-zero only for unrecoverable setup failures.
8. Add launcher fences in SKILL.md and bump the fence-shape harness.

## Edge cases

- A rebase already in progress is detected via `git.rebase_in_progress()` before calling `rebase_and_push()`.
- `conflict-fix` must not run the new pre-fix rebase: it is already mid-rebase.
- Phase14 reship continuation is detected by the phase14 flag file (`config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME`); the helper emits `NEXT_ACTION=continue` and skips the new rebase without calling `rebase_and_push()`.
- `operator-bail` remains out of scope.
- Missing `REPO`, `RUN_ID`, or tmpdir state causes non-zero exit with no `NEXT_ACTION`.
- Forked targets must use `base_remote="upstream"` to match the ship driver.
- Transient fetch failures must not lead to edits on stale `main`; they emit stall.

## Failure modes

- Malformed KVs from the new CLI would cause Step 8+ misrouting; tests pin exact stdout.
- Overwriting (not patching) the handoff env discards `FAILED_RUN_ID` and other keys that ci-fix needs; the conflict path must merge into existing env.
- Using `defer_push=True` would leave the remote branch unreachable after rebase, causing the subsequent ci-fix push to fail non-fast-forward; `defer_push=False` is required.
- Omitting the phase14 flag-file guard on reship would add a redundant rebase before the driver's own phase14 rebase loop.
- Running pre-fix after sentinel or repair steps loses the requested ordering; docs require it as the first step.

## Testing strategy

Run focused tests only:

- `python3 -m pytest python/tests/implement/test_implement_dispatch.py -k 'ship_route_exit or pre_fix_rebase'`
- `python3 -m pytest python/tests/test_cli.py -k 'ship_pre_fix_rebase or machine_stdout'`
- `python3 -m ruff check python/larch/implement/dispatch_ship.py python/larch/implement/implement_dispatch.py python/larch/cli.py python/tests/implement/test_implement_dispatch.py python/tests/test_cli.py`
- Run `scripts/test-implement-fence-shape.sh` only if a Bash fence is added, removed, or converted. This plan adds two new launcher fences so the harness must run.

## Difficulty

This is workflow-affecting Step 8+ ship handoff logic with Python routing, conflict-metadata merging, fork-aware remote selection, and prompt contract changes. Ship driver surfaces force at least `MODERATE`.

Confidence: high.

## Acceptance

Run focused tests only:

- `python3 -m pytest python/tests/implement/test_implement_dispatch.py -k 'ship_route_exit or pre_fix_rebase'`
- `python3 -m pytest python/tests/test_cli.py -k 'ship_pre_fix_rebase or machine_stdout'`
- `python3 -m ruff check python/larch/implement/dispatch_ship.py python/larch/implement/implement_dispatch.py python/larch/cli.py python/tests/implement/test_implement_dispatch.py python/tests/test_cli.py`
- Run `scripts/test-implement-fence-shape.sh` only if a Bash fence is added, removed, or converted. This plan adds two new launcher fences so the harness must run.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 310
