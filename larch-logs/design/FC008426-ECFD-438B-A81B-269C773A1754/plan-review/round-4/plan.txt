## Plan

Phase 6 — CI monitor loop (`python/ci_monitor.py`)

Port the CI-monitor portion of `scripts/ship-pr.sh` into a typed, unit-tested `python/ci_monitor.py`: poll CI, classify the action (parity with `ci-wait.sh`/`ci-status.sh`/`ci-decide.sh`), on a real failure collect+redact logs and drive the CI fixer waterfall to fix **all** failed jobs and verify each locally, push once, and emit a GOTO-Rebase signal. Compose Phase-1 foundation modules **only** (`config`, `proc`, `gh`, `agents`, `git`, `redact`, `outcomes`, `retry`, `errors`). The Phase-7 driver owns the GOTO-Rebase loop and rebase; this module signals. Additive only — no live `/implement` change, no `.sh` deletions (cutover is Phase 7). Blocked by Phase 1.

## Files to modify/create

### NEW: `python/ci_monitor.py`

The Phase-6 module. Imports stdlib + Phase-1 siblings only; must import cleanly with no import-time side effects (enforced by `test_stdlib_only.py`). Does NOT import `checks.py` (Phase 4), `rebase.py` (Phase 3), `merge.py`/`run_logs.py` (Phase 5), or `ship.py` (Phase 7). Members:

**Frozen dataclasses (typed records between functions):**
- `CiStatus` — port of `ci-status.sh` output: `status: str` (`pass`/`fail`/`pending`/`merged`/`NO_CHECKS`/`error`), `behind_count: int`, `failed_run_id: str | None`.
- `Decision` — port of `ci-decide.sh` output: `action: str` (`wait`/`rebase`/`merge`/`already_merged`/`rebase_then_evaluate`/`evaluate_failure`/`bail`), `bail_reason: str | None`.
- `JobClass` — one failed job: `name: str`, `shard: str`, `klass: str` (`fixable`/`no-local-equivalent`).
- `ClassifiedJobs` — port of `ci-failed-jobs.sh` aggregate: `count: int`, `jobs: tuple[JobClass, ...]`, `fixable: tuple[JobClass, ...]`, `unfixable: tuple[JobClass, ...]`.
- `RerunResult` — port of `ci-rerun-failed.sh`: `submitted: bool`, `already_running: bool`, `error: str | None`.
- `LogCollectResult` — port of `gh-run-logs.sh` outcome: `text: str` (redacted body; empty when unavailable), `state: str` (`ready`/`in_progress`/`error`).
- `FixResult` — outcome of one CI-fix invocation: `status: str` (`pushed`/`no-changes`/`waterfall-failed`/`first-fixer-non-health`/`head-changed`/`verify-failed`/`local-unfixable`), `winning_tier: str | None`, `delta_paths: tuple[str, ...]`, `unfixable: tuple[str, ...]`, `failed_verify: tuple[str, ...]` (job tokens that failed post-vendor `make` re-verify), `detail: str | None`.
- `MonitorResult` — the driver-facing signal: `action: str`, `ci_status: str`, `behind_count: int`, `failed_run_id: str | None`, `did_fixing: bool`, `goto_rebase: bool`, `iterations: int`, `result: outcomes.StepResult` (`OK`/`STALLED`/`TRANSIENT`/`NEEDS_USER_INPUT`).

**Status + decision (the classify heart; parity vs `ci-wait.sh` action classification):**
- `gather_status(runner, *, pr, repo, base_remote="origin", base_ref="main", empty_checks_grace=0) -> CiStatus` — port of `ci-status.sh`. Reuse `gh.pr_view` for the `MERGED` short-circuit; run `gh pr checks <pr> --repo <repo> --json name,state,bucket,link` via the injected `Runner` (mirror Phase 4's "gh.py stays minimal — extra reads via Runner"); count buckets (`fail`→`fail` + extract `FAILED_RUN_ID` from the first failed `link` via `runs/<id>` regex; else `pending`→`pending`; else `pass`); compute `behind_count` with `git.rev_count`/`git.merge_base` against `<base_remote>/<base_ref>` (fetch via Runner; fetch-fail → `pending`/0 to force retry, parity); squash-merge race detection via `git log HEAD..<base>` containing `(#<pr>)` → `merged`. Empty-checks-grace and `NO_CHECKS` handled with an injectable `sleep_fn`.
- `decide(status, *, iteration, rebase_count, fix_attempts) -> Decision` — **pure** port of `ci-decide.sh` decision matrix. `merged`→`already_merged`; `pass`+not-behind→`merge` (allowed past caps); `error`→`bail`; safety limits in order: `iteration >= config.CI_MONITOR_MAX_ITERATIONS` → `bail` (timeout), `rebase_count >= config.CI_MONITOR_MAX_REBASES` → `bail`, `fix_attempts >= config.CI_MONITOR_MAX_FIX_ATTEMPTS` → `bail` (`fix-attempts-exhausted`); then `pending`+behind→`rebase`/`pending`→`wait`; `pass`+behind→`rebase`; `fail`+behind→`rebase_then_evaluate`/`fail`→`evaluate_failure`. No I/O — the primary bash-parity test target.
- `poll_ci(runner, *, pr, repo, base_remote, base_ref, empty_checks_grace, iteration, rebase_count, fix_attempts, timeout=config.CI_WAIT_TIMEOUT_SEC, sleep_fn=time.sleep, clock=time.monotonic) -> tuple[CiStatus, Decision]` — port of `ci-wait.sh` poll loop: poll-count budget `MAX_POLLS = ceil(timeout/CI_WAIT_POLL_INTERVAL_SEC)`, suspend-resilient (a sleep window > 60s is not charged), 3-consecutive empty/`error` statuses → `bail`, `NO_CHECKS` → `bail`, return on first non-`wait` action. `sleep_fn`/`clock` injectable so tests run with zero wall-clock.

**Failed-job classification + log/rerun primitives:**
- `classify_failed_jobs(jobs) -> ClassifiedJobs` — port of `ci-failed-jobs.sh`. Input `tuple[gh.FailedJob, ...]` (from `gh.failed_jobs`); parse matrix `name (shard)` form; `klass` from `config.CI_FIXABLE_JOBS` membership (else `no-local-equivalent`); malformed names → `no-local-equivalent`.
- `read_failed_jobs(runner, *, run_id, repo) -> tuple[tuple[gh.FailedJob, ...], str]` — parity wrapper over `gh.failed_jobs_read` (not `gh.failed_jobs`): parse JSON jobs on rc==0; stderr/stdout containing `is still in progress; logs will be available` → `([], "in_progress")` (parity `ci-failed-jobs.sh` exit 3); other non-zero → log warning via Runner capture, return `([], "error")` and continue (parity `ship-pr.sh:2619-2621` — empty TSV, no hard fail).
- `collect_failed_logs(runner, *, run_id, repo) -> LogCollectResult` — port of `gh-run-logs.sh`: `gh run view <run_id> --repo <repo> --log-failed`, tail to `config.CI_MONITOR_LOG_TAIL_LINES` (100), prepend the run/repo pointer line, route captured text through `redact.redact()`; `state="ready"` when logs obtained, `"in_progress"` when the in-progress message is detected (parity rc=3), `"error"` on other failures (empty `text`).
- `rerun_failed(runner, *, run_id, repo) -> RerunResult` — port of `ci-rerun-failed.sh` via `gh.run_rerun(failed_only=True)`; combined-output "already running" → `submitted=True, already_running=True`; non-zero else → `submitted=False` + `error`.

**Local verification (per-job):**
- `per_job_command(name, shard) -> tuple[str, ...] | None` — port of `_per_job_argv` (larch CI job → local `make` argv: `lint`→`env SKIP=agnix,lint-mermaid-fences,shellcheck make lint-only`, `lint-mermaid`/`shellcheck`/`agent-lint`/`agnix`/`smoke-dialectic`/`agent-sync`→`make <target>`, `test-harnesses[-<shard>]`, `python-lint`→`make py-lint`, `python-tests`→`make py-test`); unknown → `None`.
- `prepare_python_toolchain(runner, name) -> bool` — port of `_prepare_python_job_toolchain` (best-effort `pip install -r requirements-dev.txt`/`requirements-test.txt` for `python-lint`/`python-tests`; missing tool on PATH → `False` so the job is treated unfixable-locally rather than spuriously failing).
- `verify_job_locally(runner, name, shard, *, cwd) -> bool` — run `per_job_command` via `Runner`; `True` iff rc == 0.

**Fixer waterfall + stage/push (the "fix all jobs, verify locally, push" core):**
- `run_ci_fix(runner, *, run_id, repo, classified, logs: LogCollectResult, plan_file, start_attempt, cwd, launch_fn=None, output_dir: str | None = None) -> FixResult` — drive the CI vendor waterfall once. Capture baseline tracked/untracked/staged paths + `baseline_head` (`git.rev_parse` + `git diff --name-only [--cached]` via Runner); default `launch_fn` builds argv per tier via `agents.build_launch_argv(tier, role=config.CI_FIX_ROLE, output=<per-tier path under output_dir or IMPLEMENT_TMPDIR-style prefix>, run_id=run_id, repo=repo, plan_file=plan_file, failure_log=<redacted path> only when `logs.state == "ready"` and `logs.text` is non-empty, timeout_sec=config.SUBPROCESS_DEFAULT_TIMEOUT_SEC)`, runs through `Runner`, parses `LAUNCHER_EXIT=` into `TierAttempt`, classifies with `agents.classify_launch_failure`; rotate first tier by `start_attempt % len(config.FIXER_TIER_ORDER)` and delegate iteration + the **first-fixer-non-health short-circuit** (first tier only, pre-verify) to `agents.run_waterfall`; rollback the working tree to baseline after a losing tier. After a winning tier: verify **every** `fixable` job locally (`verify_job_locally`, with `prepare_python_toolchain`); any `no-local-equivalent` row or job with no `per_job_command`/failed toolchain prep → `local-unfixable` with `unfixable` populated (immediate bail token — parity with `_verify_failed_jobs_locally` exit 3 for non-fixable rows); any fixable job that still fails `make` re-verify → `verify-failed` with `failed_verify` listing those job tokens (parity with `run_ci_fix_vendor` return `4` — **not** `local-unfixable`); detect HEAD moved underneath during fix/verify (`head-changed`); on verify success call `stage_and_push` and capture `post_stage_head`; return `first-fixer-non-health` **only** when staging completes (`stage_and_push` pushed or no-op commit path succeeds) but `baseline_head == post_stage_head` (parity `run_ci_fix_vendor:2140-2167` — compare after `_stage_and_push_ci_fixes`, not on pre-stage vendor exit alone). Do not stage/push on `verify-failed`.
- `stage_and_push(runner, *, cwd, commit_label) -> tuple[bool, str | None, tuple[str, ...]]` — `git add -- <delta>`, commit via `scripts/git-commit.sh --no-trailer -m "Apply CI fixes (<label>)"` through the Runner (commit-message parity, mirroring Phase 4), then **normal** `git.push` (no inline rebase / no force-push — the driver owns rebase + force-push). Returns `(pushed, commit_sha, delta_paths)`.

**Top-level orchestration:**
- `evaluate_failure(runner, *, run_id, repo, plan_file, transient_retries, fix_attempts, cwd, launch_fn=None, sleep_fn=time.sleep) -> FixResult` — port of `run_evaluate_failure`: when `transient_retries < config.CI_MONITOR_TRANSIENT_RERUN_MAX`, `rerun_failed` only (no fix; count toward the transient budget unless `already_running`) and return `no-changes`; otherwise loop the fix path up to `config.CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS` (3) with jittered backoff via `sleep_fn` (deterministic seed via attempt index — vary backoff by attempt index, not RNG). **Each outer attempt** (parity `ship-pr.sh:2532-2573`): `collect_failed_logs` → if `state == "in_progress"` OR `read_failed_jobs` returns `in_progress`, consume the outer attempt, apply backoff, **no** `run_ci_fix`/`launch_fn` (parity `gh-run-logs`/`ci-failed-jobs` rc=3 deferral); else `read_failed_jobs` + `classify_failed_jobs` and pass fresh `LogCollectResult` into `run_ci_fix` (never reuse logs from a prior attempt or from `monitor`). Per outer attempt after refresh: `run_ci_fix` → on `local-unfixable` bail immediately; on `verify-failed` consume the outer attempt, apply backoff, and **re-drive** on the next outer iteration (fresh logs/jobs); on `head-changed` return immediately; on `pushed` return `pushed`; on `waterfall-failed`/`first-fixer-non-health` return as-is. After the outer cap is exhausted with `verify-failed` still outstanding → `waterfall-failed` with `detail`/`failed_verify` naming the jobs (distinct from `local-unfixable`, reserved for `no-local-equivalent` rows only).
- `monitor(runner, *, pr, repo, base_remote="origin", base_ref="main", empty_checks_grace=0, iteration=0, rebase_count=0, fix_attempts=0, transient_retries=0, plan_file=None, cwd=None, launch_fn=None, sleep_fn=time.sleep, clock=time.monotonic) -> MonitorResult` — the driver entrypoint. `poll_ci` → on `merge`/`already_merged` → `OK` (no GOTO-Rebase); on `rebase`/`rebase_then_evaluate` → `goto_rebase=True`, `did_fixing=False`, `OK` (parity `ship-pr.sh:3547-3549`: rebase before fix; Phase-7 driver re-enters `monitor` after rebase — **do not** call `evaluate_failure` while still behind); on `evaluate_failure` only → `evaluate_failure(runner, run_id=<failed_run_id from CiStatus>, repo, plan_file, ...)` (no one-shot log/job prefetch — `evaluate_failure` owns per-attempt refresh), then `goto_rebase=True` when fixing pushed work, map `FixResult.status` → `StepResult` (`pushed`→`OK`+GOTO-Rebase; `head-changed`→`STALLED`; `first-fixer-non-health`→`NEEDS_USER_INPUT` with `detail` naming the token; `local-unfixable`/`waterfall-failed`/`verify-failed` after outer exhaustion→`STALLED` with detail); on `bail` → `bail_reason=fix-attempts-exhausted` → `NEEDS_USER_INPUT` (parity `needs_user_bail_reason` / exit 3); other bails → `STALLED` with `bail_reason`. The GOTO-Rebase loop + its cap stay in the Phase-7 driver.

### NEW: `python/test_ci_monitor.py`

pytest unit tests (colocated). Stub `Runner` (scripted `gh`/`git`/`make` results keyed by argv), stub `launch_fn` for the agent waterfall, injected `sleep_fn`/`clock` (zero wall-clock). Semantic Python-only parity — no bash executed. Cases under Testing strategy.

### UPDATED: `python/config.py`

Additive only (no edits to existing constants). Add under a `# CI monitor loop (Phase 6)` block:
- `CI_MONITOR_MAX_ITERATIONS = 50`, `CI_MONITOR_MAX_REBASES = 20`, `CI_MONITOR_MAX_FIX_ATTEMPTS = 10` (parity with `ci-decide.sh` safety limits).
- `CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS = 3` (parity with `run_evaluate_failure` `_max_fix`).
- `CI_MONITOR_TRANSIENT_RERUN_MAX = 1` (parity with `TRANSIENT_RETRIES < 1`).
- `CI_MONITOR_STATUS_FAILURE_BAIL = 3` (parity with `ci-wait.sh` 3-consecutive-failure bail).
- `CI_MONITOR_LOG_TAIL_LINES = 100` (parity with `gh-run-logs.sh`).
- `CI_FIX_ROLE = "fix"`.
- `CI_FIXABLE_JOBS: Final[frozenset[str]]` = the `ci-failed-jobs.sh` fixable set (`lint`, `lint-mermaid`, `shellcheck`, `test-harnesses`, `agent-lint`, `agnix`, `smoke-dialectic`, `agent-sync`, `python-lint`, `python-tests`). Reuse existing `CI_WAIT_TIMEOUT_SEC`, `CI_WAIT_POLL_INTERVAL_SEC`, `FIXER_TIER_ORDER`, `SUBPROCESS_DEFAULT_TIMEOUT_SEC`.

### UPDATED: `python/README.md`

Add one `ci_monitor.py` bullet to the Layout list (CI poll + classify + collect + fixer-waterfall + GOTO-Rebase signal; Phase 6). Doc-only; no count edits.

## Approach

- **Compose, do not duplicate.** Reuse `gh.pr_view`/`gh.failed_jobs`/`gh.run_rerun`/`gh.run_view`, `git.rev_parse`/`rev_count`/`merge_base`/`push`/`reset`, `agents.run_waterfall`/`launch_tier`/`classify_launch_failure`/`is_transient_infra_failure` (CI-only waterfall, cursor→codex→claude), `redact.redact()`, `outcomes.Outcome`/`StepResult`, `retry`. Keep `gh.py`/`git.py` edits to zero — the verbs they lack (`gh pr checks`, `git diff --name-only [--cached]`, `git add`, `git checkout --`) run through the injected `Runner` inside `ci_monitor.py` (parity with the Phase-4 precedent in #3237).
- **Two fixer surfaces are distinct.** The CI fixer is the launch-`*`-ci.sh waterfall via `agents.run_waterfall` (`FIXER_TIER_ORDER = cursor,codex,claude`). Phase 4's `run-external-agent.sh` per-job local fixer is explicitly out — when a fixable job still fails its local `make` re-verify after a winning vendor tier, return `verify-failed` and let `evaluate_failure` re-drive the CI waterfall (capped at `CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS` with backoff; Round 1 Decision 3), never import/duplicate `checks.py` and never map fixable verify regression to `local-unfixable` on the first failure.
- **Decoupled rebase.** `stage_and_push` does a normal push; on any pushed fix `monitor` returns `goto_rebase=True` and the driver re-bases (Phase 3) + force-pushes. No `run_rebase_rebump` inline (Round 1 Decision 4).
- **`rebase_then_evaluate` is rebase-only in `monitor`.** Like `rebase`, emit `goto_rebase` without fixing; the driver runs Phase-3 rebase then calls `monitor` again (which may then see `evaluate_failure`). Matches `ship-pr.sh` ordering (rebase before `run_evaluate_failure`).
- **No logging side effects.** Drop the bash `append-token-record.sh`/`refresh-run-logs.sh` calls inside stage/push — log flushing is Phase 5 / driver territory.
- **Per-outer-attempt ground truth.** `evaluate_failure` re-fetches redacted logs and failed-job classification at the start of every outer attempt (parity `run_evaluate_failure` + `test-ship-pr-fix-loop-2632.inc.sh`); `monitor` does not cache logs across the fix loop.
- **In-progress deferral consumes outers only.** rc=3-equivalent `in_progress` from `collect_failed_logs` or `read_failed_jobs` skips `run_ci_fix` for that attempt (backoff only) — never dispatch the vendor waterfall on empty/stale logs.
- **Determinism.** All subprocess work via `proc.Runner`; all wall-clock via injected `sleep_fn`/`clock`; backoff varies by attempt index (no `random`). Frozen dataclasses between functions.

## Edge cases

- `gh pr checks` empty array → `NO_CHECKS` only when `empty_checks_grace > 0` after the grace sleep, else `pending` (parity).
- `git fetch <base>` fails → `pending`/`behind_count=0` to force a retry instead of trusting stale refs.
- Squash-merge race: `behind > 0` but `HEAD..<base>` contains `(#<pr>)` → `merged`, `behind=0`, clear `failed_run_id`.
- `rebase_then_evaluate` → `goto_rebase` only (no `evaluate_failure` in the same `monitor` call); fixing runs only after the driver rebases and re-polls.
- `merge` is allowed even after a safety-limit cap is hit; safety limits only block non-merge actions.
- Transient first failure (`transient_retries < 1`) → `rerun_failed` only; `already_running` does not consume the transient budget.
- `no-local-equivalent` jobs (`gitleaks`, `trufflehog`, unknown) → never fixed locally → `local-unfixable` bail with the sanitized job list (immediate; parity with `_verify_failed_jobs_locally` exit 3 for non-fixable rows).
- Fixable job fails post-vendor `make` re-verify → `verify-failed` (parity with `run_ci_fix_vendor` return `4`); `evaluate_failure` retries up to 3 outer attempts with backoff before `waterfall-failed`/`STALLED` — one failed lint replay must not end the fix loop on the first verify miss.
- HEAD moved underneath during fix/verify/push → `head-changed` → `STALLED` (parity with `exit_stall`); the branch moved, abandon this fix.
- Winning fixer tier exits 0 but `stage_and_push` leaves `HEAD` at `baseline_head` → `first-fixer-non-health` (parity `run_ci_fix_vendor:2140-2167`; check only after staging, not on vendor exit alone).
- `gh run view --log-failed` or failed-job fetch "still in progress" → `evaluate_failure` outer deferral only (parity rc=3); no `run_ci_fix`/`launch_fn` that attempt.
- `gh.failed_jobs_read` non-zero (non-in-progress) → warning + empty job list; `monitor`/`evaluate_failure` continue (parity `ship-pr.sh:2619-2621`, `run_ci_fix_vendor` with empty TSV).
- Default CI `launch_fn` must pass `run_id`, `repo`, and per-tier `output` via `agents.build_launch_argv`; omit `--failure-log` when redacted logs are empty or `in_progress`.
- Poll budget exhausted / 3 consecutive `ci-status` failures → `bail`; suspend (sleep window > 60s) is not charged to the budget.
- `launch-claude-ci.sh` missing/non-exec → that tier is skipped in the waterfall (parity), not a hard failure.

## Failure modes

1. **Action-classification divergence from `ci-decide.sh`.** A wrong matrix cell silently mis-routes the driver (e.g. `merge` when behind, or no `bail` at the cap). Earliest signal: the table-driven parity test in `test_ci_monitor.py` flags a cell. Mitigation: `decide` is a pure function tested against every `ci-decide.sh` row, including all three caps and the `merge`-past-cap allowance.
2. **Coupling leak into Phase 3/4/5.** Importing `rebase.py`/`checks.py` or calling `run_rebase_rebump`/`run-external-agent.sh` would break "blocked by Phase 1 only" and diverge from the decoupled driver contract. Earliest signal: `test_stdlib_only.py` import graph / a grep for sibling imports. Mitigation: depend only on Phase-1 modules; rebase is a returned signal; per-job re-fix re-drives the CI waterfall via `verify-failed` → outer retry, not `checks.py`.
3. **Redaction gap in collected logs.** A failed-job log could leak a secret/path into a fixer prompt or returned text. Earliest signal: a seeded-secret redaction test on `collect_failed_logs`. Mitigation: route all `--log-failed` output through `redact.redact()` before it leaves `collect_failed_logs`; assert it.
4. **Verify-failure misclassified as `local-unfixable`.** A fixable job that fails `make` re-verify after a winning vendor tier would end the fix loop on the first miss instead of re-driving the waterfall (regression vs `run_evaluate_failure` `vendor_rc=4` retry). Earliest signal: `test_ci_monitor.py` case where stub `verify_job_locally` fails once then passes on the second `run_ci_fix` outer attempt. Mitigation: `run_ci_fix` returns `verify-failed` + `failed_verify` for fixable regressions only; `evaluate_failure` owns outer backoff/retry; reserve `local-unfixable` for `no-local-equivalent` rows.
5. **`rebase_then_evaluate` inline fix while behind.** Dispatching `evaluate_failure` before rebase would fix against a stale base and diverge from `ship-pr.sh:3547-3549`. Earliest signal: `test_ci_monitor.py` `rebase_then_evaluate` asserts `did_fixing=False` and no `evaluate_failure`/`launch_fn` calls. Mitigation: same branch as `rebase` in `monitor`.
6. **Exit-3 terminals mapped to `STALLED`.** `fix-attempts-exhausted` bail or `first-fixer-non-health` fix result routed to `STALLED` would block autonomous exit-3 handling in the Phase-7 driver. Earliest signal: parity tests on `monitor` bail/fix terminals. Mitigation: explicit `NEEDS_USER_INPUT` for those tokens only; keep timeout/`NO_CHECKS`/rebase-cap bails on `STALLED`.
7. **Stale logs across outer attempts.** Reusing one `logs_redacted` blob from `monitor` would mislead fixers after rerun/CI progression (regression vs `run_evaluate_failure` per-attempt `gh-run-logs.sh`). Earliest signal: test asserting `collect_failed_logs` call count == outer attempt index. Mitigation: refresh logs (and jobs) inside `evaluate_failure` only.
8. **Vendor dispatch on in-progress or incomplete launch argv.** Calling `run_ci_fix` with `in_progress`/empty logs or a default `launch_fn` missing `run_id`/`repo`/`output` wastes waterfall attempts or cannot invoke launchers. Earliest signal: outer loop tests with rc=3 stubs (`launch_fn` call count 0) and argv assertions on `build_launch_argv` fields. Mitigation: defer outers on `in_progress`; build argv via `agents.build_launch_argv`.

## Testing strategy

`python/test_ci_monitor.py` (pytest, stubs only — no bash, zero wall-clock):

- `decide` parity table: every `ci-decide.sh` row — `merged`→`already_merged`; `pass`/not-behind→`merge`; `pass`/behind→`rebase`; `pending`/behind→`rebase`; `pending`→`wait`; `fail`/behind→`rebase_then_evaluate`; `fail`→`evaluate_failure`; `error`→`bail`; `iteration>=50`/`rebase>=20`/`fix>=10`→`bail`; `merge` still allowed past each cap.
- `gather_status`: stub `Runner` returns canned `gh pr view` + `gh pr checks` + git → assert `status`/`behind_count`/`failed_run_id`; `MERGED` short-circuit; empty checks + grace → `NO_CHECKS`; fetch-fail → `pending`; squash-merge race → `merged`.
- `poll_ci`: returns on first non-`wait`; budget exhaustion → `bail`; 3 consecutive `error` → `bail`; suspend window not charged (stub `clock`).
- `classify_failed_jobs`: matrix shard parse; `fixable` vs `no-local-equivalent`; malformed names.
- `collect_failed_logs` / `LogCollectResult`: 100-line cap + pointer line + seeded-secret routed through `redact.redact()`; in-progress → `state=in_progress`, empty `text`; other errors → `state=error`.
- `read_failed_jobs`: rc=0 failures parsed; in-progress message → `in_progress`; other non-zero → empty jobs + `error` (no raise).
- `rerun_failed`: submitted; `already_running`; failure → `error`.
- `verify_job_locally`/`per_job_command`: job→`make` argv table; rc==0 → pass; unknown job → `None`.
- `run_ci_fix`: stub `launch_fn` — argv includes `run_id`, `repo`, `output`; `--failure-log` only when `logs.state==ready` and text non-empty; winning tier → local-verify → `stage_and_push` → `pushed`; `baseline_head == post_stage_head` after successful stage → `first-fixer-non-health` (not before stage); first-fixer non-health short-circuit on first tier pre-verify; HEAD-changed → `head-changed`; `no-local-equivalent` → `local-unfixable`; fixable verify miss → `verify-failed` (no push); baseline rollback on losing tier; normal `git.push` (no force-push).
- `evaluate_failure`: `transient_retries<1` → `rerun_failed` only; each outer calls `collect_failed_logs` + `read_failed_jobs` (assert call count tracks attempt); `in_progress` logs or jobs → backoff only, `launch_fn` call count unchanged that attempt; `verify-failed` then pass on next outer with fresh logs → second `run_ci_fix` (`launch_fn` count == 2) then `pushed`; three `verify-failed` outers → `waterfall-failed`; `local-unfixable` only when `unfixable` non-empty; `head-changed` → immediate return.
- `monitor`: `merge`→`OK`, no GOTO-Rebase; `rebase`/`rebase_then_evaluate`→`goto_rebase`, `did_fixing=False`, no `launch_fn`; `evaluate_failure` action delegates to `evaluate_failure(...)` without prefetching logs; pushed fix → `OK`+`goto_rebase`; exit-3 terminals → `NEEDS_USER_INPUT`; other bails → `STALLED`.
- stdlib-only + clean import auto-covered by `test_stdlib_only.py`.

## Acceptance

- `python/ci_monitor.py` exists and exposes `gather_status`, `decide`, `poll_ci`, `classify_failed_jobs`, `collect_failed_logs`, `rerun_failed`, `per_job_command`, `verify_job_locally`, `run_ci_fix`, `stage_and_push`, `evaluate_failure`, `monitor`, and the frozen records; imports stdlib + Phase-1 siblings only and passes `test_stdlib_only.py`.
- Poll/classify, the fix loop, cap enforcement, HEAD-changed handling, verify-failure outer retry (`verify-failed` → re-drive waterfall), and the GOTO-Rebase signal are unit-tested with a **stub gh** and **stub agent waterfall** — no bash executed.
- `decide` has full bash-parity coverage vs `ci-decide.sh` (every matrix row + all three caps + merge-past-cap).
- Collected logs are redacted (`collect_failed_logs` → `LogCollectResult` routed through `redact.redact()`, asserted on a seeded secret); logs and failed jobs refresh each `evaluate_failure` outer attempt; `in_progress` defers vendor dispatch (no `launch_fn`) for that attempt only.
- Fixable post-vendor verify regression uses `verify-failed` + outer retry; `local-unfixable` is reserved for `no-local-equivalent` jobs only.
- `first-fixer-non-health` only after `stage_and_push` when `baseline_head == post_stage_head`; default `launch_fn` uses `agents.build_launch_argv` with `run_id`, `repo`, `output`.
- `read_failed_jobs` uses `gh.failed_jobs_read`; non-in-progress failures yield empty jobs without aborting `monitor`.
- Exit-3 parity: `bail`/`fix-attempts-exhausted` and fix-path `first-fixer-non-health` map to `NEEDS_USER_INPUT`; other bails remain `STALLED`.
- `rebase_then_evaluate` does not dispatch fixes before rebase (`did_fixing=False`, same as `rebase`).
- No import of `checks.py`/`rebase.py`/`merge.py`/`run_logs.py`/`ship.py`; `gh.py`/`git.py` unedited; the live `/implement` path unchanged and no `.sh` deleted.
- `make py-lint` (ruff + pylint + pyright) and `make py-test` (pytest) pass.

## Diff size estimate

New module + colocated tests dominate (mostly additions): module ~680 lines, tests ~760 lines, `config.py` ~15, `README.md` ~2.

diff_added: 1455
diff_lines: 1475
