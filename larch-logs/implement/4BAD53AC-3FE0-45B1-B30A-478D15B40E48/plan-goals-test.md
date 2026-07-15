## Goal
Implement issue #7443: [IMPLEMENTING] [BUG] [TRIAGED] feature branch tracks origin/main at creation (root cause of #7405).

## Implementation Plan
## Summary

`create_branch` starts feature branches from `origin/main` with `git checkout -b <branch> origin/main`. Under the default `branch.autoSetupMerge=true`, that sets the new branch's upstream to `origin/main`. The feature branch then tracks the wrong ref until its first push.

This is the root cause of #7405. PR #7432 made `push branch` robust with an explicit `origin HEAD` refspec, but the branch still inherits `origin/main` tracking at creation.

## Evidence

Paths on `main`.

- `python/larch/git/pr.py:229`: `base = f"{base_remote}/{base_ref}"` resolves to `origin/main` by default.
- `python/larch/git/pr.py:245`: `runner.run(["git", "checkout", "-b", branch, base], cwd=cwd)`.
- `python/larch/state/bootstrap.py:881`: `pr.create_branch(proc, branch=branch_name)` is the only feature-branch caller.
- Git default `branch.autoSetupMerge=true` sets upstream tracking when the start point is a remote-tracking branch. So `git checkout -b feature origin/main` makes `feature` track `origin/main`.
- Nothing resets that tracking before the first push. `python/larch/git/pr.py:300` runs `git branch --set-upstream-to origin/<branch>` only on a push recovery path.

## Reproduction

1. In a clone with default git config (`branch.autoSetupMerge=true`, `push.default=simple`).
2. Run `/implement` so `create_branch` makes a feature branch from `origin/main`.
3. Run `git rev-parse --abbrev-ref @{upstream}`. It returns `origin/main`, not the feature branch.

## Expected behavior

A feature branch should not track `origin/main`. It should track nothing at creation, then track `origin/<branch>` after its first push.

## Suggested fix

Add `--no-track` to the checkout in `create_branch`:

    result = runner.run(["git", "checkout", "-b", branch, "--no-track", base], cwd=cwd)

The first `push -u origin HEAD` (used by `push branch` and the ship flow) then sets upstream to `origin/<branch>`. Rebase checkpoints fetch `origin/main` with an explicit refspec, so they do not rely on the branch upstream.

## Notes

- The original #7405 report blamed "non-default" git config. The upstream inheritance to `origin/main` happens under the default config, so this is latent for all users.
- The #7405 triage deferred this as "locus unverified". The creation path is `python/larch/git/pr.py:217` `create_branch`.

<!-- larch:triage:start -->
## Summary

`create_branch` starts feature branches with `git checkout -b <branch> origin/main` and no `--no-track`. Git's default `branch.autoSetupMerge=true` then sets the new branch's upstream to `origin/main` until the first successful push. The report is valid. The locus deferred by the #7405 triage is verified on immutable main.

## Verified behavior

- Observation: `create_branch` (`python/larch/git/pr.py:217`) builds `base = f"{base_remote}/{base_ref}"` (`python/larch/git/pr.py:229`), `origin/main` by default, fetches it, then runs `["git", "checkout", "-b", branch, base]` (`python/larch/git/pr.py:245`). No `--no-track`.
- Observation: the creation path never clears tracking. `git branch --set-upstream-to origin/<branch>` (`python/larch/git/pr.py:300`) runs only inside the `_push_open_pr_branch` recovery path (`python/larch/git/pr.py:284`).
- Observation: `python/larch/state/bootstrap.py:881` runs `created = pr.create_branch(proc, branch=branch_name)`. It is the only `create_branch` reference in the first 64 KiB of that file. `create_branch_main` (`python/larch/git/pr.py:397`, `cli.py pr create-branch`) also calls the same function.
- Inference: git documents `branch.autoSetupMerge=true` as the default, and it sets upstream tracking when the start point is a remote-tracking branch. `git checkout -b feature origin/main` therefore tracks `origin/main` under default config. The report's correction of #7405's "non-default config" framing holds.
- Observation: PR #7432 (merged 2026-07-15) hardened the push paths. `push_current_branch` in `python/larch/git/push.py` pushes explicit `origin HEAD` with `-u`, and its comment cites this exact tracking scenario.

## Corrected root cause

The report's root cause is correct as filed. Two refinements:

- The wrong upstream exists only between branch creation and the first successful `push -u origin HEAD`. That push repairs tracking to `origin/<branch>`.
- After PR #7432, larch's own push paths tolerate the wrong upstream. Remaining impact falls on `@{upstream}` consumers inside that window: bare `git push` outside larch helpers, `git status` ahead/behind counts, IDE integrations, and scripts reading `git rev-parse @{upstream}`. This is a hardening fix, not a live push failure.

## Immutable-main evidence

All code reads used `git show` at immutable main SHA `8312de618d34670ba3c76c6b6508f4f9ee77a463`:

- `python/larch/git/pr.py:217` `def create_branch`; `:229` base string; `:245` checkout argv without `--no-track`; `:284` `_push_open_pr_branch`; `:300` recovery-only `--set-upstream-to`; `:397` `create_branch_main`.
- `python/larch/state/bootstrap.py:881` caller. The file exceeds the 64 KiB inspection cap.
- `python/larch/git/push.py`: `push_current_branch` pushes explicit `origin HEAD` with `-u`; the comment cites #7405.
- `python/tests/git/test_pr.py:526` and `python/tests/git/test_pr.py:563` assert argv `("git", "checkout", "-b", branch, "origin/main")`.
- PR #7432 state `MERGED`, merge commit `79b624f530c3a2874142e41d1070560f73bf245e`.

## Reproduction

Proposed, not executed. No fixed triage probe covers git-config-dependent branch tracking.

1. In a clone with default git config, run `/implement` so `create_branch` creates a feature branch from `origin/main`.
2. Run `git rev-parse --abbrev-ref @{upstream}` on the new branch.
3. Expected per report: `origin/main` prints until the first `push -u origin HEAD` succeeds.

## Scope split

1. Primary fix: add `--no-track` to the checkout argv in `create_branch` (`python/larch/git/pr.py:245`). The in-function fix covers every caller, including `cli.py pr create-branch`.
2. Tests: update the argv assertions at `python/tests/git/test_pr.py:526` and `python/tests/git/test_pr.py:563`, and assert the new `--no-track` argv with the existing fake runner.
3. No push-path changes. `push branch` and the ship flow already push explicit `origin HEAD` with `-u` (#7432), which sets tracking to `origin/<branch>` on first push.

## Missing evidence

- The reproduction was not executed.
- `branch.autoSetupMerge` semantics come from git documentation, not an executed probe.
- `python/larch/state/bootstrap.py` exceeds the 64 KiB inspection cap. More `create_branch` callers may exist in the unread tail.
- Callers of `cli.py pr create-branch` outside `python/` were not enumerated. The in-function fix covers them regardless.

## Fix outline

Change `python/larch/git/pr.py:245` to run `["git", "checkout", "-b", branch, "--no-track", base]`. Update the two argv assertions in `python/tests/git/test_pr.py`. Keep push paths unchanged. A feature branch then tracks nothing at creation and tracks `origin/<branch>` after its first push.
<!-- larch:triage:end -->

## Test plan
(no test plan section in plan-file)
