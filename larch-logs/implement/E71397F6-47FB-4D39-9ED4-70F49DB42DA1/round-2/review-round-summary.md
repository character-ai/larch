# Review Round 2

- Mode: `diff`
- 9 accepted, 0 rejected (0 exonerated)

## Accepted Findings

### FINDING_1: `compose_pr_body` reintroduced inline `Closes #N` composition
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-stall-recovery-output.txt, dyn-python-pr-link-output.txt
- **Severity**: important
- **Concern**: `compose_pr_body` appends `Closes #N` with raw string logic instead of routing through `tracking_issue.link_pr_closes`. That violates the single-composer plan acceptance, splits behavior from `ensure_pr`, and loses idempotency for summaries/test plans that already contain a footer-style closing line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-stall-recovery-output.txt, dyn-python-pr-link-output.txt: Address the concern above.


### FINDING_10: Step 17 write-final-report failures are not mechanically captured like Step 18b failures
- **Reviewer(s)**: dyn-teardown-flow-output.txt
- **Severity**: latent
- **Concern**: Step 18b now logs token/WFR failures through the wrapper, but Step 17 still depends on prompt-side prose rather than a Bash-fenced `append-tool-failure.sh` capture. If the orchestrator skips that prose, later Step 18 emission can mask the earlier failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-flow-output.txt: Address the concern above.


### FINDING_13: Stall-recovery classify and clear/seed disagree on symlinked state files
- **Reviewer(s)**: dyn-stall-recovery-output.txt
- **Severity**: important
- **Concern**: `cmd_classify` reads `ship-pr-state.sh` when `[ -f "$state_file" ]`, including symlinks to regular files, but `clear-stall` and `seed-terminal-state` reject symlinks. A readable symlinked state can classify successfully but then fail the documented clear/seed success path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stall-recovery-output.txt: Address the concern above.


### FINDING_14: Keyless regular stall state can prevent successful recovery cleanup
- **Reviewer(s)**: dyn-stall-recovery-output.txt
- **Severity**: important
- **Concern**: When `ship-pr-state.sh` exists and is syntax-valid but has no stall keys, `clear-stall` exits 0 with `CLEARED=false` and leaves disk unchanged. If stall evidence exists only in `session-env.sh`, successful recovery can still be routed to terminal failure because Step 7 requires `CLEARED=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stall-recovery-output.txt: Address the concern above.


### FINDING_16: Stall-recovery test stub consumes argv and passes for the wrong reason
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: The new `read-session-env-key.sh` test stub shifts through all arguments and falls through to the real helper with an empty argv. Destination-read-failure cases can therefore fail on a pre-`mv` temp read instead of the intended post-`mv` destination assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


### FINDING_17: Harness contract docs and lint registry are stale for Step 18b/Case 22 coverage
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Several sibling docs/registry entries no longer describe the executable harnesses accurately: `test-write-final-report.md` still references retired Step 18 `--print-stdout`, `test-stall-recovery-report.md` omits Case 22, `test-step-18b-final-report.md` omits the real integration case, and `docs/linting.md` does not mention new clear/seed durability coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.

### FINDING_2: `link_pr_closes` treats body-wide Mermaid/prose mentions as a real footer
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stall-recovery-output.txt, dyn-python-pr-link-output.txt
- **Severity**: important
- **Concern**: `link_pr_closes` searches the whole body for `Closes #N`, so `ensure_pr` can skip appending a real GitHub closing footer when the only match is inside Mermaid, prose, or another non-footer context. Reviewers also flagged footer/terminator matching semantics as needing tightening before `compose_pr_body` delegates back to the helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stall-recovery-output.txt, dyn-python-pr-link-output.txt: Address the concern above.


### FINDING_3: Closes regression tests are weak or encode the split behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Tests do not reliably lock the intended single-helper behavior: compose-path tests can pass while bypassing `link_pr_closes`, `ensure_pr` lacks integration coverage for prefix-collision/idempotency behavior, substring-only assertions are weak, and one Mermaid test may encode the reverted split rather than the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_9: Step 18b snapshot failure can suppress refreshed final-report emission
- **Reviewer(s)**: dyn-teardown-flow-output.txt
- **Severity**: important
- **Concern**: If `.step17-emitted` exists and the pre-write snapshot copy fails, `step-18b-final-report.sh` does not promote a changed `summary-final.md` even when `write-final-report.sh` succeeds. The orchestrator can skip the Step 18 chat emit and leave users with stale Step 17 summary/cost text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-flow-output.txt: Address the concern above.


