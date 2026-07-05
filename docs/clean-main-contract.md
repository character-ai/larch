# Clean-main entry contract for `/implement` and `/design`

`/implement` and standalone `/design` fail closed at entry unless one of two preconditions holds. The check runs in `python/cli.py admission preflight` before any side effects — for `/implement`, before any tracking-issue side effects (no issue is created, no metadata summary is planted) and before any branch is created; for standalone `/design` (which does not create a tracking issue at entry), before any branch is created. An aborted entry leaves no remote state behind.

**(a) Default — clean `main`.** The skill asserts that the working tree is on `main`, has no uncommitted changes, fetches `origin/main`, and rebases local `main` onto it. A dirty tree, a non-`main` branch with no recognized prefix, or a fetch failure aborts with a normalized error.

**(b) Continuation opt-in — `<USER_PREFIX>/*` feature branch.** Running on a branch whose name starts with your configured `<USER_PREFIX>/` (e.g., `sergey-zhupanov/foo`) is the explicit signal that you want to continue from current state. The gate is bypassed; the skill keeps working on the current branch.

**(c) `--issue <N>` does not waive the gate.** Adopting an existing tracking issue with `--issue <N>` controls *identity* (which issue is updated and auto-closed) but does not relax the working-tree requirement. You still need either a clean `main` or a `<USER_PREFIX>/*` branch to start.

**(d) Failure modes and recovery.** When preflight fails, the orchestrator prints the raw `PREFLIGHT_ERROR=...` followed by a normalized message naming the skill that was invoked. From `/implement`:

> ⚠ /implement requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run (the branch naming convention is the explicit opt-in to continue from current state); (c) commit or stash uncommitted changes on `main` first.

Standalone `/design` prints the same message with `/design` substituted for `/implement`. The three remediation paths (clean `main`, `<USER_PREFIX>/*` continuation, commit-or-stash) cover dirty trees, wrong-branch starts, and transient fetch failures.
