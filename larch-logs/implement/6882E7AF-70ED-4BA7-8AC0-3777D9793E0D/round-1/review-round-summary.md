# Review Round 1

- Mode: `diff`
- 2 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_2: correctness — pre-work pause path exits with helper status instead of wrapper rc 11
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Direct pre-work pause path in `skills/design/scripts/design-step35-settle.sh:132` exits with `design-pause-save.sh` status instead of the wrapper pause rc 11. If `.pause-requested` exists before Gate B settle starts, `design-pause-save.sh` emits `PAUSE_OK=true` and exits 0, so the caller treats settle as clean and continues Step 3.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Capture pause-save output, print it, and exit 11 on `PAUSE_OK=true` or `.pause-save-complete` instead of execing the helper directly.


### FINDING_6: risk-integration — Gate B settle skips dedup on plan-changing retry after ready marker exists
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-step35-settle.sh:153-175` — Gate B settle skips dedup whenever `.gate-b-postapply-ready-N` exists, but new retry docs send plan-changing validator Fix-and-retry and autofix paths back through this same wrapper after that marker has already been written. A Gate B postplan `POSTPLAN_RC=10` can write the marker, the operator can edit `plan.txt`, and the retry will bypass `gate-b-dedup-plan.sh --dedup`, so duplicate cleanup and optional-trailer validation do not run on the repaired plan before continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Split pure idempotent resume from plan-changing retry. Add a `--force-dedup` or clear the ready marker before Gate B Fix-and-retry/autofix paths, then cover that case in `test-gate-b-dedup-plan.sh`.


