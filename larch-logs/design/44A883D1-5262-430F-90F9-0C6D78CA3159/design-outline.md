## Proposed Design Outline

### Goals
- Refresh per-difficulty vendor/model routing for the /implement coder, /implement Step 5 review panel, and /design plan-review panel.
- Retire the architectural-compliance reviewer slot from /implement Step 5; Step 8 owns architectural compliance.
- Keep all in-scope pytest suites, `generate check`, and agent-lint green.

### Non-goals
- docs/ and skills/ prose sweeps (topology, review-agents, external-reviewers, SKILL.md references); piece 2.
- Step 8 arch-assessment and /design Gate C assessment; unaffected.
- TRIVIAL review-panel behavior and the --no-fallback dispatch contract; unchanged.

### Approach sketch
- Edit model-tier constants in config.py: coder waterfall order, Cursor/Codex implement models, Codex review-panel model, design plan-review model and role overrides.
- Remove architectural-compliance from _CODE_REVIEW_ARCHETYPES and the duplicate STATIC_REVIEWERS; sweep tokens.py and plan_scout.py.
- Delete agents/reviewer-architectural-compliance.md and its pre-rendered body; drop the .manifest, rendering.py special-case, baseline, and structure-test entries.
- Update in-scope tests to the 3-specialist panel and new model tiers; regenerate pre-rendered prompts.

### Surfaces in scope
- config.py, difficulty.py, plan_review_panel.py, review_pipeline_shared.py, plan_scout.py, rendering.py, tokens.py
- agents/reviewer-architectural-compliance.md (delete), agents/pre-rendered/ body and .manifest
- skill-closure-baseline.json, review_test_support.py
- in-scope test suites under python/tests/

### Open questions
- STATIC_REVIEWERS duplicates _CODE_REVIEW_ARCHETYPES (G-Cfg-1); consolidate or update both? Resolve in Step 2b.
- G-Md-2 prose sweep deferred to piece 2 by the partition.
