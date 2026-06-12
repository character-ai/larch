### OOS_3: [OUT_OF_SCOPE] Golden fixtures duplicate shipped default rate table
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Golden fixtures duplicate default pricing lines outside the intended authority and snapshot. Future pricing changes can drift, fail golden diffs, or mask default-rate changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Scrub legend from fixtures or inject explicit test-only rates.
  - From codex-specialist-edge-cases-output.txt: Generate these fixtures with explicit test-only env rates or scrub the rate legend placeholders.
  - From cursor-specialist-testing-output.txt: Scrub fixture rate legends or drive them from explicit test env injection.
  - From codex-specialist-testing-output.txt: Regenerate these fixtures with explicit non-default rates or scrub the rate legend, leaving python/test_report_tokens_cost.py as the only default-rate snapshot.


### OOS_4: [OUT_OF_SCOPE] Unknown TOOL sidecars split NDJSON and active-ledger behavior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dedup-robustness-output.txt, dyn-pricing-authority-output.txt
- **Severity**: latent
- **Concern**: Unknown or malformed `TOOL=` values can append rows to NDJSON while `record_vendor_from_sidecar` silently skips active-ledger recording. Live costs can under-report with no warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Log or warn on unknown vendor before returning.
  - From dyn-dedup-robustness-output.txt: Emit a stderr warning (and optionally append to `execution-issues.md`) when `record_vendor_from_sidecar` skips a non-zero sidecar because of unknown vendor, matching the warn-not-fail contract. Add a test with a malformed `TOOL=` sidecar that asserts the warning and that NDJSON vs active-ledger behavior is documented.
  - From dyn-pricing-authority-output.txt: Share one post-parse gate (valid vendor set) used by both append and active-ledger paths, or have `append_token_record_from_sidecar()` delegate to the same helper as `record_vendor_from_sidecar()` so both surfaces stay aligned.


