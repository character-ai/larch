### FINDING_1: code-quality: scripts/breadcrumb-monitor.sh:139-142
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Category vocabulary duplicated instead of reusing larch_quiet_bc_valid_category from lib-quiet.sh Adding a new breadcrumb category updates lib-quiet.sh but monitor keeps dropping records until its separate case is updated Call larch_quiet_bc_valid_category from larch_bm_emit_line
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/test-ci-wait.sh:125-261
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No byte-for-byte stderr regression for stream-unset ci-wait after emit_breadcrumb_stderr migration Wait-loop stderr formatting (no-newline dots) can regress while stdout/poll-count assertions still pass Add golden stderr baseline for pending-then-pass without LARCH_BREADCRUMB_STREAM
- **Suggested revision**: Address the concern above.


### FINDING_12: security: scripts/lib-larch-log.sh:209-257
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Breadcrumb publish path scope uses prefix-only case matching without rejecting .. components unlike breadcrumb-monitor.sh. Exporting LARCH_BREADCRUMB_SOURCE_DIR=$IMPLEMENT_TMPDIR/../other/breadcrumbs can pass larch_log_breadcrumbs_under_session_tmp and commit redacted streams from another directory into larch-logs/<run-id>/breadcrumbs/. Reject .. in the full source path; canonicalize under the active session *_TMPDIR; add a test-larch-log.sh traversal case.
- **Suggested revision**: Address the concern above.


### FINDING_17: architecture: scripts/lib-larch-log.sh:305-315
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Breadcrumb publish rm -rf dest_dir before mv loses data if mv fails After a successful first publish refresh-run-logs re-commit can rm committed breadcrumbs then fail mv leaving no breadcrumbs/ in the repo worktree Publish via staging rename without deleting dest until mv succeeds; add test forcing mv failure after first publish
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/larch-log.md:109-111
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] larch-log.md still claims redaction failure removes committed breadcrumbs/ directory Operators/readers expect prior committed breadcrumbs to disappear on retry failure; code and tests now preserve them Update docs to match preserve-on-failure staging semantics
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: scripts/test-breadcrumb-monitor.sh:432-454
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate harness label Test 13 for two different cases CI failure output ambiguous about which assertion failed Renumber test section labels uniquely
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/lib-larch-log.sh:217-257
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Breadcrumb path-scope checks require *_TMPDIR env vars but source dir is derived only from --log-root larch-log.sh commit with --log-root $X/larch-logs and $X/breadcrumbs populated fails exit 3 when IMPLEMENT_TMPDIR is unset Also allow session_root derived from log-root in larch_log_breadcrumbs_under_session_tmp, or hard-require export in all commit callers plus a regression test
- **Suggested revision**: Address the concern above.


