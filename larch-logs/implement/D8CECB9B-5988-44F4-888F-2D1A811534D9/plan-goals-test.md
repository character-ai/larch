## Goal
Implement issue #6604: [IMPLEMENTING] [BUG] /analyze-bugs is blind to fixed bugs: [BUG] title match is prefix-only and case-sensitive, so [DONE] [BUG] and [Bug] titles are never selected.

## Implementation Plan
## Summary

`/analyze-bugs` exists to verify that closed bug fixes landed, but its selection predicate `_bug_title` is `title.lstrip().startswith("[BUG]")` (`python/larch/issue/analyze_bugs.py:310`). The repo convention retitles fixed issues to `[DONE] [BUG] ...`, and terminal-failure reports use `[Bug]`. Both fail the predicate. The audit funnel silently skips most of its target population.

## Evidence

- `python/larch/issue/analyze_bugs.py:34`: `BUG_PREFIX: Final = "[BUG]"`. Lines 310-311: `def _bug_title(title): return title.lstrip().startswith(BUG_PREFIX)`.
- Run 1783495808 (2026-07-08, character-ai/larch): `BUGS_REQUESTED=200 BUGS_SELECTED=32`. None of the 2026-07-07/08 bug-fix wave (#6576, #6577, #6578, #6579, #6580, #6590, #6506, #6508, #6521; all titled `[DONE] [BUG] ...` or `[DONE] [Bug] ...`) was selected, and none appears in the run ledger.
- The 7 issues that did reach triage in that run all had bare `[BUG]` prefixes (#6498, #6494, #4431, #4397, #3899, #3875, #3102).
- Case gap: `[Bug]` terminal-failure reports (for example #6580, #6591) would not match even without a lifecycle prefix.

## Expected behavior

The newest-N selection covers closed bug issues regardless of lifecycle retitling and case. `[DONE]`-retitled bugs are exactly the fixed-bug population the tool verifies.

## Observed behavior

Selection covers only never-retitled `[BUG]`-prefixed issues. The audit skews toward old or abnormally-closed bugs, and recent fixed waves are invisible.

## Suggested fix

Normalize the title before matching. Strip known leading lifecycle prefixes (`[DONE]`, `[DESIGNED]`, `[IMPLEMENTING]`, `[STALLED]`) and compare case-insensitively against `[BUG]`. Keep prefix anchoring; do not match `[BUG]` anywhere in the title, to avoid pulling in issues that merely mention bugs.

Add unit tests for `[DONE] [BUG] x`, `[Bug] x`, `[DONE] [Bug] x`, and a negative for a title that mentions `[BUG]` mid-string.

Update the `-n` flag prose in the analyze-bugs skill ("newest `[BUG]` title-prefix issues") to describe the normalized match.

## Severity

Tool-coverage bug with no runtime impact, but it undermines `/analyze-bugs` verdict completeness. The 2026-07-08 audit had to verify the recent fixed wave by hand.

## Affected files

- `python/larch/issue/analyze_bugs.py`
- analyze-bugs tests under `python/tests/`
- `.claude/skills/analyze-bugs/SKILL.md`

## Test plan
(no test plan section in plan-file)
