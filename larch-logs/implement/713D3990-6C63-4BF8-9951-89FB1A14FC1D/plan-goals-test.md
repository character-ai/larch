## Goal
Implement issue #4618: [IMPLEMENTING] [BUG] /implement --self-review tally hardcoded to 0/0 under-reports inline review.

## Implementation Plan
## Plan

## Approach

- Keep this a **tally-only fix**.
- Do **not** populate `review-findings-full.jsonl`.
- Do **not** change the external review path.
- Do **not** change `write_self_review_tally()` internals.
- Replace orchestrator mental counters with **durable tmpdir artifacts** that mirror the existing `rejected-findings.md` pattern.
- Before Step 9 tally emission, **derive integer literals from those artifacts** and substitute them into the one-line launcher fence (no shell variable persistence across Bash calls).

## Files to modify/create

### UPDATED: skills/implement/SKILL.md

**Step 5 item 4 — durable accepted-finding artifact**

- When applying each in-scope self-review fix, append **one heading per distinct finding** to `$IMPLEMENT_TMPDIR/self-review-accepted.md`.
- Use the exact heading prefix `### [Code Review] Self-review accepted` (one heading per finding, not per file/edit/commit).
- If one finding needs multiple edits, append one heading once.
- If one edit resolves multiple distinct findings, append one heading per finding.
- Create the file on first append; do not rely on mental state.
- OOS items belong in `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md` only; do not write them to `self-review-accepted.md`.

**Step 5 item 5 — rejected findings (unchanged schema, clarify count source)**

- Keep recording non-applied in-scope findings in `$IMPLEMENT_TMPDIR/rejected-findings.md` with the exact heading `### [Code Review] Self-review`.
- Missing file means rejected count `0`.

**New Step 5 item 8.5 — count reconciliation before tally**

- Insert immediately before the existing Step 9 tally fence.
- Instruct the agent to compute counts from durable artifacts (not memory):
  - **Accepted**: count lines matching `^### \[Code Review\] Self-review accepted` in `$IMPLEMENT_TMPDIR/self-review-accepted.md`; missing file → `0`.
  - **Rejected**: count lines matching `^### \[Code Review\] Self-review$` in `$IMPLEMENT_TMPDIR/rejected-findings.md`; missing file → `0`.
- Require substituting the two non-negative integer literals into the Step 9 fence before invoking Bash.
- Explicitly forbid placeholder values and forbid relying on variables from prior Bash calls.

**Step 5 item 9 — replace hardcoded tally command**

- Remove `--accepted 0 --rejected 0`.
- Show the fence with substituted integer literals, for example:
  `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py review-and-fix write-self-review-tally --implement-tmpdir "$IMPLEMENT_TMPDIR" --run-id "$RUN_ID" --accepted <ACCEPTED_COUNT> --rejected <REJECTED_COUNT>`
- Document that `<ACCEPTED_COUNT>` and `<REJECTED_COUNT>` must be replaced with the reconciled integers from item 8.5.
- Preserve the existing single-line `bash "$IMPLEMENT_TMPDIR/larch-run.sh" ...` fence shape.
- Do not add, remove, or convert Bash fences.

### UPDATED: python/test_review_and_fix.py

**Extend self-review tally writer test (non-zero inputs)**

- Add or extend a test (e.g. `test_write_self_review_tally_nonzero_counts`) calling `write_self_review_tally()` with `--accepted 2 --rejected 1`.
- Assert `code-review-tally.json` records:
  - `mode == "self-review"`
  - `rounds == 1`
  - `accepted_count == 2`
  - `rejected_count == 1`
- Assert `review-findings-full.jsonl` still exists and is empty.

**Add lightweight prompt-contract regression in the same file**

- Read `skills/implement/SKILL.md`.
- Assert the self-review tally fence no longer contains `--accepted 0 --rejected 0`.
- Assert the self-review section documents:
  - `$IMPLEMENT_TMPDIR/self-review-accepted.md`
  - accepted-count reconciliation from that file
  - rejected-count reconciliation from `$IMPLEMENT_TMPDIR/rejected-findings.md`
- Keep assertions narrow (literal removal + required terms); avoid brittle large-span prose matching.

### UPDATED: docs/run-logs.md

**Revise `code-review-tally.json` counter semantics (lines ~317–322 area)**

- Preserve the existing general rule for normal multi-round panel review: `accepted_count` and `rejected_count` remain cumulative and are derived from composed `review-findings-full.jsonl` code-review rows.
- Add an explicit **`mode: self-review` carve-out** immediately after that general rule:
  - `rounds` is always `1`.
  - `accepted_count` is the count of in-scope self-review findings fixed inline during Step 5, recorded as `### [Code Review] Self-review accepted` headings in `$IMPLEMENT_TMPDIR/self-review-accepted.md` and passed to `review-and-fix write-self-review-tally` via `--accepted`.
  - `rejected_count` is the count of self-review findings recorded under exact `### [Code Review] Self-review` headings in `$IMPLEMENT_TMPDIR/rejected-findings.md` and passed via `--rejected`.
  - For self-review runs, tally counters are **not** derived from `review-findings-full.jsonl`; they come from the Step 5 CLI flags at tally write time.
  - `review-findings-full.jsonl` may remain an empty sentinel for self-review runs (observability-only "review ran" marker).

## Edge cases

- **No findings**: no `self-review-accepted.md` and no rejected headings → accepted `0`, rejected `0`; empty JSONL still records that review ran.
- **Accepted file missing**: accepted count is `0`.
- **Rejected file missing**: rejected count is `0`.
- **Multiple edits for one finding**: one accepted heading, accepted count increments once.
- **One edit fixes multiple findings**: one accepted heading per distinct finding.
- **Wrong heading prefix**: does not count; prompt requires exact accepted/rejected heading strings.
- **OOS findings**: do not count as accepted or rejected code-review findings.

## Failure modes

- Agent applies fixes but forgets to append accepted headings.
  - Mitigate with Step 4 wording requiring append-on-fix and Step 8.5 reconciliation from `self-review-accepted.md` before tally.
- Agent runs tally fence with placeholders or stale mental counts.
  - Mitigate with Step 8.5 integer-literal substitution requirement and removal of hardcoded `0 0`.
- Docs still imply JSONL is the sole counter source for self-review.
  - Mitigate with explicit self-review carve-out under `code-review-tally.json` (FINDING_2).
- Prompt-contract test becomes brittle.
  - Keep assertions to hardcoded-literal removal and presence of artifact/count terms only.

## Testing strategy

- Run targeted tests:
  - `python3 -m pytest python/test_review_and_fix.py -k "self_review_tally or self_review"`
- Run fence-shape validation:
  - `bash scripts/test-implement-fence-shape.sh`
- Run repository checks:
  - `make lint`
- Because a Python test file changes, also run:
  - `make py-lint`
  - `make py-test`

## Acceptance

- `code-review-tally.json` records real `accepted_count` / `rejected_count` for self-review runs.
- `final-summary.md` no longer shows "0 findings" for self-review runs that applied fixes.
- The genuinely-zero case still writes a "review ran" sentinel.
- `python/test_review_and_fix.py` asserts non-zero counts flow through correctly.
- `docs/run-logs.md` documents self-review counter semantics with explicit panel/self-review carve-out.

diff_lines: 64

## Test plan
(no test plan section in plan-file)
