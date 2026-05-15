## Goal
Move post-merge larch-log push into capture-session-transcript.sh so push is script-backed and always runs

## Implementation Plan
## Goal
Move the post-merge git push from SKILL.md Step 18 prose into capture-session-transcript.sh.

## Files to modify
1. scripts/capture-session-transcript.sh — add best-effort push after larch-log.sh commit
2. skills/implement/SKILL.md — remove push prose+block from Step 18
3. scripts/capture-session-transcript.md — add push note, update Edit-in-sync

## Approach
Add after larch-log.sh commit succeeds (before emit_status captured):
  current_branch=$(git symbolic-ref --short HEAD 2>/dev/null || true)
  if [ "$current_branch" = "main" ]; then
      ahead=$(git rev-list --count "origin/main..HEAD" 2>/dev/null || echo 0)
      if [ "${ahead:-0}" -gt 0 ]; then
          git push origin main >/dev/null 2>&1 || true
      fi
  fi

Remove SKILL.md lines: "Push any post-merge run-log commit..." intro + bash block.

## Edge cases
- Push failure: non-fatal (|| true), script still emits captured
- Not on main: push block is skipped
- Nothing ahead: push block is skipped
- set -euo pipefail: || true on push; || echo 0 on rev-list ensure no premature exit


## Test plan
Run /relevant-checks; verify test-capture-session-transcript.sh passes
