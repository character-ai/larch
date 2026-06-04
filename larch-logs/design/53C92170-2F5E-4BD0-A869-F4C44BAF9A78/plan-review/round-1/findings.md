### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ruff.toml:1
- **Concern**: Decision 1 lowers the runtime floor to 3.11 but the plan only updates python/pyproject.toml and says to confirm pins; python/ruff.toml still sets target-version = "py312".. Scenario: py-lint on the planned 3.11 CI matrix still lint-checks as py312, so 3.12-only syntax or stdlib usage can pass ruff and fail at runtime on 3.11.
- **Proposed resolution**: Add ### UPDATED: python/ruff.toml — set target-version = "py311" (or drop the pin only if ruff is confirmed to follow requires-python).

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:858-879; python/rebase.py:234-238
- **Concern**: Volatile-only no-op can leave run-log changes staged or dirty. Scenario: The proposed _larch_log_commit skip happens after publishing/staging run logs but returns success without a commit; the next rebase/force-push path refuses any dirty worktree and stalls
- **Proposed resolution**: Make the volatile-only path leave repo state clean before returning, e.g. classify before publishing or restore/unstage the volatile paths; add a status-clean assertion to the new run_logs test

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ruff.toml:1; python/pyrightconfig.json:3
- **Concern**: 3.11 floor plan misses explicit 3.12 lint/type pins. Scenario: Lowering python/pyproject.toml alone will not make py-lint validate 3.11 compatibility because Ruff and Pyright are still configured for Python 3.12
- **Proposed resolution**: Update python/ruff.toml to py311 or remove the override, and set python/pyrightconfig.json pythonVersion to 3.11 alongside the pyproject/docs/CI changes

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/merge.py:311-317
- **Concern**: OID poll replaces post-force-push HEAD re-read without saying poll must re-read HEAD. Scenario: Plan replaces lines 311-313 (including `git rev-parse HEAD` after recovery) with `_poll_head_oid_match(..., local_head, ...)`. That parameter name invites passing the pre-recovery OID from line 273. After `force_push_recovery`, local HEAD changes; polling GitHub with a stale OID can exhaust retries and return `MERGE_RESULT_ERROR` on a recoverable lag, or match the wrong commit.
- **Proposed resolution**: State `_poll_head_oid_match` re-reads `git.try_rev_parse(..., "HEAD")` on every attempt (do not compare against the pre-recovery `local_head`), or keep an explicit post-recovery `rev-parse` before calling the helper; add/extend `test_merge.py` poll coverage to assert the post-push HEAD is what gets compared.

### FINDING_5:
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:851-879; python/rebase.py:234-238; python/push.py:24-32
- **Concern**: Volatile-only skip can leave the repo dirty. Scenario: The plan skips the flush commit after publishing/staging volatile run-log changes. If those files remain staged or modified, later force-push and PR push clean-tree gates fail with dirty worktree instead of avoiding divergence.
- **Proposed resolution**: On a volatile-only skip, leave git status clean: classify before copying, or unstage plus restore/clean only allowlisted volatile paths before returning. Add a regression asserting git status --porcelain is empty after the skip.

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:628-656
- **Concern**: Volatile allowlist may miss refresh JSON artifacts. Scenario: _render_token_timing_batches also copies token-report-refresh.json and timing-report-refresh.json into the run tree. If the new allowlist only covers token/timing ndjson plus session-transcript-refresh.txt, these refresh JSON files still force flush commits during CI/retry polls.
- **Proposed resolution**: Include token-report-refresh.json and timing-report-refresh.json explicitly in the volatile allowlist, or stop copying them for in-loop flushes. Test the volatile-only path with those files present.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:851-879
- **Concern**: python/rebase.py:237-238. Scenario: Volatile-only flush skip can leave staged run-log paths in the index without a commit
- **Proposed resolution**: The plan skips the flush commit after `git add` when only volatile artifacts changed, but does not unstage. `rebase._force_push_branch` rejects any non-empty `git status --porcelain`, so a later pre-rebase flush during the CI loop can leave the tree "dirty" and force-push raises `dirty worktree before force-push` (STALLED), recreating soak-style merge failures under a different signature. On volatile-only skip, run `git reset HEAD -- <rel>` (mirror `scripts/larch-log.sh` failed-commit cleanup at lines 564-565) or classify volatile paths before `git add` so nothing stays staged when no commit is created.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements, Codex-Requirements, Codex-dyn-version-floor-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:74-76
- **Concern**: The plan lowers the documented runtime floor to Python 3.11 but leaves the live /report-tokens wrapper rejecting 3.11. Scenario: Users with Python 3.11 satisfy the new docs and pyproject floor but /report-tokens still exits with "requires Python 3.12 or newer"
- **Proposed resolution**: Include run-analysis.sh in the plan and change the probe/message to require >= 3.11

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ruff.toml:1; python/pyrightconfig.json:3; python/.pylintrc:88-90
- **Concern**: The 3.11 support plan misses existing lint/type-checker pins that still target Python 3.12. Scenario: The new 3.11 CI matrix can run while ruff, pyright, and pylint still analyze as 3.12, so py-lint does not prove the new floor
- **Proposed resolution**: Change these pins to py311/3.11 or remove them so the lowered floor is enforced

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:858-879
- **Concern**: The proposed volatile-only skip runs after staging but does not specify cleaning staged or worktree changes. Scenario: A volatile-only flush can return success with larch-logs changes left staged or dirty; the next rebase/push can stall, or a later substantive commit can accidentally include the skipped files
- **Proposed resolution**: When skipping, leave the repo clean: avoid copying those paths, or unstage and restore/remove the allowlisted repo copies; add a test asserting clean status after the skip

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:74-75
- **Concern**: 3.11 floor omits live /report-tokens guard. Scenario: The plan changes docs to say /report-tokens supports Python 3.11, but the wrapper still exits unless python3 is >=3.12, so a valid 3.11 runtime remains blocked.
- **Proposed resolution**: Update this guard and error text to >=3.11 in the same floor-lowering change.

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ruff.toml:1, python/.pylintrc:90, python/pyrightconfig.json:3
- **Concern**: Explicit lint/type pins keep 3.12 despite the proposed 3.11 floor. Scenario: python-lint matrix jobs would still analyze against 3.12, so 3.11 compatibility is not fully verified and 3.12-only usage in less-covered code can pass static checks.
- **Proposed resolution**: Lower these pins to py311/3.11 or remove the ruff pin so pyproject drives it; keep truly dev-only pre-commit setup on 3.12.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:649-656
- **Concern**: O1 volatile-only allowlist omits token-report-refresh.json and timing-report-refresh.json copied into the run tree each flush. Scenario: flush_logs_pre always stages those refresh JSON paths; a allowlist limited to *.ndjson and session-transcript-refresh.txt still creates chore(larch-logs) commits on timestamp-only churn, so in-loop flushes can keep diverging HEAD from the CI-green PR tip
- **Proposed resolution**: Extend the O1 allowlist (and test_run_logs.py fixtures) to include token-report-refresh.json, timing-report-refresh.json, and any other refresh copies _render_token_timing_batches writes under larch-logs/implement/<run_id>/

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ruff.toml:1, python/pyrightconfig.json:3, python/.pylintrc:90
- **Concern**: The plan says no explicit lint/typecheck Python-version pins re-raise the floor, but the repo has three 3.12 pins used by make py-lint. Scenario: The new 3.11 CI matrix can still lint/typecheck as 3.12 and miss 3.12-only syntax, undercutting the acceptance criterion to prove 3.11 compliance
- **Proposed resolution**: Add these config files to the plan and lower target-version/pythonVersion/py-version to 3.11, or add an equivalent explicit 3.11 syntax/import gate

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:875-879, python/rebase.py:234-238, python/git.py:599-609
- **Concern**: The volatile-only flush plan skips the commit after git add without saying to clear the index/worktree. Scenario: flush_logs_pre can return success with staged volatile log changes; the next rebase/force-push path sees a dirty tree and stalls, so the no-divergence fix can still break shipping
- **Proposed resolution**: Classify volatile-only changes before staging, or unstage/revert those paths before returning a volatile-only skip; add a regression that the volatile-only path leaves git status clean before rebase/force-push

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:858-879; python/rebase.py:233-239
- **Concern**: Volatile-only flush skip is planned after publishing/staging run-log files but does not require cleaning the index or worktree. Scenario: When only token/timing/session-transcript files change, _publish_run_tree_to_repo and git.add can leave larch-logs changes staged or dirty; postbump/pre-rebase then reaches rebase._force_push_branch and stalls on dirty worktree before force-push, defeating the non-divergent skip
- **Proposed resolution**: Classify before publishing/staging, or explicitly reset/checkout/clean the volatile paths before returning; add the planned volatile-only test assertion that git status --porcelain for the run-log path is empty after the skip

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.md:187-199; scripts/ci-wait.md:36-37; scripts/ci-wait.sh:187-191,277-291
- **Concern**: The breadcrumb plan does not pin or update the documented stderr breadcrumb shapes while adding generic ship.py and ci_monitor.py stderr lines. Scenario: Python-path tests could pass with arbitrary stderr text, while consumers/operators grepping the documented ship-pr and ci-wait progress shapes miss liveness or keep expecting the old silent/shape-specific behavior
- **Proposed resolution**: Specify that Python breadcrumbs reuse the documented prefixes/shapes and assert them exactly in python/test_ship.py and python/test_ci_monitor.py, or update the docs to declare the Python-specific stderr grammar while keeping stdout JSON-only

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-run-log-invariants
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:49-54, docs/run-logs.md:363-373, python/run_logs.py:628-656
- **Concern**: Volatile allowlist names token/timing ndjson and refresh sidecars but omits committed token-report.json and timing-report.json. Scenario: Pre-push refresh rewrites those .json batches via larch-log write and _render_ledger_reports; if only they change, classifier still commits and O1 does not stop merge-adjacent flush churn
- **Proposed resolution**: Enumerate exact basenames under larch-logs/implement/<run_id>/ including token-report.json timing-report.json token-report.ndjson timing-report.ndjson token-report-refresh.json timing-report-refresh.json session-transcript-refresh.txt; extend test_run_logs.py to assert skip when only .json churn changes

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-run-log-invariants
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:49-54, docs/run-logs-required-files.tsv:12-15, python/run_logs.py:451-465
- **Concern**: Allowlist prose does not forbid treating other ndjson/jsonl batches as volatile. Scenario: An over-broad rule such as any *.ndjson under the run dir could skip commits when only execution-issues.ndjson or review-findings-full.jsonl changed, dropping substantive audit data from the PR tree
- **Proposed resolution**: Name explicit basename allowlist only; never match execution-issues.ndjson round-* artifacts manifest.json plan-goals-test.md session-transcript.jsonl; add a negative test_run_logs.py case where execution-issues.ndjson-only delta must commit

### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-run-log-invariants
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:875-879, scripts/larch-log.sh:559-566
- **Concern**: Volatile-only skip is planned after git add without an index/worktree restore step. Scenario: Staged volatile deltas remain in the index without a commit; later git operations on the feature branch can accidentally pick up log-only staged noise or confuse dirty-tree checks
- **Proposed resolution**: After volatile-only classification call git reset HEAD -- on the run pathspec (mirror larch-log.sh commit failure reset) or avoid git add until after the volatile check

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-run-log-invariants
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:870-879; python/rebase.py:234-238
- **Concern**: Volatile-only skip is planned after git add without clearing the staged volatile delta. Scenario: If _larch_log_commit stages token/timing/transcript changes and then returns the no-op CommandResult, the index/worktree stays dirty; the next rebase/force-push path can stall on dirty worktree instead of merely suppressing a churn commit
- **Proposed resolution**: Classify before staging, or reset/checkout the allowlisted paths before returning; add a regression that volatile-only skip leaves git status --porcelain empty

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-run-log-invariants
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:119-195; python/run_logs.py:628-710; scripts/larch-log-batches.sh:33-38; docs/run-logs.md:363-383
- **Concern**: The planned allowlist names ndjson/refresh copies, but current refresh rewrites canonical committed token/timing/transcript batches. Scenario: token-report.json, timing-report.json, and session-transcript.jsonl are refreshed by the current pre-push path; if omitted, volatile-only skip will not stop CI-churn commits, but if included silently, docs still promise the merged PR carries the latest refreshed reports/transcript
- **Proposed resolution**: Make the allowlist match the exact intended volatile files, including or excluding canonical batches explicitly; if canonical batches may be skipped, update docs/run-logs.md and tests to say those final refreshes can remain tmpdir-local

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-version-floor-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/report-tokens/scripts/run-analysis.sh:74-75
- **Concern**: Runtime `/report-tokens` gate still requires Python 3.12 while Decision 1 lowers the documented runtime floor to 3.11. Scenario: Plan updates `docs/installation-and-setup.md` and `python/pyproject.toml` but omits this wrapper; operators on Python 3.11 see docs/skill text promising 3.11 yet `run-analysis.sh` exits before `report_tokens_cli.py`
- **Proposed resolution**: Add `### UPDATED: skills/report-tokens/scripts/run-analysis.sh` lowering the `sys.version_info` check and error text to 3.11 (mirror the implement selector snippet)

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-version-floor-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ruff.toml:1; python/pyrightconfig.json:3; python/.pylintrc:88-90
- **Concern**: Plan says lowering python/pyproject.toml is enough and that Ruff infers the target, but current lint configs explicitly pin the analysis floor to 3.12.. Scenario: The proposed 3.11/3.12 CI matrix can go green while py-lint still analyzes as 3.12, so 3.12-only APIs or syntax are not reliably flagged as incompatible with the new floor.
- **Proposed resolution**: Add these three config files to the version-floor change and lower or remove the explicit 3.12 analysis pins so py-lint validates Python 3.11 compatibility.

### OOS_1:
- **Description**: No contract doc update for python volatile-only skip or merge-time pre-flush removal. Scenario: Operators and completeness tooling docs still describe only bash refresh-run-logs commit behavior; Phase 7 python cutover behavior is undocumented in the run-log authority doc
- **Reviewer**: Cursor-dyn-run-log-invariants
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/run-logs.md:363-383, python/README.md:20-24
- **Phase**: design
