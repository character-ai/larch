### FINDING_1: **Important** `risk-integration` [scripts/scout-dynamic-archetypes.md:24](<OPERATOR_REPO_PATH>/scripts/scout-dynamic-archetypes.md:24), [skills/review/scripts/dispatch-panel.md:13](<OPERATOR_REPO_PATH>/skills/review/scripts/dispatch-panel.md:13)  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` [scripts/scout-dynamic-archetypes.md:24](<OPERATOR_REPO_PATH>/scripts/scout-dynamic-archetypes.md:24), [skills/review/scripts/dispatch-panel.md:13](<OPERATOR_REPO_PATH>/skills/review/scripts/dispatch-panel.md:13)      The new contract text says the scout script itself only emits `ok`, `empty`, or `parse-failed`, but `scripts/scout-dynamic-archetypes.sh:280-285` also emits `SCOUT_STATUS=claude-failed` and `SCOUT_STATUS=timeout` on launcher failures. A direct caller following the documented enum could treat real timeout/subprocess-failure results as unknown even though they are established stdout statuses. Update the parenthetical to include `claude-failed` and `timeout`, or avoid enumerating scout-local statuses there; also avoid implying `validation_jq_error` maps to dispatcher `validation-failed`, since that path is caught by `emit_parse_failed_result` and exits 0 as `parse-failed`.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: skills/review/scripts/dispatch-panel.md:13
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Doc ties validation-failed to validation_jq_error exiting non-zero; emit_parse_failed_result validation_jq_error always exits 0. Debuggers expect validation-failed for jq validation failures; those flows yield parse-failed at the dispatcher. Remove validation_jq_error from non-zero examples; align with scout_rc!=0 paths only.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: skills/review/scripts/dispatch-panel.md:13
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Doc ties validation-failed to validation_jq_error and vague subprocess crash; code emits validation_jq_error with exit 0 via emit_parse_failed_result, and Claude launch failure also exits 0 with claude-failed/timeout. Operators or maintainers mis-map jq/Claude failures to SCOUT_STATUS=validation-failed and mis-debug dispatch vs scout stdout contracts. Align prose with dispatch-panel.sh scout_rc!=0 only; remove validation_jq_error from non-zero examples; distinguish scout process crash from inner Claude failure.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/review/scripts/dispatch-panel.md:13
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Doc equates parse-failed with only scout_manifest_is_valid failure after exit 0 Scout can print SCOUT_STATUS=parse-failed at exit 0 with valid empty manifest; dispatcher keeps parse-failed without scout_manifest_is_valid failing Reword parse-failed to cover scout stdout parse-failed and dispatcher validation not only scout_manifest_is_valid
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/review/scripts/dispatch-panel.md:13
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Doc ties validation-failed trigger to validation_jq_error exiting non-zero validation_jq_error uses emit_parse_failed_result then exit 0 so dispatcher uses scout_rc==0 path and parse-failed not validation-failed Remove validation_jq_error from non-zero exit list; cite fail exit 2 exit 1 mktemp set -e instead
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/review/scripts/dispatch-panel.md:13
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Doc claims validation_jq_error can yield non-zero scout exit leading to SCOUT_STATUS=validation-failed. validation_jq_error is handled by emit_parse_failed_result which always exits 0; operators may mis-attribute panel status or debug the wrong failure path. Replace validation_jq_error example with real non-zero causes (fail/exit 1/set -e/signal) or say jq validation failures surface as parse-failed with exit 0.
- **Suggested revision**: Address the concern above.


### FINDING_2: architecture: scripts/scout-dynamic-archetypes.md:28
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Planned update to Edit in sync note mentioning validation-failed was not applied. Future editors may miss dispatcher-only status when changing status contracts. Add validation-failed to the Edit in sync line as in the implementation plan.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: scripts/scout-dynamic-archetypes.md:24
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Parenthetical limits scout stdout statuses to ok|empty|parse-failed. Downstream docs or parsers treating the sentence as exhaustive omit claude-failed and timeout emitted at scout-dynamic-archetypes.sh:280-285. List claude-failed and timeout or avoid a closed three-status enumeration.
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: scripts/scout-dynamic-archetypes.md:24
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Scout stdout SCOUT_STATUS list omits claude-failed and timeout and falsely implies only ok/empty/parse-failed. Operators treat the sentence as the full enum and misinterpret real runs where launch fails with claude-failed or timeout on exit 0. List claude-failed and timeout or use explicitly non-exhaustive wording.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: scripts/scout-dynamic-archetypes.md:24
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] New parenthetical lists only ok|empty|parse-failed; scout stdout also emits claude-failed and timeout on exit 0. Readers assume an incomplete SCOUT_STATUS enum from scout stdout and contradict the doc's own line 12 non-ok invariant. List claude-failed and timeout or avoid claiming a closed three-value enum.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/scout-dynamic-archetypes.md:24
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Parenthetical claims scout only emits ok empty parse-failed Code emits claude-failed and timeout on stdout at exit 0 List all scout statuses or use non-exhaustive wording without only
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/scout-dynamic-archetypes.md:24
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Doc claims scout stdout only emits ok empty or parse-failed. Scout also emits claude-failed and timeout on exit 0; consumers relying on the doc could mis-handle those statuses. Add claude-failed and timeout to the list or avoid claiming an exhaustive enum in one parenthetical.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/review/scripts/dispatch-panel.md:13
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New text links validation-failed to validation_jq_error non-zero exit and vague subprocess crash; both disagree with shell. Operators or tests infer validation_jq_error or Claude subprocess death maps to validation-failed; they map to parse-failed or claude-failed/timeout with scout exit 0 per scripts/scout-dynamic-archetypes.sh and dispatch-panel.sh. Describe validation-failed only for non-zero scout bash exit; drop validation_jq_error from that clause; disambiguate crash as scout process vs Claude launch outcomes.
- **Suggested revision**: Address the concern above.


