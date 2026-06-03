# Review Round 3

- Mode: `diff`
- 11 accepted, 6 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: Gate-B bypass paths miss Step 3.5/3.6 completion sentinels
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-thin-fence-output.txt, dyn-classification-gate-output.txt, dyn-pause-resume-output.txt
- **Severity**: important
- **Concern**: Gate-B-bypass branches skip Step 3.5 and Step 3.6 but only mark Step 3 complete. Pause/resume then treats the run as needing Step 3.5 and can re-enter intentionally skipped Gate B/assessor work. The fix is to write `.completed/step-3`, `.completed/step-3.5`, and `.completed/step-3.6` before routing every bypass path to Step 3b, with matching structure and pause/resume coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-thin-fence-output.txt: Address the concern above.
  - From dyn-classification-gate-output.txt: Address the concern above.
  - From dyn-pause-resume-output.txt: Address the concern above.


### FINDING_11: Missing metacharacter injection test for qualification summaries
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The assessor test harness lacks a tmpdir sidecar injection case for metacharacters such as `$()` in `QUALIFICATIONS_SUMMARY`, reducing regression coverage for unsafe parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_12: rc=11 pause-save handoff omits repo passthrough
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The rc=11 pause-save path does not pass through `--repo` when `REPO` is in scope, so fork or explicit-repo runs may write pause markers with the wrong GitHub repo binding. Structure pins for this behavior are also missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_14: SECURITY.md has stale Step 3.6 Stop trust-boundary text
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: A legacy `SECURITY.md` paragraph says Stop reads the round from `.step3.6-assessor.env`, contradicting the new trailer-only Stop control boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: Assessor reference docs describe obsolete paused UX
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/references/assessor.md` still documents in-driver `design-pause-save` execution on `ASSESSOR_STATUS=paused`, conflicting with rc=11 orchestrator pause-save semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_17: `design-postplan-emit.md` still describes legacy `workflow_path` snapshot gating
- **Reviewer(s)**: dyn-classification-gate-output.txt
- **Severity**: latent
- **Concern**: The docs say snapshot eligibility uses `workflow_path=HARD` from `run-params.json`, while the script now gates on `design_classification` from `read-design-classification.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-classification-gate-output.txt: Address the concern above.


### FINDING_2: Gate-B bypass pause/resume test encodes the wrong resume point
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-thin-fence-output.txt, dyn-pause-resume-output.txt
- **Severity**: important
- **Concern**: The Gate-B-bypass pause test currently expects `STEP=3.5` when only `step-3` is complete, which codifies the buggy state rather than the intended bypass contract. Tests should assert the triple-sentinel bypass layout and resume at `STEP=3b`, with regression coverage for missing sentinels and registry pins where required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-thin-fence-output.txt: Address the concern above.
  - From dyn-pause-resume-output.txt: Address the concern above.


### FINDING_3: Structure harness lacks planned thin-fence and bypass-sentinel guards
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-thin-fence-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` does not add the planned reusable `assert_thin_fence` helper, Step 3.6 anti-shape checks, or sufficient pins for bypass triple-sentinel writes. CI may miss regressions back to fat handoff parsing or missing bypass sentinels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-thin-fence-output.txt: Address the concern above.


### FINDING_4: Assessor contract docs still describe obsolete fat handoff
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `design-plan-quality-assessor.md` still documents env parsing, symlink fallback, old exit tables, and/or orchestrator behavior from the fat-handoff design. This contradicts the thin-fence implementation and may lead future contributors to reintroduce unsafe or obsolete orchestration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: `assess-plan-round.sh` merges stdout and stderr when resolving classification
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-classification-gate-output.txt
- **Severity**: latent
- **Concern**: Classification resolution uses merged stdout/stderr with `tail -n 1`, so warnings or later stderr/stdout can alter the interpreted classification. It should capture stdout and stderr separately and default fail-closed to HARD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-classification-gate-output.txt: Address the concern above.


### FINDING_9: Legacy assessor KV lines are not neutralized
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Display neutralization covers `LARCH_ASSESSOR_*` but not legacy `ASSESSOR_RC=` or `ASSESSOR_ROUND_NUM=` lines, allowing assessor prose to show spoofed legacy trailer-like values before trusted trailer lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


