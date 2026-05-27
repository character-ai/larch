# Topology Projection

<!-- AUTO-GENERATED: Derived from skills/shared/topology.tsv. Do not edit. Regenerate via: bash scripts/generate-topology-docs.sh -->

This document is a consumer-doc projection of runtime authorities. The runtime authority listed for each row remains the source of truth; the projection exists so consumer docs can link to stable row anchors instead of repeating drift-prone counts.

`/implement` Step 5 phrases pinned by `scripts/test-quick-mode-docs-sync.sh` (for example `5 rounds`, `--panel hard`, `3-judge panel on every round`, and `6 Cursor specialists`) are intentionally excluded from this projection. They remain owned by that harness's edit-in-sync rule.

| Key | Value | Composition | Runtime Authority |
|---|---:|---|---|
| <a id="design.sketch.simple_slots"></a>`design.sketch.simple_slots` | 0 sketch agents | SIMPLE sentinel path | `skills/design/references/sketch-launch.md` |
| <a id="design.sketch.regular_slots"></a>`design.sketch.regular_slots` | 4 regular | 2 Cursor + 2 Codex | `skills/design/references/sketch-launch.md` |
| <a id="design.plan_review.cursor_archetypes"></a>`design.plan_review.cursor_archetypes` | 5 Cursor | Architecture/Standards Edge-cases/Failure-modes Innovation/Exploration Pragmatism/Safety Requirements/Completeness | `skills/design/references/plan-review.md` |
| <a id="design.plan_review.codex_archetypes"></a>`design.plan_review.codex_archetypes` | 5 Codex | Architecture/Standards Edge-cases/Failure-modes Innovation/Exploration Pragmatism/Safety Requirements/Completeness | `skills/design/references/plan-review.md` |
| <a id="design.plan_review.dynamic_archetypes"></a>`design.plan_review.dynamic_archetypes` | up to 6 | scout proposes specialists fanned into Cursor+Codex dyn slots | `skills/design/references/plan-review.md` |
| <a id="design.plan_review.panel_slots"></a>`design.plan_review.panel_slots` | 10 static + up to 12 dynamic | NDJSON manifest from dispatch-plan-review-panel.sh via paths-file sidecar | `skills/design/references/plan-review.md` |
| <a id="design.decompose.panel_slots"></a>`design.decompose.panel_slots` | 8 fixed | 4 archetypes x 2 vendors via decompose-panel-dispatch.sh | `skills/design/references/decompose-panel.md` |
| <a id="design.decompose.dispatch"></a>`design.decompose.dispatch` | decompose-panel-dispatch.sh | renders prompts + dispatch-with-waterfall | `skills/design/scripts/decompose-panel-dispatch.sh` |
| <a id="design.decompose.aggregator"></a>`design.decompose.aggregator` | decompose-aggregator.sh | single-slot merge of eight proposals | `skills/design/scripts/decompose-aggregator.sh` |
| <a id="design.decompose.file_issues"></a>`design.decompose.file_issues` | decompose-file-issues.sh | prepare annotate close-original | `skills/design/scripts/decompose-file-issues.sh` |
| <a id="design.decompose.harness_panel"></a>`design.decompose.harness_panel` | test-decompose-panel-dispatch.sh | offline panel regression harness | `skills/design/scripts/test-decompose-panel-dispatch.sh` |
| <a id="design.decompose.harness_agg"></a>`design.decompose.harness_agg` | test-decompose-aggregator.sh | offline aggregator merge harness | `skills/design/scripts/test-decompose-aggregator.sh` |
| <a id="design.decompose.harness_file"></a>`design.decompose.harness_file` | test-decompose-file-issues.sh | offline prepare annotate close-original harness | `skills/design/scripts/test-decompose-file-issues.sh` |
| <a id="design.plan.preview_emit"></a>`design.plan.preview_emit` | Step 3 plan-candidate preview | Gate C final-plan preview | `skills/design/scripts/emit-design-plan-preview.sh` |
| <a id="design.plan_commands.validate"></a>`design.plan_commands.validate` | Tier2+opt-in Tier3 | plan fenced bash/sh | `skills/design/scripts/validate-plan.sh` |
| <a id="design.dialectic.judge_panel"></a>`design.dialectic.judge_panel` | 3-judge | Claude Code Reviewer subagent + Codex + Cursor | `skills/shared/dialectic-protocol.md` |
| <a id="design.dialectic.max_decisions"></a>`design.dialectic.max_decisions` | top-5 | selected contested decisions | `skills/shared/dialectic-protocol.md` |
| <a id="implement.conflict_review.panel"></a>`implement.conflict_review.panel` | 3-reviewer | Claude Code Reviewer subagent + Codex + Cursor | `skills/implement/references/conflict-resolution.md` |
| <a id="implement.conflict_review.rounds_max"></a>`implement.conflict_review.rounds_max` | 2 total | resolution-review rounds | `skills/implement/references/conflict-resolution.md` |
| <a id="research.lanes"></a>`research.lanes` | four research lanes | architecture + edge cases + external comparisons + security | `skills/research/references/research-phase.md` |
| <a id="research.validation_panel"></a>`research.validation_panel` | 3 reviewer lanes | Claude Code Reviewer subagent + Codex + Cursor | `skills/research/references/validation-phase.md` |
| <a id="implement.review_and_fix.panel_hard"></a>`implement.review_and_fix.panel_hard` | 6 Cursor specialists | Unified hard review panel layout. SIMPLE/HARD differ only in Step 5 workflow-path classification and review-loop policy | `skills/review/scripts/dispatch-panel.sh` |
