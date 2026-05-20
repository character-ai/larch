# test-auto-resolve-changelog.sh

Offline regression harness for `scripts/auto-resolve-changelog.sh`. Builds tiny temporary git repositories with an in-progress rebase and conflicted `CHANGELOG.md`, then asserts merged output and exit codes.

Wired as `make test-auto-resolve-changelog`.
