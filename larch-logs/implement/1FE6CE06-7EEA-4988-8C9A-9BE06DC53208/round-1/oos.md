### FINDING_17: [OUT_OF_SCOPE] `design-publish.sh` may trust `PUBLISH_OK=true` despite non-zero publish exit
- **Reviewer(s)**: dyn-bash-contract-output.txt
- **Severity**: important
- **Concern**: If `design-log-publish.sh` exits non-zero while stdout contains `PUBLISH_OK=true`, failure branches may be skipped and rename may proceed; reviewer marked this as restored pre-existing envelope behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contract-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] No post-registration head recheck before watch or merge
- **Reviewer(s)**: dyn-bash-contract-output.txt
- **Severity**: latent
- **Concern**: After registration succeeds, the script relies on GitHub’s live PR-head behavior during watch/merge rather than independently rechecking `headRefOid`; reviewer treated this as reasonable for a bot-only branch and out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] Completion watch remains unbounded
- **Reviewer(s)**: dyn-gh-ci-gate-output.txt
- **Severity**: latent
- **Concern**: `gh pr checks --watch` can hang indefinitely after registration succeeds if a required job never completes; reviewer marked this as pre-existing and orthogonal to the registration race fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-ci-gate-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] Registration treats any non-empty JSON array as registered
- **Reviewer(s)**: dyn-gh-ci-gate-output.txt
- **Severity**: latent
- **Concern**: The registration predicate does not require specific pending/in-progress buckets, only a non-empty JSON array; reviewer noted this matches the plan but depends on `gh` representing required checks correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-ci-gate-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_22: [OUT_OF_SCOPE] Removed sleep stub directories can cause slow later tests
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: latent
- **Concern**: Some cases remove tempdirs while `SLEEP_SCRIPT_DIR` may still point at a deleted no-op sleep stub, causing later multi-probe tests to fall back to real sleeps; reviewer marked this as mostly masked today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] Duplicate gh stubs increase long-term drift
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: latent
- **Concern**: Separately embedded `gh` stubs across harnesses increase future drift risk; reviewer surfaced this as an out-of-scope architecture observation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] Publish envelope unit tests do not exercise merge gate
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-design-publish.sh` stubs `design-log-publish.sh` and therefore does not exercise the merge gate; reviewer considered this appropriate for that unit harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_26: [OUT_OF_SCOPE] Post-publish render runs before issue rename
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: latent
- **Concern**: Post-publish rendering and tracking-issue summary upsert run before `[DESIGNED]` rename; reviewer marked this ordering as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] Post-publish render keeps approved outcome when publish fails
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: nit
- **Concern**: The post-publish render uses `--outcome approved` even when `PUBLISH_OK=false`; reviewer treated this as matching the documented Gate-C vs log-flush split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Address the concern above.

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_5: [OUT_OF_SCOPE] Worktree cleanup precedes merge failure handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: On merge failure, the remote branch remains for recovery but local worktree state is already removed before the final `merge_rc` check; reviewers marked this as pre-existing recovery ergonomics, not a regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] Fixed registration budget may still false-fail on slow GitHub registration
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A 300-second registration budget can still false-fail if GitHub is unusually slow to register checks; this was identified as an accepted trade-off rather than a new blocker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

