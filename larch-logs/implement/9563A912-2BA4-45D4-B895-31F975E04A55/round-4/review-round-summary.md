# Review Round 4

- Mode: `diff`
- 4 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Step 0 dirty-tree resume loses fork metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `step-0-bootstrap.sh --mode resume` does not restore `FORKED_TARGET`, `UPSTREAM_REPO`, or related fork metadata when the thin resume fence omits original argv/env exports. A forked `/implement` resume can be treated as non-forked, causing wrong `gh --repo`/tracking behavior and inconsistent rebase or plan-fetch state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Deleted structure/rebase harness pins weaken regression coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Regression pins were deleted rather than re-pointed to the new wrapper/reference locations. This weakens CI detection for rebase checkpoint routing, phantom-probe coverage, NEVER pins, post-dispatch bail mirrors, background-monitor bans, and Step 18a stall layers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Wrapperized SKILL fences still contain extra export commands
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Modified `/implement` Bash fences still include standalone `export` commands before wrapper calls. The new fence-shape harness expects only allowed prelude plus one repo-script invocation, so `make test-implement-fence-shape` / related harnesses can fail and the branch does not satisfy its acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Step 0 dirty-tree resume loses preflight plan context
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The dirty-tree Step 0 resume fence no longer forwards `PREFLIGHT_TMPDIR`, `TARGET_ISSUE`, or equivalent original bootstrap context. After cleanup and resume, `copy-plan` can fail because it cannot find `$PREFLIGHT_TMPDIR/plan-from-issue.txt`, or the resume tail sentinel can fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


