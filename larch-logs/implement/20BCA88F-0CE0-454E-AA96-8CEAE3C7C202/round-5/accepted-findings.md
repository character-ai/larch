### FINDING_1: Three Tier 2 issue-comment callsites still lack transient retry
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/clarify-comment-post.sh`, `scripts/tracking-issue-summary.sh`, and `scripts/tracking-issue-write.sh` still post `gh issue comment` single-shot despite the plan requiring Tier 2 `with_transient_retry` coverage. This leaves `/design` clarify and tracking-comment writes vulnerable to first transient GitHub API failure, and the clarify script now also has a misleading unused `lib-net.sh` source.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


### FINDING_15: Design-log-publish temp files are not fully cleaned up
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-log-publish.sh` creates `list_fail_file` and `view_fail_file` without adding them to `wt_cleanup`, so early exits can leave temp files under `TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: Changelog omits retry and publish behavior changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `CHANGELOG.md` does not mention the primary behavioral changes on the branch, including the `with_transient_retry` lift, wrapped callsites, and design-log-publish cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


