# Review Round 1

- Mode: `diff`
- 1 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_8: Straggler handling can excuse dropped `generalist` in rounds 1–2
- **Reviewer(s)**: dyn-dyn-static-coverage-output.txt
- **Severity**: blocking
- **Concern**: Straggler handling in `python/review_pipeline.py:1862-1912` can let rounds 1–2 proceed without the new generic Codex reviewer. `_dropped_static_output_base` skips `straggler-dropped` lines, so a dropped `generalist` row does not increment `FAILED_SLOTS` / `DROPPED_STATIC_SLOTS`. `_straggler_excused_static_slugs` then removes `generalist` from the `_static_coverage_reason` missing set. With the generic row now always present in rounds 1–2 manifests, a straggler-cut `generalist` is treated like an excused specialist: the panel can pass threshold and static-coverage gates even though GPT 5.5 generic review never completed. That weakens the branch's core "unconditional rounds 1–2 generic Codex" contract beyond ordinary `collector-failure` drops (which are covered).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-static-coverage-output.txt: Do not excuse `generalist` in `_straggler_excused_static_slugs` when the manifest contains a generic Codex row (or pass `round_num` into `_static_coverage_reason` and require `generalist` success in rounds 1–2). Optionally map `generalist` + `straggler-dropped` to a real failure in `_dropped_static_output_base`. Add a review-core or threshold test with a straggler-dropped `generalist` line.


