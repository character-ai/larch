### FINDING_2: Outer fix loop does not refresh logs each attempt
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `monitor` collects logs once and passes a single `logs_redacted` into `evaluate_failure`; the outer fix loop does not re-fetch logs each attempt. Bash `run_evaluate_failure` calls `gh-run-logs.sh` at the start of every outer attempt (`scripts/ship-pr.sh:2532-2534`). Stale logs after rerun or CI progression can mislead the vendor fixer or omit `--failure-log` when fresh logs exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add per-outer-attempt `collect_failed_logs` inside `evaluate_failure` (refresh `logs_redacted` before each `run_ci_fix`), matching `ship-pr.sh` and `scripts/test-ship-pr-fix-loop-2632.inc.sh` outer-budget tests


### FINDING_3: No in-progress log deferral (bash rc=3 parity)
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `evaluate_failure` does not specify `gh run view --log-failed` / `ci-failed-jobs` in-progress deferral (bash rc=3) with backoff-only outer attempts. Bash skips vendor dispatch for that attempt when logs are still in progress (`scripts/ship-pr.sh:2567-2568`, `scripts/ship-pr.md:129`); calling `run_ci_fix` with empty logs diverges and wastes waterfall attempts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: On in-progress log collection (and optionally failed-job fetch), consume an outer attempt with backoff only—no `run_ci_fix` / `launch_fn`—parity with rc=3 deferral


### FINDING_4: `first-fixer-non-health` missing post-`stage_and_push` HEAD check
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `first-fixer-non-health` is described against “HEAD unchanged” without requiring a post-`stage_and_push` check. Bash classifies only after `_stage_and_push_ci_fixes` when `baseline_head` equals `pre_refresh_head` (`scripts/ship-pr.sh:2140-2167`); checking before stage/push can miss the condition or return the wrong `FixResult`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Run verify → `stage_and_push` → compare pre-stage `HEAD` to post-stage `HEAD`; return `first-fixer-non-health` only when staging completes but `HEAD` is unchanged


### FINDING_5: `run_ci_fix` default `launch_fn` omits required launch argv fields
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `run_ci_fix` default `launch_fn` omits required `agents.build_launch_argv` fields (`--run-id`, `--repo`, `--output`). `agents.launch_tier` / `build_launch_argv` require `run_id`, `repo`, and `output` (`python/agents.py:129-169`); defaults as written cannot invoke CI launchers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify `launch_fn` builds argv with `run_id`, `repo`, per-tier `output` path, optional `--failure-log` only when redacted logs are non-empty, and parses `LAUNCHER_EXIT=` into `TierAttempt`


### FINDING_6: `monitor` `gh.failed_jobs` lacks in-progress / non-zero fallback
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `monitor` calls `gh.failed_jobs` without an in-progress / non-zero fallback path. `gh.failed_jobs` raises on non-zero (`python/gh.py:507-516`); bash records a warning and may still call `run_ci_fix_vendor` with an empty TSV (`scripts/ship-pr.sh:2619-2663`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Use `failed_jobs_read`, treat “still in progress” like `ci-failed-jobs.sh` exit 3, and on other failures continue with empty classification rather than failing the whole `monitor` call

---

**Merge notes (informational):** All six inputs were kept separate. FINDING_2 and FINDING_3 both concern log handling in the fix loop but need different fixes (per-attempt refresh vs. in-progress deferral). FINDING_3 and FINDING_6 both mention in-progress CI behavior but apply to different call sites (`evaluate_failure` vs. `monitor` / `failed_jobs`). No `[OUT_OF_SCOPE]` tags in the input. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).

