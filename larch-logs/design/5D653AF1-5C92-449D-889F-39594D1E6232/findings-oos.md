### OOS_1: [OUT_OF_SCOPE] Consumer matrix omits design.plan_drafter runtime dispatch.
- **Description**: [OUT_OF_SCOPE] Consumer matrix omits design.plan_drafter runtime dispatch.. Scenario: Step 2b vendor selection resolves design.plan_drafter at runtime; registry-only tests can pass while LARCH_DESIGN_DRAFTER / resolve_vendor behavior drifts.
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/design_lifecycle.py:3632-3636
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Step 5 scripted-review banner still describes three Cursor archetype voters.
- **Description**: [OUT_OF_SCOPE] Step 5 scripted-review banner still describes three Cursor archetype voters.. Scenario: After #5311, operators reading SKILL.md at the Step 5 entry still see stale voter-composition prose; item 4 only updates skills/shared/voting-protocol.md.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/SKILL.md:591-591
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Mirrored code-review docs still describe the old three-Cursor panel and Codex-free composition
- **Description**: [OUT_OF_SCOPE] Mirrored code-review docs still describe the old three-Cursor panel and Codex-free composition. Scenario: Readers of the mirror docs will still see stale code-review voter composition even after `skills/shared/voting-protocol.md` is updated, so the docs drift remains visible outside the scoped file
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/agents.md:53; docs/skills.md:123; docs/review-agents.md:102
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] Step 5 banner still describes a three-Cursor-archetype code-review voter panel
- **Description**: [OUT_OF_SCOPE] Step 5 banner still describes a three-Cursor-archetype code-review voter panel. Scenario: Item 4 scopes doc fixes to `skills/shared/voting-protocol.md` only. Operators reading the Step 5 banner during `/implement` can still misread post-#5311 voter composition (`cursor-validity` + `codex-plan-fidelity` + `codex-pragmatism`).
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:591
- **Phase**: design



### OOS_5: Cross-role mutation guard adds a generic neighbor-alias check that the feature does not need.
- **Description**: Cross-role mutation guard adds a generic neighbor-alias check that the feature does not need.. Scenario: The per-consumer probes already pin the relevant role at the consumer boundary. This extra guard adds harness surface without closing a real runtime gap, so the plan ships correctly without it.
- **Reviewer**: Codex-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:81-83
- **Phase**: design



### OOS_6: [OUT_OF_SCOPE] scout_plan_archetypes role-id forwarding probe duplicates existing coverage
- **Description**: [OUT_OF_SCOPE] scout_plan_archetypes role-id forwarding probe duplicates existing coverage. Scenario: python/test_plan_scout.py::test_plan_wrapper_forwards_role_id_to_inner_override already asserts --role-id design.plan_archetype_scout forwarding; adding the same boundary in test_external_dispatch.py inflates diff without new drift signal
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_external_dispatch.py:72
- **Phase**: design



