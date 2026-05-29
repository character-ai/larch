# Review Round 1

- Mode: `diff`
- 11 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_10: missing absent-target cache-dir prune harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The `absent-target-fills-eight` case does not actually exercise a missing `ACTUAL_VERSION` cache dir at prune time, leaving regressions in absent-target retention/count behavior uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_11: stale keepalive cleanup behavior is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no test that stale session dirs containing `.larch-keepalive` are deleted, so a keepalive skip could return without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: TMP_REMOVED cleanup contract is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `/tmp` pattern scanning and `TMP_REMOVED=1` behavior are not covered by `make test-cleanup`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: misleading absent-target test name
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The case name `absent-target-fills-eight` implies absent-target behavior is covered even though the test creates the target cache dir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: cleanup silently disables deletion if date fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `date +%s` fails and `NOW=0`, cleanup can report success while silently disabling age-based deletions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_20: age-only cleanup can delete long-idle live sessions
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Cleanup can delete session dirs idle longer than retention even if Claude is still running, breaking long-paused design or idle implement sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_21: unstamped legacy cache dirs are evicted too aggressively
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Stamp-presence-first ordering can delete multiple still-in-use unstamped legacy cache versions during the first post-change prune.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: cleanup swallows find errors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Suppressed `find` failures can under-read session activity, leaving stale parent mtimes and causing active sessions to be misclassified stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: stamp-write failure with existing cache dir is untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The prune harness lacks coverage for failed `.larch-installed-at` writes when the target cache dir already exists, so regressions could prune the just-installed version despite warn-only stamp failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: cleanup skill dropped explicit NEVER guidance
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/SKILL.md` dropped the NEVER section instead of replacing the old singleton-abort rule with age-based guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_8: stale upgrade-larch test comment
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: A test comment still references newer-than-stable pruning removed by the Stage A redesign, creating misleading maintenance context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


