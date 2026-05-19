### FINDING_6: [OUT_OF_SCOPE] **correctness** — [`skills/review/scripts/dispatch-panel.sh:49`](skills/review/scripts/dispatch-panel.sh): The guard uses the raw `--review-tmpdir` string only; it does not canonicalize symlinks. A symlink whose **string** omits `test-dispatch-panel.*` / `test-review-core.*` / `test-scout-*` could still live under a harness directory on disk — low likelihood for normal callers, but the heuristic is string-based by design (pre-existing class of limitation for any path-guard; only noting because the scout notes asked about symlinks).
- **Reviewer**: dyn-harness-isolation-output.txt
- **Concern**: - **correctness** — [`skills/review/scripts/dispatch-panel.sh:49`](skills/review/scripts/dispatch-panel.sh): The guard uses the raw `--review-tmpdir` string only; it does not canonicalize symlinks. A symlink whose **string** omits `test-dispatch-panel.*` / `test-review-core.*` / `test-scout-*` could still live under a harness directory on disk — low likelihood for normal callers, but the heuristic is string-based by design (pre-existing class of limitation for any path-guard; only noting because the scout notes asked about symlinks). --- **Scout checklist notes (brief):**
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] Regression 3 uses `review-prod-shape.XXXXXX`, which does **not** match the harness globs; the subshell `EXIT` trap removes `prod_tmp` after assertions, so the outer harness does not rely on inspecting that directory afterward.
- **Reviewer**: dyn-harness-isolation-output.txt
- **Concern**: - Regression 3 uses `review-prod-shape.XXXXXX`, which does **not** match the harness globs; the subshell `EXIT` trap removes `prod_tmp` after assertions, so the outer harness does not rely on inspecting that directory afterward. **Commits (`git merge-base HEAD main`..HEAD):**   `8cbd618a` Address code review feedback (round 1)   `e929a125` Add test-tmpdir path guard to scout parse-failed logging
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 NEUTRAL=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] `*/test-dispatch-panel.*` matches when any path component is literally `test-dispatch-panel.<suffix>`; harness `TMP=$(mktemp -d …/test-dispatch-panel.XXXXXX")` makes that a **guaranteed** ancestor for nested `REVIEW_TMPDIR` values, not accidental.  
- **Reviewer**: dyn-harness-isolation-output.txt
- **Concern**: - `*/test-dispatch-panel.*` matches when any path component is literally `test-dispatch-panel.<suffix>`; harness `TMP=$(mktemp -d …/test-dispatch-panel.XXXXXX")` makes that a **guaranteed** ancestor for nested `REVIEW_TMPDIR` values, not accidental.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0 Result=rejected

