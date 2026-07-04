## Plan

## Approach

Make the smallest issue-body corrections needed to align #6261 and #5993 with the verified field criteria.

Read-only discovery in this environment confirmed the code-side premise:
- `git tag --contains 541b88803` includes `v52.4.6` and later.
- `git tag --contains 8e8f215ff` starts at `v52.4.7`.
- `python/larch/implement/ship.py` composes PR bodies without a code-review line.
- `python/larch/git/pr_body.py` renders `Code review: N/M accepted` in run-summary output.

Network access failed for `gh issue view`, so implementation must fetch the live issue bodies before editing.

## Files to modify/create

### UPDATED: github-issue-6261

Edit the issue body only.

- In Preconditions, change the qualifying build floor from `>= v52.4.6` to `>= v52.4.7`.
- In acceptance criterion A, update any matching floor text if it repeats the same precondition.
- In criterion C, require both verified render surfaces:
  - `final-summary.md`
  - the tracking-issue `<!-- larch:final-summary v1 runid=... -->` comment (not the `<!-- larch:metadata v1 runid=... -->` comment)
- Remove or correct any claim that the PR body carries `Code review: N/M accepted`.
- In the baseline contrast note, drop `rater: "fallback"` and `rater_tool: "bootstrap"`.
- Keep the true pre-#6229 markers: `audit_evaluated: null` and `rater_model: "unknown"`.

### UPDATED: github-issue-5993

Edit only mirrored close-condition text.

- Change any close-condition floor that echoes `>= v52.4.6` to `>= v52.4.7`.
- If #5993 mirrors the broader wording, prefer “a build containing both #6229 and #6259” only where it is already phrased as capability-based criteria.
- Do not expand #5993 beyond the mirrored close condition.

## Edge cases

- If #6261 or #5993 already contains part of the fix, preserve the current wording and only correct stale fragments.
- If the live body has diverged from the feature description, do not overwrite unrelated edits. Patch the current body.
- If #5993 has no mirrored floor text, leave it unchanged and note that verification result.
- Keep issue formatting stable. Avoid reflowing unrelated paragraphs.

## Failure modes

- Editing from stale local assumptions can erase issue-body changes made by others. Always read the live body first.
- Criterion C can regress if it names only `final-summary.md`; discussion resolved that both `final-summary.md` and the `larch:final-summary` tracking-issue comment are required. Do not use the `larch:metadata` comment as the second surface.
- `gh issue edit --body` can replace the whole body. Use a temp body assembled from the live content, then verify the resulting issue body.

## Testing strategy

- Run `gh issue view 6261 --json body` before editing and save the live body for comparison.
- Run `gh issue view 5993 --json body` before editing and save the live body for comparison.
- After each `gh issue edit --body`, rerun `gh issue view <issue> --json body`.
- Verify #6261 contains:
  - `>= v52.4.7`
  - no stale `>= v52.4.6` qualifying-build floor
  - criterion C names `final-summary.md`
  - criterion C names the `larch:final-summary` tracking-issue comment (not `larch:metadata`)
  - no PR-body requirement for `Code review: N/M accepted`
  - no `fallback` / `bootstrap` baseline claim
- Verify #5993 contains no mirrored stale `>= v52.4.6` close-condition floor.
- No repo tests are needed because no repo files change.

## Acceptance

- Run `gh issue view 6261 --json body` before editing and save the live body for comparison.
- Run `gh issue view 5993 --json body` before editing and save the live body for comparison.
- After each `gh issue edit --body`, rerun `gh issue view <issue> --json body`.
- Verify #6261 contains:
  - `>= v52.4.7`
  - no stale `>= v52.4.6` qualifying-build floor
  - criterion C names `final-summary.md`
  - criterion C names the `larch:final-summary` tracking-issue comment (not `larch:metadata`)
  - no PR-body requirement for `Code review: N/M accepted`
  - no `fallback` / `bootstrap` baseline claim
- Verify #5993 contains no mirrored stale `>= v52.4.6` close-condition floor.
- No repo tests are needed because no repo files change.

review_status: ok
rounds_completed: 2
difficulty: TRIVIAL
diff_lines: 8
