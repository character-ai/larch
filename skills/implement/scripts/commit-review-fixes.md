# commit-review-fixes.sh

Thin Step 7 wrapper around `scripts/git-commit.sh`. Emits `token-ledger.sh` and `timing-ledger.sh` marks for "Step 7 — commit review fixes" before the git commit, inheriting `LARCH_TIMING_LEDGER` and `LARCH_TOKEN_SESSION_ID` from the caller environment.

Usage:

```bash
commit-review-fixes.sh [--message "Address code review feedback"] [files...]
```

Output:

- `COMMITTED=true|false`
- `SHA=<head-sha-or-empty>`
- `ERROR=<message>` on failure
