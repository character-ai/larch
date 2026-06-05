### FINDING_1: Helper executable bit not covered
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The new runtime helper may ship without executable permissions even though the final-report script is expected to call it directly, causing line counts to silently degrade to N/A while tests miss the shipped mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Ensure the new helper is executable in git and make test-compute-pr-line-counts assert [ -x "$HELPER" ] and invoke it directly rather than via bash, so the shipped mode is covered


### FINDING_2: Runtime helper hidden from agent-lint reachability
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-caller-surface-audit
- **Severity**: important
- **Concern**: The plan excludes only the new Makefile-only harnesses, but the new runtime helper and its sibling contract may still be flagged as dead because agent-lint cannot discover the variable-expanded shell-to-shell runtime call from write-final-report.sh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Extend the planned `agent-lint.toml` block to also exclude `scripts/compute-pr-line-counts.sh` and `scripts/compute-pr-line-counts.md` with a short runtime-helper rationale, or add an equivalent structural reference; the exclude is the smaller change.
  - From Codex-dyn-caller-surface-audit: Add scripts/compute-pr-line-counts.sh and scripts/compute-pr-line-counts.md to the same agent-lint.toml exclude block with a comment that write-final-report.sh is the runtime caller and G004 cannot discover that shell edge.


### FINDING_3: Repo-unavailable path can still call GitHub helper
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements, Codex-dyn-script-kv-contract
- **Severity**: important
- **Concern**: The planned line-count wiring does not explicitly skip compute-pr-line-counts.sh when REPO_UNAVAILABLE=true, so a nonzero PR number plus empty or stale repo context can still trigger a GitHub API call and render counts from the ambient or wrong repository instead of N/A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a cheap guard in write-final-report.sh: if REPO_UNAV=true then skip the helper and leave line fields empty/LINES_STATUS unavailable; add a test-write-final-report case with REPO_UNAVAILABLE=true, nonzero PR_NUMBER, and a gh shim that fails if called
  - From Codex-Requirements: In write-final-report, set LINES_STATUS=unavailable/skipped and do not invoke the helper when REPO_UNAV=true; add a harness case with REPO_UNAVAILABLE=true and nonzero PR whose gh shim fails if called and asserts Lines (PR diff): N/A.
  - From Codex-dyn-script-kv-contract: When REPO_UNAV=true, skip the helper and set LINES_STATUS=unavailable or leave line args empty


### FINDING_4: Line-count KV contract can pass blank counters
- **Reviewer(s)**: Codex-dyn-script-kv-contract
- **Severity**: important
- **Concern**: The planned helper/caller contract does not require all line-count buckets to be zero-coerced and validated as integers before rendering, so PRs lacking one bucket can produce misleading partial counts instead of N/A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-script-kv-contract: Initialize/coerce awk counters to 0 and only build line_args when LINES_STATUS=ok and all four parsed values are non-empty integers; otherwise omit line flags for N/A

