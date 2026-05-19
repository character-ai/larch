### FINDING_1: **Important** `risk-integration` `skills/review/SKILL.md:27`, `skills/review/references/heavy-worker.md:36`: the new `SCOUT_FAIL_REASON` telemetry is only wired through the inline review path; `/review --diff --subagent` still tells the parent to parse only `SCOUT_STATUS`, `DYNAMIC_SLOTS`, `SCOUT_MANIFEST`, and `YIELD_TSV_FILE`, and the heavy-worker return contract omits `SCOUT_FAIL_REASON`. Concrete failing scenario: with `--dynamic-archetypes 4`, a malformed scout response makes `review-core.sh` emit `SCOUT_FAIL_REASON=json_parse`, but the worker footer/parent binding drops it, so the subagent path loses the new telemetry before Step 4. Update both the Step 0 parent parse list and heavy-worker preserved/returned KV contract to include `SCOUT_FAIL_REASON`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/review/SKILL.md:27`, `skills/review/references/heavy-worker.md:36`: the new `SCOUT_FAIL_REASON` telemetry is only wired through the inline review path; `/review --diff --subagent` still tells the parent to parse only `SCOUT_STATUS`, `DYNAMIC_SLOTS`, `SCOUT_MANIFEST`, and `YIELD_TSV_FILE`, and the heavy-worker return contract omits `SCOUT_FAIL_REASON`. Concrete failing scenario: with `--dynamic-archetypes 4`, a malformed scout response makes `review-core.sh` emit `SCOUT_FAIL_REASON=json_parse`, but the worker footer/parent binding drops it, so the subagent path loses the new telemetry before Step 4. Update both the Step 0 parent parse list and heavy-worker preserved/returned KV contract to include `SCOUT_FAIL_REASON`.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: scripts/scout-dynamic-archetypes.sh:283
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Pre-existing validated_tmp mktemp || exit 1 already hard-exits on tmp allocation failure. Same class of infra failure as new fence mktemp path; not introduced solely by this diff. Consider aligning all tmp failures with non-fatal scout behavior in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: skills/review/scripts/dispatch-panel.sh:329-333
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ok-but-invalid-manifest branch updates in-memory state without write_scout_status_file. Disk sidecar can remain SCOUT_STATUS=ok until another writer refreshes it. Pre-existing; fix by calling write_scout_status_file in that branch if you touch it again.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/review/scripts/test-dispatch-panel.sh:196-197
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH prefix in skip-mode loop. Readability only. Remove redundant assignment when editing tests.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/dispatch-panel.md:33
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] make test-dispatch-panel not in Makefile Operators run wrong make target Pre-existing doc fix to list shard targets
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/scout-dynamic-archetypes.sh:252
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Fence-strip mktemp failure uses exit 1, violating the scout non-fatal exit-0 contract documented for Claude failures. mktemp fails; dispatch sees scout_rc!=0 and sets SCOUT_STATUS=validation-failed instead of a parse/empty outcome, changing orchestration semantics for infra errors. On mktemp failure use the same write_empty_manifest + parse-failed (or dedicated io reason) + exit 0 path.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: skills/review/SKILL.md (wrapper Step 3)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit]  Plan file list omitted SKILL.md Orchestration doc updated correctly; plan checklist was incomplete Update future plans to include SKILL.md when KV surface changes
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/scout-dynamic-archetypes.md:23
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] SCOUT_FAIL_REASON enum in scout contract lists only three scout-local reasons. Dispatch and execution-issues now use additional reasons (dispatch_manifest_validation, missing_status_sidecar) and unknown; consumers following only scout-dynamic-archetypes.md mis-classify telemetry. Document full reason set or cross-link dispatch-panel.md and note unknown in execution-issues when KV absent.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/scout-dynamic-archetypes.sh:251-258
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Awk fence extraction concatenates all fenced blocks before jq. Multiple fenced segments can make jq fail despite a valid JSON fence. Prefer first jq-valid block or per-block attempts.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/scout-dynamic-archetypes.sh:261-264
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] json_parse used for jq archetypes gate failures. Well-formed JSON missing a proper archetypes array is labeled json_parse, skewing failure analytics. Rename or split fail reasons for JSON syntax vs shape validation.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: skills/review/scripts/dispatch-panel.sh:272-278 vs :398
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] stdout omits SCOUT_FAIL_REASON when empty but execution-issues uses reason=unknown. Legacy status sidecars produce inconsistent reason reporting across KV stream and log. Default emit_kv when parse-failed or align log text with absent KV.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: skills/review/scripts/dispatch-panel.sh:353-377
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] append_scout_parse_issue runs before waterfall while message implies static panel continuation is already settled. Minor misleading operator log ordering. Rephrase log text or move append after dispatch begins.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/scout-dynamic-archetypes.md:23
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] SCOUT_FAIL_REASON enum omits dispatcher-originated values Operators grep docs for allowed reasons and miss dispatch_manifest_validation or missing_status_sidecar seen on dispatch stdout Narrow scout doc to script-only reasons; document dispatcher reasons in dispatch-panel.md
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/scout-dynamic-archetypes.md:23 & skills/review/scripts/dispatch-panel.sh:315-343
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Contract enumerates three SCOUT_FAIL_REASON values but dispatcher invents additional reasons. Downstream parsers assume closed enum from scout doc; dispatch-only reasons undocumented. Document dispatch-side SCOUT_FAIL_REASON values in scout and/or dispatch-panel contracts.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/scout-dynamic-archetypes.sh:251-258
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Fence stripping only matches ``` at column 1; indented markdown fences are ignored. Model returns indented ```json ... ```; jq fails on full file, awk extracts nothing, scout stays parse-failed despite valid fenced JSON. Match leading whitespace or normalize lines before fence detection.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/scout-dynamic-archetypes.sh:251-258
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Fence stripping only recognizes ^``` and concatenates all fenced regions before jq validation. Multiple fenced blocks or indented fences; extracted blob is invalid JSON; stripper never helps and parse-failed rate stays high. Document limits or extract first jq-valid fenced JSON / relax fence line matching.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/scout-dynamic-archetypes.sh:261-268
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] SCOUT_FAIL_REASON=json_parse is emitted when JSON parses but the archetypes gate fails (wrong type/missing field). Output {"archetypes":{}} or bare JSON scalar; telemetry says json_parse though jq already parsed JSON. Use a separate fail reason for non-array/missing archetypes or reserve json_parse for true JSON parse failures only.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/scout-dynamic-archetypes.sh:261-268
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SCOUT_FAIL_REASON=json_parse is emitted for any failure of the .archetypes shape gate, not only invalid JSON. Model returns valid JSON without a proper archetypes array; telemetry reports json_parse and misdirects debugging away from schema or prompt compliance. Split or rename reasons so the value matches the failing gate (e.g. invalid_scout_shape vs json_parse).
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/test-scout-dynamic-archetypes.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit]  No test asserts validation_jq_error from scout third failure path Regression could remove validation_jq_error KV without failing tests Add stubbed case asserting SCOUT_FAIL_REASON=validation_jq_error
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/review/scripts/review-core.md:SCOUT_FAIL_REASON bullet
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit]  Wording implies only scout subprocess parse failures dispatch_manifest_validation misclassified mentally in docs Rephrase to cover dispatch-side manifest or sidecar failures
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/scout-dynamic-archetypes.sh:330-348
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] SCOUT_FAIL_REASON=validation_jq_error is undocumented in tests Future jq regression ships without failing CI Add fixture + grep for validation_jq_error in scripts/test-scout-dynamic-archetypes.sh
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/test-scout-dynamic-archetypes.sh;skills/review/scripts/test-dispatch-panel.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No test asserts validation_jq_error or tricky multi-fence cases. Reducer or awk heuristic regression may ship undetected. Add targeted harness cases for validation_jq_error and multi-fence outputs.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: skills/review/scripts/dispatch-panel.sh:267-278
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] append-execution-issue failures are swallowed (redirect + || true). Unwritable LARCH_EXECUTION_ISSUES_LOG path; no warning recorded and no error surfaced. Emit diagnostic on failure or fail soft with visible lib-quiet breadcrumb.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: skills/review/scripts/dispatch-panel.sh:267-278
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] append_scout_parse_issue discards append-execution-issue failures with >/dev/null and || true. Log path read-only or lock contention; no execution-issues line and no substitute warning, so the new observability path fails silently. Emit a WARN or preserve stderr when append-execution-issue returns non-zero instead of swallowing all failures.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: skills/review/scripts/dispatch-panel.sh:267-278
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] append-execution-issue failures are swallowed Execution-issues warning missing with no signal Document or surface non-zero append (e.g. WARN) if required by policy
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: skills/review/scripts/dispatch-panel.sh:269
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Gate requires append-execution-issue.sh to be executable (-x). Non-executable script bit in a packaged checkout; warning path skipped silently. Use bash dispath or -f plus explicit error logging.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: skills/review/scripts/dispatch-panel.sh:269
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Gate requires append-execution-issue.sh to be executable (-x). scripts directory on noexec or non-executable bit; warning path silently skipped. Use bash-invoked helper or -f plus explicit error handling.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: skills/review/scripts/dispatch-panel.sh:269
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] -x gate skips append if helper not executable Warning omitted on odd installs Use -f and bash helper or log skip reason
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: skills/review/scripts/dispatch-panel.sh:274-278
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] append_scout_parse_issue fully silences append-execution-issue.sh failures. I/O or lock failure while appending Warnings yields no entry and no operator-visible error. Emit a WARN or breadcrumb on append failure instead of only /dev/null || true.
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: skills/review/scripts/dispatch-panel.sh:315-345
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] dispatch-only fail reasons lack dedicated tests Reuse-branch regressions undetected Add dispatch-panel test for dispatch_manifest_validation or missing_status_sidecar + execution-issues
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: skills/review/scripts/dispatch-panel.sh:append_scout_parse_issue
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent]  append-execution-issue failures are swallowed Parse-failed run produces no execution-issues entry when log append fails; no WARN Emit WARN or quiet-stream notice on append failure
- **Suggested revision**: Address the concern above.

### FINDING_32: security: skills/review/scripts/dispatch-panel.sh:267-278
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Free-form execution-issues entry interpolates SCOUT_FAIL_REASON and full SCOUT_MANIFEST path without allowlisting or markdown-safe encoding. A substitute scout launcher or odd manifest paths can inject structured markdown or misleading text into execution-issues.md where it is consumed as documentation. Allowlist reasons; log basename only; escape or template the entry as plain text.
- **Suggested revision**: Address the concern above.

