### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: ISSUE_NUMBER accepts zero
- **Reviewer(s)**: dyn-bash-kv-output.txt
- **Severity**: latent
- **Concern**: Canonical issue number validation accepts `0`, which could be written to `stall-recovery-issue.env` and later used by `gh issue comment`, even though real `/larch:issue` output should never emit zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-kv-output.txt: Reject `issue_number` unless it matches `^[1-9][0-9]*$` (and the same for `duplicate_number` before fallback).


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: issue stdout normalization has no size bound
- **Reviewer(s)**: dyn-bash-kv-output.txt
- **Severity**: latent
- **Concern**: `--issue-stdout-file` is path-contained but not size-capped before `awk`/`kv_get`, so corrupted or verbose stdout can be loaded into memory during normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-kv-output.txt: Apply the same 64 KiB cap used for failure-detail logs (reject with `issues-stdout-oversize` and stale-env removal) before filtering.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Step-reference ambiguity can misroute fallback handling
- **Reviewer(s)**: dyn-prompt-protocol-output.txt
- **Severity**: latent
- **Concern**: `stall-recovery.md` refers to “Step 8” for fallback/comment behavior while `/implement` also has a prominent Step 8, so an orchestrator may confuse the stall-recovery procedure step with the ship phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-protocol-output.txt: Qualify every in-document step reference as “procedure step 8 (terminal-failure path)” or “step 8 below,” matching the disambiguation style used elsewhere in larch skills.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

