## Goal
Implement issue #5637: [IMPLEMENTING] [BUG] Plan-review drops all findings when Claude voter fails transiently despite Codex+Cursor both voting.

## Implementation Plan
## Plan

## Approach

- Keep the fix narrow.
- Treat voter dispatch as usable when `effective > 0`.
- Keep failing closed when no voter produced substantive output.
- Preserve degraded-panel visibility for downstream round classification.

## Files to modify/create

### UPDATED: python/larch/review/plan_review_panel.py

- In the full-panel `dispatch_voters` path, replace the Claude-only gate:
  - from `voter_1_status == "failed"`
  - to `effective > 0`
- Emit `DEGRADED_PANEL=1` when `effective < _PLAN_VOTER_PANEL_SIZE`.
- Emit `DEGRADED_PANEL=0` otherwise, unless existing nearby wire conventions make omission safer.
- Keep `DEGRADED_PANEL_WARNING` output unchanged.
- Keep failed voters marked `failed` so `plan_review_round.py` only passes available voter files to `plan-review tally`.
- Return `0` when `DISPATCH_OK=true`.
- Return `1` when `DISPATCH_OK=false`.

### UPDATED: python/test_plan_review_panel.py

- Add a regression test for full-panel voter dispatch:
  - Claude voter output is absent or empty.
  - Codex and Cursor voter outputs are non-empty.
  - Parse-rate checks return substantive status for Codex and Cursor.
  - `effective-judges` returns `2`.
- Assert:
  - return code is `0`
  - `VOTER_1_STATUS=failed`
  - `VOTER_2_STATUS=launched`
  - `VOTER_3_STATUS=launched`
  - `DEGRADED_PANEL_WARNING=` is present
  - `DEGRADED_PANEL=1` is present if implemented
  - `DISPATCH_OK=true`
  - `plan-review-voter-paths.txt` contains only Codex and Cursor paths
- Use existing monkeypatch patterns in nearby voter-dispatch tests.
- Avoid invoking real Claude, Codex, or Cursor.

### UPDATED: python/test_plan_review_round.py

- Add a regression test for `execute_round` with a degraded but usable voter dispatch:
  - `plan-review voter-dispatch` returns code `0`
  - `DISPATCH_OK=true`
  - `DEGRADED_PANEL=1`
  - voter 1 is failed
  - voters 2 and 3 are launched
- Assert:
  - `plan-review tally` is called
  - tally argv includes voters 2 and 3
  - tally argv does not include voter 1
  - accepted findings can flow through to `ACCEPTED_COUNT`
  - `LOOP_STATUS` is not `panel-failed`

## Edge cases

- **Only Claude succeeds:** `effective == 1`, dispatch remains OK.
- **Only Codex or Cursor succeeds:** `effective == 1`, dispatch is OK and degraded.
- **All voters fail or are non-substantive:** `effective == 0`, dispatch fails and Step 3 remains fail-closed.
- **A voter file exists but parse-rate returns `NOT_SUBSTANTIVE`:** status stays `failed`, and the tally excludes that voter.

## Failure modes

- If `DEGRADED_PANEL` is not emitted for partial panels, the round may look clean even though a voter failed.
- If `DISPATCH_OK` is based on any raw launched status instead of `effective`, non-substantive output may incorrectly pass dispatch.
- If round tests only check `DISPATCH_OK`, they may miss a regression where the failed Claude voter is still included in tally args.

## Testing strategy

- Run focused tests:
  - `python3 -m pytest python/test_plan_review_panel.py -q -k voter_dispatch`
  - `python3 -m pytest python/test_plan_review_round.py -q -k degraded`
- Run broader Python checks if available:
  - `make py-test`
  - `make py-lint`
- If dependency availability blocks broad checks, report the skipped command and the missing dependency.

## Acceptance

- Run focused tests:
  - `python3 -m pytest python/test_plan_review_panel.py -q -k voter_dispatch`
  - `python3 -m pytest python/test_plan_review_round.py -q -k degraded`
- Run broader Python checks if available:
  - `make py-test`
  - `make py-lint`
- If dependency availability blocks broad checks, report the skipped command and the missing dependency.

diff_added: 90
diff_deleted: 3
mechanical_churn: false
diff_lines: 93

## Test plan
(no test plan section in plan-file)
