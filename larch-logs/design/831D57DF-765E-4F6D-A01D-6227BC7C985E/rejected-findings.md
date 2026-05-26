### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/merge-pr.sh:18-29
- **Concern**: Helper exit status is always 0 when the while loop exhausts (last command is attempt=$((attempt+1))). Scenario: On exhaustion the function still returns 0; if a call site uses if retry_pr_info_unknown_recovery N or relies on $? instead of re-reading MERGE_STATE, a persistent UNKNOWN/empty state could fall through without setting MERGE_RESULT=error
- **Proposed resolution**: Keep the planned MERGE_STATE re-check at both call sites; add a one-line helper comment that $? must not be used (only MERGE_STATE), or end the helper with explicit return 1 after the loop


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/test-merge-pr.sh:386-397
- **Concern**: G1/G2 plan only asserts MERGE_RESULT=error and command counts; R2 byte-pins the post-force-push ERROR string but the new initial-path suffix after 4 retries is not pinned. Scenario: A future edit could change retry count or ERROR wording without failing G1/G2 while breaking operators/log parsers that match the full string
- **Proposed resolution**: Add assert_stdout_matches anchors for G1/G2 mirroring R2, e.g. ^ERROR=could not read mergeStateStatus .* after 4 retries$


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/merge-pr.sh:119-137
- **Concern**: Four 5-second sleeps on the initial path add up to ~20s wall-clock per merge-pr invocation before error, with no plan note for ship-pr/Step 12b latency. Scenario: Persistent UNKNOWN during ci-merge extends the merge loop materially; unrelated to the no-op sleep stub used only in tests
- **Proposed resolution**: Document the worst-case delay in merge-pr.md and/or add a short comment at the initial call site; consider whether 3 retries (15s, symmetric with post-force-push) meets #2882


