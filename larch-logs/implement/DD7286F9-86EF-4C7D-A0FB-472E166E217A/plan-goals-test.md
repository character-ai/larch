## Implementation Plan

**Goal**: Remove Claude generic reviewer from all review panels. Claude should never be used for code reviews.

**Changes** (all mechanical removals following a clear pattern):

1. skills/review/scripts/dispatch-panel.sh
   - Delete both-down fallback: remove `launch_claude_slot "generic"` call + update comment
   - Delete simple-panel Claude generic block: remove `if [[ "$PANEL" != "hard" ]]; then ... fi`
   - Both-down path keeps `panel_mode="both-down"` but dispatches 0 slots

2. skills/review/scripts/test-dispatch-panel.sh
   - Both-down test: SLOT_COUNT=1 → SLOT_COUNT=0, negative assertion for claude-generic file
   - Simple panel (no plan): SLOT_COUNT=3 → SLOT_COUNT=2, add negative assertion
   - Simple panel (with plan): SLOT_COUNT=5 → SLOT_COUNT=4, add negative assertion

3. scripts/test-quick-mode-docs-sync.sh (CRITICAL — byte-pins "Claude generic")
   - Remove "Claude generic|sensitive" from POS_MARKERS
   - Update self-test $good fixture to remove "Claude generic"

4. skills/review/scripts/dispatch-panel.md — update description
5. skills/review/scripts/test-dispatch-panel.md — update contract bullets
6. skills/implement/SKILL.md line 1375 — remove "Claude generic" from quick-mode breadcrumb

7. README.md — update --quick description
8. docs/workflow-lifecycle.md — update --quick row, fallback chain
9. docs/review-agents.md — update panel table, fallback chains
10. docs/skills.md — update --quick description
11. docs/voting-process.md — update Claude generic slot reference
12. docs/collaborative-sketches.md — update fallback chain
13. docs/topology.md — update byte-pinned phrase note

**Verification**: bash scripts/test-quick-mode-docs-sync.sh && bash skills/review/scripts/test-dispatch-panel.sh
