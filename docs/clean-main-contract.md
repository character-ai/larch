# Clean-main entry contract for `/implement` and `/design`

`/implement` fails closed at entry unless one of two preconditions holds. It checks before any side effects: no tracking issue is created, no metadata summary is planted, and no branch is created. `session entry-gate` checks the branch name first; `python/cli.py admission preflight` then enforces the result. An aborted entry leaves no remote state behind.

**(a) Default: clean `main`.** The skill checks that the working tree is on `main` with no uncommitted changes, fetches `origin/main`, and rebases local `main` onto it. A dirty tree, a non-`main` branch with no recognized prefix, or a fetch failure aborts with a normalized error.

**(b) Continuation opt-in: `<USER_PREFIX>/*` feature branch.** A branch name that starts with your configured `<USER_PREFIX>/` (for example, `sergey-zhupanov/foo`) signals that you want to continue from the current state. The gate is bypassed, and the skill keeps working on the current branch.

**(c) `--issue <N>` does not waive the gate.** Adopting an existing tracking issue with `--issue <N>` controls *identity*: which issue is updated and auto-closed. It does not relax the working-tree requirement. You still need either a clean `main` or a `<USER_PREFIX>/*` branch to start.

**(d) Failure modes and recovery.** When preflight fails, `/implement` prints the raw `PREFLIGHT_ERROR=...`, then this normalized message:

> ⚠ /implement requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run; (c) commit or stash uncommitted changes on `main` first.

The three remediation paths (clean `main`, `<USER_PREFIX>/*` continuation, commit-or-stash) cover dirty trees, wrong-branch starts, and transient fetch failures.

## Standalone `/design`

`/design` does not check the branch at all. It always continues on the current branch, whatever it is named. It still requires a clean working tree: a dirty tree aborts with a raw `PREFLIGHT_ERROR=...` line and this message:

> ⚠ /design: session setup failed. Investigate `PREFLIGHT_ERROR` and re-run.
