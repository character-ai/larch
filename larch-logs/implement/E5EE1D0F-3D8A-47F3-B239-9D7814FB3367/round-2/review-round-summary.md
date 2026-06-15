# Review Round 2

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_11: `step-2b.5` sentinel may be non-authoritative from completion-only writes
- **Reviewer(s)**: dyn-prompt-structure-output.txt
- **Severity**: important
- **Concern**: The new fail-safe prose treats `.completed/step-2b.5` as proof that "the successful postplan path already wrote the Step 2b.5 sentinel," but `design-step2b-postplan.sh` also writes that sentinel on `--write-completion-only` without running `design-postplan-emit.sh` or emitting `POSTPLAN_RC=` / `POSTPLAN_STATUS=` rows (`skills/design/scripts/design-step2b-postplan.sh:122-133`). On resume or re-entry, a stale `step-2b.5` from completion-only can coexist with missing wrapper stdout rows on a fresh drafter attempt, so the new rule can halt even though the orchestrator never got authoritative postplan KVs for the current plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-structure-output.txt: Narrow the SKILL contract: either document `--write-completion-only` as a non-authoritative `step-2b.5` writer, clear `step-2b.5` at drafter entry when re-running Step 2b, or gate fail-closed on a stronger signal (for example `POSTPLAN_EMIT_STATUS=ok` in `.design-postplan-emit-result.env` plus `step-2b.5`).


### FINDING_12: Postplan fail-safe ignores durable sidecar authority
- **Reviewer(s)**: dyn-prompt-structure-output.txt
- **Severity**: important
- **Concern**: The fail-safe branch is stdout-only (`POSTPLAN_RC=` / `POSTPLAN_STATUS=` wrapper rows), but the same SKILL already names `$DESIGN_TMPDIR/.design-postplan-emit-result.env` as the durable machine-key surface for postplan. When drafter `exec` postplan succeeds and writes `step-2b.5` but stdout rows are lost in capture, fail-closed halts instead of consulting the sidecar that postplan already populated. That splits authority across two contracts in one step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-structure-output.txt: In the missing-row branch, define precedence explicitly: if `step-2b.5` exists and `.design-postplan-emit-result.env` shows a successful emit (`POSTPLAN_EMIT_STATUS=ok` / plan-size KVs), bind routing from the sidecar and continue; reserve fail-closed for absent or conflicting sidecar state.


