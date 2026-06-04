### FINDING_11: PR URL validation is too strict for repo case and GHES hosts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-output.txt
- **Severity**: important
- **Concern**: `_repo_matches_pr_url` can reject real PR URLs because it compares repo slugs case-sensitively and hardcodes `github.com`, breaking mixed-case repos or GitHub Enterprise hosts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-output.txt: Address the concern above.


### FINDING_13: Post-recovery merge forces another CI loop after successful OID sync
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: After flush recovery verifies the refreshed PR head OID/checks, merge still returns `CI_NOT_READY` when the OID changed, contradicting the plan’s single-cycle convergence expectation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: Missing regression test for single-CI-cycle merge convergence
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests assert `merge_pr` does not call `flush_logs_pre`, but do not bound CI/check iterations on a clean green path, so churn causing multiple CI cycles could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_16: Refresh sidecar pipeline can still dirty non-volatile batch files
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-git-porcelain-output.txt
- **Severity**: important
- **Concern**: `flush_logs_pre` renders token/timing batch NDJSON before volatile classification, so live refresh-only sidecars can still produce non-volatile commits and diverge HEAD from the green PR OID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-git-porcelain-output.txt: Address the concern above.


### FINDING_17: Breadcrumb exception details are not redacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Breadcrumbs can emit raw `str(exc)` to stderr/quiet sinks without `redact_outbound`, leaking paths or secret-shaped substrings outside the redacted JSON contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_20: Merge loop lacks an iteration ceiling
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Repeated `CI_NOT_READY` after force-push can spin indefinitely without returning `STALLED` JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_23: URL fallback requires an immediate successful `pr_view`
- **Reviewer(s)**: dyn-gh-cli-output.txt
- **Severity**: important
- **Concern**: Post-create URL recovery can fail if `pr_view` transiently reports not found while stdout already contains a valid PR URL and `pr list` is still lagging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-output.txt: Address the concern above.


### FINDING_28: Secret scrub warnings bypass quiet routing
- **Reviewer(s)**: dyn-stream-protocol-output.txt
- **Severity**: latent
- **Concern**: `_warn_secret_scrub` writes directly to stderr instead of the BreadcrumbWriter/lib-quiet channel, so credential-rotation warnings can be missed in quiet sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-protocol-output.txt: Address the concern above.


