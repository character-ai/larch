# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (6 neutral)

## Accepted Findings

### FINDING_2: Non-GitHub origins are accepted as GitHub repositories
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-repo-resolution-contract
- **Severity**: major
- **Concern**: `_origin_repo_candidate` can promote GitLab, GHE, SSH-alias, or other non-GitHub remote paths into valid GitHub slugs, potentially routing `gh --repo` operations to the wrong repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Require GitHub-recognized parsing before marking a candidate valid and test non-GitHub remotes
  - From dyn-dyn-repo-resolution-contract: Treat `remote_repo()` success as the only valid acceptance path for origin fallback. Use `_raw_remote_path_candidate()` only to preserve a non-empty invalid candidate for `resolve_repo_detailed` consumers (`clarify`, diagnostics), not to promote arbitrary host paths to valid slugs. Add regression tests with GitLab/non-GitHub `origin` URLs asserting `status != "valid"`.


### FINDING_6: Detailed valid candidates bypass strict slug validation
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: Detailed valid candidates may bypass stricter repository-slug validation and allow malformed owners such as `owner/.` or `owner/..` into report URLs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Revalidate with _valid_repo_slug or strengthen the shared validator and add regression tests
