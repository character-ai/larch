# Review Round 1

- Mode: `diff`
- 4 accepted, 0 rejected (2 neutral)

## Accepted Findings

### FINDING_1: bgjob child loses required launch paths
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: The quoted-heredoc cursor launcher depends on `RESEARCH_TMPDIR` and `CLAUDE_PLUGIN_ROOT` at bgjob child runtime, but those values are not exported. Under `set -u`, the child can see `RESEARCH_TMPDIR` unset and abort immediately, which breaks the Cursor validation lane or sends it into the wrong fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Export RESEARCH_TMPDIR and CLAUDE_PLUGIN_ROOT before bgjob start or bake absolute paths into the launcher at write time.


### FINDING_2: failed bgjob lanes must be gated out before collect-results
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-bgjob-contract
- **Severity**: major
- **Concern**: The research-phase collector still pre-fills `COLLECT_ARGS` before lane status is known, so a DEAD/non-zero bgjob lane can still be passed to `collect-results` instead of being excluded and sent straight to Runtime Timeout Fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Wait and gate first; build COLLECT_ARGS only from lanes with BGJOB_RC=0; remove stale before-adding wording.
  - From cursor-specialist-edge-cases: Add explicit pre-collect bgjob failure procedure: fallback launch, slot file write, COLLECT_ARGS membership rules.
  - From cursor-specialist-edge-cases: Build COLLECT_ARGS after gating or omit failed lanes like render-failure handling.
  - From codex-specialist-edge-cases: Populate COLLECT_ARGS only after the lane passes BGJOB_RC=0 and required-KV checks, or filter failed lanes out before collection.
  - From dyn-dyn-bgjob-contract: Restructure §1.4 to start with `COLLECT_ARGS=()`, wait each started lane, append the output path only after the result-env gate passes, and on failure route immediately through Runtime Timeout Fallback without including that path in `collect-results`; mirror the validation-phase “passed the gate” wording and add a harness pin for it.
  - From dyn-dyn-bgjob-contract: Add a pre-collection subsection (or cross-reference) that maps each bgjob failure (`DEAD`, `BGJOB_RC=timeout|orphaned|non-zero`, missing `STEP`) directly to the same Runtime Timeout Fallback + Claude Agent replacement flow, and state that `collect-results` must not run for that lane until fallback output exists (or the lane is dropped).


### FINDING_5: DONE gate must parse stdout KV as well as result env
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The DONE gate only checks the result env, not the DONE stdout KV block the plan allows. A lane that prints DONE with BGJOB_RC=0 and STEP in stdout but has a truncated result env would be misclassified as failed, triggering fallback or dropping valid output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_8: validation-phase collector still needs lane gating before collect-results
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: In validation-phase.md, `COLLECT_ARGS` is still built before the lane gate and failed external lanes are not explicitly omitted the way render failures are. That lets failed paths reach `collect-results`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Build COLLECT_ARGS after gating or omit failed lanes like render-failure handling.


