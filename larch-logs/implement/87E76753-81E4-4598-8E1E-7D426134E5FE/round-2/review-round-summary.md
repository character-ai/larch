# Review Round 2

- Mode: `diff`
- Accepted findings: 9
- Rejected findings: 0
- Exonerated findings: 8
- Neutral findings: 1

## Accepted Findings

### FINDING_12: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh:89-124
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] When neither codex-commit-message nor session-transcript exists under RUN_DIR the scan counts Inline-triage via the current repo git log range. Auditing a copied or partial run directory without those artifacts can attribute unrelated local commit messages to that run and skew oos-silent-drop pass/fail. When no run-local artifacts exist return zero or mark scan incomplete unless caller supplies an explicit repo+revision range; do not default to ambient HEAD history.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/implement/scripts/oos-disposition-shared.inc.bash:35-40
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] jq parse failures on oos-issues.ndjson lines are skipped with only a stderr line. Partially corrupted NDJSON can yield a rejected-marker count that omits some rejection sections while still appearing mechanically computed. Count jq failures and fail closed (or structured incomplete) when any line fails to parse in gate-critical mode.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: .claude/skills/audit-runs/scripts/audit-scan-run.sh:197-232;.claude/skills/audit-runs/scans.tsv
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New oos-silent-drop scan without matching audit-scan-run.md and test-audit-runs updates. Registry/docs/tests can drift; scan could be removed or reshaped without CI catching wrong NDJSON contracts. Add test-audit-runs fixtures for pass/skip/fail and refresh audit-scan-run.md scan list and NDJSON field notes alongside the implementation.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/implement/scripts/oos-disposition-shared.inc.bash:32-48
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] jq parse errors skip NDJSON lines when counting rejected OOS markers. Corrupted JSONL undercounts rejections; gate or audit can false-fail disposition or mislead operators. Fail closed on jq errors or count parse failures separately and surface as exit 2 / explicit scan error.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: scripts/test-implement-structure.sh:241-265
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] NEVER #18 gate-before-clear rule lacks a grep pin unlike adjacent OOS invariants. Wording-only regressions on NEVER #18 could ship without structure harness signal. Pin a distinctive NEVER #18 substring tied to oos-disposition-gate.sh.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/review/scripts/aggregate-findings.sh (aggregate-validate.py check_revision_traceability)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Legacy singular Suggested revision ignored when bullets also present. Inconsistent merged output could carry an untraced legacy line alongside traced bullets with no warning. Trace both forms or warn when both appear; optionally fail under strict mode.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/review-and-fix/scripts/review-and-fix.sh:221
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] compose_coder_prompt rewrote the primary fix directive (Concern-first, new Justification rules) instead of only appending the planned coder sentence after the Suggested revision reference. Coders may prioritize Concern over the verbatim multi-reviewer revision list the plan was designed to preserve for implementation, diverging from the stated “add a sentence” change. Restore the original suggested-revision-centric directive and append only the plan’s sentence (plus minimal plural/legacy wording if needed).
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: skills/review/scripts/aggregate-findings.sh:390-433
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Dual-format merged blocks skip traceability for legacy singular Suggested revision when From bullets exist. A merged FINDING could carry both multi-reviewer bullets and a legacy singular line; only bullets are checked so a fabricated singular revision would not emit stderr warnings. Validate singular revision whenever present, or reject dual-format output in structural validation.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/review/scripts/aggregate-findings.sh:302-334
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Suggested revisions sub-list parser terminates on any line matching ^-\\s*\\*\\*[A-Z]. A rare verbatim continuation formatted as a top-level - **Capital... line could truncate bullets and produce false warnings or missed traces. Restrict termination to known field headers or require indented continuation lines only.
- **Suggested revision**: Address the concern above.


