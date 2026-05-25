# commit-implementation.sh

Thin Step 4 wrapper around `scripts/git-commit.sh`. Emits `token-ledger.sh` and `timing-ledger.sh` marks for "Step 4 — commit implementation" before the git commit, inheriting `LARCH_TIMING_LEDGER` and `LARCH_TOKEN_SESSION_ID` from the caller environment.

Usage:

```bash
commit-implementation.sh --message "Implement feature" [files...]
commit-implementation.sh --message "Recover implementation" --pathspec-from-file paths.nul --pathspec-file-nul
```

When `--pathspec-from-file` is present, positional file args are ignored and the wrapper passes `--only --pathspec-from-file <PATH>` through to `scripts/git-commit.sh`. Add `--pathspec-file-nul` for NUL-delimited path lists. This mode is used by malformed-manifest recovery so pre-existing staged content is not swept into the synthesized implementation commit.

Output:

- `COMMITTED=true|false`
- `SHA=<head-sha-or-empty>`
- `ERROR=<message>` on failure
