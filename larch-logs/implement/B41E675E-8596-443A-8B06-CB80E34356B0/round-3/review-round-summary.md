# Review Round 3

- Mode: `diff`
- 5 accepted, 7 rejected (6 exonerated)

## Accepted Findings

### FINDING_10: Compose-fail harness leaks inherited breadcrumb stream
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` uses `LARCH_QUIET_DISABLE=1` without clearing inherited `LARCH_BREADCRUMB_STREAM`, causing the compose-fail test to fail when run inside an `/implement` session with stream env set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Flush-warning coverage no longer asserts user-visible channel
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The flush-warning stdout breadcrumb assertion was replaced by a stub stderr assertion, so warning coverage can stay green if warnings move back to breadcrumb-only channels and stop appearing where users or execution issue tracking expect them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: run-external-agent stderr routing lacks regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-run-external-agent.sh` does not assert that wrapper diagnostics stay on stderr, so a future change could put diagnostics back on stdout and reintroduce JSONL bleed into `codex.events.jsonl`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Telemetry sidecar filenames drift from plan literals
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-fix-loop.sh` and `skills/review-and-fix/scripts/review-and-fix.sh` use `codex.telemetry.sidecar` and `coder-codex.telemetry.sidecar` rather than the plan’s `codex.sidecar` and `coder-codex.sidecar`, so operators or tooling following the plan may not find parse-diagnostic files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Breadcrumb round-entry test accepts missing breadcrumb
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` allows the round-entry breadcrumb assertion to pass when the breadcrumb is absent, so quiet/breadcrumb routing regressions can stop being caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


