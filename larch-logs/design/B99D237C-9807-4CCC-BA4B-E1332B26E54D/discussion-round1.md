## Decision 1: Change boundary
- **Question**: Is this Python-only Phase-7 hardening, or does it also flip /implement to the Python driver?
- **Resolution**: Python-only. Edit python/ship.py, python/run_logs.py, python/ci_monitor.py and their pytest files only. Do NOT edit scripts/ship-pr.sh; do NOT flip /implement Step 8+ or SKILL.md to call ship.py. The dormant path stays dormant but hardened + tested.
- **Source**: user

## Decision 2: Ground-truth unavailability fallback
- **Question**: When gh/git/manifest ground truth is unreachable on re-entry (repo_unavailable, forked dry-run, transient gh failure), how should resume behave?
- **Resolution**: State-file floor; ground truth refines. Always restore session-wide counters from the persisted state file. Query gh/git/manifest only to refine the resume phase when reachable; a failed ground-truth read degrades to the persisted PHASE/counters, never a hard error. Counters are never derived from gh.
- **Source**: user

## Decision 3: What idempotent re-entry must skip
- **Question**: What redundant work must re-entry avoid when a PR already exists?
- **Resolution**: Skip checks/postbump/pr-prep (and re-creating the PR) when the PR already exists and is open; go straight to the OOS gate (if still pending) or the CI loop. When the PR is already merged, resume at postmerge. Today run_ship always restarts at checks, causing redundant rebase/push/CI churn against an open PR.
- **Source**: codebase + issue body

## Decision 4: Counter persistence semantics
- **Question**: How are the four CI-loop counters made session-wide?
- **Resolution**: iteration/rebase_count/fix_attempts/transient_retries are restored from the persisted state file (REBASE_COUNT/FIX_ATTEMPTS/ITERATION/TRANSIENT_RETRIES) at the top of the CI loop instead of always starting at 0, so the 50/20/10/1 caps are session-wide across exit-3/exit-6 handbacks. _write_ship_state already writes these keys; the gap is that they are never read back.
- **Source**: issue body + ship.py:532-535 / _write_ship_state

## Decision 5: Test matrix scope
- **Question**: What is the test surface?
- **Resolution**: Full enumerated matrix in test_ship.py (draft, forked dry-run, repo-unavailable, transient retry, each needs_user_reason, CI goto_rebase loop, cap exhaustion, idempotent re-entry, merge=false PR-only, merge retry) plus stage-order invariants and the CLI argv/env seams; in test_ci_monitor.py the monitor local-unfixable routing and the monitor bail-to-TRANSIENT path. All seams stubbed (no real bash / gh).
- **Source**: issue body

## Decision 6: Live behavior preservation
- **Question**: What must not break?
- **Resolution**: Existing python tests must stay green; the live bash ship-pr.sh path is untouched; OUTCOME_EXIT_MAP (0/1/3/4/6) and all stage-order invariants are preserved.
- **Source**: user + issue
