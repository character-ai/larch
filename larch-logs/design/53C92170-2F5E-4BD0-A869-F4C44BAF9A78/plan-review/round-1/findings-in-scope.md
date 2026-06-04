### FINDING_1: 3.11 runtime floor plan misses explicit lint/type pins
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-version-floor-sync
- **Severity**: important
- **Concern**: Lowering the Python runtime floor to 3.11 while leaving Ruff, Pyright, and/or Pylint pinned to Python 3.12 means `py-lint` can still analyze as 3.12 and fail to catch 3.12-only syntax, APIs, or imports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/ruff.toml — set target-version = "py311" (or drop the pin only if ruff is confirmed to follow requires-python).
  - From Codex-Arch: Update python/ruff.toml to py311 or remove the override, and set python/pyrightconfig.json pythonVersion to 3.11 alongside the pyproject/docs/CI changes
  - From Codex-Innovation: Change these pins to py311/3.11 or remove them so the lowered floor is enforced
  - From Codex-Pragmatic: Lower these pins to py311/3.11 or remove the ruff pin so pyproject drives it; keep truly dev-only pre-commit setup on 3.12.
  - From Codex-Requirements: Add these config files to the plan and lower target-version/pythonVersion/py-version to 3.11, or add an equivalent explicit 3.11 syntax/import gate
  - From Codex-dyn-version-floor-sync: Add these three config files to the version-floor change and lower or remove the explicit 3.12 analysis pins so py-lint validates Python 3.11 compatibility.

### FINDING_2: Volatile-only run-log skip can leave staged or dirty files
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Cursor-Innovation, Codex-Innovation, Codex-Requirements, Codex-dyn-contract-drift, Cursor-dyn-run-log-invariants, Codex-dyn-run-log-invariants
- **Severity**: important
- **Concern**: The volatile-only no-op path is planned after publishing/staging run-log files, but does not require clearing the index or worktree before returning success. That can leave staged or dirty volatile paths, causing later rebase/force-push clean-tree gates to stall or later commits to accidentally include skipped files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the volatile-only path leave repo state clean before returning, e.g. classify before publishing or restore/unstage the volatile paths; add a status-clean assertion to the new run_logs test
  - From Codex-Edge, Codex-Pragmatic: On a volatile-only skip, leave git status clean: classify before copying, or unstage plus restore/clean only allowlisted volatile paths before returning. Add a regression asserting git status --porcelain is empty after the skip.
  - From Cursor-Innovation: The plan skips the flush commit after `git add` when only volatile artifacts changed, but does not unstage. `rebase._force_push_branch` rejects any non-empty `git status --porcelain`, so a later pre-rebase flush during the CI loop can leave the tree "dirty" and force-push raises `dirty worktree before force-push` (STALLED), recreating soak-style merge failures under a different signature. On volatile-only skip, run `git reset HEAD -- <rel>` (mirror `scripts/larch-log.sh` failed-commit cleanup at lines 564-565) or classify volatile paths before `git add` so nothing stays staged when no commit is created.
  - From Codex-Innovation: When skipping, leave the repo clean: avoid copying those paths, or unstage and restore/remove the allowlisted repo copies; add a test asserting clean status after the skip
  - From Codex-Requirements: Classify volatile-only changes before staging, or unstage/revert those paths before returning a volatile-only skip; add a regression that the volatile-only path leaves git status clean before rebase/force-push
  - From Codex-dyn-contract-drift: Classify before publishing/staging, or explicitly reset/checkout/clean the volatile paths before returning; add the planned volatile-only test assertion that git status --porcelain for the run-log path is empty after the skip
  - From Cursor-dyn-run-log-invariants: After volatile-only classification call git reset HEAD -- on the run pathspec (mirror larch-log.sh commit failure reset) or avoid git add until after the volatile check
  - From Codex-dyn-run-log-invariants: Classify before staging, or reset/checkout the allowlisted paths before returning; add a regression that volatile-only skip leaves git status --porcelain empty

### FINDING_3: OID polling must compare against post-recovery HEAD
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Replacing the post-force-push HEAD re-read with an OID poll risks comparing GitHub against a stale pre-recovery local OID unless the helper explicitly re-reads HEAD after recovery. That can exhaust retries or match the wrong commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: State `_poll_head_oid_match` re-reads `git.try_rev_parse(..., "HEAD")` on every attempt (do not compare against the pre-recovery `local_head`), or keep an explicit post-recovery `rev-parse` before calling the helper; add/extend `test_merge.py` poll coverage to assert the post-push HEAD is what gets compared.

### FINDING_4: Volatile allowlist must exactly cover intended refresh/report artifacts
- **Reviewer(s)**: Codex-Edge, Cursor-Requirements, Cursor-dyn-run-log-invariants, Codex-dyn-run-log-invariants
- **Severity**: important
- **Concern**: The planned volatile allowlist may omit refresh JSON sidecars and canonical report/transcript artifacts that are rewritten during run-log refreshes. If omitted, timestamp-only churn can still create flush commits; if canonical batches are skipped, docs/tests must make that contract explicit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Include token-report-refresh.json and timing-report-refresh.json explicitly in the volatile allowlist, or stop copying them for in-loop flushes. Test the volatile-only path with those files present.
  - From Cursor-Requirements: Extend the O1 allowlist (and test_run_logs.py fixtures) to include token-report-refresh.json, timing-report-refresh.json, and any other refresh copies _render_token_timing_batches writes under larch-logs/implement/<run_id>/
  - From Cursor-dyn-run-log-invariants: Enumerate exact basenames under larch-logs/implement/<run_id>/ including token-report.json timing-report.json token-report.ndjson timing-report.ndjson token-report-refresh.json timing-report-refresh.json session-transcript-refresh.txt; extend test_run_logs.py to assert skip when only .json churn changes
  - From Codex-dyn-run-log-invariants: Make the allowlist match the exact intended volatile files, including or excluding canonical batches explicitly; if canonical batches may be skipped, update docs/run-logs.md and tests to say those final refreshes can remain tmpdir-local

### FINDING_5: `/report-tokens` wrapper still rejects Python 3.11
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements, Codex-Requirements, Codex-dyn-version-floor-sync, Codex-Pragmatic, Cursor-dyn-version-floor-sync
- **Severity**: important
- **Concern**: The documented/runtime floor is lowered to Python 3.11, but the live `skills/report-tokens/scripts/run-analysis.sh` wrapper still requires Python 3.12, so users on 3.11 would satisfy docs and pyproject but be blocked by the skill wrapper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation, Cursor-Requirements, Codex-Requirements, Codex-dyn-version-floor-sync: Include run-analysis.sh in the plan and change the probe/message to require >= 3.11
  - From Codex-Pragmatic: Update this guard and error text to >=3.11 in the same floor-lowering change.
  - From Cursor-dyn-version-floor-sync: Add `### UPDATED: skills/report-tokens/scripts/run-analysis.sh` lowering the `sys.version_info` check and error text to 3.11 (mirror the implement selector snippet)

### FINDING_6: Python stderr breadcrumbs need documented shapes and tests
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: Adding generic Python `ship.py` and `ci_monitor.py` stderr breadcrumbs without pinning the documented stderr grammar can let tests pass with arbitrary text while operators or consumers grepping documented progress shapes miss liveness or keep expecting old behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-drift: Specify that Python breadcrumbs reuse the documented prefixes/shapes and assert them exactly in python/test_ship.py and python/test_ci_monitor.py, or update the docs to declare the Python-specific stderr grammar while keeping stdout JSON-only

### FINDING_7: Volatile allowlist must not match substantive audit batches
- **Reviewer(s)**: Cursor-dyn-run-log-invariants
- **Severity**: important
- **Concern**: If the volatile allowlist is implemented as a broad pattern such as any `*.ndjson` under the run directory, substantive audit files like execution issues or review findings could be skipped and omitted from the PR tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-run-log-invariants: Name explicit basename allowlist only; never match execution-issues.ndjson round-* artifacts manifest.json plan-goals-test.md session-transcript.jsonl; add a negative test_run_logs.py case where execution-issues.ndjson-only delta must commit
