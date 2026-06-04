### FINDING_11: [OUT_OF_SCOPE] Harness head-OID modeling can diverge from pushed worktree
- **Reviewer(s)**: dyn-gh-stub-output.txt
- **Severity**: latent
- **Concern**: The harness models `headRefOid` from `TEST_CLONE_ROOT` / `TEST_MERGE_BRANCH`, which can diverge from the publish worktree’s pushed commit if env leaks or branches are mismatched. One related allowlist-failure case was explicitly marked out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-stub-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_12: [OUT_OF_SCOPE] Integration stub does not cover registration polling races
- **Reviewer(s)**: dyn-gh-stub-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-multi-round-integration.sh` uses a slimmer `gh` stub. Reviewers marked full merge-gate race and stale-head behavior as covered elsewhere, so this is an out-of-scope integration coverage gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-stub-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] Push mktemp failure has inconsistent recovery semantics
- **Reviewer(s)**: dyn-temp-cleanup-output.txt
- **Severity**: nit
- **Concern**: `push_fail_file` mktemp failure still exits through `emit_publish_result false` / `exit 0` rather than the newer `emit_publish_failure` / `exit 1` path. Reviewer marked this as out of scope for the registration-loop temp cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-cleanup-output.txt: Address the concern above.

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] Automated publish increases operational exposure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Re-enabling automated publish increases how often trimmed/redacted design artifacts land on the default branch via admin merge. The reviewer marked this as product intent and pre-existing operational risk, not a gate bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] Admin merge still bypasses human review
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-log-publish.sh` still relies on admin merge privileges and GitHub branch-protection semantics. The reviewer marked this as unchanged and documented behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] Plan-review collector stderr refactor is unrelated
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-publish-state-output.txt
- **Severity**: nit
- **Concern**: The plan-review collector stderr handling changed in the same branch, but reviewers marked it as unrelated to the publish/merge-gate work and primarily a robustness or diagnostic concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-publish-state-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

