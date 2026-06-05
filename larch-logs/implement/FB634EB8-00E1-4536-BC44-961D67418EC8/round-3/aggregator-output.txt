### FINDING_1: Finalize bash parity subprocess coverage is too narrow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The rewritten finalize bash-parity module has only one narrow subprocess comparison, leaving cleanup, verify-main/admin suffix, postbump force-push, teardown rename, checkpoint corrupt, and other high-value implement-finalize.sh KV/status paths able to drift while pytest stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Finalize parity fail-closed gate can pass with all tests skipped
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The finalize parity gate checks collected test names but not actual execution/skip counts, so a broad skipif or script-exists skip could leave zero bash parity tests executed while the gate still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: FinalizeResult omits branch deletion outcome
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_local_cleanup` computes `branch_deleted`, but `FinalizeResult` does not expose it, so Python parity/tests/operators cannot compare or diagnose `BRANCH_DELETED` outcomes emitted by bash postmerge cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Postbump preflight runs twice on the happy path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `postbump_preflight` is invoked both from ship and postbump, duplicating git probes and risking future side effects running twice instead of having one authoritative preflight site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: CI-fix and finalize rebase/push logic is duplicated and can diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Postbump and CI-fix paths duplicate no-push rebase / rebase+force-push behavior across inline Python and shell helpers, so fetch retry, conflict abort, fork-base, lease, and dirty-tree handling can drift between code paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Plan-listed finalize unit branches are missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test_finalize.py` lacks RecordingRunner coverage for many planned postbump, postmerge, verify-main, and teardown branches, so branch guards, force-push gates, rebase-failed paths, delete-failure success, checkpoint corrupt, admin suffix, and teardown rename regressions may ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: finalize_postmerge_logs alias contract is unclear and inconsistently routed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `finalize_postmerge_logs` is currently only a passthrough to `flush_logs_post`, while callers such as merge route directly to `flush_logs_post`; if the alias later becomes the centralized recovery/manifest/report contract, behavior can diverge or ordering assumptions can be obscured.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: Postbump preflight failure result omits bash auxiliary KVs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The ship-side postbump preflight failure path constructs a `FinalizeResult` without auxiliary fields such as `rebase_status`, `force_push_status`, and `log_write_status`, producing inconsistent state envelopes for branch-mismatch stalls and parity assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: ship-pr-state writer preserves stale keys and lacks newline sanitization
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_write_ship_state` merges existing unknown keys and writes unsanitized KV values, allowing stale or tampered bash-consumed keys — and newline-containing values — to survive or split the state file and skew resume behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: Manifest recovery omits issue_number
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Manifest recovery does not repopulate `issue_number` from context even when `ISSUE_NUMBER` is set, unlike bash teardown recovery, so recovered partial manifests can cause token/report tooling to skip the run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: postbump_preflight fails to fall back when current-branch detection returns None
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `postbump_preflight` only falls back to the target branch when rev-parse stdout is empty, not when branch detection succeeds but returns `None`, causing false branch-mismatch stalls despite target branch context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: postbump exception path uses non-bash STATUS tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Exceptions during postbump set `FinalizeResult.status` to generic outcome strings such as transient/stalled rather than bash `STATUS` tokens like `rebase-failed` or `push-failed`, causing ship state phase drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: recovery_ok=false flush gating lacks tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not force manifest recovery/write failure and assert that `flush_logs_pre`, `flush_logs_post`, and `finalize_postmerge_logs` skip report/commit/done side effects with `REFRESH_SKIP_RECOVERY_FAILED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: Planned ship postmerge/postbump integration tests are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: `test_ship.py` lacks planned coverage for postmerge flush gating, sentinel negatives, postbump layering/order, and `phase=done` guard behavior, leaving the fixed `pr_closed` flush/sentinel paths and postbump refresh/preflight ordering unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-runlog-recovery-output.txt: Add tests that monkeypatch `finalize_postmerge_logs` and assert it is not called when `ctx.pr_closed=False` for skipped-OK postmerge outcomes, plus a positive test when `pr_closed=True` and merge succeeded.

### FINDING_15: Merge parity lacks a fail-closed gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no merge parity gate analogous to finalize parity, so missing `merge-pr.sh` or all-skipped merge parity tests can still leave `py-test` green despite the Part B requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: CI-fix push/pending lifecycle coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: CI-fix tests omit plain push, lease-failure mapping, and full pending-rebase monitor lifecycle set/clear propagation, so non-rebase force-push mistakes or pending-state regressions can slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_17: Timing harness shard may become unbalanced
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Three timing harnesses were added to `test-harnesses-16`, which may push shard 16 beyond CI rebalance targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: Teardown log flush is not best-effort
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_teardown_log_flush` can abort on manifest errors before stash/sentinel work, and failed log commits are silent, diverging from best-effort bash teardown behavior and risking lost run-log flush diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: CI_FIX_REBASE_PENDING can be set without bash-equivalent verify/push criteria
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ci-rebase-state-output.txt
- **Severity**: important
- **Concern**: Python can persist pending rebase retry state after local verify only, or even when `origin/<branch>` cannot be resolved, whereas bash sets pending only after post-rebase verify gates pass and the actual force-push attempt fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-ci-rebase-state-output.txt: Return `pending=False` (and surface a stall/error) when `expected_remote_oid` is missing or remote-check fails; only set `pending=True` after verify succeeded and the force-push attempt itself failed.

### FINDING_20: Pending retry mishandles missing local remote-tracking ref
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pending retry returns `pending=True` when the local `origin/<branch>` ref is missing without attempting force-push recovery, potentially causing repeated pending retries instead of lease/no-op recovery when `ls-remote` confirms the remote branch exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: Run-log commit gate only refuses main/master literals
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_larch_log_commit` lacks the bash default-branch refusal beyond literal `main`/`master`, so repos with another default branch may commit teardown or pre-push refresh logs from the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: CI-monitor ignores failed run-log refresh skips before force-push
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: After CI-fix rebase, `stage_and_push` suppresses or ignores `flush_logs_pre` recovery skip signals, allowing the path to force-push with no breadcrumb or execution-issues record for failed log refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Inspect the `RefreshSkip` return (same pattern as `ship.py` postbump refresh at `498-500`); on `REFRESH_SKIP_RECOVERY_FAILED`, emit a warning breadcrumb and optionally append to `execution-issues.md`, then continue or stall per bash `refresh-run-logs.sh || true` semantics.

### FINDING_23: Ship pre-rebase recovery skip lacks warning breadcrumb
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: latent
- **Concern**: Pre-rebase `flush_logs_pre` recovery failure is allowed to proceed without a warning, unlike the postbump path, leaving no audit trail before `rebase_and_push`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: When `pre_rebase.skipped` and `pre_rebase.reason == run_logs.REFRESH_SKIP_RECOVERY_FAILED`, call `_breadcrumb("warning", ...)` (and/or record a Warnings execution issue) before continuing, matching postbump refresh behavior.

### FINDING_24: flush_logs_pre can raise instead of returning RefreshSkip
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: important
- **Concern**: `flush_logs_pre` checks `recovery_ok` early but later `update_manifest` or manifest writes can still raise `ShipError`/`OSError`, so callers that only handle `RefreshSkip` can abort instead of degrading warning-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Wrap the `update_manifest` / commit tail in `flush_logs_pre` with try/except for `ShipError` and `OSError`, mapping failures to `RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)` or `REFRESH_SKIP_COMMIT_FAILED` as appropriate.

### FINDING_25: Resumed pending CI rebase can skip failed-job verification
- **Reviewer(s)**: dyn-ci-rebase-state-output.txt
- **Severity**: important
- **Concern**: On process restart with `ci_fix_rebase_pending=true`, `evaluate_failure` passes an empty `ClassifiedJobs` fallback, so `stage_and_push` can skip post-rebase local verify and force-push without reloading failed-job state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-rebase-state-output.txt: Before the pending `run_ci_fix` call, reload and classify failed jobs from `run_id` (or read the persisted phase TSV from `IMPLEMENT_TMPDIR`, matching bash’s `_resolve_effective_failed_jobs_tsv`) and pass that `classified` into `stage_and_push`; add a restart test that asserts verify runs before any `--force-with-lease` push.

### FINDING_26: Pending push failures incorrectly consume fix attempts
- **Reviewer(s)**: dyn-ci-rebase-state-output.txt
- **Severity**: important
- **Concern**: When a verified rebase fix fails force-push but remains pending, Python returns `did_fixing=True`, causing `run_ship` to increment `fix_attempts` on push-only retry cycles that bash would not count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-rebase-state-output.txt: Treat pending push-only retries as non-counting: return `did_fixing=False` for the `waterfall-failed` + `ci_fix_rebase_pending` branch, or increment `fix_attempts` only when `fix.status == "pushed"`.

### FINDING_27: Implement/design timing round idempotency contracts diverge
- **Reviewer(s)**: dyn-timing-ledger-output.txt, dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: Implement round timing short-circuits on any existing `(skill, step, round)` row while design fingerprints the full tuple and allows superseding rows, so implement cannot correct premature or partial ledger rows and the shared round schema has inconsistent semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Unify idempotency across both helpers (either round-keyed last-writer-wins matching `timing-report.sh`’s `emit_round_array` dedupe, or full-tuple skip with explicit supersede on changed `end_s`/counts) and document the single contract in `scripts/timing-ledger.md`; align harnesses so both workflows test deferred re-emit with updated duration.
  - From dyn-shell-portability-output.txt: Align the implement pre-check with the design fingerprint (round + step + start + end + accepted + rejected), or drop the coarse pre-check and rely only on the post-write verification already at lines 118–122.

### FINDING_28: lint-fix main-agent timing emits too early
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: latent
- **Concern**: The `lint-fix-main-agent-required` Step 5 branch both persists `round-start-s` and emits an in-loop timing row before stalling, so the later deferred orchestrator emit becomes a no-op and duration is frozen before prompt-side work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Treat `lint-fix-main-agent-required` like MAV/CMA: persist `round-start-s`, skip in-loop `_emit_implement_round_timing_row`, and let the orchestrator stall path emit exactly once after any prompt-side work; add a loop-level harness asserting no in-loop ledger row and a single deferred row with the extended `end_s`.

### FINDING_29: Step 5 resume split mark makes round attribution fragile
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: latent
- **Concern**: Step 5 resume emits a second timing mark for `--starting-round > 1`, splitting one logical review session into multiple mark intervals and making deferred round attribution dependent on fragile ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Either emit the Step 5 mark only once per session (update/resume sentinel instead of a second mark) or centralize round recording so all rows for a logical Step 5 session share one mark window; document the ordering invariant beside `review-implement-step5-loop.md` / `run-step5-review.md`.

### FINDING_30: round_start_s leaks as a global shell variable
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: `run_implement_loop` assigns `round_start_s` without declaring it local, leaking a global into the sourced parent shell and risking collisions with helpers or repeated Step 5 entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Add `round_start_s` to the existing `local` block at line 187–192 (or declare `local round_start_s` immediately before the `while` loop).

### FINDING_31: design-route accepts empty session IDs
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: `validate_session_id_arg` rejects embedded newlines but allows an explicitly empty `--session-id`, allowing blank session IDs to flow into run-params and timing artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Reject empty values in `validate_session_id_arg` (mirror `validate_plain_scalar`) or add `[[ -n "$SESSION_ID_ARG" ]] || fail '--session-id must be non-empty'` before calling it.

### OOS_1: README stale about CI_FIX_REBASE_PENDING support
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-ci-rebase-state-output.txt
- **Severity**: latent
- **Concern**: `python/README.md` still says `CI_FIX_REBASE_PENDING` is deliberately omitted even though this branch implements pending-rebase behavior, misleading Phase 7 operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-ci-rebase-state-output.txt: Address the concern above.

### OOS_2: CI monitor test docstring contradicts pending-rebase behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: A `test_monitor_push_failed_stalls` docstring can mislead contributors about which push-failure paths persist `CI_FIX_REBASE_PENDING` versus stall immediately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_3: Branch bundles unrelated large changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Large non-finalize changes are bundled with finalize parity work, making bisecting finalize regressions harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_4: merge post_flush recovery failure is intentionally hard-error
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: nit
- **Concern**: `_post_flush` maps skipped post-flush to `MERGE_RESULT_ERROR`, but the reviewer notes this is intentional for `merge_pr(..., post_flush=True)` and production ship uses a warning-only path elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.

### OOS_5: flush_logs_post done-before-report behavior matches bash
- **Reviewer(s)**: dyn-runlog-recovery-output.txt
- **Severity**: nit
- **Concern**: `flush_logs_post` writes `status=done` before report generation, but the reviewer classifies this as bash parity rather than a new divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-recovery-output.txt: Address the concern above.

### OOS_6: CI_FIX_REBASE_PENDING_HEAD is serialized but not used
- **Reviewer(s)**: dyn-ci-rebase-state-output.txt
- **Severity**: nit
- **Concern**: `CI_FIX_REBASE_PENDING_HEAD` is written but not read on hydration/resume, and the related test name overstates HEAD mismatch coverage; reviewer marks it harmless versus bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-rebase-state-output.txt: Address the concern above.

### OOS_7: Implement timing-report invocations lack symmetric env isolation note
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: nit
- **Concern**: Implement-side timing helpers do not mirror the design helper’s explicit unsetting of sibling tmpdir variables everywhere, though risk is low because ledgers/tmpdirs are usually pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.

### OOS_8: design-pause temp directory cleanup is not interrupt-safe
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: nit
- **Concern**: `render_fresh_timing_report_for_pause_publish` lacks trap/ERR cleanup for its `mktemp -d` directory on interruption, though failure paths clean up and the reviewer frames it as a minor best-effort gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.

### OOS_9: Shell-portability risk assessment for finalize parity work
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes the Python finalize parity work does not modify the main finalize shell scripts, and shell-portability risk is concentrated in the timing-ledger/helper surface, which otherwise appears Bash 3.2-compatible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.
