### FINDING_1: Unknown required-files TSV condition silently skipped in audit scan
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-shell-state-output.txt
- **Concern**: In `audit-scan-run.sh`, `_rf_condition_met` treats unknown `condition` tokens as non-met and the caller `continue`s, so the TSV row is never checked and `required-file-presence` can still pass. `verify-run-log-completeness.sh` treats unknown conditions as fatal. A typo or new condition token therefore fails verify/CI while the audit scan path can look healthy, hiding registry drift.
- **Suggested revision**: Align with the verifier: on unknown `condition`, emit a scan `error` NDJSON (or non-zero exit consistent with other registry-drift handling) instead of skipping the row.


### FINDING_12: `DISPATCH_OK` failure path omits `failure_see_phrase` in aggregate-findings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Operators lack a stable round-relative “See …” pointer for the dispatch-failed variant, unlike the non-zero dispatch path.
- **Suggested revision**: Optionally append `failure_see_phrase` for symmetry with the other branch.


### FINDING_14: Test 54 only asserts TMPDIR path redaction, not embedded stderr content
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: A regression could drop embedded stderr text while still redacting paths; the test would pass.
- **Suggested revision**: Assert an expected stderr substring remains present in the logged entry.


### FINDING_4: SKILL.md scan results prose omits informational outcomes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The scan results table/template text implies only pass/fail, so operators may mis-label informational rows (e.g. cache-freshness) when writing reports.
- **Suggested revision**: Update prose to explicitly include informational and other non-binary scan outcomes.


### FINDING_6: Tests 52–53 duplicate aggregate-findings helpers instead of exercising production
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-condition-sync-output.txt
- **Concern**: Inline `committed_ref` / `failure_see_phrase` (or equivalent) logic in tests can drift from `aggregate-findings.sh`; production wording or basename rules can change while tests stay green.
- **Suggested revision**: Source a small shared include used by production, add a dry-run/CLI hook that prints resolved phrases, or add an integration test that runs `aggregate-findings.sh` and asserts emitted warning text.


### FINDING_7: Missing test for cache-freshness empty `larch_version` fail branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: No harness coverage for the empty/missing `larch_version` failure path despite plan contract; regressions could turn that into skip/pass without CI signal.
- **Suggested revision**: Add a fixture test with empty/missing `larch_version` asserting `fail` result and expected detail.


### FINDING_8: New verifier exn-agg and glob paths lack dedicated harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: New `exn-agg-*` and glob `MISSING` branches in `verify-run-log-completeness.sh` are not exercised by `test-verify-run-log-completeness.sh`, so logic bugs can ship on CI shard 7.
- **Suggested revision**: Add positive/negative fixtures for `exn-agg-validate-fail`, `exn-agg-dispatch-fail`, and glob `MISSING` paths.


