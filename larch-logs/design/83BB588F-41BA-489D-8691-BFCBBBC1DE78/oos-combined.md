### OOS_1:
- **Description**: [OUT_OF_SCOPE] item 4 test harness scripts: scripts/test-breadcrumb-monitor.sh, scripts/test-breadcrumb-monitor-bash32.sh, scripts/test-redact-secrets.sh, scripts/test-larch-log.sh. Scenario: Core rollout has manual smoke coverage only, leaving monitor latency, truncation, symlink rejection, category enforcement, and committed-log redaction unguarded
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:211
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] Item 4 test harness scripts are deferred. Scenario: Monitor latency, truncation, done-sentinel timing, symlink rejection, streaming PEM redaction, and committed-log secret exclusion remain without dedicated CI coverage in this core slice.
- **Reviewer**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-breadcrumb-monitor.sh:1; scripts/test-breadcrumb-monitor-bash32.sh:1; scripts/test-redact-secrets.sh:1; scripts/test-larch-log.sh:1
- **Phase**: design

### OOS_3:
- **Description**: Item 7 defers agent-lint.toml allow-list entries for test-breadcrumb-monitor* paths. Scenario: Follow-up item 4 adds Makefile-only harness scripts; without item 7 exclude entries agent-lint G004 will flag scripts/test-breadcrumb-monitor.sh and .md as dead until excluded (same pattern as scripts/test-lib-quiet.sh:661-664)
- **Reviewer**: Cursor-dyn-deferred-ci-gap
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:282-1451; plan.txt:213-214
- **Phase**: design

### OOS_4:
- **Description**: Item 7 defers Makefile phony targets and test-harnesses-N shard registration. Scenario: make test-breadcrumb-monitor and make test-breadcrumb-monitor-bash32 are undefined today (verified: no Makefile match); issue acceptance requires them once follow-ups land
- **Reviewer**: Cursor-dyn-deferred-ci-gap
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:4-60; plan.txt:213-214
- **Phase**: design

### OOS_5: Aggregated rollup of 8 capped OOS items
- **Description**: Cap 5 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 8 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_2:**: - **Description**: [OUT_OF_SCOPE] item 7 Makefile/docs/agent-lint plumbing: Makefile, docs/linting.md, agent-lint.toml. Scenario: New harnesses and new script/docs siblings will not be discoverable or… [Files: Makefile agent-lint.toml. docs/linting.md plan.txt:213]
  - **OOS_3:**: - **Description**: [OUT_OF_SCOPE] item 8 security and run-log docs: SECURITY.md, docs/run-logs.md. Scenario: Users and auditors will not have the durable policy description for raw tmpdir-only breadcr… [Files: SECURITY.md docs/run-logs.md. plan.txt:215]
  - **OOS_4:**: - **Description**: [OUT_OF_SCOPE] item 9 expanded rewrite surface: .claude/skills/**/SKILL.md, .claude/rules/*.md. Scenario: Stale foreground-banner or foreground-comment patterns can continue to cont… [Files: SKILL.md plan.txt:217]
  - **OOS_5:**: - **Description**: [OUT_OF_SCOPE] item 4 test harness coverage for monitor latency, done timing, redaction, path rejection, and larch-log breadcrumb redaction is deferred. Scenario: The core rollout c… [Files: scripts/test-larch-log.sh:1-420 scripts/test-redact-secrets.sh:1-170]
  - **OOS_6:**: - **Description**: [OUT_OF_SCOPE] item 7 Makefile, linting docs, and agent-lint allow-list plumbing is deferred. Scenario: New breadcrumb monitor tests/docs may be invisible to make lint or agent-lint… [Files: Makefile Makefile:4-79 agent-lint.toml:1-220 docs/linting.md:220-280]
  - **OOS_7:**: - **Description**: [OUT_OF_SCOPE] item 8 security and run-log documentation for breadcrumb stream redaction is deferred. Scenario: Operators will not have durable docs for raw tmpdir streams, committe… [Files: SECURITY.md:1-178 docs/run-logs.md:1-70]
  - **OOS_8:**: - **Description**: [OUT_OF_SCOPE] item 9 expanded stale foreground-banner rewrite is deferred. Scenario: Some skill/rule surfaces may still teach the old foreground-required pattern while the denylist… [Files: SKILL.md scripts/lint-foreground-markers.sh:15-30]
  - **OOS_9:**: - **Description**: [OUT_OF_SCOPE] item 4 - breadcrumb monitor and streaming redactor harnesses deferred. Scenario: No dedicated harness will pin stream growth latency, partial-byte retention, truncati… [Files: scripts/breadcrumb-monitor.sh:1-218 scripts/lib-redact-streaming.sh:1-42 scripts/test-larch-log.sh:1 scripts/test-redact-secrets.sh:1]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 8 entries
- **Phase**: implement

