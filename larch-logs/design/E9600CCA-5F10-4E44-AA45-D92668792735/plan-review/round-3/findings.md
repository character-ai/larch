### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr.sh:3398-3432
- **Concern**: Rewrite `ci_fix_exhausted` to exit 3 without ready-jobs stubs. Scenario: Unified predicate requires `gh_logs_rc==0` and `ci_failed_rc==0` before `_code_fix_attempted_on_ready_log`; fixture uses default `gh` (exit 1) so `ci-failed-jobs.sh` never returns ready jobs—only vendor/check exhaustion—so flag stays false and exit 3 assertion fails after implementation
- **Proposed resolution**: Add `gh-run-logs.sh` stub (rc 0, deterministic body) and `gh`/jobs stub or `ci-failed-jobs.sh` wrapper returning rc 0 with fixable failed jobs; drive per-job entry or `vendor_rc==4` per predicate, not assert-line-only change

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2569-2657
- **Concern**: `ci_failed_rc==3` defer must skip the post-`ci_failed_rc` vendor block. Scenario: Today, when `gh_logs_rc==0` but `ci_failed_rc!=0`, only `record_failure` runs, then execution still reaches `if [[ "$per_job_verification_retry" == true ]]` / `run_ci_fix_vendor` (lines 2622-2656). A jobs-in-progress defer that only logs inside the inner `else` would still dispatch vendor fixers, breaking FINDING_4 parity with Python and reintroducing churn
- **Proposed resolution**: Add an `elif [ "$ci_failed_rc" -eq 3 ]` under `gh_logs_rc==0` that logs, bumps `_fix_attempt`, sleeps, and `continue`s the outer `while` before line 2622; do not rely on nested logic inside the `ci_failed_rc==0` `else` alone

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-bash-python-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:88-89 vs plan.txt:44-46,53-56
- **Concern**: Edge cases require fix-loop defer when logs are error/unreadable, but UPDATED Bash/Python steps only add explicit defer for in_progress (gh_logs_rc==3 / jobs in_progress). Scenario: Bash can still call run_ci_fix_vendor on gh-run-logs rc=1 (plan.txt:88-89); Python evaluate_failure only defers on logs.state==in_progress (python/ci_monitor.py:1021-1024), so error logs may still dispatch fixes and set exhaustion semantics differently than the stated contract
- **Proposed resolution**: Align UPDATED sections with Edge cases: defer outer attempts (backoff, no dispatch, no substantive flag) when gh_logs_rc!=0 && !=3 or logs.state==error; mirror in evaluate_failure
