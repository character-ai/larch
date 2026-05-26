### FINDING_1: code-quality: scripts/lib-larch-log.sh:301-309
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Empty breadcrumbs source directory deletes existing dest_dir Second larch-log commit with an empty session breadcrumbs/ dir removes previously published larch-logs/.../breadcrumbs/ from the worktree and can drop streams on the next commit On found_any=false skip publish without rm -rf dest_dir unless replacing with new redacted files; treat empty dir like absent source
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: scripts/breadcrumb-monitor.sh:209-222
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Final partial-line buffer is never emitted after done sentinel Background script exits after writing a breadcrumb record without trailing newline; monitor drops the last fragment After final stream read call larch_bm_emit_line on non-empty buf once
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/breadcrumb-monitor.sh:27-44
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated session-tmp path allowlist vs lib-larch-log.sh RESEARCH_TMPDIR or future tmpdir support may be added to only one copy Extract shared larch_session_tmp_allows_path helper used by monitor and log publish
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/breadcrumb-monitor.sh:209-222
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dead no-op buf blocks after flush removal Reader cannot tell whether intentional partial-line suppression or incomplete refactor Remove blocks or restore flush logic
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/cleanup/scripts/cleanup.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] --category= added outside plan stream-relevant scope Extra diff noise without stream-set behavior change Revert or document global category requirement in lib-quiet.md
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/lib-quiet.md:20
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] emit_breadcrumb docs omit stream-set category requirement Maintainers may omit --category= on new stream callsites Update emit_breadcrumb bullet to match lib-quiet.sh contract
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Uncategorized emit_breadcrumb in dev-only bump skill No stream in normal use; inconsistent style only Add --category=progress for consistency
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/breadcrumb-monitor.sh:209-222
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Residual buf is never flushed after done sentinel; round 1 replaced larch_bm_emit_line with no-op blocks. Background script appends a final larch:bc record without trailing newline then exits; monitor emits nothing for that tail. After final stream read call larch_bm_emit_line on non-empty buf (or normalize with a single trailing newline) per plan partial-line handling.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] apply-bump retry emit_breadcrumb lacks --category while running under ship-pr inherited LARCH_BREADCRUMB_STREAM During Step 8 origin/main race retries the breadcrumb is dropped and WARN unknown-category is emitted; monitor shows no c=retry progress test-apply-bump does not catch Add --category=retry and a stream-set harness assertion for c=retry
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/lib-larch-log.sh:301-308
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] empty session breadcrumbs/ with no ndjson deletes existing committed dest_dir Second commit or design publish with empty breadcrumbs/ removes larch-logs/<run-id>/breadcrumbs/ from the worktree Treat found_any=false as no-op without rm -rf dest_dir; add test-larch-log empty-dir regression
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-ci-wait.sh:245-261
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] no stream-set test for ci-wait bail/warn emit_breadcrumb_stderr paths Bail under background ci-wait could leak progress to stderr or omit c=warn from stream without failing CI Add STUB_STATUSES=fail or timeout case with stream set asserting c=warn and quiet stderr
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-ci-wait.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] no golden stderr byte comparison for stream-unset emit_breadcrumb_stderr fallback Regression could change dot-progress stderr formatting without failing functional grep checks Capture and assert stderr baseline on stream-unset runs
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-lib-quiet.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] missing producer test for uncategorized emit_breadcrumb when stream is set lib-quiet could stop warning on missing category while monitor tests still pass Add stream-set helper asserting WARN and no stream record
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-breadcrumb-monitor.sh:261-287
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] test 7 lacks poll-interval+1s latency assertion Slow or broken polling could still pass while violating streaming SLO Record time-to-first-line and assert <= poll-interval + 1
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-design-log-publish.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] no design publish breadcrumb redaction integration test design_publish_breadcrumbs wiring could regress independently of implement commit tests Add minimal DESIGN_TMPDIR/breadcrumbs PEM fixture and assert redacted design run log output
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] risk-integration: scripts/test-breadcrumb-monitor.sh:87-114
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] fixed sleep timing in monitor harness may flake on slow CI test 1/2 duration bounds can fail intermittently under load Prefer polling with capped timeout instead of hard sleeps
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] code-quality: scripts/test-breadcrumb-monitor-bash32.sh:22
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] bash32 harness does not compare cross-shell byte parity Plan wording overshoots what the script actually verifies Document as portability re-run only or add explicit output diff if needed
- **Suggested revision**: Address the concern above.

### FINDING_18: security: scripts/lib-quiet.sh:248-261
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] emit_breadcrumb mirrors raw text to FD3/stdout when LARCH_BREADCRUMB_STREAM is set, bypassing lib-redact-streaming.sh Background Family B script with stream + LARCH_QUIET_BREADCRUMBS=1 writes secrets or CI tokens to FD3; async task output shows them unredacted while monitor only redacts stream bytes When LARCH_BREADCRUMB_STREAM is set, skip FD3/stdout mirror in emit_breadcrumb; rely on breadcrumb-monitor.sh; add harness coverage
- **Suggested revision**: Address the concern above.

### FINDING_19: security: scripts/lib-quiet.sh:149-150
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Structured breadcrumb text= field is unescaped space-delimited text Forged or crafted stream line can deliver misleading progress text to orchestrator after redaction of PEM/token families only Encode text field structurally (JSON/length-prefix) and parse without awk token heuristics
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] security: scripts/lib-larch-log.sh:270-277
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Hardlinks in breadcrumbs/ not rejected at commit time Hardlink in session breadcrumbs could ingest out-of-directory content into committed redacted logs Reject hardlinks alongside symlinks before redaction pipeline
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

### FINDING_24: correctness: scripts/lib-larch-log.sh:293
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Committed breadcrumb redaction can read concurrently growing ndjson files. Refresh commit overlaps a still-running Family B writer; committed file may contain torn lines. Copy source to staging before redact or require done-sentinel before publish; document caller invariant.
- **Suggested revision**: Address the concern above.

### FINDING_25: architecture: scripts/lib-larch-log.sh:254-256
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Path-scope relies on exported session tmp env vars in the publishing process. Caller passes valid absolute breadcrumbs path but omits export IMPLEMENT_TMPDIR; publish fails closed. Derive allowed root from LARCH_LOG_ROOT parent when log-root matches */larch-logs.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/refresh-run-logs.sh:137-138
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Commit stderr suppressed on refresh path. Breadcrumb redaction fail-closed message never reaches operator; only REFRESH_COMMITTED=false. Propagate larch-log.sh stderr into refresh KEY=value output or larch_err.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Uncategorized emit_breadcrumb remains in apply-bump.sh. Future stream-set bump path would drop breadcrumbs silently. Add explicit --category= in a separate change.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: scripts/lib-larch-log.sh:301-308
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Empty session breadcrumbs/ directory deletes previously committed breadcrumbs/ in the repo worktree. A second larch-log commit with an existing but .ndjson-empty $IMPLEMENT_TMPDIR/breadcrumbs/ removes larch-logs/<run-id>/breadcrumbs/ before git add. Skip publish when no .ndjson files are found; do not rm -rf dest_dir; add test-larch-log coverage for empty directory.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] apply-bump retry breadcrumb lacks --category= while ship-pr inherits LARCH_BREADCRUMB_STREAM. Origin/main bump race retries emit WARN unknown-category and drop retry progress from the live breadcrumb stream. Add --category=retry (or warn) and assert stream record in test-apply-bump.sh.
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: scripts/ship-pr.sh:2160
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] ⚠-prefixed recovery message uses --category=stall contrary to plan emoji routing (⚠ → warn). Consumers filtering c=stall mis-label waterfall exhaustion handoff. Change to --category=warn or align message prefix with stall semantics.
- **Suggested revision**: Address the concern above.

