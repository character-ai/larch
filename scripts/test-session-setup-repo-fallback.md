# scripts/test-session-setup-repo-fallback.sh — contract

Regression harness for `scripts/session-setup.sh` repository discovery.

## Coverage

- Exercises the gh-first ordering in Section 4 when a real `gh repo view` call is available.
- Stubs `gh` failure and verifies the `origin` fallback resolves GitHub SSH and HTTPS remotes through `scripts/github-remote-repo.sh`.
- Verifies malformed and missing `origin` remotes fail soft with `REPO=` and `REPO_UNAVAILABLE=true`.

## Fixture Layout

The harness creates isolated temporary git repositories under `${TMPDIR:-/tmp}` and never depends on the repository under test as the target worktree. The `gh` failure cases prepend a temporary `gh` executable that exits 1 so `session-setup.sh` reaches the fallback path deterministically.

## Edit-in-sync

Update with `scripts/session-setup.sh` Section 4 and `scripts/github-remote-repo.sh` when changing repository discovery ordering, accepted remote URL shapes, or fail-soft behavior.
