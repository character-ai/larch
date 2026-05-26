### FINDING_13: [OUT_OF_SCOPE] code-quality: .claude/skills/bump-version/scripts/apply-bump.md:37-39
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Sibling doc describes old emit_breadcrumb routing Operators reading apply-bump.md get wrong stream contract guidance Update apply-bump.md for LARCH_BREADCRUMB_STREAM and --category=
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: risk-integration: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] apply-bump emit_breadcrumb lacks --category= while ship-pr inherits LARCH_BREADCRUMB_STREAM During backgrounded ship-pr Step 8 version-bump retries, retry breadcrumbs are dropped with WARN unknown-category=<missing> so operators see no structured retry progress in chat Add --category=retry and assert stream record in test-apply-bump.sh with LARCH_BREADCRUMB_STREAM set
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_2: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Only uncategorized emit_breadcrumb callsite remains Under ship-pr with LARCH_BREADCRUMB_STREAM set, bump-race retries emit WARN unknown-category and never surface in chat Add --category=retry (or progress) and a stream-set test in test-apply-bump.sh
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] risk-integration: scripts/test-refresh-run-logs.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No refresh-specific breadcrumb commit assertion refresh-run-logs.sh wiring to larch-log commit breadcrumbs could break without a targeted test Optional add refresh harness case with synthetic IMPLEMENT_TMPDIR/breadcrumbs and assert post-commit repo copy
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] security: SECURITY.md:127-141
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Documented residual risk: operational CI/diagnostic strings may be committed in redacted breadcrumbs. Public repos may expose internal CI URLs or hostnames even when PEM/token redaction succeeds. Operator discipline; optional future scrubber for URL/host patterns in breadcrumb commit pipeline.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] security: scripts/lib-quiet.sh:176-181
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Pre-existing eval of captured EXIT trap body in larch_quiet__exit_combo. Malicious or malformed trap strings could theoretically execute unexpected shell if trap capture is ever poisoned. Replace eval with explicit trap chaining or a small whitelist of known trap handlers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_26: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] apply-bump.sh emit_breadcrumb lacks --category while ship-pr.md requires inherited-stream vocabulary. During backgrounded ship-pr version bump with LARCH_BREADCRUMB_STREAM set, retry breadcrumbs are dropped (WARN unknown-category) and never surface in chat. Add --category=retry to the emit_breadcrumb callsite; add a stream-set assertion in test-apply-bump.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/lib-larch-log.sh:272-304
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Swap-based publish heavier than plan’s atomic mv Extra maintenance surface for directory replacement Keep if refresh replace is required; otherwise simplify after audit
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] architecture: scripts/ci-wait.sh:249
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Terminating newline stays on quiet FD4 not breadcrumb stream Stream consumers miss a visual separator before success text Optional: route newline through emit_breadcrumb_stderr or drop it when stream is set
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:195
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Uncategorized emit_breadcrumb under inherited LARCH_BREADCRUMB_STREAM is dropped from the stream Step 8 bump race with monitor: retry lines never appear in stream/chat despite up to 10 retries Add --category=retry (or progress) on the apply-bump emit_breadcrumb callsite
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

