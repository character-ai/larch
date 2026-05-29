### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Wrapped issue comments can duplicate after lost-success responses
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/audit-runs/scripts/audit-close-priors.sh` and `skills/design/scripts/decompose-file-issues.sh` wrap `gh issue comment` without an idempotency guard. If GitHub accepts the comment but the client sees a transient failure, retry can post duplicate supersede or decompose comments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Branch scope bundles unrelated changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The PR stack appears to include unrelated awk lint and ship-pr vendor changes alongside transient-retry work, increasing rollback and regression risk if the retry fix needs to ship independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Rebase push can multiply retry attempts inside lease loop
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/rebase-push.sh` nests transient retry inside an existing lease retry loop, allowing up to 9 push attempts plus backoff during sustained outages. This may exceed caller timeout expectations and currently lacks focused harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Retry capture boilerplate is duplicated across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Multiple scripts repeat `mktemp` plus `with_transient_retry` plus `_WTR_*` capture patterns, making future retry-contract changes harder and more error-prone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Ship-pr post-rebump title retry is effectively silent or weakened
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/ship-pr.sh` wraps the post-rebump `gh pr edit`, but redirects output and ignores the result, so transient failures can leave the PR title stale without useful signal and may not follow the documented `_WTR_RC` capture contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: Design-log-publish push failure paths may skip result envelope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Some `scripts/design-log-publish.sh` push-failure exits may return exit 1 without emitting `PUBLISH_RESULT=false`, unlike create/list failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Test-lib-net duplicates production ship-pr wrapper
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lib-net.sh` tests a duplicated `ship_pr_with_transient_retry` helper instead of the production `scripts/ship-pr.sh` wrapper, so future production wrapper regressions may pass the lib-net harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Design-log-publish lacks exhausted PR-create cleanup coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/design-log-publish.sh` retries `gh pr create` without enough duplicate-PR recovery and lacks a harness for exhausted transient create failures followed by empty PR list. A lost-success create could lead cleanup to delete the pushed branch while a PR exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

