## Goal
Remove 'unified hard panel' and 'hard review panel' terminology from /implement Step 5 breadcrumb and enforcement

## Implementation Plan

Remove "unified hard panel" and "hard review panel" terminology from the /implement Step 5 breadcrumb and all enforcement machinery.

### Files to modify

1. **scripts/test-quick-mode-docs-sync.sh** (POS_MARKERS):
   - Remove `"unified hard panel|insensitive"` entry (line 85)
   - Remove `"hard review panel|insensitive"` entry (line 89)
   - Update header comment (line 5-6) that says "unified hard-panel contract"

2. **scripts/test-quick-mode-docs-sync.md** (sibling contract):
   - Remove `unified hard panel` row from positive anchors table
   - Remove `hard review panel` row from positive anchors table
   - Update "unified hard-panel contract" prose references

3. **skills/implement/SKILL.md**:
   - Line ~1369: Change breadcrumb from `unified hard panel (review-and-fix.sh, ...; hard review panel: 6 Cursor specialists; ...)` to `review-and-fix.sh, ...; review panel: 6 Cursor specialists; ...`
   - Line ~1416: Remove `(unified hard panel)` parenthetical from write-tally.sh comment

4. **README.md** (line ~85):
   - Remove `(unified hard panel)` parenthetical
   - Change `hard review panel` to `review panel`

5. **docs/review-agents.md** (line ~102, Note A):
   - Remove `(unified hard panel)` parenthetical
   - Change `hard review panel` to `review panel`

6. **docs/workflow-lifecycle.md** (line ~34):
   - Remove `unified hard panel:` prefix in the review section
   - Change `hard review panel` to `review panel`

7. **docs/skills.md** (line ~95):
   - Remove `(unified hard panel)` parenthetical
   - Change `hard review panel` to `review panel`

8. **docs/linting.md**:
   - Update description of make test-quick-mode-docs-sync that mentions "unified hard panel"

9. **docs/topology.md**:
   - Update the exclusion note that lists "unified hard panel" and "hard review panel"

10. **scripts/generate-topology-docs.sh** and **scripts/generate-topology-docs.md**:
    - Same exclusion note update

### Approach
All changes are mechanical text replacements. The edit-in-sync rule from test-quick-mode-docs-sync.sh says: update POS_MARKERS first, then .md sibling, then public docs.

Key constraint: The self-test fixtures in test-quick-mode-docs-sync.sh still contain "Unified hard panel" and "hard review panel" — these are fine to keep since the test asserts: (1) good fixture passes, (2) bad fixture fails exactly once (from stale phrase). Both invariants hold after removing these 2 markers from POS_MARKERS since the remaining 4 markers are still in the fixtures.


## Test plan
Run: `make test-quick-mode-docs-sync`
Also run: `grep -r "unified hard panel\|hard review panel" skills/implement/SKILL.md README.md docs/review-agents.md docs/workflow-lifecycle.md docs/skills.md` should return no matches (except inside the self-test fixtures in test-quick-mode-docs-sync.sh).
