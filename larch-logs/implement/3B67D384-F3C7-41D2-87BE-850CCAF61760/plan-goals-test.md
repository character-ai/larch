## Goal
Expand the /design Step 3 plan-review panel from 4 reviewers to 10 (5 personalities × Cursor + Codex) by adding a Requirements/Completeness archetype.

## Implementation Plan
Add `requirements` case to render-plan-review-prompt.sh; add 5 new Cursor and 5 new Codex launch blocks in SKILL.md (expanding from 2+2 diagonal to 5+5 full-cross); update plan-review.md panel contract and attribution guidance; extend test harness; update timing kinds allow-list and topology.

## Test plan
- bash skills/design/scripts/test-plan-review-prompt.sh verifies all 5 archetypes × 2 vendors produce correct output
- /relevant-checks verifies CI compliance
