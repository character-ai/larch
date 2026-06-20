## Decision 1: Parity posture
- **Question**: The cli.py git/push verbs are "parity-verified on main." How much parity work should the plan budget?
- **Resolution**: Proactive full audit. Systematically diff every retired helper against its cli.py verb (flags, exit codes, stdout/stderr) and fix all gaps preemptively in python/git.py, push.py, phantom.py before deletion. Larger plan accepted.
- **Source**: user

## Decision 2: Adjacent-helper scope (opportunistic retirement)
- **Question**: If cutover surfaces a git/phantom Bash helper NOT on the 19-helper list, retire it too or stay strictly on the list?
- **Resolution**: Opportunistically retire adjacent git/phantom helpers. Codebase finding: NO adjacent git/phantom plumbing helpers exist beyond the 19 + survivor. The only non-listed candidate, scripts/check-stale-plugin.sh, is a plugin-staleness check, unrelated to git/phantom plumbing — out of scope. The issue's 19-helper list is already comprehensive for this domain.
- **Source**: user + codebase

## Decision 3: Atomicity — single PR
- **Question**: Land the migration atomically or split?
- **Resolution**: Single atomic PR. Every helper deletes together so no live consumer references a half-removed surface (issue Decision 1, DoD).
- **Source**: issue

## Decision 4: Survivor lib-phantom-probe.sh
- **Question**: Retire or keep scripts/lib-phantom-probe.sh?
- **Resolution**: Keep it (sourced library). Repoint its internals to `cli.py git phantom-probe`. Do NOT double-append warnings — the Python path already emits PHANTOM_* keys and handles warning append.
- **Source**: issue

## Decision 5: Preserve parity output (legacy stderr prefixes)
- **Question**: Remove legacy `git-commit.sh:`-style stderr prefixes inside python/git.py/push.py and pytest assertions?
- **Resolution**: Keep them. They are intentional parity output (issue Decision 3). The retired-scripts lint must continue to tolerate them (confirm migration_lint.py exclusions cover python/ port files).
- **Source**: issue

## Decision 6: Preserve fail-open exit codes
- **Question**: Normalize argument-error exit codes across verbs?
- **Resolution**: Preserve fail-open behavior where callers rely on it (e.g. snapshot-untracked.sh, check-remote-branch.sh exit 0 on parse error) (issue Decision 4). The proactive parity audit must verify these specifically.
- **Source**: issue

## Decision 7: Test-coverage bar
- **Question**: How to handle deletion of the 6 Bash test harnesses (test-git-commit-only, test-check-main-sync, test-check-clean-tree, test-check-phantom-dirty, test-phantom-probe-with-warn, test-git-push)?
- **Resolution**: Before deleting each Bash harness, confirm python/test_git.py / test_push.py / test_phantom.py cover its behavior; add pytest cases for any gap. No silent coverage loss (issue Decision 2).
- **Source**: issue

## Decision 8: Migration recording + acceptance gate
- **Question**: How is deletion recorded and verified?
- **Resolution**: Append every deleted path (.sh, .md sibling, test-*.sh) to python/migrated-scripts.tsv with `#3692`. Acceptance: `make lint-retired-scripts` (= python/cli.py lint retired-scripts), `make py-lint`, `make py-test`, `make lint` all clean, no coverage regression (DoD).
- **Source**: issue + codebase

## Decision 9: Do NOT redo #4642
- **Question**: Touch _MACHINE_STDOUT_KEYS registration or create-pr/merge-pr/rebase-checkpoint-probe?
- **Resolution**: No. #4642 already registered all git verbs + push branch/force and deleted create-pr.sh / merge-pr.sh / rebase-checkpoint-probe.sh. Do not redo registration; those are not repoint targets.
- **Source**: issue
