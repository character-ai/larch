## Goal
Implement issue #6308: [IMPLEMENTING] [Bug] /implement terminal: TRIVIAL panel-failed because edge-cases reviewer output was non-substantive on a doc-only 4-line diff (same-cause-repeat at 5).

## Implementation Plan
## Plan

Approach synthesis is `NO_SKETCHES`. Draft from direct repo inspection.

## Approach

Fix the root validation mismatch. Review prompts can produce the canonical no-findings prose `No in-scope issues found.`, while `collect-results --substantive-validation --validation-mode` currently accepts only JSON/legacy sentinels, ballots, TSV, or 30+ cited words.

Add a narrow validation-mode fast path before the word-count check:

- Accept only exact no-findings prose shapes.
- Require a `No in-scope issues found.` line.
- Allow only known no-findings lines and section headers around it.
- Do not accept generic thin narration such as `Reading files and preparing a response.`

This makes doc-only edge-cases reviewers with no findings count as `STATUS=OK`, so the Step 5 static coverage gate no longer fails on a valid empty review.

## Files to modify/create

### UPDATED: python/larch/research/research_eval.py

- Add a small helper for validation-mode reviewer no-findings prose.
- Call it inside `validate_research_output()` before word count and citation checks.
- Keep the helper strict:
  - allow `### In-Scope Findings`
  - allow `No in-scope issues found.`
  - allow `### Out-of-Scope Observations`
  - allow `No out-of-scope observations.` and close variants only if needed by existing prompts
  - reject any other nonblank line
- Leave structured reviewer validation unchanged.

### UPDATED: python/tests/research/test_research_eval.py

- Extend `test_validation_mode_sentinels_and_thresholds` or add a focused test.
- Cover:
  - headings plus `No in-scope issues found.` returns `0`
  - a thin process/narration line still returns `2`
  - a mixed line with extra prose around the no-findings phrase still fails

### UPDATED: python/tests/agents/test_collect_results.py

- Add a collector regression test using `--substantive-validation --validation-mode`.
- Write a completed reviewer output with:
  - `### In-Scope Findings`
  - `No in-scope issues found.`
- Assert collector emits `STATUS=OK`.
- Assert no `NS_RETRY_MODE` or `NS_RETRY_REASON` fields are present.
- Assert the old thin narration case still emits `STATUS=NOT_SUBSTANTIVE`.

### UPDATED: docs/external-reviewers.md

- Update the validation-mode description.
- State that short reviewer no-findings prose from the shipped reviewer template is accepted as substantive.
- Keep the JSON sentinel as the preferred no-findings output for external reviewers.
- Note that arbitrary thin narration still fails validation.

## Edge cases

- Do not accept `No in-scope issues found, but ...`.
- Do not accept a no-findings phrase plus TSV rows or bullet findings.
- Preserve current `CURSOR_EMPTY_RESPONSE` handling.
- Preserve the citation requirement for ordinary prose.
- Preserve `NO_ISSUES_FOUND_TOO_THIN` for process chatter and other thin text.

## Failure modes

- If the matcher is too broad, empty or lazy reviewer output may pass.
- If the matcher is too narrow, the same Step 5 panel failure can recur.
- If docs imply arbitrary prose is accepted, future reviewers may rely on a path the code still rejects.

## Testing strategy

Run changed Python tests only:

- `python3 -m pytest python/tests/research/test_research_eval.py`
- `python3 -m pytest python/tests/agents/test_collect_results.py`

Run relevant checks for changed files if time permits:

- `python3 python/cli.py checks run-relevant`

## Difficulty

This is a review workflow validation change. It affects `/implement` Step 5 classification and panel threshold behavior, but the code change is narrow and covered by direct tests.

## Acceptance

Run changed Python tests only:

- `python3 -m pytest python/tests/research/test_research_eval.py`
- `python3 -m pytest python/tests/agents/test_collect_results.py`

Run relevant checks for changed files if time permits:

- `python3 python/cli.py checks run-relevant`

diff_lines: 70

## Test plan
(no test plan section in plan-file)
