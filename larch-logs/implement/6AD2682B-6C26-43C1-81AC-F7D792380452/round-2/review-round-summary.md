# Review Round 2

- Mode: `diff`
- 10 accepted, 13 rejected (12 exonerated)

## Accepted Findings

### FINDING_1: code-quality: scripts/lib-larch-log.sh:301-309
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Empty breadcrumbs source directory deletes existing dest_dir Second larch-log commit with an empty session breadcrumbs/ dir removes previously published larch-logs/.../breadcrumbs/ from the worktree and can drop streams on the next commit On found_any=false skip publish without rm -rf dest_dir unless replacing with new redacted files; treat empty dir like absent source
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: scripts/lib-larch-log.sh:301-308
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] empty session breadcrumbs/ with no ndjson deletes existing committed dest_dir Second commit or design publish with empty breadcrumbs/ removes larch-logs/<run-id>/breadcrumbs/ from the worktree Treat found_any=false as no-op without rm -rf dest_dir; add test-larch-log empty-dir regression
- **Suggested revision**: Address the concern above.


### FINDING_18: security: scripts/lib-quiet.sh:248-261
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] emit_breadcrumb mirrors raw text to FD3/stdout when LARCH_BREADCRUMB_STREAM is set, bypassing lib-redact-streaming.sh Background Family B script with stream + LARCH_QUIET_BREADCRUMBS=1 writes secrets or CI tokens to FD3; async task output shows them unredacted while monitor only redacts stream bytes When LARCH_BREADCRUMB_STREAM is set, skip FD3/stdout mirror in emit_breadcrumb; rely on breadcrumb-monitor.sh; add harness coverage
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: scripts/breadcrumb-monitor.sh:209-222
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Final partial-line buffer is never emitted after done sentinel Background script exits after writing a breadcrumb record without trailing newline; monitor drops the last fragment After final stream read call larch_bm_emit_line on non-empty buf once
- **Suggested revision**: Address the concern above.


### FINDING_21: architecture: scripts/breadcrumb-monitor.sh:209-222
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Partial-line buffer is discarded at shutdown instead of flushed. Background script killed mid-write leaves an incomplete larch:bc record in buf; monitor exits 0 after done sentinel but never surfaces that progress line (regression vs earlier flush in 47fecebc). On exit call larch_bm_emit_line for non-empty buf or emit a synthetic warn truncation record; add harness case for incomplete final line at done.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: scripts/lib-larch-log.sh:301-308
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Empty session breadcrumbs/ directory deletes existing committed breadcrumbs/ in the worktree. Second commit or refresh when tmpdir breadcrumbs/ exists but has no *.ndjson removes larch-logs/<run-id>/breadcrumbs/ despite prior successful publish. Skip rm -rf dest_dir when found_any is false; only replace when staging has files; add test-larch-log empty-dir preservation case.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: scripts/lib-larch-log.sh:293-295
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Redaction failure removes destination breadcrumbs before aborting. Transient redact-secrets failure during refresh deletes worktree breadcrumbs/ then fails commit, leaving deleted paths in git status. Do not rm -rf dest_dir on redaction failure; clean staging only or restore dest from last good tree.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: scripts/lib-larch-log.sh:301-308
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Empty session breadcrumbs/ directory deletes previously committed breadcrumbs/ in the repo worktree. A second larch-log commit with an existing but .ndjson-empty $IMPLEMENT_TMPDIR/breadcrumbs/ removes larch-logs/<run-id>/breadcrumbs/ before git add. Skip publish when no .ndjson files are found; do not rm -rf dest_dir; add test-larch-log coverage for empty directory.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: scripts/lib-quiet.md:20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] emit_breadcrumb docs omit stream-set category requirement Maintainers may omit --category= on new stream callsites Update emit_breadcrumb bullet to match lib-quiet.sh contract
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/breadcrumb-monitor.sh:209-222
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Residual buf is never flushed after done sentinel; round 1 replaced larch_bm_emit_line with no-op blocks. Background script appends a final larch:bc record without trailing newline then exits; monitor emits nothing for that tail. After final stream read call larch_bm_emit_line on non-empty buf (or normalize with a single trailing newline) per plan partial-line handling.
- **Suggested revision**: Address the concern above.


