## Goal

Restructure the review panel to reduce token cost: HARD path moves to 11 reviewers (5 Cursor + 5 Codex specialists + 1 Claude generic) with a 3-round cap; SIMPLE path moves to 6 reviewers (5 Cursor specialists + 1 Codex generic) with a 3-round cap; both paths adopt tighter convergence thresholds.

## Implementation Plan

Changes:
1. skills/review/SKILL.md — expand HARD panel to 11 reviewers, remove rounds 4-7, tighten convergence thresholds, remove --full flag
2. skills/implement/SKILL.md — SIMPLE path: drop Claude generic, 6 reviewers, remove rounds 4-7, tighten thresholds
3. skills/review/references/heavy-worker.md — mirror round-state changes
4. skills/review/references/voting.md — update player count, remove rounds 4+ references
5. scripts/lib-timing-kinds.sh — add 5 codex-specialist-* slugs
6. scripts/test-quick-mode-docs-sync.sh — update POS_MARKERS for new quick-mode contract
7. scripts/test-quick-mode-docs-sync.md — update sibling docs
8. README.md, docs/workflow-lifecycle.md, docs/skills.md, docs/review-agents.md — update --quick description

## Test plan

- Run /relevant-checks (pre-commit + agent-lint)
- scripts/test-quick-mode-docs-sync.sh validates docs-SKILL.md sync
- scripts/test-implement-structure.sh assertion 28g validates new codex-specialist-* timing slugs
