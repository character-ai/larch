# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 exonerated)

## Accepted Findings

### FINDING_11: Raw dispatcher `REASON` mirroring can redact public output and misclassify compound tokens
- **Reviewer(s)**: dyn-shell-state-output.txt, dyn-workflow-handoff-output.txt
- **Severity**: important
- **Concern**: The new `STATUS=bailed` bullet mirrors raw dispatcher `REASON` into bail handoff variables; many such tokens are outside the closed enum, and tokens like `dirty-state-after-timeout` can substring-match `timeout` and route to `transient-infra` instead of dispatch-failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-state-output.txt: Either map known Step-2 dispatcher `REASON` tokens to closed-enum bail values before setting `IMPLEMENT_BAIL_REASON` (and extend `safe_bail_reason_value` for tokens like `dirty-state-after-timeout` / `main-branch-post-dispatch` that should render verbatim), or tighten the transient-infra matcher so compound bail tokens containing `timeout` do not false-positive before dispatch-failure classification; add a harness case for `classify --bail-reason dirty-state-after-timeout` to lock the intended class.
  - From dyn-workflow-handoff-output.txt: Either map known dispatcher `REASON` tokens to allowlisted equivalents before setting `IMPLEMENT_BAIL_REASON` (e.g. `wrapper-validation-failure`, `qa-loop-exceeded`), or document in §2.2 that only allowlisted tokens produce a verbatim Bail reason row and raw tokens are classification-only.

### FINDING_5: Step-2 hard-bail handoff can lose bail reason, step, and phase when no state file exists
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-workflow-handoff-output.txt
- **Severity**: important
- **Concern**: Step-2 hard-bail recovery relies on in-memory values and does not reliably persist/pass `BAIL_REASON`, `STALL_STEP`, or `PHASE`; with no `ship-pr-state.sh`, classify can emit `STALL_STEP=unknown` or default to Step 8 and produce the wrong resume hint or `Bail reason none`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Persist sanitized bail at hard-bail sites or seed into ship-pr-state before Step 18a.
  - From codex-specialist-edge-cases-output.txt: Add explicit in-memory step/phase handoff and test the no-state-file Step-2 hard-bail path.
  - From dyn-workflow-handoff-output.txt: At each Step-2 hard-bail site, also set in-memory `STALL_STEP=2` and an appropriate phase (e.g. `implementation` or `checks`), pass them into classify if needed, and add an argv-only fixture with `--in-memory-stall-tracking true`, no `ship-pr-state.sh`, and assert `STALL_STEP=2` plus `RESUME_HINT=step2-impl`.


### FINDING_8: `cmd_classify` ignores `BAIL_REASON` from `finalize-state.sh`
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A default Python-path terminal stall with finalize-state `BAIL_REASON=first-fixer-non-health` can render the new public Bail reason row as `none`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Load finalize_bail_reason and include it in bail precedence with a finalize-only rendering regression.


