## Plan

This is a SIMPLE-tier bug fix: an unclosed code fence in `plan.txt` currently makes the post-apply dedup pipeline treat the rest of the file as inside a fence, which silently disables `## Constraints` duplicate-preservation. Fix the Python heredoc inside `_run_post_apply_pipeline` to derive in-fence membership from balanced opener/closer pairs only, harden the surrounding shell wrapper against a silently-empty `dedup_removed`, and add one focused regression test plus the stdout-protocol assertion the panel called out.

## Files to modify/create

### UPDATED: `skills/design/scripts/plan-review-loop.sh`

Inside the Python heredoc in `_run_post_apply_pipeline` (the `python3 - "$plan_path" "$dedup_tmp" <<'PY' ... PY` block):

- Replace the stateful single-pass walk that toggles `in_fence` inside `update_section_state` with a two-pass approach over the file lines.
- Read the file once into a list `lines`. Pass 1: iterate with index `i`. Track a single-slot stack: when the stack is empty and the current line is a fence-marker (matches the existing `^(\x60{3,})(.*)$` regex), push `(i, ticks)` onto the stack (this records a candidate opener). When the stack is non-empty and the current line is a fence-marker, attempt to close: if `ticks >= top.ticks` and the suffix is empty, pop the stack and add every line index strictly between `top.i + 1` and `i - 1` (inclusive) to a set `in_fence_lines`; otherwise the line is a failed closer attempt and is treated as plain text (the stack stays as it was). At EOF, if the stack is non-empty the single remaining opener is dropped — its content was already iterated as plain-text because nothing was added to `in_fence_lines`.
- The "push only when the stack is empty" rule preserves the original toggle's semantics (the original code's `if not in_fence: open` only opened a fresh fence). It means there is never more than one stack entry at a time; a later candidate-opener arriving while the stack is non-empty is treated as a failed-closer attempt against the existing top per the existing closer rule.
- Pass 2: iterate `lines` again with a 0-based index `i`. Split the existing `update_section_state(line)` into two parts: keep the heading state-machine portion (`inside_constraints` / `constraints_level` updates), but consult `i in in_fence_lines` instead of mutating an `in_fence` flag. Drop `fence_len` and the toggle from `update_section_state`.
- Heading reset rule (`if m and not in_fence: prev_key = None`) and the protected-line rule (`protected = inside_constraints and not in_fence`) both consume the precomputed lookup.
- Do not change the balanced-fence closer rule (a closer needs `ticks >= fence_len` and an empty suffix). The pass-1 stack uses the same rule, so balanced fences continue to delimit exactly the same line indices.
- Do not change the surrounding shell wrapper's `mktemp` dest, the `mv -f`, the `ACTION=EMIT_PLAN` driver call, or the validator dispatch. The Python's stdout still prints the integer `removed` count consumed by `${dedup_removed:-0}`.
- Keep the test-extractor invariant: do not introduce a top-level `}` line inside the function body — the awk range `/^_run_post_apply_pipeline\(\)/,/^}$/` in `test-plan-review-loop.sh` would otherwise truncate early.

Around the Python invocation in `_run_post_apply_pipeline`, harden the shell wrapper to fail loudly instead of silently coercing an empty `dedup_removed` to `0`:

- Capture the Python rc explicitly. The current `dedup_removed=$(python3 - ... <<'PY' ... PY)` runs inside a command substitution, which masks `set -e` on this caller path because `_run_post_apply_pipeline` is invoked under `if ! _run_post_apply_pipeline ...`. Today a Python `SyntaxError` would leave `dedup_removed` empty and `${dedup_removed:-0}` would coerce it to `0`, masking the failure as "dedup-sweep: removed 0 duplicate line(s) from plan.txt".
- After the command substitution, validate `dedup_removed` against `^[0-9]+$`. If empty or non-numeric, do **not** run `mv -f "$dedup_tmp" "$plan_path"`. Instead `rm -f "$dedup_tmp"`, optionally restore `$plan_backup` if it exists, set `LOOP_STATUS=emit-plan-failed` and `LOOP_REASON=dedup-python-failed`, and `return 1`. Match the existing `emit-plan-failed` rollback shape used a few lines below in the same function so callers do not need a new branch.
- Document the wrapper guard with a one-line comment naming the invariant ("dedup_removed must be a non-negative integer; empty means the Python pass failed").

### UPDATED: `skills/design/scripts/test-plan-review-loop.sh`

Add one new test case immediately before the trailing `printf '%s\n' "test-plan-review-loop: ok"` line, after the existing `=== post-apply: section-aware duplicate-line dedup ===` case:

- Title: `=== post-apply: unclosed fence does not disable Constraints protection ===`.
- Allocate a fresh fixture variable for this case, for example `DUNCLOSED="$TMP/unclosed-fence"`. Use the fresh variable for both the fixture path and every later assertion. Do not reuse `$DDED` from the previous section-aware case.
- Reuse the existing `dedup-emit-driver.sh` and `dedup-validate.sh` stubs and the awk-extract pattern used by the section-aware test (no need to re-create them — they are still on disk from the prior case).
- Build a plan fixture under `$DUNCLOSED/plan.txt` with:
  - A `## Intro` section followed by a code-fence opener (the literal four-character sequence backtick-backtick-backtick-`b`, language `bash`, no leading whitespace) and one or two plain-text body lines. No closing fence line.
  - A `## Constraints` heading after the unclosed opener, followed by two identical duplicate constraint bullets.
  - A trailing `diff_lines: 1` line.
  - No removable duplicates outside the `## Constraints` section, so the dedup pass should remove exactly zero lines.
- Set `DESIGN_TMPDIR="$DUNCLOSED"`, export the stub `DESIGN_DRIVER_SH` / `INVOKE_PLAN_VALIDATOR_SH` / `CHECK_PLAN_SIZE_SH` and `CLAUDE_PLUGIN_ROOT`, source `lib-quiet.sh`, run `_run_post_apply_pipeline 1` via the same awk-extract `bash -c '...'` pattern as the section-aware test.
- Assert both:
  1. The duplicate constraint bullet survives — `grep -c '^<duplicate-constraint-line>$' "$DUNCLOSED/plan.txt"` equals `2`.
  2. The stdout protocol is preserved — the captured dedup log contains exactly the line `dedup-sweep: removed 0 duplicate line(s) from plan.txt`. Fail the test if either the count differs or extra debug output bleeds onto that line.

## Approach

The current bug is a state-machine leak: an opener flips `in_fence` to `True`, and without a closer the flag never returns to `False`, so heading detection is silenced through EOF. Replacing the toggle with a precomputed set makes the in-fence predicate a pure function of position, removing the leak.

The single-slot stack in pass 1 mirrors the original toggle's semantics: only the first opener after a fully-closed state starts a candidate fence; everything until a matching closer is plain text on the stack frame; an unmatched opener is silently dropped at EOF. Balanced fences continue to behave exactly as today.

The wrapper-guard change is independent of the in-fence fix — it makes any future Python regression loud instead of silent, and matches the existing rollback path used by `emit-plan-failed` so callers see a real `LOOP_STATUS=emit-plan-failed` rather than a phantom `removed 0`.

The dedup remains a streaming-like loop in pass 2 (read the buffered list line by line), so the `removed` count printed to stdout still matches the `dedup-sweep: removed N duplicate line(s)` shell-side log.

## Edge cases

- Empty plan: no openers, `in_fence_lines` is empty, dedup behaves as if there were no fence logic.
- Fence opener as the final line of the file: opener sits on the stack, never matches a closer, no lines added to `in_fence_lines`. Heading detection works for nothing afterward (file already ended).
- A second fence-marker line appears while the stack is non-empty: pass 1 treats it as a candidate closer per the existing rule. If it satisfies the closer rule (`ticks >= top.ticks` and empty suffix) it closes the fence; if not, it is text and the stack stays as it was. This matches the single-slot semantics of the original toggle.
- Mixed balanced and unbalanced fences: each balanced pair contributes its strictly-between range to `in_fence_lines`; any later unmatched opener after the balanced pair simply sits alone on the stack until EOF.
- Fence with language tag (the literal `python` after the opener marker): pass 1 records the line as a candidate opener but never matches a closer with a non-empty suffix, mirroring the existing rule.
- Closer with mismatched ticks: pass 1 leaves the opener on the stack until a properly sized closer arrives, mirroring the existing rule.

## Failure modes

1. **Python heredoc failure masked by command substitution.** Today a Python `SyntaxError` in the heredoc would leave `dedup_removed` empty; `${dedup_removed:-0}` would coerce to `0` and `mv -f "$dedup_tmp" "$plan_path"` would still run, replacing the plan with whatever (or nothing) the Python printed before failing. Earliest signal under current code: silent `dedup-sweep: removed 0 duplicate line(s) from plan.txt` with no further dedup happening. Mitigation: the wrapper-guard above validates `dedup_removed` matches `^[0-9]+$` and rolls back via the existing `emit-plan-failed` shape before `mv -f` runs. After the fix, a Python regression surfaces as a real `LOOP_STATUS=emit-plan-failed`.
2. **Off-by-one in the in-fence range.** Including the opener or closer line index in `in_fence_lines` would mark fence-marker lines as fence-content. Earliest signal: the existing section-aware test would not regress (fence-marker lines are not headings and are not duplicate content lines), but a hand-crafted opener-as-duplicate fixture would. Mitigation: range strictly between `top.i + 1` and `i - 1` inclusive; add a comment naming the invariant.
3. **Regression in balanced-fence dedup.** A two-pass rewrite could accidentally change the behavior of balanced fences (for example, fenced duplicates no longer collapsing). Earliest signal: the existing `=== post-apply: section-aware duplicate-line dedup ===` test fails its `fenced_count == 1` / `tagged_fenced_count == 1` / `lookalike_count == 1` assertions. Mitigation: do not touch the closer rule; run `make test-plan-review-loop` after every change.

## Testing strategy

- Add the new `=== post-apply: unclosed fence does not disable Constraints protection ===` case described above. With the current buggy code the new test should fail on the duplicate-count assertion (the duplicate collapses to 1). After the fix the new test passes both assertions: duplicate count stays 2, and the stdout protocol line `dedup-sweep: removed 0 duplicate line(s) from plan.txt` appears once and unchanged.
- Re-run the existing `=== post-apply: section-aware duplicate-line dedup ===` test to confirm balanced-fence behavior is unchanged: outside-Constraints duplicates collapse, inside-Constraints duplicates survive, fenced duplicates collapse, tagged-fenced duplicates collapse, nested-Constraints duplicates survive, the `Constraints-related notes` lookalike heading is not protected, and the existing `removed 4 duplicate line(s)` assertion still holds.
- Run `make test-plan-review-loop` and `make lint` after the edits.

## Acceptance

- The new `=== post-apply: unclosed fence does not disable Constraints protection ===` test case in `skills/design/scripts/test-plan-review-loop.sh` passes against the patched `_run_post_apply_pipeline`.
- The new test fails when run against the pre-patch `plan-review-loop.sh` (verifies the regression is actually exercised).
- The existing `=== post-apply: section-aware duplicate-line dedup ===` test still passes unchanged: `removed 4 duplicate line(s)`, outside/inside/nested/lookalike/fenced/tagged counts unchanged.
- `make test-plan-review-loop` is green; `make lint` is green.
- No other `in_fence` toggle sites are modified.

diff_lines: 115
