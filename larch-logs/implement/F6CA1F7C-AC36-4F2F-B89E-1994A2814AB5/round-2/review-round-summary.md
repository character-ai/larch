# Review Round 2

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Shard 13 references a non-existent Make target
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Shard 13 depends on `test-record-plan-review-round-timing-strip-body`, which does not exist. `make test-harnesses-13` and `make lint` fail before the shard can run. The intended `test-record-plan-review-round-timing` coverage is also lost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rename prerequisite to test-record-plan-review-round-timing
  - From codex-specialist-correctness-output.txt: Split the shard dependency back to test-record-plan-review-round-timing and remove only test-plan-block-strip-body
  - From cursor-specialist-edge-cases-output.txt: Restore prerequisite name to test-record-plan-review-round-timing; remove only test-plan-block-strip-body.
  - From cursor-specialist-edge-cases-output.txt: Re-add test-record-plan-review-round-timing to shard 13 (or another shard).
  - From cursor-specialist-testing-output.txt: Restore shard prerequisite to test-record-plan-review-round-timing matching the recipe at Makefile:297-298.
  - From codex-specialist-testing-output.txt: Restore test-record-plan-review-round-timing as its own dependency and remove only test-plan-block-strip-body, then run shard coverage.


### FINDING_10: Quiet diagnostics can disappear before Python quiet initialization
- **Reviewer(s)**: dyn-quiet-fd-parity-output.txt
- **Severity**: important
- **Concern**: `diagnostic()` writes to fd 4 whenever inherited quiet environment variables are present, even when this Python process did not initialize quiet mode. Early `plan-block strip-body` errors can be lost or written to an unintended fd before callers capture them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-parity-output.txt: Mirror `BreadcrumbWriter.emit`: only write fd 4 when `_self_initialized_quiet` is true; otherwise append to `LARCH_QUIET_LOG_FILE` when set, else fall back to `sys.stderr`. Add a subprocess test with inherited `LARCH_QUIET_ACTIVE` that asserts usage/diagnostic text is visible on stderr or the quiet log, not lost.
  - From dyn-quiet-fd-parity-output.txt: Either call `quiet_init(argv0="plan-block-strip-body.sh")` at entry (matching deleted bash `larch_quiet_init` at script start) for diagnostic paths only, or fix `diagnostic()` as above so pre-init errors route safely without changing the intentional “no quiet_init on success stdout” contract.


### FINDING_2: `.PHONY` lists the wrong `test-check-main-sync` target
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `.PHONY` lists `test-check-main-sync-strip-body`, but the recipe is `test-check-main-sync`. Shard coverage reports the real target as missing from `.PHONY`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rename .PHONY token to test-check-main-sync
  - From codex-specialist-correctness-output.txt: also correct the PHONY splice at Makefile:6
  - From cursor-specialist-edge-cases-output.txt: Fix the .PHONY token to test-check-main-sync.
  - From cursor-specialist-testing-output.txt: Fix .PHONY token to test-check-main-sync (drop erroneous -strip-body suffix).


