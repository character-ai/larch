### OOS_1:
- **Description**: _write_ship_state always clears RESUME_PHASE and CALLER_KIND; no Python path emits ship_pr_pre_push conflict metadata. Scenario: Pre-push rebase conflicts cannot trigger the Exit 4 RESUME_PHASE=ship-pr-rrr-phase14 / CALLER_KIND=ship_pr_pre_push handoff in skills/implement/SKILL.md:1064 on the Python driver; conflict auto-recovery remains bash-only
- **Reviewer**: Cursor-dyn-json-state-contract
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/ship.py:387-388
- **Phase**: design

