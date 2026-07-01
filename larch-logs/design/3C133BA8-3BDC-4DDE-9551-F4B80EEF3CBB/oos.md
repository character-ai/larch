### FINDING_3: `plan-review.md` plan scope is too narrow; contradictory normative sections remain
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan only lists round-matrix bullet updates for `skills/design/references/plan-review.md`, but that file is Step 3's normative contract. Sections still document cap 5, rounds 3–5 re-probe, scout cap three, round-2 generic Codex fallback, conditional `--no-fallback`, and both-absent Claude reviewer floor. That conflicts with acceptance for cap 2, empty `generic_codex_rounds`, always `--no-fallback`, no reviewer backfill, and at most one dynamic pair. The edge-case wording also leaves ambiguity about whether the both-absent Claude degraded floor stays or is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Expand the `plan-review.md` task to rewrite Dispatch, Single-pass cap, Panel pruning, Dynamic archetypes, and Claude-floor sections: cap 2, round-1 full paired panel plus at most one dynamic pair, round-2 prune on round-1 data only, no generic Codex row, always `--no-fallback`, prune-to-empty convergence; remove rounds 3-5 and legacy fallback prose.
  - From Cursor-Innovation: Expand the plan-review.md task to rewrite Dispatch Panel pruning Dynamic archetypes Single-pass and Claude-floor sections not just the matrix bullets. Remove generic Codex round-2+ fallback-return and both-absent Claude reviewer rows. Set scout cap to 1 and outer cap to 2.
  - From Cursor-Pragmatic: Narrow the edge case to single-vendor slot drops only, or add an explicit plan-review.md task to rewrite Dispatch, Panel pruning, Single-pass cap, and both-absent sections so they match always --no-fallback, no generic Codex, cap 2, and state clearly whether the both-absent Claude degraded floor stays or is removed.
  - From Cursor-Requirements: Expand the `plan-review.md` entry to require rewriting §Dispatch and the cap paragraph (not just the matrix): cap 2, round-1 full paired panel, round-2 prune-only backup, no generic Codex row, always `--no-fallback`


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_6: Public `--round-cap` flag lets direct Step 5 CLI calls bypass the new 2-round cap
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Concern**: Keeping the public `--round-cap` flag in `python/larch/review/review_and_fix.py` (lines 278–484) lets `python3 python/cli.py review-and-fix step5 --round-cap 5` still run five rounds, so the issue's cap-2 contract is not enforced on the shipped `/implement` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Clamp --round-cap to 2 in the public parser or move any higher-cap escape hatch behind an internal-only path


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_7: `scout plan-archetypes` still defaults and validates `--max-archetypes` at 3
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: In `python/larch/design/plan_scout.py` (lines 633–724), the new one-archetype cap is bypassable through the direct CLI wrapper, so `/design` can still materialize three dynamic archetypes even after the filtered-manifest path is tightened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Lower the wrapper default and max validation to 1, and add a direct regression test for `python/cli.py scout plan-archetypes`


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Installation guide still documents Gate C re-entry cap 5
- **Description**: [OUT_OF_SCOPE] Installation guide still documents Gate C re-entry cap 5. Scenario: `docs/installation-and-setup.md` still says Step 3 review-run counter caps Gate C re-entries at 5. It is not in the plan or `test-quick-mode-docs-sync.sh`, so public install docs can drift after cap 2 lands.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/installation-and-setup.md:237
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_2: [OUT_OF_SCOPE] External implementer scout prompt still says up to three dynamic archetypes
- **Description**: [OUT_OF_SCOPE] External implementer scout prompt still says up to three dynamic archetypes. Scenario: `_implementer-base.md` still instructs coders to emit up to three dynamic archetypes. `normalize_coder_scout()` will clamp to one, but the prompt invites extra scout work and confusion on the Step 5 path.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: agents/_implementer-base.md:11
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_3: [OUT_OF_SCOPE] Agent overview still documents /design per-slot Claude reviewer fallback
- **Description**: [OUT_OF_SCOPE] Agent overview still documents /design per-slot Claude reviewer fallback. Scenario: `docs/agents.md` still describes `/design` archetype slots falling back to Codex then Claude. Acceptance removes reviewer Claude backfill; this overview can mislead operators even if `docs/review-agents.md` is updated.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/agents.md:49
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_4: [OUT_OF_SCOPE] Installation guide still documents Gate C cap 5 outside docs-sync harness
- **Description**: [OUT_OF_SCOPE] Installation guide still documents Gate C cap 5 outside docs-sync harness. Scenario: docs/installation-and-setup.md still says Step 3 review-run counter caps Gate C re-entries at 5. scripts/test-quick-mode-docs-sync.sh does not scan this file so the plan omission will not fail CI.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/installation-and-setup.md:237
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Claude both-absent reviewer floor may remain after partial plan-review.md edit
- **Description**: [OUT_OF_SCOPE] Claude both-absent reviewer floor may remain after partial plan-review.md edit. Scenario: Acceptance forbids Claude reviewer backfill but plan-review.md §Claude Code Reviewer Subagent still authorizes a generic Claude reviewer when both externals are absent. If code drops that path under always --no-fallback the section becomes misleading not blocking.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:75-77
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_6: [OUT_OF_SCOPE] Active /design Step 3 skill prose still advertises up to six dynamic slots, scout cap 3, and a flattened Gate C cap of 5.
- **Description**: [OUT_OF_SCOPE] Active /design Step 3 skill prose still advertises up to six dynamic slots, scout cap 3, and a flattened Gate C cap of 5.. Scenario: Mechanical dispatch follows Python, but operators and orchestrators loading SKILL.md still see the pre-change topology and re-entry cap after code lands.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:381-548
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Gate C and flags references still hardcode review-run cap 5 while ROUND_CAP moves to 2.
- **Description**: [OUT_OF_SCOPE] Gate C and flags references still hardcode review-run cap 5 while ROUND_CAP moves to 2.. Scenario: Gate C Re-run review panel prompts and flags.md operator docs can disagree with the driver after the code change.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:15-200
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] External implementer scout guidance still tells coders to emit up to three dynamic archetypes.
- **Description**: [OUT_OF_SCOPE] External implementer scout guidance still tells coders to emit up to three dynamic archetypes.. Scenario: Main-agent and external implementer paths can still author three-archetype raw manifests until prompts change; normalize-coder-scout will clamp, but authoring guidance stays stale.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: agents/_implementer-base.md:11
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_9: Install guide still documents Gate C review re-entry cap 5
- **Description**: Install guide still documents Gate C review re-entry cap 5. Scenario: Operators reading setup docs will believe `/design` allows five Gate C re-runs after runtime cap moves to 2
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/installation-and-setup.md:237
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_10: Design flags reference still states Step 3 / Gate C review cap is 5 with no env override
- **Description**: Design flags reference still states Step 3 / Gate C review cap is 5 with no env override. Scenario: Stale normative flag text can mislead operators debugging cap behavior even when Python enforces 2
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/flags.md:57
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_11: External implementer scout prompt still says "up to three dynamic review archetypes"
- **Description**: External implementer scout prompt still says "up to three dynamic review archetypes". Scenario: Codex/Cursor implementers may emit three archetypes in raw scout JSON before `normalize_coder_scout()` clamps to one, adding avoidable scout cost/latency
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: agents/_implementer-base.md:11
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

