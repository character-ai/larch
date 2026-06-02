# test-release-prepare.sh — harness contract

Offline PATH-shimmed `gh` and `git` fixtures for `release-prepare.sh` (no network, no real clocks).

## Cases

1. Unique `isLatest` → success KV + `PR_COUNT=1` with `(#N)` extraction.
2. Zero `isLatest` → `ERROR=no-unique-latest-release`, exit **1**.
3. Multiple `isLatest` → same error.
4. `main` OID ≠ `origin/main` → `ERROR=stale-local-main`.
5. `--bump major` override → `BUMP_TYPE=MAJOR`, `NEW_VERSION=<CURRENT major+1>.0.0`.
6. Empty PR log → `PR_COUNT=0`.
7. `git fetch` fails → `ERROR=baseline-tag-unresolvable`.
8. Missing PR metadata → `ERROR=pr-metadata-incomplete`.
9. Open `release/v*` PR (`GH_FIXTURE_OPEN_PRS`) → `ERROR=release-cut-in-progress`.
10. Origin version ahead of baseline with `Release v*` log subject → `ERROR=release-already-cut`.
11. `gh pr list` failure → `ERROR=release-pr-list-failed`.

## Invocation

```bash
make test-release-prepare
```

## Edit-in-sync

- `.claude/skills/release/scripts/release-prepare.sh`
