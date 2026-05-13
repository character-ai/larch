## Goal
Add NEVER #12 to skills/implement/SKILL.md guarding against the orchestrator ending its turn after /design returns because MANIFEST_WRITTEN=<path> looks terminal.

## Implementation Plan
Five surgical text edits to skills/implement/SKILL.md:
1. Add NEVER #12 after NEVER #11 — describe the deceptive MANIFEST_WRITTEN= signal
2. Update Anti-halt continuation reminder with Critical boundary sentence citing NEVER #12
3. Change "NEVER #7-family violation" → "NEVER #12 violation" in the Post-/design boundary checkpoint
4. Change "→ NEVER #7" → "→ NEVER #12" in the same section
5. Change "See NEVER #7" → "See NEVER #7; NEVER #12" in the post-/design legal next-actions matrix

## Test plan
Run /relevant-checks after the edits. Verify test-implement-structure.sh assertions still pass.
