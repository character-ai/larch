### FINDING_1: Quiet harness drifts from run-analysis Python 3.11 probe
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: Lowering the runtime floor in `run-analysis.sh` to `sys.version_info >= (3, 11)` without updating `test-run-analysis-quiet.sh` leaves the Makefile-registered quiet harness (`test-harnesses-20`) still short-circuiting only a 3.12 probe string. The harness then diverges from the runtime guard, may invoke the real interpreter instead of exercising the wrapper contract, and can fail under `make lint` depending on host Python rather than the intended bypass behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add skills/report-tokens/scripts/test-run-analysis-quiet.sh to the #2 file list: update the python3 shim grep to match the new >= (3, 11) probe (and error text if asserted) alongside run-analysis.sh
  - From Codex-Pragmatic: Update the harness grep and any expected text to 3.11 in the same change as run-analysis.sh.


### FINDING_2: Volatile-only skip leaves dirty worktree after publish
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements, Cursor-dyn-run-log-contract, Codex-dyn-run-log-contract
- **Severity**: important
- **Concern**: The planned volatile-only path runs after `_publish_run_tree_to_repo` copies refresh artifacts into `larch-logs/implement/<run_id>/` but returns a no-op before worktree cleanup. Classify-before-`git add`, `git reset HEAD`, or path-scoped porcelain checks only affect the index or a subtree; they do not clear unstaged `M` lines or untracked `??` allowlisted files repo-wide. `rebase._force_push_branch` and other push paths reject any non-empty `git status --porcelain`, so pre-rebase/postbump force-push can stall with “dirty worktree” despite skipping the commit—reintroducing the merge-loop soak failure O1 targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: When volatile-only status is detected, restore tracked changes and remove untracked volatile files under the run path before returning; then assert git status --porcelain -- <rel> is empty in the real-git regression test.
  - From Cursor-Edge: After _publish_run_tree_to_repo, classify-before-add can skip commit while refresh files remain modified (M) or untracked (??) under rel; git reset HEAD only unstages and does not match rebase._force_push_branch full-repo status_porcelain gate — pre-rebase/postbump force-push stalls with dirty worktree despite path-scoped empty porcelain tests Spell out skip cleanup: git restore --worktree (and --staged) for allowlisted paths under rel, plus git clean -fd for untracked allowlisted names when needed; assert repo-wide status_porcelain is empty in test_run_logs (not only -- <rel>)
  - From Cursor-Innovation: After a volatile-only classification, reset the run tree to HEAD for allowlisted paths (e.g. `git restore --worktree --staged --source=HEAD -- <paths>` per changed file, plus `git clean -fd --` for untracked allowlisted files under `rel`), assert `git status --porcelain -- <rel>` is empty, then return the no-op `CommandResult`. Extend `test_run_logs.py` to publish-only volatile deltas and assert porcelain is empty without a commit.
  - From Cursor-Pragmatic: Specify the classify-before-add path: after volatile-only detection, run git restore --worktree (or checkout) on the changed allowlisted paths under rel—or equivalent—so git status --porcelain -- rel is empty before returning; keep the existing git reset HEAD cleanup for the post-add legacy path
  - From Codex-Requirements: Make the volatile-only skip cleanup explicit: avoid publishing those changes, or restore the run-log path to HEAD and remove untracked volatile files before returning; assert git status --porcelain -- <rel> is empty for unstaged and staged cases in test_run_logs.py
  - From Cursor-dyn-run-log-contract: After a volatile-only classification, restore the run path to HEAD (git restore --worktree --staged --source=HEAD -- "$rel" or per-file equivalents) and remove untracked allowlisted paths (git clean -fd -- "$rel" when needed); keep reset HEAD only as a staged-index fallback
  - From Codex-dyn-run-log-contract: Either classify before publishing into the repo, or on volatile-only skip restore/clean the scoped rel back to HEAD and assert git status --porcelain -- <rel> is empty before returning.


### FINDING_3: Basename allowlist treats substantive token/timing reports as volatile-only
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-run-log-contract, Codex-dyn-run-log-contract
- **Severity**: important
- **Concern**: A basename-only volatile allowlist that includes canonical `token-report.json`, `timing-report.json`, and related `.ndjson` outputs cannot distinguish timestamp/elapsed churn from real token or timing data changes. `refresh-run-logs.sh` and `python/run_logs.py` write substantive cost/timing data to those names; an in-loop or CI/rebase refresh whose only changes are updated totals can be classified volatile-only, skip commit (including commit-free `flush_logs_post`), and leave merged PR branches with stale reports while still satisfying overly narrow checks—contradicting `docs/run-logs.md` and plan edge cases that require substantive token/timing updates to commit before push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Remove token-report.json and timing-report.json from the volatile-only allowlist, or skip them only after a content-aware check proves only known timestamp/elapsed noise changed
  - From Codex-Innovation: Narrow the skip to refresh-only sidecars, or compare normalized report content and skip only when volatile fields changed.
  - From Codex-Pragmatic: Do not include canonical token-report.json, timing-report.json, token-report.ndjson, or timing-report.ndjson in a filename-only skip; either limit the skip to refresh-only scratch copies or add content-aware comparison that ignores only known volatile fields.
  - From Cursor-Requirements: Narrow volatility to refresh sidecars (*-refresh.json, session-transcript-refresh.txt) or require a content-aware check (e.g., token/timing totals or record-count delta) before skipping; add test_run_logs.py case where a substantive token-report.json-only delta must commit
  - From Cursor-dyn-run-log-contract: Either drop canonical token-report.json / timing-report.json from the volatile basename set (limit to *-refresh.json and sidecar ndjson) or add a minimal content/substance predicate before skipping; document the trade-off explicitly in docs/run-logs.md
  - From Codex-dyn-run-log-contract: Narrow the allowlist to scratch refresh copies/known churn files, or make the classifier content-aware so token/timing total or record changes still commit while pure volatile churn is skipped.


### FINDING_4: Installation doc falsely claims runtime floor matches contributor tooling
- **Reviewer(s)**: Cursor-dyn-runtime-floor-sync
- **Severity**: important
- **Concern**: The plan only swaps the version number on `docs/installation-and-setup.md` line 96 while leaving “matching contributor tooling” in place. After the edit the runtime floor becomes 3.11 while contributor pre-commit tooling remains 3.12+ (line 297), so the surviving phrase incorrectly implies the two floors still align.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-runtime-floor-sync: Drop "matching contributor tooling" from line 96 (or replace with explicit split: runtime ≥3.11 vs contributor dev/pre-commit 3.12+ per line 297)


### FINDING_5: Post-create PR resolution lacks resilient fallback and test coverage
- **Reviewer(s)**: Cursor-dyn-cli-fixture-parity, Codex-dyn-cli-fixture-parity
- **Severity**: important
- **Concern**: After `gh pr create` succeeds (`rc=0`), the success path calls `pr_for_branch` without the try/except used on the conflict branch. A transient list failure or timing lag can raise `ShipError`/`TransientNetworkError` or miss the PR before stdout URL fallback runs, contradicting plan edge cases and leaving no STALLED JSON path when GitHub already created the PR. The test plan does not pin stdout-URL fallback, list-lag, or total-resolution-failure cases, so regressions can reintroduce JSON-style create handling without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cli-fixture-parity: Mirror lines 353-356: wrap post-create pr_for_branch in except (ShipError, TransientNetworkError), set recovered=None, then call _recover_pr_from_conflict_text(result.stdout); only then raise ShipError if still unresolved
  - From Cursor-dyn-cli-fixture-parity: Add three fixtures: (1) create stdout URL + post-create list returns PR; (2) create stdout URL + post-create list [] (timing lag) resolves via URL only; (3) create rc=0 with empty stdout and post-create list [] raises ShipError (optionally assert test_ship #4 STALLED mapping)
  - From Codex-dyn-cli-fixture-parity: Specify that the success path catches `ShipError` and `TransientNetworkError` from the post-create `pr_for_branch` before parsing `result.stdout`, and add focused `python/test_gh.py` cases for post-create list failure/empty plus bare URL stdout fallback and for list empty plus no PR URL raising `ShipError`.

