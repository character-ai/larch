### FINDING_1: code-quality: scripts/breadcrumb-monitor.sh:139-142
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Category vocabulary duplicated instead of reusing larch_quiet_bc_valid_category from lib-quiet.sh Adding a new breadcrumb category updates lib-quiet.sh but monitor keeps dropping records until its separate case is updated Call larch_quiet_bc_valid_category from larch_bm_emit_line
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/breadcrumb-monitor.sh:28-43;scripts/lib-larch-log.sh:217-231
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Session tmpdir allowlist implemented twice for monitor vs larch-log publish Future session root (or path check fix) updated in only one copy breaks either monitor validation or commit-time publish Extract one shared under-session-tmp helper used by both call sites
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/larch-log.md:109-111
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] larch-log.md still claims redaction failure removes committed breadcrumbs/ directory Operators/readers expect prior committed breadcrumbs to disappear on retry failure; code and tests now preserve them Update docs to match preserve-on-failure staging semantics
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-breadcrumb-monitor.sh:432-454
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate harness label Test 13 for two different cases CI failure output ambiguous about which assertion failed Renumber test section labels uniquely
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-breadcrumb-monitor-bash32.sh:22
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Bash32 harness only re-execs main test without explicit parity assertion Plan wording implied stronger parity check than implemented Document intent or add minimal golden/exit parity assertion
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/ship-pr.sh:2160-2161
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dual stall+escalate breadcrumbs for one waterfall exhaustion Monitor/chat may show duplicate warnings for one event Collapse to one categorized breadcrumb if redundant
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Uncategorized emit_breadcrumb in dev-only bump script Stream-set bump runs could emit unknown-category warnings when that path is used Migrate apply-bump.sh when touching bump skill (not this PR scope)
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] apply-bump retry emit_breadcrumb lacks --category= while ship-pr inherits LARCH_BREADCRUMB_STREAM During origin/main bump-race retries under backgrounded ship-pr, WARN unknown-category drops retry progress from the live stream and committed breadcrumbs Migrate to emit_breadcrumb --category=retry with the existing message text; update apply-bump.md
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/lib-larch-log.sh:217-257
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Breadcrumb path-scope checks require *_TMPDIR env vars but source dir is derived only from --log-root larch-log.sh commit with --log-root $X/larch-logs and $X/breadcrumbs populated fails exit 3 when IMPLEMENT_TMPDIR is unset Also allow session_root derived from log-root in larch_log_breadcrumbs_under_session_tmp, or hard-require export in all commit callers plus a regression test
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] correctness: scripts/test-breadcrumb-monitor.sh:21-22
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Stale comment omits RESEARCH_TMPDIR from documented session roots None functionally Update the harness header comment to list all four tmpdir roots
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-ci-wait.sh:125-261
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No byte-for-byte stderr regression for stream-unset ci-wait after emit_breadcrumb_stderr migration Wait-loop stderr formatting (no-newline dots) can regress while stdout/poll-count assertions still pass Add golden stderr baseline for pending-then-pass without LARCH_BREADCRUMB_STREAM
- **Suggested revision**: Address the concern above.

### FINDING_12: security: scripts/lib-larch-log.sh:209-257
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Breadcrumb publish path scope uses prefix-only case matching without rejecting .. components unlike breadcrumb-monitor.sh. Exporting LARCH_BREADCRUMB_SOURCE_DIR=$IMPLEMENT_TMPDIR/../other/breadcrumbs can pass larch_log_breadcrumbs_under_session_tmp and commit redacted streams from another directory into larch-logs/<run-id>/breadcrumbs/. Reject .. in the full source path; canonicalize under the active session *_TMPDIR; add a test-larch-log.sh traversal case.
- **Suggested revision**: Address the concern above.

### FINDING_13: security: scripts/lib-larch-log.sh:246-277
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Publish checks symlinks on the breadcrumbs dir and each .ndjson file but not on session *_TMPDIR ancestors. If IMPLEMENT_TMPDIR is a symlink to a wider tree, prefix checks pass and publish reads outside the intended isolated tmpdir. Resolve non-symlink canonical session roots at publish time and require the breadcrumb source to stay under that root.
- **Suggested revision**: Address the concern above.

### FINDING_14: security: SECURITY.md:128-141
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Documented residual risk: operational wait-ci/warn breadcrumb text may be committed after secrets redaction. A failed CI wait can write check names, URLs, or failure snippets into committed larch-logs breadcrumbs visible in the public repo. Keep as documented accepted risk; cross-link from docs/run-logs.md for operator awareness.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] security: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] emit_breadcrumb retry lines lack --category= so stream-set runs drop progress records. With LARCH_BREADCRUMB_STREAM set during bump, retry breadcrumbs never reach the monitor. Add --category=retry to apply-bump.sh emit_breadcrumb calls (separate from this PR).
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] apply-bump.sh emits uncategorized emit_breadcrumb while ship-pr inherits LARCH_BREADCRUMB_STREAM Origin/main bump race retries log WARN unknown-category and drop from the live monitor stream so operators see no retry progress during Step 8 bump Add --category=retry (or progress) on the emit_breadcrumb call or unset LARCH_BREADCRUMB_STREAM around apply-bump.sh
- **Suggested revision**: Address the concern above.

### FINDING_17: architecture: scripts/lib-larch-log.sh:305-315
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Breadcrumb publish rm -rf dest_dir before mv loses data if mv fails After a successful first publish refresh-run-logs re-commit can rm committed breadcrumbs then fail mv leaving no breadcrumbs/ in the repo worktree Publish via staging rename without deleting dest until mv succeeds; add test forcing mv failure after first publish
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/larch-log.sh:127-142
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Empty breadcrumbs_source when log-root is not */larch-logs silently skips publish Caller passes non-standard --log-root without LARCH_BREADCRUMB_SOURCE_DIR; commit succeeds without breadcrumbs/ while tmpdir still has live streams Fail closed or warn when tmpdir breadcrumbs exist but source resolution fails
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/lib-larch-log.sh:293
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Commit reads session ndjson without synchronizing with active writers refresh-run-logs commit overlaps ship-pr/ci-wait appends; committed file can contain torn lines or partial secrets Follow done-sentinel gating snapshot copy or document commit-only-after-monitor-complete
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/breadcrumb-monitor.sh:117-128
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Rate cap silently drops breadcrumb lines Burst CI dot progress during wait-ci exceeds RATE_CAP; chat loses progress with only WARN rate-capped Coalesce capped output or raise wait-ci cap
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] code-quality: scripts/larch-log.md:109-110
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc claims redaction failure removes dest breadcrumbs Round 2 preserves dest on redactor failure; doc contradicts tests and code Align larch-log.md with actual fail-closed semantics
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] architecture: scripts/breadcrumb-monitor.sh:176-180
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Monitor exits 4 after 30m without stopping background script Long ship-pr can outlive monitor; orchestrator may advance before done sentinel N/A for this PR unless extending monitor contract
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/refresh-run-logs.md:1-83
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] refresh-run-logs.md omits breadcrumb publish contract that the plan required documented Operators reading only refresh-run-logs.md will not know commit now publishes redacted session breadcrumbs and can fail with REFRESH_COMMITTED=false REASON=commit-failed Add a subsection stating IMPLEMENT_TMPDIR export enables larch-log commit to publish breadcrumbs/ via the commit-only redaction pipeline
- **Suggested revision**: Address the concern above.

