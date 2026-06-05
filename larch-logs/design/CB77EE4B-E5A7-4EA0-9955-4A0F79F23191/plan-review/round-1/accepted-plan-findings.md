### FINDING_1: Optional repo fallback uses invalid gh api endpoint
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Requirements
- **Severity**: latent
- **Concern**: The planned empty `--repo` path relies on omitting owner/name from a `repos/.../pulls/.../files` endpoint, but `gh api` will not infer the current repository from that shape, causing valid runs to degrade to unavailable/N/A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use repos/{owner}/{repo}/pulls/<N>/files when --repo is empty, or set GH_REPO for the call; keep repos/<owner>/<name>/... only when --repo is nonempty
  - From Codex-Edge: For empty --repo, use gh api --paginate "repos/{owner}/{repo}/pulls/$PR_NUMBER/files"; keep "repos/$REPO/pulls/$PR_NUMBER/files" only when REPO is non-empty, and add an offline stub assertion for the empty-repo endpoint.
  - From Codex-Innovation: Use repos/{owner}/{repo}/pulls/$PR_NUMBER/files when --repo is empty, or resolve/set GH_REPO; keep repos/$REPO/pulls/$PR_NUMBER/files only when --repo is nonempty
  - From Codex-Requirements: Specify repos/{owner}/{repo}/pulls/$PR_NUMBER/files or set GH_REPO when --repo is empty; keep repos/$REPO/pulls/$PR_NUMBER/files when --repo is set


### FINDING_2: Final-report harness fixture omits new helper and gh isolation
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The planned final-report e2e tests run against a fake plugin root but do not fully wire the new line-count helper and gh shim, so tests can hit command-not-found, render Lines N/A, or invoke real gh/network.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add compute-pr-line-counts.sh to the fixture copy/chmod setup before adding the bucketed summary assertion
  - From Cursor-Requirements: In test-write-final-report.sh initial plugin setup, cp/chmod scripts/compute-pr-line-counts.sh into $plugin/scripts/ alongside the other copied helpers, and install the PATH gh shim for every fixture that sets a nonzero PR_NUMBER (not only the new case)
  - From Codex-Requirements: Copy/chmod compute-pr-line-counts.sh into the fake plugin and install a PATH gh shim for all helper-invoking cases, with explicit fixtures for bucketed output and N/A paths


### FINDING_3: Optional line-count argv expansion may break on Bash 3.2
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The planned optional line-count arguments are not specified with a Bash 3.2-safe empty-array expansion, so macOS Bash with `set -u` can abort no-PR/offline final-report rendering instead of producing Lines N/A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use the guarded ${arr[@]+"${arr[@]}"} idiom for any optional line_args array, or fold the flags into an argv array that is never empty.
  - From Codex-Requirements: Use the guarded ${line_args[@]+"${line_args[@]}"} idiom or append line flags directly to a non-empty renderer argv


### FINDING_4: New Makefile-only harness pair missing agent-lint excludes
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan omits `agent-lint.toml` exclude entries for the new Makefile-only test harness files, so dead-script reachability checks can fail during relevant checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add scripts/test-compute-pr-line-counts.sh and scripts/test-compute-pr-line-counts.md to agent-lint.toml exclude with the same comment block used for scripts/test-compose-pr-summary.sh

