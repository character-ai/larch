## Proposed Design Outline

### Goals
- Fix `_run_relevant_checks_for_site` to pass `--allow-skip`, stopping spurious `STATUS=fail` when checks legitimately skip on composite sites.
- Add `_REBASE_CHECKPOINT_DEADLINE_MS` to give the folded 7.r rebase its own outer-timeout budget, eliminating the 5-minute slack risk.
- Add per-consumer runtime tests for external-role dispatch sites and correct stale voter-composition prose in `voting-protocol.md`.

### Non-goals
- Changing skip semantics inside `checks.py` or `run_relevant_checks`.
- Refactoring the composite dispatch model beyond the targeted timeout constant.
- Addressing the companion voter auto-OOS capture issue (separate tracking issue).

### Approach sketch
- `python/implement_dispatch.py`: add `"--allow-skip"` to the `checks run-relevant` argv in `_run_relevant_checks_for_site`; add `_REBASE_CHECKPOINT_DEADLINE_MS` (e.g. 900 000 ms) and fold it into `CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS` only.
- `python/test_implement_dispatch.py`: add skip→continue tests for both composite mains; add timeout-budget constant assertion.
- New `python/test_external_dispatch.py` (or extend existing per-consumer test files): add per-consumer tests exercising `tool_order`/`slot_defaults`/`voter_policies` at each named dispatch site (bootstrap, rebase, checks/lint_fix, plan_scout, review_and_fix, ci_monitor, review_pipeline, agent_voters, review_aggregate, decompose); add cross-role mutation guard.
- `skills/shared/voting-protocol.md`: replace "three Cursor archetype voters" prose, "Codex does not vote" sentences, and per-slot v2/v3 labels to match `codex-plan-fidelity` / `codex-pragmatism`.

### Surfaces in scope
- `python/implement_dispatch.py`
- `python/test_implement_dispatch.py`
- New `python/test_external_dispatch.py` (or relevant existing test files)
- `skills/shared/voting-protocol.md`

### Open questions
- None.
