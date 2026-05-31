### FINDING_12: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:363-365
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] die_usage still exits 2 outside documented orchestrator table. Unrelated argv errors can still produce undocumented exit 2. Track separately if orchestrator table should cover usage errors.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_13: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.sh:2274-2276
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] _run_per_job_command_once not hardened for errexit. Safe today only while every call stays under if; a future bare call could reintroduce raw exit codes. Harden or add test only if call sites change; pre-existing.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


