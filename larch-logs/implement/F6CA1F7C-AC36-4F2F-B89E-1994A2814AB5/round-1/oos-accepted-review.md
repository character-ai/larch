### OOS_1: [OUT_OF_SCOPE] Makefile shard 13 references a nonexistent strip-body target
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-cutover-fidelity-output.txt, dyn-kv-routing-contracts-output.txt
- **Severity**: important
- **Concern**: `test-harnesses-13` depends on `test-record-plan-review-round-timing-strip-body`, but the defined target is `test-record-plan-review-round-timing`. This can break `make test-harnesses-13` and `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rename dependency to test-record-plan-review-round-timing
  - From cursor-specialist-edge-cases-output.txt: Restore test-record-plan-review-round-timing in the test-harnesses-13 prerequisite list.
  - From codex-specialist-edge-cases-output.txt: Replace with test-record-plan-review-round-timing and clean up accidental PHONY concatenation
  - From cursor-specialist-testing-output.txt: Restore test-check-main-sync and test-record-plan-review-round-timing names; re-run test-harness-shards-coverage.sh.
  - From dyn-cutover-fidelity-output.txt: Rename the shard entry to `test-record-plan-review-round-timing`, or add a matching recipe if a separate strip-body harness was intended.
  - From dyn-kv-routing-contracts-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] linting docs reference a removed make target
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-cutover-fidelity-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` still points operators at removed `make test-extract-plan-scope-paths` coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Retarget doc row to make py-test / python/test_issue_wire.py.
  - From dyn-cutover-fidelity-output.txt: Remove or retarget the row to `make py-test` / `python/test_issue_wire.py` scope-path tests.


