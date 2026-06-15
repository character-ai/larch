# Review Round 1

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_7: Live `review-design-step3-loop.sh` edits not reflected in embedded legacy asset
- **Reviewer(s)**: dyn-step3-timing-output.txt
- **Severity**: important
- **Concern**: Item 5 edits `skills/design/scripts/review-design-step3-loop.sh`, but production Step 3 materializes that script from the gzip entry in `python/plan_review.py` `_LEGACY_ASSETS` because it is listed in `_RETIRE_DESIGN_SKIPS`. The on-disk file changed without regenerating the embedded blob, so `plan-review run` still executes stale loop code and resumed-phase timing on `panel-failed` / `awaiting-continuation` keeps using loop-local `round_start_s`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step3-timing-output.txt: Regenerate the `review-design-step3-loop.sh` blob in `python/plan_review.py` `_LEGACY_ASSETS` from the updated source (same cutover contract as `docs/python-migration.md` C3a1), and add a harness assertion that the embedded asset matches the live script or that resumed-phase timing tests exercise `plan-review run --mode loop` rather than grep-only checks on the retired path.


