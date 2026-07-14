## Goal
Implement issue #7267: [IMPLEMENTING] OOS disposition-gate parity.

## Implementation Plan
## Plan

Move all gate and checkpoint behavior assertions into pytest. Keep the Bash harness as narrow wrapper-delegation smoke coverage. Do not change runtime behavior or Makefile routing.

### UPDATED: python/tests/issue/test_file_oos.py

- Add shared fixtures for accepted-OOS files, run directories, state files, NDJSON batches, and controlled git command results.
- Port every behavioral assertion from `test-oos-disposition-gate.sh`.
- Cover gate skips, argument validation, file validation, empty inputs, security exclusions, legacy headings, URL counting, rejected markers, inline triage, invalid ranges, and exit codes.
- Preserve strict versus loose URL rules, off-host rejection, trailing text handling, URL unions, and the rule that one filed URL satisfies a multi-item batch.
- Cover checkpoint state and path resolution:
  - Fork and unavailable-repo skips.
  - Run-ID keyed NDJSON, stale run IDs, single fallback, and ambiguous fallback.
  - Missing NDJSON validation.
  - Gate failure logging and exit-code passthrough.
  - Commit-range fallbacks.
  - Explicit design tmpdir and exported design paths.
  - Missing arguments and security-sidecar exit 3.
- Assert exact stdout, stderr, log sites, tool names, and exit-code distinctions where these are contract-bearing.
- Name focused tests so the existing `make test-oos-disposition-gate` pytest selector runs gate, checkpoint, and delegation-smoke coverage.
- Add a pytest case that executes the reduced Bash smoke and verifies it succeeds.

### REWRITTEN: skills/implement/scripts/test-oos-disposition-gate.sh

- Replace the behavioral harness with an approximately 30-line Bash 3.2-compatible delegation smoke covering both thin wrappers.
- Use a temporary fake `python3` or fake plugin CLI to capture delegated argv.
- For both `oos-disposition-gate.sh` and `oos-disposition-checkpoint.sh`, verify repository-root fallback and `CLAUDE_PLUGIN_ROOT` override selection.
- Verify exact routing to `python/cli.py oos disposition-gate` and `python/cli.py oos disposition-checkpoint`, respectively.
- Verify argument forwarding, exit-status forwarding, and unchanged stdout and stderr passthrough for each wrapper.
- Retain strict mode and reliable temporary-directory cleanup.
- Remove all gate and checkpoint behavior fixtures and assertions.

### UPDATED: skills/implement/scripts/oos-disposition-gate.md

- Keep the runtime invocation, counting rules, and exit-code contract unchanged.
- Identify `python/tests/issue/test_file_oos.py` as the behavioral authority.
- Describe `test-oos-disposition-gate.sh` as delegation-only coverage for both the gate and checkpoint wrappers.
- Point checkpoint behavior coverage to the pytest suite rather than the former combined Bash harness.

### REWRITTEN: skills/implement/scripts/test-oos-disposition-gate.md

- Document the reduced smoke-test scope for both wrapper scripts.
- Add an assertion-parity map from each former Bash gate and checkpoint case to its pytest test or delegation-smoke assertion.
- Include rows for checkpoint-wrapper plugin-root selection, exact CLI routing, argv forwarding, exit-status forwarding, and stdout/stderr passthrough.
- State that the map must contain no Bash-only behavior.
- Record the focused Make target and lint commands.

## Edge cases

- Preserve early skip behavior before required argument or filesystem validation.
- Distinguish disposition gaps from validation failures and security-sidecar handoff.
- Do not let a stale run ID bind another run’s NDJSON.
- Preserve strict URL-field parsing and loose URL token parsing as separate contracts.
- Keep incidental security prose and off-host issue URLs from satisfying the gate.
- Keep checkpoint-wrapper delegation coverage independent of direct Python checkpoint behavior tests.

## Failure modes

- A missing parity row can silently drop behavior when the Bash harness shrinks.
- Pytest names outside the existing `-k 'disposition_gate'` selector can leave focused coverage unscheduled.
- A smoke that invokes the real CLI would retest behavior instead of isolating wrapper delegation.
- Omitting the checkpoint wrapper from the smoke leaves its plugin-root selection, routing, and passthrough contract untested.
- Over-broad subprocess mocking can hide commit-range or stderr-routing mistakes.

## Testing strategy

- Run the original Bash harness before reduction as the parity baseline.
- Run the focused pytest cases during the port.
- Run `make test-oos-disposition-gate` after the smoke rewrite.
- Confirm the parity map has no unmatched Bash-only assertion, including either wrapper’s delegation contract.
- Run `make lint-bash32`.
- Run ShellCheck on `skills/implement/scripts/test-oos-disposition-gate.sh`.

## Acceptance

- Run the original Bash harness before reduction as the parity baseline.
- Run the focused pytest cases during the port.
- Run `make test-oos-disposition-gate` after the smoke rewrite.
- Confirm the parity map has no unmatched Bash-only assertion, including either wrapper’s delegation contract.
- Run `make lint-bash32`.
- Run ShellCheck on `skills/implement/scripts/test-oos-disposition-gate.sh`.

diff_added: 630
diff_deleted: 990
mechanical_churn: false
oversize_override: operator
diff_lines: 1620

## Test plan
(no test plan section in plan-file)
