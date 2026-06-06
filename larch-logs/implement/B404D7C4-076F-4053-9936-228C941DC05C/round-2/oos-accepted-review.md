### OOS_3: [OUT_OF_SCOPE] Bootstrap wrapper self-derivation can resolve the wrong tree or fail unclearly
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `implement-bootstrap-invoke.sh` derives `CLAUDE_PLUGIN_ROOT` from `$0` for non-contract invocations but does not validate plugin layout at the derive site. Relative, symlinked, copied, or failed-`cd` cases can produce a wrong or empty root and fail later with unclear errors; current tests cover only successful self-derive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Add post-derive existence check for implement-bootstrap.sh or fail at derive site with clear message.
  - From cursor-specialist-testing-output.txt: Add negative sandbox case where derivation yields empty value and assert non-zero exit with CLAUDE_PLUGIN_ROOT must be set


### OOS_4: [OUT_OF_SCOPE] `run-step5-review.md` launcher docs are stale
- **Reviewer(s)**: dyn-step5-runtime-output.txt
- **Severity**: latent
- **Concern**: The docs still describe a `--round-num`-required, `--mode diff`-only launcher and omit `--mode loop` plus session-env dynamic-archetypes forwarding, widening drift now that Step 5 banner logic depends on that launcher contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step5-runtime-output.txt: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] `append-execution-issue.sh` blurs usage-vs-I/O failure classes for unreadable entry files
- **Reviewer(s)**: dyn-quiet-contract-output.txt
- **Severity**: latent
- **Concern**: An unreadable `--entry-file` is currently routed through `fail_usage`, producing exit 1 and `USAGE=` even though the argv shape is valid and the failure is a runtime readability problem. Tests also do not pin that exit-2 I/O envelopes omit `USAGE=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-contract-output.txt: Handle unreadable `--entry-file` with the exit-`2` I/O envelope (no `USAGE=`), or document and test it as an explicit third validation class if `USAGE=` on path errors is intentional.
  - From dyn-quiet-contract-output.txt: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] Step 5 preflight-failure routing and Warnings logging are underspecified
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-step5-runtime-output.txt, dyn-make-harness-output.txt
- **Severity**: important
- **Concern**: Step 5 prose says to treat non-zero fence exit or non-integer telemetry as hard preflight failure and log to `Warnings`, but does not clearly say whether to stall, continue with defaults, skip `run-step5-review.sh`, or route to Step 18. It also lacks a literal `append-execution-issue.sh --log ... --category Warnings --entry ...` example, leaving the prior helper-argv misuse mode live on this new path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Define explicit failure routing: stall or use documented safe defaults; never continue with unset banner variables.
  - From dyn-step5-runtime-output.txt: State explicitly that a failed telemetry fence must not invoke `run-step5-review.sh` (or must set `STALL_TRACKING` and route to Step 18), and add one fenced example: `append-execution-issue.sh --log "$IMPLEMENT_TMPDIR/execution-issues.md" --category Warnings --entry "- **Step 5**: banner preflight failed: …"`.
  - From dyn-step5-runtime-output.txt: Address the concern above.
  - From dyn-make-harness-output.txt: Add a literal one-line `append-execution-issue.sh` invocation at `skills/implement/SKILL.md:812` (and mirror it at the Step 2 call site around line 630), using the `USAGE=` contract from `scripts/append-execution-issue.sh`.


