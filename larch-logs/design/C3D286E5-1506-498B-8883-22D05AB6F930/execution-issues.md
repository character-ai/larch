### External Reviewer Issues

- **Step design Step 3 — run-step3-review.sh -> plan-review-loop.sh (--convergence-threshold) failed (exit 2)**:
  ```
Step 3 plan-review panel-failed: plan-review-loop.sh rejected --convergence-threshold.
Root cause: run-step3-review.sh:210 unconditionally forwards --convergence-threshold to
plan-review-loop.sh, whose argv parser (line 89) rejects unknown options with exit 2.
Cache and working tree are byte-identical (larch 47.0.19 @ HEAD 12677a01e); the #3243
(relaxed single-round convergence, removed --convergence-threshold) and #3244 (extracted
run-step3-review.sh, still passes it) interaction left the driver/loop argv contract drifted.
Inner loop quiet log verbatim:
plan-review-loop.sh: unknown option: --convergence-threshold
Usage: plan-review-loop.sh --design-tmpdir DIR --plan-file PATH [--feature-file PATH] [--round-num N] [--round-cap N] --codex-present true|false --cursor-present true|false [--timeout SEC] [--help]
  ```
