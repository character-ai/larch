### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/report-tokens/scripts/test-run-analysis-quiet.sh:39-40
- **Concern**: Python floor change omits the quiet-wrapper harness stub. Scenario: FINDING_5 lowers the probe in run-analysis.sh to sys.version_info >= (3, 11) but test-run-analysis-quiet.sh still only short-circuits a 3.12 probe string; the Makefile-registered harness (test-harnesses-20) drifts from the runtime guard and loses its version-bypass contract when the probe string changes
- **Proposed resolution**: Add skills/report-tokens/scripts/test-run-analysis-quiet.sh to the #2 file list: update the python3 shim grep to match the new >= (3, 11) probe (and error text if asserted) alongside run-analysis.sh

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:858-875; python/rebase.py:234-238
- **Concern**: Volatile-only skip is planned after publishing files into the repo but before any worktree cleanup. Scenario: The plan says classify-before-stage can return a no-op when only allowlisted volatile files changed. At that point _publish_run_tree_to_repo has already copied changes into larch-logs/implement/<run_id>, so returning without restore/clean leaves dirty or untracked files. The later force-push path rejects any non-empty git status and stalls.
- **Proposed resolution**: When volatile-only status is detected, restore tracked changes and remove untracked volatile files under the run path before returning; then assert git status --porcelain -- <rel> is empty in the real-git regression test.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:851-879
- **Concern**: python/rebase.py:234-238. Scenario: Volatile-only skip cleanup is under-specified for unstaged/untracked publish churn
- **Proposed resolution**: After _publish_run_tree_to_repo, classify-before-add can skip commit while refresh files remain modified (M) or untracked (??) under rel; git reset HEAD only unstages and does not match rebase._force_push_branch full-repo status_porcelain gate — pre-rebase/postbump force-push stalls with dirty worktree despite path-scoped empty porcelain tests Spell out skip cleanup: git restore --worktree (and --staged) for allowlisted paths under rel, plus git clean -fd for untracked allowlisted names when needed; assert repo-wide status_porcelain is empty in test_run_logs (not only -- <rel>)

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:851; scripts/refresh-run-logs.sh:75-80
- **Concern**: The proposed volatile-only basename allowlist includes canonical token-report.json and timing-report.json even though refresh-run-logs writes substantive run cost/timing data to those batch names. Scenario: A CI/rebase refresh whose only real changes are updated token or timing totals is classified volatile-only, skipped, and never committed because flush_logs_post is commit-free; main then keeps stale run-log cost data without failing completeness checks
- **Proposed resolution**: Remove token-report.json and timing-report.json from the volatile-only allowlist, or skip them only after a content-aware check proves only known timestamp/elapsed noise changed

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:741-879
- **Concern**: Volatile-only skip does not restore the repo worktree after publish. Scenario: `_publish_run_tree_to_repo` copies refresh artifacts into `larch-logs/implement/<run_id>/` before `_larch_log_commit` decides to skip. Classify-before-`git.add` and `git reset HEAD` only avoid or undo the index; they do not clear unstaged `M` lines or `??` allowlisted files. `rebase._force_push_branch` rejects any non-empty porcelain (`python/rebase.py:234-238`), so the next pre-rebase flush can STALL with "dirty worktree before force-push" and reintroduce the soak failure O1 targets.
- **Proposed resolution**: After a volatile-only classification, reset the run tree to HEAD for allowlisted paths (e.g. `git restore --worktree --staged --source=HEAD -- <paths>` per changed file, plus `git clean -fd --` for untracked allowlisted files under `rel`), assert `git status --porcelain -- <rel>` is empty, then return the no-op `CommandResult`. Extend `test_run_logs.py` to publish-only volatile deltas and assert porcelain is empty without a commit.

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:119-195
- **Concern**: The volatile-only allowlist includes canonical token-report.json and timing-report.json, so a refresh whose only substantive change is new token/timing data can be skipped.. Scenario: After a CI fixer or rebase, the only changed run-log files may be token-report.json/timing-report.json; the plan would treat them as volatile-only and leave merged logs stale.
- **Proposed resolution**: Narrow the skip to refresh-only sidecars, or compare normalized report content and skip only when volatile fields changed.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:851-879
- **Concern**: Volatile-only classify-before-add leaves dirty worktree. Scenario: After _publish_run_tree_to_repo, allowlisted refresh files differ from HEAD; skipping git add without restoring those paths leaves porcelain under rel non-empty, and rebase._force_push_branch rejects the dirty tree (plan FINDING_2)
- **Proposed resolution**: Specify the classify-before-add path: after volatile-only detection, run git restore --worktree (or checkout) on the changed allowlisted paths under rel—or equivalent—so git status --porcelain -- rel is empty before returning; keep the existing git reset HEAD cleanup for the post-add legacy path

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:851, docs/run-logs.md:363-371
- **Concern**: Finding 1: The proposed basename-only volatile allowlist includes canonical token-report.json and timing-report.json, so it cannot distinguish elapsed churn from real token or timing data changes.. Scenario: A retry or CI-fix path that only changes token/timing reports would be treated as volatile-only and skipped, breaking the existing run-log contract that merged PRs carry the most recent token/timing batches.
- **Proposed resolution**: Do not include canonical token-report.json, timing-report.json, token-report.ndjson, or timing-report.ndjson in a filename-only skip; either limit the skip to refresh-only scratch copies or add content-aware comparison that ignores only known volatile fields.

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/report-tokens/scripts/test-run-analysis-quiet.sh:39-40
- **Concern**: Finding 2: The plan lowers run-analysis.sh to Python 3.11 but does not update the quiet-mode harness shim that only recognizes the old sys.version_info >= (3, 12) probe.. Scenario: After the probe changes to 3.11, the shim falls through to the real python command, so make lint's test-run-analysis-quiet path can fail depending on the host interpreter instead of exercising the intended wrapper contract.
- **Proposed resolution**: Update the harness grep and any expected text to 3.11 in the same change as run-analysis.sh.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:48-61; python/run_logs.py:628-657; docs/run-logs.md:363-373
- **Concern**: O1 defines volatile-only via basename allowlist that includes canonical token-report.json / timing-report.json (and .ndjson), while edge cases and docs/run-logs.md require substantive token/timing updates to still commit. Scenario: An in-loop flush that only updates ledger-driven token/timing artifacts (no execution-issues.ndjson or other non-allowlisted paths) can be classified volatile-only and skip the commit, leaving stale reports on the PR branch despite the stated substantive-change contract
- **Proposed resolution**: Narrow volatility to refresh sidecars (*-refresh.json, session-transcript-refresh.txt) or require a content-aware check (e.g., token/timing totals or record-count delta) before skipping; add test_run_logs.py case where a substantive token-report.json-only delta must commit

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:858-879
- **Concern**: Volatile-only skip is planned after publishing but before staging without an explicit worktree restore. Scenario: _publish_run_tree_to_repo can overwrite repo files; returning no-op before git add leaves unstaged volatile files dirty, so later push.assert_clean_worktree or rebase._force_push_branch can fail and reintroduce the merge-loop stall
- **Proposed resolution**: Make the volatile-only skip cleanup explicit: avoid publishing those changes, or restore the run-log path to HEAD and remove untracked volatile files before returning; assert git status --porcelain -- <rel> is empty for unstaged and staged cases in test_run_logs.py

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-run-log-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:851-879
- **Concern**: Volatile-only skip cleanup cites git reset HEAD only but publish leaves modified or untracked allowlisted files on disk. Scenario: After _publish_run_tree_to_repo copies refreshed token/timing artifacts, porcelain under the run path stays non-empty; rebase._force_push_branch rejects any repo-wide dirty porcelain (python/rebase.py:234-238) even when _larch_log_commit skips staging
- **Proposed resolution**: After a volatile-only classification, restore the run path to HEAD (git restore --worktree --staged --source=HEAD -- "$rel" or per-file equivalents) and remove untracked allowlisted paths (git clean -fd -- "$rel" when needed); keep reset HEAD only as a staged-index fallback

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-run-log-contract
- **Severity**: important
- **Focus area**: architecture
- **Location**: docs/run-logs.md:363-383
- **Concern**: Plan allowlists canonical token-report.json and timing-report.json for volatile-only skip using basename rules only, but edge cases describe timestamp/elapsed churn and docs require CI-retry refreshes to commit before push. Scenario: Pre-rebase flush_logs_pre (python/ship.py:402-418) can skip a commit when only allowlisted canonical reports changed even after CI-fix steps add new token/timing rows; merged PR can carry stale reports relative to bash refresh-run-logs.sh and docs/run-logs.md
- **Proposed resolution**: Either drop canonical token-report.json / timing-report.json from the volatile basename set (limit to *-refresh.json and sidecar ndjson) or add a minimal content/substance predicate before skipping; document the trade-off explicitly in docs/run-logs.md

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-run-log-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:54-60; python/run_logs.py:741-771; python/rebase.py:227-239
- **Concern**: 1. Volatile-only skip returns after copying the run tree without restoring the worktree. Scenario: _publish_run_tree_to_repo replaces larch-logs/implement/<run_id> in the repo before the proposed no-op return; returning before git add still leaves unstaged allowlisted files, and git reset HEAD only unstages. rebase._force_push_branch then sees non-empty porcelain and stalls with dirty worktree before force-push.
- **Proposed resolution**: Either classify before publishing into the repo, or on volatile-only skip restore/clean the scoped rel back to HEAD and assert git status --porcelain -- <rel> is empty before returning.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-run-log-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:50-60; python/run_logs.py:119-195; python/run_logs.py:628-657; docs/run-logs.md:363-373
- **Concern**: 2. Basename-only allowlist marks canonical token/timing outputs as volatile. Scenario: python/run_logs.py writes canonical token-report.json and timing-report.json from current ledgers, and docs/run-logs.md promises these refresh before push. If only token or timing totals change on a retry, the proposed basename allowlist can skip the commit and merge stale reports despite the plan saying substantive changes still commit.
- **Proposed resolution**: Narrow the allowlist to scratch refresh copies/known churn files, or make the classifier content-aware so token/timing total or record changes still commit while pure volatile churn is skipped.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-runtime-floor-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/installation-and-setup.md:96
- **Concern**: Plan swaps only the version number on line 96 and leaves the clause "matching contributor tooling" untouched. Scenario: After the edit the runtime floor is 3.11 while contributor pre-commit tooling stays 3.12+ (line 297); the surviving phrase falsely claims the two floors still match
- **Proposed resolution**: Drop "matching contributor tooling" from line 96 (or replace with explicit split: runtime ≥3.11 vs contributor dev/pre-commit 3.12+ per line 297)

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-cli-fixture-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/gh.py:313-383
- **Concern**: Post-create success path omits the try/except around pr_for_branch that the conflict branch already uses. Scenario: After rc=0 create, a transient pr list failure raises TransientNetworkError/ShipError before stdout URL fallback runs, contradicting Edge cases (plan.txt:183-184) and leaving no STALLED JSON path
- **Proposed resolution**: Mirror lines 353-356: wrap post-create pr_for_branch in except (ShipError, TransientNetworkError), set recovered=None, then call _recover_pr_from_conflict_text(result.stdout); only then raise ShipError if still unresolved

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-cli-fixture-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_gh.py:140-144
- **Concern**: test_gh.py (#3) names only --json argv capture and one combined success fixture; no required cases for list-lag URL fallback or total resolution failure. Scenario: Stubs can keep returning post-create list hits so stdout URL parsing never runs, or success-with-unparseable-output never asserts ShipError—regression reintroduces JSON-style create handling without detection
- **Proposed resolution**: Add three fixtures: (1) create stdout URL + post-create list returns PR; (2) create stdout URL + post-create list [] (timing lag) resolves via URL only; (3) create rc=0 with empty stdout and post-create list [] raises ShipError (optionally assert test_ship #4 STALLED mapping)

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-cli-fixture-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/gh.py:267-269,313-383; <TMPDIR>/plan.txt:16-19,140-144
- **Concern**: Post-create PR resolution fallback is not pinned by the test plan. Scenario: `pr_for_branch` raises on non-zero list reads, and the plan asks the success path to query it after `gh pr create`; without an explicit test where that post-create list fails or returns no rows, an implementation can skip the stdout URL fallback and falsely stall after GitHub already created the PR.
- **Proposed resolution**: Specify that the success path catches `ShipError` and `TransientNetworkError` from the post-create `pr_for_branch` before parsing `result.stdout`, and add focused `python/test_gh.py` cases for post-create list failure/empty plus bare URL stdout fallback and for list empty plus no PR URL raising `ShipError`.
