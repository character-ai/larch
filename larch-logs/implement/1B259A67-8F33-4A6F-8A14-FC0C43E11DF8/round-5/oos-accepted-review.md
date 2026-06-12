### OOS_8: [OUT_OF_SCOPE] relevant-checks misses lint-fix-loop harness mapping
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Edits to `scripts/lint-fix-loop.sh` may not trigger `test-lint-fix-loop.sh` through `scripts/relevant-checks.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add lint-fix-loop.sh mapping to test-lint-fix-loop in relevant-checks.sh


### OOS_9: [OUT_OF_SCOPE] Python lint-fix path drops sidecar fan-out
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: The Python ship lint-fix path reads the wrong events path and does not ingest `codex.log.token-record`, so `codex_lint_fix` usage can miss the active ledger and/or `token-report.ndjson`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After _run_codex, ingest run_dir/codex.log.token-record like bash lint-fix-loop.sh (append-record + record-vendor-sidecar or ingest_launcher_token_sidecar). Remove or fix the dead events hook; avoid double-counting sidecar plus direct record.


