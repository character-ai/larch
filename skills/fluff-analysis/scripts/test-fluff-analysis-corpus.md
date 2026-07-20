# test-fluff-analysis-corpus.sh

Smoke-check an explicitly supplied cached `implement/` corpus (when present)
passes the v49+ low-value acceptance regression: the `post nit` acc% row must
be exactly 0.0%.

## Behavior

Skips silently (exit 0) when:

- the cached `implement/` directory does not exist.
- `larch-logs/implement/` exists but contains no run directories (sparse
  checkout or empty tree).
- The analyzer produces no `post nit` row (no v≥49 post-nit slice in the
  corpus).

Fails (non-zero) when the `post nit` acc% is non-zero, indicating a
regression in the fluff-reduction rubric.

## Sparse-checkout guard

A legacy sparse Git fixture may include a `larch-logs/` directory stub but omit
the per-run contents. The script detects an empty `implement/`
subdirectory (no child directories) and skips rather than falsely passing on
an empty corpus.

## Primary

`skills/fluff-analysis/scripts/fluff-analysis.py` — the analyzer invoked by
this test.
