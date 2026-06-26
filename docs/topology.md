# Topology Projection

<!-- AUTO-GENERATED: Derived from skills/shared/topology.tsv. Do not edit. Regenerate via: python3 python/cli.py generate topology-docs -->

This document is a consumer-doc projection of runtime authorities. The runtime authority listed for each row remains the source of truth; the projection exists so consumer docs can link to stable row anchors instead of repeating drift-prone counts.

`/implement` Step 5 public phrases are pinned by `scripts/test-quick-mode-docs-sync.sh`; the review-panel shape is also projected here from `skills/shared/topology.tsv` so the topology row and public-doc harness stay aligned.

| Key | Value | Composition | Runtime Authority |
|---|---:|---|---|
| <a id="design.plan_review.cursor_archetypes"></a>`design.plan_review.cursor_archetypes` | Cursor | Architecture/Standards Innovation/Exploration Pragmatism/Safety Requirements/Completeness | `skills/design/references/plan-review.md` |
| <a id="design.plan_review.codex_archetypes"></a>`design.plan_review.codex_archetypes` | Codex | Architecture/Standards Innovation/Exploration Pragmatism/Safety Requirements/Completeness | `skills/design/references/plan-review.md` |
| <a id="design.plan_review.dynamic_archetypes"></a>`design.plan_review.dynamic_archetypes` | up to 3 | scout proposes specialists fanned into Cursor+Codex dyn slots | `python/plan_scout.py` |
| <a id="design.plan_review.panel_slots"></a>`design.plan_review.panel_slots` | round gated static plus dynamic | NDJSON manifest from python/cli.py plan-review panel-dispatch via paths-file sidecar | `python/plan_review_panel.py` |
| <a id="design.decompose.panel_slots"></a>`design.decompose.panel_slots` | 8 fixed | 4 archetypes x 2 vendors via python/cli.py | `skills/design/references/decompose-panel.md` |
| <a id="design.decompose.dispatch"></a>`design.decompose.dispatch` | python/cli.py | renders prompts + agent dispatch-waterfall | `python/cli.py` |
| <a id="design.decompose.aggregator"></a>`design.decompose.aggregator` | python/cli.py | single-slot merge of panel proposals | `python/cli.py` |
| <a id="design.decompose.file_issues"></a>`design.decompose.file_issues` | python/cli.py | prepare annotate close-original | `python/cli.py` |
| <a id="design.decompose.harness_panel"></a>`design.decompose.harness_panel` | cli.py | offline panel regression coverage | `python/cli.py` |
| <a id="design.decompose.harness_agg"></a>`design.decompose.harness_agg` | cli.py | offline aggregator merge coverage | `python/cli.py` |
| <a id="design.decompose.harness_file"></a>`design.decompose.harness_file` | cli.py | offline prepare annotate close-original coverage | `python/cli.py` |
| <a id="design.plan.preview_emit"></a>`design.plan.preview_emit` | Step 3 plan-candidate preview | Gate C final-plan preview | `python/plan_review.py` |
| <a id="design.plan_commands.validate"></a>`design.plan_commands.validate` | Tier2+opt-in Tier3 | plan fenced bash/sh | `python/plan_quality.py` |
| <a id="implement.conflict_review.panel"></a>`implement.conflict_review.panel` | 3-reviewer | Claude Code Reviewer subagent + Codex + Cursor | `skills/implement/references/conflict-resolution.md` |
| <a id="implement.conflict_review.rounds_max"></a>`implement.conflict_review.rounds_max` | 2 total | resolution-review rounds | `skills/implement/references/conflict-resolution.md` |
| <a id="research.lanes"></a>`research.lanes` | four research lanes | architecture + edge cases + external comparisons + security | `skills/research/references/research-phase.md` |
| <a id="research.validation_panel"></a>`research.validation_panel` | 3 reviewer lanes | Claude Code Reviewer subagent + Codex + Cursor | `skills/research/references/validation-phase.md` |
| <a id="implement.review_and_fix.panel_hard"></a>`implement.review_and_fix.panel_hard` | specialists per vendor | Cursor + Codex | `python/review_pipeline.py` |
| <a id="deps.issue_audit"></a>`deps.issue_audit` | one approval gate | open-issue grouping + REGULAR refresh + explicit and latent dependency audit | `skills/deps/SKILL.md` |
| <a id="runtime.residual_bash.inventory"></a>`runtime.residual_bash.inventory` | residual-bash | hooks linters thin wrappers sleep helper G-track delegation fences and residual harnesses | `python/cli.py` |
| <a id="runtime.pr_closes_issue"></a>`runtime.pr_closes_issue` | closes-issue | PR-body Closes issue extraction authority | `python/larch/git/pr.py` |
