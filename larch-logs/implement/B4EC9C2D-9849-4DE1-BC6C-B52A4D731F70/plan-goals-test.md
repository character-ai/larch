## Goal
Fix agnix AS-014 false positive: disable rule in .agnix.toml and rewrite escaped-dot patterns in github-remote-repo.sh

## Implementation Plan

### Goal
Fix agnix AS-014 false positive on escaped-dot bash regex patterns in `scripts/github-remote-repo.sh`. The fix is two-pronged (Options B + C from the issue):

**Option B** — Disable AS-014 in `.agnix.toml` since it produces false positives for `\.` inside bash `[[ =~ ]]` regex context (agnix v0.27.1 incorrectly flags these as Windows path separators).

**Option C** — Rewrite the two offending `\.` patterns in `scripts/github-remote-repo.sh` to use `[.]` instead, which is equivalent regex syntax but avoids the backslash-dot form that triggers AS-014.

### Files to modify

1. **`.agnix.toml`** — add `"AS-014"` to the `disabled_rules` list with a comment explaining the false positive context.

2. **`scripts/github-remote-repo.sh`** — change lines 25 and 30:
   - Line 25: `^git@github\.com:` → `^git@github[.]com:`
   - Line 30: `github\.com/` → `github[.]com/`

### Edge cases
- Both `\.` and `[.]` are functionally identical in bash `[[ =~ ]]` POSIX extended regex. The change is purely syntactic.
- No other files reference these patterns.
- The `scripts/github-remote-repo.md` sibling doc does not mention the regex syntax, so no doc update needed.
- Per the issue, Option A (pinning the CI binary version) is not pursued here because the CI yaml uses `agent-sh/agnix@v0.17.0` without a `version:` parameter; any drift is via the GitHub Action's bundled binary, and the combination of Options B+C provides best protection regardless of future version drift.


## Test plan
1. Run `make agent-lint` — should report zero AS-014 errors.
2. After the fix, if the failing agnix version (v0.27.1) is available locally, run `./agnix . --strict --target claude-code --config .agnix.toml` to confirm zero errors.
3. The existing pre-commit hook and `/relevant-checks` (`agent-lint`) cover this path.
