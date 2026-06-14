# Review Round 3

- Mode: `diff`
- 17 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Loop preflight skips progress/done cleanup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Loop preflight failures skip progress/done cleanup that old run-step5-review wrote via EXIT trap for plan/codex/dynamic-archetypes errors. Empty plan or invalid CODEX_PRESENT on loop entry leaves progress/done uncleared while old shell trap still wrote done; Monitor/progress can show Step 5 stuck or behave differently vs bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Wrap loop-mode entry in try/finally: unlink progress/done on entry and always touch done in finally for loop mode including preflight ValueError paths.


### FINDING_12: Multi-round summaries do not accumulate exonerated/neutral counts
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Multi-round Step 5 summaries no longer accumulate `EXONERATED_COUNT` or `NEUTRAL_COUNT`. Round 1 with 3 exonerated findings followed by round 2 with 2 exonerated findings writes `exonerated_count=2` to `review-and-fix-summary.json` and passes 2 to the code-review tally flush, instead of the expected total 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Persist and read prior exonerated and neutral totals, or port the old prior-summary accumulation guard keyed by `rounds_completed < current_round`.


### FINDING_13: Missing findings.md no longer fail-closes convergence safety check
- **Reviewer(s)**: codex-generic-output.txt, dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: The convergence safety check silently skips the old fail-closed path when `findings.md` is missing. If review core reports accepted non-nit findings but the round artifact is absent, Step 5 can finish as `complete` or `no-changes` without scanning for Important findings, where the shell path treated that as `classifier-failed`. The Python port only runs convergence when `findings_path.is_file()`; if the file is absent it leaves `status` as `complete` or `no-changes`, so the Step 5 loop can emit `STEP5_REVIEW_STATUS=complete` instead of stalling with `classifier-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Port the previous behavior: for non-degraded convergence-candidate statuses, if non-nit accepted findings exist and `round-N/findings.md` is unreadable, set `classifier-failed` and return nonzero.
  - From dyn-step5-contract-output.txt: Mirror the shell contract: when `non_nit > 0` and `non_nit <= 5`, treat a missing or unreadable `round-N/findings.md` as a scan failure (`classifier-failed`, `exit_code=2`, loop terminal `stall` with `STALL_REASON=classifier-failed`). Add pytest for the missing-findings path.


### FINDING_15: Terminal complete path returns per-round RC instead of always 0
- **Reviewer(s)**: dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: On the normal completion path the loop emits `STEP5_REVIEW_STATUS=complete` but returns `result.rc` instead of always exiting `0`. The retired `review-implement-step5-loop.sh` routed on `IRF_LAST_ROUND_STATUS` and always `exit 0` for `complete` / `converged-small-changes` / `no-changes` / `in-scope-filtered-out`, ignoring the per-round subprocess exit code. Python can propagate a non-zero `result.rc` (for example when `review_core_capture` returns a non-zero RC while `REVIEW_CORE_STATUS` is `ok` / `zero-findings`) even though the final envelope says `complete`. That can make the background Step 5 task look failed while the orchestrator parses a success status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step5-contract-output.txt: On terminal `complete` (and other non-stall success envelopes that used `exit 0` in the shell loop), return `0` explicitly, matching `cap-hit` and `mav-resume-past-cap`. Keep non-zero RC only for stall and preflight-failure paths.


### FINDING_16: _important_present regex narrower than retired shell grep
- **Reviewer(s)**: dyn-step5-contract-output.txt
- **Severity**: important
- **Concern**: `_important_present` uses a narrower regex than the retired `important_findings_present` grep, which also matched `^- **Concern**: [Important]`. Findings that mark importance only in the Concern line (without `**Important**` in the heading) can be misclassified as non-important, triggering `converged-small-changes` and an early `STEP5_REVIEW_STATUS=complete` when the shell would have continued review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step5-contract-output.txt: Port the full bash pattern (heading, inline `**Important**`, and Concern-line `[Important]`) into `_important_present`, and add a pytest with a Concern-only Important marker.


### FINDING_19: skills/implement/SKILL.md lists retired contract siblings
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: The Extracted Script Registry still lists retired contract siblings `commit-review-fixes.md`, `write-rejected-findings.md`, and `check-review-changes.md`, but those files were deleted in this migration (`python/migrated-scripts.tsv:719-730`). The registry tells `/implement` readers to load contracts that no longer exist, while the live surfaces are `python/review_and_fix.py` and `python/cli.py review-and-fix {commit-fixes,write-rejected,check-changes}` via `step-6-entry.sh` / `step-16.sh`. `make lint-retired-scripts` does not catch this: bare basenames in `skills/implement/SKILL.md` are outside `skills/implement/scripts/`, so `python/migration_lint.py`'s `_dev_skill_markdown_bare_basename_ref` gate does not fire.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Replace the three retired `.md` entries with `python/review_and_fix.py` / CLI verb pins (or wrapper-only entries like `step-6-entry.md` / `step-16.md`), and extend `scripts/test-implement-structure.sh` or `python/migration_lint.py` so bare retired basenames in `skills/implement/SKILL.md` fail the stale-reference sweep.


### FINDING_2: apply_findings does not rehydrate session-env before coder dispatch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `apply_findings` parses `--session-env-path` but never rehydrates token/timing env before coder dispatch. `/review` fix-required calls apply-findings with `--session-env`; Codex/Cursor runs without parent `LARCH_TOKEN_SESSION_ID` and timing ledger, breaking nested token accounting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Mirror step5/commit_fixes: read session-env keys into `os.environ` before `apply_findings_with_coder`; add pytest for propagation.


### FINDING_20: test-implement-structure.sh lacks negative checks for deleted shell entrypoints
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: The plan's acceptance criteria required structural harnesses to assert deleted shell path absence (`run-step5-review.sh`, `review-and-fix.sh`, `check-review-changes.sh`, etc.), but `scripts/test-implement-structure.sh` has no negative checks for those paths (it only pins the new `larch-run.sh` → `python/cli.py review-and-fix step5` fences at lines 98–99 and 161–167). A future edit can reintroduce deleted shell entrypoints without `make lint` / harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Add explicit `[[ ! -e ... ]]` / `grep -Fq` negative assertions for every path in `python/migrated-scripts.tsv` tagged `#3678`, and fail if any tracked doc still cites them outside `larch-logs/` and the manifest.


### FINDING_21: review-core subprocess ban only in pytest, not make lint-codex-exec-auth
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: The plan called for lint coverage that blocks Step 5 from subprocessing `python/cli.py review core`. That guard exists only as a pytest source scan (`python/test_review_and_fix.py:144-149`), not in `make lint-codex-exec-auth` (which still scans only raw `codex exec` sites). A subprocess reintroduction would not be caught until a pytest shard runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Extend `python/lint_codex_exec_auth.py` (or a sibling migration lint) to reject `"review", "core"` / `cli.py review core` in `python/review_and_fix.py`, wire it into `make lint-codex-exec-auth`, and keep the existing pytest assertion as a backstop.


### FINDING_26: REVIEW_AND_FIX_REVIEW_CORE_SH lacks fail-closed executable guard
- **Reviewer(s)**: dyn-coder-dispatch-output.txt
- **Severity**: important
- **Concern**: The Python port dropped the shell's fail-closed guard on `REVIEW_AND_FIX_REVIEW_CORE_SH`. The deleted `review-and-fix.sh` required `[[ -x "$REVIEW_AND_FIX_REVIEW_CORE_SH" ]]` before running the override; `review_core_capture()` now runs whatever path is in the environment with no executable check, no plugin-root constraint, and no refusal when the path is missing or non-executable. Any process that can poison the implement environment (inherited shell env, wrapper scripts, or test harness leakage into a real run) can redirect Step 5 review-core execution to arbitrary code while the orchestrator still treats the result as a normal review round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-coder-dispatch-output.txt: Restore shell parity: refuse when the override is set but not a regular executable file under an allowed location; prefer the existing `review_core_impl` injection seam for tests instead of keeping a production env override, or gate the env override behind an explicit test-only flag.


### FINDING_27: _scrub_findings copies raw input when scrub output missing
- **Reviewer(s)**: dyn-coder-dispatch-output.txt
- **Severity**: important
- **Concern**: `_scrub_findings()` adds a new fallback that copies the raw accepted-findings file into `accepted-findings.scrubbed.md` whenever the scrub output is missing, even though the legacy shell refused coder dispatch on scrub failure and never copied unscrubbed input into the scrubbed path. If the scrub helper ever returns success without writing output (CLI bug, partial failure, or stdout/envelope mismatch), `scrub_ok` can stay true and `apply_findings_with_coder()` will dispatch Codex/Cursor against unscrubbed findings that may still reference submodule paths the scrubber was meant to remove.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-coder-dispatch-output.txt: Delete the `shutil.copyfile()` fallback; treat a missing scrub output as `SCRUB_OK=false` and fail closed exactly like the shell path, with a regression test that asserts unscrubbed input is never dispatched.


### FINDING_28: Cursor coder dispatch missing Darwin external serial lock
- **Reviewer(s)**: dyn-coder-dispatch-output.txt
- **Severity**: important
- **Concern**: Cursor coder dispatch no longer acquires the Darwin external serial lock before spawn. The deleted `review-and-fix.sh` called `external_serial_lock_acquire` / `external_serial_lock_release_after` around Cursor `run-external-agent`; the Python `_run_coder_cursor()` path invokes `python/cli.py agent run-external-agent` directly, and `run_external_agent_main()` does not take that lock (unlike `launch-codex-exec`, which does via `_run_external_agent_with_auth_retries`). Concurrent Codex/Cursor runs in the same user session can interleave auth state, temp homes, or workspace side effects across trust boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-coder-dispatch-output.txt: Route Cursor coder dispatch through the same authenticated/locked launcher path used elsewhere (or call `external_serial_lock_acquire("cursor")` around the `run-external-agent` invocation) so review-fix matches the shell and `docs/external-reviewers.md` serial-lock contract.


### FINDING_3: check-changes regression harness not ported from deleted shell
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted `test-check-review-changes.sh` covered 16 regression cases; pytest has only parse-error coverage. Step 6 check-changes can regress on untracked baselines, HEAD movement, strict mode, or probe failures without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port the deleted harness matrix into pytest with git worktree fixtures.


### FINDING_4: Post-round gates lack dedicated pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Post-round gates (lint-fix cap, bulk-skip cap, prune-skipped) lack dedicated tests despite plan requirement. Step 5 can stall early, continue incorrectly, or skip mechanical pruning without test detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest stubs for `_run_relevant_checks_captured` and `_run_lint_fix_loop` covering each gate branch.


### FINDING_5: Pre-scouted manifest forwarding untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Pre-scouted manifest forwarding has no pytest though plan required eligible/ineligible/MAV cases. Wrong `--pre-scouted-manifest` argv can change dynamic archetype behavior in review core.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert core argv in tests for eligible, ineligible, and mav-apply modes.


### FINDING_6: Step 5 preflight hard-fail gates beyond empty plan untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Step 5 preflight hard-fail gates beyond empty plan are untested per plan. Missing session-env, feature file, RUN_ID, or boolean presence keys can fail late or with wrong errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add negative preflight pytest cases for each gate with stall envelope assertions.


### FINDING_7: commit_fixes token and timing side effects not asserted
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `commit_fixes` token and timing side effects are implemented but not asserted in tests. Step 7 cost/timing reporting can regress silently when `commit_fixes` changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Capture `_run` argv and assert token mark and timing mark with `LARCH_TIMING_SKILL=implement`.


