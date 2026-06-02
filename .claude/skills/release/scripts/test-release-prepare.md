# test-release-prepare.sh — harness contract

Offline PATH-shimmed `gh` and `git` fixtures for `release-prepare.sh` (no network, no real clocks).

## Cases

1. Unique `isLatest` → success KV + `PR_COUNT=1` with `(#N)` extraction.
2. Zero `isLatest` → `ERROR=no-unique-latest-release`, exit **1**.
3. Multiple `isLatest` → same error.
4. `main` OID ≠ `origin/main` → `ERROR=stale-local-main`.
5. `--bump major` override → `BUMP_TYPE=MAJOR`, `NEW_VERSION=2.0.0`.
6. Empty PR log → `PR_COUNT=0`.

## Invocation

```bash
make test-release-prepare
```

## Edit-in-sync

- `.claude/skills/release/scripts/release-prepare.sh`
