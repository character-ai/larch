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



### FINDING_18: Python SKILL exit routing still depends on bash state file
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` says Python routing should use JSON, but adjacent Step 8+ blocks still read `ship-pr-state.sh` for exit 3/4/6/OOS routing and transient phase counters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt, dyn-ci-handback-output.txt: Address the concern above.



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



### FINDING_28: postbump rebase and force-push gates are collapsed
- **Reviewer(s)**: dyn-teardown-stall-output.txt
- **Severity**: important
- **Concern**: Python postbump drives a combined rebase+push path instead of bash’s separate rebase, remote-branch check, and force-push gate, causing divergent failure and lease semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-stall-output.txt: Address the concern above.



### FINDING_34: CI loop caps reset across Python re-invocation
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: Python CI loop counters are function-local and reset on every `run_ship()` invocation, so transient re-entry can bypass bash-equivalent iteration/rebase/fix caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.



### FINDING_37: merge parity harness can silently skip all tests
- **Reviewer(s)**: dyn-workflow-harness-output.txt
- **Severity**: important
- **Concern**: `test-merge-parity` can exit green if every test is skipped due to the module-level bash skip marker, undermining the fail-closed parity gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-harness-output.txt: Address the concern above.



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



