### OOS_1: [OUT_OF_SCOPE] Step 3.6 ${!_assessor_key} macOS Bash 3.2 portability
- **Reviewer(s)**: dyn-bash-shell-correctness-output.txt
- **Severity**: latent
- **Concern**: The Step 3.6 handoff uses `${!_assessor_key}` fill-only-unset merging, copied from the Step 2b postplan fence. That pattern predates this branch; on macOS `/bin/bash` 3.2, `${!name}` is not general scalar indirection (only array-index expansion), so portability depends on the Bash version Claude Code uses for skill fences, not on the new driver.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] parse_kv_from_output trailing-CR corruption class
- **Reviewer(s)**: dyn-bash-shell-correctness-output.txt
- **Severity**: latent
- **Concern**: `parse_kv_from_output` assigns into globals and does not trim values; corrupted child stdout with trailing `\r` in `ROUND_CURSOR=` could make `write-after --round` fail validation and is only handled indirectly via the write-after-failure path. Same class of risk exists in other KV parsers in this tree.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] approval-gates.md unchanged for assess-failed
- **Reviewer(s)**: dyn-assess-failed-propagation-output.txt
- **Severity**: nit
- **Concern**: `approval-gates.md` is not in the diff; it documents `LOOP_STATUS` short-circuits that skip Step 3.6 entirely, not per-run `ASSESSOR_STATUS` no-prompt values. No change required for `assess-failed` there; defer to `assessor.md` / `SKILL.md` for assessor-status enumeration.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Six-key Stop-branch contract unchanged on assess-failed
- **Reviewer(s)**: dyn-assess-failed-propagation-output.txt
- **Severity**: nit
- **Concern**: On `assess-failed`, the driver still writes `ASSESSOR_STATUS`, `ASSESSOR_VERDICT`, `EFFECTIVE_ASSESSORS`, `ASSESSOR_VERDICT_FILE`, `ASSESSOR_VERDICT_ENV`, and `ROUND_NUM` via `_write_result_and_emit`. `WORKFLOW_PATH` is an orchestrator routing key (seven-key handoff); the WORSE-Stop branch still reads fixed keys from `.step3.6-assessor.env` — no rename drift observed.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] assess-failed is intentional new degradation behavior
- **Reviewer(s)**: dyn-assess-failed-propagation-output.txt
- **Severity**: nit
- **Concern**: Pre-extraction inline Step 3.6 called `assess-plan-round.sh` without `set +e`; a non-zero child exit would have aborted the fence under `set -e`. The driver's settled `assess-failed` path is an intentional degradation, correctly reflected in `SKILL.md`, `assessor.md`, and `design-plan-quality-assessor.md`.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

