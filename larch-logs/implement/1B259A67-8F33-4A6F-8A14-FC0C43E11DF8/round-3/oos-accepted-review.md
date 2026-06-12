### OOS_5: [OUT_OF_SCOPE] Python lint-fix records active ledger only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-arch-ingestion-output.txt
- **Severity**: important
- **Concern**: Python lint-fix records Codex usage directly to the active ledger but does not append the launcher `.token-record` to `token-report.ndjson`. Committed run-log token batches can omit `codex_lint_fix` rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Call the shared sidecar ingestion helper after _run_codex, or ingest codex.log.token-record once instead of direct record-vendor.
  - From dyn-arch-ingestion-output.txt: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] Golden fixtures duplicate shipped default rates
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-pricing-rates-output.txt
- **Severity**: important
- **Concern**: Golden fixtures embed another copy of shipped default rates in rendered rate legends. Future rate changes can break golden tests and conflict with the intended single-authority rate snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Scrub or remove the rates legend from golden fixtures; keep defaults pinned only in test_display_rates_shipped_defaults_snapshot.
  - From dyn-pricing-rates-output.txt: Address the concern above.


