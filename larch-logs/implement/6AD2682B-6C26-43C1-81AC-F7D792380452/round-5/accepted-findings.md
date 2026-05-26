### FINDING_12: risk-integration: scripts/lib-larch-log.sh:391-430
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Publisher commits all regular breadcrumb files while docs say *.ndjson only Non-ndjson files in session breadcrumbs/ would be committed redacted; design harness requires .quiet sidecar contrary to run-logs tree Align publisher filter, docs, and tests on ndjson-only or documented multi-file publish
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/test-refresh-run-logs.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Refresh path breadcrumb commit untested because larch-log.sh is fully stubbed larch_log_breadcrumb_source_dir regression on refresh-run-logs would not fail CI Add integration case with real or partial larch-log commit and PEM breadcrumb fixture
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/test-larch-log.sh:280-313
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Only redact-secrets stage failure tested for breadcrumb commit fail-closed redact-tmpdir-paths.sh failure might still publish partial breadcrumbs without test coverage Stub stage-1 failure and assert no larch-logs/.../breadcrumbs/ directory
- **Suggested revision**: Address the concern above.


### FINDING_20: security: scripts/lib-larch-log.sh:391-431
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Commit walker publishes every regular file in breadcrumbs/ including quiet logs and monitor sidecars not just NDJSON streams On log flush a public repo gains redacted *.quiet files containing full Family B stdout/stderr plus done/status/surfaced and *.bc-offset state under larch-logs/.../breadcrumbs/ increasing leakage beyond structured breadcrumb NDJSON Allowlist only *.ndjson stream basenames for commit; keep quiet and control files tmpdir-only; align SECURITY.md and run-logs docs with the chosen boundary
- **Suggested revision**: Address the concern above.


### FINDING_22: security: scripts/breadcrumb-monitor.sh:117-136
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Non-larch:bc stream lines bypass category enforcement and still emit to stdout after redaction Malicious or malformed content appended to the stream can reach the orchestrator chat context as if it were progress output Reject non-structured lines or parse and validate records before emission
- **Suggested revision**: Address the concern above.


### FINDING_25: architecture: scripts/lib-larch-log.sh:391-431
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Breadcrumb commit publishes all regular files in session breadcrumbs/ including monitor coupling sidecars Real /implement runs place .done .quiet .status .surfaced and .bc-offset next to .ndjson streams under IMPLEMENT_TMPDIR/breadcrumbs/; commit copies them into larch-logs/.../breadcrumbs/ Filter publish to *.ndjson (or larch:bc streams only); skip coupling/monitor files; add test with colocated sidecars
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: scripts/ci-wait.sh:249
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] larch_errf newline bypasses breadcrumb stream when stream is set Monitor-mode ci-wait can emit stray stderr newline contrary to stream-quiet contract Route newline through emit_breadcrumb_stderr or suppress when LARCH_BREADCRUMB_STREAM is set
- **Suggested revision**: Address the concern above.


### FINDING_29: risk-integration: scripts/refresh-run-logs.sh:137-140
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Commit stderr discarded on breadcrumb redaction failure Operators see REFRESH_COMMITTED=false without ERROR= naming failing file/stage Capture and surface redacted commit stderr on failure
- **Suggested revision**: Address the concern above.


### FINDING_33: correctness: scripts/lib-larch-log.sh:391-431
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] larch_log_publish_breadcrumbs_shared publishes every regular file in session breadcrumbs/ but docs and tests expect only *.ndjson A real /implement flush can commit redacted .done/.quiet/.status/.surfaced sidecars alongside stream ndjson contrary to docs/run-logs.md and test-larch-log.sh Filter the publish walker to *.ndjson (or an explicit allow-list) and extend test-larch-log.sh with sidecar files present in the source directory
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: scripts/ship-pr.sh:2160-2161
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] stall category on a warning-prefixed recovery handoff line Consumers filtering c=stall may treat waterfall exhaustion like a hard stall instead of warn/escalate handoff Reclassify line 2160 to warn or escalate per the emoji routing table
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/ci-wait.sh:249
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] larch_errf newline still runs when breadcrumb stream is set Stream-set ci-wait completion writes a stray stderr newline while tests only strip newlines before compare Skip or relocate the separator when LARCH_BREADCRUMB_STREAM is set
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: docs/run-logs.md:381-382 vs scripts/lib-larch-log.sh:391-431
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] run-logs tree says only *.ndjson but publish commits every regular file in breadcrumbs/ Implement run commits .quiet/.done sidecars alongside streams; operators reading run-logs.md underestimate published surface Align docs and publish filter, or document sidecar commit in run-logs and tests
- **Suggested revision**: Address the concern above.


