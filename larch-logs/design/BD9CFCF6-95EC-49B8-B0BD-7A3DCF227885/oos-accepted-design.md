### OOS_2:
- **Description**: Lint-fix stall on `main-agent-required` after earlier `applied` iterations leaves a dirty tree. Scenario: Plan commits only on successful recheck exits; if lint-fix applies once then returns `main-agent-required`, Step 5 stalls without committing, and stall recovery may resume toward ship with dirty state
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/review_and_fix.py:1178-1179
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/4740
