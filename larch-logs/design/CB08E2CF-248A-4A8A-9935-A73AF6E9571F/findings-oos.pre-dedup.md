### OOS_1: SECURITY.md still documents the retired delegated Claude/Opus in-session Agent CI-fix loop
- **Description**: SECURITY.md still documents the retired delegated Claude/Opus in-session Agent CI-fix loop. Scenario: The plan updates `docs/configuration-and-permissions.md` but not `SECURITY.md`, which still describes write-capable Claude/Opus agentic CI fixing and no Codex/Cursor fallback tiers. Operators reading security policy will follow the removed default path.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: SECURITY.md:335
- **Phase**: design



### OOS_2: agent-lint.toml still exempts the wrapper as intentionally dormant
- **Description**: agent-lint.toml still exempts the wrapper as intentionally dormant. Scenario: After cutover, `SKILL.md` will reference `step-8-ci-fixer.sh` and tests will assert active wiring, but `agent-lint.toml` still excludes the wrapper and harness with a dormancy comment and `not_contains` rationale. Stale lint policy can hide orphan or mis-wiring regressions.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:342-348
- **Phase**: design



### OOS_3: SECURITY.md still documents Step 8 CI fixing as a write-capable Claude/Opus in-session agentic loop. The cutover removes the default Agent path and moves repair to bgjob lanes.
- **Description**: SECURITY.md still documents Step 8 CI fixing as a write-capable Claude/Opus in-session agentic loop. The cutover removes the default Agent path and moves repair to bgjob lanes.. Scenario: Refresh SECURITY.md Step 8+ CI-fix wording to match the wrapper waterfall and `LARCH_CI_FIXER=0` inline exception.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: SECURITY.md:335
- **Phase**: design



### OOS_4: The plan runs `skills/implement/scripts/test-step-8-ci-fixer.sh` in its testing strategy, but that harness is not registered in any Makefile `test-harnesses-*` target (unlike `test-implement-step8-exit3-first-fixer`).
- **Description**: The plan runs `skills/implement/scripts/test-step-8-ci-fixer.sh` in its testing strategy, but that harness is not registered in any Makefile `test-harnesses-*` target (unlike `test-implement-step8-exit3-first-fixer`).. Scenario: Default-branch CI may miss wrapper regressions until an operator runs the script manually. Add a Makefile target and shard registration for `test-step-8-ci-fixer.sh`.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: Makefile
- **Phase**: design



