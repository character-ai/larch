# commit-implementation.sh

Thin Step 4 wrapper around `scripts/git-commit.sh`. Emits `token-ledger.sh` and `timing-ledger.sh` marks for "Step 4 — commit implementation" before the git commit, inheriting `LARCH_TIMING_LEDGER` and `LARCH_TOKEN_SESSION_ID` from the caller environment.

Usage:

```bash
commit-implementation.sh --message "Implement feature" [files...]
```

Output:

- `COMMITTED=true|false`
- `SHA=<head-sha-or-empty>`
- `ERROR=<message>` on failure
