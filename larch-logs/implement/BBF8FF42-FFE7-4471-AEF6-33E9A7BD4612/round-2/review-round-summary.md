# Review Round 2

- Mode: `diff`
- 3 accepted, 5 rejected (3 neutral)

## Accepted Findings

### FINDING_12: release-prepare treats GitHub API failures as unmatched commits
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` swallows `gh api`/jq failures and treats commits as having no PR association, so transient GitHub, auth, rate-limit, or parsing failures can be misclassified as `unmatched-commits`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: Step 5 review detail root/argv mismatch can omit live round data
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-schema-compat-output.txt
- **Severity**: important
- **Concern**: Step 5 reporting can use different round roots for the liveness header and detailed parity table, causing the header to show an active tmpdir round while the appended table reads only flushed `larch-logs` rounds. Existing tests mock the detail renderer and do not verify subprocess argv, rounds-root selection, or ledger flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-schema-compat-output.txt: Address the concern above.


### FINDING_6: Between-round Step 5 state reports completed rounds as active
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_current_round_dir` falls back to the highest settled round when no unsettled round exists, so inter-round gaps can display a completed review round as still in progress with stale reviewer counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


