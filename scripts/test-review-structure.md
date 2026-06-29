# scripts/test-review-structure.sh — contract

Assertion 1 pins nine registered `review` CLI verbs in `python/cli.py` (`gather-context`, `core`, `dispatch-panel`, `collect-findings`, `tally-code-votes`, `emit-tally`, `log-phase`, `check-reviewer-failure-threshold`, `reviewer-prune`), asserts the `python/larch/review/review_collect.py` collect/findings and `python/larch/review/review_prune.py` pruning contract pins, and maps those verbs to pytest-backed harnesses (`python/test_review_pipeline.py`, `python/test_review_aggregate.py`, `python/test_review_tally.py`, `python/test_compose_review.py`). It also asserts that `skills/review-and-fix/SKILL.md`, `review-and-fix CLI`, the `python/cli.py redact scrub-submodule-paths` registry entry, and the Codex/Cursor dispatch literals exist. The same assertion fails if `review-and-fix CLI` still references `launch-claude-subprocess.sh`, because coder dispatch is Codex then Cursor only.

Assertions 1c/1d verify the hand-maintained orchestration aggregator is named `agents/orchestrator-aggregator.md`, carries the `HAND-MAINTAINED` annotation, and does not regress to the generated-reviewer `reviewer-*` namespace. They also assert that `agents/reviewer-aggregator.md`, `agents/orchestrator-judge.md`, and `skills/review/references/voting.md` do not exist.

Assertion 20 pins both halves of the security OOS boundary in `skills/shared/voting-protocol.md` and `python/voting.py`: shared voting prose says security-tagged findings are held locally and never filed publicly, and the voting module documents the canonical `focus-area\s*=\s*security` token match.

Wired into `make lint` via the `test-review-structure` target. Update this contract with the harness whenever adding or renumbering assertions.
