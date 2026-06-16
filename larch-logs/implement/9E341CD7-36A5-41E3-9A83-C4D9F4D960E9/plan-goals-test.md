## Goal
Implement issue #4402: [IMPLEMENTING] [Bug] /implement escalation: lint-fix-loop failed to suppress pyright private-usage and type errors introduced by review-round fixes (ship-pr:main-agent-required).

## Implementation Plan
## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Follow the approved outline scope.
- Keep the fix narrow.
- Make six behavior changes:
  - Teach lint-fix coders that exact Pyright `# type: ignore[...]` comments are acceptable for narrow type-checker failures that should not be fixed by broad refactors.
  - Preserve Step 5 lint-fix stall tokens into the stall-recovery bail input so timeout-only detail logs cannot hide the real lint-fix failure.
  - Clear stale Step 5 lint-fix bail tokens on non-lint-fix stalls.
  - Classify lint-fix terminal bail tokens as `lint-failure` before scanning for `timeout`.
  - Allow the new classifier pattern and persisted lint-fix bail tokens through Python report-safe rendering.
  - Keep the bash report-safe bail allowlist in sync with the Python bail-token config.

## Files to modify/create

### UPDATED: python/checks.py

Add a short `## Pyright type errors` section inside `_compose_prompt`.

Place it before the final-line instructions and before the untrusted log fence.

Include these points:

- If Pyright reports a narrow line-level issue and a safe local typed fix is not obvious, add an exact ignore comment.
- Use the exact error code, for example `# type: ignore[reportPrivateUsage]`.
- Cover these codes:
  - `reportPrivateUsage`
  - `reportCallIssue`
  - `reportArgumentType`
  - `reportUnknownArgumentType`
  - `reportUnknownLambdaType`
- When Pyright prints multiple codes for one line, use one exact comma-separated ignore comment, for example `# type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]`.
- Do not rename private helpers or broaden APIs just to silence `reportPrivateUsage`.
- Keep edits minimal.

Do not move the existing untrusted-log warning.

### UPDATED: skills/implement/references/step5-review-branches.md

In the `stall` branch, preserve lint-fix stall reasons into the durable bail channel that Step 18a classification reads.

Define the lint-fix stall tokens as:

- `lint-fix-failed`
- `lint-fix-attempt-cap`
- `lint-fix-main-agent-required`

When `$IMPLEMENT_TMPDIR/ship-pr-state.sh` already exists:

- Continue rewriting `STALL_TRACKING=$STALL_TRACKING` by key.
- Compute the current durable lint-fix bail value from the current `STALL_REASON`.
- If `STALL_REASON` is one of the lint-fix tokens, rewrite `BAIL_REASON=$STALL_REASON` by key.
- If `STALL_REASON` is not one of the lint-fix tokens, rewrite `BAIL_REASON=` by key.
- If an `IMPLEMENT_BAIL_REASON` key already exists in that state file, apply the same rule:
  - Rewrite it to the current lint-fix token when `STALL_REASON` matches.
  - Rewrite it to empty when `STALL_REASON` does not match.
- Do not leave a prior lint-fix `BAIL_REASON` or `IMPLEMENT_BAIL_REASON` in place across a later non-lint-fix Step 5 stall.
- Do not source the file.

When seeding `$IMPLEMENT_TMPDIR/ship-pr-state.sh` from the Step 8 canonical key block:

- Keep copying the full canonical key set.
- Set `BAIL_REASON=$STALL_REASON` only when `STALL_REASON` is one of the lint-fix tokens.
- Otherwise leave `BAIL_REASON=` empty.
- Keep `IMPLEMENT_BAIL_REASON` consistent with the canonical key block behavior if that key is present in the seeded file.
- Keep `BAIL_FAILURE_DETAIL_LOG=` empty unless existing local logic already has a validated detail log.
- Keep the existing `PHASE=checks`, `STALL_STEP=5`, retry counters, timeout behavior, and PR fields unchanged.

This is the durable handoff that makes Step 18a classification see the current lint-fix token even when the separate detail log only contains timeout or Pyright text.

### UPDATED: python/config.py

Add the three lint-fix tokens to the render-safe stall-recovery bail token set:

- `lint-fix-failed`
- `lint-fix-attempt-cap`
- `lint-fix-main-agent-required`

Place them with the other `STALL_RECOVERY_BAIL_REASON_TOKENS`.

This keeps the new Step 5 `BAIL_REASON` values public-report safe for Python report paths.

### UPDATED: python/stall_recovery.py

In `_classify_text`, add an explicit lint-fix bail-token check before the transient `timeout` check.

Return:

- `FAILURE_CLASS=lint-failure`
- `RESUME_HINT=step5-review`
- `MATCHED_CLASSIFIER_PATTERN=lint-fix-bail-token`

Match these tokens in `lower`:

- `lint-fix-failed`
- `lint-fix-attempt-cap`
- `lint-fix-main-agent-required`

Keep the existing generic lint-output classifier later in the function.

Do not change retry counts, timeout behavior, or the rebase special case.

Update `_sensitive_value_is_allowlisted` so `lint-fix-bail-token` is an allowed matched-classifier pattern.

### UPDATED: scripts/stall-recovery-report.sh

Keep the bash render-safe allowlist in sync with `python/config.py`.

Update `safe_bail_reason_value()` so its hardcoded safe case list accepts:

- `lint-fix-failed`
- `lint-fix-attempt-cap`
- `lint-fix-main-agent-required`

Place them near the existing stall-recovery bail tokens.

Do not broaden the function to accept arbitrary values.

Ensure `lint_runtime_bail_tokens()` can iterate the Python config tokens without redacting these three values.

### UPDATED: python/test_checks.py

Add a focused `_compose_prompt` test near the existing prompt tests.

Test shape:

- Create a temp checks log with Pyright-like output.
- Call `checks._compose_prompt(...)` with the existing test ignore for private usage.
- Assert the prompt includes:
  - `## Pyright type errors`
  - `# type: ignore[reportPrivateUsage]`
  - `# type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]`
  - each listed Pyright code
  - a sentence or phrase that rejects renaming private helpers only to satisfy `reportPrivateUsage`

Do not assert the whole prompt byte-for-byte.

### UPDATED: python/test_stall_recovery.py

Add classifier and rendering regressions.

Classifier regression:

- Parametrize over:
  - `lint-fix-failed`
  - `lint-fix-attempt-cap`
  - `lint-fix-main-agent-required`
- Write `ship-pr-state.sh` with:
  - `STALL_TRACKING=true`
  - `STALL_STEP=5`
  - `PHASE=review`
  - `BAIL_REASON=`
  - `EXIT_CODE=1`
- Write an in-tmpdir detail log that includes `timeout` and Pyright text, but no lint-fix token.
- Run `stall_recovery.classify_main(...)` with:
  - `--failure-detail-log <detail-log>`
  - `--bail-reason <token>`
- Assert output includes:
  - `FAILURE_CLASS=lint-failure`
  - `RESUME_HINT=step5-review`
  - `MATCHED_CLASSIFIER_PATTERN=lint-fix-bail-token`

Add a second branch or separate parametrized case for the durable-state path:

- Write `BAIL_REASON=<token>` in `ship-pr-state.sh`.
- Omit `--bail-reason`.
- Use the same timeout-only detail log.
- Assert the same lint-failure classification.

Add a negative regression:

- Use `STALL_TRACKING=true`, `STALL_STEP=5`, `PHASE=review`, and empty `BAIL_REASON`.
- Use a timeout-only detail log.
- Do not pass `--bail-reason`.
- Assert ordinary timeout still classifies as the existing transient class and resume hint.

Add a report-safety regression:

- Verify `lint-fix-bail-token` does not cause Tier B chat-print sensitive-token rejection.
- Prefer a small `compose_report_main(... --surface chat-print ...)` test with `MATCHED_CLASSIFIER_PATTERN=lint-fix-bail-token`.
- If that harness is too large, assert `_sensitive_value_is_allowlisted("lint-fix-bail-token")` directly with the existing private-usage ignore pattern.

### UPDATED: bash/report or lint harness tests for stall-recovery-report.sh

Add or update the smallest existing shell regression that covers `safe_bail_reason_value()`.

Test shape:

- Exercise the runtime bail-token list that includes `config.STALL_RECOVERY_BAIL_REASON_TOKENS`.
- Assert these values are not redacted:
  - `lint-fix-failed`
  - `lint-fix-attempt-cap`
  - `lint-fix-main-agent-required`
- Keep existing unsafe-token redaction coverage.

If harness 17 already validates `lint_runtime_bail_tokens()`, update its expected output so these three tokens pass.

## Edge cases

- A Step 5 lint-fix bail with stderr containing `timeout` must not become `transient-infra`.
- A Step 5 lint-fix bail whose detail log contains only timeout and Pyright text must still classify as `lint-failure` after the Step 5 bail handoff.
- Ordinary timeout text without a lint-fix bail token must keep the current transient classification.
- Existing `ship-pr-state.sh` and fresh-seeded `ship-pr-state.sh` must both carry the current lint-fix bail token.
- A later non-lint-fix Step 5 stall must clear stale `BAIL_REASON` and existing `IMPLEMENT_BAIL_REASON` values.
- Python and bash render-safe bail allowlists must both accept the new lint-fix bail tokens.
- Prompt guidance must not treat the checks log as instructions.
- Prompt guidance must not encourage broad public API changes for test-only `reportPrivateUsage`.
- Multi-code Pyright failures on one line must be covered by one comma-separated ignore comment.

## Failure modes

- If the Pyright section is placed after the log fence, a coder may miss it in long logs.
- If Step 5 preserves only `STALL_REASON` and not `BAIL_REASON`, Step 18a classification may still see empty bail input.
- If Step 5 does not clear stale `BAIL_REASON` on non-lint-fix stalls, a later stall may be misclassified as lint failure.
- If the classifier check is placed after the transient check, the reported bug remains.
- If `lint-fix-bail-token` is not allowlisted, Tier B chat-print validation may reject its own classifier pattern.
- If the Python lint-fix bail tokens are not render-safe bail values, the new Step 5 `BAIL_REASON` values may be redacted or rejected in Python report paths.
- If the bash `safe_bail_reason_value()` list omits the new tokens, `stall-recovery lint` or the shell harness may redact valid runtime bail tokens.

## Testing strategy

Run targeted tests first:

```bash
python3 -m pytest \
  python/test_checks.py::test_compose_prompt_includes_pyright_type_ignore_guidance \
  python/test_stall_recovery.py::test_classify_lint_fix_bail_token_beats_timeout \
  python/test_stall_recovery.py::test_classify_lint_fix_bail_token_from_state_beats_timeout \
  python/test_stall_recovery.py::test_classify_timeout_without_lint_fix_token_stays_transient \
  python/test_stall_recovery.py::test_compose_report_allows_lint_fix_bail_classifier_pattern
```

Run the smallest shell/report regression that covers `safe_bail_reason_value()` or harness 17.

Then run repository-required validation for Python and docs changes:

```bash
make py-lint
make py-test
make lint
```

diff_added: 145
diff_deleted: 8
mechanical_churn: false
diff_lines: 153

## Test plan
(no test plan section in plan-file)
