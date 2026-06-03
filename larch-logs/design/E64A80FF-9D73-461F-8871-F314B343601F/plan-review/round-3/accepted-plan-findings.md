### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh (proposed)
- **Concern**: Plan mandates set -euo pipefail but does not require set +e around design-driver.sh / invoke-plan-validator.sh / snapshot-plan-round.sh child calls. Scenario: Child non-zero exit can abort before .design-postplan-emit-result.env and stdout KVs are written — harness case #10 and orchestrator file-first parse break
- **Proposed resolution**: Specify per-step set +e capture (emit_out=…; rc=$?; set -e) and always flush result-env + emit_kv before exit 1, matching design-driver.sh process_line pattern


