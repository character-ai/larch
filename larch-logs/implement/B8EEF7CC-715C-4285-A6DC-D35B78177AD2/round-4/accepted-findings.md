### FINDING_1: flush_logs_post writes final report before manifest done
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-runlog-manifest-output.txt
- **Severity**: important
- **Concern**: `python/run_logs.py` finalizes post-merge logs in the wrong order: it renders final-summary/ledger output before persisting `status=done` and `pr_number`. This violates the fail-closed bash/plan ordering and is not pinned by an ordering test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-runlog-manifest-output.txt: Address the concern above.


### FINDING_10: Python Step 8+ cutover lacks structural harness pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The SKILL Python branch can rot without CI because no structural harness pins the `LARCH_SHIP_PR_IMPL` selector, `python/ship.py` invocation, and JSON routing contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: OOS checkpoint finalize-state fallback is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/oos-disposition-checkpoint.sh` fallback behavior for fork/repo flags from `finalize-state.sh` is untested, risking Python-path misreads when `ship-pr-state.sh` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: write-final-report finalize-state fallback is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `write-final-report.sh` fallback for PR keys from `finalize-state.sh` is untested, so Python runs that only write finalize-state could show missing PR fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: ci_monitor routing changes lack tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `ci_monitor.monitor()` routing branches lack updated tests for local-unfixable, transient bail, and related monitor outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Step 18 restore can overwrite authoritative Python finalize-state
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Step 18 restore rebuilds `finalize-state.sh` from stale `ship-pr-state.sh`, while Python ship writes authoritative PR state only to `finalize-state.sh`. This can erase merged PR fields before teardown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_15: uncaught Python exceptions bypass JSON result contract
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` can traceback instead of emitting the promised JSON+exit-code result, breaking Step 8+ routing and potentially leaking raw exception text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_18: Python SKILL exit routing still depends on bash state file
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` says Python routing should use JSON, but adjacent Step 8+ blocks still read `ship-pr-state.sh` for exit 3/4/6/OOS routing and transient phase counters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-handback-output.txt: Address the concern above.


### FINDING_19: CI goto_rebase conflict handoff is not ported
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python CI `goto_rebase` uses rebase behavior that can auto-handle or generically stall conflicts instead of bash’s keep-on-conflict exit-4 orchestrator handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_2: postmerge finalize-state clears merged PR state
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-runlog-manifest-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` writes `PR_CLOSED` from postmerge cleanup/verify outcome instead of preserving merge-time PR state. A successfully merged PR with failed postmerge verification can be classified as not closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-runlog-manifest-output.txt: Address the concern above.


### FINDING_20: Python CI-fix refresh still requires ship-pr-state.sh
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Step 10 still calls `refresh-run-logs.sh --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"`, which can silently skip on the Python path if that state file is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


### FINDING_22: postmerge manifest recovery is weaker than bash
- **Reviewer(s)**: dyn-runlog-manifest-output.txt
- **Severity**: important
- **Concern**: Python postmerge recovery only loads or locally recovers the manifest, while bash gates through `larch-log.sh init`, partial status tagging, and recovery failure handling before writing done.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlog-manifest-output.txt: Address the concern above.


### FINDING_24: Python postmerge cleanup does not match local-cleanup.sh
- **Reviewer(s)**: dyn-teardown-stall-output.txt
- **Severity**: important
- **Concern**: `python/finalize.py` uses a simplified `git switch` / `pull` / `branch -D` cleanup and misses bash fetch, transient retry, orphan log-flush reset, and verify-main-equivalent behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-stall-output.txt: Address the concern above.


### FINDING_25: stalled stash failures are hidden
- **Reviewer(s)**: dyn-teardown-stall-output.txt
- **Severity**: important
- **Concern**: `auto_stash_stalled_changes()` can return an empty stash ref on failure without surfacing that dirty worktree state to teardown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-stall-output.txt: Address the concern above.


### FINDING_26: stalled stash labels lack timestamp disambiguation
- **Reviewer(s)**: dyn-teardown-stall-output.txt
- **Severity**: latent
- **Concern**: Python stalled stash messages omit the UTC timestamp used by bash to keep stash lookup unambiguous across concurrent runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-stall-output.txt: Address the concern above.


### FINDING_27: Branch A rename allows missing issue state
- **Reviewer(s)**: dyn-teardown-stall-output.txt
- **Severity**: important
- **Concern**: Python Branch A rename treats missing or empty issue state as rename-eligible, while bash only renames when the issue state is explicitly open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-stall-output.txt: Address the concern above.


### FINDING_28: postbump rebase and force-push gates are collapsed
- **Reviewer(s)**: dyn-teardown-stall-output.txt
- **Severity**: important
- **Concern**: Python postbump drives a combined rebase+push path instead of bash’s separate rebase, remote-branch check, and force-push gate, causing divergent failure and lease semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-stall-output.txt: Address the concern above.


### FINDING_3: postmerge warning conditions become hard stalls
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-teardown-stall-output.txt
- **Severity**: important
- **Concern**: `python/finalize.py` maps partial cleanup or unexpected main verification to `Outcome.STALLED`, while bash emits warnings and exits successfully after merge. Python `/implement` can therefore stall after a completed merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-teardown-stall-output.txt: Address the concern above.


### FINDING_30: cleanup target verification derives prefix from wrong cwd
- **Reviewer(s)**: dyn-teardown-stall-output.txt
- **Severity**: latent
- **Concern**: `_cleanup_target_ok()` derives its default basename prefix from `Path.cwd()` rather than the repo root used for teardown, risking false accepts/refusals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-stall-output.txt: Address the concern above.


### FINDING_33: rebase_then_evaluate defers evaluation
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: `ci_monitor.monitor()` treats `rebase_then_evaluate` like plain rebase and does not immediately call failure evaluation, unlike bash’s back-to-back behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.


### FINDING_34: CI loop caps reset across Python re-invocation
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: Python CI loop counters are function-local and reset on every `run_ship()` invocation, so transient re-entry can bypass bash-equivalent iteration/rebase/fix caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.


### FINDING_36: workflow dependency comment is stale
- **Reviewer(s)**: dyn-workflow-harness-output.txt
- **Severity**: latent
- **Concern**: `.github/workflows/ci.yaml` still says the harness job installs only PyYAML, but the requirements now include pytest for Python parity harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-harness-output.txt: Address the concern above.


### FINDING_37: merge parity harness can silently skip all tests
- **Reviewer(s)**: dyn-workflow-harness-output.txt
- **Severity**: important
- **Concern**: `test-merge-parity` can exit green if every test is skipped due to the module-level bash skip marker, undermining the fail-closed parity gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-harness-output.txt: Address the concern above.


### FINDING_4: CI handback needs_user_reason tokens are unstable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: Python CI handbacks can emit composite or non-canonical `needs_user_reason` strings, especially for local-unfixable and related CI-fix reasons. The SKILL routing expects stable tokens, so autonomous CI-fix or user handback can dispatch incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-ci-handback-output.txt: Address the concern above.


### FINDING_6: refresh skip-code parity may regress lenient bash behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `REFRESH_SKIP_COMMIT_FAILED` is missing from the Python merge-ok skip set, so Python ship may stall on a run-log commit failure that bash treats as lenient.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: test_ship acceptance coverage is too thin for Python cutover
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` lacks most plan-required driver scenarios, including transient, stall, forked/repo-unavailable, goto-rebase, CI cap, merge-false, and integration handback paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: finalize unit tests miss plan-listed branches
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize.py` does not cover several plan-listed postbump, postmerge, teardown, guard, and skip branches, leaving finalize behavior without targeted regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_9: finalize bash parity harness is smoke-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` does not provide side-by-side bash parity coverage comparable to merge parity, so finalize.py can drift from `implement-finalize.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


