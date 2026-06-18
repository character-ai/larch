# Review Round 1

- Mode: `diff`
- 9 accepted, 5 rejected (5 neutral)

## Accepted Findings

### FINDING_1: Postbump validation dropped semver enforcement for NEW_VERSION
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Postbump CLI validation only checks that `NEW_VERSION` is non-empty when `BUMP_TYPE` is not `NONE`, not that it matches the former `X.Y.Z` semver contract. A corrupt `finalize-state.sh` (e.g. `BUMP_TYPE=PATCH`, `NEW_VERSION=not-a-version`) passes validation and reaches postbump rebase/force-push with invalid version metadata that the retired shell rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore the deleted Bash semver regex check and add a regression test in python/test_finalize.py.
  - From cursor-specialist-edge-cases-output.txt: Restore the `^[0-9]+\.[0-9]+\.[0-9]+$` check from implement-finalize.sh and add a pytest regression.
  - From codex-specialist-testing-output.txt: Restore the semver regex check for non-NONE bump types and add a direct `implement_finalize_postbump_main` regression test.


### FINDING_10: `test-finalize-sanity-check` retargeted without `_cleanup_target_ok` unit tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: A retargeted `test-finalize-sanity-check` runs `implement_finalize` CLI tests instead of cleanup-target sanity checks; `_cleanup_target_ok` has zero direct tests. Wrong-session tmpdir deletion guards (#1572) could regress with no harness failure while docs still claim sanity coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `_cleanup_target_ok` unit tests matching the deleted bash harness and wire `test-finalize-sanity-check` to them.


### FINDING_2: Step 16-17 silently skips closeout when tmpdir is missing or fence omits env
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-closeout-flow-output.txt
- **Severity**: important
- **Concern**: `step_16_17` returns exit `0` when `IMPLEMENT_TMPDIR` cannot be resolved, while `step_16` and `step_17` return `2` for the same error and the retired `step-16-17.sh` failed via `${IMPLEMENT_TMPDIR:?…}`. The Step 16-17 SKILL fence invokes `python3 …/cli.py implement step-16-17` directly without `--implement-tmpdir "$IMPLEMENT_TMPDIR"` and without routing through `bash "$IMPLEMENT_TMPDIR/larch-run.sh"`, so a misconfigured Bash subprocess can silently skip rejected-findings, Slack announce, final-report, and summary markers while the orchestrator proceeds to Step 18.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return `2` from `step_16_17` on `_resolve_tmpdir` failure, consistent with `step_16` and `step_17`.
  - From cursor-specialist-edge-cases-output.txt: Add `--implement-tmpdir "$IMPLEMENT_TMPDIR"` to the SKILL fence and/or route through `larch-run.sh`; make `step_16_17` fail loud when tmpdir cannot be resolved.
  - From codex-specialist-edge-cases-output.txt: Invoke through `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement step-16-17`.
  - From dyn-closeout-flow-output.txt: Match sibling entrypoints: return `2` on tmpdir resolution failure. Keep the wrapper’s unconditional `return 0` only after tmpdir validation succeeds and the Step 16 / Slack / Step 17 sequence has run.


### FINDING_4: Teardown sentinel writes are unguarded, breaking best-effort finalize
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Teardown uses unguarded sentinel writes (e.g. `.run-cleaned-up`). If `finalize-state.sh` is readable but the tmpdir cannot create `.run-cleaned-up`, `implement-finalize teardown` raises `OSError` before tail KVs or cleanup completes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Catch `OSError` and `ShipError` around sentinel writes, store warning detail, and continue teardown.


### FINDING_5: Step 16-17 wrapper raises on log/filesystem errors instead of best-effort exit 0
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The composed `step_16_17` wrapper can raise on log-open or other filesystem errors (e.g. `slack_log.open`) when the tmpdir exists but is not writable, instead of always returning `0` after best-effort Step 16 / Slack / Step 17 work. The same pattern appears in related closeout log handling around lines 191–216.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Make Slack and Step 17 log handling best-effort, guard `step_17`, and always return `0` from the composed wrapper.
  - From codex-specialist-edge-cases-output.txt: Wrap log opens, backup cleanup, and marker touches in `OSError`-tolerant paths and fall back to `DEVNULL` or a temp sink while preserving `step_16_17_main` exit `0`.


### FINDING_6: Preflight lets corrupt issue JSON and read failures escape as uncontrolled exceptions
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, dyn-preflight-gates-output.txt
- **Severity**: important
- **Concern**: `_read_json_field` lets `json.JSONDecodeError` and other read/decode failures propagate uncaught. The retired `scripts/implement-preflight.sh` used `json_field … || exit 2`, so corrupt or empty `issue.json` exited **2** with no success envelope. Malformed issue JSON or truncated `gh` output can instead produce a traceback and a non-**2** exit, breaking Preflight exit semantics and the operator contract for machine-parseable failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Catch `OSError` and `JSONDecodeError` around captures and issue JSON reads, print a generic preflight failure, and return `2` without emitting the success envelope.
  - From dyn-preflight-gates-output.txt: Wrap `_read_json_field` (or each call site) in a small helper that catches `OSError` and `json.JSONDecodeError`, prints `**❌ /implement preflight: gh issue view failed for issue #<N>.**` or a dedicated decode-failure line matching the shell contract, and returns exit **2** without leaking file contents.


### FINDING_7: Preflight propagates OSError on write/append without controlled exit 2
- **Reviewer(s)**: dyn-preflight-gates-output.txt
- **Severity**: important
- **Concern**: `_write_text` and `_append_bypass` propagate `OSError` on mkdir/write/append failure. The Bash `write_fallback_plan` / `append_bypass` paths used `|| exit 2`, so a full tmpdir or failed bypass-log append aborted Preflight with exit **2** before later gates ran. The port can crash mid-emergency-bypass after printing warnings, leaving a partial run and an unreliable `BYPASS_COUNT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-preflight-gates-output.txt: Catch `OSError` at these boundaries, print the same class of `**❌ /implement preflight: ...**` operator errors the shell used for hard helper failures, and `return 2` from `preflight_main` (do not continue to `gh` / plan-block after a failed bypass append).


### FINDING_8: Insufficient `test_preflight.py` coverage after harness retirement
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Replacing `scripts/test-implement-preflight.sh` with a small pytest module drops coverage for plan-required gates: emergency `missing-designed-prefix` bypass, malformed-plan refusal/fallback, `panel-init-failed` / `panel-skipped` refusal, and `gh issue view` retry-once. Regressions in admission bypass, zero-review refusal, retry path, or emergency/non-emergency malformed-plan behavior could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add stubbed test: admission `rc!=0` with `ADMISSION_RESULT=missing-designed-prefix`, `--emergency`, assert success envelope and `BYPASS_COUNT=1`.
  - From cursor-specialist-testing-output.txt: Extend `test_preflight.py` with stub cases from the deleted harness; update `docs/linting.md` to match.
  - From codex-specialist-testing-output.txt: Add tests stubbing first `gh` failure then success, plus plan-block `rc 1` with `MALFORMED` for refusal and emergency fallback.


### FINDING_9: Insufficient `test_closeout.py` coverage for composed Step 16-17 wrapper
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-closeout-flow-output.txt
- **Severity**: important
- **Concern**: The deleted `skills/implement/scripts/test-step-16-17.sh` covered six integration scenarios at the composed-wrapper level (happy path, Step 16 failure still reaching markers, Slack skip vs fail, stale-summary failure with no markers, upsert-fail with fresh summary and markers, empty-summary failure with no markers). The new pytest module exercises only a subset in isolation and does not assert wrapper-level marker gating for stale failure, upsert-fail, or empty failure paths that drive operator-visible closeout (`---LARCH-SUMMARY-FINAL-*---`, `.step17-printed` vs `.step17-emitted`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port the deleted harness scenarios into `test_closeout.py` with stubbed `subprocess.run` and assert markers, sentinels, Tool Failures, and exit codes.
  - From dyn-closeout-flow-output.txt: Port the retired harness cases into `python/test_closeout.py`, especially `step_16_17` tests for: stale write failure → no markers and restored `summary-final.md`; upsert/post-write failure → Tool Failure logged and markers with refreshed body; `fail-empty` → no markers.


