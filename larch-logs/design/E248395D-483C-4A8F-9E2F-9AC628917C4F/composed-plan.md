## Plan

## Approach

- Keep the change narrow.
- Make `review-and-fix write-self-review-tally` derive counts after validating `--implement-tmpdir`.
- Remove `--accepted` and `--rejected` from the self-review launcher in `skills/implement/SKILL.md`.
- Update `docs/run-logs.md` so the canonical self-review tally contract matches the new CLI behavior (artifact-derived counts, no count flags).
- Update tests to assert the new contract: the prompt no longer asks the orchestrator to count or pass literals.

## Files to modify/create

### UPDATED: python/review_and_fix.py

- Add a small private helper near existing count helpers:
  - Count matching lines in a file.
  - Return `0` when the file is missing, empty, or absent.
  - Use `re.MULTILINE`.
- Derive:
  - accepted from `implement_tmpdir / "self-review-accepted.md"` with `^### \[Code Review\] Self-review accepted`
  - rejected from `implement_tmpdir / "rejected-findings.md"` with `^### \[Code Review\] Self-review$`
- Remove `parser.add_argument("--accepted", ...)` and `parser.add_argument("--rejected", ...)`.
- Remove `_non_negative_int()` parsing from this verb.
- Keep `--implement-tmpdir` and `--run-id` validation behavior.
- Pass the derived integers to `voting write-tally`.

### UPDATED: skills/implement/SKILL.md

- Delete item 8.5, or fold it into item 9 as a short note that the CLI reconciles self-review counts from durable artifacts.
- Update the Step 9 fence to:
  - `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py review-and-fix write-self-review-tally --implement-tmpdir "$IMPLEMENT_TMPDIR" --run-id "$RUN_ID"`
- Remove the prose that tells the LLM to `grep -c`, substitute integer literals, or avoid memory from earlier Bash calls.
- Do not alter unrelated Step 5 self-review instructions for recording accepted and rejected findings.

### UPDATED: docs/run-logs.md

- In the `mode: self-review` paragraph under the code-review tally envelope section (currently lines 349–358):
  - Keep the durable-artifact paths and heading contracts for `self-review-accepted.md` and `rejected-findings.md`.
  - Replace prose that says counts are "passed to `review-and-fix write-self-review-tally` via `--accepted`" / "via `--rejected`" and "come from the Step 5 CLI flags at tally write time".
  - State that `write-self-review-tally` reads those two files under `--implement-tmpdir` and derives `accepted_count` / `rejected_count` internally (missing or empty file → `0`).
  - Retain the existing note that self-review tally counters are not derived from `review-findings-full.jsonl` and that JSONL may remain an empty sentinel for self-review runs.

### UPDATED: python/test_review_and_fix.py

- Update `test_write_self_review_tally_emits_step5_artifacts` to omit `--accepted` and `--rejected`.
- Update `test_write_self_review_tally_nonzero_counts`:
  - Write two accepted headings to `self-review-accepted.md`.
  - Write one exact rejected heading to `rejected-findings.md`.
  - Call the verb without count flags.
  - Assert `accepted_count == 2` and `rejected_count == 1`.
- Add or adjust coverage for missing files producing `0`.
- Update `test_self_review_prompt_reconciles_tally_counts_from_artifacts`:
  - Assert the self-review section no longer contains `grep -c`, `<ACCEPTED_COUNT>`, `<REJECTED_COUNT>`, or `--accepted`.
  - Assert the launcher still calls `write-self-review-tally`.
  - Assert the section still names the durable artifacts where findings are recorded.

## Edge cases

- Missing `self-review-accepted.md` counts as `0`.
- Missing `rejected-findings.md` counts as `0`.
- Empty files count as `0`.
- Accepted headings with suffix text still count, matching the current prefix contract.
- Rejected headings count only when the line is exactly `### [Code Review] Self-review`.

## Failure modes

- If `--implement-tmpdir` is not a directory, keep returning `2`.
- If `--run-id` is empty, keep returning `2`.
- If downstream run-log writes fail, keep the current best-effort warning and return `0`.

## Testing strategy

- Run `python3 -m pytest python/test_review_and_fix.py -k 'write_self_review_tally or self_review_prompt_reconciles_tally_counts_from_artifacts'`.
- Run `make py-test`.
- Run `make py-lint`.
- Run `make lint`.

diff_added: 55
diff_deleted: 45
mechanical_churn: false
diff_lines: 100

## Acceptance

- `write-self-review-tally` derives both counts internally from `self-review-accepted.md` and `rejected-findings.md` (missing → 0).
- The SKILL.md prose that asks the LLM to `grep -c` and thread literals is removed.

review_status: ok
rounds_completed: 2
diff_lines: 100
