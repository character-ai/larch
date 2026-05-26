### FINDING_1: code-quality: scripts/breadcrumb-monitor.sh:28-43,scripts/lib-larch-log.sh:236-265
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicated session-tmpdir guards with prefix vs canonical semantics Monitor accepts a path commit rejects after symlink/normalization (or opposite), yielding empty committed breadcrumbs despite live streams Factor one shared allowlist helper used by monitor and larch-log publish
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Only uncategorized emit_breadcrumb callsite remains Under ship-pr with LARCH_BREADCRUMB_STREAM set, bump-race retries emit WARN unknown-category and never surface in chat Add --category=retry (or progress) and a stream-set test in test-apply-bump.sh
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/lib-larch-log.sh:342-371
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Commit walker only ingests *.ndjson Non-ndjson files in session breadcrumbs/ are dropped silently on publish Glob all regular files per plan or document and test ndjson-only contract
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/breadcrumb-monitor.sh:162-171
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] larch_bm_read_chunk slurps full delta into memory Large stream growth bursts can allocate multi-MiB strings in the monitor Use chunked reads or cap delta before command substitution
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-breadcrumb-monitor.sh:454-482
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate Test 14 labels and mismatched alloc_sentinels prefixes CI failure messages point at the wrong scenario Renumber tests and align alloc_sentinels prefixes
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/larch-log.sh:127-143,scripts/refresh-run-logs.sh:5157-5162
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Implicit breadcrumb source derivation only Mis-set log-root yields no committed breadcrumbs without an explicit caller error Export LARCH_BREADCRUMB_SOURCE_DIR from refresh/finalize publish callers
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/lib-larch-log.sh:272-304
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Swap-based publish heavier than plan’s atomic mv Extra maintenance surface for directory replacement Keep if refresh replace is required; otherwise simplify after audit
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] architecture: scripts/ci-wait.sh:249
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Terminating newline stays on quiet FD4 not breadcrumb stream Stream consumers miss a visual separator before success text Optional: route newline through emit_breadcrumb_stderr or drop it when stream is set
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Uncategorized emit_breadcrumb under inherited LARCH_BREADCRUMB_STREAM is dropped from the stream Step 8 bump race with monitor: retry lines never appear in stream/chat despite up to 10 retries Add --category=retry (or progress) on the apply-bump emit_breadcrumb callsite
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/implement-finalize.sh:1388-1434
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 18 teardown never invokes larch-log.sh commit so breadcrumbs are not published on stall-before-PR paths Stall after Step 5 background scripts: tmpdir has breadcrumbs/*.ndjson but committed larch-logs/<run-id>/breadcrumbs/ is never created before tmpdir cleanup Call larch-log.sh commit best-effort in teardown before cleanup-tmpdir when post-merge sentinel absent
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/ship-pr.sh:1162-1168
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Breadcrumb publish failure inside larch-log commit is non-fatal at ship-pr pre-PR-create Pre-PR-create redaction failure: PR still created without committed breadcrumbs while raw streams sit in tmpdir Fail ship-pr step or add mandatory teardown commit on breadcrumb publish failure
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/ci-wait.sh:191-208
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan said larch_err for error-tier paths; code still uses larch_errf No functional regression on stream-unset harness; plan/doc mismatch only Align plan/docs or rename calls to larch_err if desired
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] code-quality: .claude/skills/bump-version/scripts/apply-bump.md:37-39
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Sibling doc describes old emit_breadcrumb routing Operators reading apply-bump.md get wrong stream contract guidance Update apply-bump.md for LARCH_BREADCRUMB_STREAM and --category=
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-design-log-publish.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Design publish breadcrumb redaction path is untested despite new design_publish_breadcrumbs wiring A PEM or tmpdir path in $DESIGN_TMPDIR/breadcrumbs/ could reach larch-logs/design/<run-id>/breadcrumbs/ unredacted or publish could leave a partial directory on failure without CI catching it Add harness cases for PEM/tmpdir redaction success and fail-closed symlink/redactor failure matching test-larch-log.sh patterns
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] apply-bump emit_breadcrumb lacks --category= while ship-pr inherits LARCH_BREADCRUMB_STREAM During backgrounded ship-pr Step 8 version-bump retries, retry breadcrumbs are dropped with WARN unknown-category=<missing> so operators see no structured retry progress in chat Add --category=retry and assert stream record in test-apply-bump.sh with LARCH_BREADCRUMB_STREAM set
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/test-breadcrumb-monitor.sh:261-286
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Test 7 does not assert poll-interval+1s latency bound from the plan Monitor could defer all stream output until done-sentinel without failing CI Record elapsed time from breadcrumb write to stdout emission; assert elapsed <= 2 when poll-interval=1
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/test-lib-quiet.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing tests for category enforcement when LARCH_BREADCRUMB_STREAM is set Invalid or missing categories could regress without unit-test signal Add stream-set cases asserting WARN and no record for missing/invalid category
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-ci-wait.sh:257-273
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Stream-set ci-wait tests do not cover pending/dot progress path Regression in emit_breadcrumb_stderr no-newline dot writes to stream during pending polls would not fail CI Add Case 6 with STUB_STATUSES=pending:pending:pass and assert c=wait-ci dot records in stream
- **Suggested revision**: Address the concern above.

### FINDING_19: code-quality: scripts/test-breadcrumb-monitor.sh:454-512
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Duplicate Test 14 labels for two different cases Harness failure output is ambiguous about which assertion failed Renumber partial-line retention test to 15 and subsequent tests accordingly
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration: scripts/test-refresh-run-logs.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No refresh-specific breadcrumb commit assertion refresh-run-logs.sh wiring to larch-log commit breadcrumbs could break without a targeted test Optional add refresh harness case with synthetic IMPLEMENT_TMPDIR/breadcrumbs and assert post-commit repo copy
- **Suggested revision**: Address the concern above.

### FINDING_21: security: scripts/breadcrumb-monitor.sh:91-95,203-231
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Stream path is validated only at startup; the poll loop reads via dd without re-checking symlink or path containment. A local attacker racing to replace the stream file with a symlink after validation could cause the monitor to read arbitrary file bytes into chat (PEM redaction reduces but does not eliminate leakage of other sensitive content). Re-validate before each read using canonical path containment (pwd -P) matching lib-larch-log.sh, or reject -L on every poll iteration.
- **Suggested revision**: Address the concern above.

### FINDING_22: security: scripts/lib-larch-log.sh:342-349
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Breadcrumb publish rejects symlinks but accepts hardlinks under the session breadcrumbs directory. A hardlink to a sensitive file outside the session tmpdir can be ingested and committed after partial redaction if content is not in the secrets/tmpdir families. Reject hardlinks whose target inode resolves outside the canonical session root, or read via O_NOFOLLOW-safe open before piping to redactors.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] security: SECURITY.md:127-141
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Documented residual risk: operational CI/diagnostic strings may be committed in redacted breadcrumbs. Public repos may expose internal CI URLs or hostnames even when PEM/token redaction succeeds. Operator discipline; optional future scrubber for URL/host patterns in breadcrumb commit pipeline.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security: scripts/lib-quiet.sh:176-181
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Pre-existing eval of captured EXIT trap body in larch_quiet__exit_combo. Malicious or malformed trap strings could theoretically execute unexpected shell if trap capture is ever poisoned. Replace eval with explicit trap chaining or a small whitelist of known trap handlers.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/ci-wait.sh:191-238
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Hard CI failure paths bypass the breadcrumb stream when LARCH_BREADCRUMB_STREAM is set Monitor shows wait-ci dots then stops with no terminal reason; bail cause is only on stderr or stdout KV Migrate timeout/ci-status/decide failure messages to emit_breadcrumb_stderr with --category=warn; add test-ci-wait stream-set bail coverage
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] apply-bump.sh emit_breadcrumb lacks --category while ship-pr.md requires inherited-stream vocabulary. During backgrounded ship-pr version bump with LARCH_BREADCRUMB_STREAM set, retry breadcrumbs are dropped (WARN unknown-category) and never surface in chat. Add --category=retry to the emit_breadcrumb callsite; add a stream-set assertion in test-apply-bump.sh.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/test-breadcrumb-monitor.sh:407-463
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Duplicate Test 14 labels for two distinct harness cases. Harness/docs inventory is ambiguous when triaging failures or comparing to the plan checklist. Renumber cases 14+ and sync scripts/test-breadcrumb-monitor.md.
- **Suggested revision**: Address the concern above.

