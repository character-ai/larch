# Review Round 2

- Mode: `diff`
- Accepted findings: 6
- Rejected findings: 0
- Exonerated findings: 4
- Neutral findings: 0

## Accepted Findings

### FINDING_11: correctness: scripts/test-ship-pr.sh:1473-1477
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] postmerge --no-logs-commit assertion dropped explicit no-commit grep. Future edits could weaken ordering checks and miss a stray commit invocation without failing the env-focused conjunct. Re-add ! grep '^LARCH_LOG_ARGS=commit' alongside existing assertions.
- **Suggested revision**: Address the concern above.


### FINDING_17: **correctness** `scripts/ship-pr.sh:1755-1756` — The inline comment above the post-merge `write-final-report.sh` call still claims the goal is so the **committed** run-log reflects `OUTCOME=merged`, but this change set removes the post-merge `larch-log.sh commit` path and codifies NEVER #19 (no post-merge git commits). After merge, `final-summary.md` and related artifacts are updated under `$IMPLEMENT_TMPDIR` (and the tracking-issue comment via the report helper), not as a new commit on `main`. **Suggested fix:** Reword the comment to describe tmpdir/API outcomes only (for example, that the tmpdir `final-summary.md` / report output aligns with `MERGE_RESULT`), and drop “committed” so it cannot contradict `scripts/ship-pr.md` and NEVER #19.
- **Reviewer**: dyn-state-ordering-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:1755-1756` — The inline comment above the post-merge `write-final-report.sh` call still claims the goal is so the **committed** run-log reflects `OUTCOME=merged`, but this change set removes the post-merge `larch-log.sh commit` path and codifies NEVER #19 (no post-merge git commits). After merge, `final-summary.md` and related artifacts are updated under `$IMPLEMENT_TMPDIR` (and the tracking-issue comment via the report helper), not as a new commit on `main`. **Suggested fix:** Reword the comment to describe tmpdir/API outcomes only (for example, that the tmpdir `final-summary.md` / report output aligns with `MERGE_RESULT`), and drop “committed” so it cannot contradict `scripts/ship-pr.md` and NEVER #19.
- **Suggested revision**: Address the concern above.


### FINDING_18: **correctness** `scripts/ship-pr.sh:1734-1736` — When `recovery_ok=false`, the branch is a no-op (`:`) but the comment still says “Skip commit” and warns that “committing would produce a partial dir,” even though post-merge `git commit` was removed and the skipped work is the entire `else` tail (`status=done` manifest finalize plus `write-final-report.sh`), not merely a commit step. **Suggested fix:** Replace the comment with wording that matches control flow (skip manifest finalization and final-report when manifest recovery failed, since downstream assumes a coherent manifest tree).
- **Reviewer**: dyn-state-ordering-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:1734-1736` — When `recovery_ok=false`, the branch is a no-op (`:`) but the comment still says “Skip commit” and warns that “committing would produce a partial dir,” even though post-merge `git commit` was removed and the skipped work is the entire `else` tail (`status=done` manifest finalize plus `write-final-report.sh`), not merely a commit step. **Suggested fix:** Replace the comment with wording that matches control flow (skip manifest finalization and final-report when manifest recovery failed, since downstream assumes a coherent manifest tree).
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: scripts/ship-pr.sh:1755-1756
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Stale comment claims postmerge re-render makes the committed run-log reflect OUTCOME=merged after commits were removed from this phase. Maintainer misreads invariant and expects a git commit on main during postmerge. Update comment to refer to tmpdir-only updates.
- **Suggested revision**: Address the concern above.


### FINDING_4: risk-integration: scripts/test-ship-pr.sh:1387-1391
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] orphan_count coerces git failures to the literal string error producing a confusing fail line. git rev-list fails; message says left error commit(s). Handle rev-list failure explicitly instead of echoing error into the count.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: scripts/ship-pr.md:93
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Schema note implies post-merge committed manifests carry merge-finalized manifest keys. Downstream automation or operators grepping git-backed larch-logs on main may expect status=done/pr_number after merge but ship-pr no longer performs a post-merge log commit; plausible false negatives or wrong merge diagnostics. Reword to distinguish tmpdir postmerge manifest vs git-committed snapshots and note NEVER #19 means no post-merge log commit publishes those keys.
- **Suggested revision**: Address the concern above.


