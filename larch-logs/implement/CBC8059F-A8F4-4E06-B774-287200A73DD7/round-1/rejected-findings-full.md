### [rejected] FINDING_15

### FINDING_15: risk-integration: scripts/ship-pr.sh (run_pr_create_phase; emit after PR_NUMBER state_set in branch diff)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Breadcrumb prints `PR_NUMBER` from helper KV without format validation. A compromised or buggy `create-pr.sh` could emit a `PR_NUMBER` with embedded newlines; the breadcrumb splits the quiet stream and can break consumers that assume one line per progress record. Validate `pr_number` as numeric (or sanitize to a single safe token) before string interpolation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

### FINDING_16: risk-integration: scripts/ship-pr.sh:129-131 scripts/lib-quiet.sh:114-119
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] mark_stall always calls emit_breadcrumb; when breadcrumbs are off, text goes to the quiet log via FD1. Quiet logs grow with stall lines vs previous mark_stall (no printf); could affect log-volume assumptions. Accept as diagnostic improvement or gate printf behind the same truthy check used for operator-visible emits.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

### FINDING_8: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:414-417
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Success breadcrumb uses inline $(cat "$tool_file") before repeated reads If tool_file were empty the breadcrumb could mis-label the tool while claiming success Read tool name once into a variable with a fallback or reuse the value read for the result_file block
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

### FINDING_9: code-quality: skills/review/scripts/dispatch-panel.sh:400-413
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Breadcrumb total recomputed from array lengths instead of static_slot_count After a refactor that changes queueing without updating the parallel counts the human-readable total can disagree with STATIC_SLOT_COUNT/SLOT_COUNT emitted later Use total=$((static_slot_count + DYNAMIC_SLOTS)) for the numeric total aligned with emit_kv and keep breakdown text separate
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

