# Review Round 1

- Mode: `diff`
- 8 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Review append vs emit auth_verdict mismatch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-diag-parity-output.txt
- **Severity**: important
- **Concern**: On review agent failure, `_review_append_launch_failure` still classifies auth via a legacy fixed sidecar list and omits the resolved diagnostic `source` and `stderr_sink`, while `_review_emit_launcher_result` was updated to use them. When auth markers exist only in the resolved `.failure-diag`, retry/NS-retry `.failure-diag`, or launcher `stderr_sink`, execution-issues can log a non-auth/unknown verdict while stdout emits `LAUNCHER_FAILURE_REASON=auth` for the same failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Wire append auth_verdict the same way as emit: external_auth_verdict(tool, source, Path(stderr_sink) if stderr_sink else "", output.with_suffix(".diag"), output) after resolve.
  - From codex-specialist-correctness-output.txt: Include source, stderr_sink, base failure-diag, retry failure-diag, and NS-retry failure-diag in external_auth_verdict.
  - From cursor-specialist-edge-cases-output.txt: Pass stderr_sink into external_auth_verdict in _review_append_launch_failure or share one classification helper with _review_emit_launcher_result.
  - From dyn-diag-parity-output.txt: **Suggested fix:** Align `_review_append_launch_failure` with emit: pass `external_auth_verdict(tool, source, Path(stderr_sink) if stderr_sink else "", output.with_suffix(output.suffix + ".diag"), output)` (or equivalent) so both paths classify from the same diagnostic ordering.


### FINDING_2: Codex implement auth verdict computed before source resolution
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Codex implement auth verdict is computed before the resolved diagnostic source is selected. If `codex-impl-retry.txt.failure-diag` or `codex-impl-ns-retry.txt.failure-diag` contains the only auth signature, the run-log failure is appended with a non-auth verdict even though the resolved carrier shows auth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Move verdict classification into _append_implement_launch_failure after source resolution, or recompute auth against the resolved source and candidate set.


### FINDING_3: Cursor implement auth verdict computed before source resolution
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Cursor implement auth verdict is computed before the resolved diagnostic source is selected. If cursor implement retry or NS-retry `.failure-diag` contains the only auth signature, the chosen diagnostic source shows auth but the logged verdict remains non-auth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Move verdict classification into _append_implement_launch_failure after source resolution, or recompute auth against the resolved source and candidate set.


### FINDING_4: Duplicate `_compose_failure_diag` on review failure paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-diag-parity-output.txt
- **Severity**: important
- **Concern**: `_compose_failure_diag` runs in both `_review_append_launch_failure` and `_review_emit_launcher_result` (and review failures may already compose in `run_external_agent`'s failure `finally`). A second compose appends another `===== additional failure diagnostics =====` block instead of being idempotent, bloating `.failure-diag` (up to ~16KB per append) and degrading downstream stderr-tail rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Compose once per failure path, or skip the emit-time compose when append already composed.
  - From dyn-diag-parity-output.txt: **Suggested fix:** Compose in only one review failure hook (append for terminal failures, emit for preflight-only failures), or skip emit-time compose when append already ran / when `.failure-diag` is already populated for this attempt.


### FINDING_5: Implement stderr-tail regeneration from composed carrier drops launcher stderr
- **Reviewer(s)**: dyn-diag-parity-output.txt
- **Severity**: important
- **Concern**: Implement stderr-tail regeneration renders from the resolved `source`, which is usually the composed `.failure-diag`. Because `_compose_failure_diag` writes the sink section before the diag section while `render_failed_agent_stderr_tail` keeps only the last N lines, regeneration can surface generic `.diag` text and drop launcher stderr that remains only in the earlier sink section, overwriting a better tail that `run_external_agent` wrote from the sidecar via `select_failed_agent_stderr_source`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-diag-parity-output.txt: **Suggested fix:** Regenerate stderr-tail from the most specific launcher stream (for example `sidecar` / `stderr_sink`, or `select_failed_agent_stderr_source`) rather than from the full composed carrier, or reorder/filter compose so sink/launcher stderr is what last-N-line rendering sees.


### FINDING_7: `append-failure --redact` omits tmpdir path scrubbing on richer diagnostic sources
- **Reviewer(s)**: dyn-redaction-bounds-output.txt
- **Severity**: important
- **Concern**: This branch routes richer composed/resolver-selected diagnostics (`.failure-diag`, retry/NS-retry carriers, sidecar/launcher stderr) into `run-log append-failure --redact`, but that path still applies only `redact_secrets_only` and not `redact_tmpdir_paths`. More session tmpdir paths can therefore reach committed `execution-issues.md` / larch-logs without the tmpdir scrubbing used elsewhere (`render_failed_agent_stderr_tail`, `_append_vendor_failure_diagnostics`, `plan_review_panel.py:338`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-bounds-output.txt: **Suggested fix:** When `--redact` is set, apply both `redact.redact_tmpdir_paths` and `redact.redact_secrets_only` in `append_failure_main`, or pre-redact composed/resolver-selected sources in `_append_implement_launch_failure` and `_review_append_launch_failure` before calling append-failure.


### FINDING_9: Missing plan-mandated preflight/auth review integration tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Preflight paths now call `_review_emit_launcher_result` with `stderr_sink` at six sites, but there is no parametrized preflight failure integration test asserting resolver parity. A regression removing sink forwarding or reverting to bare `.diag` classification would pass existing bundle/dirty-tree tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add parametrized _review_launch_codex/_review_launch_cursor preflight failure tests with stderr_sink plus retry/NS-retry .failure-diag files; assert resolved carrier and LAUNCHER_FAILURE_* KVs


### FINDING_10: Missing implement failure test for retry/NS-retry `.failure-diag` selection
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_append_implement_launch_failure` compose/resolve/tail-regen is only tested for generic `.diag` masking; retry/NS-retry filename handling in the full path is unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test seeding *-retry.txt.failure-diag or *-ns-retry.txt.failure-diag and assert append-failure source and regenerated stderr-tail use the retry carrier


