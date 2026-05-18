## Goal
Fix apply-bump.sh phantom-file tolerance and add retry resilience (backoff, detached-HEAD, cap) to push/rebase retry loops

## Implementation Plan

### Goal
Fix two ship-pr.sh resilience issues:
A. apply-bump.sh tolerates known-larch-internal untracked files (launcher-stderr sidecars, *.redacted.log) instead of failing the version bump.
B. Retry resilience: jittered backoff, detached-HEAD pre-check, and retry cap for push/rebase retry loops.

### Files to modify

1. `.claude/skills/bump-version/scripts/apply-bump.sh`
   - Replace the single `git status --porcelain` dirty check with a two-pass check: filter `??` untracked entries matching `*.launcher-stderr` or `*.redacted.log`; only fail if non-internal dirty entries remain. Tolerated internal entries emit WARN to stderr.
   - Keep full fail for any staged/tracked-modified or other untracked files.

2. `.claude/skills/bump-version/scripts/apply-bump.md`
   - Document the new larch-internal filter behavior and add it to invariants.

3. `scripts/test-apply-bump.sh`
   - Add sub-test I: create untracked `.launcher-stderr` and `something.redacted.log` files in the test repo, assert apply-bump.sh succeeds (APPLIED=true) and emits WARN.

4. `scripts/test-apply-bump.md`
   - Add sub-test I entry.

5. `scripts/git-push.sh`
   - Replace `exec git push` with a retry loop (max 3 attempts, jittered backoff ~1s/2s, detached-HEAD check before each attempt). Exit 1 on detached HEAD.

6. `scripts/git-push.md`
   - Document retry behavior and detached-HEAD check.

7. `scripts/rebase-push.sh`
   - Add retry loop with jittered backoff (~1s/2s) for the force-push step (lines 244–252). Add detached-HEAD check before each push attempt.

8. `scripts/rebase-push.md`
   - Document force-push retry and detached-HEAD per-attempt check.

9. `scripts/ship-pr.sh`
   - `run_rebase_rebump()`: add REBASE_COUNT cap (>= 5 → exit_stall with `10-max-retries` or `12-max-retries`) and a detached-HEAD pre-check before `rebase-push.sh`.
   - `run_evaluate_failure()`: change `for _ in 1 2 3` to a tracked loop with cap 5, jittered backoff between iterations, and detached-HEAD check before each `run_ci_fix_vendor` call. Stall with step `10-max-retries` / `12-max-retries` on exhaustion.

10. `scripts/ship-pr.md`
    - Document the cap and detached-HEAD guards added to `run_rebase_rebump` and `run_evaluate_failure`.

### Edge cases
- Filter patterns are anchored to `??` untracked prefix only; staged/tracked-modified dirty entries always fail the bump.
- Detached HEAD exits immediately (no retry) in git-push.sh.
- REBASE_COUNT cap applies only to `run_rebase_rebump` (CI phases 10/12); step8b path stalls via its own rebase-failed status path.
- Backoff in git-push.sh: 1s/2s ±25% jitter (max 3 attempts → total max delay ~3s).
- Backoff in run_evaluate_failure: 2s/4s/8s ±25% jitter (max 5 attempts).


## Test plan
- `scripts/test-apply-bump.sh` sub-test I covers the apply-bump internal-artifact tolerance.
- No harness for git-push.sh retry (relies on integration), but detached-HEAD path is exercised by the existing `exit 1 on not a named branch` contract.
- `run_rebase_rebump` cap is tested implicitly when run >= 5 causes stall.
