### OOS_1:
- **Description**: [OUT_OF_SCOPE] item 4 test harness scripts: scripts/test-breadcrumb-monitor.sh, scripts/test-breadcrumb-monitor-bash32.sh, scripts/test-redact-secrets.sh, scripts/test-larch-log.sh. Scenario: Core rollout has manual smoke coverage only, leaving monitor latency, truncation, symlink rejection, category enforcement, and committed-log redaction unguarded
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:211
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] item 7 Makefile/docs/agent-lint plumbing: Makefile, docs/linting.md, agent-lint.toml. Scenario: New harnesses and new script/docs siblings will not be discoverable or CI-enforced until target and allow-list plumbing lands
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: plan.txt:213
- **Phase**: design

### OOS_3:
- **Description**: [OUT_OF_SCOPE] item 8 security and run-log docs: SECURITY.md, docs/run-logs.md. Scenario: Users and auditors will not have the durable policy description for raw tmpdir-only breadcrumb streams and mandatory streaming redaction before commit
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: security
- **Location**: plan.txt:215
- **Phase**: design

### OOS_4:
- **Description**: [OUT_OF_SCOPE] item 9 expanded rewrite surface: .claude/skills/**/SKILL.md, .claude/rules/*.md. Scenario: Stale foreground-banner or foreground-comment patterns can continue to contradict the new background+monitor contract outside the core rollout
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:217
- **Phase**: design

### OOS_5:
- **Description**: [OUT_OF_SCOPE] item 4 test harness coverage for monitor latency, done timing, redaction, path rejection, and larch-log breadcrumb redaction is deferred. Scenario: The core rollout can land without tests for the highest-risk contracts around streaming, traps, and fail-closed redaction
- **Reviewer**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-breadcrumb-monitor.sh:new; scripts/test-breadcrumb-monitor-bash32.sh:new; scripts/test-redact-secrets.sh:1-170; scripts/test-larch-log.sh:1-420
- **Phase**: design

### OOS_6:
- **Description**: [OUT_OF_SCOPE] item 7 Makefile, linting docs, and agent-lint allow-list plumbing is deferred. Scenario: New breadcrumb monitor tests/docs may be invisible to make lint or agent-lint until the deferred harness work lands
- **Reviewer**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:4-79; docs/linting.md:220-280; agent-lint.toml:1-220
- **Phase**: design

### OOS_7:
- **Description**: [OUT_OF_SCOPE] item 8 security and run-log documentation for breadcrumb stream redaction is deferred. Scenario: Operators will not have durable docs for raw tmpdir streams, committed redaction, and residual sensitive-content risk
- **Reviewer**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:1-178; docs/run-logs.md:1-70
- **Phase**: design

### OOS_8:
- **Description**: [OUT_OF_SCOPE] item 9 expanded stale foreground-banner rewrite is deferred. Scenario: Some skill/rule surfaces may still teach the old foreground-required pattern while the denylist moves to background plus breadcrumb-monitor
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lint-foreground-markers.sh:15-30; .claude/skills/*/SKILL.md; .claude/rules/*.md
- **Phase**: design

### OOS_9:
- **Description**: [OUT_OF_SCOPE] item 4 - breadcrumb monitor and streaming redactor harnesses deferred. Scenario: No dedicated harness will pin stream growth latency, partial-byte retention, truncation, DONE-sentinel timing, fail-closed redaction, symlink/path rejection, category enforcement, or committed-copy secret exclusion in this PR.
- **Reviewer**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:1-218; scripts/lib-redact-streaming.sh:1-42; scripts/test-redact-secrets.sh:1; scripts/test-larch-log.sh:1
- **Phase**: design

### OOS_10:
- **Description**: [OUT_OF_SCOPE] Item 4 test harness scripts are deferred. Scenario: Monitor latency, truncation, done-sentinel timing, symlink rejection, streaming PEM redaction, and committed-log secret exclusion remain without dedicated CI coverage in this core slice.
- **Reviewer**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-breadcrumb-monitor.sh:1; scripts/test-breadcrumb-monitor-bash32.sh:1; scripts/test-redact-secrets.sh:1; scripts/test-larch-log.sh:1
- **Phase**: design

### OOS_11:
- **Description**: Item 7 defers agent-lint.toml allow-list entries for test-breadcrumb-monitor* paths. Scenario: Follow-up item 4 adds Makefile-only harness scripts; without item 7 exclude entries agent-lint G004 will flag scripts/test-breadcrumb-monitor.sh and .md as dead until excluded (same pattern as scripts/test-lib-quiet.sh:661-664)
- **Reviewer**: Cursor-dyn-deferred-ci-gap
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:282-1451; plan.txt:213-214
- **Phase**: design

### OOS_12:
- **Description**: Item 7 defers Makefile phony targets and test-harnesses-N shard registration. Scenario: make test-breadcrumb-monitor and make test-breadcrumb-monitor-bash32 are undefined today (verified: no Makefile match); issue acceptance requires them once follow-ups land
- **Reviewer**: Cursor-dyn-deferred-ci-gap
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:4-60; plan.txt:213-214
- **Phase**: design

### OOS_13:
- **Description**: PR #2786 left breadcrumb-monitor.md missing; core plan adds it (item 5) — agent-lint on PR #2786 runtime files passes without item 7 exclusions. Scenario: pre-commit run agent-lint --all-files on current main exits 0; scripts/breadcrumb-monitor.sh is SKILL.md-reachable; scripts/lib-redact-streaming.sh is not separately excluded but does not fail CI today
- **Reviewer**: Cursor-dyn-deferred-ci-gap
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:3; plan.txt:145-168
- **Phase**: design

