# Review Round 4

- Mode: `diff`
- 11 accepted, 6 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: code-quality: scripts/breadcrumb-monitor.sh:28-43,scripts/lib-larch-log.sh:236-265
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicated session-tmpdir guards with prefix vs canonical semantics Monitor accepts a path commit rejects after symlink/normalization (or opposite), yielding empty committed breadcrumbs despite live streams Factor one shared allowlist helper used by monitor and larch-log publish
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: scripts/implement-finalize.sh:1388-1434
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 18 teardown never invokes larch-log.sh commit so breadcrumbs are not published on stall-before-PR paths Stall after Step 5 background scripts: tmpdir has breadcrumbs/*.ndjson but committed larch-logs/<run-id>/breadcrumbs/ is never created before tmpdir cleanup Call larch-log.sh commit best-effort in teardown before cleanup-tmpdir when post-merge sentinel absent
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/test-design-log-publish.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Design publish breadcrumb redaction path is untested despite new design_publish_breadcrumbs wiring A PEM or tmpdir path in $DESIGN_TMPDIR/breadcrumbs/ could reach larch-logs/design/<run-id>/breadcrumbs/ unredacted or publish could leave a partial directory on failure without CI catching it Add harness cases for PEM/tmpdir redaction success and fail-closed symlink/redactor failure matching test-larch-log.sh patterns
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


### FINDING_22: security: scripts/lib-larch-log.sh:342-349
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Breadcrumb publish rejects symlinks but accepts hardlinks under the session breadcrumbs directory. A hardlink to a sensitive file outside the session tmpdir can be ingested and committed after partial redaction if content is not in the secrets/tmpdir families. Reject hardlinks whose target inode resolves outside the canonical session root, or read via O_NOFOLLOW-safe open before piping to redactors.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: scripts/ci-wait.sh:191-238
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Hard CI failure paths bypass the breadcrumb stream when LARCH_BREADCRUMB_STREAM is set Monitor shows wait-ci dots then stops with no terminal reason; bail cause is only on stderr or stdout KV Migrate timeout/ci-status/decide failure messages to emit_breadcrumb_stderr with --category=warn; add test-ci-wait stream-set bail coverage
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: scripts/test-breadcrumb-monitor.sh:407-463
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Duplicate Test 14 labels for two distinct harness cases. Harness/docs inventory is ambiguous when triaging failures or comparing to the plan checklist. Renumber cases 14+ and sync scripts/test-breadcrumb-monitor.md.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/lib-larch-log.sh:342-371
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Commit walker only ingests *.ndjson Non-ndjson files in session breadcrumbs/ are dropped silently on publish Glob all regular files per plan or document and test ndjson-only contract
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: scripts/test-breadcrumb-monitor.sh:454-482
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate Test 14 labels and mismatched alloc_sentinels prefixes CI failure messages point at the wrong scenario Renumber tests and align alloc_sentinels prefixes
- **Suggested revision**: Address the concern above.


