# Topology Projection

<!-- AUTO-GENERATED: Derived from skills/shared/topology.tsv. Do not edit. Regenerate via: bash scripts/generate-topology-docs.sh -->

This document is a consumer-doc projection of runtime authorities. The runtime authority listed for each row remains the source of truth; the projection exists so consumer docs can link to stable row anchors instead of repeating drift-prone counts.

Quick-mode `/implement` reviewer-loop phrases such as `7 rounds`, `rounds 1-3`, `5 Cursor specialists`, and `generic Codex` are intentionally excluded. They are byte-pinned by `scripts/test-quick-mode-docs-sync.sh` and remain owned by that harness's edit-in-sync rule.

| Key | Value | Composition | Runtime Authority |
|---|---:|---|---|
| <a id="design.sketch.regular_slots"></a>`design.sketch.regular_slots` | 8 regular | 4 Cursor + 4 Codex | `skills/design/references/sketch-launch.md` |
| <a id="design.sketch.quick_slots"></a>`design.sketch.quick_slots` | 2 sketch agents | 1 Cursor-Generic + 1 Codex-Generic | `skills/design/references/flags.md` |
| <a id="design.plan_review.cursor_archetypes"></a>`design.plan_review.cursor_archetypes` | 4 Cursor | Architecture/Standards Edge-cases/Failure-modes Innovation/Exploration Pragmatism/Safety | `skills/design/references/plan-review.md` |
| <a id="design.plan_review.codex_archetypes"></a>`design.plan_review.codex_archetypes` | 4 Codex | Architecture/Standards Edge-cases/Failure-modes Innovation/Exploration Pragmatism/Safety | `skills/design/references/plan-review.md` |
| <a id="design.dialectic.judge_panel"></a>`design.dialectic.judge_panel` | 3-judge | Claude Code Reviewer subagent + Codex + Cursor | `skills/shared/dialectic-protocol.md` |
| <a id="design.dialectic.max_decisions"></a>`design.dialectic.max_decisions` | top-5 | selected contested decisions | `skills/shared/dialectic-protocol.md` |
| <a id="implement.conflict_review.panel"></a>`implement.conflict_review.panel` | 3-reviewer | Claude Code Reviewer subagent + Codex + Cursor | `skills/implement/references/conflict-resolution.md` |
| <a id="implement.conflict_review.rounds_max"></a>`implement.conflict_review.rounds_max` | 2 total | resolution-review rounds | `skills/implement/references/conflict-resolution.md` |
| <a id="research.lanes"></a>`research.lanes` | four research lanes | architecture + edge cases + external comparisons + security | `skills/research/references/research-phase.md` |
| <a id="research.validation_panel"></a>`research.validation_panel` | 3 reviewer lanes | Claude Code Reviewer subagent + Codex + Cursor | `skills/research/references/validation-phase.md` |
