### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: code-quality
- **Location**: skills/design/references/approval-gates.md:185-198
- **Concern**: Gate C invariant persist branches lack dispatch rules tying clean vs remediated-violations vs no-flags paths. Scenario: The plan lists three persist branches but not when to choose each. After the existing remediation loop (lines 177, 190), an orchestrator can call `architectural-invariants persist-design-assessment --assessment clean` and commit `CLEAN_INVARIANT_PRESENTATION_NOTE` even when `INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true` was raised and violations were fixed. That contradicts the issue requirement for a remediated sidecar and loses audit evidence that violations occurred.
- **Proposed resolution**: Mirror the guideline persist dispatch shape: **Clean** only when invariants are present with parsed non-empty content and no violation assessment was required; **Remediated-violations** when violations were identified and the remediation loop produced a clean plan (write a short summary to `$DESIGN_TMPDIR/architectural-invariant-assessment.input.sidecar`, then persist with `--assessment-file`); **Absent, invalid, or present-but-empty** when `read_invariants().status` is not `present` or parsed `content.strip()` is empty (no assessment flags). Pin the dispatch prose and branch order in `scripts/test-design-structure.sh` alongside the existing persist-command pins.



### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:458-472
- **Concern**: New invariant refusal path only resets VALIDATE_STATUS. Scenario: After a missing-invariant-assessment refusal, Step 5c can still carry the prior validation log path and other stale validation metadata, so the refusal env no longer matches the guideline refusal contract and downstream consumers see a false validation trail.
- **Proposed resolution**: Mirror `_emit_missing_guideline_assessment_refusal`'s full validation reset, especially `VALIDATE_LOG_FILE`, when emitting the invariant refusal.



### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/design/design_summary.py:34,502-516,695-699
- **Concern**: Additive prefixing can reverse the required warning order. Scenario: `_prefix_missing_*` prepends text. If the invariant warning is added by calling the new helper next to the existing guideline helper, the guideline warning can stay at the top when both markers exist, which violates the required invariant-first order.
- **Proposed resolution**: Compose both warning lines in one write, or call the guideline prefix first and the invariant prefix second so the invariant warning is rendered first.



