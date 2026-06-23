### OOS_1: [OUT_OF_SCOPE] [SCOPE-REDUCTION] `implement step-8-ship` CLI verb bypasses the planned bash handoff sidecar contract
- **Description**: [OUT_OF_SCOPE] [SCOPE-REDUCTION] `implement step-8-ship` CLI verb bypasses the planned bash handoff sidecar contract. Scenario: `step8_ship_main` still runs guard plus `ship pr` directly with no `.step-8-ship-handoff.{rc,json}` writer. SKILL uses the bash wrapper today, but the registry entry invites a second ship path that cannot feed `ship route-exit`
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/implement_dispatch.py:674-710
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] [SCOPE-REDUCTION] Optional frozen dataclass for ship-route parsing adds abstraction without a stated need
- **Description**: [OUT_OF_SCOPE] [SCOPE-REDUCTION] Optional frozen dataclass for ship-route parsing adds abstraction without a stated need. Scenario: The plan introduces a dataclass "if it keeps the router readable" for a single `ship_route_exit_main` with a fixed rc-to-action table; one function plus small helpers matches existing `ship_pre_driver_main` style and keeps the diff smaller
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/implement_dispatch.py:36
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Stale contract cross-reference after checkpoint authority moves.
- **Description**: [OUT_OF_SCOPE] Stale contract cross-reference after checkpoint authority moves.. Scenario: Step 8+ still points operators at `oos-disposition-checkpoint.md` even though runtime authority shifts to `implement step-8-oos-checkpoint` and `step-8-oos-checkpoint.md`.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:870
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] `implement step-8-ship` bypasses the planned bash handoff sidecar contract.
- **Description**: [OUT_OF_SCOPE] `implement step-8-ship` bypasses the planned bash handoff sidecar contract.. Scenario: `step8_ship_main` forwards directly to `ship pr` with no `.step-8-ship-handoff.*` capture; any caller of the Python verb skips `ship route-exit` inputs.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/implement_dispatch.py:674-710
- **Phase**: design



