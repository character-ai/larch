## Proposed Design Outline

### Goals
- Cut over Step 8 `ci-fix` from the Agent-tool fixer to the existing dormant bgjob lane `step-8-ci-fixer.sh`.
- Remove the Step 8 inline-fallback leaks: the post-bail 10-attempt main-agent loop and `fallback-attempts.count` routing.
- Keep `LARCH_CI_FIXER=0` as the sole sanctioned inline path with its existing 30-attempt budget.

### Non-goals
- Do not touch the Step 3/5/6 checks repair-loop or its `main-agent-edit` leak. That is a sibling piece.
- Do not resize the checks external-lane budget in `checks_lint_fix.py`. That is a sibling piece.
- Do not change the bgjob lane internals, `ci fixer-lane`, or the `ci_recovery_fixer` role. Piece 3 already landed them.

### Approach sketch
- Rewrite `ship-pr-ci-fix.md` so the default fixer path invokes `step-8-ci-fixer.sh` through the Step 8 bgjob start/wait pair and consumes the compact `RESULT` envelope.
- Delete the Agent-tool spawn section and the post-bail inline 10-attempt loop plus `fallback-attempts.count` from `ship-pr-ci-fix.md` and from Step 8 in `skills/implement/SKILL.md`.
- Surface `ci-fix-exhausted` on full waterfall exhaustion. Preserve the `LARCH_CI_FIXER=0` inline path verbatim.
- Remove `CI_FIXER_MAIN_FALLBACK_MAX_ATTEMPTS` and any Agent-only constant from `python/larch/core/config.py` once their consumers are gone. Keep the kill-switch 30-attempt constant.
- Update Step 8 tests and the fence-shape harness to assert the bgjob lane is the default and the removed paths are gone.

### Surfaces in scope
- skills/implement/references/ship-pr-ci-fix.md
- skills/implement/SKILL.md (Step 8 plus the architectural-invariants branch)
- scripts/test-implement-fence-shape.sh
- scripts/test-implement-step8-exit3-first-fixer.sh
- scripts/test-implement-structure.sh
- skills/implement/scripts/test-architectural-guidelines-step.sh
- python/tests/implement/test_implement_dispatch.py
- docs/configuration-and-permissions.md
- python/larch/core/config.py
- python/tests/core/test_config.py

### Open questions
- None.
