## Goal
Implement issue #5898: [IMPLEMENTING] [BUG] stall-recovery classify misclassifies checks-child-failed SIGTERM as contract-failure; missing --in-memory-stall-tracking causes no-stall premature exit.

## Implementation Plan
## Plan

## Approach

Use the approved outline as binding scope. `approach-synthesis.txt` is `NO_SKETCHES`, so this plan is based on direct repo inspection and the approved discussion constraints.

Keep the change narrow:

- Do not add a new producer bail token.
- Do not edit `dispatch_commit_route.py`.
- Do not change `retry_policy()`.
- Do not add Step 6 retry dispatch.
- Reuse the existing `checks-commit-route-retry` resume path for Step 3 only.

## Files to modify/create

### UPDATED: python/larch/state/_classify.py

- Thread raw exit-code text into `_classify_text`.
  - Add an `exit_code: str = "unknown"` keyword parameter.
  - In `classify()`, compute `raw_exit_code = args.exit_code or st.get("EXIT_CODE", "unknown")` before calling `_classify_text`.
  - Pass that raw value into `_classify_text`.
  - Keep the existing rendered `EXIT_CODE` safety behavior unless tests show a current contract expects negative values to print.
  - In `_classify_generic_from_terminal_state()`, pass the terminal state's raw `EXIT_CODE` into `_classify_text` before output sanitization.

- Add a small private helper for the new condition.
  - Match `checks-child-failed`.
  - Match only `step in {"3", "6"}`.
  - Treat a negative integer exit code as signal-killed.
  - Treat `unknown` or an otherwise unparseable raw exit code as unresolvable and retryable for this bail token.
  - Do not treat positive numeric exits as transient.

- Place the new guard before the current blanket `if step in {"3", "6"}` contract-failure return.
  - Return `("transient-infra", "checks-commit-route-retry", "checks-child-sigterm")` for the matched condition.
  - The second tuple value is mostly legacy because `classify()` recomputes the hint, but keep it semantically accurate.

- Extend `_resume_hint_for`.
  - For `safe_step == "3"`, return `checks-commit-route-retry` when `pattern` is either `checks-leg-abandoned` or `checks-child-sigterm`.
  - Preserve `safe_step == "6"` as `none`.
  - Preserve current behavior for Step 5 self-review abandoned checks markers.

### UPDATED: python/larch/state/_tokens.py

- Add `checks-child-sigterm` to `_safe_matched_pattern_value()`'s allowlist.
- Do not add a new bail token.
- Do not relax generic token validation beyond this matched-pattern string.

### UPDATED: skills/implement/references/stall-recovery.md

- Update Step 18a procedure item 3.
  - Say the classify call must pass the in-memory stall tracking value.
  - Use the existing flag name:
    - `--in-memory-stall-tracking "${STALL_TRACKING:-false}"`
  - Also keep the instruction to pass validated `BAIL_FAILURE_DETAIL_LOG`.

- Update item 5 retry-dispatch prose.
  - Document that `RESUME_HINT=checks-commit-route-retry` also covers `MATCHED_CLASSIFIER_PATTERN=checks-child-sigterm`.
  - State that Step 3 retries the same Step 3 composite launcher through the existing immediate-background fence.
  - State that Step 6 still classifies accurately but does not get automatic retry dispatch.
  - Keep the current genuine checks-content failure sentence.

### UPDATED: python/tests/state/test_stall_recovery.py

- Add focused classifier tests near the existing Step 3/6 classifier tests.

- Add a Step 3 SIGTERM regression test:
  - Set or pass `STALL_STEP=3`, `PHASE=checks`, `BAIL_REASON=checks-child-failed`.
  - Pass `--in-memory-stall-tracking true`.
  - Pass `--exit-code -15`.
  - Assert:
    - `STALL_TRACKING=true`
    - `FAILURE_CLASS=transient-infra`
    - `RESUME_HINT=checks-commit-route-retry`
    - `MATCHED_CLASSIFIER_PATTERN=checks-child-sigterm`
    - not `MATCHED_CLASSIFIER_PATTERN=no-stall`

- Add a Step 3 unknown-exit regression test:
  - Use the same bail token and step.
  - Use `--exit-code unknown`.
  - Assert the same transient retry classification.

- Add a positive-exit guard test:
  - Use `checks-child-failed`, Step 3, and `--exit-code 1`.
  - Assert the existing Step 3 `contract-failure` / `step-contract` behavior remains.

- Add a Step 6 SIGTERM classification-only test:
  - Use `checks-child-failed`, Step 6, and `--exit-code -15`.
  - Assert:
    - `FAILURE_CLASS=transient-infra`
    - `RESUME_HINT=none`
    - `MATCHED_CLASSIFIER_PATTERN=checks-child-sigterm`

- Add or adjust generic-profile coverage only if an existing nearby generic classify test can be extended without large setup.
  - Expected class: `transient-infra`.
  - Expected resume hint: `none`.

## Edge cases

- Missing `--in-memory-stall-tracking` should still allow existing dead `.bg-wait-active` marker recovery.
- Positive checks-child exits should not become transient.
- Step 6 should not retry even when it classifies as `transient-infra`.
- Unknown exit code should be transient only with `checks-child-failed`, not for arbitrary Step 3/6 bails.
- Existing lint/test evidence for Step 3/6 positive exits should still fall through to `step-contract`.

## Failure modes

- If raw exit code is sanitized before classification, `-15` becomes `unknown`. Avoid that by passing raw text into `_classify_text`.
- If the new pattern is not allowlisted, output becomes `MATCHED_CLASSIFIER_PATTERN=redacted`, which hides the fix.
- If `_resume_hint_for` matches the new pattern without a Step 3 gate, Step 6 could get an unsupported retry path.
- If Step 18a docs omit `--in-memory-stall-tracking`, prompt-side recovery can still return `no-stall` before the classifier sees the bail reason.

## Testing strategy

Run changed-file tests only:

- `python3 -m pytest python/tests/state/test_stall_recovery.py`
- `make py-lint` if Python lint dependencies are available.
- For the Markdown-only prompt change, inspect the rendered prose or grep for `--in-memory-stall-tracking` and `checks-child-sigterm` in `skills/implement/references/stall-recovery.md`.

## Acceptance

- A Step 3 `checks-child-failed` stall with a negative (SIGTERM) or unresolvable exit code classifies as `FAILURE_CLASS=transient-infra`, `MATCHED_CLASSIFIER_PATTERN=checks-child-sigterm`, `RESUME_HINT=checks-commit-route-retry` — not `no-stall` / `unrecoverable`.
- The same Step 3 stall with a positive exit code still classifies as `FAILURE_CLASS=contract-failure` / `MATCHED_CLASSIFIER_PATTERN=step-contract` (unchanged regression behavior).
- A Step 6 `checks-child-failed` SIGTERM stall classifies as `FAILURE_CLASS=transient-infra` but keeps `RESUME_HINT=none` (accurate classification, no automatic retry).
- `MATCHED_CLASSIFIER_PATTERN=checks-child-sigterm` is emitted un-redacted (present in `_tokens.py`'s allowlist), not rewritten to `redacted`.
- `skills/implement/references/stall-recovery.md` Step 18a item 3 documents passing `--in-memory-stall-tracking "${STALL_TRACKING:-false}"` to `stall-recovery classify`.
- `skills/implement/references/stall-recovery.md` item 5 documents that `RESUME_HINT=checks-commit-route-retry` now also covers the `checks-child-sigterm` pattern, and that Step 6 still does not get automatic retry dispatch.
- `python3 -m pytest python/tests/state/test_stall_recovery.py` passes, including new SIGTERM/unknown-exit/positive-exit/Step-6 regression tests and the existing unchanged `test_classify_step3_contract_failure_despite_pytest_evidence` / `test_classify_step6_contract_failure_despite_lint_evidence` tests.
- `dispatch_commit_route.py` and `retry_policy()` are unmodified (no new bail token, no new retry cap).

diff_lines: 77

## Test plan
(no test plan section in plan-file)
