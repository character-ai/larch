## Plan


Issue: #2909. When `/implement` dispatches an external coder via `scripts/lint-fix-loop.sh` to fix a per-job CI failure, the coder occasionally commits the fix directly to HEAD instead of just modifying files. `scripts/lint-fix-loop.sh:322` then emits `LINT_FIX_STATUS=failed FAILURE_REASON=head-changed-after-dispatch`, `scripts/ship-pr.sh:148` maps it to `_RCC_STATUS=head-changed`, `run_per_job_local_fix_loop` returns 2, and the outer per-job loop hits `exit_stall "10-head-changed"` at `scripts/ship-pr.sh:1991`. The committed fix sits on the branch but is never pushed and CI never re-runs.

Fix at the **lint-fix-loop layer** per discussion-round1.md Decision 1 (broad), but only on the narrow safe path: same named branch, ancestor relationship preserved, clean pre-dispatch baseline. All other HEAD-drift shapes (detached HEAD, branch switch, history rewrite, dirty baseline) keep emitting the existing `head-changed-after-dispatch` failure. Commit-content forbidden-path enforcement (Decision 2) uses the same prefix-match semantics as the existing working-tree revert. After accepting the commit, the existing working-tree forbidden-path revert still runs so the coder cannot leave uncommitted submodule edits.

## Files to modify/create

### UPDATED: `scripts/lint-fix-loop.sh`

Pre-dispatch additions (immediately after `baseline_head` capture at line 286):
- Capture the baseline symbolic branch: `baseline_branch=$(git symbolic-ref --short HEAD 2>/dev/null || true)`. Empty means detached HEAD already; do not block dispatch, just record the empty value.

Replace the head-changed bail at lines 320-323 with three branches, evaluated in order:

1. **Detached / unresolvable HEAD after dispatch** (`current_head` empty): keep existing `fail_status "head-changed-after-dispatch" 1`.
2. **HEAD unchanged** (`current_head == baseline_head`): fall through to the existing working-tree path at line 325+ (no behavior change).
3. **HEAD moved**:
   - **Same-branch ancestor-preserved on a clean baseline**: accept as coder-owned commit (steps below).
   - **Anything else** (different branch, detached after move, history rewrite, OR `baseline_clean=false`): emit existing `fail_status "head-changed-after-dispatch" 1`.

The same-branch-ancestor-preserved test is exactly:
```
current_branch=$(git symbolic-ref --short HEAD 2>/dev/null || true)
if [[ -z "$baseline_branch" || -z "$current_branch" || "$baseline_branch" != "$current_branch" ]]; then
    fail_status "head-changed-after-dispatch" 1
fi
if ! git merge-base --is-ancestor "$baseline_head" "$current_head" 2>/dev/null; then
    fail_status "head-changed-after-dispatch" 1
fi
if [[ "$baseline_clean" != "true" ]]; then
    fail_status "head-changed-after-dispatch" 1
fi
```

Coder-owned commit acceptance steps:
1. Compute the committed delta path list: `git diff --name-only "$baseline_head".."$current_head" | awk 'NF && !seen[$0]++ { print }' > "$delta_paths_file"`.
2. Run a commit-content forbidden-path check with **prefix-aware matching** (per finding 1/3/6/9/12/15) that mirrors `post_dispatch_forbidden_revert` semantics. Either factor a shared helper used by both call sites or inline an equivalent `case` loop. Concrete shape:
   ```
   committed_forbidden_count=0
   while IFS= read -r diff_path || [[ -n "$diff_path" ]]; do
       [[ -n "$diff_path" ]] || continue
       while IFS= read -r forbidden_path || [[ -n "$forbidden_path" ]]; do
           [[ -n "$forbidden_path" ]] || continue
           case "$diff_path" in
               "$forbidden_path"|"$forbidden_path"/*)
                   committed_forbidden_count=$((committed_forbidden_count + 1))
                   ;;
           esac
       done < "$forbidden_paths_file"
   done < "$delta_paths_file"
   if (( committed_forbidden_count > 0 )); then
       git reset --hard "$baseline_head" >> "$run_dir/forbidden-revert.log" 2>&1 || true
       fail_status "forbidden-path-violation" 1
   fi
   ```
   (The `git reset --hard` is safe here because the `baseline_clean=true` guard above ensures no pre-existing dirty work to destroy.)
3. After commit-content check passes, **still run** `post_dispatch_forbidden_revert "$run_dir" "$forbidden_paths_file"` (per finding 7/22) so any uncommitted forbidden-path edits the coder left behind get reverted; on `revert_count > 0` use the existing `fail_status "forbidden-path-violation" 1`.
4. Skip the `delta_paths_after_dispatch` / `baseline_clean` block at lines 330-359 (already computed above and helper does not own the commit). Set `commit_sha="$current_head"`.
5. Fall through to the existing `emit_kv LINT_FIX_STATUS applied` block at lines 362-368.
6. Emit one additive field alongside the applied envelope: `emit_kv LINT_FIX_HEAD_CHANGED true`. Existing consumers ignore unknown fields; tests assert on it.

Preserve `set -euo pipefail` (per `.claude/rules/shell-strict-mode.md`); the `|| true` guards on `symbolic-ref` and `merge-base` are intentional (empty/non-zero are valid signals here, not errors).

If a shared prefix-match helper is factored out, it lives inside `lint-fix-loop.sh` (no library cross-script change). Naming suggestion: `forbidden_paths_match_count <paths-list-file> <forbidden-paths-file>`.

### UPDATED: `scripts/lint-fix-loop.md`

Document the new applied-with-coder-commit branch and the guards that gate it (`baseline_clean=true`, same symbolic branch, `baseline_head` is ancestor of `current_head`). Document the commit-content forbidden-path enforcement using the same prefix-match contract as the working-tree revert. Add `LINT_FIX_HEAD_CHANGED=true` to the documented output-contract bullet list. Note that `LINT_FIX_COMMIT_SHA` is now emitted for both helper-owned commits (existing) and coder-owned commits (new). Per `.claude/rules/script-md-siblings.md`, this update ships in the same PR as the `.sh` behavior change.

### UPDATED: `scripts/test-lint-fix-loop.sh`

- **Case 1 (lines 124-142)** — rewrite from "external coder commits; lint-fix-loop must fail closed on HEAD drift" to "external coder commits on clean baseline same branch; lint-fix-loop reports applied with committed delta paths". Replace assertions with:
  - `assert case1_rc == 0` (per finding 16 — the applied path exits 0, not 1).
  - `LINT_FIX_STATUS=applied`
  - `LINT_FIX_COMMIT_SHA=<non-empty>` (the new HEAD)
  - `LINT_FIX_HEAD_CHANGED=true`
  - `LINT_FIX_DELTA_PATHS_FILE=<path>` whose content includes `tracked.txt`
  Keep the existing `write_wrapper_commit_head` fixture unchanged.
- **New case** (forbidden-path-in-commit): build a fixture that synthesizes a submodule entry (write `.gitmodules` with a `[submodule "submod"]` block, create the `submod/` directory with a tracked file). Wrapper commits a change to `submod/file`. Assert `LINT_FIX_STATUS=failed`, `FAILURE_REASON=forbidden-path-violation`, exit 1, and `git rev-parse HEAD` equals the baseline (commit was reset). This case exercises the prefix-match path (nested path under a forbidden dir).
- **New case** (detached-HEAD-after-dispatch): wrapper executes `git checkout --detach` then commits. Assert `LINT_FIX_STATUS=failed`, `FAILURE_REASON=head-changed-after-dispatch`, exit 1 (preserves the defensive failure for detached-HEAD shape).
- **New case** (branch-switch-after-dispatch): wrapper creates+checks out a sibling branch and commits there. Assert the same failure as the detached-HEAD case.
- **New case** (dirty-baseline-plus-head-change): pre-dispatch wrapper leaves a tracked dirty edit, then wrapper commits. Assert the failure path (`baseline_clean=false` guard) — do NOT assert `git reset --hard` happened (dirty work must survive).

Keep the existing modify-only case 2 etc. as-is.

### UPDATED: `scripts/test-ship-pr.sh`

Rewrite the existing per-job head-changed regression starting at line 3265-3304 (~40 lines) using `ci_per_job_happy` (lines 3056-3111) as the structural template, per finding 17. Specifically:
- Replace the single-shot `ci-wait.sh` stub that always returns `evaluate_failure` with a count-based stub that returns `evaluate_failure` on call 1 and `ok` on call 2 (pattern from `ci_per_job_happy`).
- Replace the always-failing `env` stub with one that fails on first invocation and succeeds on replay (so the per-job verification passes after the coder-committed fix).
- Add a `git-push.sh` stub that logs to `push-calls.txt`.
- Replace `STUB_LINT_FIX_STATUS=failed STUB_LINT_FIX_FAILURE_REASON=head-changed-after-dispatch` with `STUB_LINT_FIX_STATUS=applied STUB_LINT_FIX_HEAD_CHANGED=true` (and any required `STUB_LINT_FIX_COMMIT_SHA` — extend the stub minimally to honor these envs).
- Assertions (per finding 18):
  - `assert_rc "$tmp/rc" 0` — the run completes successfully.
  - `push-calls.txt` exists and is non-empty (push happened).
  - No `STALL_TRACKING=true` in state.
  - `ci-wait.sh` invoked twice (call counter).
  - The lint-fix stub site argv contains `ship-pr-ci-per-job`.

Drop the obsolete `BAIL_REASON` non-`ci-local-unfixable` assertion (lines 3299-3303) — the bail path is gone on this branch.

### UPDATED: `SECURITY.md`

Update the lint-fix-loop section (around line 53) to describe the accepted-coder-commit path and its mechanical checks: same-branch invariant, ancestor-preserved invariant, clean-baseline invariant, commit-content prefix-aware forbidden-path check, residual working-tree forbidden-path revert. Per `AGENTS.md` "Update SECURITY.md when security-relevant behavior changes". Also addresses OOS_2 in spirit (full OOS_2 filing in Step 5b documents the lint-fix-loop layer explicitly).

### UPDATED: `docs/linting.md`

Update the section around line 203 that currently states the harness pins fail-closed HEAD drift. Replace with a description of the new behavior: same-branch ancestor-preserved coder commits are accepted as applied; all other HEAD-drift shapes still fail closed.

## Approach

The fix lives at `scripts/lint-fix-loop.sh`. `ship-pr.sh`'s `_rcc_handle_fix_status` is left untouched — its `head-changed` branch remains as a defensive fallback for the failure-classified HEAD-drift shapes (detached, branch switch, dirty baseline) that this PR still rejects.

Acceptance is gated by three invariants captured pre-dispatch and rechecked post-dispatch:
- **Same symbolic branch** — `git symbolic-ref --short HEAD` resolves identically before and after.
- **Ancestor preserved** — `git merge-base --is-ancestor "$baseline_head" "$current_head"` succeeds (prevents `commit --amend` / rebase from being accepted).
- **Clean baseline** — `baseline_clean=true` (prevents folding pre-existing dirty work into the pushed commit, and makes `git reset --hard` on forbidden-path violation safe).

Both callers of `run_captured_cmd_then_fix_loop` already handle `applied` correctly:
- `run_per_job_local_fix_loop` (ship-pr.sh:1863) → `_RCC_STATUS=ok` → `_stage_and_push_ci_fixes` (ship-pr.sh:1973). That helper calls `git-push.sh` on already-committed HEAD with no staged delta — exactly the desired no-op-then-push behavior.
- `run_checks_with_lint_fix_loop` (ship-pr.sh:1087) → continues its dispatch-first iteration. If the coder's commit fixes the relevant-checks failure, the next rerun returns rc=0 and `_RCC_STATUS=ok`.

## Edge cases

- **Detached HEAD after dispatch**: emit `head-changed-after-dispatch` (preserved defensive failure).
- **Branch switch / different symbolic branch**: emit `head-changed-after-dispatch` (new explicit guard).
- **History rewrite (`commit --amend`, rebase)**: `merge-base --is-ancestor` returns false → emit `head-changed-after-dispatch` (new explicit guard).
- **`baseline_clean=false` plus HEAD change**: emit `head-changed-after-dispatch` (new explicit guard; preserves dirty work, no destructive `reset`).
- **Coder commits a nested submodule path** (e.g. `submod/file`): prefix-match catches it → `git reset --hard "$baseline_head"` (safe because `baseline_clean=true`) → emit `forbidden-path-violation`.
- **Coder commits an allowed file AND leaves a dirty `.gitmodules` edit**: commit-content check passes; subsequent `post_dispatch_forbidden_revert` catches the dirty edit and emits `forbidden-path-violation`.
- **Coder commits and ALSO leaves clean working-tree-only edits**: commit captured via `baseline_head..current_head` diff; subsequent `delta_paths_after_dispatch` path is skipped; remaining clean tracked changes are picked up by the parent's `_stage_and_push_ci_fixes` capture step. Acceptable.
- **Coder commits, then `_stage_and_push_ci_fixes` push fails**: standard CI-fix retry budget engages; same as helper-owned-commit failure.

## Failure modes

1. **Forbidden-path detection misses a path** (e.g., new submodule added between baseline capture and the coder's commit such that `forbidden_paths_file` doesn't list it): the pre-dispatch `forbidden_paths_file` is computed once at lines 291-295 and not refreshed. Mitigation: this is a pre-existing gap that affects the working-tree path too — `relevant-checks` on the next CI re-run catches it. Acceptable for this PR. Earliest warning: CI re-run failing on relevant-checks after the broken push.
2. **`git reset --hard "$baseline_head"` fails** (index corruption, lock contention): the `|| true` ensures `fail_status` still emits. The repo may be left in an inconsistent state; subsequent `git` commands in the parent surface the failure. The `baseline_clean=true` guard makes this exceedingly unlikely outside of catastrophic system errors.
3. **Symbolic-ref check returns empty pre-dispatch** (detached HEAD before dispatch): `baseline_branch=""` is recorded; the post-dispatch comparison `baseline_branch != current_branch` catches the case where the coder somehow re-attached to a branch — the path falls into the failure branch. This is desired: detached-HEAD-then-attach is not a supported recovery.
4. **`merge-base --is-ancestor` aborts on missing commit** (e.g., coder force-pushed): returns non-zero → failure branch. Safe.
5. **Test stub framework lacks `LINT_FIX_HEAD_CHANGED` knob**: the ship-pr test stub is extended in this PR (small env-var honored by the existing stub). Lint-fix-loop tests exercise the real script, so the contract is verified there.

## Testing strategy

- **`scripts/test-lint-fix-loop.sh`**: case 1 rewritten + 4 new cases (forbidden-path-in-commit, detached-HEAD-after-dispatch, branch-switch-after-dispatch, dirty-baseline-plus-head-change). Run `bash scripts/test-lint-fix-loop.sh` and verify all cases pass.
- **`scripts/test-ship-pr.sh`**: per-job head-changed case rewritten to the happy-path shape with the new assertions. Run `bash scripts/test-ship-pr.sh` (or its Makefile target).
- **`bash scripts/relevant-checks.sh`**: run after edits per `AGENTS.md` editing rules; resolve any new violations.
- **Manual verification**: not feasible in this PR (would require dispatching real Codex/Cursor on a CI failure). The harness coverage is the contract.

## Diff size estimate

The six files together: ~210 net lines.
- `scripts/lint-fix-loop.sh`: ~60 (more guards, helper, three new code paths beyond the original ~40)
- `scripts/lint-fix-loop.md`: ~25
- `scripts/test-lint-fix-loop.sh`: ~80 (case 1 rewrite + 4 new cases)
- `scripts/test-ship-pr.sh`: ~35 (full rewrite of the per-job head-changed case to happy-path shape)
- `SECURITY.md`: ~5
- `docs/linting.md`: ~5


## Acceptance

The fix is accepted when all of the following hold on `main`:

1. **`scripts/lint-fix-loop.sh` behavior**: when an external coder commits a fix on the same named branch with `baseline_head` as an ancestor and a clean pre-dispatch baseline, the script emits `LINT_FIX_STATUS=applied`, `LINT_FIX_COMMIT_SHA=<new HEAD>`, `LINT_FIX_HEAD_CHANGED=true`, and a `LINT_FIX_DELTA_PATHS_FILE` whose contents reflect `git diff --name-only baseline_head..current_head`. All other HEAD-drift shapes (detached, branch switch, history rewrite, dirty baseline) continue to emit `LINT_FIX_STATUS=failed FAILURE_REASON=head-changed-after-dispatch`.
2. **Commit-content forbidden-path enforcement**: a coder commit that touches a path equal to or under any entry in `forbidden_paths_file` triggers `git reset --hard "$baseline_head"` and emits `LINT_FIX_STATUS=failed FAILURE_REASON=forbidden-path-violation`. Matching uses prefix semantics identical to `post_dispatch_forbidden_revert`.
3. **Working-tree forbidden cleanup**: after a coder commit passes the commit-content check, `post_dispatch_forbidden_revert` still runs on the working tree to catch uncommitted forbidden edits.
4. **`scripts/test-lint-fix-loop.sh`**: case 1 rewritten to assert `rc=0`, `LINT_FIX_STATUS=applied`, `LINT_FIX_HEAD_CHANGED=true`, and a delta-paths file containing `tracked.txt`. New regression cases for forbidden-path-in-commit, detached-HEAD-after-dispatch, branch-switch-after-dispatch, and dirty-baseline-plus-head-change all pass.
5. **`scripts/test-ship-pr.sh`**: the per-job head-changed case is rewritten to the happy-path shape with `assert_rc 0`, `push-calls.txt` present, no `STALL_TRACKING=true`, ci-wait invoked twice, and the `ship-pr-ci-per-job` lint-fix site exercised.
6. **`scripts/lint-fix-loop.md`** documents the accepted-coder-commit branch, its three invariants (same branch, ancestor preserved, clean baseline), the prefix-aware commit-content forbidden-path check, and the new `LINT_FIX_HEAD_CHANGED=true` output field.
7. **`SECURITY.md`** describes the lint-fix-loop accepted-coder-commit path and its mechanical checks per AGENTS.md security-relevant-behavior contract.
8. **`docs/linting.md`** describes the revised lint-fix-loop behavior (no longer fail-closed on every HEAD drift).
9. `bash scripts/relevant-checks.sh` passes.
10. `bash scripts/test-lint-fix-loop.sh` and `bash scripts/test-ship-pr.sh` (or their Makefile targets) pass.

diff_lines: 210
