### FINDING_1: Three Tier 2 issue-comment callsites still lack transient retry
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/clarify-comment-post.sh`, `scripts/tracking-issue-summary.sh`, and `scripts/tracking-issue-write.sh` still post `gh issue comment` single-shot despite the plan requiring Tier 2 `with_transient_retry` coverage. This leaves `/design` clarify and tracking-comment writes vulnerable to first transient GitHub API failure, and the clarify script now also has a misleading unused `lib-net.sh` source.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Branch scope bundles unrelated changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The PR stack appears to include unrelated awk lint and ship-pr vendor changes alongside transient-retry work, increasing rollback and regression risk if the retry fix needs to ship independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Changelog omits retry and publish behavior changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `CHANGELOG.md` does not mention the primary behavioral changes on the branch, including the `with_transient_retry` lift, wrapped callsites, and design-log-publish cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Rebase push can multiply retry attempts inside lease loop
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/rebase-push.sh` nests transient retry inside an existing lease retry loop, allowing up to 9 push attempts plus backoff during sustained outages. This may exceed caller timeout expectations and currently lacks focused harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Retry capture boilerplate is duplicated across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Multiple scripts repeat `mktemp` plus `with_transient_retry` plus `_WTR_*` capture patterns, making future retry-contract changes harder and more error-prone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Ship-pr post-rebump title retry is effectively silent or weakened
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/ship-pr.sh` wraps the post-rebump `gh pr edit`, but redirects output and ignores the result, so transient failures can leave the PR title stale without useful signal and may not follow the documented `_WTR_RC` capture contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: Design-log-publish push failure paths may skip result envelope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Some `scripts/design-log-publish.sh` push-failure exits may return exit 1 without emitting `PUBLISH_RESULT=false`, unlike create/list failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: Test-lib-net duplicates production ship-pr wrapper
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lib-net.sh` tests a duplicated `ship_pr_with_transient_retry` helper instead of the production `scripts/ship-pr.sh` wrapper, so future production wrapper regressions may pass the lib-net harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Design-log-publish lacks exhausted PR-create cleanup coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/design-log-publish.sh` retries `gh pr create` without enough duplicate-PR recovery and lacks a harness for exhausted transient create failures followed by empty PR list. A lost-success create could lead cleanup to delete the pushed branch while a PR exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Relevant-checks does not map lib-net changes to test-lib-net
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/relevant-checks.sh` lacks a mapping from `lib-net.sh` and related docs/tests to `test-lib-net`, so scoped local checks can miss retry helper regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Transient signature fixtures are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-lib-net.sh` does not include positive fixtures for all documented transient signatures, so some matcher regressions may only be caught indirectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: New test-lib-net target is undocumented
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` does not document the new `test-lib-net` target, making it less discoverable for contributors debugging retry behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Close-path retry logs unredacted GitHub stderr
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/combine-issues/scripts/apply-combination.sh` appends unredacted `gh` close stderr from the retry fail file to warnings, which can leak token-shaped diagnostics across repeated attempts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Wrapped issue comments can duplicate after lost-success responses
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/audit-runs/scripts/audit-close-priors.sh` and `skills/design/scripts/decompose-file-issues.sh` wrap `gh issue comment` without an idempotency guard. If GitHub accepts the comment but the client sees a transient failure, retry can post duplicate supersede or decompose comments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Design-log-publish temp files are not fully cleaned up
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-log-publish.sh` creates `list_fail_file` and `view_fail_file` without adding them to `wt_cleanup`, so early exits can leave temp files under `TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Merge-pr read calls remain unwrapped
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/merge-pr.sh` leaves `gh pr view` and `gh pr checks` calls without transient retry. Reviewers marked this as pre-existing or outside the current plan scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Rebase no-push fetch remains unwrapped
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/rebase-push.sh --no-push` still hard-fails a bare `git fetch` without transient retry. Reviewer marked this as pre-existing and outside the current plan file list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Create-pr failure diagnostics are unredacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/create-pr.sh` logs raw PR create stderr/stdout-tail diagnostics without redaction on failure. Reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Issue create failure emits unredacted output
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/combine-issues/scripts/apply-combination.sh` emits unredacted `CREATE_OUT` on issue-create failure. Reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Create-pr lost-success duplicate risk remains
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/create-pr.sh` wraps `gh pr create` and has recovery, but a lost-success duplicate-PR risk may remain if recovery misses; reviewer marked this as not introduced solely by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
