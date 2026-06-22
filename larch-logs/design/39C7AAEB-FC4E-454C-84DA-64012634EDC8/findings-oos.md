### OOS_1: New post-7a launcher scripts are not listed in Extracted Script Registry / S030 machine-reachability blocks
- **Description**: New post-7a launcher scripts are not listed in Extracted Script Registry / S030 machine-reachability blocks. Scenario: agent-lint S030 may not reach step-architectural-guidelines-*.sh and test-architectural-guidelines-step.sh until a later hygiene pass
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:91-110
- **Phase**: design



### OOS_2: note_consumable gates only on HEAD_SHA match, not on DIFF_FINGERPRINT vs current materialized diff
- **Description**: note_consumable gates only on HEAD_SHA match, not on DIFF_FINGERPRINT vs current materialized diff. Scenario: If a ship.py invalidation hook is missed on an implementation commit, a stale staged assessment could still be pinned and consumed at the new HEAD with misleading deviation text
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/architectural_guidelines.py:note_consumable
- **Phase**: design



### OOS_3: Root resolution is specified ad hoc instead of reusing python/repo_roots.py helpers
- **Description**: Root resolution is specified ad hoc instead of reusing python/repo_roots.py helpers. Scenario: Custom CLAUDE_PROJECT_DIR plus cwd logic may drift from checks._default_repo_root and consumer_repo_root over time
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/architectural_guidelines.py:read_guidelines
- **Phase**: design



