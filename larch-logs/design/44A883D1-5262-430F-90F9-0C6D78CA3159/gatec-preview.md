## Final Design Plan

## Plan

### UPDATED: python/larch/core/config.py
- Keep `CODEX_DEFAULT_MODEL` at `gpt-5.6-sol`.
- Route TRIVIAL coders Cursor → Codex → Claude, with Cursor `grok-4.5`; set MODERATE and HARD Codex implement mappings explicitly to `gpt-5.6-terra`.
- Set MODERATE and HARD Codex review-panel mappings to `gpt-5.6-terra`; retain the TRIVIAL luna fallback.
- Remove the plan-review role overrides so static plan-review Codex rows use `review`.
- Remove `architectural-compliance` from `_CODE_REVIEW_ARCHETYPES`; retain a stable `three specialists per vendor` topology-anchor comment because this file remains the authority for the topology row.

### UPDATED: python/larch/calibration/difficulty.py
- Simplify HARD archetype role resolution after override removal so static plan-review archetypes resolve to `review`.

### UPDATED: python/larch/review/plan_review_panel.py
- Launch static Codex plan-review rows with `--model-role review` and pass the tier-resolved review-panel model through `--default-model`.
- Assert the dispatched waterfall arguments preserve terra for MODERATE and HARD rather than falling back to the review-role luna default.

### UPDATED: python/larch/review/review_pipeline_shared.py
- Reduce `STATIC_REVIEWERS` to correctness, edge-cases, and testing so manifests and coverage gates require three static reviewers.

### UPDATED: python/larch/design/plan_scout.py
- Remove the retired architectural-compliance names from reserved review archetypes.
- Update scout prompt text to list only the three active static reviewers.

### UPDATED: python/larch/rendering/rendering.py
- Remove the retired reviewer-specific architectural-knowledge rendering path and its cache-key behavior.

### REWRITTEN: agents/reviewer-architectural-compliance.md
- Delete the retired specialist definition.

### REWRITTEN: agents/pre-rendered/reviewer-architectural-compliance-body.txt
- Delete the retired pre-rendered specialist body.

### UPDATED: agents/pre-rendered/.manifest
- Remove the deleted specialist body checksum.

### UPDATED: python/skill-closure-baseline.json
- Remove the deleted specialist agent from the closure baseline.

### UPDATED: python/review_test_support.py
- Update review harness fixtures, expected outputs, and missing-static-reviewer variants for the three-specialist panel.

### UPDATED: python/tests/core/test_config.py
- Assert the explicit terra MODERATE/HARD implement mappings, TRIVIAL Cursor-first order, and `grok-4.5` Cursor model.

### UPDATED: python/tests/core/test_external_role_defaults.py
- Assert an empty plan-review role-override map and three-specialist review-panel topology.

### UPDATED: python/tests/calibration/test_difficulty.py
- Update HARD plan-review role expectations so every static archetype resolves to `review`.

### UPDATED: python/tests/implement/test_implement_dispatch.py
- Update MODERATE/HARD Codex implement-model, TRIVIAL ordering, and TRIVIAL Cursor-model assertions.

### UPDATED: python/tests/review/test_review_pipeline.py
- Replace four-specialist manifest and coverage-gate expectations with correctness, edge-cases, and testing only.
- Remove architectural-compliance dispatch, manifest, and missing-coverage scenarios.

### UPDATED: python/tests/review/test_plan_review_panel.py
- Assert all HARD static Codex rows use `review`, and verify the waterfall receives both `--model-role review` and tier-specific `--default-model gpt-5.6-terra`.

### UPDATED: python/tests/rendering/test_rendering.py
- Remove retired architectural-compliance rendering and cache tests; retain coverage that ordinary specialists do not receive architectural knowledge.

### UPDATED: python/tests/design/test_plan_scout.py
- Update reserved-name and generated-prompt expectations after architectural-compliance is no longer static or reserved.

### UPDATED: python/tests/skills/_structure_review_specialized.py
- Remove the deleted specialist from required-agent structural checks.

### MAY_UPDATE: python/larch/review/review_core_body.py
- No production edit expected. Verify its manifest-derived coverage behavior now requires the three remaining static reviewers.

## Approach
Retire architectural-compliance from the shared static review topology, including its agent, pre-rendered body, rendering branch, scout reservation, baseline, fixtures, and coverage expectations. Keep the topology authority in `config.py` and preserve its exact `three specialists per vendor` anchor.

Apply tier-specific model routing without changing the global Codex default. Plan-review rows must carry both the `review` role and the tier-resolved `--default-model`, ensuring MODERATE and HARD launches use terra.

## Edge cases
- TRIVIAL review routing remains Cursor single when available, otherwise Codex luna single.
- Generic model-less launches and historical token rows continue to use sol.
- Dynamic scouts may propose architectural focus when justified; it is no longer blocked as a retired static archetype.
- Coverage gates require only correctness, edge-cases, and testing.

## Failure modes
1. A stale topology authority still says four specialists. Earliest signal: topology validation cannot find `three specialists per vendor`. Mitigation: retain the exact anchor in `config.py`.
2. A review-role launch falls back to luna. Earliest signal: waterfall arguments lack the tier-specific `--default-model`. Mitigation: pass and test the resolved panel model.
3. A deleted reviewer remains referenced. Earliest signal: rendering, closure, structural, or review-pipeline tests fail. Mitigation: remove all named runtime, fixture, and baseline references together.

## Testing strategy
- Run applicable Python linters and targeted pytest:
  `pytest python/tests/core/test_config.py python/tests/core/test_external_role_defaults.py python/tests/calibration/test_difficulty.py python/tests/implement/test_implement_dispatch.py python/tests/review/test_review_pipeline.py python/tests/review/test_plan_review_panel.py python/tests/rendering/test_rendering.py python/tests/design/test_plan_scout.py python/tests/skills/_structure_review_specialized.py`.
- Run `python3 python/cli.py generate check` and agent-lint.
- Verify MODERATE and HARD plan-review waterfall arguments include `--model-role review` and `--default-model gpt-5.6-terra`.

difficulty: MODERATE
diff_added: 90
diff_deleted: 510
oversize_override: operator
diff_lines: 600
