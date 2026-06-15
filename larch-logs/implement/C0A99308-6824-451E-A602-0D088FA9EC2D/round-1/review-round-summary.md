# Review Round 1

- Mode: `diff`
- 10 accepted, 6 rejected (2 neutral)

## Accepted Findings

### FINDING_10: Retry output path naming diverges from shell for non-`.txt` outputs
- **Reviewer(s)**: dyn-collector-contract-output.txt
- **Severity**: important
- **Concern**: `_retry_output_path()` appends `-retry` / `-ns-retry` directly when the output does not end in `.txt`, but the shell always used `${ORIG_OUTPUT%.txt}-retry.txt`. For `foo.out`, Python writes `foo.out-retry` while bash wrote `foo.out-retry.txt`. The same mismatch affects stderr-tail candidate paths, so retry sentinels, outputs, and tail dedup can miss each other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-collector-contract-output.txt: Match the shell suffix rule: strip a trailing `.txt` when present, then always append `-retry.txt` / `-ns-retry.txt` (and align stderr-tail candidate paths to the same stems).


### FINDING_11: Insufficient pytest parity with retired bash collector harnesses
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-retirement-hygiene-output.txt
- **Severity**: important
- **Concern**: Retiring `test-collect-agent-results.sh`, `test-collect-agent-retry.sh`, and `test-collect-agent-bash32.sh` left only eight pytest cases in `test_collect_results.py`, each forcing `LARCH_QUIET_DISABLE=1` in `_reset()`. Many plan-pinned acceptance behaviors (outer-launcher matrix, malformed-sentinel coercion, cap_hit, NS-retry sidecar publish, retired launcher fail-closed) lack regression coverage. `docs/linting.md` may overstate what pytest actually asserts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add monkeypatched tests for `wait_reviewers`, `Popen` cwd, legacy trailer, and env filtering.
  - From cursor-specialist-edge-cases-output.txt: Port the deleted harness scenarios into `test_collect_results.py` with monkeypatched launch/wait seams.
  - From cursor-specialist-testing-output.txt: Port deleted harness case inventory into `test_collect_results.py` via monkeypatched wait/launch/filesystem seams; keep one test per acceptance-criteria cluster.
  - From dyn-retirement-hygiene-output.txt: Add focused pytest cases for each retired-harness concern (retired launcher fail-closed, structured NS-retry success/failure, parallel outer retries with distinct workdirs, quiet-mode stdout on fd 3), and trim `docs/linting.md` to list only what `test_collect_results.py` actually asserts.


### FINDING_20: `test-design-multi-round-integration.sh` passes on `LOOP_STATUS=panel-failed`
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The integration test exits 0 when `LOOP_STATUS=panel-failed`, so CI can pass while the multi-round plan-review integration path is broken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Remove the skip branch and update the stub or invocation to assert `LOOP_STATUS=complete`.


### FINDING_3: `LARCH_COLLECT_RESULTS_*` env vars not stripped before retry launches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-retirement-hygiene-output.txt
- **Severity**: important
- **Concern**: `_env_without_test_hooks()` does not remove `LARCH_COLLECT_RESULTS_*` keys before retry `Popen`. Integration test hooks can leak into production retry subprocesses and skew behavior. Acceptance criterion 23 is unmet and uncovered by pytest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove all env keys with prefix `LARCH_COLLECT_RESULTS_` before `Popen`.
  - From cursor-specialist-edge-cases-output.txt: Strip `LARCH_COLLECT_RESULTS_*` keys in `_env_without_test_hooks()` and add pytest coverage.
  - From dyn-retirement-hygiene-output.txt: Extend `_env_without_test_hooks()` to drop every env key matching `LARCH_COLLECT_RESULTS_*` (and any other collector-specific test hooks named in the old bash harnesses), then add a pytest that sets a hook var, launches a retry, and asserts the child environment omits it.


### FINDING_4: Invalid initial `.done` with empty output treated as `STATUS=OK`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: When sentinel coercion yields a non-numeric `.done` (e.g. `abc`) and the reviewer output file is empty, the `coerced and not output_nonempty` branch sets `exit_code = "0"` and skips the normal `EMPTY_OUTPUT`/retry path. Corrupt sentinels can be accepted as successful empty results instead of retrying or failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Continue through the normal empty-output path after sentinel coercion and add pytest coverage.
  - From codex-specialist-edge-cases-output.txt: After coercion, continue through the empty-output classification/retry path instead of skipping it via `elif`.
  - From codex-specialist-testing-output.txt: Continue through normal empty-output classification after coercion and add pytest coverage.


### FINDING_5: `_cmd_json_requires_outer_launcher` uses first `--mode`/`--sandbox`, not last
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: For review-shaped `CMD_JSON`, the helper stops at the first `--mode` or `--sandbox` argument. A command with `--sandbox full-auto` followed by `--sandbox read-only` bypasses the outer-launcher requirement and can replay through `run-external-agent` without launcher post-processing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Scan all args and let the last `--mode`/`--sandbox` value determine review-shaped replay.


### FINDING_6: `design_publish` writes review provenance at plan top, not before `diff_lines` trailer
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `review_status` and `rounds_completed` are prepended to the composed plan. `scripts/implement-preflight.sh` scans only the final metadata trailer (immediately above `diff_lines`). Plans with provenance at the top and `diff_lines` at the bottom are not refused when panel review failed or completed zero rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Insert or replace provenance in the final trailer block immediately above `diff_lines`.
  - From codex-specialist-edge-cases-output.txt: Insert provenance into the final trailer block immediately before `diff_lines` and optional size trailers.
  - From codex-specialist-testing-output.txt: Insert provenance before the `diff_lines` trailer block and add publish-to-preflight coverage.


### FINDING_7: Stderr-tail dedup uses byte-sum instead of POSIX `cksum`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-caller-cutover-output.txt
- **Severity**: important
- **Concern**: `failed_agent_stderr_signature()` hashes with `sum(norm.encode()) % 2_147_483_647` while `scripts/lib-failed-agent-stderr-tail.sh` uses `cksum`. Normalized tails can collide (e.g. `ab` vs `ba`), changing which failure tails are suppressed during live multi-reviewer collection versus bash parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Port POSIX `cksum` or call `cksum` through a seam and add parity tests.
  - From dyn-caller-cutover-output.txt: Port `failed_agent_stderr_signature()` to use the same `cksum` normalization as `scripts/lib-failed-agent-stderr-tail.sh`, or delegate to a shared Python implementation tested against the bash harness vectors.


### FINDING_8: `derive_tool()` hardcodes codex/cursor instead of external-tool registry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_registered_tools` / `derive_tool()` hardcode `codex` and `cursor` rather than loading the shared external-tool-registry allowlist. Registry expansion will not be reflected in `TOOL=` validation during collection and retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Load allowlist from agent external-tool-registry with test fallback.
  - From cursor-specialist-edge-cases-output.txt: Wire `derive_tool()` and retry validation to the shared external-tool registry surface.


### FINDING_9: `CollectorRecord.fields()` omits `NS_RETRY_MODE` / `NS_RETRY_REASON`
- **Reviewer(s)**: dyn-collector-contract-output.txt
- **Severity**: important
- **Concern**: `CollectorRecord.fields()` does not emit `NS_RETRY_MODE=` or `NS_RETRY_REASON=` on stdout blocks even when populated on `NOT_SUBSTANTIVE` rows. The retired shell collector included these in each `RESULTS[]` entry and emitted them as extra `KEY=value` lines, so failed substantive/structured rows awaiting or after NS retry no longer match the shell stdout grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-collector-contract-output.txt: Extend `fields()` to append `NS_RETRY_MODE=` / `NS_RETRY_REASON=` when non-empty (and preserve the shell field order relative to `STRUCTURED_SIDECAR` / `FAILURE_REASON`), then add pytest coverage that asserts those lines appear on a `NOT_SUBSTANTIVE` block.


