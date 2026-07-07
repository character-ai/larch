# Review Round 1

- Mode: `diff`
- 1 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: deleted bgjob harness script breaks Makefile targets
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-bgjob-proc
- **Severity**: major
- **Concern**: `make test-bgjob` and `test-harnesses-4` still invoke `bash scripts/test-bgjob.sh`, but that script is absent from the branch, so the targets fail immediately and the real-process bgjob coverage never runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Restore scripts/test-bgjob.sh and keep Makefile shard wiring
  - From codex-specialist-edge-cases: Add scripts/test-bgjob.sh or revert the Makefile wiring until the harness lands.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Add the new harness script in this chunk, or keep the target on the existing pytest command until the script lands
  - From dyn-dyn-bgjob-proc: Restore scripts/test-bgjob.sh and keep it in `test-harnesses-4`; do not leave Makefile targets pointing at a deleted script.


