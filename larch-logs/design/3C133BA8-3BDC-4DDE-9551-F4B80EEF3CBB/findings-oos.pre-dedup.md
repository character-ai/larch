### OOS_1: [OUT_OF_SCOPE] Installation guide still documents Gate C re-entry cap 5
- **Description**: [OUT_OF_SCOPE] Installation guide still documents Gate C re-entry cap 5. Scenario: `docs/installation-and-setup.md` still says Step 3 review-run counter caps Gate C re-entries at 5. It is not in the plan or `test-quick-mode-docs-sync.sh`, so public install docs can drift after cap 2 lands.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/installation-and-setup.md:237
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] External implementer scout prompt still says up to three dynamic archetypes
- **Description**: [OUT_OF_SCOPE] External implementer scout prompt still says up to three dynamic archetypes. Scenario: `_implementer-base.md` still instructs coders to emit up to three dynamic archetypes. `normalize_coder_scout()` will clamp to one, but the prompt invites extra scout work and confusion on the Step 5 path.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: agents/_implementer-base.md:11
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Agent overview still documents /design per-slot Claude reviewer fallback
- **Description**: [OUT_OF_SCOPE] Agent overview still documents /design per-slot Claude reviewer fallback. Scenario: `docs/agents.md` still describes `/design` archetype slots falling back to Codex then Claude. Acceptance removes reviewer Claude backfill; this overview can mislead operators even if `docs/review-agents.md` is updated.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/agents.md:49
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] Installation guide still documents Gate C cap 5 outside docs-sync harness
- **Description**: [OUT_OF_SCOPE] Installation guide still documents Gate C cap 5 outside docs-sync harness. Scenario: docs/installation-and-setup.md still says Step 3 review-run counter caps Gate C re-entries at 5. scripts/test-quick-mode-docs-sync.sh does not scan this file so the plan omission will not fail CI.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/installation-and-setup.md:237
- **Phase**: design



### OOS_5: [OUT_OF_SCOPE] Claude both-absent reviewer floor may remain after partial plan-review.md edit
- **Description**: [OUT_OF_SCOPE] Claude both-absent reviewer floor may remain after partial plan-review.md edit. Scenario: Acceptance forbids Claude reviewer backfill but plan-review.md §Claude Code Reviewer Subagent still authorizes a generic Claude reviewer when both externals are absent. If code drops that path under always --no-fallback the section becomes misleading not blocking.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:75-77
- **Phase**: design



### OOS_6: [OUT_OF_SCOPE] Active /design Step 3 skill prose still advertises up to six dynamic slots, scout cap 3, and a flattened Gate C cap of 5.
- **Description**: [OUT_OF_SCOPE] Active /design Step 3 skill prose still advertises up to six dynamic slots, scout cap 3, and a flattened Gate C cap of 5.. Scenario: Mechanical dispatch follows Python, but operators and orchestrators loading SKILL.md still see the pre-change topology and re-entry cap after code lands.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:381-548
- **Phase**: design



### OOS_7: [OUT_OF_SCOPE] Gate C and flags references still hardcode review-run cap 5 while ROUND_CAP moves to 2.
- **Description**: [OUT_OF_SCOPE] Gate C and flags references still hardcode review-run cap 5 while ROUND_CAP moves to 2.. Scenario: Gate C Re-run review panel prompts and flags.md operator docs can disagree with the driver after the code change.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:15-200
- **Phase**: design



### OOS_8: [OUT_OF_SCOPE] External implementer scout guidance still tells coders to emit up to three dynamic archetypes.
- **Description**: [OUT_OF_SCOPE] External implementer scout guidance still tells coders to emit up to three dynamic archetypes.. Scenario: Main-agent and external implementer paths can still author three-archetype raw manifests until prompts change; normalize-coder-scout will clamp, but authoring guidance stays stale.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: agents/_implementer-base.md:11
- **Phase**: design



### OOS_9: Install guide still documents Gate C review re-entry cap 5
- **Description**: Install guide still documents Gate C review re-entry cap 5. Scenario: Operators reading setup docs will believe `/design` allows five Gate C re-runs after runtime cap moves to 2
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/installation-and-setup.md:237
- **Phase**: design



### OOS_10: Design flags reference still states Step 3 / Gate C review cap is 5 with no env override
- **Description**: Design flags reference still states Step 3 / Gate C review cap is 5 with no env override. Scenario: Stale normative flag text can mislead operators debugging cap behavior even when Python enforces 2
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/flags.md:57
- **Phase**: design



### OOS_11: External implementer scout prompt still says "up to three dynamic review archetypes"
- **Description**: External implementer scout prompt still says "up to three dynamic review archetypes". Scenario: Codex/Cursor implementers may emit three archetypes in raw scout JSON before `normalize_coder_scout()` clamps to one, adding avoidable scout cost/latency
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: agents/_implementer-base.md:11
- **Phase**: design



