### [Plan Review] FINDING_1

### FINDING_1: Preserve JSON serialization while projecting complete CI result-env rows
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: Result-env CI rows must be projected independently from the JSON-bound sparse payload. JSON serialization must remain unchanged, while result-env output must always include `FAILED_JOBS_COUNT` and `CI_ERRORS_FILE`, plus `CI_ERRORS_DISTILL_CLASS` only when the file value is empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In emit_result, build JSON from the current redacted ShipResult payload with unchanged conditional CI injection, then build a separate result-env row map (or copy) that applies dispatch_ship pairing rules: always emit FAILED_JOBS_COUNT and CI_ERRORS_FILE, emit CI_ERRORS_DISTILL_CLASS only when the file value is empty, without altering the JSON-bound dict.
  - From Cursor-Innovation: Build result-env CI rows from `emit_result`'s `ci_errors_file` / `ci_errors_distill_class` / `failed_jobs_count` arguments using the same pairing rules as `dispatch_ship._write_ship_route_handoff` (always file + count; class only when file empty). Keep JSON serialization unchanged.


### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/ship.py
- **Concern**: [SCOPE-REDUCTION] Prefer the established `--merge-result-env` child flag over `--result-env-path`. Scenario: `bgjob.adapt` and every other implement child (`dispatch_commit_route.py`, `step-8-ship.sh`) wire `--merge-result-env`. A new flag name forces piece 2 to add translation glue or fork adapt conventions.
- **Proposed resolution**: Add `--merge-result-env` to `ship pr` (accept the validated path from adapt); keep `--result-env-path` out unless both are required as aliases for one release. **1. CI projection must bypass the JSON-sparse payload (FINDING_3 still open).** `emit_result()` only adds CI fields to the payload when truthy: if ci_errors_file: payload["ci_errors_file"] = ci_errors_file if ci_errors_distill_class: payload["ci_errors_distill_class"] = ci_errors_distill_class if failed_jobs_count: payload["failed_jobs_count"] = failed_jobs_count Route-exit always emits `FAILED_JOBS_COUNT` and `CI_ERRORS_FILE`, with `CI_ERRORS_DISTILL_CLASS` only when the file is empty (`dispatch_ship.py:362-374`). The plan's mirror rule is right, but "build from the redacted JSON payload" still conflicts with it. The env writer should take the raw CI arguments and apply pairing rules directly. **2. Mixed-case keys, not uniform uppercase.** Handoff tests pin lowercase ledger keys (`ledger_ready=true`). Repair and CI keys stay uppercase. Blanket uppercasing would change the wire shape piece 2 inherits. **3. Use `--merge-result-env`.** That matches `bgjob.adapt` and `step-8-ship.sh` today; a new flag name is extra surface for piece 2 with no functional gain. Accepted ledger items (prevalidation, fail-closed write ordering, CI pairing intent) look adequately covered. I am not re-raising rejected FINDING_2 or OOS duplicate-validation items.

