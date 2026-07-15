## Goal
Implement issue #7405: [IMPLEMENTING] [BUG] [TRIAGED] push branch fails with upstream tracking mismatch on feature branches.

## Implementation Plan
## Summary

`python3 python/cli.py push branch` fails with exit 128 when the feature branch's local upstream tracking was set to a different remote ref (e.g., `main`) rather than the feature branch itself. The error is `fatal: The upstream branch of your current branch does not match the name of your current branch`. The command uses `git push -u origin HEAD` without an explicit remote refspec, which triggers this failure under non-default `push.default` or `branch.autoSetupMerge` git configurations.

## Original report

During /implement run BA7BF6F8 for #6990, running `python3 python/cli.py push branch` on the feature branch `sergey-zhupanov/implementing-bug-treadmill-feature-migra-6990` failed with:

```
fatal: The upstream branch of your current branch does not match the name of your current branch. To push to the upstream branch on the remote, use git push origin HEAD:main. To push to the branch of the same name on the remote, use git push origin HEAD.
```

The command exited 128. The workaround was to use `git push origin HEAD` directly.

## Reproduction scenario

1. Configure git with `push.default=upstream` or `branch.autoSetupMerge=always`.
2. Run `/implement` so `step-0-bootstrap.sh` creates a new feature branch (`git checkout -b feature-...`). Under certain configurations, this sets the upstream tracking to `main` instead of the new branch.
3. Run `python3 python/cli.py push branch`.
4. Observe exit 128: `fatal: The upstream branch of your current branch does not match the name of your current branch.`

## Expected behavior

`push branch` succeeds by pushing the current branch's HEAD to `origin/<branch-name>`, regardless of the local upstream tracking configuration.

## Observed behavior

`push branch` exits 128 with a fatal git error because `git push -u origin HEAD` interprets `push.default=upstream` and pushes to the tracked upstream ref (`main`) rather than the feature branch name. Git rejects this because the local branch name does not match the remote ref name.

## Root cause analysis

`python/larch/git/git.py` line 970 implements `push_set_upstream` as:
```python
return _run(runner, ["git", "push", "-u", remote, refspec], cwd=cwd)
```

where `refspec` is `"HEAD"`. When `push.default=upstream`, git resolves `HEAD` to the tracked upstream ref (in this case `main`) and tries to push there. Git refuses because the current local branch (`feature-...`) does not match the upstream branch name (`main`).

The fix is to use an explicit refspec: `git push -u origin HEAD:refs/heads/<branch-name>` (or equivalently `origin HEAD:<branch-name>`). This bypasses the upstream tracking configuration entirely and always pushes to the matching remote branch name.

## Evidence

- `python/larch/git/push.py` line 75: `result = git.push_set_upstream(runner, remote, "HEAD", cwd=cwd)` — passes bare `"HEAD"` as refspec.
- `python/larch/git/git.py` line 970: `return _run(runner, ["git", "push", "-u", remote, refspec], cwd=cwd)` — no explicit destination ref.
- Git behavior: `git push -u origin HEAD` with `push.default=upstream` resolves to `git push -u origin HEAD:main` when the local branch tracks `main`. Git rejects this because the local branch name (`feature-...`) differs from the remote name (`main`).
- Workaround used in the run: `git push origin HEAD` (plain, without `-u`) succeeded because git's default `simple` mode for that command matches the branch name.

## Affected files

- `python/larch/git/push.py`: `push_branch` function calls `push_set_upstream(runner, remote, "HEAD")` — should pass an explicit refspec.
- `python/larch/git/git.py`: `push_set_upstream` — currently passes `refspec` verbatim; needs either an explicit refspec from the caller or resolution to the branch name internally.
- `python/tests/git/test_push.py` (or equivalent): should add a test case for `push.default=upstream` with mismatched upstream tracking.

## Suggested fix(es)

In `push_branch` (`python/larch/git/push.py`), pass the branch name as the explicit refspec:
```python
result = git.push_set_upstream(runner, remote, f"HEAD:refs/heads/{branch}", cwd=cwd)
```

This makes the push unconditionally target the correct remote branch regardless of `push.default` or upstream tracking configuration.

Alternatively, modify `push_set_upstream` to accept an optional `branch` argument and construct the full refspec there. Either way, the fix is to never rely on git's `push.default` resolution for implementation branch pushes.

## Open questions

- Does `step-0-bootstrap.sh` explicitly set the upstream tracking on branch creation? If it runs `git checkout -b <branch>` without `--no-track` and the repo uses `branch.autoSetupMerge=always`, the new branch inherits the current branch's upstream. Fixing that at branch creation time may be a complementary approach.
- Are there other call sites in the codebase that use `push_set_upstream` with bare `"HEAD"` that would also be affected?

<!-- larch:triage:start -->
## Summary

`python3 python/cli.py push branch` can exit 128 with `fatal: The upstream branch of your current branch does not match the name of your current branch.` The report is valid. The cited root cause is wrong: the failing call is the bare `git push` in `push_current_branch`, not `push_set_upstream`.

## Verified behavior

- Observation: `("push", "branch")` dispatches to `larch.git.push.branch_main` in `python/larch/cli.py`.
- Observation: `branch_main` (`python/larch/git/push.py:312`) calls `push_current_branch` (`python/larch/git/push.py:87`), which runs bare `["git", "push"]` with no refspec (`python/larch/git/push.py:112`) inside the retry loop.
- Observation: `push_set_upstream` (`python/larch/git/git.py:970`) runs `git push -u <remote> <refspec>`. `push_branch` passes explicit `"HEAD"` (`python/larch/git/push.py:75`). Its only found callers are the ship flow (`python/larch/implement/ship_pr.py:184` and `:309`), not the `push branch` CLI.
- Inference: the quoted fatal error is git's `die_push_simple`. Git emits it only for a push with no command-line refspec, with `push.default` unset or `simple`, with the same remote for push and upstream, and with an upstream branch name that differs from the local branch name. The bare push at `python/larch/git/push.py:112` meets those conditions when a feature branch tracks `origin/main`.

## Corrected root cause

`push_current_branch` pushes with no refspec, so git falls back to `push.default`. With the default `simple` mode and upstream set to `origin/main`, git refuses the name mismatch and exits 128.

The report blames `git push -u origin HEAD` in `push_set_upstream` under `push.default=upstream`. That mechanism cannot produce this error:

- `HEAD` on the command line is an explicit refspec. Git then ignores `push.default` and pushes to the branch of the same name. This is why the workaround `git push origin HEAD` succeeded.
- The quoted message comes from git's `simple` mode. With `push.default=upstream`, bare `git push` would instead try to push to `refs/heads/main`.
- The `cli.py push branch` path never reaches `push_set_upstream`.

## Immutable-main evidence

All code reads used `git show` at immutable main SHA `49c7df11a77053a7d5cb33da18605fa3afe22836`:

- `python/larch/cli.py`: dispatch row `("push", "branch"): ("larch.git.push", "branch_main")`.
- `python/larch/git/push.py:75`: `push_branch` calls `git.push_set_upstream(runner, remote, "HEAD", cwd=cwd)`. Matches the report's citation.
- `python/larch/git/push.py:87` and `:112`: `push_current_branch` runs `runner.run(["git", "push"], cwd=cwd)`.
- `python/larch/git/push.py:312`: `branch_main` calls `push_current_branch(proc)`.
- `python/larch/git/git.py:970`: `push_set_upstream` runs `["git", "push", "-u", remote, refspec]`. Matches the report's citation.
- `python/larch/implement/ship_pr.py:184` and `:309`: `push.push_branch(...)` call sites.

## Reproduction

Proposed, not executed. No fixed triage probe covers git-config-dependent push behavior.

1. In a scratch clone, create a feature branch that tracks `origin/main`, for example `git checkout -b feature origin/main`.
2. Keep `push.default` unset or `simple`.
3. Commit a change and run `python3 python/cli.py push branch`.
4. Expected: bare `git push` fails with the quoted upstream-mismatch error on every retry, then the CLI exits 128.

## Scope split

1. Primary fix: `push_current_branch` (`python/larch/git/push.py:87`). Push an explicit refspec, for example `["git", "push", "origin", "HEAD"]`. The workaround already validated this shape. Optional `-u` also repairs tracking for later pushes.
2. Optional hardening only: `push_branch` and `push_set_upstream` already pass explicit `HEAD` and are immune to this failure. `HEAD:refs/heads/<branch>` remains a defensive option.
3. Complementary, locus unverified: stop feature-branch creation from inheriting `origin/main` tracking, for example with `--no-track`. The creation code path was not located within the inspection byte caps.
4. Tests: assert the exact push argv in `push_current_branch` tests with an injected fake runner. No live git config simulation is needed.

## Missing evidence

- The committed run log `larch-logs/implement/BA7BF6F8-9DA4-4DDD-B65D-CD6BA50B5617/` does not record the push failure. `execution-issues.ndjson` holds only G-Py-11 warnings; `final-summary.md`, `breadcrumbs/quiet.log`, and `session-transcript.jsonl` have no push or upstream mention. The original report stands uncorroborated by committed logs.
- `python/larch/implement/ship.py`, `python/larch/state/session_env.py`, and `skills/implement/SKILL.md` exceeded the 64 KiB inspection cap. More `push_branch` callers or the branch-creation site may exist in the unread tails.
- The reproduction was not executed.
- How the feature branch's upstream became `origin/main` in run BA7BF6F8 is unverified.

## Fix outline

Change `push_current_branch` to push `origin HEAD` (optionally with `-u`), keep the retry and stderr dedup behavior, and add a fake-runner test asserting the new argv. Leave `push_set_upstream` callers unchanged unless /design opts into the defensive full refspec.
<!-- larch:triage:end -->

## Test plan
(no test plan section in plan-file)
