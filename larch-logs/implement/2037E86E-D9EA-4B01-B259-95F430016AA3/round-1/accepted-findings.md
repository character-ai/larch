### FINDING_1: lib-cost-line-format inherits global shell strict mode
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: A sourced library runs `set -euo pipefail` at top level, contradicting a no-side-effects-style expectation: parents inherit `errexit`/`nounset`/`pipefail` and may fail or mishandle errors in unrelated code after the `source` line unless flags are scoped or removed and the header comment matches behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_10: Legacy blended env vars mis-price per-bucket lanes when per-bucket counts are active
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `LARCH_CLAUDE_RATE_PER_M` / `LARCH_TOKEN_RATE_PER_M`-style blended overrides are used as fallback rates for each per-bucket lane when per-bucket env vars are unset, even on the per-bucket token path—so an operator keeping an older blended override can inflate/deflate specific buckets (e.g., cache-heavy runs) versus differentiated defaults unless legacy blended applies only on aggregate fallback or is explicitly documented and covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: `token-report.sh` jq path drops usage rows lacking `.timestamp`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: A `jq` filter requires `.timestamp` on assistant usage rows; hypothetical/corrupt JSONL with `message.usage` but no `timestamp` omits billing-relevant tokens from totals/cost unless the requirement is relaxed, documented, and tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: `test-report-tokens-recompute.sh` env can be overwritten by `run-analysis.sh` exports from empty CLI flags
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `NO_ISSUE` / `NO_PLOT` (and similar harness env) may be overwritten by `run-analysis.sh` exporting from empty CLI flags, causing `run-analysis.sh` to exit non-zero after `gh` auth succeeds—risking red CI without a clear `FAIL` line on stdout unless flags/env precedence is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Unvalidated `int()` coercion on bucket/total fields before invoking `token-cost.sh`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Corrupt/hostile JSON types can make `int()` coercion throw, crashing the Python analyzer (availability) instead of degrading safely; suggests guarded coercion/defaulting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_17: `num()` silently maps malformed numerics to zero in `token-cost.sh`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Silent coercion can understate tokens/cost for typos or pasted values with commas unless input is validated, documented, or fails closed on bad input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: render-cost-line realism harness never enforces ±10% bound
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The realism harness is effectively a stub: even when a gated fixture exists, no reference replay / numeric ±10% assertion runs, so acceptance/plan claims about end-to-end realism do not hold and checked-in fixtures would not block regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Step 5 review loop refactor bundled with token-cost work
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: A large Step 5 (`run-step5-review` and related) change set is bundled with DE-2622 cost work despite the cost plan treating Step 5 as unchanged, increasing unrelated orchestration risk, bisect difficulty, and review surface unless stacks are split or intentional coupling is documented in the PR narrative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_4: token-cost failure surfaces as authoritative $0.00 cost line
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Failed or empty `token-cost` invocation can yield empty KV input so downstream parsing fills `0.00`, emitting a plausible zero-dollar formatted line while diagnostics may be partial—masking failure after the cost line became authoritative (parallel paths cited in one source include `render-run-summary.sh` and `token-report.sh`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: callsite guards pin known files instead of repo-wide invocation contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Tests/guards only inspect narrow windows (e.g., design `SKILL` block, specific scripts) rather than every `render-cost-line` / related invocation repo-wide, so new aggregate-only or wrong-flag call sites can ship without CI failure despite plan “every call site” intent (including `render-run-summary` wiring called out separately).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: report-tokens analyzer costing/env wiring diverges from token-cost subprocess; stderr suppressed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Embedded Python uses separate `RATES` / env-key families vs `token-cost.sh`, so vendor trend/table dollars can drift from subprocess headline totals; `subprocess` stderr is dropped (`DEVNULL`), hiding blended-fallback and similar warnings operators might need when trusting estimates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: report-tokens recompute regression test skips without authenticated `gh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: The harness exits success with `SKIP` when `gh` is missing or unauthenticated, so typical CI without `gh` auth often never runs the fixture regression the plan describes; recomputation regressions can ship undetected without an offline/hermetic path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


