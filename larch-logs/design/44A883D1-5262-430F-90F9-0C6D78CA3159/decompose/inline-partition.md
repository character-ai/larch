## Pieces

### Piece 1: Config, runtime, and agent-deletion code
- Scope: Model-tier constant edits and architectural-compliance archetype retirement in config.py; STATIC_REVIEWERS in review_pipeline_shared.py; plan_scout prompt; rendering.py special-case removal; tokens.py slot set; .manifest and skill-closure-baseline.json entries after deleting agents/reviewer-architectural-compliance.md and its pre-rendered body. Verify (no edit expected) python/larch/calibration/difficulty.py and python/larch/review/plan_review_panel.py.
- Firm-headings: python/larch/core/config.py, python/larch/review/review_pipeline_shared.py, python/larch/design/plan_scout.py, python/larch/rendering/rendering.py, python/larch/report/tokens.py, agents/pre-rendered/.manifest, python/skill-closure-baseline.json
- Acceptance: python/cli.py generate check passes; agent-lint green; modules import clean.
- Dependencies: none
- Size estimate: ~85 diff lines

### Piece 2: Test and test-support updates for the 3-specialist panel and new model tiers
- Scope: Update pytest suites and test-support to the 3-specialist panel (6 slots), new model tiers, and the removed role override; remove tests rendering the deleted agent file; update the structure test and scout/tokens assertions; update review_test_support.py slot loops. Verify (no edit expected) python/tests/calibration/test_difficulty.py and python/tests/review/test_plan_review_panel.py.
- Firm-headings: python/review_test_support.py, python/tests/skills/_structure_review_specialized.py, python/tests/core/test_config.py, python/tests/core/test_external_role_defaults.py, python/tests/implement/test_implement_dispatch.py, python/tests/review/test_review_pipeline.py, python/tests/rendering/test_rendering.py, python/tests/design/test_plan_scout.py, python/tests/report/test_tokens.py
- Acceptance: all listed pytest suites pass against Piece 1 code.
- Dependencies: blocked-by Piece 1
- Size estimate: ~95 diff lines
