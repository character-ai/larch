# Review Round 1

- Mode: `diff`
- 4 accepted, 7 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Step 5b annotate fence unconditional and misordered
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: blocking
- **Concern**: Step 5b places `design-step5b-annotate.sh` unconditionally after `NEXT_ACTION` branch bullets instead of only under `file-issues`. On `NEXT_ACTION=skip-pipeline` (e.g. `skip-no-items`), the orchestrator still runs annotate even when `finalize-step5.md` says annotate is not needed, risking spurious failures or wrong `.completed/step-5b` state before Step 5b.5. On `file-issues`, annotate may run twice. Because `file-issues` is a forward reference, annotate can run before `/larch:issue`, leaving empty `oos-issue.stdout.txt` and continuing without filed OOS issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Optional raw-pending dialectic sidecar write can abort valid draft
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Optional raw-pending dialectic sidecar write at `python/agents.py:3386-3389` is unguarded and can abort a valid draft. Read-only or full tmpdir causes the optional `.dialectic-raw-pending.json` write to fail, which currently kills the whole drafter run even though the plan itself parsed successfully.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Dialectic promotion limited to postplan rc 0
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Dialectic promotion at `python/design_lifecycle.py:3667-3670` only runs for postplan rc 0, not for all success outcomes the wrapper accepts. When Step 2b exits via plan-size-trigger or partition-requested success paths, the raw dialectic sidecar is never promoted and is then deleted on the next run, so Gate C loses valid candidates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: `--probe-only` writes Gate C completion sentinel
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: At `python/design_dialectic.py:917-931`, `--probe-only` still writes the Gate C completion sentinel. The preflight probe can satisfy later recovery checks before the real tail has run, so the orchestrator may believe Gate C already completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


