### FINDING_1: Missing ship driver acceptance coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-handback-output.txt, dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` covers only a small mocked subset of the planned driver acceptance matrix, leaving draft/forked/repo-unavailable/transient/CI handback/goto-rebase/cap-exhaustion/stall/JSON-routing regressions unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-handback-output.txt, dyn-ci-harness-output.txt: Address the concern above.


### FINDING_13: Merge stalls do not mark STALL_TRACKING
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Merge failure exits write finalize state without `STALL_TRACKING=true`, so Step 18 can treat a failed merge as completed tracking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: Postmerge failure state can imply success
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `run_postmerge_phase` writes `PR_CLOSED=true` before failed postmerge handling updates stall flags, causing finalize/cleanup logic to misclassify the run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_15: Post-merge manifest recovery omits bash init/recovery metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Python post-merge manifest recovery lacks bash-parity init and `recovery_reason` handling, so mid-run recovery can lose issue-scoped metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_17: Stalled sentinel writer allows newline injection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_write_stalled_sentinel` writes `KEY=value` lines without the newline/carriage-return validation used by `write_finalize_state`, allowing spoofed sentinel fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_19: Catch-all Exception path leaks details and misclassifies failures
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `main()` catches bare `Exception`, maps programming/library failures to `STALLED`, and emits `str(exc)` after one redact pass, risking leaked details and wrong Step 18 routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_20: Final-report comment refresh failures are suppressed
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Post-PR `write_final_report_comment` errors are swallowed, so public tracking summaries can remain stale while the driver returns OK.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_22: Pre-PR log refresh commit failure can be skipped
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `REFRESH_SKIP_COMMIT_FAILED` is treated as merge-ok, so a pre-push log batch commit failure can let PR creation proceed without committed run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_23: Python Step 8+ invoke/routing remains bash-state-oriented
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-handback-output.txt, dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` documents the Python selector but still routes important Step 8+ paths through bash concepts like `ship-pr.sh`, `ship-pr-state.sh`, `PHASE`, and bash retry counters instead of Python JSON fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-handback-output.txt, dyn-ci-harness-output.txt: Address the concern above.


### FINDING_24: postbump ignores log-refresh skip results
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `finalize.postbump` ignores `flush_logs_pre` skip/failure outcomes, so Step 8b rebase/push can proceed without surfacing missing log refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_26: finalize.py unit coverage is incomplete versus the plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` lacks planned postbump/postmerge/teardown matrix cases, leaving session guard, cleanup, and branch rename behavior under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_28: run_ship lacks idempotent phase re-entry
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Reinvoking Python `run_ship()` after handbacks starts from checks/postbump instead of resuming near the current PR/CI/merge phase, and can unnecessarily rerun rebase/push work against an open PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.


### FINDING_29: CI loop counters reset on every Python process
- **Reviewer(s)**: dyn-state-machine-output.txt, dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: CI iteration/rebase/fix/transient counters are local variables reset on each `run_ship()` invocation, so Step 8+ reinvokes can exceed bash’s session-wide caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt, dyn-ci-handback-output.txt: Address the concern above.


### FINDING_30: ci-local-unfixable maps to the wrong outcome
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python maps `local-unfixable` CI fixes to `STALLED`/exit 4, while bash routes that failure class to `NEEDS_USER_INPUT`/exit 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_32: Python rebase-conflict handoff lacks bash-compatible fields
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python rebase conflicts surface only as JSON detail, without `CONFLICT_FILES`/handoff fields required by the documented conflict-resolution procedure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_33: Python CLI omits expected session/tmpdir guard inputs
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Bash passes expected session id and tmpdir basename prefix, but Python CLI/SKILL invocation does not, weakening Step 18 teardown/finalize guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_34: OOS gate uses origin/main even for forked runs
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python OOS pre-PR git-log matching always compares against `origin/main`, while forked runs should mirror upstream-base logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_35: Forked postmerge verification pulls the wrong remote
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `finalize.postmerge` always runs `git pull --ff-only origin main`, which can verify the wrong default branch tip for forked Python runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_37: Postmerge run-log finalization is blocked by postmerge cleanup failures
- **Reviewer(s)**: dyn-runlog-integrity-output.txt
- **Severity**: important
- **Concern**: `run_postmerge_phase` skips `flush_logs_post` when `finalize.postmerge` returns non-OK, whereas bash still finalizes run logs for merged PRs even if local cleanup/verify emits warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-integrity-output.txt: Address the concern above.


### FINDING_38: PLAN_FILE does not default to tmpdir plan.txt on Python path
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: Python CI monitor receives a plan only when `PLAN_FILE` is exported, unlike bash’s `$IMPLEMENT_TMPDIR/plan.txt` fallback, weakening CI fixer context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.


### FINDING_42: Teardown cleanup target validation is non-canonical
- **Reviewer(s)**: dyn-teardown-state-output.txt
- **Severity**: important
- **Concern**: `_cleanup_target_ok` uses string-prefix and basename heuristics before `shutil.rmtree`, allowing crafted `IMPLEMENT_TMPDIR` paths with `..` or symlinks to target directories outside allowed session roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-state-output.txt: Address the concern above.


### FINDING_43: Python driver accepts unconstrained tmpdir for state writes
- **Reviewer(s)**: dyn-teardown-state-output.txt
- **Severity**: important
- **Concern**: Python accepts `IMPLEMENT_TMPDIR`/`--tmpdir` without upfront confinement, then writes finalize state, sentinels, and journals under that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-state-output.txt: Address the concern above.


### FINDING_48: Merge bash-parity tests do not skip when bash is absent
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `python/test_merge_bash_parity.py` skips when `merge-pr.sh` is absent but not when `bash` is absent, unlike other bash-parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.


### FINDING_5: Subprocess cwd handling is inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_ship` runs some phases with `repo_root` and others with `cwd=None`, so PR/CI/merge stages can execute in the wrong directory when invoked outside the repo root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: OOS git-log gate uses the wrong cwd
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_oos_gate` runs `git log` with `cwd=None`, which can miss inline-triage commits or falsely require OOS filing when the CLI cwd is not the repository root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: pr_number is stored redundantly with inconsistent types
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `run_logs.py` records `pr_number` in multiple manifest locations with different types, inviting downstream parser mistakes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


