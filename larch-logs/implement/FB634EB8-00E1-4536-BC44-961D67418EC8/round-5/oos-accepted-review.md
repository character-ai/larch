### FINDING_13: [OUT_OF_SCOPE] Pre-rebase flush proceeds after manifest recovery failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Python ship loop can exempt `REFRESH_SKIP_RECOVERY_FAILED` from stall gating and proceed into rebase/push work despite failed run-log manifest recovery, unlike stricter post-flush handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_14: [OUT_OF_SCOPE] Postmerge report can be rendered before manifest done write
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` writes or renders final report artifacts before successfully writing `status=done`/`pr_number` to `manifest.json`, allowing summary output to claim completion while the manifest remains partial or failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] Timing harness targets added to unrelated shard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Unrelated Makefile timing harness changes increase CI time/flake risk on a finalize-focused branch without testing finalize behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


### FINDING_19: [OUT_OF_SCOPE] Merge parity lacks symmetric fail-closed gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Docs imply both merge and finalize bash parity fail closed, but merge parity can still all-skip green if module marks broaden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


### FINDING_22: [OUT_OF_SCOPE] `_write_ship_state` lacks newline validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: GitHub-derived KV fields written to `ship-pr-state.sh` are not newline-validated like finalize state, so multiline values could corrupt parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


