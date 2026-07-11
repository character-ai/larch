### FINDING_3: Invariant-primary mode lacks an explicit lane, evidence, and run-ID contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The invariant-primary path is not explicitly distinguished from ordinary CI-failure repair. Existing validation still expects a numeric GitHub run ID, run resolution may select an unrelated failed run, CI-log collection remains implicit, and dispatch still expects a failure-log-backed `EvidenceState`. The plan also does not define how invariant-only evidence is passed or how stale evidence is prevented from changing ordinary CI behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define invariant-primary mode explicitly: bind a documented non-CI `RUN_ID` sentinel in the launch envelope and sidecar; skip `_resolve_run_id` and `_collect_evidence`; omit `--failure-log` or pass a validated invariant-only placeholder; require `--invariant-evidence` only.
  - From Cursor-Requirements: Add an explicit invariant-primary signal (`--invariant-primary` or equivalent) on wrapper start and `ci fixer-lane`, branch lane entry to skip run-id resolution and `_collect_evidence` only on that path, and forbid forwarding optional invariant evidence on ordinary CI-failure tiers.
  - From Cursor-Requirements: Define invariant-primary run identity explicitly (for example bind sidecar `RUN_ID` to `LARCH_RUN_ID` and relax numeric-only validation on that path only), skip PR run-id resolution in wrapper start mode, and add harness coverage for violation-without-`FAILED_RUN_ID`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: SECURITY.md still documents the retired delegated Claude/Opus in-session Agent CI-fix loop
- **Description**: SECURITY.md still documents the retired delegated Claude/Opus in-session Agent CI-fix loop. Scenario: The plan updates `docs/configuration-and-permissions.md` but not `SECURITY.md`, which still describes write-capable Claude/Opus agentic CI fixing and no Codex/Cursor fallback tiers. Operators reading security policy will follow the removed default path.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: SECURITY.md:335
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_2: agent-lint.toml still exempts the wrapper as intentionally dormant
- **Description**: agent-lint.toml still exempts the wrapper as intentionally dormant. Scenario: After cutover, `SKILL.md` will reference `step-8-ci-fixer.sh` and tests will assert active wiring, but `agent-lint.toml` still excludes the wrapper and harness with a dormancy comment and `not_contains` rationale. Stale lint policy can hide orphan or mis-wiring regressions.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:342-348
- **Phase**: design




Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_3: SECURITY.md still documents Step 8 CI fixing as a write-capable Claude/Opus in-session agentic loop. The cutover removes the default Agent path and moves repair to bgjob lanes.
- **Description**: SECURITY.md still documents Step 8 CI fixing as a write-capable Claude/Opus in-session agentic loop. The cutover removes the default Agent path and moves repair to bgjob lanes.. Scenario: Refresh SECURITY.md Step 8+ CI-fix wording to match the wrapper waterfall and `LARCH_CI_FIXER=0` inline exception.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: SECURITY.md:335
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: The plan runs `skills/implement/scripts/test-step-8-ci-fixer.sh` in its testing strategy, but that harness is not registered in any Makefile `test-harnesses-*` target (unlike `test-implement-step8-exit3-first-fixer`).
- **Description**: The plan runs `skills/implement/scripts/test-step-8-ci-fixer.sh` in its testing strategy, but that harness is not registered in any Makefile `test-harnesses-*` target (unlike `test-implement-step8-exit3-first-fixer`).. Scenario: Default-branch CI may miss wrapper regressions until an operator runs the script manually. Add a Makefile target and shard registration for `test-step-8-ci-fixer.sh`.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: Makefile
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

