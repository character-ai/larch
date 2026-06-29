## Goal
Implement issue #5843: [IMPLEMENTING] [BUG] Round IX softened "Never use em dashes" to "Avoid" in AGENTS.md.

## Implementation Plan
**Severity**: Low (no live consequence today).

**What**: #5785's Tier-1a prose trim (PR #5832) changed an `AGENTS.md` Output Style rule from a hard prohibition to a soft one, and dropped its guidance.

- **Before**: *"Never use em dashes. Use periods, commas, colons, or semicolons instead."*
- **After** (`AGENTS.md`, folded into a list): *"...Avoid walls of prose, em dashes, over-hedging, and passive filler."*

**Consequence**: a modality flip (Never to Avoid) on a style rule the project otherwise enforces, plus loss of the explicit alternative-punctuation guidance. No live breakage today (0 em dashes currently present), but it weakens a contract-adjacent rule.

**Fix**: restore the hard "Never use em dashes" (and its alternative-punctuation guidance), or confirm the softening was intentional.

**Origin**: PR #5832 (#5785), umbrella #5788.

## Test plan
(no test plan section in plan-file)
