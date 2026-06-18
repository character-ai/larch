## Proposed Design Outline

### Goals
- Prevent recurrence of the three issue #4712 gaps with the smallest change per gap.
- Cut the cost of #1/#2: prevent at source, and let CI self-heal instead of escalating to Main Claude.
- Stop uncommitted review-loop fixes from stalling the ship driver.

### Non-goals
- Not loosening the allow-list or partition guards; keep their anti-sprawl / strict-partition intent.
- Not running heavy harnesses (`test-harnesses`, `pytest --co`) locally pre-ship.
- Not changing CI parallelization or shard layout.

### Approach sketch
- #1 prevent: add an implementer-prompt checklist line for the legacy-prefix `ALLOW=` contract.
- #1 fast-lane: add the git-grep allow-list check to the local fast lane (`.pre-commit-config.yaml`); it is sub-second and repo-global.
- #1+#2 self-heal: teach `python/ci_agentic_fix.py` to recognize and mechanically fix the two known CI failure signatures.
- #2 prevent: add an implementer-prompt checklist line for the `-k` strict-partition contract.
- #3: make the review/fix loop commit its working-tree changes before the ship handoff.

### Surfaces in scope
- `agents/codex-implementer.md`, `agents/cursor-implementer.md` (or a shared implementer checklist surface) — prevent-at-source notes.
- `.pre-commit-config.yaml` + `scripts/test-legacy-title-prefix-literals-scope.sh` — fast-lane.
- `python/ci_agentic_fix.py` — self-heal signatures.
- Review/fix-loop commit point vs. ship dirty-tree check (`python/review_and_fix.py` / ship driver / `skills/implement/SKILL.md`) — #3.

### Open questions
- #3 exact locus: confirm where review-loop fixes are applied vs. where ship checks the dirty tree, then place the commit there.
- Self-heal breadth: target only these two signatures (recommended) vs. a more general CI-fix capability.
