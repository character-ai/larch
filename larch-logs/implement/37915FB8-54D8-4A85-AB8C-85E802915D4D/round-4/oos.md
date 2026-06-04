### FINDING_12: [OUT_OF_SCOPE] Limit counts directories instead of parseable runs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: `LARCH_REPORT_TOKENS_LIMIT` is consumed by every run directory, including empty/invalid ones, so a limit can stop scanning before later valid runs are parsed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scan-pipeline-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Empty manifest/report warnings are misleading
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: Empty manifest/report objects reuse missing-field warnings, causing operators to misdiagnose empty JSON as a missing `issue_number` or missing tokens condition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-scan-pipeline-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_1: Plot date axis differs from per-day table date basis
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-token-pricing-output.txt, dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: Plot series use `closed_at` while per-day tables use `started_at`, so long-running issues can disagree; reviewers noted this is pre-existing/plan-documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-token-pricing-output.txt, dyn-scan-pipeline-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: Plot subprocess stderr is unredacted
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: latent
- **Concern**: Plot child failures echo subprocess stderr without redaction, adjacent to but outside the issue-create path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_11: Local cache NDJSON contains unredacted manifest titles
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: latent
- **Concern**: Local cache NDJSON can include unredacted manifest titles and its path is echoed via the `Cache JSON:` trailer, though it is not posted to GitHub.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_12: Duplicate issue numbers are still aggregated
- **Reviewer(s)**: dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: Multiple run directories with the same `issue_number` are aggregated without deduplication; reviewer noted this is plan-documented and matches old behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scan-pipeline-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_13: `LARCH_REPORT_TOKENS_NO_OPEN` truthiness differs from no-plot flag parsing
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: `NO_OPEN` uses raw environment truthiness while `NO_PLOT` uses flag parsing, so values like `0`/`false` behave differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_14: Matplotlib isolation appears sound
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that runtime Python remains stdlib-only, matplotlib imports are isolated to the child script, child failures degrade cleanly, and returned paths are constrained to the persistent plot temp dir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_15: `test-merge-parity` lacks a secondary `.PHONY` entry
- **Reviewer(s)**: dyn-ci-surface-output.txt
- **Severity**: nit
- **Concern**: `test-merge-parity` is wired into harness execution but absent from the secondary `.PHONY` block; reviewer marked this as Make hygiene, not a CI functional break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-surface-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_16: pytest is installed on all harness shards
- **Reviewer(s)**: dyn-ci-surface-output.txt
- **Severity**: nit
- **Concern**: Installing `pytest==9.0.3` on every harness shard adds pip work to unrelated shards; reviewer called this an acceptable trade-off, not a report-tokens correctness defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-surface-output.txt: Address the concern above.

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_2: Report-token temp directories are intentionally retained
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Repeated local runs accumulate `larch-report-tokens` temp directories, but this was noted as intentional for cache JSON and PNG lifetime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_3: Per-bucket happy path appears correct
- **Reviewer(s)**: dyn-token-pricing-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that successful per-vendor mixed bucket argv construction, KV parsing, and rate forwarding align with existing expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: Quiet wrapper restores stderr before Python
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that the wrapper’s `exec 1>&3 2>&4` before Python correctly fixes a prior quiet-mode FD gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: Quiet-mode stderr conventions otherwise match contract
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that pre-restore bash errors and post-restore Python stderr diagnostics follow the quiet-mode contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: Issue success output follows analysis block
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: latent
- **Concern**: Reviewer noted that successful issue posting emits the issue URL after the analysis block, while callers must still check exit codes for late failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_7: Issue-posting pipeline is materially improved
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed improvements including removal of raw JSON issue appendix, post-redaction trim sizing, loud failure on oversize/gh errors, slug validation, and tmpdir scrubbing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: Synthesized issue URLs are not verified against repository state
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: latent
- **Concern**: Issue URLs are built from `repo_slug` and issue number without verifying the issue exists in that repository, so wrong repo configuration can produce misleading links.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_9: Phase step strings still flow into posted markdown
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: latent
- **Concern**: Phase-breakdown `step` strings still reach posted markdown tables after secret-pattern redaction; reviewer marked this as pre-existing and reduced by dropping raw JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

