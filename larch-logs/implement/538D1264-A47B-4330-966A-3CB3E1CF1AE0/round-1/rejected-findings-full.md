### [rejected] FINDING_10

### FINDING_10: code-quality: skills/review/scripts/dispatch-panel.sh:284-299
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] append_scout_parse_issue resolves execution-issues log before the harness suppress return. Suppressed harness runs still invoke resolve_execution_issues_log even though issues_log is unused. Move issues_log resolution after the suppress check or only when invoking append-execution-issue.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_11

### FINDING_11: code-quality: skills/review/scripts/test-dispatch-panel.sh:332-385
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Regression env-isolation and path-guard largely duplicate the same harness-tmpdir plus parent LARCH_EXECUTION_ISSUES_LOG setup; only the second adds a diag grep. Maintainers may update one test and miss the other, or spend time reasoning about two names for one behavior. Merge into one test with the stronger assertions or give regression 2 a distinct invariant (different code path or inputs).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_15

### FINDING_15: risk-integration: skills/review/scripts/dispatch-panel.sh:267-271
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Broad path substring globs (e.g. */test-scout-*) can match legitimate project directories. Accidental suppression of execution-issues warnings if real paths include test-scout-* segments. Narrow patterns or use explicit opt-in from harness.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_17

### FINDING_17: risk-integration: skills/review/scripts/dispatch-panel.sh:267-281
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Suppression uses path-component globs including test-scout-* on REVIEW_TMPDIR or SCOUT_MANIFEST. A production REVIEW_TMPDIR that includes a matching segment (e.g. test-scout-artifacts) drops the execution-issues warning; a future harness using a different mktemp basename than test-dispatch-panel. / test-review-core. may not match and can leak again. Document naming contract; add explicit opt-out env; or gate on harness-set flag instead of path substrings.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_18

### FINDING_18: risk-integration: skills/review/scripts/dispatch-panel.sh:291-296
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Diag file write uses || true; failures are silent. Disk full: no diag sidecar and (if not suppressed) still possible silent skip of useful telemetry. On diag write failure emit WARN= or avoid swallowing the error entirely.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_19

### FINDING_19: risk-integration: skills/review/scripts/test-dispatch-panel.sh:486-539
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Regression 1 and 2 largely duplicate the same parse-failed scenario. Maintenance noise if one assertion changes but not the other. Merge into one test with combined assertions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_7

### FINDING_7: code-quality: plan: Part B vs skills/review/scripts/test-dispatch-panel.sh:332-385
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan promised three distinct regressions; two are structurally overlapping (code-quality / plan). Slightly inflated test surface for one guard clause. Consolidate or differentiate scenarios per finding 1.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: code-quality: skills/review/scripts/dispatch-panel.md:18-19
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc says harness ancestor; code matches path substrings/globs. Misleading operational contract for integrators. Align wording with glob semantics or tighten implementation to ancestor checks.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_9

### FINDING_9: code-quality: skills/review/scripts/dispatch-panel.sh:279-289
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Parameter manifest_path vs passed SCOUT_MANIFEST value naming (manifest_label) obscures intent. Readers may misread which path the second OR branch is guarding. Rename parameter or caller variable for consistency.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

