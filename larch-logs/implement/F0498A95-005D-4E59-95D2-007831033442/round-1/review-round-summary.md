# Review Round 1

- Mode: `diff`
- 1 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Missing `.degraded-tools-gate-prompted` sentinel short-circuit in folded session gate
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, dyn-step0-flow-output.txt, dyn-gate-envelope-output.txt
- **Severity**: important
- **Concern**: The folded degraded gate in `design-step0-session.sh` always re-runs and, on interactive both-down (`DEGRADED=true`, `BOTH_DOWN=true`), emits `STEP0_STATUS=needs-degraded-decision` and `DEGRADED_PROMPT_REQUIRED=true` without checking whether `$DESIGN_TMPDIR/.degraded-tools-gate-prompted` already exists. Step 0a re-entry against the same `DESIGN_TMPDIR` after the operator chose Continue can duplicate the degraded prompt, unlike `/implement` bootstrap's `sentinel_exists` handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Check for .degraded-tools-gate-prompted before the interactive branch; emit degraded-both-down-auto or proceed without DEGRADED_PROMPT_REQUIRED when the sentinel is present.
  - From codex-specialist-correctness-output.txt: Check the sentinel before choosing needs-degraded-decision and proceed degraded when it already exists.
  - From dyn-step0-flow-output.txt: At the start of the gate block, if `.degraded-tools-gate-prompted` is present, skip `agent degraded-tools-gate`, emit `STEP0_STATUS=degraded-one-down` (or a dedicated `degraded-already-prompted` status), and avoid re-emitting `DEGRADED_PROMPT_REQUIRED=true`; add a harness pin for the sentinel short-circuit.
  - From dyn-gate-envelope-output.txt: Before branch selection, if `[ -f "$DESIGN_TMPDIR/.degraded-tools-gate-prompted" ]` and `DEGRADED=true` with `BOTH_DOWN=true` in interactive mode, emit `STEP0_STATUS=ok` (or `degraded-both-down-auto`) and omit `DEGRADED_PROMPT_REQUIRED`.


