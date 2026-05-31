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

### FINDING_14: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:2274-2277` — `_run_per_job_command_once` still uses the pre-change `cmd > log 2>&1` pattern without `||` hardening; if errexit were ever leaked again, verification could still abort before callers handle failure. **Why out of scope:** unchanged by this branch; plan explicitly left it alone.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_15: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/ship-pr.sh:2180-2221` — Arbitrary command execution would require poisoning `_PJA_ARGV` outside `_per_job_argv()`; callers today only set argv through the whitelist dispatcher. **Why out of scope:** pre-existing design surface, not introduced or widened by this diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:2872
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] recovery_waterfall invokes OOS gate without outer set +e; non-zero return with leaked errexit could abort before verify_rc=$?. Only matters if errexit leaks again from elsewhere; not introduced by this branch. Optional follow-up: wrap call in same save/restore pattern or rely on helper-only (already sufficient post-fix).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/test-ship-pr.sh:470-472
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Section list comment omits errexit section. Developers may not know errexit runs in full test-ship-pr invocations. Add errexit to the listed sections when editing that header.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:362-365
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] die_usage exits 2 separate from orchestrator CI table. Unrelated exit 2 can still confuse incident triage. Pre-existing; address in a separate exit-code hygiene change if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

