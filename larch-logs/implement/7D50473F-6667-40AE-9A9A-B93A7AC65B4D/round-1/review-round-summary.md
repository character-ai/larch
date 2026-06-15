# Review Round 1

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_8: `hook-bg-poll-guard.sh` completion-release checks unreliable/missing terminal sentinels
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New completion-release cases in `scripts/hook-bg-poll-guard.sh:82-85` check sentinels that are not reliable terminal markers for the actual wrappers. Step 5c with `PLAN_WRITE_OK=false` does not write `.completed/step-5c`. `design-step-final-summary.sh` never writes `.completed/step-5d` (Step 6 prelude writes step-5d, not final-summary completion). In a same-turn task-notification race, while `.bg-wait-active` is still live, the hook can deny Read fallback for `final-summary.md` because the expected sentinel is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Write true per-wrapper terminal sentinels after artifacts are ready, and update marker_step_completed plus tests to use those sentinels.
  - From codex-specialist-edge-cases-output.txt: Add a final-summary-owned completion sentinel before design-step-final-summary.sh exits and have marker_step_completed check it, or remove the final-summary release until such a sentinel exists; update the hook test to use the real sentinel.
  - From codex-specialist-testing-output.txt: Have design-step-final-summary.sh write a real terminal sentinel and update the hook/test to use it, or remove the final-summary release case until that sentinel exists.

---


