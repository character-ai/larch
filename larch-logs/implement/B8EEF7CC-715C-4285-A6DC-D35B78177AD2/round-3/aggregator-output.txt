### FINDING_1: Missing ship driver acceptance coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-handback-output.txt, dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` covers only a small mocked subset of the planned driver acceptance matrix, leaving draft/forked/repo-unavailable/transient/CI handback/goto-rebase/cap-exhaustion/stall/JSON-routing regressions unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-handback-output.txt, dyn-ci-harness-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Finalize bash-parity coverage is only smoke coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` is labeled/treated as bash parity but does not invoke `scripts/implement-finalize.sh`, so postbump/postmerge/teardown behavior can drift from bash while tests stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-harness-output.txt: Address the concern above.

### FINDING_3: run_ship is a monolithic orchestrator
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/ship.py::run_ship` contains a large nested orchestration flow with repeated state writes, making phase changes and tests brittle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: RunContext has duplicate fields for the same concepts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `RunContext` duplicates branch/issue/fork fields with inconsistent fallbacks, so partial updates can make call sites diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_7: [OUT_OF_SCOPE] flush_logs_post writes final report before manifest done and lacks ordering tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt, dyn-runlog-integrity-output.txt, dyn-teardown-state-output.txt, dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` can render final reports/ledgers before setting manifest `status=done`/`pr_number`, violating the planned fail-closed ordering; existing tests assert final state but not call order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt, dyn-runlog-integrity-output.txt, dyn-teardown-state-output.txt, dyn-ci-harness-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Legacy exit aliases can confuse outcome routing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: Legacy `EXIT_BAIL`/`EXIT_STALL` constants duplicate newer outcome-map values and are easy to import or reason about incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-bash-parity-output.txt: Address the concern above.

### FINDING_9: pr_number is stored redundantly with inconsistent types
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `run_logs.py` records `pr_number` in multiple manifest locations with different types, inviting downstream parser mistakes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: finalize-state writes are repeated across bail paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Repeated `write_finalize_state` blocks in `ship.py` make it easy to miss fields like `STALL_STEP` on one branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_11: Availability probes ignore RunContext session fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `codex_present`/`cursor_present` are re-probed from env instead of loaded session context, so resume routing can diverge from Step 0 availability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] RecordingRunner helpers are duplicated across tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Multiple test modules duplicate `RecordingRunner`, risking helper drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_16: CI wiring for merge-parity harness is unclear
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The plan mentioned CI wiring for merge parity, but the diff appears to rely on Makefile/shard changes without clear `ci.yaml` traceability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_17: Stalled sentinel writer allows newline injection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_write_stalled_sentinel` writes `KEY=value` lines without the newline/carriage-return validation used by `write_finalize_state`, allowing spoofed sentinel fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: JSON stdout redaction is incomplete
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: stdout JSON redaction skips `pr_url` and only partially handles free-text fields, allowing tokenized/internal URLs or sensitive strings to reach orchestrator output.
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

### FINDING_21: [OUT_OF_SCOPE] Report subprocesses inherit the full environment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_report_subprocess_env` forwards the full parent environment to report helpers, so child logging could expose tokens or other secrets.
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

### FINDING_25: [OUT_OF_SCOPE] OOS checkpoint can use the wrong RUN_ID
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: OOS checkpoint fallback derives `RUN_ID` from session id rather than parent issue/finalize state, which can miss `oos-issues.ndjson` on rediscovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_26: finalize.py unit coverage is incomplete versus the plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` lacks planned postbump/postmerge/teardown matrix cases, leaving session guard, cleanup, and branch rename behavior under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_27: 8-pre-ship probe text is bash-only
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The 8-pre-ship SKILL probe still assumes bash state-file prerequisites, which can confuse or misroute Python-path operators.
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

### FINDING_31: Python CI-fix log refresh still depends on ship-pr-state.sh
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Autonomous CI-fix steps read `FAILED_RUN_ID`/`REPO` and refresh logs through `ship-pr-state.sh`, which is absent on the Python path, so post-fix log batches can be skipped.
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

### FINDING_36: [OUT_OF_SCOPE] Default bash implementation remains unchanged
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: The default `LARCH_SHIP_PR_IMPL=bash` is unchanged; many Python-path risks apply only when operators opt into Python.
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

### FINDING_39: [OUT_OF_SCOPE] Plan references rebase_and_rebump but code exposes rebase_and_push
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: nit
- **Concern**: The plan names `rebase.rebase_and_rebump` for CI goto-rebase, while the current module exposes and uses `rebase_and_push`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] transient_rerun_attempted behavior is bash-adjacent and reasonable
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: nit
- **Concern**: The in-process transient rerun wiring for `no-changes` appears reasonable and bash-adjacent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] CI-fix fork flags still depend on ship-pr-state.sh in one path
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: latent
- **Concern**: OOS checkpoint fallback to finalize state helps Python runs, but autonomous CI-fix step 2 still reads fork flags only from `ship-pr-state.sh`.
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

### FINDING_44: Post-merge sentinel writer allows newline injection
- **Reviewer(s)**: dyn-teardown-state-output.txt
- **Severity**: latent
- **Concern**: `run_postmerge_phase` writes `MERGE_RESULT={ctx.merge_result}` without newline/carriage-return validation, unlike finalize-state serialization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-state-output.txt: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] Bash teardown shares string-prefix cleanup weakness
- **Reviewer(s)**: dyn-teardown-state-output.txt
- **Severity**: latent
- **Concern**: Bash teardown uses a similar non-canonical cleanup-target pattern; Python inherits the weakness but adds direct `shutil.rmtree`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-state-output.txt: Address the concern above.

### FINDING_46: [OUT_OF_SCOPE] Cleanup allowlist omits XDG_CACHE_HOME
- **Reviewer(s)**: dyn-teardown-state-output.txt
- **Severity**: nit
- **Concern**: `finalize.py` omits `XDG_CACHE_HOME` from the cache cleanup allowlist, causing fail-safe cleanup skips for non-default cache layouts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-state-output.txt: Address the concern above.

### FINDING_47: [OUT_OF_SCOPE] Positive hardening was observed
- **Reviewer(s)**: dyn-teardown-state-output.txt
- **Severity**: nit
- **Concern**: `write_finalize_state()` newline rejection, JSON stdout redaction, and tracking issue title redaction are positive hardening measures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-state-output.txt: Address the concern above.

### FINDING_48: Merge bash-parity tests do not skip when bash is absent
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `python/test_merge_bash_parity.py` skips when `merge-pr.sh` is absent but not when `bash` is absent, unlike other bash-parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.

### FINDING_49: [OUT_OF_SCOPE] docs/linting omits test-merge-parity
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` documents `make test-merge-pr` but not the new `make test-merge-parity` target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.
