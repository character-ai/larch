## Goal
Prevent stray larch-log commits to main after merge by exporting IMPLEMENT_TMPDIR and adding branch-name guards

## Implementation Plan

### Problem
After `/implement --merge` merges a PR, `capture-session-transcript.sh` (called in Step 18) has a post-merge sentinel guard that relies on `IMPLEMENT_TMPDIR` being in the subprocess environment. But the Step 18 Bash block that calls it omits `export IMPLEMENT_TMPDIR`, so the guard never fires and a stray `chore(larch-logs)` commit lands on local `main`.

### Fix 1 — Primary (skills/implement/SKILL.md)

In the Step 18 Bash block for `capture-session-transcript.sh` (around lines 1887-1901), prepend:
```
IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"
export IMPLEMENT_TMPDIR
```
This matches the pattern used by every other Step 18 Bash block.

### Fix 2 — Defense-in-depth (scripts/larch-log.sh commit)

After the existing post-merge sentinel guard (line 305), add a branch-name guard:
- Get current branch via `git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD`
- Get default branch via `git -C "$REPO_ROOT" symbolic-ref refs/remotes/origin/HEAD | sed 's|.*/||'`
- If current == "main" or current == default: print stderr diagnostic and exit 1

This catches any future case where `IMPLEMENT_TMPDIR` is missing from the environment for any reason.

### Fix 3 — Defense-in-depth (scripts/capture-session-transcript.sh)

After the post-merge sentinel check (line 149), add a similar branch-name guard that calls `emit_status "suppressed-default-branch"` when the current branch is main/default. This gives a specific, traceable status in the Warnings log (rather than the generic `commit-failed`).

### Fix 4 — Docs (scripts/capture-session-transcript.md, scripts/larch-log.md)

Update both sibling `.md` files to document the new guards.


## Test plan
- `/relevant-checks` must pass
- The three changed files must have the new guards
