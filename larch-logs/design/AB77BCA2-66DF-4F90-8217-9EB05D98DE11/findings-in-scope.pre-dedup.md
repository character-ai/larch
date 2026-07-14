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



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_result.py
- **Concern**: [SCOPE-REDUCTION] Blanket uppercase key rendering drifts from route-exit wire names. Scenario: `dispatch_ship` handoff emits lowercase ledger keys such as `ledger_ready=true` (see `test_implement_dispatch.py`), while repair/CI keys are uppercase. Uniform uppercasing of JSON keys would emit `LEDGER_READY` and break parity with established handoff vocabulary piece 2 must consume.
- **Proposed resolution**: Name an explicit mixed-case key map aligned with `dispatch_ship` (`FAILED_RUN_ID`, lowercase `ledger_*`, uppercase repair/CI keys, plus documented `outcome` casing) instead of uppercasing every JSON field.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/ship.py
- **Concern**: [SCOPE-REDUCTION] Prefer the established `--merge-result-env` child flag over `--result-env-path`. Scenario: `bgjob.adapt` and every other implement child (`dispatch_commit_route.py`, `step-8-ship.sh`) wire `--merge-result-env`. A new flag name forces piece 2 to add translation glue or fork adapt conventions.
- **Proposed resolution**: Add `--merge-result-env` to `ship pr` (accept the validated path from adapt); keep `--result-env-path` out unless both are required as aliases for one release. **1. CI projection must bypass the JSON-sparse payload (FINDING_3 still open).** `emit_result()` only adds CI fields to the payload when truthy: if ci_errors_file: payload["ci_errors_file"] = ci_errors_file if ci_errors_distill_class: payload["ci_errors_distill_class"] = ci_errors_distill_class if failed_jobs_count: payload["failed_jobs_count"] = failed_jobs_count Route-exit always emits `FAILED_JOBS_COUNT` and `CI_ERRORS_FILE`, with `CI_ERRORS_DISTILL_CLASS` only when the file is empty (`dispatch_ship.py:362-374`). The plan's mirror rule is right, but "build from the redacted JSON payload" still conflicts with it. The env writer should take the raw CI arguments and apply pairing rules directly. **2. Mixed-case keys, not uniform uppercase.** Handoff tests pin lowercase ledger keys (`ledger_ready=true`). Repair and CI keys stay uppercase. Blanket uppercasing would change the wire shape piece 2 inherits. **3. Use `--merge-result-env`.** That matches `bgjob.adapt` and `step-8-ship.sh` today; a new flag name is extra surface for piece 2 with no functional gain. Accepted ledger items (prevalidation, fail-closed write ordering, CI pairing intent) look adequately covered. I am not re-raising rejected FINDING_2 or OOS duplicate-validation items.



### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:2156-2161; python/larch/bgjob/model.py:127-143
- **Concern**: The accepted path-prevalidation fix remains incomplete for lexical `..` paths. Scenario: An absolute in-root path such as `<tmpdir>/../<tmpdir-name>/result.env` resolves under the tmpdir, but the validator’s lexical parent loop may never reach the resolved root and can hang at `/`
- **Proposed resolution**: Reject result-env paths containing `..` before calling the validator, and add this case to the planned preflight tests



