# Review Round 3

- Mode: `diff`
- 8 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: tracking issue append comments lack transient retry
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/tracking-issue-write.sh` append-comment still calls `gh issue comment` without `with_transient_retry`, so transient GitHub API failures can drop lifecycle comments immediately despite the Tier-2 retry requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: create-pr push failure logs may expose credentials
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/create-pr.sh` logs unredacted wrapper push failure output; credential-helper or tokenized remote URL data in git stdout/stderr could appear in implement `larch_err` output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_2: tracking issue summary create comments lack transient retry
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/tracking-issue-summary.sh` wraps PATCH updates but not the first-summary `gh issue comment` create path, so initial summary creation can fail on a single transient GitHub error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: clarify comments lack transient retry
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/clarify-comment-post.sh` sources `lib-net.sh` but posts `gh issue comment` as a bare one-shot command, so clarify round-trips can still fail on transient GitHub hiccups without retry/backoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: ship-pr transient exhaustion path lacks direct test coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-lib-net.sh` does not directly cover `ship_pr_with_transient_retry` when all attempts return nonzero with transient signatures, so regressions in the return-style path to exit 6 could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: design-log publish cleanup skipped after inconclusive PR recovery
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: In `scripts/design-log-publish.sh`, if push succeeds, `gh pr create` fails, and the subsequent `gh pr list` recovery probe also fails, remote branch cleanup is skipped; a full script retry may then hit a non-fast-forward branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: design-log publish lacks end-to-end transient-success harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-log-publish.sh` lacks a harness case where `gh pr create` succeeds after transient failures, leaving the incident reproduction path unverified end-to-end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: merge-pr may log unredacted retry failure text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `scripts/merge-pr.sh` embeds raw `with_transient_retry` fail-file text in `larch_err` and stdout `ERROR=`, so GitHub auth/proxy errors that echo secrets could flow into ship-pr results and run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


