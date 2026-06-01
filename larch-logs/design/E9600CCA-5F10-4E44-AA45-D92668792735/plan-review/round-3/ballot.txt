Validating referenced locations in read-only mode so normalized concerns match the code.
Three independent correctness risks (test fixture, Bash `ci_failed_rc==3` control flow, plan/Bash/Python defer contract). None describe the same behavioral failure with different wording, so they stay as three findings in first-seen order.

### FINDING_1: `ci_fix_exhausted` test cannot satisfy unified exit-3 predicate without log/job stubs
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Rewriting the `ci_fix_exhausted` scenario to assert exit 3 (without ready-jobs stubs) conflicts with the unified predicate that requires `gh_logs_rc==0` and `ci_failed_rc==0` before `_code_fix_attempted_on_ready_log` is set. With the fixture’s default `gh` (exit 1), `ci-failed-jobs.sh` never yields ready jobs—only vendor/check exhaustion—so the flag stays false and the post-implementation exit-3 assertion fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `gh-run-logs.sh` stub (rc 0, deterministic body) and `gh`/jobs stub or `ci-failed-jobs.sh` wrapper returning rc 0 with fixable failed jobs; drive per-job entry or `vendor_rc==4` per predicate, not assert-line-only change

### FINDING_2: `ci_failed_rc==3` defer must skip vendor block before line 2622
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: When `gh_logs_rc==0` but `ci_failed_rc==3` (jobs in progress), deferral must skip the post-`ci_failed_rc` vendor path. Today, a non-zero `ci_failed_rc` only runs `record_failure` in the inner `else`, then execution still reaches `if [[ "$per_job_verification_retry" == true ]]` / `run_ci_fix_vendor` (approximately lines 2622–2656). A jobs-in-progress defer confined to the nested `ci_failed_rc==0` branch would still dispatch vendor fixers, breaking FINDING_4 parity with Python and reintroducing churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an `elif [ "$ci_failed_rc" -eq 3 ]` under `gh_logs_rc==0` that logs, bumps `_fix_attempt`, sleeps, and `continue`s the outer `while` before line 2622; do not rely on nested logic inside the `ci_failed_rc==0` `else` alone

### FINDING_3: Error/unreadable logs defer missing from UPDATED plan and Python `evaluate_failure`
- **Reviewer(s)**: Cursor-dyn-bash-python-parity
- **Severity**: important
- **Concern**: Edge cases call for fix-loop defer when logs are error/unreadable, but the UPDATED Bash/Python steps only spell out defer for in-progress (`gh_logs_rc==3` / jobs `in_progress`). Bash can still call `run_ci_fix_vendor` on `gh-run-logs` rc=1 (per plan lines 88–89), while Python `evaluate_failure` defers only when `logs.state == "in_progress"` (`python/ci_monitor.py` ~1021–1024), so error logs may still dispatch fixes and set exhaustion semantics differently than the stated contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bash-python-parity: Align UPDATED sections with Edge cases: defer outer attempts (backoff, no dispatch, no substantive flag) when gh_logs_rc!=0 && !=3 or logs.state==error; mirror in evaluate_failure

**Merge note (for voters):** FINDING_2 targets the `gh_logs_rc==0` + `ci_failed_rc==3` path in `scripts/ship-pr.sh`. FINDING_3 targets log-collection failures (`gh_logs_rc` not 0/3, `logs.state==error`) and plan/Python parity. They share a “defer, don’t dispatch vendor” theme but need different control-flow and contract edits; keeping them separate avoids collapsing distinct fix surfaces.
