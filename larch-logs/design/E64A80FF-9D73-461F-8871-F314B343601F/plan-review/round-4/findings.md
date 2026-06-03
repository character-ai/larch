### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md (plan UPDATED Step 2b ~201-203)
- **Concern**: Step 2b driver handoff specifies file-first `.design-postplan-emit-result.env` parse but not stdout fallback from the `set +e` capture. Scenario: If `phase_driver_write_result_env` fails after `emit_kv` (or the env file is missing/unreadable), orchestrator may see empty `POSTPLAN_EMIT_STATUS` / `VALIDATE_STATUS` while the Bash capture still has KVs — wrong hard-failure vs `defects-found` routing
- **Proposed resolution**: In the Step 2b fence prose, mirror Step 0b `design-route.sh` / Step 5c: parse the env file first (symlink-guarded), then fill any still-unset allowlisted keys from `_postplan_out`

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:284-287 vs skills/design/references/flags.md:68
- **Concern**: Docs verification greps for inline Step 2b EMIT/snapshot/validator fences; flags.md says the plan-command validator runs unconditionally and does not mention review_budget=quick skip or discussion-round2 --force-validate. Scenario: Implementer may skip flags.md; consumer doc stays wrong after the driver change
- **Proposed resolution**: Extend the verification grep (or explicit file list) to include flags.md Plan-command validator and align line 68 with driver skipped-quick plus --force-validate parity
