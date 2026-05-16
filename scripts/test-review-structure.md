# scripts/test-review-structure.sh — contract

Assertion 1 now expects nine `/review` scripts, including `review-core`, and verifies each has a sibling contract and harness. It also asserts that `skills/review-and-fix/SKILL.md`, `review-and-fix.sh`, executable `scripts/scrub-submodule-paths.sh`, and the Codex/Cursor dispatch literals exist. The same assertion fails if `review-and-fix.sh` still references `launch-claude-subprocess.sh`, because coder dispatch is Codex then Cursor only.

Assertions 1c/1d verify the hand-maintained orchestration aggregator is named `agents/orchestrator-aggregator.md`, carries the `HAND-MAINTAINED` annotation, and does not regress to the generated-reviewer `reviewer-*` namespace. They also assert that `agents/reviewer-aggregator.md`, `agents/orchestrator-judge.md`, and `skills/review/references/voting.md` do not exist.

Assertion 20 pins both halves of the security OOS boundary in `skills/shared/voting-protocol.md` and `scripts/lib-vote-tally.md`: shared voting prose says security-tagged findings are held locally and never filed publicly, and the tally library contract documents the canonical `focus-area\s*=\s*security` token match.

Wired into `make lint` via the `test-review-structure` target. Update this contract with the harness whenever adding or renumbering assertions.
