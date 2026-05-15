## Goal
Fix local main diverging from origin/main after /implement by pushing post-merge larch-log commits and improving divergence warning in local-cleanup.sh

## Implementation Plan

### Goal
Fix the bug where local `main` diverges from `origin/main` after `/implement` runs because
`capture-session-transcript.sh` commits on local `main` via `larch-log.sh commit` (Step 18)
but those commits are never pushed. Also improve the divergence warning in `local-cleanup.sh`.

### Files to change
1. `skills/implement/SKILL.md` — Add best-effort `git push origin main` after the
   `capture-session-transcript.sh` bash block in Step 18, guarded by "on main" + "ahead of
   origin/main" checks. Insert between the "larch-log.sh commit does not push" prose and the
   "Run the consolidated teardown" prose.
2. `scripts/local-cleanup.sh` — When `git pull origin main` fails, check if local main is
   ahead of `origin/main` and emit a specific divergence warning to stderr instead of the
   generic "Failed to pull origin main" message.
3. `scripts/local-cleanup.md` — Document the new divergence warning behavior.

### Approach
- SKILL.md change: single bash block, no new scripts. Guard with
  `git symbolic-ref --short HEAD == "main"` and `git rev-list --count "origin/main..HEAD" > 0`
  so it is a no-op on draft/design-only/non-merge paths and when no transcript was committed.
- local-cleanup.sh change: after failed pull, run
  `git rev-list --count "origin/main..HEAD"`. If non-zero, emit the specific divergence message.
  Preserve `exit 0` and `CLEANUP_SUCCESS=false` semantics (non-fatal).
- local-cleanup.md: add one sentence/paragraph describing the stderr warn-on-divergence behavior.


## Test plan
Run `/relevant-checks` (pre-commit + agent-lint) after the changes.
