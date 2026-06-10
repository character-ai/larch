# test-emit-design-plan-preview.sh

Offline regression harness for `emit-design-plan-preview.sh`.

Exercises Step 3 / Gate C preview rendering, threshold-driven summary mode, and warning paths for missing design artifacts.

Additional summary-freshness coverage:

- large plans with non-empty `plan-summary.md` use the generated summary only when the summary mtime is greater than or equal to `plan.txt`'s mtime;
- stale generated summaries fall back to the synthetic title/outline renderer;
- missing or empty generated summaries fall back to the synthetic title/outline renderer;
- small plans print the full plan body and ignore any generated summary;
- threshold normalization remains unchanged, including invalid/zero fallback to the default threshold.
