## Goal
Implement issue #4424: [IMPLEMENTING] [BUG] (URGENT) /implement --self-review final report shows Code review: N/A.

## Implementation Plan
## Plan

## Approach

- Emit an explicit **self-review Step 5 signal**.
- Write both Step 5 run-log artifacts for self-review:
  - `code-review-tally.json`
  - an empty `review-findings-full.jsonl`
- Keep counts conservative:
  - `accepted=0`
  - `rejected=0`
- Treat a present zero-count **code-review** tally as "review ran clean".
- Reserve `N/A` for absent, unreadable, malformed, wrong-phase, or invalid tally data.
- Keep plan-review zero-count tallies as `N/A`.
- Make self-review tally emission **best effort**.
- Do not block Step 6 if tally emission fails.
- Do not edit `python/audit_runs.py`; the self-review path will satisfy its current Step 5 detection when both Step 5 artifacts are written.

## Files to modify/create

### UPDATED: python/voting.py

- Allow `--mode self-review` only for `--phase code-review`.
- Keep existing `simple` and `hard` behavior unchanged.
- Use phase-aware validation:
  - `plan-review`: allow `simple|hard`.
  - `code-review`: allow `simple|hard|self-review`.
- Preserve `schema_version: 2`.
- Preserve the existing code-review rule that omits `body` from the JSON record.
- Keep `plan-review --mode self-review` invalid with rc `2`.

### UPDATED: python/review_and_fix.py

- Add `write_self_review_tally(argv)` as a small CLI entry point.
- Parse:
  - `--implement-tmpdir`
  - `--run-id`
  - `--accepted` default `0`
  - `--rejected` default `0`
- Validate:
  - `--implement-tmpdir` is an existing directory.
  - `--run-id` is non-empty.
  - accepted and rejected are non-negative integers.
- Write `code-review-tally.json` by calling `python/cli.py voting write-tally` with:
  - `--log-root "$IMPLEMENT_TMPDIR/larch-logs"`
  - `--skill implement`
  - `--run-id "$RUN_ID"`
  - `--phase code-review`
  - `--mode self-review`
  - `--rounds 1`
  - passed accepted and rejected values
- Also write an empty `review-findings-full.jsonl` batch through `python/cli.py run-log write`.
- Store the empty input under the existing batch-input temp area.
- Return the first non-zero writer rc.
- Do not derive exact self-review finding counts in this change.

### UPDATED: python/cli.py

- Register `("review-and-fix", "write-self-review-tally")`.
- Add the command to the review-and-fix command allowlist/help surface beside `write-rejected` and `record-round-timing`.

### UPDATED: python/pr_body.py

- Update `_derive_review_line`.
- Keep returning `N/A` when the tally file is absent, unreadable, malformed, or not a JSON object.
- Parse `accepted_count` and `rejected_count` defensively.
- Treat invalid or negative counts as malformed and return `N/A`.
- Scope zero-count review text to **code-review tallies only**:
  - require `filename == "code-review-tally.json"` and/or parsed `phase == "code-review"`.
  - for `plan-review-tally.json` or any non-code-review phase, keep zero totals as `N/A`.
- When the tally exists, is valid, is code-review scoped, and `accepted + rejected == 0`:
  - return `self-review: 0 findings` when `mode == "self-review"`.
  - return `0 findings` for other code-review modes.
- Keep the existing positive-count output format:
  - `<accepted>/<total> accepted`

### UPDATED: skills/implement/SKILL.md

- In Step 5 self-review mode, after logging `Step 5 — self-review mode: main-agent inline review complete`, add one foreground Bash fence.
- The fence must be exactly one physical command line.
- The command must start with the post-Step-0 launcher.
- Make the fence **best effort**:
  - if the tally writer exits non-zero, append a Warnings entry to `$IMPLEMENT_TMPDIR/execution-issues.md`.
  - then continue with `true`.
  - do not block Step 6 or the post-Step-5 chain.
- The command shape should be:

```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py review-and-fix write-self-review-tally --implement-tmpdir "$IMPLEMENT_TMPDIR" --run-id "$RUN_ID" --accepted 0 --rejected 0 || { printf '%s\n' '- Step 5 self-review tally emission failed; continuing with N/A fallback.' >> "$IMPLEMENT_TMPDIR/execution-issues.md"; true; }
```

- Then proceed to the existing post-Step-5 chain.
- Do not invoke the scripted review loop in self-review mode.
- Do not try to derive exact per-finding self-review counts in this change.

### UPDATED: scripts/test-implement-fence-shape.sh

- Update the expected new-shape Bash fence count because `skills/implement/SKILL.md` gains one post-Step-0 launcher fence.
- Change `EXPECTED_NEW` from `31` to `32`.
- Do not change `EXPECTED_OLD`.
- Ensure the new fence remains one physical line.

### UPDATED: python/test_pr_body.py

- Add focused tests for `_derive_review_line`:
  - absent `code-review-tally.json` returns `N/A`.
  - malformed tally returns `N/A`.
  - non-object JSON returns `N/A`.
  - invalid count values return `N/A`.
  - negative count values return `N/A`.
  - `filename: code-review-tally.json`, `phase: code-review`, `mode: self-review`, `accepted_count: 0`, `rejected_count: 0` returns `self-review: 0 findings`.
  - code-review non-self-review zero total returns `0 findings`.
  - plan-review zero total still returns `N/A`.
  - non-code-review phase zero total still returns `N/A`.
  - positive totals still return `<accepted>/<total> accepted`.

### UPDATED: python/test_voting.py

- Add a record-composition test for code-review `--mode self-review`.
- Assert the JSON contains:
  - `batch: code-review-tally`
  - `phase: code-review`
  - `mode: self-review`
  - `rounds: 1`
  - zero accepted and rejected counts
- Add a negative validation test:
  - `plan-review --mode self-review` exits with rc `2`.

### UPDATED: python/test_review_and_fix.py

- Add one focused CLI smoke test for `python/cli.py review-and-fix write-self-review-tally`.
- Invoke the command against a temp `IMPLEMENT_TMPDIR` and run id.
- Assert `larch-logs/implement/<run-id>/code-review-tally.json` exists.
- Assert the tally contains:
  - `phase: code-review`
  - `mode: self-review`
  - `rounds: 1`
  - `accepted_count: 0`
  - `rejected_count: 0`
- Assert `larch-logs/implement/<run-id>/review-findings-full.jsonl` exists.
- Assert the self-review `review-findings-full.jsonl` is empty.

## Edge cases

- **No review artifact**: final report still shows `N/A`.
- **Clean self-review**: final report shows `self-review: 0 findings`.
- **Clean scripted code review**: final report shows `0 findings` if a zero-count code-review tally exists.
- **Clean plan review stub**: final report still shows `Plan review: N/A`.
- **Bad tally JSON**: final report stays defensive and shows `N/A`.
- **Self-review run-log completeness**: self-review writes both Step 5 required run-log files when the best-effort writer succeeds.
- **Self-review tally-write failure**: Step 6 still runs, and final reporting may fall back to `N/A`.
- **Positive self-review tally in future**: existing positive-count format remains valid.

## Failure modes

- If the self-review tally writer fails, the Step 5 fence records a Warnings entry and continues.
- If the empty `review-findings-full.jsonl` write fails, run-log completeness may still report the Step 5 companion artifact missing.
- Surface command failures through the normal Bash/tool output path and the Warnings entry.
- Do not hide writer failures.
- Do not make final-summary rendering depend on `review-findings-full.jsonl`.
- Do not let observability-only tally emission block Step 6.

## Testing strategy

- Run `make py-lint`.
- Run `make py-test`.
- Run `make lint`.
- If isolating first, run:
  - `python3 -m pytest python/test_pr_body.py python/test_voting.py python/test_review_and_fix.py`
  - `bash scripts/test-implement-fence-shape.sh`

## Acceptance

review_status: partial (2 review rounds completed; session stopped by operator for re-design)
rounds_completed: 2

diff_lines: 230

## Test plan
(no test plan section in plan-file)
