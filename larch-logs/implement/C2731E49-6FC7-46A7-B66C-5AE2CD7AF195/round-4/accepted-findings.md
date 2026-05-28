### FINDING_11: Add argv and non-emergency Preflight coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `--emergency`/`--draft` mutex and non-emergency no-plan exit behavior are grep-only assertions rather than executable control-flow tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Rename misleading bypass-log test header
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: A test section header says the bypass log is replayed even though the assertion is about no replay, which can mislead maintainers during future emergency/resume edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Only consume bypass log after successful append
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If both `append-tool-failure.sh` and fallback `append-execution-issue.sh` fail, bootstrap still writes the consumed sentinel, losing the bypass log permanently without an execution-issues entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Add executable emergency Preflight regression coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Emergency Preflight bypass behavior is prompt-only and currently pinned mostly by static grep tests, so regressions in bypass, warning, empty-body, audit-refuse, exit, or log behavior could ship without executable coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Structurally pin emergency bootstrap argument forwarding
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests do not sufficiently pin `_ib_emergency` expansion in both initial bootstrap and resume-plan-tail call paths, so one path could stop forwarding emergency state until runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Surface tracking metadata post failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `post_tracking_metadata` uses `|| true` on resume paths, allowing `gh` upsert failures to continue silently without `Emergency: true` in `larch:metadata`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: Cover clean emergency run without bypass log
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: There is no bootstrap harness case for an emergency run with a valid plan and no bypass log, so regressions that add spurious warnings or drop emergency metadata on clean emergency runs may be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


