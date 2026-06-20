## Plan

## Approach

Implement stale `.git/index.lock` handling at the shared git helper layer so every production commit path benefits, including pre-commit staging.

The original plan only wrapped `commit()` / `commit_with_trailer()`. Production Step 5 and stall-recovery paths fail earlier on `git add` when a stale lock is present:

- `commit_main()` runs `add_pathspec_file()` / `add()` before commit.
- `_stage_and_commit_round()` runs a raw `git add --pathspec-from-file` before `cli.py git commit`.
- `commit_fixes --stage-all` runs a raw `git add --pathspec-from-file` before `cli.py git commit`.
- `_commit_lint_fix_delta_paths()` runs a raw `git add --pathspec-from-file` before `cli.py git commit` on Step 5 post-round lint-fix commits.

Fix at the chokepoints:

1. Add shared stale-lock probe/remove helpers in `python/git.py`.
2. Add a generic one-shot retry wrapper for any git argv that can fail on `index.lock`.
3. Route `add()`, `add_pathspec_file()`, `commit()`, and `commit_with_trailer()` through that policy.
4. In `commit_main()`, run a preemptive safe-lock sweep before staging, then rely on the wrapped staging helpers (which retry once on lock failure).
5. Remove duplicate raw pre-add calls in `review_and_fix.py` so **all three** commit helpers route staging only through `commit_main()`:
   - `_stage_and_commit_round`
   - `commit_fixes --stage-all`
   - `_commit_lint_fix_delta_paths`
6. Surface a distinct `CODER_STATUS=stale-index-lock` on the Step 5 review coder path when lock cleanup is refused, while **keeping** `STALL_REASON=coder-failed` so existing `stall_recovery.py` classification and `RESUME_HINT=step5-review` behavior remain intact without touching `stall_recovery.py`.

**Stall-reason scope reduction (accepted finding):** Do **not** introduce `STALL_REASON=stale-index-lock`. That token is absent from `config.LINT_FIX_BAIL_REASON_TOKENS` and has no `_classify_text` branch, so it would classify as `unrecoverable` / `RESUME_HINT=none` and break Step 18a resume after an operator manually clears a lock larch refused to remove. Keep the existing `coder-failed` stall envelope; operators and logs distinguish stale-lock via `CODER_STATUS=stale-index-lock` and `larch: stale .git/index.lock not removed: …` stderr from `git.py`. With guarded auto-removal in `commit_main()`, most stalls should clear on retry; when removal is refused, `coder-failed` + `CODER_STATUS=stale-index-lock` preserves the documented `step5-review` recovery path once the operator removes the lock.

**Repo-scoped live-process probe (accepted finding):** Do **not** block stale-lock removal because an unrelated `git` process is running in a different repository (e.g., a concurrent `/design` session). Replace the planned system-wide "any live git process" scan with a **target-repo / lock-holder** probe:

- Resolve `lock_path` via `_git_index_lock_path(runner, cwd=cwd)`.
- Treat the lock as actively held only when a process is using **this** `index.lock` or operating on **this** git directory.
- Unrelated git PIDs must **not** block removal of a 0-byte stale lock in the target repo.

Do not change `python/implement_dispatch.py` timeout guard.

Do not change `python/stall_recovery.py`.

## Files to modify/create

### UPDATED: python/git.py

Add stale-lock helpers near the existing commit helpers.

Suggested helper shape:

- `_output_mentions_index_lock(result: CommandResult) -> bool`
  - True when combined stdout/stderr mentions `index.lock` or the canonical `Unable to create` lock error.
- `_git_index_lock_path(runner: Runner, cwd: str | None = None) -> Path | None`
  - Prefer `git rev-parse --absolute-git-dir`.
  - Return `<git-dir>/index.lock`.
  - If the probe fails, return `None` (fail closed).
- `_index_lock_is_held(runner: Runner, lock_path: Path, *, cwd: str | None = None) -> bool`
  - **Replace** the original system-wide `_has_live_git_process(runner)` design.
  - Return `True` only when evidence shows the **target** lock is in active use.
  - **Primary signal — lock-holder detection** (preferred):
    - On Linux: walk `/proc/<pid>/fd/*`, resolve symlinks, return `True` when any resolved path equals `lock_path.resolve()` (exclude the current process PID).
    - On Darwin (and as a portable fallback when `/proc` is unavailable): run `lsof` on `str(lock_path)` via the existing `Runner`; return `True` when output lists a PID other than the current process holding the file.
    - If the lock file does not exist, return `False`.
  - **Secondary signal — repo-scoped git process** (only when lock-holder detection is inconclusive because the probe errored, not when it cleanly found zero holders):
    - Resolve `git_dir = lock_path.parent` (or re-use `_git_index_lock_path` parent).
    - Enumerate candidate `git` PIDs via stdlib `/proc/<pid>/cmdline` on Linux or `Runner.run(["ps", "-eo", "pid,args"])` / `pgrep -lf git` as fallback.
    - Return `True` only when a candidate's argv or environment indicates it is operating on **this** repo, e.g.:
      - `--git-dir=<git_dir>` (exact or normalized path match), or
      - `--work-tree=` / cwd within the same work tree as `cwd` / `git_dir`, or
      - argv contains the resolved `git_dir` or repo-root path.
    - **Do not** treat bare `git` in another cwd as blocking.
  - **Probe failure policy:** If lock-holder detection errors **and** repo-scoped enumeration errors, return `True` (fail closed). If lock-holder detection cleanly reports no holders, return `False` even when unrelated `git` processes exist elsewhere.
- `_try_remove_stale_index_lock(runner: Runner, *, cwd: str | None = None) -> tuple[bool, str]`
  - Resolve `lock_path` via `_git_index_lock_path`.
  - Return `(False, diagnostic)` when `lock_path` is `None` (git-dir probe failure).
  - Return `(False, diagnostic)` when the lock is absent, non-empty, stat fails, or unlink fails.
  - Call `_index_lock_is_held(runner, lock_path, cwd=cwd)` before unlink; refuse when held.
  - Return `(True, diagnostic)` only after removing a 0-byte lock that was not held.
  - Include the lock path in diagnostics.
  - Diagnostic examples for refused removal:
    - `larch: stale .git/index.lock not removed: lock held by process; lock=<path>`
    - `larch: stale .git/index.lock not removed: repo-scoped git process detected; lock=<path>`
    - `larch: stale .git/index.lock not removed: non-empty lock; lock=<path>`
    - `larch: stale .git/index.lock not removed: <reason>; lock=<path>`

Add a generic retry wrapper:

- `_run_with_stale_index_lock_retry(runner, argv, *, cwd=None) -> CommandResult`
  - Run `_run(runner, argv, cwd=cwd)`.
  - If success, return it.
  - If failure does not mention `index.lock` and no lock path exists, return unchanged.
  - Call `_try_remove_stale_index_lock(runner, cwd=cwd)`.
  - If removal succeeds, rerun the same argv once.
  - Do not retry more than once.
  - Append a short stderr note on removal and retry.
  - If removal is refused, return the original result with an added diagnostic such as:

Wire the wrapper into staging and commit entrypoints:

- `add(...)` — wrap the `git add` argv; pass `cwd` through to retry/removal helpers.
- `add_pathspec_file(...)` — wrap the `git add --pathspec-from-file=...` argv.
- `commit(...)` — wrap only the final `git commit` argv.
- `commit_with_trailer(...)` — wrap only the final `git commit --file ...` argv; do **not** wrap `git interpret-trailers`.

Update `commit_main(...)`:

- After argv parse, before staging:
  - Run `_try_remove_stale_index_lock(proc)` once as a preemptive sweep (uses repo-scoped / lock-holder probe).
  - If removal succeeds, emit a short stderr note; continue.
  - If removal is refused but a lock path exists, do not abort yet; let the wrapped staging/commit path surface diagnostics.
- Keep existing staging order:
  - `add_pathspec_file(...)` when `--pathspec-from-file` is set.
  - `add(proc, *args.files)` when file args are present.
- Both staging calls inherit the guarded retry via the updated `add` / `add_pathspec_file` helpers.
- Call `commit_with_trailer(...)` for the commit phase (inherits commit retry).
- Preserve `--only`, `--pathspec-from-file`, `--pathspec-file-nul`, and explicit file argv semantics.

Optional but low-cost: route `stage_main(...)` through the wrapped `add(...)` only (no behavior change beyond lock handling).

### UPDATED: python/review_and_fix.py

Remove duplicate raw staging that bypasses `git.py` lock policy in **all three** commit helpers.

In `_stage_and_commit_round(...)`:

- Delete the standalone `_run(["git", "add", "--pathspec-from-file", ...])` call.
- Keep writing `coder-stage-paths.txt`.
- Invoke only:
  - `cli.py git commit --only --pathspec-from-file <stage_file> -m <msg>`
- `commit_main()` owns staging through wrapped `add_pathspec_file()`.
- Change return type from `str` to `RoundCommitResult(sha: str = "", failure_reason: str = "")`.
- On success, return `RoundCommitResult(sha=_git_head())`.
- On commit failure, inspect `commit.stdout + commit.stderr`:
  - If output contains `larch: stale .git/index.lock not removed`, return `RoundCommitResult(failure_reason="stale-index-lock")`.
  - Otherwise return `RoundCommitResult()` (empty sha, no failure_reason).
- Also treat staging-phase lock diagnostics surfaced by `commit_main` the same way.
- Preserve existing `coder-commit.log` append.

**`apply_findings_with_coder` call-site contract (blocking fix):** After `RoundCommitResult` migration, the call site must **not** treat the return value as a string. Dataclass instances are always truthy, so `if not commit_sha` would always be false and skip generic cleanup/fallback.

Replace the current pattern:

```python
commit_sha = _stage_and_commit_round(round_num, round_dir)
if not commit_sha:
    ...
result = CoderResult(0, tool, "applied", ..., commit_sha)
```

With explicit field access:

round_commit = _stage_and_commit_round(round_num, round_dir)
if round_commit.failure_reason == "stale-index-lock":
    result = CoderResult(2, tool, "stale-index-lock", str(tool_log), scrubbed_count, scrub_count, 0)
    _write_env(result_file, _coder_env(result))
    return result
if not round_commit.sha:
    if not _cleanup_failed_coder_attempt(round_dir):
        result = CoderResult(2, tool, "failed", str(tool_log), scrubbed_count, scrub_count, 0)
        _write_env(result_file, _coder_env(result))
        return result
    commit_failed = True
    continue
result = CoderResult(0, tool, "applied", str(tool_log), scrubbed_count, scrub_count, 0, round_commit.sha)

Branch order matters: stale-lock first (distinct status, no cleanup/fallback), then empty-sha generic failure (existing cleanup/fallback), then success with `round_commit.sha` passed into `CoderResult`.

In `commit_fixes(...)` when `--stage-all`:

- Keep building `review-fix-stage-paths.txt`.
- Delete the standalone `_run(["git", "add", "--pathspec-from-file", ...])` call and its early-return error branch.
  - `cli.py git commit --only --pathspec-from-file <stage_file> -m <message>`
- `commit_main()` owns staging.

In `_commit_lint_fix_delta_paths(...)`:

- Keep writing `lint-fix-stage-paths.txt`.
- Preserve existing empty-path early return and `lint-fix-commit.log` append.
- Invoke only `cli.py git commit --only --pathspec-from-file <stage_file> -m <msg>`.

Thread the distinct stale-lock cause through the review coder surface **without** changing `STALL_REASON`:

- Add `RoundCommitResult` dataclass near `_stage_and_commit_round`.
- `_stage_and_commit_round` returns `RoundCommitResult` as above.

In Step 5 result mapping (`step5_main` stall-reason block):

- Keep `RoundResult.status == "coder-failed"` for `coder.rc == 2`.
- **Do not** map `result.coder.status == "stale-index-lock"` to a distinct `STALL_REASON`.
- Keep the existing stall-reason branch:
  - `submodule-violation` when `result.coder.status == "submodule-violation"`
  - otherwise `coder-failed`
- `CODER_STATUS` in the Step 5 envelope already carries `result.coder.status`, so stale-lock stalls emit `STALL_REASON=coder-failed` **and** `CODER_STATUS=stale-index-lock`.
- This preserves `stall_recovery.py` evidence classification and `RESUME_HINT=step5-review` for Step 5 stalls without modifying `stall_recovery.py`.

In `apply_findings_main(...)` (`apply_findings` CLI):

- Keep `REVIEW_AND_FIX_STATUS=coder-failed`.
- Emit `CODER_STATUS=stale-index-lock` through the existing field when the coder returns that status.

### UPDATED: python/test_git.py

Add focused regression tests for commit and staging paths.

Existing commit-wrapper tests (keep; update live-process monkeypatch target):

- `test_commit_removes_zero_byte_index_lock_and_retries`
- `test_commit_refuses_non_empty_index_lock`
- `test_commit_refuses_zero_byte_index_lock_when_lock_held` (rename from `when_git_process_seen`; monkeypatch `_index_lock_is_held` to return `True`)
- `test_commit_retries_only_once`

Add repo-scoped probe coverage:

- `test_try_remove_stale_index_lock_ignores_unrelated_git_process`
  - Real temp git repo with 0-byte `.git/index.lock`.
  - Monkeypatch `_index_lock_is_held` to return `False` (simulating unrelated git elsewhere not blocking).
  - Assert `_try_remove_stale_index_lock` returns `(True, …)` and lock is removed.
- `test_try_remove_stale_index_lock_refuses_when_lock_held`
  - Monkeypatch `_index_lock_is_held` to return `True`.
  - Assert removal refused and diagnostic mentions `lock=`.
- `test_index_lock_is_held_false_when_lock_absent`
  - No lock file; assert `_index_lock_is_held` returns `False`.

Add staging coverage:

- `test_add_removes_zero_byte_index_lock_and_retries`
  - Real temp git repo with a tracked change.
  - Create `.git/index.lock` as 0 bytes.
  - Monkeypatch `_index_lock_is_held` to return `False`.
  - Call `git.add(proc, "file")`.
  - Assert rc is 0, lock is gone, file is staged.

- `test_add_pathspec_file_removes_zero_byte_index_lock_and_retries`
  - Same setup with a pathspec file.
  - Call `git.add_pathspec_file(proc, pathspec)`.
  - Assert rc is 0 and lock is gone.

Add Step-5-shaped CLI coverage:

- `test_commit_main_pathspec_from_file_removes_zero_byte_index_lock_and_retries`
  - Real temp git repo with a modified tracked file.
  - Write a pathspec file listing that file.
  - Create 0-byte `.git/index.lock`.
  - Run `git.commit_main(["--only", "--pathspec-from-file", str(pathspec), "-m", "msg"])`.
  - Assert rc is 0, lock is gone, commit landed.
  - Assert staging ran (file committed) without needing a separate raw `git add` caller.

- `test_commit_main_pathspec_from_file_refuses_non_empty_index_lock`
  - Non-empty lock, `_index_lock_is_held` returns `False`.
  - Assert rc is non-zero, lock remains, stderr contains `stale .git/index.lock` and lock path.

Keep existing `test_commit_pathspec_file_nul_only_*` tests passing unchanged.

### UPDATED: python/test_review_and_fix.py

Add Step 5 / stall-recovery surface coverage.

Coder status tests:

- `test_apply_findings_with_coder_stale_index_lock_returns_distinct_status`
  - Monkeypatch `_stage_and_commit_round` to return `RoundCommitResult(failure_reason="stale-index-lock")`.
  - Assert `CODER_STATUS=stale-index-lock` and `REVIEW_AND_FIX_STATUS=coder-failed`.
  - Assert cleanup/fallback is **not** invoked (no `_cleanup_failed_coder_attempt` call).

- `test_step5_stall_reason_stays_coder_failed_for_stale_index_lock`
  - Assert `STEP5_REVIEW_STATUS=stall`, `STALL_REASON=coder-failed`, and `CODER_STATUS=stale-index-lock`.
  - Assert `STALL_REASON` is **not** `stale-index-lock`.

RoundCommitResult call-site regression:

- `test_apply_findings_with_coder_generic_commit_failure_cleans_and_falls_through`
  - Monkeypatch `_stage_and_commit_round` to return `RoundCommitResult(sha="")` (empty sha, no failure_reason).
  - Assert `if not round_commit.sha` path runs: `_cleanup_failed_coder_attempt` is called and flow falls through to `main-agent-required` on generic commit failure.
  - Guards against the dataclass-truthiness bug where `if not commit_sha` would skip cleanup when `commit_sha` is a `RoundCommitResult` instance.

Migrate `RoundCommitResult` monkeypatches:

- Update `test_apply_findings_with_coder_commit_failure_cleans_and_falls_through`:
  - Change the `_stage_and_commit_round` monkeypatch to return `RoundCommitResult(sha="")` instead of `""`.
  - Assert `apply_findings_with_coder` still cleans and falls through to `main-agent-required` on generic commit failure.
- Scan for any other `_stage_and_commit_round` monkeypatches returning bare `str` and update them to `RoundCommitResult`.

Update `commit_fixes` contract tests for deduped staging:

- Adjust `test_commit_fixes_stage_all_uses_review_delta_pathspec` so it expects **no** standalone `["git", "add", ...]` call.
- Assert exactly one commit invocation with `--only --pathspec-from-file`.

Add stale-lock regression on the Step 18a path:

- `test_commit_fixes_stage_all_removes_zero_byte_index_lock_and_retries`
  - Real temp git repo under `IMPLEMENT_TMPDIR` layout (reuse existing `_tmp_impl` helpers).
  - Monkeypatch `_collect_review_fix_stage_paths` to return one changed path.
  - Monkeypatch `git._index_lock_is_held` (or the review_and_fix import path) to return `False`.
  - Run `commit_fixes(["--stage-all", "--message", "fix review"])`.
  - Assert rc is 0, `COMMITTED=true`, lock is gone.

Add Step-5-round coverage for removed duplicate add:

- `test_stage_and_commit_round_uses_commit_main_staging_only`
  - Monkeypatch/spy `_run` or record subprocess argv.
  - Call `_stage_and_commit_round` with a round dir containing stage paths.
  - Assert no raw `git add` invocation.
  - Assert one `cli.py git commit --only --pathspec-from-file ...` invocation.
  - Assert return value is `RoundCommitResult` with non-empty `sha` on success.

Add lint-fix commit coverage for deduped staging and stale-lock handling:

- Update `test_commit_lint_fix_delta_paths_uses_pathspec_file`:
  - Expect **no** standalone `["git", "add", ...]` call.
  - Assert exactly one `cli.py git commit --only --pathspec-from-file ...` invocation.
- Add `test_commit_lint_fix_delta_paths_uses_commit_main_staging_only`:
  - Spy `_run` argv.
  - Call `_commit_lint_fix_delta_paths` with non-empty paths.
- Add `test_commit_lint_fix_delta_paths_removes_zero_byte_index_lock_and_retries`:
  - Call `_commit_lint_fix_delta_paths(...)`.
  - Assert non-empty sha returned, lock is gone.

### UPDATED: scripts/test-implement-structure.sh

Align the structural harness with commit_main-only staging.

- Remove the `require()` that pins raw `("git", "add", "--pathspec-from-file")` in `python/review_and_fix.py` for `commit-fixes` pathspec staging.
- Add `forbid('python/review_and_fix.py', '"git", "add", "--pathspec-from-file"', 'staging owned by commit_main only')` so all three deduped commit helpers (`_stage_and_commit_round`, `commit_fixes --stage-all`, `_commit_lint_fix_delta_paths`) cannot reintroduce standalone pre-add calls.
- Keep the existing `require()` for `"--only",\n            "--pathspec-from-file"` pathspec-only commit argv.
- Keep the existing `forbid()` on `"git", "add", "-A"`.

## Edge cases

- **Non-empty lock:** Do not remove it; surface diagnostic with lock path.
- **Lock held by process:** Refuse removal when `_index_lock_is_held` reports a holder for **this** `index.lock`.
- **Unrelated git process:** A `git` process in another repository must **not** block removal of a 0-byte stale lock in the target repo.
- **Repo-scoped git process:** Only git PIDs tied to the target `git_dir` / work tree block removal when lock-holder detection is inconclusive.
- **Process probe failure:** When both lock-holder and repo-scoped probes error, fail closed and keep the lock.
- **Lock disappears before unlink:** Treat as not removed; return original failure with diagnostic.
- **Retry fails after removal:** Return the retry result; do not loop.
- **Worktrees:** Resolve lock via `git rev-parse --absolute-git-dir`, not repo-root `/.git`; repo-scoped argv matching must use resolved absolute paths.
- **Pathspec commits:** Retry the exact same argv so `--only`, `--pathspec-from-file`, and `--pathspec-file-nul` keep current semantics.
- **Duplicate staging removed:** `_stage_and_commit_round`, `commit_fixes --stage-all`, and `_commit_lint_fix_delta_paths` must not pre-add; `commit_main()` is the sole staging owner for those paths.
- **Lint-fix commit path:** Post-round lint-fix commits must not bypass `commit_main` staging; otherwise a stale lock still surfaces as `lint-fix-commit-failed`.
- **Staging failure before commit:** Lock cleanup must run on `git add` failures, not only on `git commit` failures.
- **Mid-transaction lock:** Preemptive sweep handles pre-existing stale locks; wrapped add/commit handles locks encountered at invocation time.
- **RoundCommitResult truthiness:** `RoundCommitResult` instances are always truthy in Python; `apply_findings_with_coder` must branch on `.failure_reason` and `.sha`, never `if not round_commit`.
- **RoundCommitResult migration:** Any test monkeypatching `_stage_and_commit_round` must return `RoundCommitResult`, not bare `str`, so generic failure routing stays correct.
- **Stall reason vs coder status:** Stale-lock refusal sets `CODER_STATUS=stale-index-lock` but leaves `STALL_REASON=coder-failed` so Step 18a stall recovery keeps the existing `step5-review` resume contract without `stall_recovery.py` changes.

## Failure modes

- Lock-holder detection may be unavailable on some platforms; repo-scoped fallback and fail-closed behavior must not regress to system-wide git blocking.
- A conservative lock-holder probe may refuse cleanup when another process legitimately holds `index.lock`. That is safer than deleting an active lock. Diagnostics must name the lock path and reason (`lock held by process` vs `repo-scoped git process detected`).
- Removing duplicate raw `git add` calls changes call order slightly (single staged add inside `commit_main`). Behavior should remain equivalent because `commit_main` already re-staged the same pathspec file.
- If `scripts/test-implement-structure.sh` is not updated alongside the dedup, `make lint` fails on the stale `require()` for raw `git add` even when runtime behavior is correct.
- Introducing a novel `STALL_REASON=stale-index-lock` would break Step 18a resume classification (`unrecoverable` / `RESUME_HINT=none`) because `stall_recovery.py` is out of scope; distinct stale-lock signaling must stay on `CODER_STATUS` and commit stderr only.
- **`RoundCommitResult` without call-site update:** If `_stage_and_commit_round` returns a dataclass but `apply_findings_with_coder` still assigns it to `commit_sha` and tests `if not commit_sha`, generic commit failures skip cleanup/fallback and may pass a non-`str` into `CoderResult.commit_sha`.

## Testing strategy

Run targeted tests first:

- `python3 -m pytest python/test_git.py -k "index_lock or commit_pathspec or add_pathspec or lock_is_held or unrelated_git"`
- `python3 -m pytest python/test_review_and_fix.py -k "stale_index_lock or commit_failure or step5_stall or commit_fixes_stage_all or lint_fix_delta_paths or round_commit"`

Then run required repo checks:

- `make test-implement-structure`
- `make py-lint`
- `make py-test`
- `make lint`

## Acceptance

- A stale 0-byte `.git/index.lock` with no lock holder is removed and the failing git argv is retried **once** across every `commit_main`-routed path: the Step 5 review round commit (`_stage_and_commit_round`), the stall-recovery commit (`commit_fixes --stage-all`), and the post-round lint-fix commit (`_commit_lint_fix_delta_paths`).
- Cleanup runs on `git add` (staging) failures, not only on `git commit` failures, via wrapped `add()` / `add_pathspec_file()` and the `commit_main()` preemptive sweep.
- A non-empty lock, a lock held by a process, or a probe failure is **never** removed; a distinct `larch: stale .git/index.lock not removed: <reason>; lock=<path>` diagnostic naming the lock path is emitted to stderr.
- An unrelated `git` process running in a different repository does **not** block removal of a 0-byte stale lock in the target repo; only a holder of **this** `index.lock` or a repo-scoped git process blocks it.
- When stale-lock cleanup is refused on the Step 5 review coder path, the coder surface emits `CODER_STATUS=stale-index-lock` while the Step 5 envelope keeps `STALL_REASON=coder-failed`, preserving `stall_recovery.py` classification and `RESUME_HINT=step5-review`.
- `python/implement_dispatch.py` and `python/stall_recovery.py` are unchanged.
- `_stage_and_commit_round` returns `RoundCommitResult`; `apply_findings_with_coder` branches on `.failure_reason` then `.sha` (no dataclass-truthiness regression in generic commit-failure cleanup/fallback).
- `scripts/test-implement-structure.sh` forbids standalone `"git", "add", "--pathspec-from-file"` in `python/review_and_fix.py` and the new `test_git.py` / `test_review_and_fix.py` regression tests pass.
- `make test-implement-structure`, `make py-lint`, `make py-test`, and `make lint` all pass.

review_status: complete
rounds_completed: 5
diff_added: 412
diff_deleted: 58
mechanical_churn: false
diff_lines: 470
