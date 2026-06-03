### FINDING_1: Driver e2e acceptance scenarios are under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-gate-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` covers only a small happy-path subset. Required draft/forked/repo-unavailable/transient/stall/GOTO-rebase/cap/short-circuit/teardown and flush invariants can regress with green tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-gate-output.txt: Address the concern above.



### FINDING_2: Finalize parity and unit coverage are too shallow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `python/test_finalize_bash_parity.py` and finalize unit tests smoke-test only a narrow subset, leaving postbump, force-push gate, teardown/stall, session guard, and rename parity with `implement-finalize.sh` uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt: Address the concern above.



### FINDING_28: Python cutover docs and invocation routing are incomplete
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` still has bash-only state-file/routing assumptions, lacks a complete Python invoke contract, and omits env/argv needed for retries, log commits, and teardown guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-bash-parity-output.txt: Address the concern above.



### FINDING_37: Postmerge manifest recovery is weaker than bash
- **Reviewer(s)**: dyn-runlogs-output.txt
- **Severity**: important
- **Concern**: Python does not fully port bash’s missing-manifest recovery before setting done/reporting, so report generation can proceed after best-effort recovery where bash would fail closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-runlogs-output.txt: Address the concern above.



### FINDING_44: `rebase_then_evaluate` split changes CI loop accounting
- **Reviewer(s)**: dyn-ci-handback-output.txt
- **Severity**: important
- **Concern**: Python separates rebase from evaluate-failure handling, consuming extra CI-loop iterations and potentially adding another full poll wait compared with bash’s atomic handler.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-handback-output.txt: Address the concern above.



