# Review Round 3

- Mode: `diff`
- 1 accepted, 7 rejected (4 neutral)

## Accepted Findings

### FINDING_3: Negotiation-round docs and tests out of sync on Darwin serial-lock coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-caller-cutover-output.txt
- **Severity**: important
- **Concern**: `docs/linting.md` still describes an offline bash harness that pins the Darwin serial-lock spawn guard, but the retargeted pytest surface (`make test-run-negotiation-round` → `python/test_agents.py -k negotiation_round`) does not assert serial-lock acquire/release around Codex/Cursor spawns. Lock-ordering regressions in `run_negotiation_round()` would pass CI while breaking concurrent-auth parity on Darwin. The linting row also cites the wrong harness shard (`test-harnesses-8` vs Makefile `test-harnesses-6`) and describes deleted `scripts/test-run-negotiation-round.sh` behavior rather than current pytest coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add pytest assertions for serial-lock ordering on both negotiation tools, or update docs to match actual coverage.
  - From cursor-specialist-testing-output.txt: Add tests monkeypatching external_serial_lock_acquire/release_after with LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin and assert both tools lock immediately before subprocess spawn.
  - From dyn-caller-cutover-output.txt: Rewrite the row for the pytest `-k negotiation_round` coverage (exit codes, `RESPONSE_FILE=`, serial-lock argv, temp-home cleanup) and fix the shard reference to `test-harnesses-6`; add a parallel row for `make test-check-reviewers` on `test-harnesses-4` if operators expect symmetry.


