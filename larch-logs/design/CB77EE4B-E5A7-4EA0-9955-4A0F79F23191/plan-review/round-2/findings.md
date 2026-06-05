### FINDING_1:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/compute-pr-line-counts.sh:1
- **Concern**: New runtime helper may not be executable while write-final-report is planned to call it directly. Scenario: If the file lands mode 0644, the non-fatal helper call returns 126 and every final report silently renders Lines (PR diff): N/A; test-write-final-report can miss this because the plan chmods the copied fake-plugin helper
- **Proposed resolution**: Ensure the new helper is executable in git and make test-compute-pr-line-counts assert [ -x "$HELPER" ] and invoke it directly rather than via bash, so the shipped mode is covered

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:52-67; agent-lint.toml:297-302
- **Concern**: The plan excludes only the new Makefile-only harness, but the new runtime helper is also hidden from agent-lint reachability because it will be invoked through a variable-expanded `$PLUGIN_ROOT/scripts/...` path.. Scenario: `make lint` can still fail G004/dead-script on `scripts/compute-pr-line-counts.sh` or its sibling contract even though `write-final-report.sh` calls it at runtime.
- **Proposed resolution**: Extend the planned `agent-lint.toml` block to also exclude `scripts/compute-pr-line-counts.sh` and `scripts/compute-pr-line-counts.md` with a short runtime-helper rationale, or add an equivalent structural reference; the exclude is the smaller change.

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/write-final-report.sh:101-102
- **Concern**: Planned line-count wiring does not gate on REPO_UNAVAILABLE before using an empty --repo fallback. Scenario: When REPO_UNAVAILABLE=true and PR_NUMBER is still present, compute-pr-line-counts.sh can be invoked with --repo "" and use gh's repos/{owner}/{repo} placeholder expansion from the current checkout, so the final report can show line counts for an unrelated local repo/PR instead of N/A
- **Proposed resolution**: Add a cheap guard in write-final-report.sh: if REPO_UNAV=true then skip the helper and leave line fields empty/LINES_STATUS unavailable; add a test-write-final-report case with REPO_UNAVAILABLE=true, nonzero PR_NUMBER, and a gh shim that fails if called

### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/write-final-report.sh:101-102
- **Concern**: Plan says repo-unavailable should degrade to N/A but still calls compute-pr-line-counts with the resolved repo and PR, with no explicit skip when REPO_UNAVAILABLE=true.. Scenario: If REPO_UNAVAILABLE=true and PR_NUMBER is nonzero, the helper can still use current repo context or a stale REPO and make a GitHub API call; the final report may show counts instead of the required N/A.
- **Proposed resolution**: In write-final-report, set LINES_STATUS=unavailable/skipped and do not invoke the helper when REPO_UNAV=true; add a harness case with REPO_UNAVAILABLE=true and nonzero PR whose gh shim fails if called and asserts Lines (PR diff): N/A.

### FINDING_5:
- **Reviewer(s)**: Codex-dyn-script-kv-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/write-final-report.sh:86-103
- **Concern**: The plan does not gate the new helper when REPO_UNAVAILABLE=true. Scenario: With REPO_UNAVAILABLE=true and empty REPO, compute-pr-line-counts.sh would be called with --repo "" and may use gh placeholder expansion for the ambient repo, rendering concrete line counts instead of the planned N/A
- **Proposed resolution**: When REPO_UNAV=true, skip the helper and set LINES_STATUS=unavailable or leave line args empty

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-script-kv-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/compute-pr-line-counts.sh:planned; skills/implement/scripts/write-final-report.sh:406-455
- **Concern**: The planned KV contract does not require zero-coerced bucket counters or all-four integer validation before passing line flags. Scenario: An all-code, all-log, or binary-only PR can leave one awk bucket empty; LINES_STATUS=ok could then pass blank values and render misleading partial counts such as larch-logs +/-
- **Proposed resolution**: Initialize/coerce awk counters to 0 and only build line_args when LINES_STATUS=ok and all four parsed values are non-empty integers; otherwise omit line flags for N/A

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-caller-surface-audit
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:65-67
- **Concern**: The plan excludes only the new Makefile-only test harnesses, but not the new runtime helper. Agent-lint G004 does not follow shell-to-shell calls, and compute-pr-line-counts.sh would only be reached from write-final-report.sh.. Scenario: make lint / agent-lint can flag scripts/compute-pr-line-counts.sh and its sibling md as dead despite the runtime call.
- **Proposed resolution**: Add scripts/compute-pr-line-counts.sh and scripts/compute-pr-line-counts.md to the same agent-lint.toml exclude block with a comment that write-final-report.sh is the runtime caller and G004 cannot discover that shell edge.
