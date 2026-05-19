### FINDING_1: **Important** `risk-integration` `skills/review/SKILL.md:27`, `skills/review/references/heavy-worker.md:36`: the new `SCOUT_FAIL_REASON` telemetry is only wired through the inline review path; `/review --diff --subagent` still tells the parent to parse only `SCOUT_STATUS`, `DYNAMIC_SLOTS`, `SCOUT_MANIFEST`, and `YIELD_TSV_FILE`, and the heavy-worker return contract omits `SCOUT_FAIL_REASON`. Concrete failing scenario: with `--dynamic-archetypes 4`, a malformed scout response makes `review-core.sh` emit `SCOUT_FAIL_REASON=json_parse`, but the worker footer/parent binding drops it, so the subagent path loses the new telemetry before Step 4. Update both the Step 0 parent parse list and heavy-worker preserved/returned KV contract to include `SCOUT_FAIL_REASON`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/review/SKILL.md:27`, `skills/review/references/heavy-worker.md:36`: the new `SCOUT_FAIL_REASON` telemetry is only wired through the inline review path; `/review --diff --subagent` still tells the parent to parse only `SCOUT_STATUS`, `DYNAMIC_SLOTS`, `SCOUT_MANIFEST`, and `YIELD_TSV_FILE`, and the heavy-worker return contract omits `SCOUT_FAIL_REASON`. Concrete failing scenario: with `--dynamic-archetypes 4`, a malformed scout response makes `review-core.sh` emit `SCOUT_FAIL_REASON=json_parse`, but the worker footer/parent binding drops it, so the subagent path loses the new telemetry before Step 4. Update both the Step 0 parent parse list and heavy-worker preserved/returned KV contract to include `SCOUT_FAIL_REASON`.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: scripts/scout-dynamic-archetypes.sh:251-258
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Fence stripping only matches ``` at column 1; indented markdown fences are ignored. Model returns indented ```json ... ```; jq fails on full file, awk extracts nothing, scout stays parse-failed despite valid fenced JSON. Match leading whitespace or normalize lines before fence detection.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: scripts/scout-dynamic-archetypes.sh:261-268
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] SCOUT_FAIL_REASON=json_parse is emitted when JSON parses but the archetypes gate fails (wrong type/missing field). Output {"archetypes":{}} or bare JSON scalar; telemetry says json_parse though jq already parsed JSON. Use a separate fail reason for non-array/missing archetypes or reserve json_parse for true JSON parse failures only.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: scripts/test-scout-dynamic-archetypes.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit]  No test asserts validation_jq_error from scout third failure path Regression could remove validation_jq_error KV without failing tests Add stubbed case asserting SCOUT_FAIL_REASON=validation_jq_error
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: skills/review/scripts/dispatch-panel.sh:267-278
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] append_scout_parse_issue discards append-execution-issue failures with >/dev/null and || true. Log path read-only or lock contention; no execution-issues line and no substitute warning, so the new observability path fails silently. Emit a WARN or preserve stderr when append-execution-issue returns non-zero instead of swallowing all failures.
- **Suggested revision**: Address the concern above.


### FINDING_30: risk-integration: skills/review/scripts/dispatch-panel.sh:315-345
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] dispatch-only fail reasons lack dedicated tests Reuse-branch regressions undetected Add dispatch-panel test for dispatch_manifest_validation or missing_status_sidecar + execution-issues
- **Suggested revision**: Address the concern above.


### FINDING_6: architecture: scripts/scout-dynamic-archetypes.sh:252
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Fence-strip mktemp failure uses exit 1, violating the scout non-fatal exit-0 contract documented for Claude failures. mktemp fails; dispatch sees scout_rc!=0 and sets SCOUT_STATUS=validation-failed instead of a parse/empty outcome, changing orchestration semantics for infra errors. On mktemp failure use the same write_empty_manifest + parse-failed (or dedicated io reason) + exit 0 path.
- **Suggested revision**: Address the concern above.


### FINDING_8: code-quality: scripts/scout-dynamic-archetypes.md:23
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] SCOUT_FAIL_REASON enum in scout contract lists only three scout-local reasons. Dispatch and execution-issues now use additional reasons (dispatch_manifest_validation, missing_status_sidecar) and unknown; consumers following only scout-dynamic-archetypes.md mis-classify telemetry. Document full reason set or cross-link dispatch-panel.md and note unknown in execution-issues when KV absent.
- **Suggested revision**: Address the concern above.


