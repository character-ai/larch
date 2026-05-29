### FINDING_1: round cursor and cap counter can desynchronize after snapshot failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Step 3 cursor/cap advancement and assessor round numbering are not driven by one successfully materialized round state. A write-after failure can leave cursor/cap state ahead of missing or stale `plan-after-round-N` artifacts, causing retries to consume cap slots, reuse/clobber round artifacts, or compare the wrong snapshots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_2: missing snapshot preflight bypasses execution-issues audit logging
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 3.6 duplicates missing-input checks, skips `assess-plan-round.sh`, and does not call `append-tool-failure.sh`. Operators see only chat warnings when required snapshots are absent, while `execution-issues.md` lacks the required warning/audit trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: write-after failures are mislabeled as assessor degradation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Snapshot I/O failure is recorded as `degraded-default-open` with `EFFECTIVE_ASSESSORS=0`, which can mislead operators into looking for assessor verdict artifacts that were never produced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: first-round assessor call always pays for a skipped subprocess
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `assess-plan-round.sh` is invoked on round 1 even though the orchestrator always skips assessment there, adding unnecessary process and parsing overhead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: degraded verdict artifact schema is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_default_verdict_artifacts` duplicates degraded `.env` schema logic from `tally-plan-assessor.sh`, making future field additions easy to miss in one path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: structural test misses cancelled-assessor-worse harness pin
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-design-structure.sh` does not pin the `cancelled-assessor-worse` case in `test-render-final-summary.sh`, so that harness coverage could be removed without structural CI detecting it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] strip_md_bold corrupts literal asterisks
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `strip_md_bold` strips all asterisks rather than only paired Markdown wrappers, which can corrupt assessor reasoning containing literal `*` characters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] malformed cursor warning lacks reason detail
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `snapshot-plan-round.sh` emits a generic malformed cursor warning, making empty, non-numeric, or whitespace-related cursor problems harder to diagnose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: tally parser uses the last assessment instead of the first
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `parse_assessment` keeps parsing later `ASSESSMENT` lines, so a response with an initial valid verdict followed by another verdict can be tallied using the later value and incorrectly continue or stop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: verdict token parsing rejects valid assessments with trailing rationale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The verdict value is validated without first isolating the first token, so lines like `ASSESSMENT WORSE because ...` fail validation and can exclude assessors, potentially fail-opening the panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] assessor Claude slot is not parallel with external assessors
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The Claude assessor slot runs before the external waterfall instead of in parallel with it, increasing panel wall-clock time if true parallel dispatch was intended.
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

### FINDING_14: Step 3.6 WORSE-majority UX lacks automated coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The operator-facing WORSE-majority path, including AskUserQuestion behavior, `QUALIFICATIONS_SUMMARY`, and Stop cancellation outcome, could regress without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: cap-reached and degraded-empty-collector bypass paths lack structural pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Step 3 short-circuit paths for cap reached and degraded empty collector are not structurally pinned, so future refactors could accidentally route them through Step 3.6 with the wrong loop status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: assessor timing-kind structural pins are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Structural timing-kind tests cover only a subset of the twelve phase-qualified assessor slugs, allowing accidental removal of unpinned slugs to escape CI until runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: write-original structural pin does not verify HARD-only gating
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The `write-original` structural pin does not assert that snapshot creation remains guarded to HARD workflows, so SIMPLE/TRIVIAL paths could start writing snapshots unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: dispatch harness does not verify Cursor-to-Codex-to-Claude retry chain
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The narration-only Cursor dispatch test only verifies `DISPATCH_OK=false` and does not assert the planned fallback/retry chain through Codex and then Claude, so waterfall retry wiring could regress without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: assessor prompt lacks untrusted-input delimiters
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `render-assessor-prompt.sh` inlines the feature and plan files without explicit untrusted-data boundaries, allowing instruction-like text inside revised plans to influence external assessor votes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

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

### FINDING_22: assessor dispatch accepts unconstrained input and output paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Helper scripts do not confine assessor input/output paths to `DESIGN_TMPDIR`, so direct invocation with arbitrary paths could exfiltrate local files to assessors or write verdicts outside the session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_23: write-original exit status is ignored
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 2b does not check whether `write-original` succeeded. Disk or permission failures can leave no `plan.txt-original`, causing later assessor rounds to fail-open without a hard stop at plan emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: write-after refuses overwrite and can preserve stale snapshots
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `snapshot-plan-round.sh` refuses to overwrite an existing `plan-after-round-N`, so same-round replay after `plan.txt` changes can keep a stale snapshot while cursor advancement treats it as valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: feature-description path resolution prefers IMPLEMENT_TMPDIR over DESIGN_TMPDIR
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` resolves `feature-description.txt` from `IMPLEMENT_TMPDIR` before `DESIGN_TMPDIR`, which can skip assessment in nested or split-tmpdir orchestration even when the design tmpdir contains the feature file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_26: degraded verdict artifacts are written non-atomically
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `write_default_verdict_artifacts` can leave a partial `assessor-verdict-round-N.env` if interrupted mid-write.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] short-circuit paths skip Gate B and Step 3.6 assessor
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: HARD runs that hit degraded-empty-collector or cap-reached skip the plan-quality assessor entirely, which may be intentional but should be documented or changed if parity is desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_28: cancelled-assessor-worse is missing from consolidated cancellation outcomes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `cancelled-assessor-worse` is documented as a state invariant but not listed alongside other cancellation outcomes in a consolidated cancellation-outcomes summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
