## Plan


Reduce the round-aware static-panel denominator to the post-#2449 reality: both `hard` and `simple` panels run with **6 Cursor specialist slots only**, regardless of round. Eliminate phantom never-launched failures triggered by the stale `STATIC_INTENDED_SLOTS=12` (HARD) / `=7` (SIMPLE) values that PR #2449 left behind when it removed the Codex specialist slots from `dispatch-panel.sh`.

## Files to modify/create

### UPDATED: `skills/review/scripts/check-reviewer-failure-threshold.sh`

Replace the round-aware `STATIC_INTENDED_SLOTS` block (the comment header plus the `if (( ROUND_NUM == 1 )); then ... else ... fi` body that currently spans the comment block and the round-aware case) with a single flat assignment that matches the actual launcher manifest.

- Replace the four-line comment block describing the round-aware Codex omission with: `# Both panels use 6 Cursor specialist slots only (Codex removed in #2449).` followed by the existing second sentence that explains dynamic-scout exclusion: `# Dynamic scout reviewers are excluded from the threshold denominator and should not affect the static panel result.`
- Replace the `if (( ROUND_NUM == 1 )); then case "$PANEL" in ...; esac else STATIC_INTENDED_SLOTS=6 fi` block with a single line: `STATIC_INTENDED_SLOTS=6`.
- Update the inline comment above the threshold math (currently: `# Threshold: >50% of intended panel size. HARD=12 → fail if >6. SIMPLE=7 → fail if >3.`) to read: `# Threshold: >50% of intended panel size. 6 slots → fail if >3 (HALF_PLUS_ONE_MIN=4).`
- **Do not** delete or otherwise touch the `--round-num` flag parsing, `ROUND_NUM` default/validation, or the `ROUND_NUM=$((10#$ROUND_NUM))` line. The issue explicitly states this is dead but harmless code; `review-core.sh` still passes the flag.

### UPDATED: `skills/review/scripts/check-reviewer-failure-threshold.md`

Update three drift-prone prose locations to match the new flat denominator (no other edits):

- `--panel hard|simple` row in the Args table: change `The intended panel size: HARD=12, SIMPLE=7.` to `The intended panel size: 6 (both panels).` (panel enum kept for backward CLI compatibility with `review-core.sh`).
- `INTENDED_SLOTS` row in the Output table: change `12 (HARD) or 7 (SIMPLE)` to `6 (both panels)`.
- Threshold section: replace the example math `For HARD (12) this is 7 → fail if FAILED_SLOTS >= 7. For SIMPLE (7) this is 4 → fail if FAILED_SLOTS >= 4.` with `For 6 slots this is 4 → fail if FAILED_SLOTS >= 4 (both panels).`

### UPDATED: `skills/review/scripts/test-check-reviewer-failure-threshold.sh`

Adjust the four existing test cases whose recorded assertions encode the stale 12/7 denominator. Keep the test count, labels, and ordering; only update the assertion expected values (and one threshold-outcome flip in the half_fail_hard case) so the harness reflects the new flat behavior. The round2_* cases already assert INTENDED_SLOTS=6 and continue to pass unchanged — they document the `--round-num` flag is still parsed even though dead code.

1. `half_fail_hard` (6 OK + 6 timeout, no `--launched-slots`):
   - Now FAILED_SLOTS=6 and INTENDED_SLOTS=6, so 6 ≥ HALF_PLUS_ONE_MIN(4) → THRESHOLD_OK=false. Flip the expected from `true` to `false` and update the assertion label from "6/12 fail HARD → OK (not >50%)" to "6 fail (12 records) → over threshold". Keep the `FAILED_SLOTS=6` assertion unchanged (still correct).
2. `never_launched` (`--launched-slots 6`, 6 OK records):
   - NEVER_LAUNCHED is now `6 − 6 = 0`, so FAILED_SLOTS=0 (was 6). Update the expected from `6` to `0` and the label to reflect "6 OK launched + 0 never-launched → FAILED_SLOTS=0". The `THRESHOLD_OK=true` assertion remains correct; update its label phrasing only if needed for clarity.
3. `both_down` (`--launched-slots 0`, zero records):
   - NEVER_LAUNCHED is now `6 − 0 = 6` (was 12). Update FAILED_SLOTS expected from `12` to `6`. The `THRESHOLD_OK=false` assertion remains correct.
4. `dynamic_hard` (`--launched-slots 16`, 12 static + 4 dyn records):
   - INTENDED_SLOTS is now 6 (was 12). Update the expected from `12` to `6` and the label from "dynamic slots do not widen intended denominator" to "dynamic slots do not widen intended denominator (static=6)". The remaining `THRESHOLD_OK=true` and `COUNTED_SLOTS=12` assertions still pass (3 of 12 records failed; 3 < HALF_PLUS_ONE_MIN=4).

No new test cases. No removed test cases. No changes to `emit_records`, `assert_eq`, `run_case`, or the trap teardown.

### UPDATED: `skills/review/scripts/test-check-reviewer-failure-threshold.md`

Required by `.claude/rules/script-md-siblings.md`: update the sibling doc to reflect the new flat-denominator coverage so the .sh harness and its .md description stay in sync.

- Coverage bullet currently reading `HARD (12-slot) panel: all OK, exactly half fail (6/12 → still OK), just-over-half fail (7/12 → fail), all fail (12/12 → fail).`: drop the "(12-slot)" qualifier, rephrase the half-fail exemplar as "6 fail of 12 records → over threshold (6-slot panel)", and keep the 7/12 / 12/12 exemplars as record-counts only (these still drive the harness inputs unchanged).
- Coverage bullet currently reading `SIMPLE (7-slot) panel: under threshold (3/7), just-over (4/7).`: drop the "(7-slot)" qualifier; record-count exemplars (3/7, 4/7) are accurate as-is since the harness still injects 7 records.
- Coverage bullet currently reading `Both-down case: zero records, zero launched → all 12 counted as failures.`: change "all 12" to "6" to match the new `NEVER_LAUNCHED = 6 − 0` math.
- No changes to Invocation, exit-code sections, or the round-2+ description.

Total ~3 line edits in `test-check-reviewer-failure-threshold.md`.

## Approach

The fix is mechanical: collapse a round-aware case statement into a single flat constant, and propagate the new value through three doc strings and four test assertions. The implementation follows the diff exactly as specified in the issue body, with two minor expansions:

1. **Inline comment at the threshold-math anchor** (line "Threshold: >50% of intended panel size..."): the issue body does not explicitly call this out, but it documents stale HARD=12 / SIMPLE=7 numbers and would drift after the fix. Updating it is consistent with the issue's directive to update doc strings (`check-reviewer-failure-threshold.md`).
2. **Test harness assertion updates**: the issue body does not name `test-check-reviewer-failure-threshold.sh`, but four existing test cases assert values derived from the stale denominator. The harness will fail CI after the fix unless these are updated. Keep the changes minimal — only the four broken cases, no rewrites.

Preserve the `--round-num` flag, the `ROUND_NUM` validation block, and the `ROUND_NUM` value normalization (`$((10#$ROUND_NUM))`). The issue body explicitly designates this dead code as "harmless to leave"; removing it would expand the diff blast radius and could break the `review-core.sh` caller, which continues to pass `--round-num` per its own argparse loop.

## Edge cases

- **`--round-num 0` validation still rejects**: the validator block at the top of the script (`(( ROUND_NUM > 0 )) || exit 2`) is unchanged. Operators passing `--round-num 0` still get an exit 2 with the same error message.
- **Non-default `--panel` value**: the existing `--panel hard|simple` validation gate (`[[ "$PANEL" == "hard" || "$PANEL" == "simple" ]]`) is unchanged. Both branches set the same `STATIC_INTENDED_SLOTS=6` after the fix.
- **`--launched-slots` higher than 6**: arithmetic now produces a negative `NEVER_LAUNCHED` which the existing `(( NEVER_LAUNCHED < 0 )) && NEVER_LAUNCHED=0` guard already clamps to zero. No new behavior. The `dynamic_hard` test case (`--launched-slots 16`) exercises exactly this path.
- **Empty collector results file with non-zero `--launched-slots`**: NEVER_LAUNCHED contributes the only failures; threshold math uses the flat denominator. `both_down` test case exercises this with `--launched-slots 0` after fix; the symmetric `--launched-slots 6` case (6 OK records, no never-launched) is exercised by `never_launched`.

## Failure modes

1. **CI breaks on `make test-check-reviewer-failure-threshold` after the .sh edit lands without the test update**: the four broken assertions trip on the first run. Earliest signal: the harness's labeled `FAIL ...` lines. Mitigation: include all three file edits in a single commit; do not split.
2. **review-core.sh caller observes a behavior shift mid-flight**: not possible — both pre- and post-fix code emit the same `INTENDED_SLOTS`/`FAILED_SLOTS`/`THRESHOLD_OK` KV contract; review-core only reads `THRESHOLD_OK` from the output. The behavior shift is intentional and corrects the bug.
3. **Drift between the inline `# Threshold: >50% ...` comment and the doc table**: if the comment update is omitted, the .md doc and the .sh inline comment will disagree. Mitigation: the plan lists both update locations together.

## Testing strategy

- Re-run the existing harness via `make test-check-reviewer-failure-threshold` (or directly `bash skills/review/scripts/test-check-reviewer-failure-threshold.sh`) after editing all three files. Expect all assertions to PASS.
- Re-run `make lint` (which exercises `scripts/relevant-checks.sh` / pre-commit hooks repo-wide) to confirm `bash32` and structure checks still pass.
- No new test case is needed: the existing harness already exercises the post-fix code paths (zero `NEVER_LAUNCHED`, flat denominator, dynamic-slot exclusion) — the four updated cases verify the new flat-denominator math and the round2_* cases continue to assert flat-denominator behavior on the dead `--round-num 2` path.


## Acceptance

- `bash skills/review/scripts/test-check-reviewer-failure-threshold.sh` exits 0 with all assertions PASS, including the four updated cases (half_fail_hard, never_launched, both_down, dynamic_hard) and the unchanged round2_* cases.
- `bash scripts/relevant-checks.sh` (or `make lint`) exits 0 (bash32 / structure / lint-foreground-markers / markdownlint all clean).
- Inspecting `skills/review/scripts/check-reviewer-failure-threshold.sh`, `grep STATIC_INTENDED_SLOTS` returns exactly one assignment line `STATIC_INTENDED_SLOTS=6` (no case statement, no round-aware if/else block); the `--round-num` flag parsing and `ROUND_NUM` validation are preserved verbatim per the issue body directive.
- `skills/review/scripts/check-reviewer-failure-threshold.md` no longer contains the literal tokens `12 (HARD)`, `7 (SIMPLE)`, `HARD=12`, or `SIMPLE=7`; the Threshold section reflects the 6-slot flat denominator.
- `skills/review/scripts/test-check-reviewer-failure-threshold.md` Coverage bullets no longer contain `(12-slot)` or `(7-slot)` qualifiers, and the both-down bullet reads "6 counted as failures" (not "all 12").

diff_lines: 25
