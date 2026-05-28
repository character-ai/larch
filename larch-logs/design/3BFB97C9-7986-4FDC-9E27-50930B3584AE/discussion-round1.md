## Decision 1: Fix scope
- **Question**: Should the design only modify `_run_post_apply_pipeline`, audit other `in_fence` sites, or fix all of them?
- **Resolution**: Limit fix to `_run_post_apply_pipeline` in `plan-review-loop.sh` plus a focused regression test in `test-plan-review-loop.sh`. Other `in_fence` toggle sites (`write-tally.sh`, `oos-serialize.sh`, `render-findings-batch.sh`, `lint-bare-grep-probe.sh`) are out of scope; if they ever surface a similar bug, file separately.
- **Source**: user

## Decision 2: Fix shape
- **Question**: Which fix shape inside the Python heredoc?
- **Resolution**: Two-pass: first pass precomputes the set of line indices truly inside a balanced fence (opener with matching closer); unmatched openers are treated as text. Second pass runs the existing dedup logic using that precomputed in-fence set instead of stateful toggling.
- **Source**: user
