### FINDING_1: [OUT_OF_SCOPE] Stub-root naming clarity
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The harness now has two similarly named stub roots, `stub-bin` for `LARCH_PLAN_REVIEW_*_SH` wrappers and `bin` for PATH binary backstops, which could be misread when adding cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_2: [OUT_OF_SCOPE] Production external-agent launchers can still hang when installed binaries are unhealthy
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Production Codex/Cursor launcher paths still lack a fast-fail health probe or shorter timeout, so installed-but-unhealthy external binaries can still block outside this test harness. Reviewers consistently marked this as pre-existing or intentionally deferred from #3338.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_3: [OUT_OF_SCOPE] EXTSTUB cursor output path does not match capture-stdout-only mode
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The `EXTSTUB` cursor test helper parses `--output` from argv, but `launch-review` uses capture-stdout-only for cursor agent invocations, so the real-panel case may not deterministically produce JSON when the real cursor is broken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


