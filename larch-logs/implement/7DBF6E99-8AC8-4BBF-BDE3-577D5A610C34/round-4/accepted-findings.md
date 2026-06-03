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


### FINDING_15: rc=10 pending prompt can be mishandled as settled completion
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-shell-fence-output.txt
- **Severity**: important
- **Concern**: The rc=10 case arm is a no-op and completion-marker prose is ambiguous. An orchestrator could halt, advance, or write `step-3.6` before the Continue/Stop decision, leaving a false completion sentinel or skipping the required prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-shell-fence-output.txt: Address the concern above.


### FINDING_19: Legacy `STEP=3b` pause markers can skip the new Step 3.6 assessor
- **Reviewer(s)**: dyn-pause-resume-output.txt
- **Severity**: important
- **Concern**: Resume load/route trusts frozen `STEP=3b` markers from before Step 3.6 existed. A HARD design paused after Gate B can resume directly to 3b with `step-3.6` missing, permanently skipping the new assessor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-output.txt: Address the concern above.


### FINDING_4: Design classification is stored under misleading `workflow_path` naming
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `assess-plan-round.sh` stores `resolve_design_classification` output in `workflow_path`, inviting future maintainers to confuse new design classification semantics with legacy workflow-path behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: rc=10 fail-closed trailer tests miss no-marker spoof cases
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Handoff tests cover invalid numeric trailers but not rc=10 outputs with no trusted marker frame or display-only spoof markers. The orchestrator could leak trailers or prompt without validating the final trusted frame.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


