### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:42-43,68-69,78
- **Concern**: `rebase_then_evaluate` defers fixing to a second `monitor()` poll after driver rebase. Scenario: Bash runs `run_rebase_rebump` then `run_evaluate_failure` immediately (`scripts/ship-pr.sh:3547-3549`). Re-polling can return `wait`/`pending` while CI is still running and skip the fix path that bash always enters.
- **Proposed resolution**: Phase 7 contract: after `goto_rebase` from `rebase_then_evaluate`, call `evaluate_failure` directly (or add a monitor flag) instead of relying only on a fresh `poll_ci`.

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:42-43
- **Concern**: `monitor` collects logs once and passes a single `logs_redacted` into `evaluate_failure`; the outer fix loop does not re-fetch logs each attempt. Scenario: Bash `run_evaluate_failure` calls `gh-run-logs.sh` at the start of every outer attempt (`scripts/ship-pr.sh:2532-2534`); stale logs after rerun or CI progression can mislead the vendor fixer or omit `--failure-log` when fresh logs exist
- **Proposed resolution**: Add per-outer-attempt `collect_failed_logs` inside `evaluate_failure` (refresh `logs_redacted` before each `run_ci_fix`), matching `ship-pr.sh` and `scripts/test-ship-pr-fix-loop-2632.inc.sh` outer-budget tests

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:42-43
- **Concern**: `evaluate_failure` does not specify `gh run view --log-failed` / `ci-failed-jobs` in-progress deferral (bash rc=3) with backoff-only outer attempts. Scenario: Bash skips vendor dispatch for that attempt when logs are still in progress (`scripts/ship-pr.sh:2567-2568`, `scripts/ship-pr.md:129`); calling `run_ci_fix` with empty logs diverges and wastes waterfall attempts
- **Proposed resolution**: On in-progress log collection (and optionally failed-job fetch), consume an outer attempt with backoff only—no `run_ci_fix` / `launch_fn`—parity with rc=3 deferral

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:37-39
- **Concern**: `first-fixer-non-health` is described against “HEAD unchanged” without requiring a post-`stage_and_push` check. Scenario: Bash classifies only after `_stage_and_push_ci_fixes` when `baseline_head` equals `pre_refresh_head` (`scripts/ship-pr.sh:2140-2167`); checking before stage/push can miss the condition or return the wrong `FixResult`
- **Proposed resolution**: Run verify → `stage_and_push` → compare pre-stage `HEAD` to post-stage `HEAD`; return `first-fixer-non-health` only when staging completes but `HEAD` is unchanged

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:38
- **Concern**: `run_ci_fix` default `launch_fn` omits required `agents.build_launch_argv` fields (`--run-id`, `--repo`, `--output`). Scenario: `agents.launch_tier` / `build_launch_argv` require `run_id`, `repo`, and `output` (`python/agents.py:129-169`); defaults as written cannot invoke CI launchers
- **Proposed resolution**: Specify `launch_fn` builds argv with `run_id`, `repo`, per-tier `output` path, optional `--failure-log` only when redacted logs are non-empty, and parses `LAUNCHER_EXIT=` into `TierAttempt`

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:42
- **Concern**: `monitor` calls `gh.failed_jobs` without an in-progress / non-zero fallback path. Scenario: `gh.failed_jobs` raises on non-zero (`python/gh.py:507-516`); bash records a warning and may still call `run_ci_fix_vendor` with an empty TSV (`scripts/ship-pr.sh:2619-2663`)
- **Proposed resolution**: Use `failed_jobs_read`, treat “still in progress” like `ci-failed-jobs.sh` exit 3, and on other failures continue with empty classification rather than failing the whole `monitor` call
