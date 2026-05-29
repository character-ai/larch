### FINDING_10: [OUT_OF_SCOPE] SLEEP_SCRIPT_DIR can redirect retry sleep executable
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-net.sh:57-58` executes `"${SLEEP_SCRIPT_DIR:-$_lib_net_dir}/sleep-seconds.sh"` when executable, so a poisoned operator environment could redirect backoff execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_5: [OUT_OF_SCOPE] Remaining bare network calls
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Several pre-existing `gh`/`git` call sites outside the changed rebase-push/create-pr/merge-pr paths still lack `with_transient_retry`, including `create-pr.sh` PR view fallbacks and other scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_6: [OUT_OF_SCOPE] refresh_pr_info temp-file churn
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/merge-pr.sh:113-125` repeatedly creates and removes temp files inside the UNKNOWN recovery loop, adding unnecessary churn on slow UNKNOWN paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_7: [OUT_OF_SCOPE] no such host matcher overmatches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-net.sh:10-15` uses a bare substring match for `no such host`, so unrelated messages such as `no such hostname` may be classified as transient network failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_8: [OUT_OF_SCOPE] Text fallback lacks transient-once test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/merge-pr.sh:181-194` has no regression case proving the text-only fallback path recovers after a single transient failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_9: [OUT_OF_SCOPE] PR URL regex fallback trusts CLI text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/create-pr.sh:218-221` still falls back to extracting a PR URL from `gh pr create` stderr/stdout with a regex when list recovery yields no number or URL, trusting CLI text as authoritative PR identity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


