# Topology Projection

<!-- AUTO-GENERATED: Derived from skills/shared/topology.tsv. Do not edit. Regenerate via: python3 python/cli.py generate topology-docs -->

This document is a consumer-doc projection of runtime authorities. The runtime authority listed for each row remains the source of truth; the projection exists so consumer docs can link to stable row anchors instead of repeating drift-prone counts.

`/implement` Step 5 public phrases are pinned by `scripts/test-quick-mode-docs-sync.sh`; the review-panel shape is also projected here from `skills/shared/topology.tsv` so the topology row and public-doc harness stay aligned.

| Key | Value | Composition | Runtime Authority |
|---|---:|---|---|
| <a id="debate.panel"></a>`debate.panel` | debate.panel | persistent Cursor subprocess + Codex subprocess + Claude Agent session | `python/larch/debate/orchestrator.py` |
| <a id="debate.rounds"></a>`debate.rounds` | two-round debate protocol | blind position round + validated mailbox negotiation round | `python/larch/debate/orchestrator.py` |
| <a id="debate.adjudication"></a>`debate.adjudication` | AskUserQuestion | default operator decisions or autonomous anonymized voter panel | `skills/debate/SKILL.md` |
| <a id="debate.publication"></a>`debate.publication` | /issue | verified source creation + proposal filing + bidirectional links | `skills/debate/SKILL.md` |
| <a id="design.plan_review.cursor_archetypes"></a>`design.plan_review.cursor_archetypes` | Cursor | Architecture/Standards Innovation/Exploration Pragmatism/Safety Requirements/Completeness | `skills/design/references/plan-review-runtime.md` |
| <a id="design.plan_review.codex_archetypes"></a>`design.plan_review.codex_archetypes` | Codex | Architecture/Standards Innovation/Exploration Pragmatism/Safety Requirements/Completeness | `skills/design/references/plan-review-runtime.md` |
| <a id="design.plan_review.dynamic_archetypes"></a>`design.plan_review.dynamic_archetypes` | up to 1 | scout proposes specialists fanned into Cursor+Codex dyn slots | `python/larch/design/plan_scout.py` |
| <a id="design.plan_review.panel_slots"></a>`design.plan_review.panel_slots` | round gated static plus dynamic | NDJSON manifest from python/cli.py plan-review panel-dispatch via paths-file sidecar | `python/larch/review/plan_review_panel.py` |
| <a id="design.decompose.split_path"></a>`design.decompose.split_path` | AskUserQuestion | main-agent inline proposal + single AskUserQuestion Partition/Override/chat | `skills/design/references/decompose-panel.md` |
| <a id="design.decompose.umbrella_handoff"></a>`design.decompose.umbrella_handoff` | /umbrella | exact approved batch + dependencies + in-place original conversion | `skills/design/references/decompose-panel.md` |
| <a id="implement.partition.umbrella_handoff"></a>`implement.partition.umbrella_handoff` | /umbrella | multi-issue target replacement owner | `skills/implement/SKILL.md` |
| <a id="umbrella.leaf_filing"></a>`umbrella.leaf_filing` | /issue | deduplication + prepared dependency wiring + identity-bound verified sentinel | `skills/umbrella/SKILL.md` |
| <a id="complete_umbrella.audit_gap_filing"></a>`complete_umbrella.audit_gap_filing` | /issue | exact no-dedup leaf filing + caller-bound graph attachment | `skills/complete-umbrella/SKILL.md` |
| <a id="complete_umbrella.leaf_execution"></a>`complete_umbrella.leaf_execution` | bgjob | serial thin Claude orchestrator with larch skills disabled | `skills/complete-umbrella/SKILL.md` |
| <a id="complete_umbrella.leaf_phases"></a>`complete_umbrella.leaf_phases` | fresh phase contexts | recon/design + implement + adversarial review + ship | `skills/complete-umbrella/SKILL.md` |
| <a id="complete_umbrella.leaf_ship"></a>`complete_umbrella.leaf_ship` | Deterministic leaf ship driver | one umbrella leaf | `python/larch/implement/complete_umbrella_ship.py` |
| <a id="design.decompose.harness_panel"></a>`design.decompose.harness_panel` | cli.py | offline panel regression coverage | `python/cli.py` |
| <a id="design.decompose.harness_agg"></a>`design.decompose.harness_agg` | cli.py | offline aggregator merge coverage | `python/cli.py` |
| <a id="design.decompose.harness_file"></a>`design.decompose.harness_file` | cli.py | offline prepare annotate close-original coverage | `python/cli.py` |
| <a id="design.plan.preview_emit"></a>`design.plan.preview_emit` | Step 3 plan-candidate preview | Gate C final-plan preview | `python/larch/review/plan_review_loop.py` |
| <a id="design.plan_commands.validate"></a>`design.plan_commands.validate` | Tier2+opt-in Tier3 | plan fenced bash/sh | `python/larch/design/plan_quality.py` |
| <a id="implement.conflict_review.panel"></a>`implement.conflict_review.panel` | ci-fixer | ci-fixer MODE conflict self-review only | `skills/implement/references/conflict-resolution.md` |
| <a id="implement.conflict_review.rounds_max"></a>`implement.conflict_review.rounds_max` | 2 total | resolution-review rounds | `agents/ci-fixer.md` |
| <a id="research.lanes"></a>`research.lanes` | four research lanes | architecture + edge cases + external comparisons + security | `skills/research/references/research-phase.md` |
| <a id="research.validation_panel"></a>`research.validation_panel` | 3 reviewer lanes | Claude Code Reviewer subagent + Codex + Cursor | `skills/research/references/validation-phase.md` |
| <a id="implement.review_and_fix.panel_hard"></a>`implement.review_and_fix.panel_hard` | three specialists per vendor | correctness edge-cases testing | `python/larch/core/config.py` |
| <a id="deps.issue_audit"></a>`deps.issue_audit` | one approval gate | open-issue grouping + REGULAR refresh + explicit and latent dependency audit | `skills/deps/SKILL.md` |
| <a id="runtime.residual_bash.inventory"></a>`runtime.residual_bash.inventory` | residual-bash | hooks linters thin wrappers sleep helper G-track delegation fences and residual harnesses | `python/larch/cli.py` |
| <a id="runtime.pr_closes_issue"></a>`runtime.pr_closes_issue` | closes-issue | PR-body Closes issue extraction authority | `python/larch/git/pr.py` |
