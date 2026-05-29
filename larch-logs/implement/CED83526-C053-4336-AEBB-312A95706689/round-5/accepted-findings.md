### FINDING_1: round cursor and cap counter can desynchronize after snapshot failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Step 3 cursor/cap advancement and assessor round numbering are not driven by one successfully materialized round state. A write-after failure can leave cursor/cap state ahead of missing or stale `plan-after-round-N` artifacts, causing retries to consume cap slots, reuse/clobber round artifacts, or compare the wrong snapshots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: verdict token parsing rejects valid assessments with trailing rationale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The verdict value is validated without first isolating the first token, so lines like `ASSESSMENT WORSE because ...` fail validation and can exclude assessors, potentially fail-opening the panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: stale-output sweep test misses diagnostic and JSON sidecars
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The stale-output cleanup test only verifies `.txt` artifacts and omits `.diag`/`.json` sidecars, so stale sidecar metadata could survive cleanup without CI detecting it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: no behavioral test covers successful HARD cursor advancement
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no behavioral regression test proving that, after round 1 write-after succeeds and cursor advances, the next HARD review loop receives `--round-num 2`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: dispatch harness does not verify Cursor-to-Codex-to-Claude retry chain
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The narration-only Cursor dispatch test only verifies `DISPATCH_OK=false` and does not assert the planned fallback/retry chain through Codex and then Claude, so waterfall retry wiring could regress without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: missing snapshot preflight bypasses execution-issues audit logging
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 3.6 duplicates missing-input checks, skips `assess-plan-round.sh`, and does not call `append-tool-failure.sh`. Operators see only chat warnings when required snapshots are absent, while `execution-issues.md` lacks the required warning/audit trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_20: full assessor verdict is displayed without untrusted handling
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Step 3.6 prints the full assessor verdict artifact to the operator while only marking `QUALIFICATIONS_SUMMARY` as untrusted, exposing synthesized reasoning text verbatim at the Continue/Stop decision point.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_21: SECURITY.md lacks assessor panel trust-boundary documentation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The external Step 3.6 assessor panel ships without canonical `SECURITY.md` documentation covering assessor delegation, untrusted rationale handling, and fail-open behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_23: write-original exit status is ignored
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 2b does not check whether `write-original` succeeded. Disk or permission failures can leave no `plan.txt-original`, causing later assessor rounds to fail-open without a hard stop at plan emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_25: feature-description path resolution prefers IMPLEMENT_TMPDIR over DESIGN_TMPDIR
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` resolves `feature-description.txt` from `IMPLEMENT_TMPDIR` before `DESIGN_TMPDIR`, which can skip assessment in nested or split-tmpdir orchestration even when the design tmpdir contains the feature file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: write-after failures are mislabeled as assessor degradation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Snapshot I/O failure is recorded as `degraded-default-open` with `EFFECTIVE_ASSESSORS=0`, which can mislead operators into looking for assessor verdict artifacts that were never produced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: structural test misses cancelled-assessor-worse harness pin
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-design-structure.sh` does not pin the `cancelled-assessor-worse` case in `test-render-final-summary.sh`, so that harness coverage could be removed without structural CI detecting it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: tally parser uses the last assessment instead of the first
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `parse_assessment` keeps parsing later `ASSESSMENT` lines, so a response with an initial valid verdict followed by another verdict can be tallied using the later value and incorrectly continue or stop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


