# scripts/test-render-final-summary-bash32.sh - contract

`scripts/test-render-final-summary-bash32.sh` is the regression harness for the Bash 3.2 empty-array nounset hazard in `skills/design/scripts/render-final-summary.sh` (issue #3039). The subject owns the runtime behavior; this script is a Makefile-only harness wired through the `test-render-final-summary-bash32` target and the `test-harnesses-14` shard.

The harness has two layers:

1. Static grep, always run. It pins the `${COST_ARGS[@]+"${COST_ARGS[@]}"}` copy into `render_cost_args` and the single-line `render-run-summary.sh` invocation that expands both `render_cost_args` and `note_args` with the Bash 3.2-safe `${ARR[@]+"${ARR[@]}"}` idiom.
2. Dynamic fixture, only under `/bin/bash` versions older than 4.4. It creates a minimal `$DESIGN_TMPDIR`, runs `render-final-summary.sh --outcome approved --mode SIMPLE --post-publish-only` with `ISSUE_NUMBER=""`, and asserts `final-summary.md` is non-empty, the redirected renderer stderr does not contain `unbound variable`, and no `render-run-summary` warning was appended to `execution-issues.md`.

The dynamic check intentionally greps `$DESIGN_TMPDIR/render-final-summary.stderr.log`, not only the harness stderr. `render-final-summary.sh` redirects the renderer's stderr there, and the self-composed fallback can otherwise mask the original Bash 3.2 failure by still writing a summary body.

The script is excluded in `agent-lint.toml` because agent-lint does not follow Makefile target reachability. Keep this contract, the Makefile target, the `test-harnesses-14` membership, and the exclude entry in sync when renaming or moving the harness.
