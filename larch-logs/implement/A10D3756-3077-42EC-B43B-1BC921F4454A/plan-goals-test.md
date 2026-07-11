## Goal
Implement issue #6899: [IMPLEMENTING] [BUG] scope-disposition residuals: origin/main hardcode, churn-as-coverage.

## Implementation Plan
## Plan

## Approach

Replace the `origin/main` assumption with a typed base-resolution result that distinguishes a missing usable remote default branch from a merge-base failure.

1. Read `FORKED_TARGET` only from trusted run-state files. When `ship-pr-state.sh` exists, it is authoritative; otherwise read `session-env.sh`. Treat only the exact trusted value `true` as forked-target mode. Default to `false` for a missing, malformed, or non-true key. Never use ambient process state.
2. Select `origin` for normal runs and `upstream` for forked-target runs.
3. Resolve `refs/remotes/<remote>/HEAD` with `git symbolic-ref --short`.
4. Validate symbolic-ref output before using it in Git argv: it must be non-empty, non-option-like, and exactly under the selected remote (`<remote>/<branch>`). Allow branch names containing slashes.
5. If the selected remote default branch resolves, run `git merge-base <resolved-remote-branch> HEAD`.
   - On success, use the live merge base and attribute both committed `baseline..HEAD` paths and current working-tree paths.
   - On merge-base failure, raise `ShipError` so coverage recomputation fails loudly. Do not silently under-count committed coverage with a working-tree-only result.
6. Only when the selected remote default branch cannot be resolved or validated, fall back to `step2-baseline.txt`. Mark this as frozen, emit a sanitized stderr diagnostic naming the remote and fallback, and do not invoke `git diff <baseline>..HEAD`.
7. On frozen fallback, derive candidate coverage only from porcelain working-tree paths. Persist trusted internal provenance for plan paths first observed during fallback, including a bounded path-state signature:
   - record whether each path was present or absent, plus a content or link-target digest for present paths;
   - on every recomputation, retain a persisted path only while its current worktree or `HEAD` state matches the recorded signature;
   - prune entries whose observed state no longer matches, including a committed change later reverted with a clean worktree.
   This preserves coverage after dispatcher commits leave the tree clean without letting stale committed or reverted churn satisfy coverage.
8. Keep plan-path filtering and fingerprint construction unchanged after touched-path attribution. The frozen sidecar is internal provenance only. It cannot be replaced by implementer-authored manifest claims or alter `PlanCoverage`, coverage JSON/env, fingerprint, disposition, or CLI wire formats.
9. Keep live-base behavior stable across pre-commit and post-commit recomputation. Frozen fallback remains conservative: it can retain only verified path states first seen in this run’s porcelain state, and never treats upstream committed churn as coverage.

## Files to modify/create

### UPDATED: python/larch/implement/scope_disposition.py

- Add a frozen internal baseline-resolution result type carrying:
  - the selected baseline SHA;
  - whether committed-path attribution is trustworthy;
  - whether frozen fallback provenance is active;
  - selected remote and sanitized diagnostic context.
- Add trusted `FORKED_TARGET` lookup with deterministic lifecycle precedence:
  - read `ship-pr-state.sh` when that file exists;
  - otherwise read `session-env.sh`;
  - accept only exact `true` as forked mode;
  - default false for missing, malformed, or non-true values;
  - never consult `os.environ`.
- Resolve the selected remote’s symbolic default branch rather than assuming `origin/main`.
- Reject empty, malformed, cross-remote, and option-like symbolic-ref output before it can reach `git merge-base`.
- Make remote-ref resolution failure distinct from merge-base failure:
  - unresolved or invalid selected remote HEAD uses the frozen Step 2 fallback;
  - a valid selected remote branch with failed `git merge-base` raises `ShipError` for an explicit coverage-recompute failure.
- Update `_merge_base_baseline` and `_baseline_sha` to return the typed provenance result rather than a bare SHA.
- Split committed diff paths from porcelain working-tree paths in `touched_paths_since_baseline`.
- For live merge-base resolution, retain current committed-diff plus porcelain attribution.
- For frozen fallback:
  - skip `git diff <baseline>..HEAD` entirely, so an invalid frozen range after rebase or shallow-history changes cannot block coverage;
  - always collect porcelain status paths, including modified, renamed, copied, and untracked paths;
  - read and update a trusted internal fallback-provenance sidecar containing only in-scope plan paths first observed while fallback is active;
  - record a verifiable path-state signature for each observed path, including deleted rename/copy source paths;
  - before using persisted entries, compare their signatures with the current worktree or `HEAD` path state and discard mismatches;
  - union current porcelain plan paths with only verified persisted fallback paths before coverage filtering, so clean-tree post-commit recomputation remains stable but a later revert removes stale coverage.
- Keep sidecar parsing strict and bounded. Treat malformed sidecar data as unusable provenance rather than a coverage source.
- Emit a sanitized stderr warning for unresolved remote HEAD fallback without changing machine-readable stdout or persisted coverage schemas.
- Ensure a live merge-base failure has a clear `ShipError` message identifying the selected remote/ref failure context.
- Update comments and docstrings that currently describe `origin/main` as the universal base.
- Preserve existing `PlanCoverage`, coverage JSON/env, fingerprint, disposition, and CLI output contracts.

### UPDATED: python/tests/implement/test_scope_disposition.py

- Extend `FakeRunner` to model symbolic-ref resolution independently from merge-base resolution.
- Define an unambiguous successful live-base default so existing `FakeRunner(diff_paths=...)` tests remain live-base tests:
  - default normal symbolic-ref resolution returns `origin/main`;
  - forked-target tests can default or explicitly configure `upstream/main`;
  - default merge-base resolution returns a non-empty successful SHA;
  - explicit failure sentinels or configuration are required for symbolic-ref and merge-base failures.
- Audit existing `FakeRunner(diff_paths=...)` call sites and retain their intended live-base assertions unless a test specifically targets frozen fallback behavior.
- Replace the hardcoded `origin/main` assertion with coverage for an `origin/trunk` remote HEAD.
- Add forked-target coverage proving trusted state selects `upstream/<default>`.
- Add state-precedence coverage for:
  - early session-only state;
  - later ship-state-only state;
  - conflicting `session-env.sh` and `ship-pr-state.sh` values, with `ship-pr-state.sh` deterministically winning;
  - missing or malformed keys defaulting to normal (`origin`) mode without ambient-environment fallback.
- Verify normal runs ignore an unrelated upstream HEAD and forked runs ignore origin HEAD.
- Verify malformed, cross-remote, empty, and unresolved symbolic refs never reach `git merge-base`, use the frozen fallback, and emit the fallback diagnostic.
- Verify a valid resolved remote branch is passed exactly to `git merge-base`.
- Add explicit merge-base-failure coverage: a valid remote HEAD followed by failed `git merge-base` raises coverage recomputation failure rather than entering frozen fallback.
- Rewrite `test_compute_requires_step2_baseline` to force symbolic-ref failure before asserting that `step2-baseline.txt` is required. Keep this requirement scoped to frozen fallback only.
- Add a separate live-base test proving successful symbolic-ref and merge-base resolution computes coverage without `step2-baseline.txt`.
- Rewrite `test_baseline_falls_back_to_step2_without_origin_main` so it asserts frozen fallback does not run or attribute `STEP2BASE..HEAD`, retains the frozen SHA only as internal diagnostic provenance, and sources touched paths from porcelain status.
- Verify frozen fallback counts modified, renamed, copied, and untracked working-tree plan paths.
- Add the invalid-range regression: symbolic-ref fallback with a would-fail baseline diff still returns porcelain plan paths rather than raising before status is consulted.
- Add the core upstream-churn regression: a plan path present only in `baseline..HEAD` cannot be marked covered on frozen fallback.
- Add a post-commit frozen-fallback regression:
  1. compute coverage with an uncommitted plan path while remote HEAD is unavailable;
  2. simulate dispatcher commit by clearing porcelain status while preserving the observed path state;
  3. call `record_disposition` without an explicit coverage argument;
  4. verify the trusted fallback provenance preserves the original plan-path coverage and avoids a stale/live-coverage mismatch.
- Add a stale-provenance regression:
  1. observe a fallback edit and persist its path-state signature;
  2. simulate commit, then a later revert that restores the prior file state and clears porcelain status;
  3. recompute coverage;
  4. verify the signature mismatch prunes the persisted path and the reverted path is no longer covered.
- Retain a test proving live-base coverage still ignores non-plan and run-log paths.
- Verify fallback diagnostics do not alter machine-readable stdout.

## Edge cases

- `refs/remotes/origin/HEAD` or `refs/remotes/upstream/HEAD` may be absent in shallow clones or fixtures.
- Forked flows may have only `upstream/HEAD`, only `origin/HEAD`, or neither. Only the selected remote is relevant.
- Both trusted state files may exist with conflicting `FORKED_TARGET` values. `ship-pr-state.sh` remains authoritative whenever present.
- The selected state file may omit or malformedly encode `FORKED_TARGET`. That file remains authoritative and defaults to normal mode.
- The symbolic ref may point to a deleted branch, contain an unexpected remote prefix, be empty, or be option-like.
- A remote default branch may contain slashes.
- The selected remote branch may resolve while no merge base exists because history is shallow. This is a loud recomputation failure, not a frozen fallback.
- A frozen Step 2 SHA may no longer form a valid `baseline..HEAD` range after a rebase. Frozen fallback must not attempt that diff.
- The worktree may contain rename or copy records with two paths.
- Coverage may be recomputed after dispatcher commits or run-log flush commits. Live-base attribution remains stable. Frozen fallback retains only plan paths whose current worktree or `HEAD` state still matches provenance first observed from this run’s porcelain state.
- A fallback-observed edit may be committed and later reverted. The provenance signature must no longer match and must not satisfy coverage.
- The internal fallback sidecar must be trusted, bounded to plan paths, and unavailable as a manifest-controlled coverage source.

## Failure modes

- Do not silently treat an unresolved default branch as `main`.
- Do not pass unvalidated state or symbolic-ref text into Git argv.
- Do not let `session-env.sh` override an existing later `ship-pr-state.sh`.
- Do not let a stale frozen baseline grant coverage from committed paths.
- Do not fail open when the selected remote HEAD resolves but merge-base computation fails.
- Do not run a possibly invalid frozen `baseline..HEAD` diff before collecting porcelain fallback paths.
- Do not allow clean-tree post-commit recomputation to erase verified fallback coverage first observed in the same run.
- Do not let persistent fallback provenance survive a reverted, deleted, or otherwise changed observed path state.
- Do not change coverage artifact schemas merely to expose internal baseline provenance.
- Do not suppress the frozen-fallback diagnostic. Operators need to know why attribution became conservative.

## Testing strategy

Run only the changed-file checks:

- `python3 -m pytest python/tests/implement/test_scope_disposition.py`
- Run the repository’s Python lint and type-check commands scoped to:
  - `python/larch/implement/scope_disposition.py`
  - `python/tests/implement/test_scope_disposition.py`

Confirm the focused tests cover:

- successful normal and forked live-base resolution;
- successful live-base coverage without `step2-baseline.txt`;
- trusted-state precedence and malformed-state defaults;
- frozen-fallback-only missing Step 2 baseline failure;
- unresolved-ref frozen fallback;
- loud merge-base failure;
- pre-commit porcelain attribution;
- post-commit `record_disposition` recomputation with verified frozen-fallback provenance retention;
- reverted fallback edits being removed from coverage; and
- upstream plan-path churn being unable to satisfy coverage on fallback.

## Acceptance

Run only the changed-file checks:

- `python3 -m pytest python/tests/implement/test_scope_disposition.py`
- Run the repository’s Python lint and type-check commands scoped to:
  - `python/larch/implement/scope_disposition.py`
  - `python/tests/implement/test_scope_disposition.py`

Confirm the focused tests cover:

- successful normal and forked live-base resolution;
- successful live-base coverage without `step2-baseline.txt`;
- trusted-state precedence and malformed-state defaults;
- frozen-fallback-only missing Step 2 baseline failure;
- unresolved-ref frozen fallback;
- loud merge-base failure;
- pre-commit porcelain attribution;
- post-commit `record_disposition` recomputation with verified frozen-fallback provenance retention;
- reverted fallback edits being removed from coverage; and
- upstream plan-path churn being unable to satisfy coverage on fallback.

diff_added: 225
diff_deleted: 45
mechanical_churn: false
diff_lines: 270

## Test plan
(no test plan section in plan-file)
