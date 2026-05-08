# get-issue-info.sh

**Purpose**: Query a single field (`state` or `url`) from a GitHub issue. Replaces inline `ISSUE_STATE=$(gh issue view ...)` and `ISSUE_URL=$(gh issue view ...)` command substitutions in `/implement` Step 18 that triggered permission prompts.

**Not to be confused with**: `skills/fix-issue/scripts/get-issue-details.sh`, which fetches the full issue body + comments for `/fix-issue`'s triage workflow. This script queries a single scalar field.

**Invariants**:
- Always exits 0 (fail-open)
- Emits `VALUE=<result>` on success, `VALUE=` on any failure
- Uses `--json`/`--jq` for structured output (no grep/sed parsing)
- Accepts `--repo OWNER/REPO`; when omitted, resolves the current repo with `scripts/resolve-repo.sh` and passes `--repo` if resolution succeeds, falling back to gh's default context only when resolution fails

**Stdout contract**: `VALUE=<string>` (exactly one line).

**Call sites**:
- `skills/implement/SKILL.md` Step 18 (issue state check for stalled rename, issue URL for tracking-issue link)

**Edit-in-sync**: None.
