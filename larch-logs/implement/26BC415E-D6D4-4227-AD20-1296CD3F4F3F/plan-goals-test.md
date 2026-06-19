## Goal
Implement issue #4780: [IMPLEMENTING] [port-drift] [BUG] redact.py submodule-path review-finding scrubber misses bold and exact-directory references.

## Implementation Plan
## Summary

`python/cli.py redact scrub-submodule-paths` (ported from `scrub-submodule-paths.sh` in #3672) no longer drops accepted review findings that point at a submodule directory unless the path has a trailing slash, and its primary label match is effectively dead against real findings. Submodule-targeted findings then reach the `review-and-fix` coder. Integration-safety regression (not a secret leak); mitigated downstream. Found by the post-#4766 migration-wave audit (confirmed by differential test against the recovered bash).

## Root cause

`python/redact.py` `scrub_submodule_paths` (around L552-556) matches a finding block to a submodule with:

- a label regex anchored `^(Location|File):` — but production findings use markdown-bold `- **Location**:` / `- **File**:`, so this branch never matches real blocks; and
- an inline regex that requires a trailing `/` after the submodule path.

The recovered bash matched via exact-equality (`"$submodule_path"|"$submodule_path"/*`), so a bare `vendor/foo` (or `vendor/foo:120`) was dropped.

## Evidence

- `python/redact.py:553-556` — the `^(Location|File):` anchor and the trailing-slash-only inline match.
- Production finding shape uses `- **Location**:` (e.g. `python/plan_review_round.py` ~L105/L114; `skills/design/references/plan-review.md`).
- Differential test (fresh repo, `.gitmodules path = vendor/libfoo`): bash dropped `vendor/libfoo:120` + `vendor/libfoo` + `vendor/libfoo/src/x.py` (3); Python dropped only the third (1).
- Downstream mitigation: `skills/review-and-fix/SKILL.md` coder prompt forbids submodule paths and the review-and-fix path reverts post-dispatch submodule changes — hence severity medium, not high.

## Affected files

- `python/redact.py` (`scrub_submodule_paths`).
- `python/test_redact.py` — add cases for bold-label and exact-dir (no-slash, `:line` suffix) references.

## Suggested fix

Anchor the label match to the actual markdown-bold `- **Location**:` / `- **File**:` form, and add an exact-directory branch alongside the trailing-slash inline match (e.g. match `{sub}` followed by `/`, `:`, or end-of-token). Cover both shapes in the harness.

## Test plan
(no test plan section in plan-file)
