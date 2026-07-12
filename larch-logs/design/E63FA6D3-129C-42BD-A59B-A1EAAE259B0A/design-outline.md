## Proposed Design Outline

### Goals
- Replace the direct marker-only commit in `/learn-from-bugs` with a branch-push + PR flow.
- Merge the PR with `--admin` when possible; fall back to prompting the user to merge manually.
- Apply the fix to both default mode and filing mode (both run the same `git commit --only` step).

### Non-goals
- No change to report generation, issue mining, or proposal reconciliation logic.
- No change to the `/issue` filing step in filing mode.
- No change to rollback behavior on `write-state` failure.

### Approach sketch
- After `write-state` succeeds, create a short-lived branch (`chore/learn-from-bugs-state-<date>`).
- Commit `MARKER_REL` to that branch with the existing message.
- Push the branch and create a PR via `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" pr create --body-file`.
- Try `gh pr merge --admin --merge --auto` on `ANALYSIS_ROOT`; on failure (403 / no admin), print a prompt asking the user to merge the PR.
- Extract the shared commit+PR+merge sequence into a bash fragment reused by both modes.

### Surfaces in scope
- `skills/learn-from-bugs/SKILL.md` (default-mode marker-only commit section and filing-mode "Scan marker after successful create" section)

### Open questions
- None.
