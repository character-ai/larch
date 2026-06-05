### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:10
- **Concern**: Optional repo fallback uses an ambiguous/invalid gh api endpoint shape. Scenario: If --repo is empty, gh api will not infer the repository from a literal repos/<repo>/... endpoint with the owner/name segment omitted
- **Proposed resolution**: Use repos/{owner}/{repo}/pulls/<N>/files when --repo is empty, or set GH_REPO for the call; keep repos/<owner>/<name>/... only when --repo is nonempty

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-write-final-report.sh:45-56
- **Concern**: Planned end-to-end final-report test omits the new helper from the fake plugin fixture. Scenario: write-final-report.sh resolves helpers under CLAUDE_PLUGIN_ROOT, so the new stubbed-gh assertion will render N/A or hit command-not-found unless compute-pr-line-counts.sh is copied into $plugin/scripts
- **Proposed resolution**: Add compute-pr-line-counts.sh to the fixture copy/chmod setup before adding the bucketed summary assertion

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/compute-pr-line-counts.sh (planned; plan.txt:10)
- **Concern**: Empty --repo contract names an invalid gh api shape. Scenario: gh api can fill repos/{owner}/{repo}/... placeholders, but it will not infer a repo from repos//pulls/N/files or pulls/N/files. A valid run with blank REPO but an inferable current repo would degrade to Lines: N/A.
- **Proposed resolution**: For empty --repo, use gh api --paginate "repos/{owner}/{repo}/pulls/$PR_NUMBER/files"; keep "repos/$REPO/pulls/$PR_NUMBER/files" only when REPO is non-empty, and add an offline stub assertion for the empty-repo endpoint.

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/compute-pr-line-counts.sh:NEW
- **Concern**: Optional --repo fallback is invalid as specified. Scenario: The plan says to omit <repo> from repos/<repo>/pulls/<N>/files so gh uses the default remote, but gh api only infers the current repo via {owner}/{repo} placeholders or GH_REPO; dropping that segment yields an invalid endpoint and degrades the documented optional path to N/A
- **Proposed resolution**: Use repos/{owner}/{repo}/pulls/$PR_NUMBER/files when --repo is empty, or resolve/set GH_REPO; keep repos/$REPO/pulls/$PR_NUMBER/files only when --repo is nonempty

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/write-final-report.sh:431-455
- **Concern**: The plan adds conditionally present line-count argv but does not require Bash 3.2-safe empty-array expansion.. Scenario: On macOS Bash 3.2 with set -u, an empty optional array for no-PR/offline paths can raise unbound variable and break final-report rendering.
- **Proposed resolution**: Use the guarded ${arr[@]+"${arr[@]}"} idiom for any optional line_args array, or fold the flags into an argv array that is never empty.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:1612-1617
- **Concern**: Plan omits agent-lint.toml exclude entries for the new Makefile-only harness pair. Scenario: New scripts/test-compute-pr-line-counts.sh and .md match the Makefile-only harness pattern; without agent-lint.toml registration, agent-lint dead-script reachability fails and bash scripts/relevant-checks.sh breaks after the PR
- **Proposed resolution**: Add scripts/test-compute-pr-line-counts.sh and scripts/test-compute-pr-line-counts.md to agent-lint.toml exclude with the same comment block used for scripts/test-compose-pr-summary.sh

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-write-final-report.sh:45-56
- **Concern**: Plan adds a stubbed-gh e2e case but not the plugin fixture wiring the harness already requires. Scenario: write-final-report.sh will invoke $PLUGIN_ROOT/scripts/compute-pr-line-counts.sh while tests set CLAUDE_PLUGIN_ROOT to a fake plugin that today copies render-run-summary.sh and peers but not the new helper; the new case can hit command-not-found or always render Lines N/A instead of bucketed values
- **Proposed resolution**: In test-write-final-report.sh initial plugin setup, cp/chmod scripts/compute-pr-line-counts.sh into $plugin/scripts/ alongside the other copied helpers, and install the PATH gh shim for every fixture that sets a nonzero PR_NUMBER (not only the new case)

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/compute-pr-line-counts.sh:NEW
- **Concern**: Optional repo fallback endpoint is ambiguous/invalid. Scenario: If --repo is empty and PR_NUMBER is nonzero, omitting owner/name from repos/<repo>/pulls/<N>/files will not make gh infer the current repo, so the helper can report unavailable instead of using the default remote
- **Proposed resolution**: Specify repos/{owner}/{repo}/pulls/$PR_NUMBER/files or set GH_REPO when --repo is empty; keep repos/$REPO/pulls/$PR_NUMBER/files when --repo is set

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/write-final-report.sh:406-455
- **Concern**: Optional line-count argv expansion is not pinned as Bash 3.2-safe. Scenario: On macOS Bash 3.2 with set -u, an empty line_args array on no-PR/offline paths can abort rendering instead of producing Lines N/A
- **Proposed resolution**: Use the guarded ${line_args[@]+"${line_args[@]}"} idiom or append line flags directly to a non-empty renderer argv

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-write-final-report.sh:45-56; skills/implement/scripts/test-write-final-report.sh:93-102
- **Concern**: Final-report harness plan does not require the helper fixture and offline gh shim for all PR fixtures. Scenario: The harness runs with CLAUDE_PLUGIN_ROOT=$plugin; without copying compute-pr-line-counts.sh or shielding existing PR-number cases, tests can render N/A, hit command-not-found, or invoke real gh/network
- **Proposed resolution**: Copy/chmod compute-pr-line-counts.sh into the fake plugin and install a PATH gh shim for all helper-invoking cases, with explicit fixtures for bucketed output and N/A paths
