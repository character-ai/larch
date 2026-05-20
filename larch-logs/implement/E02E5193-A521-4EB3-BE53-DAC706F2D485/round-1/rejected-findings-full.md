### [rejected] FINDING_12

### FINDING_12: risk-integration: scripts/ship-pr.sh:951-952
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] ISSUE_NUMBER is interpolated into the PR title without validation or trimming after read_state. Whitespace-only or non-numeric ISSUE_NUMBER (e.g. corrupted state) yields a title like Fixes # : … or Fixes #abc: …; GitHub may not link the issue and operators get a misleading PR title while the flow still succeeds. Trim whitespace and require an all-digit ISSUE_NUMBER before applying the Fixes # prefix; otherwise leave title unchanged or stall loudly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

### FINDING_3: **security** `scripts/ship-pr.sh:951-952` — `issue_num` from `read_state ISSUE_NUMBER` is concatenated into the PR title and later persisted as `PR_TITLE` without checking that it is a plain GitHub issue id (for example digits-only). That does not bypass the quoting chain into `gh`, but a malformed or hand-edited state value yields a misleading `Fixes #…` title and weakens the guarantee that the prefix refers to a real issue the way operators expect. The new test in `scripts/test-ship-pr.sh:132-140` only covers a numeric issue and does not exercise rejection or stripping of invalid values. **Suggested fix:** Before applying the prefix, require a safe pattern (for example `case "$issue_num" in ''|*[!0-9]*) ;; *) title="Fixes #${issue_num}: ${title}";; esac`) or reuse a single small validator shared with other `ISSUE_NUMBER` uses, and optionally add a regression test for a non-numeric value so the prefix is skipped and a warning is logged.
- **Reviewer**: dyn-issue-num-injection-output.txt
- **Concern**: - **security** `scripts/ship-pr.sh:951-952` — `issue_num` from `read_state ISSUE_NUMBER` is concatenated into the PR title and later persisted as `PR_TITLE` without checking that it is a plain GitHub issue id (for example digits-only). That does not bypass the quoting chain into `gh`, but a malformed or hand-edited state value yields a misleading `Fixes #…` title and weakens the guarantee that the prefix refers to a real issue the way operators expect. The new test in `scripts/test-ship-pr.sh:132-140` only covers a numeric issue and does not exercise rejection or stripping of invalid values. **Suggested fix:** Before applying the prefix, require a safe pattern (for example `case "$issue_num" in ''|*[!0-9]*) ;; *) title="Fixes #${issue_num}: ${title}";; esac`) or reuse a single small validator shared with other `ISSUE_NUMBER` uses, and optionally add a regression test for a non-numeric value so the prefix is skipped and a warning is logged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

### FINDING_8: code-quality: scripts/ship-pr.sh:946-948
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] tail -1 on git log pipeline drains entire filtered history Large merge-base..HEAD (or long HEAD fallback) forces a full log scan on each pr-create instead of stopping at the first eligible line Use git log --reverse with the same grep filter and head -1 to select the oldest non-flush subject without reading the whole list
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

