### OOS_1: [OUT_OF_SCOPE] Always-loaded `AGENTS.md` still prescribes global foreground sentinel probing on non-empty premature notifications without an `/implement` carve-out
- **Description**: [OUT_OF_SCOPE] Always-loaded `AGENTS.md` still prescribes global foreground sentinel probing on non-empty premature notifications without an `/implement` carve-out. Scenario: Plan line 241 defers `AGENTS.md` changes. `AGENTS.md` still tells every orchestrator to foreground-probe on non-empty premature output while the trimmed implement stub will require notification-only recovery for all premature notifications. Operators reading `AGENTS.md` before implement NEVER #8 may probe design sentinels.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: AGENTS.md:86
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Always-loaded AGENTS.md still mandates foreground sentinel probing on non-empty premature notifications without an /implement carve-out
- **Description**: [OUT_OF_SCOPE] Always-loaded AGENTS.md still mandates foreground sentinel probing on non-empty premature notifications without an /implement carve-out. Scenario: Plan defers AGENTS.md (plan.txt:241) while implement NEVER #8 will require notification-only recovery for all premature notifications; AGENTS.md remains always-loaded and can contradict implement recovery on non-empty premature stdout
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: AGENTS.md:86
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Always-loaded `AGENTS.md` still mandates foreground sentinel probing on any premature non-empty `<task-notification>` project-wide, with no `/implement` carve-out, while the trimmed implement NEVER #8 stub will require notification-only recovery for all premature notifications.
- **Description**: [OUT_OF_SCOPE] Always-loaded `AGENTS.md` still mandates foreground sentinel probing on any premature non-empty `<task-notification>` project-wide, with no `/implement` carve-out, while the trimmed implement NEVER #8 stub will require notification-only recovery for all premature notifications.. Scenario: Operators and agents loading Tier-1a `AGENTS.md` during `/implement` can still foreground-probe design sentinels on non-empty premature output despite the skill stub and lazy-read split.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: AGENTS.md:86
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] Add the shared-orchestrator smoke checks and empty-qualifier mirrors to the design-structure harness duplicates the stricter anti-polling harness.
- **Description**: [OUT_OF_SCOPE] Add the shared-orchestrator smoke checks and empty-qualifier mirrors to the design-structure harness duplicates the stricter anti-polling harness.. Scenario: The feature already gets full coverage from scripts/test-implement-anti-polling-rule.sh, so this extra harness surface adds maintenance-only complexity without changing correctness.
- **Reviewer**: Codex-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/test-design-structure.sh:300-339
- **Phase**: design



