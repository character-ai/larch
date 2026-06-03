### FINDING_1: [OUT_OF_SCOPE] Step 3.6 thin-fence structure tests are not step-scoped
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-fence-output.txt, dyn-pause-resume-output.txt
- **Severity**: important
- **Concern**: `assert_thin_fence` checks whole files and is also applied to the driver script, so it does not mechanically pin the Step 3.6 orchestrator fence shape. A regression could reintroduce file-first env parsing, symlink refusal, `phase_driver_read_result_env`, or the wrong rc/display handling while CI remains green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-fence-output.txt, dyn-pause-resume-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Gate-B-bypass triple-sentinel writes are duplicated and prompt-dependent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-fence-output.txt
- **Severity**: important
- **Concern**: Gate-B-bypass branches rely on duplicated prose to write `step-3`, `step-3.5`, and `step-3.6`. If one bypass branch misses a sentinel, pause/resume can rerun skipped Gate B or advance incorrectly. Tests pin breadcrumbs more than the per-branch sentinel contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-fence-output.txt: Address the concern above.

### FINDING_3: Trailer parsing logic is duplicated between SKILL and harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Trusted trailer parsing exists in both the Step 3.6 fence and the handoff harness. Future validation changes must be edited in lockstep, risking drift that could break spoof protection or fail-closed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Design classification is stored under misleading `workflow_path` naming
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `assess-plan-round.sh` stores `resolve_design_classification` output in `workflow_path`, inviting future maintainers to confuse new design classification semantics with legacy workflow-path behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Assessor machine KVs are printed into user-facing chat
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ASSESSOR_RC` and `ASSESSOR_ROUND_NUM` are echoed alongside display output, mixing machine-readable handoff lines with operator-facing WORSE copy despite the FD-3/display split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Step 3.6 lacks a start breadcrumb comparable to peer steps
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Step 3.6 does not clearly print an orchestrator-owned start breadcrumb before the cheap gate. SIMPLE runs may only show a skip line, while HARD runs depend on driver output for visibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Resume ladder hardcodes fractional step ordering
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.sh` hardcodes the `3 -> 3.5 -> 3.6 -> 3b` resume ladder before registry scanning. Future fractional steps will require more bespoke branches or risk wrong resume targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Stale harness markdown header lists retired pins
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-design-plan-quality-assessor.md` still advertises an obsolete symlink-refusal pin list, conflicting with later thin-fence regression documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: rc=10 fail-closed trailer tests miss no-marker spoof cases
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Handoff tests cover invalid numeric trailers but not rc=10 outputs with no trusted marker frame or display-only spoof markers. The orchestrator could leak trailers or prompt without validating the final trusted frame.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Assessor contract docs are stale about banner/helper ownership
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Assessor docs still reference the old helper name and/or say the orchestrator prints the HARD banner, while implementation moved banner rendering into the driver and uses the thin-fence handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Stale test comment describes obsolete empty-key abort behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: A test comment still says handoff aborts on empty mandatory keys, while the thin-fence behavior has settled differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: Partial Step 3.6 sentinel state can skip Gate B on resume
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-pause-resume-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.sh` treats `step-3.6` present and `step-3b` absent as sufficient to resume at 3b, without requiring `step-3.5` or `step-3`. A partial/corrupt sentinel layout can therefore skip Gate B.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-pause-resume-output.txt: Address the concern above.

### FINDING_13: WARN lines are emitted without diagnostic sanitization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `_emit_warn_lines` emits warning text to FD 3 without passing each line through `sanitize_diagnostic_line`, unlike WORSE display output. Control characters from classification stderr or composed warning strings could reach orchestrator chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Driver-rendered WORSE prose remains semantically untrusted to the orchestrator
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Trailer spoofing is mitigated, but the WORSE block itself is still echoed into the orchestrator LLM. Crafted assessor prose could attempt semantic prompt injection even without controlling trusted trailers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: rc=10 pending prompt can be mishandled as settled completion
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-shell-fence-output.txt
- **Severity**: important
- **Concern**: The rc=10 case arm is a no-op and completion-marker prose is ambiguous. An orchestrator could halt, advance, or write `step-3.6` before the Continue/Stop decision, leaving a false completion sentinel or skipping the required prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-shell-fence-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Post-plan classification warnings are dropped
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `design-postplan-emit.sh` resolves classification with stderr redirected to `/dev/null`, so operators may not see helper warnings explaining why a SIMPLE-looking run still snapshots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: rc=10 trailer parsing uses an unquoted heredoc that can execute command substitutions
- **Reviewer(s)**: dyn-shell-fence-output.txt
- **Severity**: important
- **Concern**: The Step 3.6 fence feeds trusted trailers through an unquoted heredoc. If a trailer value contains command substitution, Bash can execute it during parsing; `ROUND_NUM` is not validated as digits-only before trailer emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fence-output.txt: Address the concern above.

### FINDING_18: Invalid rc=10 trailer abort hides the driver-rendered display
- **Reviewer(s)**: dyn-shell-fence-output.txt
- **Severity**: latent
- **Concern**: On missing or invalid trusted trailers, the fence exits before echoing the pre-marker display. Operators see only the fail-closed stderr banner, losing the driver-rendered WORSE context already present in captured output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fence-output.txt: Address the concern above.

### FINDING_19: Legacy `STEP=3b` pause markers can skip the new Step 3.6 assessor
- **Reviewer(s)**: dyn-pause-resume-output.txt
- **Severity**: important
- **Concern**: Resume load/route trusts frozen `STEP=3b` markers from before Step 3.6 existed. A HARD design paused after Gate B can resume directly to 3b with `step-3.6` missing, permanently skipping the new assessor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-output.txt: Address the concern above.

### FINDING_20: Pause/resume tests do not cover post-3b bypass progression
- **Reviewer(s)**: dyn-pause-resume-output.txt
- **Severity**: latent
- **Concern**: Current bypass tests assert resume at 3b with bypass sentinels present, but do not simulate completing 3b and pausing again to ensure the next resume advances to Step 4 rather than re-entering Gate B or Step 3.6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-output.txt: Address the concern above.

### FINDING_21: Mid-WORSE pause reruns assessment instead of restoring pending decision
- **Reviewer(s)**: dyn-pause-resume-output.txt
- **Severity**: latent
- **Concern**: If rc=10 occurs and the operator pauses before Continue/Stop, only `step-3.5` is complete. Resume reruns the full HARD assessor rather than restoring the pending decision, potentially duplicating work or changing the verdict.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Step 3.6 entry pause guard omits explicit repo threading
- **Reviewer(s)**: dyn-pause-resume-output.txt
- **Severity**: latent
- **Concern**: The Step 3.6 entry `.pause-requested` guard omits `${REPO:+--repo "$REPO"}`, while the new rc=11 branch includes it. Fork or multi-repo flows may therefore lose explicit repo context on entry pause.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-output.txt: Address the concern above.
