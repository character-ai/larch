## Goal
Remove generic Claude reviewer from hard panel, reducing 13-reviewer panel to 12 reviewers

## Implementation Plan

Goal: Remove the generic Claude reviewer from the hard reviewer panel, reducing it from 13 to 12 reviewers. The Claude generic should remain in the simple panel and in the both-down fallback path.

### Files to modify

1. **skills/review/scripts/dispatch-panel.sh** (main logic)
   - In the `else` branch (normal mode, at least one external tool available):
   - Move `launch_claude_slot "generic"` inside an `if [[ "$PANEL" != "hard" ]]` guard
   - The `both-down` path is unchanged (still launches claude generic as the sole reviewer)

2. **skills/review/scripts/test-dispatch-panel.sh** (test)
   - Hard panel test: change `SLOT_COUNT=13` → `SLOT_COUNT=12`
   - Add assertion that `claude-generic-output.txt.done` does NOT exist for the hard panel

3. **skills/review/scripts/dispatch-panel.md** (contract doc)
   - Update: "The Claude generic slot always runs through scripts/launch-claude-subprocess.sh" → clarify it only runs in both-down path and simple panels, not hard panels in normal mode

4. **skills/implement/SKILL.md** (two locations)
   - Line 132 (--hard flag): "13-reviewer /review panel" → "12-reviewer /review panel"
   - Line 1494 (Step 5 Normal Mode): "13-reviewer panel (6 Cursor specialists + 6 Codex specialists + 1 Claude generic" → "12-reviewer panel (6 Cursor specialists + 6 Codex specialists"

5. **skills/fix-issue/SKILL.md**
   - "13-reviewer /review panel" → "12-reviewer /review panel"

6. **skills/shared/voting-protocol.md** (two locations)
   - Line 31: remove `Claude-Generic` from hard panel attribution labels, update "13-reviewer panel" → "12-reviewer panel"
   - Line 213: remove `Claude-Generic` from the reviewer example list

### Testing strategy
- Run the dispatch-panel test harness: `bash skills/review/scripts/test-dispatch-panel.sh`
- Run /relevant-checks after edits

## Test plan
(no test plan section in plan-file)
