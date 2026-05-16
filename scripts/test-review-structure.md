# scripts/test-review-structure.sh — contract

Assertion 1 now expects eight `/review` scripts, including `review-core`, and verifies each has a sibling contract and harness. It also asserts that `skills/review-and-fix/SKILL.md`, `review-and-fix.sh`, and `call-fixer.sh` exist.

Assertions 1c/1d verify the hand-maintained orchestration agents are named `agents/orchestrator-aggregator.md` and `agents/orchestrator-judge.md`, carry the `HAND-MAINTAINED` annotation, and do not regress to the generated-reviewer `reviewer-*` namespace.

Assertion 20 pins both halves of the security OOS boundary in `references/voting.md`: diff mode excludes security-tagged findings from `oos-accepted-review.md` using the canonical `focus-area\s*=\s*security` token match, and the existing description-mode guard remains present.

Wired into `make lint` via the `test-review-structure` target. Update this contract with the harness whenever adding or renumbering assertions.
