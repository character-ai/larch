### OOS_1: [OUT_OF_SCOPE] read-result-env failure discards captured stdout
- **Reviewer(s)**: dyn-handoff-status-output.txt
- **Severity**: latent
- **Concern**: When `read-result-env.sh` exits non-zero (~414–425), the wrapper deletes `_plan_review_stdout_file` before the stdout merge loop, discarding any `STEP3_REVIEW_LOOP_STATUS` lines already written there by `emit_kv` and forcing `panel-failed`. Pre-dates the new back-map guard; can still mask operational statuses on persist/read failures even when the loop emitted them to the quiet FD 3 capture stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot provided a concrete fix direction beyond “Address the concern above”)


