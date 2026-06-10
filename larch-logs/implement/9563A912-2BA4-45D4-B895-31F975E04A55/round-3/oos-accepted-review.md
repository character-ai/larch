### OOS_7: [OUT_OF_SCOPE] Bash 3.2 lint does not catch empty-array nounset hazards
- **Reviewer(s)**: dyn-bash32-compat-output.txt
- **Severity**: latent
- **Concern**: `make lint-bash32` scans for documented Bash 4+ syntax tokens but does not detect empty-array expansion under `set -u`, allowing the Step 8 bash-wrapper issue to pass Ubuntu CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-compat-output.txt: Address the concern above.


### OOS_8: [OUT_OF_SCOPE] Step 17 write-final-report failure exits success
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-kv-relay-output.txt
- **Severity**: latent
- **Concern**: `step-17.sh` logs `write-final-report.sh --print-stdout` failures but still exits 0, making failed final-report rendering indistinguishable from success for SKILL routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit exit $_step17_wfr_rc on failure or adjust SKILL contract (separate from wrapperization).
  - From dyn-kv-relay-output.txt: After the failure append, `exit "$_step17_wfr_rc"` (or emit an explicit `WFR_RC=` KV and document token-scan routing); keep the success path unchanged and add a harness case that stubs a failing `write-final-report.sh` and asserts non-zero wrapper exit.


### OOS_9: [OUT_OF_SCOPE] Step 0 resume does not restore fork/upstream flags
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-kv-relay-output.txt
- **Severity**: important
- **Concern**: Dirty-tree resume can restart bootstrap without restoring fork/upstream context, causing forked runs to continue with `FORKED_TARGET=false` or missing `UPSTREAM_REPO` and potentially changing CI base or fetch behavior mid-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Read FORKED_TARGET/UPSTREAM_REPO from session-env.sh or run-flags.sh on --mode resume before invoke, like emergency flag restore.
  - From dyn-kv-relay-output.txt: worth a separate resume/fork follow-up, not a KV-relay defect in the wrappers audited here.


### OOS_10: [OUT_OF_SCOPE] commit-review-fixes --stage-all can include untracked secrets
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The self-review commit path uses `git add -A`, so unrelated untracked secret files in the worktree could be staged and committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Scope staging to reviewed paths or rely on pre-commit secret scanning.


