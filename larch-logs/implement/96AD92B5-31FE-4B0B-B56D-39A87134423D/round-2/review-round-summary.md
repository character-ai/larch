# Review Round 2

- Mode: `diff`
- 3 accepted, 13 rejected (13 exonerated)

## Accepted Findings

### FINDING_12: Research collect lacks exported tmpdir for paired-PID writer
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `collect-agent-results` depends on an exported session tmpdir for paired-PID writing, but research fences omit `export RESEARCH_TMPDIR`, so the writer can fail open and leave the monitor unable to signal an orphaned background process.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: Breadcrumb monitor test docs omit required test mode
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-breadcrumb-monitor.md` documents `LARCH_BM_TEST_TIMEOUT_SECONDS` without also documenting the required `LARCH_BM_TEST_MODE=1`, so contributors following that doc alone get the production timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: Nested Family B parent env unset is not tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Removing `unset LARCH_PAIRED_PID_FILE` before nested Family B calls such as `ci-wait` would not fail CI, allowing a nested writer to clobber the parent PID file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


