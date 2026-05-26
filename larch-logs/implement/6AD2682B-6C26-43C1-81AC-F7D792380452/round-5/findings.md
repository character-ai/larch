### FINDING_1: code-quality: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] apply-bump.sh emit_breadcrumb lacks --category= while ship-pr inherits LARCH_BREADCRUMB_STREAM During Step 8 bump races the monitor shows WARN unknown-category and drops apply-bump retry breadcrumbs so operators lose version-bump retry visibility in chat Add --category=retry (or progress) on line 195 and extend test-apply-bump.sh with a stream-set assertion
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/lib-quiet.sh:210-297
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate --category= parsing in emit_breadcrumb and emit_breadcrumb_stderr Future category-option changes must be edited twice increasing drift risk Extract a shared larch_quiet_shift_bc_category helper used by both emitters
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-breadcrumb-monitor.sh:44-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] make_monitor_fixture copies unused larch-log-batches.sh Fixture trees carry a misleading dependency and extra file I/O per test Remove the larch-log-batches.sh copy from make_monitor_fixture
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/ship-pr.sh:2160-2161
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] stall category on a warning-prefixed recovery handoff line Consumers filtering c=stall may treat waterfall exhaustion like a hard stall instead of warn/escalate handoff Reclassify line 2160 to warn or escalate per the emoji routing table
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/ci-wait.sh:282
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] suspend message uses warn instead of plan network-flake category Structured consumers cannot distinguish suspend/network-flake from generic warnings Use --category=network-flake or document warn as intentional in ci-wait.md
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh (and related skill scripts)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Category migration outside stream-relevant inventory Wider diff than the plan’s ~54 stream callsites required No action required unless minimizing diff radius is a priority
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] apply-bump emit_breadcrumb lacks --category= on retry path ship-pr runs with LARCH_BREADCRUMB_STREAM set; apply-bump retry emits WARN unknown-category and drops breadcrumb from stream Add --category=retry (or progress) and add stream-set harness coverage
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/ci-wait.sh:249
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] larch_errf newline still runs when breadcrumb stream is set Stream-set ci-wait completion writes a stray stderr newline while tests only strip newlines before compare Skip or relocate the separator when LARCH_BREADCRUMB_STREAM is set
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: docs/run-logs.md:381-382 vs scripts/lib-larch-log.sh:391-431
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] run-logs tree says only *.ndjson but publish commits every regular file in breadcrumbs/ Implement run commits .quiet/.done sidecars alongside streams; operators reading run-logs.md underestimate published surface Align docs and publish filter, or document sidecar commit in run-logs and tests
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] architecture: scripts/test-larch-log.sh:218-221 vs scripts/test-design-log-publish.sh:354-389
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Conflicting harness expectations for breadcrumb sidecars test-larch-log expects no foo.quiet; design-log-publish expects stream.quiet committed Reconcile harness contracts with chosen publish policy
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Uncategorized emit_breadcrumb on bump-retry path under inherited LARCH_BREADCRUMB_STREAM During background ship-pr with stream set, origin/main race retries emit WARN unknown-category and no c=retry/progress record reaches the monitor Add --category=retry (or progress) and a stream-set harness assertion in test-apply-bump.sh or test-ship-pr.sh
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/lib-larch-log.sh:391-430
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Publisher commits all regular breadcrumb files while docs say *.ndjson only Non-ndjson files in session breadcrumbs/ would be committed redacted; design harness requires .quiet sidecar contrary to run-logs tree Align publisher filter, docs, and tests on ndjson-only or documented multi-file publish
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: repo-wide
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No static enforcement that emit_breadcrumb includes --category= in stream-relevant scripts Future edit without --category= passes CI until runtime stream is set and breadcrumbs silently drop Add lint target grepping production scripts for uncategorized emit_breadcrumb
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-refresh-run-logs.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Refresh path breadcrumb commit untested because larch-log.sh is fully stubbed larch_log_breadcrumb_source_dir regression on refresh-run-logs would not fail CI Add integration case with real or partial larch-log commit and PEM breadcrumb fixture
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-larch-log.sh:280-313
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Only redact-secrets stage failure tested for breadcrumb commit fail-closed redact-tmpdir-paths.sh failure might still publish partial breadcrumbs without test coverage Stub stage-1 failure and assert no larch-logs/.../breadcrumbs/ directory
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/test-lib-quiet.sh:141-155
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No emit_breadcrumb_stderr no-newline larch_errf fallback test Dot-progress stderr byte contract relies on indirect ci-wait coverage Add stream-unset/stream-set test for emit_breadcrumb_stderr --category=wait-ci "."
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/test-breadcrumb-monitor.sh:265-290
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test 7 does not bound stream growth latency to poll-interval plus 1s Slow monitor poll would not be detected by current end-state grep only Record time before append; assert output within 2s with poll-interval=1
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration: acceptance criteria
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Manual /implement E2E breadcrumb smoke not automatable CI cannot verify chat streaming during ship-pr/ci-wait/collect-agent-results Keep as documented operator acceptance step
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] risk-integration: scripts/test-breadcrumb-monitor-bash32.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Bash32 harness only re-execs full suite Bash-3.2-specific divergence would surface only as full harness failure Acceptable; optional split of bash32-only cases if flakes appear
- **Suggested revision**: Address the concern above.

### FINDING_20: security: scripts/lib-larch-log.sh:391-431
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Commit walker publishes every regular file in breadcrumbs/ including quiet logs and monitor sidecars not just NDJSON streams On log flush a public repo gains redacted *.quiet files containing full Family B stdout/stderr plus done/status/surfaced and *.bc-offset state under larch-logs/.../breadcrumbs/ increasing leakage beyond structured breadcrumb NDJSON Allowlist only *.ndjson stream basenames for commit; keep quiet and control files tmpdir-only; align SECURITY.md and run-logs docs with the chosen boundary
- **Suggested revision**: Address the concern above.

### FINDING_21: security: scripts/lib-larch-log.sh:391-425
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Symlink check before read is subject to TOCTOU A race can turn a validated breadcrumb path into a symlink to host files before redact-tmpdir-paths/redact-secrets reads it Open via no-follow or copy-through staging after verifying a stable regular file identity
- **Suggested revision**: Address the concern above.

### FINDING_22: security: scripts/breadcrumb-monitor.sh:117-136
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Non-larch:bc stream lines bypass category enforcement and still emit to stdout after redaction Malicious or malformed content appended to the stream can reach the orchestrator chat context as if it were progress output Reject non-structured lines or parse and validate records before emission
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] security: scripts/lib-quiet.sh:176-181
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] eval of prior EXIT trap in larch_quiet__exit_combo Malicious trap body in a compromised sourced script could execute arbitrary shell on exit Replace eval with a fixed trap chain or allowlisted trap dispatch
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security: scripts/ci-wait.sh:255-257
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] External CI strings in printf formats via emit_breadcrumb_stderr Unusual % sequences in BAIL_REASON could corrupt formatted output (inherited from larch_errf) Escape % in externally sourced strings or use fixed format with %s-only arguments
- **Suggested revision**: Address the concern above.

### FINDING_25: architecture: scripts/lib-larch-log.sh:391-431
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Breadcrumb commit publishes all regular files in session breadcrumbs/ including monitor coupling sidecars Real /implement runs place .done .quiet .status .surfaced and .bc-offset next to .ndjson streams under IMPLEMENT_TMPDIR/breadcrumbs/; commit copies them into larch-logs/.../breadcrumbs/ Filter publish to *.ndjson (or larch:bc streams only); skip coupling/monitor files; add test with colocated sidecars
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Uncategorized emit_breadcrumb under inherited LARCH_BREADCRUMB_STREAM from ship-pr Origin/main bump race retries during backgrounded ship-pr drop breadcrumb records and only WARN on stderr Add --category=retry (or warn) on apply-bump emit_breadcrumb; extend test-apply-bump if needed
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/larch-log.sh:127-142
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Missing/empty breadcrumb source skips publish and preserves prior committed breadcrumbs Tmpdir breadcrumbs cleared before final commit leaves stale larch-logs/.../breadcrumbs/ while other run artifacts update Document behavior or warn/replace when committed breadcrumbs exist but source is empty
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: scripts/ci-wait.sh:249
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] larch_errf newline bypasses breadcrumb stream when stream is set Monitor-mode ci-wait can emit stray stderr newline contrary to stream-quiet contract Route newline through emit_breadcrumb_stderr or suppress when LARCH_BREADCRUMB_STREAM is set
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: scripts/refresh-run-logs.sh:137-140
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Commit stderr discarded on breadcrumb redaction failure Operators see REFRESH_COMMITTED=false without ERROR= naming failing file/stage Capture and surface redacted commit stderr on failure
- **Suggested revision**: Address the concern above.

### FINDING_30: architecture: scripts/breadcrumb-monitor.sh:103-115
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Rate cap permanently drops breadcrumb lines Burst progress during ship-pr/Step 5 can lose stall or escalate messages Defer capped lines or exempt high-severity categories from cap
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] architecture: docs/run-logs.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] REVIEW/RESEARCH breadcrumb streams lack commit publish path Review/research monitor streams never land in committed larch-logs breadcrumbs/ Add review/research publish callers if parity is desired
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] apply-bump.sh still calls emit_breadcrumb without --category= while ship-pr inherits LARCH_BREADCRUMB_STREAM During backgrounded ship-pr version-bump retries the monitor never receives structured retry breadcrumbs; stderr may only show WARN unknown-category=<missing> Add --category=retry on the apply-bump emit_breadcrumb call and add a stream-set regression in test-apply-bump.sh
- **Suggested revision**: Address the concern above.

### FINDING_33: correctness: scripts/lib-larch-log.sh:391-431
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] larch_log_publish_breadcrumbs_shared publishes every regular file in session breadcrumbs/ but docs and tests expect only *.ndjson A real /implement flush can commit redacted .done/.quiet/.status/.surfaced sidecars alongside stream ndjson contrary to docs/run-logs.md and test-larch-log.sh Filter the publish walker to *.ndjson (or an explicit allow-list) and extend test-larch-log.sh with sidecar files present in the source directory
- **Suggested revision**: Address the concern above.

