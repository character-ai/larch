### [rejected] FINDING_11

### FINDING_11: code-quality: skills/review/scripts/dispatch-panel.sh:272-278 vs :398
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] stdout omits SCOUT_FAIL_REASON when empty but execution-issues uses reason=unknown. Legacy status sidecars produce inconsistent reason reporting across KV stream and log. Default emit_kv when parse-failed or align log text with absent KV.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_12

### FINDING_12: code-quality: skills/review/scripts/dispatch-panel.sh:353-377
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] append_scout_parse_issue runs before waterfall while message implies static panel continuation is already settled. Minor misleading operator log ordering. Rephrase log text or move append after dispatch begins.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_20

### FINDING_20: correctness: skills/review/scripts/review-core.md:SCOUT_FAIL_REASON bullet
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit]  Wording implies only scout subprocess parse failures dispatch_manifest_validation misclassified mentally in docs Rephrase to cover dispatch-side manifest or sidecar failures
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_21

### FINDING_21: risk-integration: scripts/scout-dynamic-archetypes.sh:330-348
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] SCOUT_FAIL_REASON=validation_jq_error is undocumented in tests Future jq regression ships without failing CI Add fixture + grep for validation_jq_error in scripts/test-scout-dynamic-archetypes.sh
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_22

### FINDING_22: risk-integration: scripts/test-scout-dynamic-archetypes.sh;skills/review/scripts/test-dispatch-panel.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No test asserts validation_jq_error or tricky multi-fence cases. Reducer or awk heuristic regression may ship undetected. Add targeted harness cases for validation_jq_error and multi-fence outputs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_26

### FINDING_26: risk-integration: skills/review/scripts/dispatch-panel.sh:269
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Gate requires append-execution-issue.sh to be executable (-x). Non-executable script bit in a packaged checkout; warning path skipped silently. Use bash dispath or -f plus explicit error logging.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_27

### FINDING_27: risk-integration: skills/review/scripts/dispatch-panel.sh:269
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Gate requires append-execution-issue.sh to be executable (-x). scripts directory on noexec or non-executable bit; warning path silently skipped. Use bash-invoked helper or -f plus explicit error handling.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_28

### FINDING_28: risk-integration: skills/review/scripts/dispatch-panel.sh:269
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] -x gate skips append if helper not executable Warning omitted on odd installs Use -f and bash helper or log skip reason
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_32

### FINDING_32: security: skills/review/scripts/dispatch-panel.sh:267-278
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Free-form execution-issues entry interpolates SCOUT_FAIL_REASON and full SCOUT_MANIFEST path without allowlisting or markdown-safe encoding. A substitute scout launcher or odd manifest paths can inject structured markdown or misleading text into execution-issues.md where it is consumed as documentation. Allowlist reasons; log basename only; escape or template the entry as plain text.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_7

### FINDING_7: architecture: skills/review/SKILL.md (wrapper Step 3)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit]  Plan file list omitted SKILL.md Orchestration doc updated correctly; plan checklist was incomplete Update future plans to include SKILL.md when KV surface changes
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_9

### FINDING_9: code-quality: scripts/scout-dynamic-archetypes.sh:251-258
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Awk fence extraction concatenates all fenced blocks before jq. Multiple fenced segments can make jq fail despite a valid JSON fence. Prefer first jq-valid block or per-block attempts.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

