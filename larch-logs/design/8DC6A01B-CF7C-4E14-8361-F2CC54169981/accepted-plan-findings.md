### FINDING_2: review-design-step3-loop.sh edits require _LEGACY_ASSETS blob regeneration
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: If the plan updates on-disk `review-design-step3-loop.sh` for `write-design-round-meta` cutover but omits regenerating the gzip `_LEGACY_ASSETS` blob, production `/design` Step 3 still runs the stale embedded loop. Live Step 3 delegates through `plan_review._run_legacy()`, which skips linking on-disk `skills/design/scripts` for `review-design-step3-loop.sh` (it is in `_RETIRE_DESIGN_SKIPS`) and overwrites the materialized script from `_LEGACY_ASSETS`. Deleting `scripts/write-design-round-meta.sh` while the stale embedded loop still defaults to that path leaves the `[[ -x "$_rmd_sh" ]]` gate false and post-revise `round-meta.json` refresh silently stops.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ### UPDATED: python/plan_review.py to regenerate the embedded skills/design/scripts/review-design-step3-loop.sh asset from the edited live script per docs/python-migration.md C3a1; keep test_embedded_review_design_step3_loop_matches_live_script passing

