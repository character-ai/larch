## Goal
Implement issue #4911: [IMPLEMENTING] [BUG] #4891 deferred tail: implement-launcher site + review_pipeline parity.

## Implementation Plan
[BUG] #4891 deferred tail: implement-launcher site + review_pipeline parity

Follow-up to #4891 (which combined #4886 + #4888). During `/design` of #4891, the plan-review panel accepted two `[SCOPE-REDUCTION]` findings that deferred two items out of that PR to keep it surgical. The operator approved the narrower #4891 scope and asked for this follow-up so the deferred work is not lost. Two distinct deferred items:

## Deferred item 1 (from #4888): `_append_implement_launch_failure` hardcoded site "2"

`python/agents.py::_append_implement_launch_failure` is the `/implement` Step 2 *implement* launcher failure logger (distinct from the reviewer-launch logger that #4891 fixed). It still hardcodes the failure site:

- `python/agents.py:4931` passes `--site "2"` to `run-log append-failure`.
- `python/agents.py:4938` passes `site=f"2 {tool}-implement"` to `_append_vendor_failure_diagnostics`.

#4891 generalized only the reviewer-launch site (`"review Step 2"` -> caller-derived via a new `agent launch-review --site` arg). Normalize `"2"` -> `"implement Step 2"` for both call sites so `/implement` Step 2 launch failures carry a descriptive, caller-consistent site label in `execution-issues.md`.

- Add a regression assertion pinning the new label in `python/test_implement_dispatch.py` (or `python/test_agents.py`) per `.claude/rules/launcher-argv-test-coverage.md`.
- Check Codex/Cursor launcher parity per `.claude/rules/external-tool-launcher-parity.md`.

## Deferred item 2 (from #4886): `review_pipeline.py` no-issues sentinel parity

#4891 fixed the shared collect-time validator (`python/research_eval.py::validate_structured_reviewer_output`) and the Cursor launch normalizer (`python/agents.py::_review_cursor_normalize_no_issues`) so a clean no-issues reviewer is recovered when narration precedes the `{"no_issues_found": true}` sentinel. The `/review` + `/implement` review-collection path in `python/review_pipeline.py` (`_parse_output`, `_file_has_no_findings_sentinel`, `collect_findings`) was explicitly NOT broadened in #4891, to avoid regressing unrelated `/review` markdown parsing.

Result: the cited `/design` Step 3 `NOT_SUBSTANTIVE` bug is fixed (covered by `research_eval.py` via `collect_results._validate_structured`), but the `/review` and `/implement` collection path keeps the leading-only sentinel limitation as a latent surface.

- Broaden `_file_has_no_findings_sentinel` to recognize a standalone JSON sentinel line after prose (do NOT accept inline JSON embedded in prose), reusing the #4891 helpers where practical.
- Add `python/test_review_pipeline.py` coverage.
- Prioritize if a live `/review` or `/implement` collision is filed; otherwise proactive parity.

## Affected files

- `python/agents.py` (item 1)
- `python/review_pipeline.py` (item 2)
- `python/test_implement_dispatch.py` or `python/test_agents.py` (item 1 tests)
- `python/test_review_pipeline.py` (item 2 tests)

## Severity

Low. Both are deferred cleanups; the primary #4891 bugs are fixed in that PR. This issue exists so the deferred scope is tracked rather than lost.

## Test plan
(no test plan section in plan-file)
