# Review Round 3

- Mode: `diff`
- 5 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Partial sidecar ingestion can duplicate token records
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-arch-ingestion-output.txt, dyn-pricing-rates-output.txt
- **Severity**: important
- **Concern**: `ingest_launcher_token_sidecar` can return success after only one ingestion leg succeeds, while `seen` is updated only after full dual success. Retries can duplicate `token-report.ndjson` rows or active-ledger rows while leaving the other accounting path incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Track append and vendor ingest separately in seen logic, or retry vendor-only without re-appending.
  - From cursor-specialist-edge-cases-output.txt: Mark seen when either ingest succeeds or return False unless both succeed; document partial state explicitly
  - From cursor-specialist-edge-cases-output.txt: Add seen on first successful sub-ingest or make ledger append idempotent per sidecar fingerprint
  - From cursor-specialist-testing-output.txt: Mark seen after successful append-record or treat partial ingest as non-success for dedup; add a test blocking second append-record on the same path.
  - From dyn-arch-ingestion-output.txt: Track append and vendor completion separately (e.g. `seen_append` / `seen_vendor`, or mark `seen` after each successful sub-step and skip only the leg that already succeeded), or make `append_token_record_from_sidecar` idempotent on `(tool, raw, totals, model)` before re-append.
  - From dyn-arch-ingestion-output.txt: Use the same per-leg `seen` tracking; return a small status enum or require both legs OK before returning success; only add to `seen` when the legs that actually succeeded are recorded so retries complete missing work without redoing successful legs.
  - From dyn-pricing-rates-output.txt: Return `True` only when both paths succeed (or when `implement_tmpdir` is unset and append alone is intended). Mark `seen` after append-only when no active ledger is requested. On vendor failure after a successful append, either roll back the NDJSON row or record a per-path partial state so retries cannot double-append.


### FINDING_10: Launcher harnesses miss TOKEN_RECORD, MODEL, and stale cleanup coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Launcher harnesses were not updated for sidecar path, model metadata, and stale sidecar cleanup behavior. Reused outputs after preflight failure can leave stale usage for later ingestion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add plan-specified fixtures to test-launch-codex-exec.sh, test-launch-codex-ci.sh, test-launch-codex-drafter.sh, test-launch-cursor-ci.sh, and test-lib-external-launcher-common.sh.


### FINDING_11: Python lint-fix model metadata lacks tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `checks.py` threads resolved Codex model metadata through direct ledger recording, but `python/test_checks.py` does not cover the launch argv or recording helper shape. Regressions can drop model metadata silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test_checks.py cases for model args in launch argv and codex_launcher_record_usage_from_events invocation shape.


### FINDING_12: Display-rate env ladder lacks alias coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required parametrized display-rate coverage for every alias tuple is missing. Legacy aliases can stop resolving and silently fall back to table defaults.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest.mark.parametrize cases over each display_rates ladder tuple and legacy alias.


### FINDING_9: Ship-pr recovery ingestion lacks focused regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Ship-pr recovery waterfall and CI-fix sidecar ingestion lack focused tests. Regressions can drop active-ledger ingestion or dedup while NDJSON append still succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add python/test_ship.py or scripts/test-dispatch-with-waterfall.sh cases stubbing tier sidecars; assert append-record and record-vendor-sidecar run once with IMPLEMENT_TMPDIR exported and dedup on repeated paths.


