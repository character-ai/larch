### FINDING_1: [OUT_OF_SCOPE] correctness: scripts/scout-dynamic-archetypes.md:11-12
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Invariant implies scout always emits SCOUT_STATUS before exit; several exit 1 paths omit stdout status. Pre-existing bullet unchanged this PR. Optional future edit to align invariant with exit 1 paths or dispatcher validation-failed.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: scripts/scout-dynamic-archetypes.md:24
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Narrow phrase 'before the manifest can be evaluated' for dispatcher validation-failed vs broader dispatcher contract. Readers may infer validation-failed only for early scout crashes rather than any scout non-zero exit that skips stdout parsing. Align wording with dispatch-panel.md ('manifest/status output can be trusted') or state dispatcher maps any scout_rc!=0 the same way.
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: skills/review/scripts/dispatch-panel.md:13
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Doc claims launcher failures always yield scout exit-0 with claude-failed or timeout, never dispatcher validation-failed. After launch_rc!=0, write_empty_manifest runs mktemp||exit 1; if mktemp fails the scout exits 1 before emitting status, so dispatch-panel still sets validation-failed. Qualify: claude-failed/timeout with exit 0 when empty-manifest write succeeds; note temp-file failures can still exit non-zero.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: skills/review/scripts/dispatch-panel.md:13
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Doc ties validation_jq_error to parse-failed/exit-0, not to dispatcher validation-failed, diverging from the supplied implementation_plan draft. The draft plan implied validation_jq_error could surface as SCOUT_STATUS=validation-failed; the branch doc instead classifies it with parse-failed. In code, emit_parse_failed_result always exits 0, so that draft scenario does not apply; a reader using only the draft plan could misjudge completeness. Treat the draft plan bullet as superseded by code-accurate wording; optionally correct the plan template for future /implement plans.
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: skills/review/scripts/dispatch-panel.md:13
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] validation-failed is documented next to parse-failed diagnostics without stating they are parse-failed-only. Operator expects scout-parse-failed sidecar or execution-issues Warnings after validation-failed; append_scout_parse_issue only runs for parse-failed (dispatch-panel.sh:284-285), so no diag append and misleading troubleshooting. Add one sentence that validation-failed skips parse-failure sidecar and execution-issues append because stdout is not parsed when the scout exits non-zero.
- **Suggested revision**: Address the concern above.

