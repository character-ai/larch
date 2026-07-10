## Goal
Implement issue #6826: [IMPLEMENTING] [BUG] Codex reports STATUS=complete on quota exit instead of STATUS=bailed.

## Implementation Plan
## Plan

## Approach

Detect quota truncation only in the validated `complete` path, after plan coverage has been computed and before the dispatcher materializes a commit message or stages changes.

- Reuse `is_quota_failure(tool=st.coder, sidecar=st.sidecar_log)` rather than duplicating quota matching.
- Override a self-reported complete result only when both conditions hold:
  - `plan_coverage.disposition_required` is true.
  - The selected coder’s sidecar is classified as a quota failure.
- Route the override through `st.emit_bailed("quota")` so no partial working tree is committed.
- Register `quota` across the dispatcher and stall-recovery bail-token surfaces so downstream classification preserves the reason, renders `BAIL_REASON=quota`, and takes the established Step 2 dispatch-failure recovery route.
- Keep full-coverage runs complete even when their sidecar contains a quota marker. Ensure that control fixture has no blocking `todos_left`.
- Leave manifest schema, launcher behavior, `needs_qa`, implementer-authored `bailed` manifests, small-gap warnings, and quota mirroring unchanged.

## Files to modify/create

### UPDATED: python/larch/implement/dispatch_step2.py

- Import `is_quota_failure` from `larch.agents._launch_failure`.
- After `compute_and_write_coverage()` succeeds, check whether `plan_coverage.disposition_required` is true and the selected coder’s sidecar reports quota exhaustion.
- Perform that check before uncovered-path diagnostics that lead into commit-message materialization, `git add`, and `git commit`.
- Return `st.emit_bailed("quota")` for the combined condition, preserving its existing `STATUS=bailed`, `REASON=quota`, and `ORCHESTRATOR_EDIT_AUTHORITY=forbidden` wire contract.
- Continue the existing complete path when coverage does not require operator disposition, including when the sidecar contains a quota marker.

### UPDATED: python/larch/state/_tokens.py

- Add `quota` to `_DISPATCH_BAIL_TOKENS` so the downstream classifier recognizes the dispatcher-produced bail reason.
- Add `quota` to the explicit expanded safe bail-reason set used by `_safe_bail_reason_value`, allowing stall-recovery output to render the actionable token instead of `redacted`.

### UPDATED: python/larch/core/config.py

- Add `quota` to `STALL_RECOVERY_BAIL_REASON_TOKENS`.
- Keep this configuration list aligned with the stall-recovery runtime token validation and safe rendering contract.

### UPDATED: python/tests/implement/test_implement_dispatch.py

- Add a partial-coverage-plus-quota regression using a plan fixture that deterministically requires disposition—for example, two required paths with only one modified, producing 50% untouched coverage.
- Have the fake launcher:
  - return exit code 0,
  - write a schema-valid `complete` manifest,
  - write the quota marker to `st.sidecar_log`, and
  - modify only one required plan path.
- Assert the computed coverage artifact records `PLAN_COVERAGE_DISPOSITION_REQUIRED=true`, proving the fixture reaches the pre-bail condition.
- Assert dispatcher stdout emits `STATUS=bailed` and `REASON=quota`, does not emit `STATUS=complete` or `PLAN_COVERAGE_DISPOSITION_REQUIRED=true`, and leaves the partial working-tree edit uncommitted.
- Add a full-coverage quota-sidecar control case that touches every required plan path and uses `todos_left: []` (or only recognized nonblocking full-suite validation TODOs).
- Assert the control coverage is not disposition-required, emits `STATUS=complete` with `PLAN_COVERAGE_DISPOSITION_REQUIRED=false`, and commits normally despite the quota marker.

### UPDATED: python/tests/state/test_stall_recovery.py

- Extend the dispatch-bail classification coverage with `quota`.
- Assert a state or command-line `BAIL_REASON=quota` is preserved in classifier output, produces `FAILURE_CLASS=dispatch-failure`, `RESUME_HINT=step2-impl`, and `MATCHED_CLASSIFIER_PATTERN=dispatch-bail-token`, rather than falling back to an unrecoverable/redacted result.

### UPDATED: python/tests/core/test_config.py

- Assert that `quota` is included in `config.STALL_RECOVERY_BAIL_REASON_TOKENS`, protecting the configuration-level registration required by stall-recovery token validation.

## Edge cases

- Missing, empty, or non-quota sidecars remain ignored through `is_quota_failure()`’s existing behavior.
- Full coverage remains complete even when a stale or informational quota marker is present.
- Blocking `todos_left` continues to require disposition; the full-coverage control explicitly avoids that state.
- Advisory and middle-band coverage gaps remain on their existing complete/warning path because the quota override requires `disposition_required`.
- The check applies through `st.coder` and `st.sidecar_log`, without adding Codex-specific dispatch branching.
- `needs_qa` and implementer-authored `bailed` results do not enter the complete-path coverage override.

## Failure modes

- Checking after `git add` or `git commit` would preserve the partial-commit bug; the override must run immediately after coverage calculation and before all commit operations.
- A weak fixture with only an advisory coverage gap would not exercise the bail condition; use a deterministic high-band or blocking-TODO coverage state and assert its pre-bail artifact.
- An unconditional quota override could discard fully covered work; require `plan_coverage.disposition_required`.
- Registering `quota` only in the dispatcher would cause downstream rendering/classification drift; update the dispatcher token set, safe renderer allowlist, and stall-recovery configuration together.
- Reimplementing quota regexes could diverge from launcher classification; reuse `is_quota_failure`.
- Emitting new wire fields could break consumers; use the existing `st.emit_bailed("quota")` contract.

## Testing strategy

- Run the focused Step 2 dispatcher regression:
  - `make test-step2-dispatch`
- Run the focused stall-recovery classification coverage:
  - `make test-stall-recovery-report-1`
- Run the focused configuration test:
  - `python3 -m pytest python/tests/core/test_config.py -q`
- Run changed-file Python lint and type checks:
  - `cd python && python3 -m ruff check larch/implement/dispatch_step2.py larch/state/_tokens.py larch/core/config.py tests/implement/test_implement_dispatch.py tests/state/test_stall_recovery.py tests/core/test_config.py`
  - `cd python && python3 -m pyright larch/implement/dispatch_step2.py larch/state/_tokens.py larch/core/config.py tests/implement/test_implement_dispatch.py tests/state/test_stall_recovery.py tests/core/test_config.py`
- Confirm all routing outcomes:
  - Partial coverage plus quota computes a disposition-required coverage artifact, bails before commit, and preserves `REASON=quota`.
  - Full coverage plus quota remains complete and commits.
  - Stall recovery preserves and classifies `quota` as a Step 2 dispatch bail.

Confidence: high. The dispatcher already owns the coverage result and commit boundary; the quota classifier already owns sidecar matching. The revision also closes the accepted downstream token-registration gap.

## Acceptance

- Run the focused Step 2 dispatcher regression:
  - `make test-step2-dispatch`
- Run the focused stall-recovery classification coverage:
  - `make test-stall-recovery-report-1`
- Run the focused configuration test:
  - `python3 -m pytest python/tests/core/test_config.py -q`
- Run changed-file Python lint and type checks:
  - `cd python && python3 -m ruff check larch/implement/dispatch_step2.py larch/state/_tokens.py larch/core/config.py tests/implement/test_implement_dispatch.py tests/state/test_stall_recovery.py tests/core/test_config.py`
  - `cd python && python3 -m pyright larch/implement/dispatch_step2.py larch/state/_tokens.py larch/core/config.py tests/implement/test_implement_dispatch.py tests/state/test_stall_recovery.py tests/core/test_config.py`
- Confirm all routing outcomes:
  - Partial coverage plus quota computes a disposition-required coverage artifact, bails before commit, and preserves `REASON=quota`.
  - Full coverage plus quota remains complete and commits.
  - Stall recovery preserves and classifies `quota` as a Step 2 dispatch bail.

Confidence: high. The dispatcher already owns the coverage result and commit boundary; the quota classifier already owns sidecar matching. The revision also closes the accepted downstream token-registration gap.

diff_lines: 165

## Test plan
(no test plan section in plan-file)
