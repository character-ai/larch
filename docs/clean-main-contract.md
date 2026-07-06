# Clean-main entry contract for `/implement` and `/design`

`/implement` fails closed at entry unless one of two preconditions holds. It checks before remote side effects: no tracking issue is created, no metadata summary is planted, and no branch is created. `session entry-gate` checks the branch name first. `python/cli.py admission preflight` then enforces the result. An aborted entry leaves no remote state behind.

**(a) Default: clean `main`.** The default gate requires all of these conditions:

- the current branch is `main`
- the working tree is clean
- `git stash list` is empty
- `origin/main` can be fetched
- local `main` can be checked and rebased onto `origin/main`

A dirty tree, non-empty stash, non-`main` branch with no recognized prefix, fetch failure, sync failure, or rebase failure aborts with a normalized error.

**(b) Continuation opt-in: `<USER_PREFIX>/*` feature branch.** For `/implement`, a branch name that starts with your configured `<USER_PREFIX>/` (for example, `sergey-zhupanov/foo`) signals that you want to continue from the current state. This bypass covers branch position and main-sync checks only. Working-tree cleanliness and an empty stash still apply on a feature branch.

**(c) `--issue <N>` does not waive the gate.** Adopting an existing tracking issue with `--issue <N>` controls *identity*: which issue is updated and auto-closed. It does not relax the working-tree or stash requirement. You still need either a clean `main` or a `<USER_PREFIX>/*` branch to start `/implement`.

**(d) Failure modes and recovery.** When preflight fails, `/implement` prints the raw `PREFLIGHT_ERROR=...`, then this normalized message:

> ⚠ /implement requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run. This bypass covers branch position and main-sync only; stash cleanliness still applies on feature branches; (c) commit or stash uncommitted changes on `main` first; (d) clear a non-empty stash with `git stash pop` to restore and commit, or `git stash drop` to discard.

Use the recovery path that matches the raw preflight error:

- Wrong branch: switch to `main`, or use a `<USER_PREFIX>/*` branch for `/implement` continuation.
- Dirty tree: commit or stash uncommitted changes before re-running.
- Non-empty stash: run `git stash pop` or `git stash drop` before re-running.
- Fetch, sync, or rebase failure: repair local Git state, then re-run.

## Standalone `/design`

`/design` now uses the same default entry gate as `/implement`: start on `main`, keep the working tree clean, and keep `git stash list` empty. It also runs the shared fetch, sync, and rebase preflight. `/design` does not use the `<USER_PREFIX>/*` continuation bypass.

On failure, `/design` prints the raw `PREFLIGHT_ERROR=...` line and this message:

> ⚠ /design: session setup failed. Investigate `PREFLIGHT_ERROR` and re-run.
