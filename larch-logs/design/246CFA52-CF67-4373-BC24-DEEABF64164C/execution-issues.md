### Tool Failures

- **Step design Step 3 — run-step3-review.sh -> plan-review-loop.sh (--convergence-threshold drift) failed (exit 2)**:
  ```
Step 3 plan-review panel FAILED — larch driver contract drift (v47.0.19, HEAD 12677a01e).

plan-review-loop.sh emitted: "unknown option: --convergence-threshold" (exit 2).
run-step3-review.sh:210 passes --convergence-threshold to plan-review-loop.sh,
but plan-review-loop.sh (usage line 40, unknown-option line 89) does not accept it.
Accepted loop flags: --design-tmpdir --plan-file --feature-file --round-num --round-cap --codex-present --cursor-present --timeout --help.

Effect: LOOP_STATUS=panel-failed; NO reviewers launched; plan.txt was NOT reviewed.
Scope: deterministic, repo-wide — affects every /design run at this version (externals Cursor+Codex are both healthy).
Likely cause: #3244 (extract run-step3-review driver) + #3243 (relax convergence) left the --convergence-threshold flag on the driver but removed it from the loop.
  ```

### Warnings

- **Step dispatch-plan-voters.sh cursor — launch-review.sh --tool cursor (voter parse-rate check) warning (exit 0)**:
  ```
slot=3
voter_tool=cursor
judge_error_count=4
total_findings=4
total_ballot_items=4
voter_file=<TMPDIR>/cursor-vote-output.txt
voter_sha256=f020b4c5010a72e9ed7c8e3f953c8649325b7f386523d3dbf8ea1edaca8d9d9d
--- first 200 bytes of voter output ---
CURSOR_DEGRADED_RESPONSE

  ```

- **Step design Step 3 (degraded panel + plan-size override) — plan-review-loop.sh (codex usage-limit; cursor degraded; operator override) failed (exit 0)**:
  ```
Step 3 plan-review ran DEGRADED (1/3 effective judges) via direct plan-review-loop.sh workaround for bug #3275.

Codex (10 reviewers + voter): OpenAI usage limit — "You've hit your usage limit ... try again at 1:22 PM"; codex exec exit 1, 0 bytes. The trailing "codex_core::session: failed to record rollout items: thread not found" is a post-abort teardown artifact, not the cause. Reproduced in an isolated single-invocation probe.
Cursor voter: returned a degraded/empty .result (outputTokens>1000, result<500 bytes, no sentinel) -> launch-review.sh promoted to CURSOR_DEGRADED_RESPONSE -> 4/4 ballot items JUDGE_ERROR -> NOT_SUBSTANTIVE. Cursor reviewers (5) earlier in the run succeeded, so this was a transient degraded episode, not an outage.
Effective panel: Claude voter only. 4 important findings accepted (binding-single-judge) and auto-applied to plan.txt.
Plan-size hard trigger (DIFF_ADDED=2080>2000) fired post-apply; operator chose OVERRIDE AND CONTINUE (proceed past the hard gate).
  ```
