# commit-implementation.sh

Thin Step 4 wrapper around `scripts/git-commit.sh`. Emits `python3 python/cli.py token` and `python3 python/cli.py timing` marks for "Step 4 — commit implementation" before the git commit, inheriting `LARCH_TIMING_LEDGER` and `LARCH_TOKEN_SESSION_ID` from the caller environment while forcing `LARCH_TIMING_SKILL=implement` for the timing mark.

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

When telemetry env keys are absent, the wrapper self-rehydrates `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` from `$IMPLEMENT_TMPDIR/session-env.sh` before marking Step 4.
