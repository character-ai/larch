## Proposed Design Outline

### Goals
- Route MODERATE Step 2 Cursor launches to grok-4.5; keep TRIVIAL/HARD at composer-2.5.
- Respect `LARCH_CURSOR_MODEL` and `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL` overrides at every tier.
- Cover all acceptance criteria with tests in the three firm test files.

### Non-goals
- Change the Step 2 vendor order waterfall (Piece 1, #6838).
- Modify non-Step-2 Cursor defaults (CI fixer, plan revision, review).
- Touch Codex model selection.

### Approach sketch
- Add `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` dict to `config.py` (TRIVIAL/HARD=composer-2.5, MODERATE=grok-4.5).
- Update `dispatch_step2._resolve_implement_rater_model` to use `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY.get(difficulty_tier, CURSOR_DEFAULT_MODEL)` as the cursor default.
- Update `_launch_failure.resolve_model_args` to forward `default_model` for the cursor branch instead of hard-coding `CURSOR_DEFAULT_MODEL`.
- Update `_ci_launcher.launch_cursor_implement_main` to look up the tier-specific model from `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` before calling `resolve_model_args`.
- Add `test_config.py` assertion for `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` shape.
- Extend `test_implement_dispatch.py` routing matrix with TRIVIAL/HARD cursor cases.

### Surfaces in scope
- `python/larch/core/config.py` (CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY only)
- `python/larch/implement/dispatch_step2.py`
- `python/larch/agents/_launch_failure.py`
- `python/larch/agents/_ci_launcher.py`
- `python/tests/core/test_config.py`
- `python/tests/implement/test_implement_dispatch.py`
- `python/tests/agents/test_agents.py`

### Open questions
- None.
