### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_result.py:245-277
- **Concern**: Result-env CI projection must not mutate the JSON serialization dict (G-Wire-1). Scenario: The plan derives result-env rows from the same redacted payload used for JSON while also requiring always-on CI rows (FAILED_JOBS_COUNT and CI_ERRORS_FILE even when zero/empty) and byte-stable JSON for no-flag callers. Today emit_result only injects failed_jobs_count into the payload when it is positive. Adding always-on CI keys to the shared dict before json.dumps would change JSON bytes and break existing stdout consumers/tests.
- **Proposed resolution**: In emit_result, build JSON from the current redacted ShipResult payload with unchanged conditional CI injection, then build a separate result-env row map (or copy) that applies dispatch_ship pairing rules: always emit FAILED_JOBS_COUNT and CI_ERRORS_FILE, emit CI_ERRORS_DISTILL_CLASS only when the file value is empty, without altering the JSON-bound dict.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_result.py
- **Concern**: Result-env CI rows cannot come only from the JSON-bound sparse payload. Scenario: The JSON path keeps omitting empty/zero CI fields (`if ci_errors_file:`, `if failed_jobs_count:`), while route-exit always needs `CI_ERRORS_FILE`, `FAILED_JOBS_COUNT`, and conditional `CI_ERRORS_DISTILL_CLASS`. A naive projection from the JSON payload drops `FAILED_JOBS_COUNT=0` and empty digest rows, so piece 2 cannot replace the stdout sniffer.
- **Proposed resolution**: Build result-env CI rows from `emit_result`'s `ci_errors_file` / `ci_errors_distill_class` / `failed_jobs_count` arguments using the same pairing rules as `dispatch_ship._write_ship_route_handoff` (always file + count; class only when file empty). Keep JSON serialization unchanged.

### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:2156-2161; python/larch/bgjob/model.py:127-143
- **Concern**: The accepted path-prevalidation fix remains incomplete for lexical `..` paths. Scenario: An absolute in-root path such as `<tmpdir>/../<tmpdir-name>/result.env` resolves under the tmpdir, but the validator’s lexical parent loop may never reach the resolved root and can hang at `/`
- **Proposed resolution**: Reject result-env paths containing `..` before calling the validator, and add this case to the planned preflight tests
