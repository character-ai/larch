# scripts/test-lint-fix-loop.sh

Purpose: regression-test `scripts/lint-fix-loop.sh` safety around external
coder dispatch and helper-owned commits.

The harness builds disposable git repositories plus fixture script copies. One
case uses a stub external agent wrapper that edits and commits, and asserts the
helper fails closed on `HEAD` drift. Another case uses a stub wrapper that only
edits while a fixture `git-commit.sh` fails, and asserts the helper resets the
staged delta paths before reporting failure.

Primary callers: `make test-lint-fix-loop` and `make test-harnesses`.

Edit in sync: update `scripts/test-lint-fix-loop.sh` with
`scripts/lint-fix-loop.sh` and `scripts/lint-fix-loop.md` whenever dispatch
safety, commit ownership, failure reasons, or clean-index rollback behavior
changes.
